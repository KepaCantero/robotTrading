"""
Robust Backtesting Engine - Main Backtester Class.

This module implements the main backtesting engine capable of handling
25+ years of historical data with proper bias corrections and corporate
actions handling.

Key Features:
- Memory-efficient chunking for large datasets
- Checkpoint/resume functionality
- Progress tracking for long backtests
- Survivorship bias correction
- Corporate actions handling
- Dividend reinvestment (DRIP)
- Comprehensive performance metrics

Reference:
    AUDIT_PLAN_COMPLETO - FASE 5.1: Core Backtesting Engine

SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import pandas as pd

# SINGLE SOURCE OF TRUTH: Import CentralizedConfig
from app.shared.config.centralized_config import get_config

from ..point_in_time_database import PointInTimeDatabase
from .corporate_actions import CorporateActionHandler
from .dividend_handler import DividendHandler, DripConfig
from .look_ahead_validator import LookAheadValidator, ValidationResult
from .models import BacktestCheckpoint, CorporateAction, ProgressUpdate, StockSplit
from .performance_tracker import (
    PerformanceMetrics,
    PerformanceTracker,
    RollingMetrics,
    YearlyBreakdown,
)
from .pit_database import PITDatabaseClient
from .survivorship_adjuster import SurvivorshipAdjuster, SurvivorshipFreeResult

if TYPE_CHECKING:
    from app.domain.models.signal import Signal

logger = logging.getLogger(__name__)


def _get_backtesting_config():
    """Helper to get backtesting config from CentralizedConfig."""
    return get_config().backtesting


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal and datetime objects."""

    def default(self, obj):
        """Convert Decimal and datetime to JSON-serializable types."""
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class RobustBacktestConfig:
    """
    Configuration for the robust backtesting engine.

    Attributes:
        initial_capital: Starting capital for the backtest
        start_date: Backtest start date
        end_date: Backtest end date
        commission_per_trade: Commission per trade (fixed or percentage)
        slippage_bps: Slippage in basis points
        enable_survivorship_correction: Enable survivorship bias correction
        enable_dividend_reinvestment: Enable dividend reinvestment (DRIP)
        enable_checkpointing: Enable checkpoint/resume functionality
        checkpoint_dir: Directory to save checkpoints
        checkpoint_frequency: Checkpoint frequency (in days)
        chunk_size_days: Process data in chunks of this many days
        progress_callback: Optional callback for progress updates
        pit_data_path: Path to point-in-time database
        enable_look_ahead_validation: Enable automatic look-ahead bias validation
        validation_strict_mode: Whether validation failures block execution
    """

    initial_capital: Decimal = field(default=Decimal("100000"))
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    commission_per_trade: Decimal | None = field(default=None)  # Uses CentralizedConfig if None
    slippage_bps: Decimal | None = field(default=None)  # Uses CentralizedConfig if None
    risk_free_rate: Decimal | None = field(default=None)  # Uses CentralizedConfig if None

    # Feature flags
    enable_survivorship_correction: bool = field(default=True)
    enable_dividend_reinvestment: bool = field(default=False)
    enable_checkpointing: bool = field(default=True)

    # Checkpointing
    checkpoint_dir: Path | None = field(default=None)
    checkpoint_frequency: int = field(default=365)  # Checkpoint annually

    # Memory optimization
    chunk_size_days: int = field(default=365)  # Process 1 year at a time

    # Progress tracking
    progress_callback: Callable[[ProgressUpdate], None] | None = field(default=None)

    # DRIP config
    drip_config: DripConfig = field(default_factory=DripConfig)

    # Point-in-Time database configuration
    pit_data_path: Path | None = field(default=None)
    pit_cache_size_mb: int = field(default=100)

    # Look-ahead bias validation
    enable_look_ahead_validation: bool = field(default=True)
    validation_strict_mode: bool = field(default=True)

    def __post_init__(self):
        """
        Validate configuration and fill defaults from CentralizedConfig.

        SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.
        """
        # Fill defaults from CentralizedConfig
        config = _get_backtesting_config()
        if self.commission_per_trade is None:
            self.commission_per_trade = config.min_commission
        if self.slippage_bps is None:
            self.slippage_bps = config.base_slippage_bps
        if self.risk_free_rate is None:
            self.risk_free_rate = config.risk_free_rate

        # Validate configuration
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")

        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        # Set default checkpoint directory
        if self.checkpoint_dir is None:
            self.checkpoint_dir = Path("./checkpoints")


