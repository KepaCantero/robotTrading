"""
Market Data Models for Real-time Trading

This module defines models for market data feeds, quotes, and real-time data
for the algorithmic trading system.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)


class DataFeedType(str, Enum):
    """Market data feed types."""

    ALPHA_VANTAGE = "alpha_vantage"
    YAHOO_FINANCE = "yahoo_finance"
    IBKR_TWS = "ibkr_tws"
    BINANCE = "binance"
    MOCK = "mock"


class DataFrequency(str, Enum):
    """Data update frequency."""

    REAL_TIME = "real_time"
    SECOND = "1s"
    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    HOURLY = "1h"
    DAILY = "1d"


class MarketDataStatus(str, Enum):
    """Market data status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SUSPENDED = "suspended"


class Quote(BaseModel):
    """Real-time market quote."""

    model_config = ConfigDict(
        strict=True,  # Prevenir conversiones implícitas
        validate_assignment=True,  # Validar en asignación
        extra="forbid",  # Prohibir campos extra
        str_strip_whitespace=True,  # Limpiar espacios en strings
        use_enum_values=True,  # Usar valores de enum
    )

    id: UUID = Field(default_factory=uuid4, description="Unique quote identifier")
    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Quote timestamp"
    )

    # Price data
    bid: Decimal = Field(..., gt=0, description="Bid price")
    ask: Decimal = Field(..., gt=0, description="Ask price")
    last: Decimal = Field(..., gt=0, description="Last traded price")
    open: Decimal = Field(
        default_factory=lambda: Decimal("0"), ge=0, description="Opening price"
    )
    high: Decimal = Field(
        default_factory=lambda: Decimal("0"), ge=0, description="High price"
    )
    low: Decimal = Field(
        default_factory=lambda: Decimal("0"), ge=0, description="Low price"
    )
    close: Decimal = Field(
        default_factory=lambda: Decimal("0"), ge=0, description="Closing price"
    )

    # Volume and spread
    volume: Decimal = Field(..., ge=0, description="Trading volume")
    spread: Decimal = Field(
        default_factory=lambda: Decimal("0"), ge=0, description="Bid-ask spread"
    )

    # Additional metrics
    change: Decimal = Field(default=Decimal("0"), description="Price change")
    change_percent: Decimal = Field(
        default=Decimal("0"), description="Price change percentage"
    )
    volatility: Optional[Decimal] = Field(None, ge=0, description="Price volatility")

    # Metadata
    feed_type: DataFeedType = Field(
        default=DataFeedType.MOCK, description="Data feed source"
    )
    status: MarketDataStatus = Field(
        default=MarketDataStatus.ACTIVE, description="Quote status"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("bid", "ask", "last")
    @classmethod
    def validate_required_price_fields(cls, v) -> Decimal:
        """Validate required price fields are positive and within reasonable limits."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Price fields must be numbers")

        if v <= 0:
            raise ValueError(f"Required price fields must be positive, got {v}")
        if v > Decimal("1000000"):  # $1M limit
            raise ValueError(f"Price exceeds maximum limit of $1M, got {v}")

        return v

    @field_validator("open", "high", "low", "close")
    @classmethod
    def validate_optional_price_fields(cls, v) -> Decimal:
        """Validate optional price fields are non-negative and within reasonable limits."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Price fields must be numbers")

        if v < 0:
            raise ValueError(f"Price fields must be non-negative, got {v}")
        if v > Decimal("1000000"):  # $1M limit
            raise ValueError(f"Price exceeds maximum limit of $1M, got {v}")

        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v) -> Decimal:
        """Validate volume is non-negative and within reasonable limits."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Volume must be a number")

        if v < 0:
            raise ValueError(f"Volume must be non-negative, got {v}")
        if v > Decimal("1000000000"):  # 1B shares limit
            raise ValueError(f"Volume exceeds maximum limit of 1B shares, got {v}")

        return v

    @field_validator("spread")
    @classmethod
    def validate_spread(cls, v) -> Decimal:
        """Validate spread is non-negative and reasonable."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Spread must be a number")

        if v < 0:
            raise ValueError(f"Spread must be non-negative, got {v}")
        if v > Decimal("1000"):  # $1000 spread limit
            raise ValueError(f"Spread exceeds maximum limit of $1000, got {v}")

        return v

    @model_validator(mode="after")
    def validate_quote_consistency(self) -> "Quote":
        """Validate consistency between price fields."""
        if self.high < self.low:
            raise ValueError(
                f"High price ({self.high}) cannot be less than low price ({self.low})."
            )

        if not (self.low <= self.open <= self.high):
            raise ValueError(
                f"Open price ({self.open}) must be between low ({self.low}) and high ({self.high})."
            )

        if not (self.low <= self.close <= self.high):
            raise ValueError(
                f"Close price ({self.close}) must be between low ({self.low}) and high ({self.high})."
            )

        if self.bid > self.ask:
            raise ValueError(
                f"Bid price ({self.bid}) must be less than or equal to ask price ({self.ask})."
            )

        # Auto-calculate spread if not provided or if it doesn't match
        calculated_spread = self.ask - self.bid
        if self.spread == 0 and calculated_spread > 0:
            self.spread = calculated_spread
        elif self.spread != calculated_spread and self.spread != 0:
            raise ValueError(
                f"Calculated spread ({calculated_spread}) does not match provided spread ({self.spread})."
            )

        return self


