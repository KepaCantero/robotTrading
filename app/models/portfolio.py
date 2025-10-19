"""
Portfolio Provider Interface and Models

This module defines the core interfaces and models for portfolio management
across different brokers (IBKR, Binance, Paper Trading).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Protocol
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AssetClass(str, Enum):
    """Asset class enumeration for portfolio categorization."""
    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    BOND = "bond"


class Position(BaseModel):
    """Represents a single position in the portfolio."""
    
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTCUSDT)")
    asset_class: AssetClass = Field(..., description="Asset class category")
    quantity: Decimal = Field(..., description="Position quantity (positive=long, negative=short)")
    avg_price: Decimal = Field(..., description="Average entry price")
    market_price: Decimal = Field(..., description="Current market price")
    unrealized_pnl: Decimal = Field(..., description="Unrealized profit/loss")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized profit/loss")
    currency: str = Field(default="USD", description="Position currency")
    broker: str = Field(..., description="Broker identifier")
    
    @field_validator('quantity', 'avg_price', 'market_price', 'unrealized_pnl', 'realized_pnl')
    @classmethod
    def validate_decimal_fields(cls, v):
        """Ensure decimal fields are properly formatted."""
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
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
    
    cash: Decimal = Field(..., description="Available cash balance")
    positions: List[Position] = Field(default_factory=list, description="List of positions")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Portfolio snapshot timestamp")
    broker: str = Field(..., description="Broker identifier")
    currency: str = Field(default="USD", description="Portfolio base currency")
    
    @field_validator('cash')
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
    OPEN = "open"      # Circuit breaker triggered
    HALF_OPEN = "half_open"  # Testing if issue is resolved


class CircuitBreaker(BaseModel):
    """Circuit breaker for error handling and risk management."""
    
    name: str = Field(..., description="Circuit breaker identifier")
    state: CircuitBreakerState = Field(default=CircuitBreakerState.CLOSED, description="Current state")
    error_count: int = Field(default=0, description="Consecutive error count")
    max_errors: int = Field(default=3, description="Maximum errors before triggering")
    last_error_time: Optional[datetime] = Field(None, description="Last error timestamp")
    cooldown_seconds: int = Field(default=300, description="Cooldown period in seconds")
    
    def should_trigger(self) -> bool:
        """Check if circuit breaker should trigger."""
        return self.error_count >= self.max_errors
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.error_count = 0
        self.last_error_time = None


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
    
    async def place_order(self, symbol: str, quantity: Decimal, price: Optional[Decimal] = None) -> str:
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
