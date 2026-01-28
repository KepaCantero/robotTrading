"""
Data models for the Robust Backtesting Engine.

This module defines all data structures used throughout the robust backtesting
system including corporate actions, dividend tracking, survivorship data, and
checkpointing structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

try:
    from pydantic import BaseModel, Field, field_validator, model_validator

    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback to standard library
    PYDANTIC_AVAILABLE = False

    from dataclasses import Field, dataclass as BaseModel, field


class CorporateActionType(str, Enum):
    """Types of corporate actions that affect stock prices and positions."""

    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    SPINOFF = "spinoff"
    DIVIDEND = "dividend"
    SPECIAL_DIVIDEND = "special_dividend"
    RIGHTS_OFFERING = "rights_offering"
    TENDER_OFFER = "tender_offer"
    DELISTING = "delisting"


class DelistingReason(str, Enum):
    """Reasons for stock delisting."""

    BANKRUPTCY = "bankruptcy"
    ACQUISITION = "acquisition"
    MERGER = "merger"
    DELISTING = "delisting"
    PRIVATE_GOING = "private_going"
    REGULATORY = "regulatory"
    LIQUIDATION = "liquidation"


@dataclass
class CorporateAction:
    """
    Base class for all corporate actions.

    Attributes:
        action_id: Unique identifier for this action
        symbol: Ticker symbol affected
        action_type: Type of corporate action
        declaration_date: Date action was announced
        ex_date: Ex-date (when action takes effect)
        record_date: Record date
        payment_date: Payment date (if applicable)
        description: Human-readable description
        metadata: Additional action-specific data
    """

    action_id: UUID = field(default_factory=uuid4)
    symbol: str = field(default="")
    action_type: CorporateActionType = field(default=CorporateActionType.STOCK_SPLIT)
    declaration_date: date = field(default_factory=date.today)
    ex_date: date = field(default_factory=date.today)
    record_date: Optional[date] = field(default=None)
    payment_date: Optional[date] = field(default=None)
    description: str = field(default="")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StockSplit(CorporateAction):
    """
    Stock split corporate action.

    Attributes:
        split_ratio: Ratio as new_shares:old_shares (e.g., 2:1 = 2.0)
        adjustment_factor: Factor to multiply historical prices by
    """

    split_ratio: Decimal = field(default=Decimal("1"))
    adjustment_factor: Decimal = field(default=Decimal("1"))

    def __post_init__(self):
        """Calculate adjustment factor from split ratio."""
        self.action_type = CorporateActionType.STOCK_SPLIT
        if self.split_ratio > 0:
            self.adjustment_factor = Decimal("1") / self.split_ratio


@dataclass
class Merger(CorporateAction):
    """
    Merger or acquisition corporate action.

    Attributes:
        target_symbol: Symbol of company being acquired
        acquirer_symbol: Symbol of acquiring company
        exchange_ratio: Ratio of acquirer shares per target share
        cash consideration: Cash amount per share (if any)
    """

    target_symbol: str = field(default="")
    acquirer_symbol: str = field(default="")
    exchange_ratio: Decimal = field(default=Decimal("1"))
    cash_consideration: Optional[Decimal] = field(default=None)

    def __post_init__(self):
        """Set action type based on symbols."""
        self.action_type = CorporateActionType.MERGER


@dataclass
class SpinOff(CorporateAction):
    """
    Spin-off corporate action.

    Attributes:
        parent_symbol: Original company symbol
        spinoff_symbol: New company symbol
        distribution_ratio: Ratio of spinoff shares per parent share
    """

    parent_symbol: str = field(default="")
    spinoff_symbol: str = field(default="")
    distribution_ratio: Decimal = field(default=Decimal("1"))

    def __post_init__(self):
        """Set action type."""
        self.action_type = CorporateActionType.SPINOFF


@dataclass
class DividendPayment(CorporateAction):
    """
    Dividend payment corporate action.

    Attributes:
        amount: Dividend amount per share
        frequency: Payment frequency (monthly, quarterly, etc.)
        qualified: Whether dividend is qualified for tax purposes
    """

    amount: Decimal = field(default=Decimal("0"))
    frequency: str = field(default="quarterly")
    qualified: bool = field(default=True)

    def __post_init__(self):
        """Set action type."""
        self.action_type = CorporateActionType.DIVIDEND


@dataclass
class DelistedStock:
    """
    Information about a delisted stock for survivorship bias correction.

    Attributes:
        symbol: Stock ticker symbol
        delisting_date: Date the stock was delisted
        reason: Primary reason for delisting
        last_price: Last trading price before delisting
        recovery_rate: Estimated recovery rate for shareholders
        returns_daily: Daily returns from listing to delisting
        market_cap: Market cap at time of delisting
        volatility: Volatility in the year before delisting
    """

    symbol: str = field(default="")
    delisting_date: date = field(default_factory=date.today)
    reason: DelistingReason = field(default=DelistingReason.DELISTING)
    last_price: Decimal = field(default=Decimal("0"))
    recovery_rate: Decimal = field(default=Decimal("0.1"))
    returns_daily: List[Tuple[date, Decimal]] = field(default_factory=list)
    market_cap: Optional[Decimal] = field(default=None)
    volatility: Optional[float] = field(default=None)


@dataclass
class DelistedReturnData:
    """
    Return data for delisted stocks to include in backtesting.

    This allows accurate backtesting by including the negative returns
    from stocks that would later be delisted.

    Attributes:
        symbol: Stock ticker symbol
        return_series: Time series of daily returns
        listing_date: When the stock was listed
        delisting_date: When the stock was delisted
        total_return: Total return from listing to delisting
        annualized_return: Annualized return
    """

    symbol: str = field(default="")
    return_series: Dict[date, Decimal] = field(default_factory=dict)
    listing_date: date = field(default_factory=date.today)
    delisting_date: date = field(default_factory=date.today)
    total_return: Decimal = field(default=Decimal("0"))
    annualized_return: Decimal = field(default=Decimal("0"))


@dataclass
class BacktestCheckpoint:
    """
    Checkpoint data for resuming interrupted backtests.

    For 25-year backtests, this allows saving progress after each year
    and resuming if the backtest is interrupted.

    Attributes:
        checkpoint_id: Unique identifier
        timestamp: When checkpoint was created
        current_date: Current simulation date
        capital: Current capital amount
        positions: Current open positions
        year: Year number in backtest (1-25)
        progress: Progress percentage (0-100)
        metrics_snapshot: Performance metrics snapshot
    """

    checkpoint_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    current_date: date = field(default_factory=date.today)
    capital: Decimal = field(default=Decimal("0"))
    positions: Dict[str, Decimal] = field(default_factory=dict)
    year: int = field(default=1)
    progress: float = field(default=0.0)
    metrics_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "checkpoint_id": str(self.checkpoint_id),
            "timestamp": self.timestamp.isoformat(),
            "current_date": self.current_date.isoformat(),
            "capital": float(self.capital),
            "positions": {k: float(v) for k, v in self.positions.items()},
            "year": self.year,
            "progress": self.progress,
            "metrics_snapshot": self.metrics_snapshot,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestCheckpoint":
        """Create checkpoint from dictionary."""
        return cls(
            checkpoint_id=UUID(data["checkpoint_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            current_date=date.fromisoformat(data["current_date"]),
            capital=Decimal(str(data["capital"])),
            positions={k: Decimal(str(v)) for k, v in data["positions"].items()},
            year=data["year"],
            progress=data["progress"],
            metrics_snapshot=data["metrics_snapshot"],
        )


@dataclass
class ProgressUpdate:
    """
    Real-time progress update for long-running backtests.

    Attributes:
        current_year: Current year being processed
        total_years: Total years to process
        current_date: Current simulation date
        total_days: Total days in backtest
        capital: Current capital
        return_pct: Current return percentage
        estimated_time_remaining: Estimated seconds remaining
        trades_executed: Number of trades executed so far
        messages: List of informational messages
    """

    current_year: int = field(default=1)
    total_years: int = field(default=25)
    current_date: date = field(default_factory=date.today)
    total_days: int = field(default=252 * 25)
    capital: Decimal = field(default=Decimal("0"))
    return_pct: Decimal = field(default=Decimal("0"))
    estimated_time_remaining: float = field(default=0.0)
    trades_executed: int = field(default=0)
    messages: List[str] = field(default_factory=list)

    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_days == 0:
            return 0.0
        days_completed = (self.current_year - 1) * 252
        return (days_completed / self.total_days) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_year": self.current_year,
            "total_years": self.total_years,
            "current_date": self.current_date.isoformat(),
            "total_days": self.total_days,
            "capital": float(self.capital),
            "return_pct": float(self.return_pct),
            "estimated_time_remaining": self.estimated_time_remaining,
            "trades_executed": self.trades_executed,
            "progress_percentage": self.progress_percentage(),
            "messages": self.messages,
        }


@dataclass
class DividendAction:
    """
    Record of a dividend action taken during backtesting.

    Attributes:
        symbol: Stock that paid dividend
        ex_date: Ex-dividend date
        amount: Dividend amount per share
        shares: Number of shares held
        total_amount: Total dividend received
        reinvested: Whether dividend was reinvested
        reinvestment_price: Price at which dividend was reinvested
        reinvestment_shares: Number of shares acquired via reinvestment
    """

    symbol: str = field(default="")
    ex_date: date = field(default_factory=date.today)
    amount: Decimal = field(default=Decimal("0"))
    shares: Decimal = field(default=Decimal("0"))
    total_amount: Decimal = field(default=Decimal("0"))
    reinvested: bool = field(default=False)
    reinvestment_price: Optional[Decimal] = field(default=None)
    reinvestment_shares: Optional[Decimal] = field(default=None)


@dataclass
class DividendTracker:
    """
    Tracks all dividend activity during backtesting.

    Attributes:
        total_dividends_received: Total cash dividends received
        total_dividends_reinvested: Total dividends reinvested
        dividend_yield: Overall dividend yield percentage
        dividend_count: Number of dividend payments received
        yield_on_cost: Yield on original investment
        dividend_history: List of all dividend actions
    """

    total_dividends_received: Decimal = field(default=Decimal("0"))
    total_dividends_reinvested: Decimal = field(default=Decimal("0"))
    dividend_yield: Decimal = field(default=Decimal("0"))
    dividend_count: int = field(default=0)
    yield_on_cost: Decimal = field(default=Decimal("0"))
    dividend_history: List[DividendAction] = field(default_factory=list)
    _original_investment: Decimal = field(default=Decimal("0"))

    def add_dividend(self, action: DividendAction) -> None:
        """Add a dividend action to the tracker."""
        self.dividend_history.append(action)
        self.total_dividends_received += action.total_amount
        self.dividend_count += 1

        if action.reinvested:
            self.total_dividends_reinvested += action.total_amount

    def calculate_yield(self, current_portfolio_value: Decimal) -> None:
        """Calculate dividend yield metrics."""
        if self._original_investment > 0:
            self.yield_on_cost = self.total_dividends_received / self._original_investment * 100

        if current_portfolio_value > 0:
            self.dividend_yield = self.total_dividends_received / current_portfolio_value * 100

    def set_original_investment(self, amount: Decimal) -> None:
        """Set the original investment for yield on cost calculation."""
        self._original_investment = amount


@dataclass
class DripConfig:
    """
    Configuration for dividend reinvestment (DRIP).

    Attributes:
        enable_drip: Whether to enable dividend reinvestment
        reinvest_all: Whether to reinvest all dividends (vs. partial)
        reinvest_same_stock: Reinvest in the same stock that paid dividend
        min_reinvestment_amount: Minimum amount for reinvestment
        commission_drip: Commission rate for DRIP transactions
        fractional_shares: Allow fractional shares for DRIP
    """

    enable_drip: bool = field(default=False)
    reinvest_all: bool = field(default=True)
    reinvest_same_stock: bool = field(default=True)
    min_reinvestment_amount: Decimal = field(default=Decimal("10"))
    commission_drip: Decimal = field(default=Decimal("0"))
    fractional_shares: bool = field(default=True)
