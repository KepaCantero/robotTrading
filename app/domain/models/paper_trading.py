"""
Paper Trading Models for Analytic Mode

This module defines models for paper trading simulation, virtual portfolio management,
and trade execution simulation for the algorithmic trading system.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class PaperTradingMode(str, Enum):
    """Paper trading simulation modes."""

    SIMPLE = "simple"  # Basic simulation without fees/slippage
    REALISTIC = "realistic"  # Includes fees, slippage, and market impact
    ADVANCED = "advanced"  # Full simulation with latency and partial fills


class TradeStatus(str, Enum):
    """Paper trade status."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(str, Enum):
    """Order side for paper trading."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type for paper trading."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class PaperTrade(BaseModel):
    """Paper trading trade record."""

    id: UUID = Field(default_factory=uuid4, description="Unique trade identifier")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Trade side (buy/sell)")
    order_type: OrderType = Field(..., description="Order type")

    # Trade details
    quantity: Decimal = Field(..., gt=0, description="Trade quantity")
    price: Decimal = Field(..., gt=0, description="Execution price")
    filled_quantity: Decimal = Field(default=Decimal("0"), ge=0, description="Filled quantity")
    filled_price: Decimal | None = Field(None, gt=0, description="Average fill price")

    # Simulation details
    slippage: Decimal = Field(default=Decimal("0"), ge=0, description="Slippage amount")
    commission: Decimal = Field(default=Decimal("0"), ge=0, description="Commission paid")
    market_impact: Decimal = Field(default=Decimal("0"), ge=0, description="Market impact cost")

    # Status and timing
    status: TradeStatus = Field(default=TradeStatus.PENDING, description="Trade status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Trade creation time")
    filled_at: datetime | None = Field(None, description="Fill time")
    cancelled_at: datetime | None = Field(None, description="Cancellation time")

    # P&L calculation
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")

    # Metadata
    strategy_id: str | None = Field(None, description="Strategy that generated the trade")
    signal_id: UUID | None = Field(None, description="Signal that triggered the trade")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional trade metadata")

    @field_validator("quantity", "price", "filled_quantity", "filled_price")
    @classmethod
    def validate_positive_fields(cls, v) -> Decimal:
        """Validate positive numeric fields."""
        if v is None:
            return v

        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Numeric fields must be numbers")

        if v <= 0:
            raise ValueError(f"Field must be positive, got {v}")

        return v

    @field_validator("filled_quantity")
    @classmethod
    def validate_filled_quantity(cls, v, info) -> Decimal:
        """Validate filled quantity doesn't exceed order quantity."""
        if v is None:
            return v

        if isinstance(v, (int, float)):
            v = Decimal(str(v))

        # Get quantity from the model data
        if hasattr(info, "data") and "quantity" in info.data:
            quantity = Decimal(str(info.data["quantity"]))
            if v > quantity:
                raise ValueError(f"Filled quantity ({v}) cannot exceed order quantity ({quantity})")

        return v

    @model_validator(mode="after")
    def validate_trade_consistency(self) -> PaperTrade:
        """Validate trade consistency."""
        if self.filled_quantity > self.quantity:
            logger.error(
                "Trade validation failed: filled quantity exceeds order quantity",
                extra={
                    "trade_id": str(self.id),
                    "symbol": self.symbol,
                    "filled_quantity": float(self.filled_quantity),
                    "quantity": float(self.quantity),
                },
            )
            raise ValueError(
                f"Filled quantity ({self.filled_quantity}) cannot exceed order quantity ({self.quantity})"
            )

        if self.status == TradeStatus.FILLED and self.filled_quantity != self.quantity:
            logger.error(
                "Trade validation failed: filled status but quantity mismatch",
                extra={
                    "trade_id": str(self.id),
                    "symbol": self.symbol,
                    "status": self.status.value,
                    "filled_quantity": float(self.filled_quantity),
                    "quantity": float(self.quantity),
                },
            )
            raise ValueError("Filled trade must have filled_quantity equal to quantity")

        if self.status == TradeStatus.PARTIALLY_FILLED and self.filled_quantity >= self.quantity:
            logger.error(
                "Trade validation failed: partial fill status but invalid quantity",
                extra={
                    "trade_id": str(self.id),
                    "symbol": self.symbol,
                    "status": self.status.value,
                    "filled_quantity": float(self.filled_quantity),
                    "quantity": float(self.quantity),
                },
            )
            raise ValueError("Partially filled trade must have filled_quantity less than quantity")

        if self.filled_at and self.filled_at < self.created_at:
            logger.error(
                "Trade validation failed: fill time before creation time",
                extra={
                    "trade_id": str(self.id),
                    "symbol": self.symbol,
                    "filled_at": self.filled_at.isoformat(),
                    "created_at": self.created_at.isoformat(),
                },
            )
            raise ValueError(
                f"Fill time ({self.filled_at}) cannot be before creation time ({self.created_at})"
            )

        logger.debug(
            "Paper trade validated successfully",
            extra={
                "trade_id": str(self.id),
                "symbol": self.symbol,
                "status": self.status.value,
            },
        )

        return self


