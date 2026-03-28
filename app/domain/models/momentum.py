"""
Momentum strategy models for AlgoTrading system.

This module defines the data models for momentum trading strategies,
technical indicators, and momentum signals.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class MomentumType(str, Enum):
    """Momentum strategy types."""

    PRICE_MOMENTUM = "price_momentum"
    VOLUME_MOMENTUM = "volume_momentum"
    VOLATILITY_MOMENTUM = "volatility_momentum"
    COMBINED_MOMENTUM = "combined_momentum"


class Timeframe(str, Enum):
    """Trading timeframes."""

    DAILY = "1d"
    HOURLY = "1h"
    FOUR_HOUR = "4h"
    WEEKLY = "1w"


class TechnicalIndicator(str, Enum):
    """Technical indicators for momentum analysis."""

    RSI = "rsi"
    EMA = "ema"
    MACD = "macd"
    STOCHASTIC = "stochastic"
    BOLLINGER_BANDS = "bollinger_bands"
    ATR = "atr"
    VOLUME_SMA = "volume_sma"


class MomentumSignal(BaseModel):
    """Momentum trading signal."""

    symbol: str = Field(..., description="Asset symbol")
    signal_type: MomentumType = Field(..., description="Type of momentum signal")
    timeframe: Timeframe = Field(default=Timeframe.DAILY, description="Trading timeframe")

    # Signal strength and direction
    strength: float = Field(ge=0, le=100, description="Signal strength (0-100)")
    direction: str = Field(..., description="Signal direction (BUY/SELL)")
    confidence: float = Field(ge=0, le=100, description="Signal confidence (0-100)")

    # Technical indicators
    rsi: Optional[float] = Field(None, ge=0, le=100, description="RSI value")
    ema_short: Optional[float] = Field(None, ge=0, description="Short EMA value")
    ema_long: Optional[float] = Field(None, ge=0, description="Long EMA value")
    macd: Optional[float] = Field(None, description="MACD value")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    macd_divergence: Optional[str] = Field(
        None, description="TASK-IND-3: MACD divergence detected (bullish/bearish)"
    )

    # Price and volume data
    current_price: Decimal = Field(ge=0, description="Current asset price")
    price_change: Decimal = Field(description="Price change from previous period")
    price_change_pct: float = Field(description="Price change percentage")
    volume: Decimal = Field(ge=0, description="Current volume")
    volume_change: Decimal = Field(description="Volume change from previous period")
    volume_change_pct: float = Field(description="Volume change percentage")

    # Volatility metrics
    atr: Optional[Decimal] = Field(None, ge=0, description="Average True Range")
    volatility: Optional[float] = Field(None, ge=0, description="Price volatility")

    # Signal metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Signal timestamp")
    expires_at: datetime = Field(description="Signal expiration time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if not v or len(v.strip()) == 0:
            logger.error("MomentumSignal validation failed: empty symbol")
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        """Validate signal direction."""
        if v.upper() not in ["BUY", "SELL"]:
            logger.error(
                "MomentumSignal validation failed: invalid direction", extra={"direction": v}
            )
            raise ValueError("Direction must be BUY or SELL")
        return v.upper()

    @property
    def is_expired(self) -> bool:
        """Check if signal is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def time_to_expiry(self) -> timedelta:
        """Get time until signal expires."""
        return self.expires_at - datetime.utcnow()

    @property
    def momentum_score(self) -> float:
        """Calculate combined momentum score."""
        # Weight different components
        price_weight = 0.4
        volume_weight = 0.3
        technical_weight = 0.3

        # Price momentum score
        price_score = min(100, max(0, abs(self.price_change_pct) * 10))

        # Volume momentum score
        volume_score = min(100, max(0, abs(self.volume_change_pct) * 5))

        # Technical momentum score (based on RSI and MACD)
        technical_score = 0
        if self.rsi is not None:
            if (self.direction == "BUY" and self.rsi < 30) or (self.direction == "SELL" and self.rsi > 70):
                technical_score += 30  # Oversold/Overbought

        if self.macd_histogram is not None:
            if (self.direction == "BUY" and self.macd_histogram > 0) or (self.direction == "SELL" and self.macd_histogram < 0):
                technical_score += 20  # Bullish/Bearish MACD

        return (
            price_score * price_weight
            + volume_score * volume_weight
            + technical_score * technical_weight
        )


