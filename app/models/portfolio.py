"""
Portfolio Provider Interface and Models

This module defines the core interfaces and models for portfolio management
across different brokers (IBKR, Binance, Paper Trading).
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.centralized_config import get_config


class HedgingMetadata(BaseModel):
    """Metadata for currency hedging on positions [TASK-5.5-CURRENCY-HEDGING]."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    is_hedge: bool = Field(
        default=False, description="Whether this position is a hedge (not a base position)"
    )
    base_position_id: Optional[str] = Field(
        default=None, description="ID of the position being hedged (if is_hedge=True)"
    )
    hedge_ratio: Decimal = Field(
        default=Decimal("1.0"),
        ge=Decimal("0"),
        le=Decimal("1.0"),
        description="Ratio of position being hedged (0-1)",
    )
    hedge_currency_pair: Optional[str] = Field(
        default=None, description="Forex pair used for hedging (e.g., EUR/USD)"
    )
    hedge_cost_bps: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), description="Hedging cost in basis points"
    )
    hedge_created_at: Optional[datetime] = Field(
        default=None, description="When the hedge was created"
    )
    hedge_expires_at: Optional[datetime] = Field(
        default=None, description="When rolling hedge expires (if applicable)"
    )

    @field_validator("hedge_cost_bps")
    @classmethod
    def validate_hedge_cost(cls, v) -> Decimal:
        """
        Validate hedge cost.

        Uses configured maximum hedge cost limit.
        """
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Hedge cost must be a number")

        # Get max hedge cost from config
        config = get_config()
        max_hedge_cost = Decimal(str(getattr(config.compliance, 'MAX_HEDGE_COST_BPS', 1000)))

        if v > max_hedge_cost:
            raise ValueError(f"Hedge cost exceeds maximum limit of {max_hedge_cost} bps, got {v}")

        return v


class AssetClass(str, Enum):
    """Asset class enumeration for portfolio categorization."""

    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    BOND = "bond"