@dataclass
class RobustBacktestResult:
    """
    Result from a robust backtest run.

    Attributes:
        config: Backtest configuration used
        performance: Comprehensive performance metrics
        equity_curve: Full equity curve (date -> capital)
        trades: List of all trades executed
        yearly_breakdown: Year-by-year performance
        rolling_metrics: Rolling metrics over different windows
        survivorship_adjustment: Survivorship bias adjustment info
        dividend_tracker: Dividend tracking information
        checkpoints_used: Number of checkpoints loaded/resumed from
        total_duration_seconds: Total backtest execution time
    """

    config: RobustBacktestConfig = field(default_factory=RobustBacktestConfig)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    equity_curve: list[tuple[date, Decimal]] = field(default_factory=list)
    trades: list[dict[str, str | int | float | datetime]] = field(default_factory=list)
    yearly_breakdown: list[YearlyBreakdown] = field(default_factory=list)
    rolling_metrics: RollingMetrics | None = field(default=None)
    survivorship_adjustment: SurvivorshipFreeResult | None = field(default=None)
    dividend_tracker: DividendHandler | None = field(default=None)
    checkpoints_used: int = field(default=0)
    total_duration_seconds: float = field(default=0.0)


class RobustBacktester:
    """
    Robust backtesting engine for 25+ year backtests.

    This engine implements all requirements from AUDIT_PLAN_COMPLETO:
    - FASE 5.1: Core Backtesting Engine
    - Memory-efficient processing of large datasets
    - Checkpoint/resume functionality
    - Survivorship bias correction
    - Corporate actions handling
    - Dividend reinvestment

    Example:
        ```python
        config = RobustBacktestConfig(
            initial_capital=Decimal("100000"),
            start_date=date(1999, 1, 1),
            end_date=date(2024, 12, 31),
            enable_dividend_reinvestment=True
        )

        backtester = RobustBacktester(config)
        result = await backtester.run_backtest(
            strategy=strategy,
            market_data=data,
            signals=signals
        )
        ```
    """

    def __init__(
        self,
        config: RobustBacktestConfig,
    ):
        """
        Initialize the robust backtester.

        Args:
            config: Backtest configuration
        """
        self.config = config

        # Initialize components
        self.corporate_action_handler = CorporateActionHandler()
        self.dividend_handler = DividendHandler(
            drip_config=(
                config.drip_config
                if config.enable_dividend_reinvestment
                else DripConfig(enable_drip=False)
            )
        )
        self.survivorship_adjuster = SurvivorshipAdjuster()
        self.performance_tracker = PerformanceTracker(
            initial_capital=config.initial_capital,
            risk_free_rate=config.risk_free_rate,
        )

        # Initialize Point-in-Time database client
        self.pit_client: PITDatabaseClient | None = None
        if config.pit_data_path is not None:
            pit_db = PointInTimeDatabase(
                pit_data_path=config.pit_data_path,
                cache_size_mb=config.pit_cache_size_mb,
            )
            self.pit_client = PITDatabaseClient(
                pit_db=pit_db,
                cache_size_mb=config.pit_cache_size_mb,
                enable_caching=True,
            )
            logger.info(f"PIT database client initialized with path: {config.pit_data_path}")

        # Initialize look-ahead bias validator
        self.lookahead_validator = LookAheadValidator(
            pit_database=self.pit_client,
            strict_mode=config.validation_strict_mode,
        )

        # State
        self._capital: Decimal = config.initial_capital
        self._positions: dict[str, Decimal] = {}
        self._cost_basis: dict[str, Decimal] = {}  # Track cost basis per symbol for P&L calculation
        self._trades: list[dict[str, str | int | float | datetime]] = []
        self._current_date: date | None = config.start_date

        # Checkpointing
        self._latest_checkpoint: BacktestCheckpoint | None = None
        self._checkpoint_count: int = 0

        # Validation results
        self._validation_result: ValidationResult | None = None

        # Timing
        self._start_time: datetime | None = None

        # Ensure checkpoint directory exists
        if config.enable_checkpointing and config.checkpoint_dir:
            config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    async def run_backtest(
        self,
        strategy: object,
        market_data: pd.DataFrame | list[object],
        signals: list[Signal] | None = None,
        resume_from_checkpoint: bool = False,
    ) -> RobustBacktestResult:
        """
        Run a complete backtest over the configured period.

        Args:
            strategy: Trading strategy with generate_signals() method
            market_data: Historical market data (DataFrame or list)
            signals: Optional pre-generated signals
            resume_from_checkpoint: Whether to resume from last checkpoint

        Returns:
            RobustBacktestResult with comprehensive results
        """
        self._start_time = datetime.utcnow()

        # Try to resume from checkpoint if enabled
        if resume_from_checkpoint and self._load_latest_checkpoint():
            logger.info(f"Resuming from checkpoint: {self._current_date}")
        else:
            # Reset state for fresh run
            self._reset_state()

        # Convert market data to DataFrame if needed
        if not isinstance(market_data, pd.DataFrame):
            market_data = self._convert_to_dataframe(market_data)

        # Perform look-ahead bias validation if enabled
        await self._perform_validation_if_enabled(signals, market_data)

        # Apply survivorship correction if enabled
        if self.config.enable_survivorship_correction:
            logger.info("Applying survivorship bias correction...")
            market_data = self._apply_survivorship_correction(market_data)

        # Process in chunks for memory efficiency
        await self._process_backtest_chunks(
            strategy=strategy,
            market_data=market_data,
            signals=signals,
        )

        # Calculate final metrics
        performance = self.performance_tracker.calculate_metrics()

        # Build result
        result = self._build_backtest_result(performance)

        # Save final checkpoint
        if self.config.enable_checkpointing:
            self._save_checkpoint(is_final=True)

        self._log_completion_summary(performance)

        return result

    def _reset_state(self) -> None:
        """Reset backtester state for fresh run."""
        self._capital = self.config.initial_capital
        self._positions.clear()
        self._trades.clear()
        self._current_date = self.config.start_date

        self.performance_tracker = PerformanceTracker(
            initial_capital=self.config.initial_capital,
            risk_free_rate=self.config.risk_free_rate,
        )
        self.dividend_handler.reset()

    async def _perform_validation_if_enabled(
        self,
        signals: list[Signal] | None,
        market_data: pd.DataFrame,
    ) -> None:
        """
        Perform look-ahead bias validation if enabled.

        Args:
            signals: Optional pre-generated signals
            market_data: Market data DataFrame

        Raises:
            ValueError: Validation fails and strict_mode is enabled
        """
        if not self.config.enable_look_ahead_validation or signals is None:
            return

        logger.info("Performing look-ahead bias validation...")
        self._validation_result = self._validate_backtest_data(
            signals=signals,
            market_data=market_data,
        )

        if not self._validation_result.is_valid:
            error_msg = (
                f"Look-ahead bias validation failed. Issues: {self._validation_result.issues}"
            )
            logger.error(error_msg)
            if self.config.validation_strict_mode:
                raise ValueError(error_msg)

    def _build_backtest_result(
        self,
        performance: PerformanceMetrics,
    ) -> RobustBacktestResult:
        """
        Build RobustBacktestResult from performance metrics.

        Args:
            performance: Calculated performance metrics

        Returns:
            RobustBacktestResult with all results
        """
        return RobustBacktestResult(
            config=self.config,
            performance=performance,
            equity_curve=self.performance_tracker.equity_curve,
            trades=self._trades,
            yearly_breakdown=self.performance_tracker.get_yearly_breakdown(),
            rolling_metrics=self.performance_tracker.get_rolling_metrics(),
            dividend_tracker=self.dividend_handler,
            checkpoints_used=self._checkpoint_count,
            total_duration_seconds=(
                (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0.0
            ),
        )

    def _log_completion_summary(
        self,
        performance: PerformanceMetrics,
    ) -> None:
        """
        Log backtest completion summary.

        Args:
            performance: Calculated performance metrics
        """
        logger.info(
            f"Backtest completed: {performance.total_return:.2%} total return, "
            f"{performance.cagr:.2%} CAGR, {performance.sharpe_ratio:.2f} Sharpe"
        )

    async def _process_backtest_chunks(
        self,
        strategy: object,
        market_data: pd.DataFrame,
        signals: list[Signal] | None,
    ) -> None:
        """
        Process backtest in chunks for memory efficiency.

        Args:
            strategy: Trading strategy
            market_data: Market data DataFrame
            signals: Optional pre-generated signals
        """
        # Split data into chunks
        chunks = self._split_data_into_chunks(market_data)

        total_chunks = len(chunks)
        logger.info(f"Processing backtest in {total_chunks} chunks")

        for chunk_idx, chunk in enumerate(chunks, 1):
            await self._process_single_chunk(
                chunk_idx=chunk_idx,
                total_chunks=total_chunks,
                chunk=chunk,
                strategy=strategy,
                signals=signals,
            )

    async def _process_single_chunk(
        self,
        chunk_idx: int,
        total_chunks: int,
        chunk: pd.DataFrame,
        strategy: object,
        signals: list[Signal] | None,
    ) -> None:
        """
        Process a single chunk with progress tracking and checkpointing.

        Args:
            chunk_idx: Current chunk index (1-based)
            total_chunks: Total number of chunks
            chunk: Data chunk to process
            strategy: Trading strategy
            signals: Optional pre-generated signals
        """
        chunk_start = datetime.utcnow()

        logger.info(
            f"Processing chunk {chunk_idx}/{total_chunks}: "
            f"{chunk.index[0].date()} to {chunk.index[-1].date()}"
        )

        # Process this chunk
        await self._process_chunk(
            strategy=strategy,
            chunk=chunk,
            signals=signals,
        )

        # Update progress
        self._update_progress(
            chunk_idx=chunk_idx,
            total_chunks=total_chunks,
            chunk_end_date=chunk.index[-1].date(),
        )

        # Save checkpoint if needed
        await self._save_checkpoint_if_needed(chunk_idx, total_chunks)

        chunk_duration = (datetime.utcnow() - chunk_start).total_seconds()
        logger.info(f"Chunk {chunk_idx}/{total_chunks} completed in {chunk_duration:.1f}s")

    async def _save_checkpoint_if_needed(
        self,
        chunk_idx: int,
        total_chunks: int,
    ) -> None:
        """
        Save checkpoint if conditions are met.

        Args:
            chunk_idx: Current chunk index (1-based)
            total_chunks: Total number of chunks
        """
        if not self.config.enable_checkpointing:
            return

        # Calculate days completed to determine if checkpoint is needed
        days_completed = chunk_idx * self.config.chunk_size_days
        should_checkpoint = (
            days_completed % self.config.checkpoint_frequency == 0 or chunk_idx == total_chunks
        )

        if should_checkpoint:
            self._save_checkpoint()

    async def _process_chunk(
        self,
        strategy: object,
        chunk: pd.DataFrame,
        signals: list[Signal] | None,
    ) -> None:
        """
        Process a single chunk of data.

        Args:
            strategy: Trading strategy
            chunk: Data chunk to process
            signals: Optional signals for this period
        """
        # Use itertuples instead of iterrows for better performance
        for row in chunk.itertuples():
            idx = row.Index
            current_date = idx.date() if hasattr(idx, "date") else idx
            self._current_date = current_date

            # Check for corporate actions
            self._process_corporate_actions(current_date)

            # Process signals for this date
            await self._process_signals_for_date(
                strategy=strategy,
                chunk=chunk,
                idx=idx,
                row=row,
                signals=signals,
                current_date=current_date,
            )

            # Update tracker
            self.performance_tracker.update(current_date, self._capital)

    async def _process_signals_for_date(
        self,
        strategy: object,
        chunk: pd.DataFrame,
        idx: pd.Timestamp | int,
        row: tuple,
        signals: list[Signal] | None,
        current_date: date,
    ) -> None:
        """
        Process all signals for a specific date.

        Args:
            strategy: Trading strategy
            chunk: Data chunk
            idx: Current row index
            row: Current row data
            signals: Optional pre-generated signals
            current_date: Current date being processed
        """
        if signals is not None:
            # Use pre-generated signals
            chunk_signals = [s for s in signals if s.timestamp.date() == current_date]
            for signal in chunk_signals:
                await self._process_signal(signal, row)
        elif hasattr(strategy, "generate_signals"):
            # Generate signals from strategy
            chunk_signals = strategy.generate_signals(chunk.loc[:idx])
            for signal in chunk_signals:
                await self._process_signal(signal, row)

    async def _process_signal(
        self,
        signal: Signal,
        market_data: pd.Series,
    ) -> None:
        """
        Process a trading signal.

        Args:
            signal: Trading signal
            market_data: Market data at signal time
        """
        # Extract signal attributes
        try:
            signal_type = (
                signal.signal_type.value.lower()
                if hasattr(signal.signal_type, "value")
                else str(signal.signal_type).lower()
            )
            symbol = signal.symbol
            # Use Decimal for price to maintain precision
            price_input = (
                signal.price if hasattr(signal, "price") else market_data.get("close", Decimal("0"))
            )
            price = (
                Decimal(str(price_input)) if not isinstance(price_input, Decimal) else price_input
            )
        except (AttributeError, KeyError, ValueError) as e:
            logger.warning(f"Could not process signal: {e}")
            return

        if signal_type == "buy":
            self._execute_buy(symbol, price, signal)
        elif signal_type == "sell":
            self._execute_sell(symbol, price, signal)

    def _execute_buy(
        self,
        symbol: str,
        price: Decimal,
        signal: Signal,
    ) -> None:
        """Execute a buy order."""
        # Ensure we have a current date
        if self._current_date is None:
            self._current_date = self.config.start_date

        # Calculate position size (simplified)
        position_value = self._capital * Decimal("0.1")  # 10% of capital
        shares = int(position_value / price)

        if shares <= 0:
            return

        # Calculate commission - use Decimal for precision
        commission = self.config.commission_per_trade

        # Execute trade - all Decimal arithmetic
        total_cost = Decimal(str(shares)) * price + commission
        if total_cost > self._capital:
            shares = int((self._capital - commission) / price)

        if shares <= 0:
            return

        actual_cost = Decimal(str(shares)) * price + commission
        self._capital -= actual_cost
        self._positions[symbol] = self._positions.get(symbol, Decimal("0")) + Decimal(str(shares))

        # Track cost basis for P&L calculation (use average cost basis)
        current_cost_basis = self._cost_basis.get(symbol, Decimal("0"))
        current_shares = self._positions.get(symbol, Decimal("0")) - Decimal(str(shares))
        new_shares = Decimal(str(shares))
        total_cost = current_cost_basis * current_shares + Decimal(str(shares)) * price
        self._cost_basis[symbol] = (
            total_cost / (current_shares + new_shares)
            if (current_shares + new_shares) > 0
            else price
        )

        # Record trade
        self._trades.append(
            {
                "symbol": symbol,
                "side": "buy",
                "shares": shares,
                "price": float(price),  # Convert to float for JSON serialization
                "commission": float(commission),
                "date": self._current_date,
                "timestamp": datetime.combine(self._current_date, datetime.min.time()),
            }
        )

    def _execute_sell(
        self,
        symbol: str,
        price: Decimal,
        signal: Signal,
    ) -> None:
        """Execute a sell order."""
        # Ensure we have a current date
        if self._current_date is None:
            self._current_date = self.config.start_date

        current_shares = self._positions.get(symbol, Decimal("0"))

        if current_shares <= 0:
            return

        # Use Decimal to preserve fractional shares
        shares_to_sell = current_shares
        commission = self.config.commission_per_trade

        # Calculate proceeds using Decimal arithmetic
        proceeds = shares_to_sell * price - commission
        self._capital += proceeds
        self._positions[symbol] = Decimal("0")  # Clear entire position including fractional shares

        # Calculate P&L using stored cost basis (Decimal arithmetic)
        cost_basis = self._cost_basis.get(symbol, price)
        pnl = proceeds - shares_to_sell * cost_basis
        # Clear cost basis for this symbol
        self._cost_basis[symbol] = Decimal("0")

        # Update trade
        self._trades.append(
            {
                "symbol": symbol,
                "side": "sell",
                "shares": float(shares_to_sell),
                "price": float(price),
                "commission": float(commission),
                "pnl": float(pnl),
                "date": self._current_date,
                "timestamp": datetime.combine(self._current_date, datetime.min.time()),
            }
        )

    def _process_corporate_actions(
        self,
        current_date: date,
    ) -> None:
        """
        Process corporate actions for current date.

        Args:
            current_date: Current simulation date
        """
        # Check for splits, mergers, spin-offs
        # This would interact with CorporateActionHandler

    def _split_data_into_chunks(
        self,
        data: pd.DataFrame,
    ) -> list[pd.DataFrame]:
        """
        Split data into memory-efficient chunks.

        Args:
            data: Full market data DataFrame

        Returns:
            List of data chunks
        """
        chunk_size_days = self.config.chunk_size_days
        chunks = []

        # Get unique dates
        if isinstance(data.index, pd.DatetimeIndex):
            dates = data.index.normalize().unique()
        else:
            dates = data.index.unique()

        for i in range(0, len(dates), chunk_size_days):
            chunk_dates = dates[i : i + chunk_size_days]
            chunk = data.loc[data.index.isin(chunk_dates)]
            chunks.append(chunk)

        return chunks

    def _convert_to_dataframe(
        self,
        data: list[object],
    ) -> pd.DataFrame:
        """
        Convert list of market data objects to DataFrame.

        Args:
            data: List of market data objects

        Returns:
            DataFrame with OHLCV data
        """
        records = []
        for item in data:
            if hasattr(item, "timestamp") and hasattr(item, "close"):
                records.append(
                    {
                        "timestamp": item.timestamp,
                        "open": float(getattr(item, "open", item.close)),
                        "high": float(getattr(item, "high", item.close)),
                        "low": float(getattr(item, "low", item.close)),
                        "close": float(item.close),
                        "volume": float(getattr(item, "volume", 0)),
                        "symbol": getattr(item, "symbol", "UNKNOWN"),
                    }
                )

        df = pd.DataFrame(records)
        if not df.empty and "timestamp" in df.columns:
            df.set_index("timestamp", inplace=True)

        return df

    def _apply_survivorship_correction(
        self,
        market_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Apply survivorship bias correction to market data.

        Args:
            market_data: Original market data

        Returns:
            Adjusted market data
        """
        # This would integrate with SurvivorshipAdjuster
        # For now, return original data
        return market_data

    def _update_progress(
        self,
        chunk_idx: int,
        total_chunks: int,
        chunk_end_date: date,
    ) -> None:
        """
        Send progress update if callback is configured.

        Args:
            chunk_idx: Current chunk index
            total_chunks: Total number of chunks
            chunk_end_date: End date of current chunk
        """
        if self.config.progress_callback is None:
            return

        # Estimate years completed
        years_completed = chunk_idx * self.config.chunk_size_days / 365.25
        total_years = (self.config.end_date - self.config.start_date).days / 365.25

        update = ProgressUpdate(
            current_year=int(years_completed) + 1,
            total_years=int(total_years) + 1,
            current_date=chunk_end_date,
            total_days=(self.config.end_date - self.config.start_date).days,
            capital=self._capital,
            return_pct=(
                (self._capital - self.config.initial_capital) / self.config.initial_capital * 100
                if self._capital > 0
                else Decimal("0")
            ),
            trades_executed=len(self._trades),
        )

        self.config.progress_callback(update)

    def _save_checkpoint(self, is_final: bool = False) -> None:
        """
        Save current state to checkpoint file.

        Args:
            is_final: Whether this is the final checkpoint
        """
        if not self.config.enable_checkpointing or self.config.checkpoint_dir is None:
            return

        checkpoint = BacktestCheckpoint(
            timestamp=datetime.utcnow(),
            current_date=self._current_date or self.config.start_date,
            capital=self._capital,
            positions=dict(self._positions),
            cost_basis=dict(self._cost_basis),
            year=(
                (self._current_date.year - self.config.start_date.year) + 1
                if self._current_date
                else 1
            ),
            progress=(
                (self._current_date - self.config.start_date).days
                / (self.config.end_date - self.config.start_date).days
                * 100
                if self._current_date
                else 0.0
            ),
            metrics_snapshot={},
        )

        checkpoint_path = self.config.checkpoint_dir / (
            "checkpoint_final.json"
            if is_final
            else f"checkpoint_{checkpoint.current_date.strftime('%Y%m%d')}.json"
        )

        # Use DecimalEncoder for JSON serialization
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint.to_dict(), f, cls=DecimalEncoder, indent=2)

        self._latest_checkpoint = checkpoint
        self._checkpoint_count += 1

        logger.info(f"Saved checkpoint: {checkpoint_path}")

    def _load_latest_checkpoint(self) -> bool:
        """
        Load the most recent checkpoint.

        Returns:
            True if checkpoint was loaded successfully
        """
        if self.config.checkpoint_dir is None:
            return False

        checkpoint_files = list(self.config.checkpoint_dir.glob("checkpoint_*.json"))

        if not checkpoint_files:
            return False

        # Get most recent checkpoint
        latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

        try:
            with open(latest_file) as f:
                data = json.load(f)

            checkpoint = BacktestCheckpoint.from_dict(data)

            # Restore state
            self._current_date = checkpoint.current_date
            self._capital = checkpoint.capital
            self._positions = checkpoint.positions
            self._cost_basis = checkpoint.cost_basis

            self._latest_checkpoint = checkpoint
            self._checkpoint_count += 1

            logger.info(f"Loaded checkpoint from {checkpoint.current_date}")
            return True

        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return False

    def add_corporate_action(self, action: CorporateAction) -> None:
        """
        Add a corporate action to the handler.

        Args:
            action: CorporateAction object
        """
        if isinstance(action, StockSplit):
            self.corporate_action_handler.add_split(
                symbol=action.symbol,
                split_ratio=action.split_ratio,
                ex_date=action.ex_date,
            )
        # Add other action types as needed

    def load_corporate_actions_from_csv(self, filepath: str) -> int:
        """
        Load corporate actions from CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            Number of actions loaded
        """
        return self.corporate_action_handler.load_actions_from_csv(filepath)

    def load_delisted_database(self, filepath: str) -> int:
        """
        Load delisted stocks database.

        Args:
            filepath: Path to CSV file

        Returns:
            Number of delisted stocks loaded
        """
        return self.survivorship_adjuster.load_delisted_database(Path(filepath))

    def _validate_backtest_data(
        self,
        signals: list[Signal] | pd.DataFrame,
        market_data: pd.DataFrame,
    ) -> ValidationResult:
        """
        Validate backtest data for look-ahead bias.

        Args:
            signals: Trading signals (list or DataFrame)
            market_data: Market data DataFrame

        Returns:
            ValidationResult with validation details
        """
        # Convert signals to DataFrame if needed
        if not isinstance(signals, pd.DataFrame):
            signals_df = self._convert_signals_to_dataframe(signals)
        else:
            signals_df = signals.copy()

        # Run validation
        result = self.lookahead_validator.validate_backtest(
            signals=signals_df,
            market_data=market_data,
            strategy_params=None,
        )

        # Log validation report
        report = self.lookahead_validator.get_validation_report(result)
        logger.info(f"\n{report}")

        return result

    def _convert_signals_to_dataframe(
        self,
        signals: list[Signal],
    ) -> pd.DataFrame:
        """
        Convert list of signal objects to DataFrame.

        Args:
            signals: List of signal objects

        Returns:
            DataFrame with signals indexed by timestamp
        """
        records = []
        for signal in signals:
            try:
                record = {
                    "timestamp": signal.timestamp,
                    "symbol": signal.symbol,
                    "signal_type": (
                        signal.signal_type.value
                        if hasattr(signal.signal_type, "value")
                        else str(signal.signal_type)
                    ),
                }

                # Add optional fields
                if hasattr(signal, "price") and signal.price is not None:
                    record["price"] = float(signal.price)
                if hasattr(signal, "quantity") and signal.quantity is not None:
                    record["quantity"] = float(signal.quantity)

                records.append(record)
            except (AttributeError, TypeError) as e:
                logger.warning(f"Could not convert signal to DataFrame record: {e}")

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        if "timestamp" in df.columns:
            df.set_index("timestamp", inplace=True)

        return df

    def get_validation_result(self) -> ValidationResult | None:
        """
        Get the validation result from the last backtest.

        Returns:
            ValidationResult if validation was performed, None otherwise
        """
        return self._validation_result

    def get_pit_cache_statistics(self) -> dict[str, bool | str | int | float]:
        """
        Get PIT database cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if self.pit_client is None:
            return {
                "pit_enabled": False,
                "message": "PIT database client not initialized",
            }

        return {
            "pit_enabled": True,
            **self.pit_client.get_cache_statistics(),
        }


# Type alias for checkpoint data
CheckpointData = BacktestCheckpoint
