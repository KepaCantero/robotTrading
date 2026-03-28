"""
Abstract Base Backtest Engine.

This module defines the abstract base class for all backtest engines,
providing a unified interface and shared functionality to reduce code
duplication across the 4 existing engines:
- engine.py (BacktestEngine)
- execution_engine.py (PessimisticExecutionEngine)
- multi_strategy_engine.py (MultiStrategyBacktester)
- robust_engine/robust_backtester.py (RobustBacktester)

SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union

from pydantic import BaseModel

from app.backtesting.models import Trade

# SINGLE SOURCE OF TRUTH: Import CentralizedConfig
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


def _get_backtesting_config():
    """Helper to get backtesting config from CentralizedConfig."""
    return get_config().backtesting


# ============================================================================
# GENERIC TYPES
# ============================================================================

ConfigType = TypeVar("ConfigType", bound=BaseModel)
ResultType = TypeVar("ResultType", bound=BaseModel)


# ============================================================================
# SHARED ENUMS AND DATACLASSES
# ============================================================================


class ExecutionType(str, Enum):
    """Type of execution simulation."""

    OPTIMISTIC = "optimistic"  # Best case: TP before SL
    PESSIMISTIC = "pessimistic"  # Worst case: SL before TP (Req #10)
    REALISTIC = "realistic"  # Mid-point estimate


class EngineType(str, Enum):
    """Type of backtest engine."""

    STANDARD = "standard"  # Standard backtest engine
    EXECUTION = "execution"  # Pessimistic execution engine
    MULTI_STRATEGY = "multi_strategy"  # Multi-strategy engine
    ROBUST = "robust"  # Robust long-term backtest engine


@dataclass
class Position:
    """Open position tracking for intra-bar execution."""

    symbol: str
    side: str  # "long" or "short"
    quantity: Decimal
    entry_price: Decimal
    entry_time: datetime
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    stop_loss_bps: Optional[Decimal] = None
    take_profit_bps: Optional[Decimal] = None


@dataclass
class ExecutionResult:
    """Result of an order execution."""

    symbol: str
    side: str  # "buy" or "sell"
    quantity: Decimal
    signal_time: datetime  # Time signal was generated (close of bar t)
    execution_time: datetime  # Time order was executed (open of bar t+1)
    signal_price: Decimal  # Price at signal time
    execution_price: Decimal  # Actual fill price (with slippage)
    slippage_bps: Decimal  # Slippage in basis points
    commission: Decimal
    executed: bool
    partial_fill: bool = False
    fill_ratio: Decimal = Decimal("1")  # Amount actually filled

    # For positions with stops
    stop_loss_hit: bool = False
    take_profit_hit: bool = False
    stop_execution_price: Optional[Decimal] = None


@dataclass
class SlippageParams:
    """Parameters for slippage calculation."""

    price: Decimal
    is_buy: bool
    slippage_pct: Optional[Decimal] = None
    is_stop: bool = False
    is_volatile: bool = False


@dataclass
class EngineInitParams:
    """Parameters for base engine initialization."""

    config: BaseModel
    strategy: Optional[object] = None
    diagnostic_logger: Optional[object] = None
    strategy_name: str = "unknown"
    enable_risk_envelope: bool = True


@dataclass
class BacktestState:
    """
    Shared backtest state container.

    This class encapsulates all the mutable state that needs to be
    managed during a backtest run, making it easier to reset, checkpoint,
    and restore state.
    """

    capital: Decimal = Decimal("100000")
    positions: Dict[str, Decimal] = field(default_factory=dict)
    cost_basis: Dict[str, Decimal] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    last_known_prices: Dict[str, Decimal] = field(default_factory=dict)
    current_date: Optional[date] = None
    equity_curve: List[Tuple[datetime, Decimal]] = field(default_factory=list)

    def reset(self, initial_capital: Decimal) -> None:
        """Reset all state to initial values."""
        self.capital = initial_capital
        self.positions.clear()
        self.cost_basis.clear()
        self.trades.clear()
        self.last_known_prices.clear()
        self.current_date = None
        self.equity_curve.clear()

    def to_dict(self) -> Dict[str, Union[int, float, str, bool]]:
        """Convert state to dictionary for serialization."""
        return {
            "capital": float(self.capital),
            "positions": {k: float(v) for k, v in self.positions.items()},
            "cost_basis": {k: float(v) for k, v in self.cost_basis.items()},
            "trades_count": len(self.trades),
            "last_known_prices": {k: float(v) for k, v in self.last_known_prices.items()},
            "current_date": self.current_date.isoformat() if self.current_date else None,
            "equity_curve_points": len(self.equity_curve),
        }


# ============================================================================
# BASE BACKTEST ENGINE (ABSTRACT)
# ============================================================================


class BaseBacktestEngine(ABC, Generic[ConfigType, ResultType]):
    """
    Abstract base class for all backtest engines.

    This class provides:
    - Common initialization and configuration
    - Shared utility methods (slippage, validation, metrics)
    - Abstract methods that must be implemented by subclasses
    - Template method pattern for backtest execution

    Subclasses must implement:
    - run_backtest(): Main entry point for backtest execution
    - _create_result(): Create engine-specific result object
    - get_engine_type(): Return the engine type identifier

    Design Pattern: Template Method
    - The base class defines the skeleton of the algorithm
    - Subclasses implement specific steps without changing the structure
    """

    def __init__(
        self,
        config: ConfigType,
        strategy: Optional[object] = None,
        diagnostic_logger: Optional[object] = None,
        strategy_name: str = "unknown",
        enable_risk_envelope: bool = True,
    ):
        """
        Initialize the base backtest engine.

        Args:
            config: Engine configuration (BacktestConfig or subclass)
            strategy: Optional strategy instance
            diagnostic_logger: Optional diagnostic logger for detailed logging
            strategy_name: Name of the strategy being backtested
            enable_risk_envelope: Enable risk envelope validation
        """
        self.config = config
        self.strategy = strategy
        self.diagnostic_logger = diagnostic_logger
        self.strategy_name = strategy_name
        self.enable_risk_envelope = enable_risk_envelope

        # Initialize shared state
        self.state = BacktestState(
            capital=self._get_initial_capital(),
        )

        # Get configuration from CentralizedConfig
        self._bt_config = _get_backtesting_config()

        # Cache commonly used config values
        self._base_slippage_bps = self._bt_config.base_slippage_bps
        self._stop_slippage_multiplier = self._bt_config.stop_slippage_multiplier
        self._volatility_multiplier = self._bt_config.volatility_multiplier

        logger.info(
            f"{self.__class__.__name__} initialized for {strategy_name} "
            f"with capital={self.state.capital:,.2f}"
        )

    # =========================================================================
    # ABSTRACT METHODS (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    def run_backtest(
        self,
        market_data: Union[List[object], object],
        signals: Optional[List[object]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs,
    ) -> ResultType:
        """
        Run a complete backtest simulation.

        This is the main entry point for all backtest engines.
        Each subclass implements its specific backtest logic.

        Args:
            market_data: Historical market data (format varies by engine)
            signals: Optional pre-generated trading signals
            start_date: Optional start date filter
            end_date: Optional end date filter
            **kwargs: Additional engine-specific parameters

        Returns:
            Engine-specific result object (BacktestResult or subclass)
        """
        pass

    @abstractmethod
    def _create_result(self, **kwargs) -> ResultType:
        """
        Create the engine-specific result object.

        Each engine has its own result type with different metrics
        and data structures.

        Args:
            **kwargs: Parameters specific to result creation

        Returns:
            Engine-specific result object
        """
        pass

    @abstractmethod
    def get_engine_type(self) -> EngineType:
        """
        Return the engine type identifier.

        Returns:
            EngineType enum value for this engine
        """
        pass

    # =========================================================================
    # TEMPLATE METHODS (can be overridden by subclasses)
    # =========================================================================

    def _reset_backtest(self) -> None:
        """Reset backtest state for a new run."""
        self.state.reset(self._get_initial_capital())
        logger.debug(f"{self.strategy_name}: Backtest state reset")

    def _validate_config(self) -> None:
        """
        Validate the configuration before running backtest.

        Subclasses can override to add engine-specific validation.
        """
        if hasattr(self.config, "initial_capital") and self.config.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")

        if hasattr(self.config, "commission_per_trade") and self.config.commission_per_trade < 0:
            raise ValueError("Commission cannot be negative")

    def _validate_market_data(self, market_data: List[object]) -> None:
        """
        Validate market data before processing.

        Args:
            market_data: List of market data points

        Raises:
            ValueError: If market data is invalid
        """
        if not market_data:
            raise ValueError("No market data available for backtest")

    def _validate_signals(self, signals: List[object]) -> None:
        """
        Validate signals before processing.

        Args:
            signals: List of trading signals

        Raises:
            ValueError: If signals are invalid
        """
        # Subclasses can add specific validation

    # =========================================================================
    # SHARED UTILITY METHODS
    # =========================================================================

    def _get_initial_capital(self) -> Decimal:
        """Get initial capital from config."""
        if hasattr(self.config, "initial_capital"):
            return self.config.initial_capital
        return Decimal("100000")

    def _apply_slippage(self, params: SlippageParams) -> Decimal:
        """
        Apply slippage to execution price.

        SINGLE SOURCE OF TRUTH: This method provides consistent slippage
        calculation across all engines.

        Args:
            params: SlippageParams containing all parameters

        Returns:
            Execution price with slippage applied
        """
        # Use shared utility if available, otherwise use local implementation
        try:
            from app.backtesting.shared.slippage_utils import (
                apply_slippage as shared_apply_slippage,
            )

            return shared_apply_slippage(
                price=params.price,
                is_buy=params.is_buy,
                slippage_pct=params.slippage_pct,
                is_stop=params.is_stop,
                is_volatile=params.is_volatile,
            )
        except ImportError:
            # Fallback to local implementation
            return self._apply_slippage_local(params)

    def _apply_slippage_local(self, params: SlippageParams) -> Decimal:
        """
        Local implementation of slippage calculation.

        Used as fallback when shared utility is not available.
        """
        slippage = (
            params.slippage_pct
            if params.slippage_pct is not None
            else self._base_slippage_bps / Decimal("10000")
        )

        # Apply stop multiplier for stop-loss executions
        if params.is_stop:
            slippage = slippage * self._stop_slippage_multiplier

        # Apply volatility multiplier
        if params.is_volatile:
            slippage = slippage * (Decimal("1") + self._volatility_multiplier)

        # Apply slippage (buy: pay more, sell: receive less)
        if params.is_buy:
            return params.price * (Decimal("1") + slippage)
        else:
            return params.price * (Decimal("1") - slippage)

    def _build_trade_reason(self, signal: object, market_data: object) -> str:
        """
        Build human-readable reason for the trade from signal metadata.

        Args:
            signal: Trading signal
            market_data: Current market data

        Returns:
            Human-readable trade reason string
        """
        try:
            from app.backtesting.shared.trade_utils import (
                build_trade_reason as shared_build_trade_reason,
            )

            return shared_build_trade_reason(signal=signal, market_data=market_data)
        except ImportError:
            # Fallback implementation
            return self._build_trade_reason_local(signal, market_data)

    def _build_trade_reason_local(self, signal: object, market_data: object) -> str:
        """Local implementation of trade reason building."""
        reasons = []

        if hasattr(signal, "metadata") and signal.metadata:
            if "indicator" in signal.metadata:
                reasons.append(f"Indicator: {signal.metadata['indicator']}")
            if "condition" in signal.metadata:
                reasons.append(f"Condition: {signal.metadata['condition']}")

        if not reasons:
            reasons.append(f"Strategy: {self.strategy_name}")

        return " | ".join(reasons)

    def _get_price(self, md: object) -> Decimal:
        """
        Get closing price from MarketData or Quote object.

        Args:
            md: Market data object

        Returns:
            Closing price as Decimal

        Raises:
            AttributeError: If object has no price attribute
        """
        if hasattr(md, "close"):
            return md.close
        elif hasattr(md, "close_price"):
            return md.close_price
        else:
            raise AttributeError(
                f"MarketData object has no 'close' or 'close_price' attribute: {type(md)}"
            )

    def _build_price_map(self, market_data: List[object]) -> Dict[str, Decimal]:
        """
        Build a price map from market data for accurate position closing.

        Args:
            market_data: List of market data points

        Returns:
            Dictionary mapping symbol to most recent price
        """
        price_map = {}
        for md in reversed(market_data):  # Start from most recent
            if md.symbol not in price_map:
                price_map[md.symbol] = self._get_price(md)
        return price_map

    def _sort_data_by_timestamp(
        self,
        market_data: List[object],
        signals: Optional[List[object]] = None,
    ) -> Tuple[List[object], List[object]]:
        """
        Sort market data and signals by timestamp.

        Args:
            market_data: List of market data points
            signals: Optional list of signals

        Returns:
            Tuple of (sorted_market_data, sorted_signals)
        """
        market_data = sorted(market_data, key=lambda x: x.timestamp)

        if signals:
            signals = sorted(signals, key=lambda x: x.timestamp)

        return market_data, signals or []

    def _filter_by_date_range(
        self,
        data: List[object],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        timestamp_attr: str = "timestamp",
    ) -> List[object]:
        """
        Filter data by date range.

        Args:
            data: List of data points with timestamp attribute
            start_date: Optional start date filter
            end_date: Optional end date filter
            timestamp_attr: Name of timestamp attribute

        Returns:
            Filtered list
        """
        if start_date:
            data = [d for d in data if getattr(d, timestamp_attr) >= start_date]
        if end_date:
            data = [d for d in data if getattr(d, timestamp_attr) <= end_date]
        return data

    # =========================================================================
    # PICKLE SUPPORT (for multiprocessing)
    # =========================================================================

    def __getstate__(self) -> Dict[str, Union[int, float, str, bool]]:
        """
        Get state for pickling (excludes unpicklable objects).

        Subclasses should override and call super().__getstate__()
        to add their own state.
        """
        return {
            "config": self.config,
            "strategy_name": self.strategy_name,
            "state": self.state.to_dict(),
            "enable_risk_envelope": self.enable_risk_envelope,
        }

    def __setstate__(self, state: Dict[str, Union[int, float, str, bool]]) -> None:
        """
        Restore state from pickling.

        Subclasses should override and call super().__setstate__()
        to restore their own state.
        """
        self.config = state["config"]
        self.strategy_name = state["strategy_name"]
        self.enable_risk_envelope = state.get("enable_risk_envelope", True)

        # Restore state
        self.state = BacktestState(
            capital=self._get_initial_capital(),
        )

        # Reset unpicklable objects
        self.strategy = None
        self.diagnostic_logger = None

    # =========================================================================
    # LOGGING UTILITIES
    # =========================================================================

    def _log_trade(
        self,
        trade: Trade,
        action: str = "EXECUTED",
        level: int = logging.INFO,
    ) -> None:
        """Log trade execution details."""
        pnl_str = f"{trade.pnl:.2f}" if trade.pnl else "N/A"
        logger.log(
            level,
            f"{self.strategy_name} {action}: {trade.side.upper()} {trade.quantity} "
            f"{trade.symbol} @ {trade.entry_price:.2f} (PnL={pnl_str})",
        )

    def _log_signal_rejected(
        self,
        symbol: str,
        reason: str,
        details: str = "",
    ) -> None:
        """Log rejected signal details."""
        logger.warning(f"{self.strategy_name} SIGNAL REJECTED: {symbol} - {reason}. {details}")
        if self.diagnostic_logger:
            self.diagnostic_logger.log_signal_rejected(
                self.strategy_name,
                symbol,
                reason,
                details,
                {},
            )

    def _log_progress(
        self,
        current: int,
        total: int,
        message: str = "Processing",
    ) -> None:
        """Log progress during long operations."""
        if total > 0:
            pct = (current / total) * 100
            logger.info(f"{self.strategy_name}: {message} {current}/{total} ({pct:.1f}%)")
