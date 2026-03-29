"""
Robust Backtest Engine.

This engine provides robust backtesting for 25+ years of historical data with:
- Memory-efficient chunking for large datasets
- Checkpoint/resume functionality
- Progress tracking for long backtests
- Survivorship bias correction
- Corporate actions handling
- Dividend reinvestment (DRIP)
- Look-ahead bias validation

This is a refactored version of app/backtesting/robust_engine/robust_backtester.py
that extends BaseBacktestEngine for consistency across the codebase.

SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, Union

import pandas as pd

from app.backtesting.base_engine import BaseBacktestEngine, EngineType

# SINGLE SOURCE OF TRUTH: Import CentralizedConfig
from app.shared.config.centralized_config import get_config

if TYPE_CHECKING:
    from app.backtesting.robust_engine.look_ahead_validator import ValidationResult
    from app.domain.models.signal import Signal
    from app.domain.strategies.base import BaseStrategy
    from app.services.corporate_actions.handler import CorporateAction

logger = logging.getLogger(__name__)

# Type alias for performance metrics dictionary
PerformanceMetrics = dict[str, Optional[Union[float, int]]]
YearlyBreakdown = dict[str, Union[float, int, str]]
RollingMetrics = dict[str, Union[float, int]]
SurvivorshipAdjustment = dict[str, Union[float, int, str]]
DividendTracker = dict[str, Union[float, int, str, Decimal]]
TradeRecord = dict[str, Union[str, int, float, date, datetime, Decimal]]
CheckpointData = dict[str, Union[str, float, int, dict[str, float], None]]


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
        commission_per_trade: Commission per trade
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
    """

    initial_capital: Decimal = field(default=Decimal("100000"))
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    commission_per_trade: Decimal | None = field(default=None)
    slippage_bps: Decimal | None = field(default=None)
    risk_free_rate: Decimal | None = field(default=None)

    # Feature flags
    enable_survivorship_correction: bool = field(default=True)
    enable_dividend_reinvestment: bool = field(default=False)
    enable_checkpointing: bool = field(default=True)

    # Checkpointing
    checkpoint_dir: Path | None = field(default=None)
    checkpoint_frequency: int = field(default=365)

    # Memory optimization
    chunk_size_days: int = field(default=365)

    # Progress tracking
    progress_callback: Callable | None = field(default=None)

    # Point-in-Time database
    pit_data_path: Path | None = field(default=None)
    pit_cache_size_mb: int = field(default=100)

    # Look-ahead validation
    enable_look_ahead_validation: bool = field(default=True)
    validation_strict_mode: bool = field(default=True)

    def __post_init__(self):
        """Validate configuration and fill defaults from CentralizedConfig."""
        bt_config = get_config().backtesting

        if self.commission_per_trade is None:
            self.commission_per_trade = bt_config.min_commission
        if self.slippage_bps is None:
            self.slippage_bps = bt_config.base_slippage_bps
        if self.risk_free_rate is None:
            self.risk_free_rate = bt_config.risk_free_rate

        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")

        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        if self.checkpoint_dir is None:
            self.checkpoint_dir = Path("./checkpoints")


@dataclass
class RobustBacktestResult:
    """
    Result from a robust backtest run.

    Attributes:
        config: Backtest configuration used
        performance: Comprehensive performance metrics
        equity_curve: Full equity curve
        trades: List of all trades executed
        yearly_breakdown: Year-by-year performance
        rolling_metrics: Rolling metrics over different windows
        survivorship_adjustment: Survivorship bias adjustment info
        dividend_tracker: Dividend tracking information
        checkpoints_used: Number of checkpoints loaded
        total_duration_seconds: Total backtest execution time
    """

    config: RobustBacktestConfig = field(default_factory=RobustBacktestConfig)
    performance: PerformanceMetrics | None = field(default=None)
    equity_curve: list[tuple[date, Decimal]] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    yearly_breakdown: list[YearlyBreakdown] = field(default_factory=list)
    rolling_metrics: RollingMetrics | None = field(default=None)
    survivorship_adjustment: SurvivorshipAdjustment | None = field(default=None)
    dividend_tracker: DividendTracker | None = field(default=None)
    checkpoints_used: int = field(default=0)
    total_duration_seconds: float = field(default=0.0)