class PaperPosition(BaseModel):
    """Paper trading position."""

    id: UUID = Field(default_factory=uuid4, description="Unique position identifier")
    symbol: str = Field(..., description="Trading symbol")

    # Position details
    quantity: Decimal = Field(
        ..., description="Current position quantity (can be negative for short)"
    )
    avg_price: Decimal = Field(..., gt=0, description="Average entry price")
    current_price: Decimal = Field(..., gt=0, description="Current market price")

    # P&L calculations
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    total_pnl: Decimal = Field(default=Decimal("0"), description="Total P&L")

    # Position metrics
    market_value: Decimal = Field(..., ge=0, description="Current market value")
    cost_basis: Decimal = Field(..., ge=0, description="Total cost basis")

    # Timing
    opened_at: datetime = Field(
        default_factory=datetime.utcnow, description="Position opening time"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional position metadata"
    )

    @field_validator("avg_price", "current_price")
    @classmethod
    def validate_price_fields(cls, v) -> Decimal:
        """Validate price fields are positive."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Price fields must be numbers")

        if v <= 0:
            raise ValueError(f"Price fields must be positive, got {v}")

        return v

    @field_validator("market_value", "cost_basis")
    @classmethod
    def validate_value_fields(cls, v) -> Decimal:
        """Validate value fields are non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Value fields must be numbers")

        if v < 0:
            raise ValueError(f"Value fields must be non-negative, got {v}")

        return v

    @model_validator(mode="after")
    def calculate_metrics(self) -> PaperPosition:
        """Calculate position metrics."""
        # Calculate market value
        self.market_value = abs(self.quantity) * self.current_price

        # Calculate cost basis
        self.cost_basis = abs(self.quantity) * self.avg_price

        # Calculate unrealized P&L
        if self.quantity > 0:  # Long position
            self.unrealized_pnl = self.quantity * (self.current_price - self.avg_price)
        elif self.quantity < 0:  # Short position
            self.unrealized_pnl = abs(self.quantity) * (self.avg_price - self.current_price)
        else:  # No position
            self.unrealized_pnl = Decimal("0")

        # Calculate total P&L
        self.total_pnl = self.unrealized_pnl + self.realized_pnl

        logger.debug(
            "Position metrics calculated",
            extra={
                "position_id": str(self.id),
                "symbol": self.symbol,
                "quantity": float(self.quantity),
                "unrealized_pnl": float(self.unrealized_pnl),
                "total_pnl": float(self.total_pnl),
            },
        )

        return self

    def recalculate_metrics(self) -> None:
        """Recalculate position metrics after price update."""
        # Calculate market value
        self.market_value = abs(self.quantity) * self.current_price

        # Calculate cost basis
        self.cost_basis = abs(self.quantity) * self.avg_price

        # Calculate unrealized P&L
        if self.quantity > 0:  # Long position
            self.unrealized_pnl = self.quantity * (self.current_price - self.avg_price)
        elif self.quantity < 0:  # Short position
            self.unrealized_pnl = abs(self.quantity) * (self.avg_price - self.current_price)
        else:  # No position
            self.unrealized_pnl = Decimal("0")

        # Calculate total P&L
        self.total_pnl = self.unrealized_pnl + self.realized_pnl

        logger.debug(
            "Position metrics recalculated",
            extra={
                "position_id": str(self.id),
                "symbol": self.symbol,
                "current_price": float(self.current_price),
                "unrealized_pnl": float(self.unrealized_pnl),
            },
        )