class Position(BaseModel):
    """Represents a single position in the portfolio."""

    model_config = ConfigDict(
        strict=True,  # Prevenir conversiones implícitas
        validate_assignment=True,  # Validar en asignación
        extra="forbid",  # Prohibir campos extra
        str_strip_whitespace=True,  # Limpiar espacios en strings
        use_enum_values=True,  # Usar valores de enum
    )

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTCUSDT)")
    asset_class: AssetClass = Field(..., description="Asset class category")
    quantity: Decimal = Field(..., description="Position quantity (positive=long, negative=short)")
    avg_price: Decimal = Field(..., description="Average entry price")
    market_price: Decimal = Field(..., description="Current market price")
    unrealized_pnl: Decimal = Field(..., description="Unrealized profit/loss")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized profit/loss")
    currency: str = Field(default="USD", description="Position currency")
    sector: Optional[str] = Field(
        default=None, description="Sector classification (e.g., technology, energy, healthcare)"
    )
    country: Optional[str] = Field(
        default=None, description="Country or region code (e.g., US, UK, JP, EU)"
    )
    broker: str = Field(..., description="Broker identifier")
    hedging: HedgingMetadata = Field(
        default_factory=HedgingMetadata, description="Currency hedging metadata"
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v) -> Decimal:
        """Validate quantity is non-zero."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Quantity must be a number")

        if v == 0:
            raise ValueError("Position quantity cannot be zero")

        if v > Decimal("1000000"):  # 1M shares limit
            raise ValueError(f"Quantity exceeds maximum limit of 1M shares, got {v}")
        if v < Decimal("-1000000"):  # -1M shares limit
            raise ValueError(f"Quantity below minimum limit of -1M shares, got {v}")

        return v

    @field_validator("avg_price", "market_price")
    @classmethod
    def validate_prices(cls, v) -> Decimal:
        """Validate prices are positive."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Price must be a number")

        if v <= 0:
            raise ValueError(f"Price must be positive, got {v}")
        if v > Decimal("1000000"):  # $1M per share limit
            raise ValueError(f"Price exceeds maximum limit of $1M, got {v}")

        return v

    @field_validator("unrealized_pnl", "realized_pnl")
    @classmethod
    def validate_pnl(cls, v) -> Decimal:
        """Validate P&L fields."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("P&L must be a number")

        if v > Decimal("1000000000"):  # $1B limit
            raise ValueError(f"P&L exceeds maximum limit of $1B, got {v}")
        if v < Decimal("-1000000000"):  # -$1B limit
            raise ValueError(f"P&L below minimum limit of -$1B, got {v}")

        return v

    @model_validator(mode="after")
    def validate_position_consistency(self) -> "Position":
        """Validate position consistency rules."""
        # Validate quantity and prices are consistent
        if self.quantity != 0 and self.avg_price <= 0:
            raise ValueError("Average price must be positive for non-zero positions")

        if self.quantity != 0 and self.market_price <= 0:
            raise ValueError("Market price must be positive for non-zero positions")

        # Validate unrealized P&L calculation
        if self.quantity != 0:
            from app.core.centralized_config import get_config
            cfg = get_config()
            tolerance = Decimal(str(getattr(cfg.trading, 'portfolio_pnl_tolerance', 0.01)))
            expected_unrealized = self.quantity * (self.market_price - self.avg_price)
            if abs(self.unrealized_pnl - expected_unrealized) > tolerance:
                raise ValueError(
                    "Unrealized P&L calculation mismatch. "
                    f"Expected: {expected_unrealized}, Got: {self.unrealized_pnl}"
                )

        return self

    @property
    def market_value(self) -> Decimal:
        """Calculate current market value of the position."""
        return abs(self.quantity) * self.market_price

    @property
    def cost_basis(self) -> Decimal:
        """Calculate cost basis of the position."""
        return abs(self.quantity) * self.avg_price

    @property
    def total_pnl(self) -> Decimal:
        """Calculate total profit/loss (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def pnl_percentage(self) -> Decimal:
        """Calculate P&L as percentage of cost basis."""
        if self.cost_basis == 0:
            return Decimal("0")
        return (self.total_pnl / self.cost_basis) * 100


class Portfolio(BaseModel):
    """Represents a complete portfolio state."""

    model_config = ConfigDict(
        strict=True,  # Prevenir conversiones implícitas
        validate_assignment=True,  # Validar en asignación
        extra="forbid",  # Prohibir campos extra
        str_strip_whitespace=True,  # Limpiar espacios en strings
        use_enum_values=True,  # Usar valores de enum
    )

    portfolio_id: str = Field(default="", description="Unique portfolio identifier")
    cash: Decimal = Field(..., description="Available cash balance")
    positions: List[Position] = Field(default_factory=list, description="List of positions")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Portfolio snapshot timestamp"
    )
    broker: str = Field(..., description="Broker identifier")
    currency: str = Field(default="USD", description="Portfolio base currency")

    @field_validator("cash")
    @classmethod
    def validate_cash(cls, v):
        """Ensure cash is properly formatted as Decimal."""
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @property
    def total_equity(self) -> Decimal:
        """Calculate total portfolio equity (cash + positions value)."""
        positions_value = sum(pos.market_value for pos in self.positions)
        return self.cash + positions_value

    @property
    def total_value(self) -> Decimal:
        """Calculate total portfolio value (alias for total_equity)."""
        return self.total_equity

    @property
    def total_pnl(self) -> Decimal:
        """Calculate total portfolio P&L."""
        return sum(pos.total_pnl for pos in self.positions)

    @property
    def total_pnl_percentage(self) -> Decimal:
        """Calculate total P&L as percentage of total equity."""
        if self.total_equity == 0:
            return Decimal("0")
        return (self.total_pnl / self.total_equity) * 100

    @property
    def positions_by_asset_class(self) -> dict:
        """Group positions by asset class."""
        grouped = {}
        for position in self.positions:
            if position.asset_class not in grouped:
                grouped[position.asset_class] = []
            grouped[position.asset_class].append(position)
        return grouped