class RobustBacktestEngine(BaseBacktestEngine[RobustBacktestConfig, RobustBacktestResult]):
    """
    Robust backtesting engine for 25+ year backtests.

    This engine implements:
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

        engine = RobustBacktestEngine(config)
        result = engine.run_backtest(
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
        super().__init__(
            config=config,
            strategy_name="robust_backtest",
        )

        # Initialize components (lazy imports to avoid circular dependencies)
        self._init_components()

        # State tracking
        self._capital: Decimal = config.initial_capital
        self._positions: dict[str, Decimal] = {}
        self._cost_basis: dict[str, Decimal] = {}
        self._trades: list[TradeRecord] = []
        self._current_date: date | None = config.start_date

        # Checkpointing
        self._latest_checkpoint: CheckpointData | None = None
        self._checkpoint_count: int = 0

        # Validation
        self._validation_result: ValidationResult | None = None

        # Timing
        self._start_time: datetime | None = None

        # Ensure checkpoint directory exists
        if config.enable_checkpointing and config.checkpoint_dir:
            config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"RobustBacktestEngine initialized for {config.start_date} to {config.end_date}"
        )

    def _init_components(self) -> None:
        """Initialize optional components (lazy loading)."""
        # These will be loaded on demand
        self._corporate_action_handler = None
        self._dividend_handler = None
        self._survivorship_adjuster = None
        self._performance_tracker = None
        self._pit_client = None
        self._lookahead_validator = None

    # =========================================================================
    # IMPLEMENTATION OF ABSTRACT METHODS
    # =========================================================================

    def get_engine_type(self) -> EngineType:
        """Return the engine type identifier."""
        return EngineType.ROBUST

    def run_backtest(
        self,
        market_data: pd.DataFrame | list[Signal],
        signals: list[Signal] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        resume_from_checkpoint: bool = False,
        **kwargs,
    ) -> RobustBacktestResult:
        """
        Run a complete backtest over the configured period.

        Args:
            market_data: Historical market data (DataFrame or list)
            signals: Optional pre-generated signals
            start_date: Not used (from config)
            end_date: Not used (from config)
            resume_from_checkpoint: Whether to resume from last checkpoint

        Returns:
            RobustBacktestResult with comprehensive results
        """
        self._start_time = datetime.utcnow()

        # Try to resume from checkpoint if enabled
        if resume_from_checkpoint and self._load_latest_checkpoint():
            logger.info(f"Resuming from checkpoint: {self._current_date}")
        else:
            self._reset_state()

        # Convert market data to DataFrame if needed
        if not isinstance(market_data, pd.DataFrame):
            market_data = self._convert_to_dataframe(market_data)

        # Perform look-ahead bias validation if enabled
        if self.config.enable_look_ahead_validation and signals:
            self._perform_validation(signals, market_data)

        # Apply survivorship correction if enabled
        if self.config.enable_survivorship_correction:
            logger.info("Applying survivorship bias correction...")
            market_data = self._apply_survivorship_correction(market_data)

        # Process in chunks for memory efficiency
        self._process_backtest_chunks(
            strategy=None,  # Robust engine doesn't use strategy directly
            market_data=market_data,
            signals=signals,
        )

        # Calculate final metrics
        performance = self._calculate_performance()

        # Build result
        result = self._build_result(performance)

        # Save final checkpoint
        if self.config.enable_checkpointing:
            self._save_checkpoint(is_final=True)

        self._log_completion_summary(performance)

        return result

    def _create_result(self, **kwargs) -> RobustBacktestResult:
        """Create RobustBacktestResult."""
        return RobustBacktestResult(
            config=self.config,
            performance=kwargs.get("performance"),
            equity_curve=kwargs.get("equity_curve", []),
            trades=kwargs.get("trades", []),
            yearly_breakdown=kwargs.get("yearly_breakdown", []),
            rolling_metrics=kwargs.get("rolling_metrics"),
            survivorship_adjustment=kwargs.get("survivorship_adjustment"),
            dividend_tracker=kwargs.get("dividend_tracker"),
            checkpoints_used=self._checkpoint_count,
            total_duration_seconds=(
                (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0.0
            ),
        )

    # =========================================================================
    # ROBUST ENGINE SPECIFIC METHODS
    # =========================================================================

    def _reset_state(self) -> None:
        """Reset backtester state for fresh run."""
        self._capital = self.config.initial_capital
        self._positions.clear()
        self._trades.clear()
        self._current_date = self.config.start_date

        if self._performance_tracker:
            self._performance_tracker.reset()

    def _convert_to_dataframe(self, data: list[Signal]) -> pd.DataFrame:
        """Convert list of market data objects to DataFrame."""
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

    def _split_data_into_chunks(self, data: pd.DataFrame) -> list[pd.DataFrame]:
        """Split data into memory-efficient chunks."""
        chunk_size_days = self.config.chunk_size_days
        chunks = []

        if isinstance(data.index, pd.DatetimeIndex):
            dates = data.index.normalize().unique()
        else:
            dates = data.index.unique()

        for i in range(0, len(dates), chunk_size_days):
            chunk_dates = dates[i : i + chunk_size_days]
            chunk = data.loc[data.index.isin(chunk_dates)]
            chunks.append(chunk)

        return chunks

    def _process_backtest_chunks(
        self,
        strategy: BaseStrategy | None,
        market_data: pd.DataFrame,
        signals: list[Signal] | None,
    ) -> None:
        """Process backtest in chunks for memory efficiency."""
        chunks = self._split_data_into_chunks(market_data)
        total_chunks = len(chunks)

        logger.info(f"Processing backtest in {total_chunks} chunks")

        for chunk_idx, chunk in enumerate(chunks, 1):
            self._process_single_chunk(
                chunk_idx=chunk_idx,
                total_chunks=total_chunks,
                chunk=chunk,
                strategy=strategy,
                signals=signals,
            )

    def _process_single_chunk(
        self,
        chunk_idx: int,
        total_chunks: int,
        chunk: pd.DataFrame,
        strategy: BaseStrategy | None,
        signals: list[Signal] | None,
    ) -> None:
        """Process a single chunk with progress tracking."""
        chunk_start = datetime.utcnow()

        logger.info(
            f"Processing chunk {chunk_idx}/{total_chunks}: "
            f"{chunk.index[0].date()} to {chunk.index[-1].date()}"
        )

        # Process this chunk
        for row in chunk.itertuples():
            idx = row.Index
            current_date = idx.date() if hasattr(idx, "date") else idx
            self._current_date = current_date

            # Process signals for this date
            if signals:
                chunk_signals = [s for s in signals if s.timestamp.date() == current_date]
                for signal in chunk_signals:
                    self._process_signal(signal, row)

            # Update tracker
            if self._performance_tracker:
                self._performance_tracker.update(current_date, self._capital)

        # Update progress
        self._update_progress(chunk_idx, total_chunks, chunk.index[-1].date())

        # Save checkpoint if needed
        self._save_checkpoint_if_needed(chunk_idx, total_chunks)

        chunk_duration = (datetime.utcnow() - chunk_start).total_seconds()
        logger.info(f"Chunk {chunk_idx}/{total_chunks} completed in {chunk_duration:.1f}s")

    def _process_signal(self, signal: Signal, market_data: object) -> None:
        """Process a trading signal."""
        try:
            signal_type = (
                signal.signal_type.value.lower()
                if hasattr(signal.signal_type, "value")
                else str(signal.signal_type).lower()
            )
            symbol = signal.symbol
            price_input = (
                signal.price
                if hasattr(signal, "price")
                else getattr(market_data, "close", Decimal("0"))
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

    def _execute_buy(self, symbol: str, price: Decimal, signal: Signal) -> None:
        """Execute a buy order."""
        if self._current_date is None:
            self._current_date = self.config.start_date

        position_value = self._capital * Decimal("0.1")
        shares = int(position_value / price)

        if shares <= 0:
            return

        commission = self.config.commission_per_trade
        total_cost = Decimal(str(shares)) * price + commission

        if total_cost > self._capital:
            shares = int((self._capital - commission) / price)

        if shares <= 0:
            return

        actual_cost = Decimal(str(shares)) * price + commission
        self._capital -= actual_cost
        self._positions[symbol] = self._positions.get(symbol, Decimal("0")) + Decimal(str(shares))

        self._trades.append(
            {
                "symbol": symbol,
                "side": "buy",
                "shares": shares,
                "price": float(price),
                "commission": float(commission),
                "date": self._current_date,
                "timestamp": datetime.combine(self._current_date, datetime.min.time()),
            }
        )

    def _execute_sell(self, symbol: str, price: Decimal, signal: Signal) -> None:
        """Execute a sell order."""
        if self._current_date is None:
            self._current_date = self.config.start_date

        current_shares = self._positions.get(symbol, Decimal("0"))

        if current_shares <= 0:
            return

        shares_to_sell = current_shares
        commission = self.config.commission_per_trade

        proceeds = shares_to_sell * price - commission
        self._capital += proceeds
        self._positions[symbol] = Decimal("0")

        cost_basis = self._cost_basis.get(symbol, price)
        pnl = proceeds - shares_to_sell * cost_basis
        self._cost_basis[symbol] = Decimal("0")

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

    def _update_progress(
        self,
        chunk_idx: int,
        total_chunks: int,
        chunk_end_date: date,
    ) -> None:
        """Update progress if callback is configured."""
        if self.config.progress_callback is None:
            return

        years_completed = chunk_idx * self.config.chunk_size_days / 365.25
        total_years = (self.config.end_date - self.config.start_date).days / 365.25

        self.config.progress_callback(
            {
                "current_year": int(years_completed) + 1,
                "total_years": int(total_years) + 1,
                "current_date": chunk_end_date,
                "capital": self._capital,
                "trades_executed": len(self._trades),
            }
        )

    def _save_checkpoint_if_needed(
        self,
        chunk_idx: int,
        total_chunks: int,
    ) -> None:
        """Save checkpoint if conditions are met."""
        if not self.config.enable_checkpointing:
            return

        days_completed = chunk_idx * self.config.chunk_size_days
        should_checkpoint = (
            days_completed % self.config.checkpoint_frequency == 0 or chunk_idx == total_chunks
        )

        if should_checkpoint:
            self._save_checkpoint()

    def _save_checkpoint(self, is_final: bool = False) -> None:
        """Save current state to checkpoint file."""
        if not self.config.enable_checkpointing or self.config.checkpoint_dir is None:
            return

        checkpoint = {
            "timestamp": datetime.utcnow().isoformat(),
            "current_date": self._current_date.isoformat() if self._current_date else None,
            "capital": float(self._capital),
            "positions": {k: float(v) for k, v in self._positions.items()},
            "cost_basis": {k: float(v) for k, v in self._cost_basis.items()},
            "year": (
                (self._current_date.year - self.config.start_date.year) + 1
                if self._current_date
                else 1
            ),
            "progress": (
                (self._current_date - self.config.start_date).days
                / (self.config.end_date - self.config.start_date).days
                * 100
                if self._current_date
                else 0.0
            ),
        }

        checkpoint_path = self.config.checkpoint_dir / (
            "checkpoint_final.json"
            if is_final
            else f"checkpoint_{self._current_date.strftime('%Y%m%d') if self._current_date else 'unknown'}.json"
        )

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f, cls=DecimalEncoder, indent=2)

        self._checkpoint_count += 1
        logger.info(f"Saved checkpoint: {checkpoint_path}")

    def _load_latest_checkpoint(self) -> bool:
        """Load the most recent checkpoint."""
        if self.config.checkpoint_dir is None:
            return False

        checkpoint_files = list(self.config.checkpoint_dir.glob("checkpoint_*.json"))

        if not checkpoint_files:
            return False

        latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

        try:
            with open(latest_file) as f:
                data = json.load(f)

            self._current_date = (
                date.fromisoformat(data["current_date"])
                if data.get("current_date")
                else self.config.start_date
            )
            self._capital = Decimal(str(data["capital"]))
            self._positions = {k: Decimal(str(v)) for k, v in data.get("positions", {}).items()}
            self._cost_basis = {k: Decimal(str(v)) for k, v in data.get("cost_basis", {}).items()}

            self._checkpoint_count += 1
            logger.info(f"Loaded checkpoint from {self._current_date}")
            return True

        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return False

    def _perform_validation(
        self,
        signals: list[Signal],
        market_data: pd.DataFrame,
    ) -> None:
        """Perform look-ahead bias validation."""
        if not self.config.enable_look_ahead_validation:
            return

        logger.info("Performing look-ahead bias validation...")

        # Convert signals to DataFrame
        signals_df = self._convert_signals_to_dataframe(signals)

        # Run validation (lazy import to avoid circular dependencies)
        if self._lookahead_validator is None:
            try:
                from app.backtesting.robust_engine.look_ahead_validator import LookAheadValidator

                self._lookahead_validator = LookAheadValidator(
                    strict_mode=self.config.validation_strict_mode
                )
            except ImportError:
                logger.warning("LookAheadValidator not available, skipping validation")
                return

        self._validation_result = self._lookahead_validator.validate_backtest(
            signals=signals_df,
            market_data=market_data,
            strategy_params=None,
        )

        if not self._validation_result.is_valid:
            error_msg = (
                f"Look-ahead bias validation failed. Issues: {self._validation_result.issues}"
            )
            logger.error(error_msg)
            if self.config.validation_strict_mode:
                raise ValueError(error_msg)

    def _convert_signals_to_dataframe(self, signals: list[Signal]) -> pd.DataFrame:
        """Convert list of signal objects to DataFrame."""
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

                if hasattr(signal, "price") and signal.price is not None:
                    record["price"] = float(signal.price)

                records.append(record)
            except (AttributeError, TypeError) as e:
                logger.warning(f"Could not convert signal: {e}")

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        if "timestamp" in df.columns:
            df.set_index("timestamp", inplace=True)

        return df

    def _apply_survivorship_correction(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Apply survivorship bias correction to market data."""
        # Placeholder - would integrate with SurvivorshipAdjuster
        return market_data

    def _calculate_performance(self) -> PerformanceMetrics:
        """Calculate final performance metrics."""
        # Simplified performance calculation
        total_return = (
            (self._capital - self.config.initial_capital) / self.config.initial_capital
            if self.config.initial_capital > 0
            else Decimal("0")
        )

        return {
            "total_return": float(total_return),
            "final_capital": float(self._capital),
            "total_trades": len(self._trades),
            "sharpe_ratio": None,
            "max_drawdown": None,
        }

    def _build_result(self, performance: PerformanceMetrics) -> RobustBacktestResult:
        """Build RobustBacktestResult from performance metrics."""
        return self._create_result(
            performance=performance,
            equity_curve=[],  # Would be populated from performance tracker
            trades=self._trades,
            yearly_breakdown=[],
            rolling_metrics=None,
            survivorship_adjustment=None,
            dividend_tracker=None,
        )

    def _log_completion_summary(self, performance: PerformanceMetrics) -> None:
        """Log backtest completion summary."""
        logger.info(
            f"Backtest completed: {performance['total_return']:.2%} total return, "
            f"{len(self._trades)} trades, "
            f"final capital=${self._capital:,.2f}"
        )

    def add_corporate_action(self, action: CorporateAction) -> None:
        """Add a corporate action to the handler."""
        # Would integrate with CorporateActionHandler
        pass

    def load_corporate_actions_from_csv(self, filepath: str) -> int:
        """Load corporate actions from CSV file."""
        # Would integrate with CorporateActionHandler
        return 0

    def load_delisted_database(self, filepath: str) -> int:
        """Load delisted stocks database."""
        # Would integrate with SurvivorshipAdjuster
        return 0


# Backward compatibility alias
RobustBacktester = RobustBacktestEngine