class MarketData(BaseModel):
    """Market data for signal evaluation."""

    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the market data"
    )
    open_price: Decimal = Field(..., gt=0, description="Opening price")
    high_price: Decimal = Field(..., gt=0, description="Highest price")
    low_price: Decimal = Field(..., gt=0, description="Lowest price")
    close_price: Decimal = Field(..., gt=0, description="Closing price")
    volume: Decimal = Field(..., ge=0, description="Trading volume")
    bid: Decimal = Field(..., gt=0, description="Current bid price")
    ask: Decimal = Field(..., gt=0, description="Current ask price")
    spread: Decimal = Field(..., ge=0, description="Bid-ask spread")

    @field_validator("open_price", "high_price", "low_price", "close_price", "bid", "ask")
    @classmethod
    def validate_price_fields(cls, v) -> Decimal:
        """Ensure price fields are positive and within reasonable limits."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            logger.error("MarketData validation failed: invalid price type")
            raise ValueError("Price fields must be numbers")

        if v <= 0:
            logger.error(
                "MarketData validation failed: non-positive price", extra={"price": str(v)}
            )
            raise ValueError(f"Price fields must be positive, got {v}")
        if v > Decimal("1000000"):  # $1M limit
            logger.error(
                "MarketData validation failed: price exceeds limit",
                extra={"price": str(v), "limit": "1000000"},
            )
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

    @field_validator("bid", "ask")
    @classmethod
    def validate_bid_ask(cls, v) -> Decimal:
        """Validate bid and ask prices are positive."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Bid/Ask prices must be numbers")

        if v <= 0:
            raise ValueError(f"Bid/Ask prices must be positive, got {v}")

        return v

    @model_validator(mode="after")
    def validate_price_consistency(self) -> "MarketData":
        """Validate consistency between high, low, open, and close prices."""
        logger.debug("Validating market data price consistency", extra={"symbol": self.symbol})
        if self.high_price < self.low_price:
            logger.error(
                "MarketData validation failed: high < low",
                extra={
                    "symbol": self.symbol,
                    "high_price": str(self.high_price),
                    "low_price": str(self.low_price),
                },
            )
            raise ValueError(
                f"High price ({self.high_price}) cannot be less than low price ({self.low_price})."
            )

        if not (self.low_price <= self.open_price <= self.high_price):
            logger.error(
                "MarketData validation failed: open price outside range",
                extra={
                    "symbol": self.symbol,
                    "open_price": str(self.open_price),
                    "low_price": str(self.low_price),
                    "high_price": str(self.high_price),
                },
            )
            raise ValueError(
                f"Open price ({self.open_price}) must be between low ({self.low_price}) and high ({self.high_price})."
            )

        if not (self.low_price <= self.close_price <= self.high_price):
            logger.error(
                "MarketData validation failed: close price outside range",
                extra={
                    "symbol": self.symbol,
                    "close_price": str(self.close_price),
                    "low_price": str(self.low_price),
                    "high_price": str(self.high_price),
                },
            )
            raise ValueError(
                f"Close price ({self.close_price}) must be between low ({self.low_price}) and high ({self.high_price})."
            )

        if self.bid >= self.ask:
            logger.error(
                "MarketData validation failed: bid >= ask",
                extra={"symbol": self.symbol, "bid": str(self.bid), "ask": str(self.ask)},
            )
            raise ValueError(f"Bid price ({self.bid}) must be less than ask price ({self.ask}).")

        if self.ask - self.bid != self.spread:
            logger.error(
                "MarketData validation failed: spread mismatch",
                extra={
                    "symbol": self.symbol,
                    "calculated_spread": str(self.ask - self.bid),
                    "provided_spread": str(self.spread),
                },
            )
            raise ValueError(
                f"Calculated spread ({self.ask - self.bid}) does not match provided spread ({self.spread})."
            )

        if self.spread < 0:
            logger.error(
                "MarketData validation failed: negative spread",
                extra={"symbol": self.symbol, "spread": str(self.spread)},
            )
            raise ValueError(f"Spread cannot be negative, got {self.spread}")

        if self.spread > self.ask * Decimal("0.1"):  # 10% spread limit
            logger.error(
                "MarketData validation failed: excessive spread",
                extra={"symbol": self.symbol, "spread": str(self.spread), "ask": str(self.ask)},
            )
            raise ValueError(
                f"Excessive spread ({self.spread}) detected for ask price ({self.ask})."
            )

        logger.debug("MarketData validation passed", extra={"symbol": self.symbol})
        return self