class HistoricalData(BaseModel):
    """Historical market data."""

    id: UUID = Field(default_factory=uuid4, description="Unique data identifier")
    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(..., description="Data timestamp")

    # OHLCV data
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="High price")
    low: Decimal = Field(..., gt=0, description="Low price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: Decimal = Field(..., ge=0, description="Trading volume")

    # Additional metrics
    adjusted_close: Optional[Decimal] = Field(
        None, gt=0, description="Adjusted closing price"
    )
    dividend_amount: Optional[Decimal] = Field(
        None, ge=0, description="Dividend amount"
    )
    split_coefficient: Optional[Decimal] = Field(
        None, gt=0, description="Stock split coefficient"
    )

    # Metadata
    feed_type: DataFeedType = Field(..., description="Data feed source")
    frequency: DataFrequency = Field(..., description="Data frequency")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("open", "high", "low", "close", "adjusted_close")
    @classmethod
    def validate_price_fields(cls, v) -> Decimal:
        """Validate price fields are positive."""
        if v is None:
            return v

        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Price fields must be numbers")

        if v <= 0:
            raise ValueError(f"Price fields must be positive, got {v}")

        return v

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "HistoricalData":
        """Validate OHLC consistency."""
        if self.high < self.low:
            raise ValueError(
                f"High price ({self.high}) cannot be less than low price ({self.low})."
            )

        if not (self.low <= self.open <= self.high):
            raise ValueError(
                f"Open price ({self.open}) must be between low ({self.low}) and high ({self.high})."
            )

        if not (self.low <= self.close <= self.high):
            raise ValueError(
                f"Close price ({self.close}) must be between low ({self.low}) and high ({self.high})."
            )

        return self


class DataFeedConfig(BaseModel):
    """Configuration for market data feeds."""

    id: UUID = Field(default_factory=uuid4, description="Unique config identifier")
    name: str = Field(..., description="Feed configuration name")
    feed_type: DataFeedType = Field(..., description="Type of data feed")

    # API configuration
    api_key: Optional[str] = Field(None, description="API key for the feed")
    base_url: str = Field(..., description="Base URL for the API")
    rate_limit: int = Field(
        default=60, ge=1, le=3600, description="Rate limit per minute"
    )

    # Data configuration
    supported_symbols: List[str] = Field(
        default_factory=list, description="Supported trading symbols"
    )
    supported_frequencies: List[DataFrequency] = Field(
        default_factory=list, description="Supported data frequencies"
    )
    max_history_days: int = Field(
        default=365, ge=1, le=3650, description="Maximum historical data days"
    )

    # Connection settings
    timeout_seconds: int = Field(
        default=30, ge=1, le=300, description="Request timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3, ge=0, le=10, description="Number of retry attempts"
    )
    retry_delay: float = Field(
        default=1.0, ge=0.1, le=60.0, description="Delay between retries in seconds"
    )

    # Status
    is_active: bool = Field(default=True, description="Whether the feed is active")
    last_updated: Optional[datetime] = Field(None, description="Last successful update")
    error_count: int = Field(
        default=0, ge=0, description="Number of consecutive errors"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional configuration metadata"
    )


class MarketDataSubscription(BaseModel):
    """Market data subscription."""

    id: UUID = Field(
        default_factory=uuid4, description="Unique subscription identifier"
    )
    symbol: str = Field(..., description="Trading symbol to subscribe to")
    feed_config_id: UUID = Field(..., description="Data feed configuration ID")

    # Subscription settings
    frequency: DataFrequency = Field(
        default=DataFrequency.REAL_TIME, description="Data update frequency"
    )
    is_active: bool = Field(default=True, description="Whether subscription is active")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Subscription creation time"
    )
    last_update: Optional[datetime] = Field(None, description="Last data update")
    expires_at: Optional[datetime] = Field(
        None, description="Subscription expiration time"
    )

    # Statistics
    total_updates: int = Field(
        default=0, ge=0, description="Total number of updates received"
    )
    error_count: int = Field(
        default=0, ge=0, description="Number of errors encountered"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional subscription metadata"
    )


class MarketDataCache(BaseModel):
    """Cached market data."""

    id: UUID = Field(default_factory=uuid4, description="Unique cache identifier")
    symbol: str = Field(..., description="Trading symbol")
    data_type: str = Field(..., description="Type of cached data (quote, historical)")

    # Cache data
    data: Any = Field(..., description="Cached market data (can be dict or list)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Cache timestamp"
    )

    # Cache settings
    ttl_seconds: int = Field(
        default=60, ge=1, le=3600, description="Time to live in seconds"
    )
    is_expired: bool = Field(default=False, description="Whether cache is expired")

    # Metadata
    feed_type: DataFeedType = Field(..., description="Data feed source")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional cache metadata"
    )

    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self.is_expired:
            return False

        age_seconds = (datetime.utcnow() - self.timestamp).total_seconds()
        return age_seconds < self.ttl_seconds