class PaperPortfolio(BaseModel):
    """Paper trading portfolio."""

    id: UUID = Field(default_factory=uuid4, description="Unique portfolio identifier")
    name: str = Field(..., description="Portfolio name")

    # Cash and equity
    cash_balance: Decimal = Field(..., ge=0, description="Available cash balance")
    initial_cash: Decimal = Field(..., gt=0, description="Initial cash amount")
    total_equity: Decimal = Field(..., ge=0, description="Total portfolio equity")

    # Positions
    positions: list[PaperPosition] = Field(default_factory=list, description="Current positions")

    # Performance metrics
    total_pnl: Decimal = Field(default=Decimal("0"), description="Total portfolio P&L")
    total_return: Decimal = Field(default=Decimal("0"), description="Total return percentage")
    daily_pnl: Decimal = Field(default=Decimal("0"), description="Daily P&L")
    daily_return: Decimal = Field(default=Decimal("0"), description="Daily return percentage")

    # Risk metrics
    max_drawdown: Decimal = Field(default=Decimal("0"), ge=0, description="Maximum drawdown")
    sharpe_ratio: Decimal | None = Field(None, description="Sharpe ratio")
    volatility: Decimal | None = Field(None, ge=0, description="Portfolio volatility")

    # Settings
    simulation_mode: PaperTradingMode = Field(
        default=PaperTradingMode.REALISTIC, description="Simulation mode"
    )
    config_id: UUID | None = Field(None, description="Configuration ID")
    commission_rate: Decimal = Field(
        default=Decimal("0.001"),
        ge=0,
        le=Decimal("0.01"),
        description="Commission rate",
    )
    slippage_rate: Decimal = Field(
        default=Decimal("0.0005"), ge=0, le=Decimal("0.01"), description="Slippage rate"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Portfolio creation time"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional portfolio metadata"
    )

    @field_validator("cash_balance", "initial_cash", "total_equity")
    @classmethod
    def validate_cash_fields(cls, v) -> Decimal:
        """Validate cash fields are non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Cash fields must be numbers")

        if v < 0:
            raise ValueError(f"Cash fields must be non-negative, got {v}")

        return v

    @field_validator("commission_rate", "slippage_rate")
    @classmethod
    def validate_rate_fields(cls, v) -> Decimal:
        """Validate rate fields are within reasonable bounds."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Rate fields must be numbers")

        if v < 0:
            raise ValueError(f"Rate fields must be non-negative, got {v}")
        if v > Decimal("0.1"):  # 10% max rate
            raise ValueError(f"Rate fields must be less than 10%, got {v}")

        return v

    @model_validator(mode="after")
    def calculate_portfolio_metrics(self) -> PaperPortfolio:
        """Calculate portfolio metrics."""
        # Calculate total equity
        positions_value = sum(pos.market_value for pos in self.positions)
        self.total_equity = self.cash_balance + positions_value

        # Calculate total P&L
        positions_pnl = sum(pos.total_pnl for pos in self.positions)
        cash_pnl = self.cash_balance - self.initial_cash
        self.total_pnl = positions_pnl + cash_pnl

        # Calculate total return
        if self.initial_cash > 0:
            self.total_return = (self.total_pnl / self.initial_cash) * Decimal("100")

        logger.debug(
            "Portfolio metrics calculated",
            extra={
                "portfolio_id": str(self.id),
                "portfolio_name": self.name,
                "total_equity": float(self.total_equity),
                "total_pnl": float(self.total_pnl),
                "total_return": float(self.total_return),
                "positions_count": len(self.positions),
            },
        )

        return self


