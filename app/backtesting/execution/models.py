"""
Data models for the Execution Model (FASE 5.2)

This module defines all data models used throughout the execution system,
including orders, fills, market snapshots, and execution results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

try:
    from pydantic import BaseModel, Field, field_validator, model_validator

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    # Create pydantic-like API using dataclasses
    class Field:
        """Fallback Field descriptor for dataclasses."""

        def __init__(self, default=None, default_factory=None, **kwargs):
            self.default = default
            self.default_factory = default_factory
            self.kwargs = kwargs

    class BaseModel:
        """Fallback base class using dataclasses."""

        def model_dump(self):
            """Convert to dictionary."""
            result = {}
            for key in self.__dataclass_fields__:
                value = getattr(self, key)
                if isinstance(value, Decimal):
                    result[key] = float(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list):
                    result[key] = [v.model_dump() if hasattr(v, "model_dump") else v for v in value]
                else:
                    result[key] = value
            return result

    def field_validator(*args):
        """Fallback field validator decorator."""

        def decorator(func):
            return func

        return decorator

    def model_validator(*args, **kwargs):
        """Fallback model validator decorator."""

        def decorator(func):
            return func

        return decorator

    # Apply dataclass decorator to subclasses
    def __init_subclass__(cls, **kwargs):
        dataclass(cls)


class OrderSide(str, Enum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeOfDay(str, Enum):
    """Time of day categories for slippage impact."""

    PRE_MARKET = "pre_market"  # Before 9:30 AM ET
    OPEN = "open"  # First 30 minutes (9:30-10:00 AM ET)
    MORNING = "morning"  # 10:00 AM - 12:00 PM ET
    LUNCH = "lunch"  # 12:00 PM - 1:00 PM ET
    AFTERNOON = "afternoon"  # 1:00 PM - 3:30 PM ET
    CLOSE = "close"  # Last 30 minutes (3:30-4:00 PM ET)
    AFTER_HOURS = "after_hours"  # After 4:00 PM ET


class FillReason(str, Enum):
    """Reason for order fill or rejection."""

    """
    Fill reasons:
    - FULL_FILL: Order filled completely at once
    - PARTIAL_FILL: Order partially filled (remaining cancelled)
    - MULTIPLE_FILL: Order filled in multiple portions
    - IMMEDIATE_FILL: Market order filled immediately

    Rejection reasons:
    - INSUFFICIENT_LIQUIDITY: Not enough volume to fill
    - PRICE_LIMIT: Price moved outside limit
    - MARKET_CLOSED: Market not open
    - CAPITAL_LIMIT: Insufficient capital
    - POSITION_LIMIT: Position size limit reached
    - RISK_LIMIT: Risk management limit
    - EXCEEDS_ADV: Order too large for average daily volume
    """
    FULL_FILL = "full_fill"
    PARTIAL_FILL = "partial_fill"
    MULTIPLE_FILL = "multiple_fill"
    IMMEDIATE_FILL = "immediate_fill"
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    PRICE_LIMIT = "price_limit"
    MARKET_CLOSED = "market_closed"
    CAPITAL_LIMIT = "capital_limit"
    POSITION_LIMIT = "position_limit"
    RISK_LIMIT = "risk_limit"
    EXCEEDS_ADV = "exceeds_adv"


@dataclass(frozen=True)
class MarketSnapshot:
    """
    Snapshot of market conditions at a point in time.

    This represents all market data needed for execution decisions.
    """

    timestamp: datetime
    symbol: str

    # Price data
    bid: Decimal
    ask: Decimal
    last_price: Decimal
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None

    # Volume data
    bid_size: int = 0
    ask_size: int = 0
    volume: int = 0
    average_daily_volume: Decimal = Decimal("0")

    # Volatility data
    implied_volatility: Optional[Decimal] = None
    historical_volatility_20d: Optional[Decimal] = None
    vix: Optional[Decimal] = None

    # Market conditions
    is_market_open: bool = True
    is_trading_halt: bool = False
    is_short_sale_restricted: bool = False

    # Spread calculation
    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread."""
        return self.ask - self.bid

    @property
    def spread_bps(self) -> Decimal:
        """Calculate spread in basis points."""
        if self.last_price > 0:
            return (self.spread / self.last_price) * Decimal("10000")
        return Decimal("0")

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price."""
        return (self.bid + self.ask) / 2

    def get_time_of_day(self) -> TimeOfDay:
        """
        Determine time of day category.

        Returns:
            TimeOfDay category based on timestamp
        """
        if not self.timestamp:
            return TimeOfDay.AFTERNOON

        t = self.timestamp.time()

        if t < time(9, 30):
            return TimeOfDay.PRE_MARKET
        elif t < time(10, 0):
            return TimeOfDay.OPEN
        elif t < time(12, 0):
            return TimeOfDay.MORNING
        elif t < time(13, 0):
            return TimeOfDay.LUNCH
        elif t < time(15, 30):
            return TimeOfDay.AFTERNOON
        elif t < time(16, 0):
            return TimeOfDay.CLOSE
        else:
            return TimeOfDay.AFTER_HOURS


@dataclass
class Order:
    """
    Order representation for execution.

    This represents an order to be executed by the execution model.
    """

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int  # Number of shares

    # Price fields (required for limit/stop orders)
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Constraints
    max_slippage_bps: Optional[Decimal] = None
    min_fill_quantity: int = 0  # Minimum acceptable fill (all-or-none if > 0)
    adv_limit_pct: Decimal = Decimal("0.1")  # Max 10% of ADV by default

    # Status tracking
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: Decimal = Decimal("0")

    # Metadata
    strategy_name: str = ""
    reason: str = ""

    @property
    def remaining_quantity(self) -> int:
        """Get remaining unfilled quantity."""
        return self.quantity - self.filled_quantity

    @property
    def is_fully_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.filled_quantity >= self.quantity

    @property
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        )

    @property
    def estimated_value(self) -> Decimal:
        """Estimate order value at current market price."""
        # This is a rough estimate, actual value depends on fill prices
        return Decimal(str(self.quantity)) * Decimal("100")  # Placeholder

    def validate(self) -> bool:
        """
        Validate order parameters.

        Returns:
            True if valid

        Raises:
            ValueError: If order parameters are invalid
        """
        if self.quantity <= 0:
            raise ValueError(f"Order quantity must be positive, got {self.quantity}")

        if self.side not in OrderSide:
            raise ValueError(f"Invalid order side: {self.side}")

        if self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and self.limit_price is None:
            raise ValueError(f"{self.order_type} orders require limit_price")

        if self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self.stop_price is None:
            raise ValueError(f"{self.order_type} orders require stop_price")

        if self.max_slippage_bps is not None and self.max_slippage_bps < 0:
            raise ValueError("max_slippage_bps cannot be negative")

        if self.adv_limit_pct <= 0 or self.adv_limit_pct > 1:
            raise ValueError("adv_limit_pct must be between 0 and 1")

        return True


@dataclass(frozen=True)
class CostBreakdown:
    """
    Detailed breakdown of execution costs.

    This provides transparency into all components of trading costs.
    """

    # Commission
    commission: Decimal = Decimal("0")

    # US Equity regulatory fees
    sec_fee: Decimal = Decimal("0")  # SEC fee on sells
    finra_taf: Decimal = Decimal("0")  # Trading Activity Fee
    exchange_fee: Decimal = Decimal("0")  # Exchange fees

    # Execution costs
    slippage_cost: Decimal = Decimal("0")  # Cost from slippage
    market_impact_cost: Decimal = Decimal("0")  # Cost from market impact

    # Spread cost
    spread_cost: Decimal = Decimal("0")  # Half-spread cost

    # Platform/other fees
    platform_fee: Decimal = Decimal("0")

    @property
    def total_regulatory_fees(self) -> Decimal:
        """Total regulatory fees."""
        return self.sec_fee + self.finra_taf + self.exchange_fee

    @property
    def total_execution_costs(self) -> Decimal:
        """Total execution costs (slippage + impact + spread)."""
        return self.slippage_cost + self.market_impact_cost + self.spread_cost

    @property
    def total_cost(self) -> Decimal:
        """Total all costs."""
        return (
            self.commission
            + self.total_regulatory_fees
            + self.total_execution_costs
            + self.platform_fee
        )


@dataclass(frozen=True)
class FillResult:
    """
    Result of an order execution attempt.

    This represents the outcome of trying to fill an order.
    """

    order_id: str
    symbol: str
    side: OrderSide

    # Fill details
    filled: bool
    filled_shares: int
    fill_price: Decimal
    fill_time: Optional[datetime]

    # Cost breakdown
    commission: Decimal
    slippage_bps: Decimal
    market_impact_bps: Decimal
    total_cost: Decimal

    # Fill reason
    fill_reason: FillReason

    # Additional context
    bid_at_fill: Optional[Decimal] = None
    ask_at_fill: Optional[Decimal] = None
    spread_at_fill_bps: Optional[Decimal] = None
    adv_at_fill: Decimal = Decimal("0")
    volatility_at_fill: Optional[Decimal] = None

    # Partial fill info
    is_partial_fill: bool = False
    remaining_shares: int = 0
    estimated_remaining_cost: Decimal = Decimal("0")

    # Metadata
    execution_time_ms: int = 0  # Time taken to execute in milliseconds
    warnings: List[str] = field(default_factory=list)

    @property
    def fill_value(self) -> Decimal:
        """Total value of the fill."""
        return Decimal(str(self.filled_shares)) * self.fill_price

    @property
    def effective_cost_bps(self) -> Decimal:
        """Effective total cost in basis points of fill value."""
        if self.fill_value > 0:
            return (self.total_cost / self.fill_value) * Decimal("10000")
        return Decimal("0")

    @property
    def net_profit_loss(self) -> Decimal:
        """
        Calculate P&L from the fill (for sells only).

        For buy orders, this is the negative of total cost.
        For sell orders, this is fill value minus total cost.
        """
        if self.side == OrderSide.SELL:
            return self.fill_value - self.total_cost
        else:
            return -self.total_cost


@dataclass(frozen=True)
class ExecutionResult:
    """
    Complete execution result for a trade.

    This aggregates all fills for an order into a complete execution result.
    """

    order: Order
    fills: List[FillResult]

    # Aggregated results
    total_filled_shares: int
    avg_fill_price: Decimal
    total_commission: Decimal
    total_slippage_bps: Decimal
    total_market_impact_bps: Decimal
    total_cost: Decimal

    # Timing
    first_fill_time: Optional[datetime]
    last_fill_time: Optional[datetime]

    # Status
    is_fully_filled: bool
    is_partial_fill: bool
    is_rejected: bool

    # Cost breakdown
    cost_breakdown: CostBreakdown

    # Metadata
    execution_summary: str = ""
    warnings: List[str] = field(default_factory=list)

    @property
    def total_fill_value(self) -> Decimal:
        """Total value of all fills."""
        return Decimal(str(self.total_filled_shares)) * self.avg_fill_price

    @property
    def total_cost_bps(self) -> Decimal:
        """Total cost as percentage of fill value."""
        if self.total_fill_value > 0:
            return (self.total_cost / self.total_fill_value) * Decimal("10000")
        return Decimal("0")

    @property
    def execution_duration_seconds(self) -> Optional[float]:
        """Time between first and last fill in seconds."""
        if self.first_fill_time and self.last_fill_time:
            return (self.last_fill_time - self.first_fill_time).total_seconds()
        return None


@dataclass
class ExecutionSummary:
    """
    High-level summary of execution statistics.

    This provides aggregated statistics for reporting and analysis.
    """

    # Order statistics
    total_orders: int = 0
    filled_orders: int = 0
    partially_filled_orders: int = 0
    rejected_orders: int = 0

    # Volume statistics
    total_shares_requested: int = 0
    total_shares_filled: int = 0
    fill_rate: Decimal = Decimal("0")

    # Cost statistics
    total_commission: Decimal = Decimal("0")
    total_slippage_cost: Decimal = Decimal("0")
    total_market_impact_cost: Decimal = Decimal("0")
    total_regulatory_fees: Decimal = Decimal("0")
    total_all_costs: Decimal = Decimal("0")

    # Performance metrics
    avg_slippage_bps: Decimal = Decimal("0")
    avg_market_impact_bps: Decimal = Decimal("0")
    avg_effective_cost_bps: Decimal = Decimal("0")

    # Value statistics
    total_execution_value: Decimal = Decimal("0")
    total_cost_as_pct: Decimal = Decimal("0")

    def add_execution(self, result: ExecutionResult) -> None:
        """
        Add an execution result to the summary.

        Args:
            result: ExecutionResult to add to summary
        """
        self.total_orders += 1

        if result.is_fully_filled:
            self.filled_orders += 1
        elif result.is_partial_fill:
            self.partially_filled_orders += 1
        elif result.is_rejected:
            self.rejected_orders += 1

        self.total_shares_requested += result.order.quantity
        self.total_shares_filled += result.total_filled_shares

        if result.total_fill_value > 0:
            self.total_execution_value += result.total_fill_value

        self.total_commission += result.total_commission
        self.total_slippage_cost += result.cost_breakdown.slippage_cost
        self.total_market_impact_cost += result.cost_breakdown.market_impact_cost
        self.total_regulatory_fees += result.cost_breakdown.total_regulatory_fees
        self.total_all_costs += result.total_cost

        # Recalculate averages
        if self.total_orders > 0:
            self.fill_rate = (
                Decimal(str(self.total_shares_filled)) / Decimal(str(self.total_shares_requested))
                if self.total_shares_requested > 0
                else Decimal("0")
            )

            if self.total_execution_value > 0:
                self.total_cost_as_pct = (
                    self.total_all_costs / self.total_execution_value * Decimal("100")
                )

    def to_dict(self) -> Dict:
        """Convert summary to dictionary."""
        return {
            "order_statistics": {
                "total_orders": self.total_orders,
                "filled_orders": self.filled_orders,
                "partially_filled_orders": self.partially_filled_orders,
                "rejected_orders": self.rejected_orders,
            },
            "volume_statistics": {
                "total_shares_requested": self.total_shares_requested,
                "total_shares_filled": self.total_shares_filled,
                "fill_rate": float(self.fill_rate),
            },
            "cost_statistics": {
                "total_commission": float(self.total_commission),
                "total_slippage_cost": float(self.total_slippage_cost),
                "total_market_impact_cost": float(self.total_market_impact_cost),
                "total_regulatory_fees": float(self.total_regulatory_fees),
                "total_all_costs": float(self.total_all_costs),
            },
            "performance_metrics": {
                "avg_slippage_bps": float(self.avg_slippage_bps),
                "avg_market_impact_bps": float(self.avg_market_impact_bps),
                "avg_effective_cost_bps": float(self.avg_effective_cost_bps),
            },
            "value_statistics": {
                "total_execution_value": float(self.total_execution_value),
                "total_cost_as_pct": float(self.total_cost_as_pct),
            },
        }