class TechnicalIndicators(BaseModel):
    """Technical indicators for an asset."""

    symbol: str = Field(..., description="Asset symbol")
    timeframe: Timeframe = Field(default=Timeframe.DAILY, description="Timeframe")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Calculation timestamp"
    )

    # Price indicators
    rsi: Optional[float] = Field(None, ge=0, le=100, description="Relative Strength Index")
    ema_9: Optional[float] = Field(None, ge=0, description="9-period EMA")
    ema_21: Optional[float] = Field(None, ge=0, description="21-period EMA")
    ema_50: Optional[float] = Field(None, ge=0, description="50-period EMA")
    ema_200: Optional[float] = Field(None, ge=0, description="200-period EMA")

    # MACD indicators
    macd: Optional[float] = Field(None, description="MACD line")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")

    # Stochastic indicators
    stoch_k: Optional[float] = Field(None, ge=0, le=100, description="Stochastic %K")
    stoch_d: Optional[float] = Field(None, ge=0, le=100, description="Stochastic %D")

    # Bollinger Bands
    bb_upper: Optional[float] = Field(None, ge=0, description="Bollinger Band upper")
    bb_middle: Optional[float] = Field(None, ge=0, description="Bollinger Band middle")
    bb_lower: Optional[float] = Field(None, ge=0, description="Bollinger Band lower")
    bb_width: Optional[float] = Field(None, ge=0, description="Bollinger Band width")

    # Volatility indicators
    atr: Optional[float] = Field(None, ge=0, description="Average True Range")
    adx: Optional[float] = Field(
        None, ge=0, le=100, description="Average Directional Index (>25=strong trend)"
    )
    volatility: Optional[float] = Field(None, ge=0, description="Price volatility")

    # Volume indicators
    volume_sma_20: Optional[Decimal] = Field(None, ge=0, description="20-period volume SMA")
    volume_ratio: Optional[float] = Field(None, ge=0, description="Volume ratio vs average")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format."""
        return v.strip().upper()

    @property
    def ema_trend(self) -> Optional[str]:
        """Determine EMA trend."""
        if not all([self.ema_9, self.ema_21, self.ema_50]):
            return None

        if self.ema_9 > self.ema_21 > self.ema_50:
            return "BULLISH"
        elif self.ema_9 < self.ema_21 < self.ema_50:
            return "BEARISH"
        else:
            return "NEUTRAL"

    @property
    def rsi_signal(self) -> Optional[str]:
        """Determine RSI signal."""
        if self.rsi is None:
            return None

        if self.rsi < 30:
            return "OVERSOLD"
        elif self.rsi > 70:
            return "OVERBOUGHT"
        else:
            return "NEUTRAL"

    @property
    def macd_signal_indicator(self) -> Optional[str]:
        """Determine MACD signal."""
        if self.macd_histogram is None:
            return None

        if self.macd_histogram > 0:
            return "BULLISH"
        elif self.macd_histogram < 0:
            return "BEARISH"
        else:
            return "NEUTRAL"


class MomentumStrategy(BaseModel):
    """Momentum trading strategy configuration."""

    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    momentum_type: MomentumType = Field(..., description="Type of momentum strategy")
    timeframe: Timeframe = Field(default=Timeframe.DAILY, description="Trading timeframe")

    # Signal parameters
    min_strength: float = Field(default=60.0, ge=0, le=100, description="Minimum signal strength")
    min_confidence: float = Field(
        default=70.0, ge=0, le=100, description="Minimum signal confidence"
    )
    signal_duration: int = Field(default=24, ge=1, description="Signal duration in hours")

    # Technical indicator thresholds
    rsi_oversold: float = Field(default=30.0, ge=0, le=100, description="RSI oversold threshold")
    rsi_overbought: float = Field(
        default=70.0, ge=0, le=100, description="RSI overbought threshold"
    )
    ema_short_period: int = Field(default=9, ge=1, description="Short EMA period")
    ema_long_period: int = Field(default=21, ge=1, description="Long EMA period")

    # Volume requirements
    min_volume_ratio: float = Field(default=1.2, ge=0, description="Minimum volume ratio")
    volume_spike_threshold: float = Field(default=2.0, ge=0, description="Volume spike threshold")

    # Risk management
    max_position_size: float = Field(default=0.1, ge=0, le=1, description="Maximum position size")
    stop_loss_pct: float = Field(default=0.05, ge=0, le=1, description="Stop loss percentage")
    take_profit_pct: float = Field(default=0.15, ge=0, le=1, description="Take profit percentage")

    # Strategy status
    is_active: bool = Field(default=True, description="Whether strategy is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate strategy name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Strategy name cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        """Validate strategy description."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Strategy description cannot be empty")
        return v.strip()

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class MomentumAnalysis(BaseModel):
    """Comprehensive momentum analysis for an asset."""

    symbol: str = Field(..., description="Asset symbol")
    timeframe: Timeframe = Field(default=Timeframe.DAILY, description="Analysis timeframe")
    analysis_date: datetime = Field(default_factory=datetime.utcnow, description="Analysis date")

    # Technical indicators
    indicators: TechnicalIndicators = Field(..., description="Technical indicators")

    # Momentum signals
    signals: List[MomentumSignal] = Field(default_factory=list, description="Generated signals")

    # Analysis results
    overall_momentum: float = Field(ge=0, le=100, description="Overall momentum score")
    trend_direction: str = Field(description="Trend direction (BULLISH/BEARISH/NEUTRAL)")
    signal_count: int = Field(default=0, ge=0, description="Number of active signals")

    # Risk assessment
    risk_level: str = Field(description="Risk level (LOW/MEDIUM/HIGH)")
    volatility_level: str = Field(description="Volatility level (LOW/MEDIUM/HIGH)")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format."""
        return v.strip().upper()

    @field_validator("trend_direction")
    @classmethod
    def validate_trend_direction(cls, v):
        """Validate trend direction."""
        if v.upper() not in ["BULLISH", "BEARISH", "NEUTRAL"]:
            raise ValueError("Trend direction must be BULLISH, BEARISH, or NEUTRAL")
        return v.upper()

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v):
        """Validate risk level."""
        if v.upper() not in ["LOW", "MEDIUM", "HIGH"]:
            raise ValueError("Risk level must be LOW, MEDIUM, or HIGH")
        return v.upper()

    @field_validator("volatility_level")
    @classmethod
    def validate_volatility_level(cls, v):
        """Validate volatility level."""
        if v.upper() not in ["LOW", "MEDIUM", "HIGH"]:
            raise ValueError("Volatility level must be LOW, MEDIUM, or HIGH")
        return v.upper()

    def add_signal(self, signal: MomentumSignal):
        """Add a momentum signal to the analysis."""
        logger.info(
            "Adding momentum signal to analysis",
            extra={
                "symbol": self.symbol,
                "signal_type": signal.signal_type.value,
                "direction": signal.direction,
                "strength": signal.strength,
            },
        )
        self.signals.append(signal)
        self.signal_count = len(self.signals)

    def get_active_signals(self) -> List[MomentumSignal]:
        """Get active (non-expired) signals."""
        return [signal for signal in self.signals if not signal.is_expired]

    def get_signals_by_type(self, signal_type: MomentumType) -> List[MomentumSignal]:
        """Get signals by type."""
        return [signal for signal in self.signals if signal.signal_type == signal_type]


class MomentumFilter(BaseModel):
    """Filter criteria for momentum analysis."""

    symbols: Optional[List[str]] = Field(None, description="Filter by symbols")
    momentum_types: Optional[List[MomentumType]] = Field(
        None, description="Filter by momentum types"
    )
    timeframes: Optional[List[Timeframe]] = Field(None, description="Filter by timeframes")
    min_strength: float = Field(default=50.0, ge=0, le=100, description="Minimum signal strength")
    min_confidence: float = Field(
        default=60.0, ge=0, le=100, description="Minimum signal confidence"
    )
    active_only: bool = Field(default=True, description="Only active signals")
    max_age_hours: int = Field(default=24, ge=1, description="Maximum signal age in hours")

    def matches(self, signal: MomentumSignal) -> bool:
        """Check if signal matches filter criteria."""
        logger.debug(
            "Checking signal against filter",
            extra={
                "signal_symbol": signal.symbol,
                "signal_strength": signal.strength,
                "signal_confidence": signal.confidence,
            },
        )
        if self.symbols and signal.symbol not in self.symbols:
            return False

        if self.momentum_types and signal.signal_type not in self.momentum_types:
            return False

        if self.timeframes and signal.timeframe not in self.timeframes:
            return False

        if signal.strength < self.min_strength:
            return False

        if signal.confidence < self.min_confidence:
            return False

        if self.active_only and signal.is_expired:
            return False

        if self.max_age_hours:
            age_hours = (datetime.utcnow() - signal.timestamp).total_seconds() / 3600
            if age_hours > self.max_age_hours:
                return False

        logger.debug("Signal matches filter criteria", extra={"signal_symbol": signal.symbol})
        return True