class PaperTradingConfig(BaseModel):
    """Paper trading configuration."""

    id: UUID = Field(default_factory=uuid4, description="Unique config identifier")
    name: str = Field(..., description="Configuration name")

    # Simulation settings
    simulation_mode: PaperTradingMode = Field(
        default=PaperTradingMode.REALISTIC, description="Simulation mode"
    )
    initial_cash: Decimal = Field(
        default=Decimal("100000"), gt=0, description="Initial cash amount"
    )

    # Trading costs
    commission_rate: Decimal = Field(
        default=Decimal("0.001"),
        ge=0,
        le=Decimal("0.01"),
        description="Commission rate",
    )
    slippage_rate: Decimal = Field(
        default=Decimal("0.0005"), ge=0, le=Decimal("0.01"), description="Slippage rate"
    )
    market_impact_rate: Decimal = Field(
        default=Decimal("0.0001"),
        ge=0,
        le=Decimal("0.01"),
        description="Market impact rate",
    )

    # Risk limits
    max_position_size: Decimal = Field(
        default=Decimal("0.1"),
        gt=0,
        le=Decimal("1"),
        description="Max position size as % of portfolio",
    )
    max_daily_loss: Decimal = Field(
        default=Decimal("0.05"),
        gt=0,
        le=Decimal("0.5"),
        description="Max daily loss as % of portfolio",
    )
    max_drawdown: Decimal = Field(
        default=Decimal("0.15"),
        gt=0,
        le=Decimal("0.5"),
        description="Max drawdown as % of portfolio",
    )

    # Execution settings
    execution_delay_ms: int = Field(
        default=100, ge=0, le=5000, description="Execution delay in milliseconds"
    )
    partial_fill_probability: Decimal = Field(
        default=Decimal("0.1"),
        ge=0,
        le=Decimal("1"),
        description="Probability of partial fills",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Configuration creation time"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional configuration metadata"
    )

    @field_validator("initial_cash")
    @classmethod
    def validate_initial_cash(cls, v) -> Decimal:
        """Validate initial cash is positive."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Initial cash must be a number")

        if v <= 0:
            raise ValueError(f"Initial cash must be positive, got {v}")

        return v


class PaperTradingSession(BaseModel):
    """Paper trading session."""

    id: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    portfolio_id: UUID = Field(..., description="Portfolio ID")
    config_id: UUID = Field(..., description="Configuration ID")

    # Session details
    name: str = Field(..., description="Session name")
    description: str | None = Field(None, description="Session description")

    # Status
    is_active: bool = Field(default=True, description="Whether session is active")
    status: str = Field(default="running", description="Session status")

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Session start time")
    ended_at: datetime | None = Field(None, description="Session end time")
    last_activity: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity time"
    )

    # Statistics
    total_trades: int = Field(default=0, ge=0, description="Total number of trades")
    successful_trades: int = Field(default=0, ge=0, description="Number of successful trades")
    failed_trades: int = Field(default=0, ge=0, description="Number of failed trades")

    # Performance
    session_pnl: Decimal = Field(default=Decimal("0"), description="Session P&L")
    session_return: Decimal = Field(default=Decimal("0"), description="Session return percentage")

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional session metadata"
    )

    @field_validator("session_pnl")
    @classmethod
    def validate_session_pnl(cls, v) -> Decimal:
        """Validate session P&L."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Session P&L must be a number")

        return v

    @model_validator(mode="after")
    def validate_session_timing(self) -> PaperTradingSession:
        """Validate session timing."""
        if self.ended_at and self.ended_at < self.started_at:
            logger.error(
                "Session timing validation failed: end time before start time",
                extra={
                    "session_id": str(self.id),
                    "session_name": self.name,
                    "started_at": self.started_at.isoformat(),
                    "ended_at": self.ended_at.isoformat(),
                },
            )
            raise ValueError(
                f"End time ({self.ended_at}) cannot be before start time ({self.started_at})"
            )

        if self.last_activity < self.started_at:
            logger.error(
                "Session timing validation failed: last activity before start time",
                extra={
                    "session_id": str(self.id),
                    "session_name": self.name,
                    "started_at": self.started_at.isoformat(),
                    "last_activity": self.last_activity.isoformat(),
                },
            )
            raise ValueError(
                f"Last activity ({self.last_activity}) cannot be before start time ({self.started_at})"
            )

        logger.debug(
            "Paper trading session validated successfully",
            extra={
                "session_id": str(self.id),
                "session_name": self.name,
                "is_active": self.is_active,
                "total_trades": self.total_trades,
            },
        )

        return self