class MarketRegime(str, Enum):
    """Market regime enumeration for strategy adaptation."""

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class MarketRegimeData(BaseModel):
    """Market regime detection data."""

    regime: MarketRegime = Field(..., description="Detected market regime")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level (0-1)")
    atr_ratio: float = Field(..., description="ATR to price ratio")
    trend_strength: float = Field(..., description="Trend strength indicator")
    volatility_level: float = Field(..., description="Volatility level indicator")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Detection timestamp")


class AssetUniverse(BaseModel):
    """Defines supported assets for a specific broker."""

    broker: str = Field(..., description="Broker identifier")
    asset_class: AssetClass = Field(..., description="Asset class")
    symbols: List[str] = Field(..., description="List of supported symbols")
    min_volume: Optional[Decimal] = Field(None, description="Minimum daily volume requirement")
    max_spread: Optional[Decimal] = Field(None, description="Maximum bid-ask spread")

    def is_supported(self, symbol: str) -> bool:
        """Check if a symbol is supported in this universe."""
        return symbol.upper() in [s.upper() for s in self.symbols]


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit breaker triggered
    HALF_OPEN = "half_open"  # Testing if issue is resolved


class CircuitBreaker(BaseModel):
    """Circuit breaker for error handling and risk management."""

    name: str = Field(..., description="Circuit breaker identifier")
    state: CircuitBreakerState = Field(
        default=CircuitBreakerState.CLOSED, description="Current state"
    )
    error_count: int = Field(default=0, description="Consecutive error count")
    max_errors: int = Field(default=3, description="Maximum errors before triggering")
    last_error_time: Optional[datetime] = Field(None, description="Last error timestamp")
    last_success_time: Optional[datetime] = Field(None, description="Last success timestamp")
    cooldown_seconds: int = Field(default=300, description="Cooldown period in seconds")
    success_count: int = Field(default=0, description="Consecutive success count")
    success_threshold: int = Field(
        default=3, description="Success count needed to close circuit breaker"
    )

    def should_trigger(self) -> bool:
        """Check if circuit breaker should trigger."""
        return self.error_count >= self.max_errors

    def should_close(self):
        """Check if circuit breaker should close (half-open to closed)."""
        return self.success_count >= self.success_threshold

    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.error_count = 0
        self.last_error_time = None
        self.success_count = 0

    def record_error(self):
        """Record an error and update circuit breaker state."""
        self.error_count += 1
        self.last_error_time = datetime.utcnow()
        self.success_count = 0

        if self.should_trigger():
            self.state = CircuitBreakerState.OPEN

    def record_success(self):
        """Record a success and update circuit breaker state."""
        self.success_count += 1
        self.last_success_time = datetime.utcnow()

        if self.state == CircuitBreakerState.HALF_OPEN and self.success_count >= 2:
            self.state = CircuitBreakerState.CLOSED
            self.error_count = 0
        elif self.state == CircuitBreakerState.OPEN:
            self.state = CircuitBreakerState.HALF_OPEN

    def should_trip(self) -> bool:
        """Check if circuit breaker should trip (alias for should_trigger)."""
        return self.should_trigger()


class PortfolioProvider(Protocol):
    """Protocol for portfolio data providers."""

    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio state."""
        ...

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get specific position by symbol."""
        ...

    async def get_asset_universe(self) -> List[AssetUniverse]:
        """Get supported asset universe for this provider."""
        ...

    async def get_market_regime(self, symbol: str) -> Optional[MarketRegimeData]:
        """Get market regime data for a symbol."""
        ...


class TradingClientInterface(Protocol):
    """Common interface for all trading clients."""

    async def place_order(
        self, symbol: str, quantity: Decimal, price: Optional[Decimal] = None
    ) -> str:
        """Place a trading order."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        ...

    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        ...

    async def get_market_data(self, symbol: str) -> dict:
        """Get current market data for a symbol."""
        ...

    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio state."""
        ...
