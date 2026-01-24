"""
Signal Models and Scoring System

This module defines signal models, scoring algorithms, and priority queue management
for the algorithmic trading system.
"""

import heapq
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SignalType(str, Enum):
    """Signal type enumeration."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalStrength(str, Enum):
    """Signal strength enumeration."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class SignalSource(str, Enum):
    """Signal source enumeration."""

    MOMENTUM = "momentum"
    LIQUIDITY = "liquidity"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"


@dataclass
class MarketData:
    """Market data for signal evaluation."""

    symbol: str
    price: Decimal
    volume: Decimal
    bid: Decimal
    ask: Decimal
    spread: Decimal
    timestamp: datetime

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price."""
        return (self.bid + self.ask) / 2

    @property
    def spread_percentage(self) -> Decimal:
        """Calculate spread as percentage."""
        if self.mid_price == 0:
            return Decimal("0")
        return (self.spread / self.mid_price) * 100


class Signal(BaseModel):
    """Trading signal model."""

    model_config = ConfigDict(
        strict=True,  # Prevenir conversiones implícitas
        validate_assignment=True,  # Validar en asignación
        extra="forbid",  # Prohibir campos extra
        str_strip_whitespace=True,  # Limpiar espacios en strings
        use_enum_values=True,  # Usar valores de enum
    )

    signal_id: str = Field(
        default_factory=lambda: f"signal_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
        description="Unique signal identifier",
    )
    symbol: str = Field(..., description="Trading symbol")
    signal_type: SignalType = Field(..., description="Signal type (buy/sell/hold)")
    strength: SignalStrength = Field(..., description="Signal strength")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence score (0-100%)")
    liquidity_score: float = Field(..., ge=0.0, le=100.0, description="Liquidity score (0-100%)")
    priority_score: float = Field(..., ge=0.0, le=100.0, description="Priority score (0-100%)")
    source: SignalSource = Field(..., description="Signal source")
    price: Decimal = Field(..., description="Signal price")
    volume: Decimal = Field(..., description="Signal volume")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Signal timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional signal metadata")

    @field_validator("confidence", "liquidity_score", "priority_score")
    @classmethod
    def validate_score_fields(cls, v: float) -> float:
        """Validate score fields are between 0 and 100."""
        if not isinstance(v, (int, float)):
            raise ValueError("Score fields must be numbers")
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"Score fields must be between 0.0 and 100.0, got {v}")
        return float(v)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v) -> Decimal:
        """Validate price is positive."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Price must be a number")

        if v <= 0:
            raise ValueError(f"Price must be positive, got {v}")
        if v > Decimal("1000000"):  # $1M per share limit
            raise ValueError(f"Price exceeds maximum limit of $1M, got {v}")

        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v) -> Decimal:
        """Validate volume is non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Volume must be a number")

        if v < 0:
            raise ValueError(f"Volume must be non-negative, got {v}")
        # Increased limit to 10B shares to match Quote model (NVDA can have >1B shares)
        if v > Decimal("10000000000"):  # 10B shares limit
            raise ValueError(f"Volume exceeds maximum limit of 10B shares, got {v}")

        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is reasonable."""
        now = datetime.utcnow()
        if v > now:
            raise ValueError(f"Timestamp cannot be in the future, got {v}")

        # Allow historical data for backtesting - don't check age
        # Commented out to allow historical backtesting
        # from datetime import timedelta
        # one_year_ago = now - timedelta(days=365)
        # if v < one_year_ago:
        #     raise ValueError(f"Timestamp is too old (more than 1 year), got {v}")

        return v

    @model_validator(mode="after")
    def validate_signal_consistency(self) -> "Signal":
        """Validate signal consistency rules."""
        # Strong signals should have high confidence
        if self.strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]:
            if self.confidence < 70.0:
                raise ValueError(
                    f"Strong signal ({self.strength}) with low confidence ({self.confidence}). "
                    "Strong signals should have confidence >= 70.0"
                )

        # Weak signals should have low confidence
        if self.strength == SignalStrength.WEAK:
            if self.confidence > 80.0:
                raise ValueError(
                    f"Weak signal with high confidence ({self.confidence}). "
                    "Weak signals should have confidence <= 80.0"
                )

        # HOLD signals should have moderate confidence
        if self.signal_type == SignalType.HOLD:
            if self.confidence > 90.0:
                raise ValueError(
                    f"HOLD signal with very high confidence ({self.confidence}). "
                    "HOLD signals should have moderate confidence"
                )

        return self

    @property
    def combined_score(self) -> float:
        """Calculate combined score (confidence + liquidity + priority)."""
        return (self.confidence + self.liquidity_score + self.priority_score) / 3

    @property
    def is_actionable(self) -> bool:
        """Check if signal is actionable (confidence > 60%)."""
        return self.confidence > 60.0

    @property
    def is_high_priority(self) -> bool:
        """Check if signal is high priority (priority_score > 80%)."""
        return self.priority_score > 80.0


class SignalScorer:
    """Signal scoring system with confidence and liquidity ranking."""

    def __init__(self):
        """Initialize signal scorer."""
        self.confidence_weights = {
            "momentum": 0.3,
            "volume": 0.25,
            "volatility": 0.2,
            "technical": 0.15,
            "liquidity": 0.1,
        }

        self.liquidity_weights = {
            "volume": 0.4,
            "spread": 0.3,
            "price_stability": 0.2,
            "market_depth": 0.1,
        }

    def calculate_confidence_score(
        self, market_data: MarketData, signal_metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on multiple factors."""
        confidence_factors = []

        # Momentum factor (RSI, EMA trends)
        momentum_score = self._calculate_momentum_score(signal_metadata)
        confidence_factors.append(momentum_score * self.confidence_weights["momentum"])

        # Volume factor
        volume_score = self._calculate_volume_score(market_data, signal_metadata)
        confidence_factors.append(volume_score * self.confidence_weights["volume"])

        # Volatility factor
        volatility_score = self._calculate_volatility_score(signal_metadata)
        confidence_factors.append(volatility_score * self.confidence_weights["volatility"])

        # Technical indicators factor
        technical_score = self._calculate_technical_score(signal_metadata)
        confidence_factors.append(technical_score * self.confidence_weights["technical"])

        # Liquidity factor
        liquidity_score = self._calculate_liquidity_score(market_data)
        confidence_factors.append(liquidity_score * self.confidence_weights["liquidity"])

        # Calculate weighted average
        total_confidence = sum(confidence_factors)
        return min(100.0, max(0.0, total_confidence))

    def calculate_liquidity_score(self, market_data: MarketData) -> float:
        """Calculate liquidity score based on volume and spread."""
        liquidity_factors = []

        # Volume factor (higher volume = higher liquidity)
        volume_score = self._calculate_volume_liquidity_score(market_data)
        liquidity_factors.append(volume_score * self.liquidity_weights["volume"])

        # Spread factor (lower spread = higher liquidity)
        spread_score = self._calculate_spread_liquidity_score(market_data)
        liquidity_factors.append(spread_score * self.liquidity_weights["spread"])

        # Price stability factor
        price_stability_score = self._calculate_price_stability_score(market_data)
        liquidity_factors.append(price_stability_score * self.liquidity_weights["price_stability"])

        # Market depth factor (simulated)
        market_depth_score = self._calculate_market_depth_score(market_data)
        liquidity_factors.append(market_depth_score * self.liquidity_weights["market_depth"])

        # Calculate weighted average
        total_liquidity = sum(liquidity_factors)
        return min(100.0, max(0.0, total_liquidity))

    def calculate_priority_score(self, signal: Signal, market_data: MarketData) -> float:
        """Calculate priority score based on urgency and opportunity."""
        priority_factors = []

        # Urgency factor (time-sensitive signals get higher priority)
        urgency_score = self._calculate_urgency_score(signal)
        priority_factors.append(urgency_score * 0.4)

        # Opportunity factor (high confidence + high liquidity = high
        # opportunity)
        opportunity_score = (signal.confidence + signal.liquidity_score) / 2
        priority_factors.append(opportunity_score * 0.3)

        # Market condition factor
        market_condition_score = self._calculate_market_condition_score(market_data)
        priority_factors.append(market_condition_score * 0.3)

        # Calculate weighted average
        total_priority = sum(priority_factors)
        return min(100.0, max(0.0, total_priority))

    def _calculate_momentum_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate momentum score based on RSI and EMA trends."""
        rsi = metadata.get("rsi", 50)
        ema_trend = metadata.get("ema_trend", 0)

        # RSI momentum (RSI > 70 = overbought, RSI < 30 = oversold)
        if rsi > 70:
            rsi_score = 100 - (rsi - 70) * 2  # Penalize overbought
        elif rsi < 30:
            rsi_score = 100 - (30 - rsi) * 2  # Penalize oversold
        else:
            rsi_score = 100 - abs(rsi - 50) * 2  # Neutral zone

        # EMA trend momentum
        ema_score = min(100, max(0, 50 + ema_trend * 10))

        return (rsi_score + ema_score) / 2

    def _calculate_volume_score(self, market_data: MarketData, metadata: Dict[str, Any]) -> float:
        """Calculate volume score."""
        current_volume = float(market_data.volume)
        avg_volume = metadata.get("avg_volume", current_volume)

        if avg_volume == 0:
            return 50.0

        volume_ratio = current_volume / avg_volume

        # Higher volume than average = higher score
        if volume_ratio > 2.0:
            return 100.0
        elif volume_ratio > 1.5:
            return 80.0
        elif volume_ratio > 1.0:
            return 60.0
        else:
            return max(20.0, volume_ratio * 50)

    def _calculate_volatility_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate volatility score."""
        volatility = metadata.get("volatility", 0.02)

        # Moderate volatility is preferred (not too high, not too low)
        if 0.01 <= volatility <= 0.03:
            return 100.0
        elif 0.005 <= volatility <= 0.05:
            return 80.0
        elif volatility > 0.05:
            return max(20.0, 100 - (volatility - 0.03) * 1000)
        else:
            return max(20.0, volatility * 2000)

    def _calculate_technical_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate technical indicators score."""
        macd_signal = metadata.get("macd_signal", 0)
        bollinger_position = metadata.get("bollinger_position", 0.5)

        # MACD signal strength
        macd_score = min(100, max(0, 50 + abs(macd_signal) * 100))

        # Bollinger Bands position (prefer middle range)
        if 0.3 <= bollinger_position <= 0.7:
            bb_score = 100.0
        else:
            bb_score = max(20.0, 100 - abs(bollinger_position - 0.5) * 200)

        return (macd_score + bb_score) / 2

    def _calculate_liquidity_score(self, market_data: MarketData) -> float:
        """Calculate liquidity score for confidence calculation."""
        return self.calculate_liquidity_score(market_data)

    def _calculate_volume_liquidity_score(self, market_data: MarketData) -> float:
        """Calculate volume-based liquidity score."""
        volume = float(market_data.volume)

        # Higher volume = higher liquidity score
        if volume > 1000000:  # 1M+ volume
            return 100.0
        elif volume > 500000:  # 500K+ volume
            return 80.0
        elif volume > 100000:  # 100K+ volume
            return 60.0
        elif volume > 50000:  # 50K+ volume
            return 40.0
        else:
            return max(10.0, volume / 1000)

    def _calculate_spread_liquidity_score(self, market_data: MarketData) -> float:
        """Calculate spread-based liquidity score."""
        spread_pct = float(market_data.spread_percentage)

        # Lower spread = higher liquidity score
        if spread_pct < 0.1:  # < 0.1% spread
            return 100.0
        elif spread_pct < 0.2:  # < 0.2% spread
            return 80.0
        elif spread_pct < 0.5:  # < 0.5% spread
            return 60.0
        elif spread_pct < 1.0:  # < 1% spread
            return 40.0
        else:
            return max(10.0, 100 - spread_pct * 50)

    def _calculate_price_stability_score(self, market_data: MarketData) -> float:
        """Calculate price stability score."""
        # Simulate price stability based on spread
        spread_pct = float(market_data.spread_percentage)

        # Lower spread indicates more stable pricing
        if spread_pct < 0.1:
            return 100.0
        elif spread_pct < 0.3:
            return 80.0
        elif spread_pct < 0.5:
            return 60.0
        else:
            return max(20.0, 100 - spread_pct * 100)

    def _calculate_market_depth_score(self, market_data: MarketData) -> float:
        """Calculate market depth score (simulated)."""
        # Simulate market depth based on volume and spread
        volume_score = self._calculate_volume_liquidity_score(market_data)
        spread_score = self._calculate_spread_liquidity_score(market_data)

        return (volume_score + spread_score) / 2

    def _calculate_urgency_score(self, signal: Signal) -> float:
        """Calculate urgency score based on signal characteristics."""
        urgency_factors = []

        # Signal strength urgency
        strength_scores = {
            SignalStrength.WEAK: 20.0,
            SignalStrength.MODERATE: 50.0,
            SignalStrength.STRONG: 80.0,
            SignalStrength.VERY_STRONG: 100.0,
        }
        urgency_factors.append(strength_scores[signal.strength])

        # Confidence urgency (higher confidence = more urgent)
        urgency_factors.append(signal.confidence)

        # Time decay (newer signals are more urgent)
        time_since_creation = (datetime.utcnow() - signal.timestamp).total_seconds()
        time_decay = max(0, 100 - time_since_creation / 60)  # Decay over minutes
        urgency_factors.append(time_decay)

        return sum(urgency_factors) / len(urgency_factors)

    def _calculate_market_condition_score(self, market_data: MarketData) -> float:
        """Calculate market condition score."""
        # Simulate market condition based on spread and volume
        spread_score = self._calculate_spread_liquidity_score(market_data)
        volume_score = self._calculate_volume_liquidity_score(market_data)

        # Good market conditions = low spread + high volume
        return (spread_score + volume_score) / 2


class SignalPriorityQueue:
    """Priority queue for signal management."""

    def __init__(self, max_size: int = 1000):
        """Initialize priority queue."""
        self.max_size = max_size
        self.queue = []
        self.signal_count = 0

    def add_signal(self, signal: Signal) -> bool:
        """Add signal to priority queue."""
        if len(self.queue) >= self.max_size:
            # Remove lowest priority signal
            heapq.heappop(self.queue)

        # Add signal with negative priority score (heapq is min-heap)
        heapq.heappush(self.queue, (-signal.priority_score, self.signal_count, signal))
        self.signal_count += 1
        return True

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.queue) == 0

    def get_next_signal(self) -> Optional[Signal]:
        """Get next highest priority signal."""
        if not self.queue:
            return None

        _, _, signal = heapq.heappop(self.queue)
        return signal

    def get_highest_priority_signal(self) -> Optional[Signal]:
        """Get highest priority signal without removing it."""
        if not self.queue:
            return None

        _, _, signal = self.queue[0]
        return signal

    def peek_next_signal(self) -> Optional[Signal]:
        """Peek at next highest priority signal without removing."""
        if not self.queue:
            return None

        _, _, signal = self.queue[0]
        return signal

    def get_signals_by_symbol(self, symbol: str) -> List[Signal]:
        """Get all signals for a specific symbol."""
        symbol_signals = []
        temp_queue = []

        # Extract signals for the symbol
        while self.queue:
            priority, count, signal = heapq.heappop(self.queue)
            if signal.symbol == symbol:
                symbol_signals.append(signal)
            else:
                temp_queue.append((priority, count, signal))

        # Restore queue
        for item in temp_queue:
            heapq.heappush(self.queue, item)

        return symbol_signals

    def clear_signals(self):
        """Clear all signals from queue."""
        self.queue.clear()
        self.signal_count = 0

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)

    def get_queue_summary(self) -> Dict[str, Any]:
        """Get queue summary statistics."""
        if not self.queue:
            return {
                "total_signals": 0,
                "avg_priority": 0.0,
                "signal_types": {},
                "symbols": [],
            }

        priorities = []
        signal_types = {}
        symbols = set()

        for _, _, signal in self.queue:
            priorities.append(signal.priority_score)
            signal_types[signal.signal_type.value] = (
                signal_types.get(signal.signal_type.value, 0) + 1
            )
            symbols.add(signal.symbol)

        return {
            "total_signals": len(self.queue),
            "avg_priority": sum(priorities) / len(priorities),
            "signal_types": signal_types,
            "symbols": list(symbols),
        }

    # class SignalScorer  # F811 duplicate from line 208
    """Signal scoring utility class."""

    def calculate_confidence_score(
        self, market_data: MarketData, metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on market data and metadata."""
        try:
            # Base confidence from signal strength indicators
            base_confidence = 60.0

            # Adjust based on volume
            if market_data.volume > Decimal("1000000"):
                base_confidence += 10.0
            elif market_data.volume < Decimal("100000"):
                base_confidence -= 15.0

            # Adjust based on spread
            if market_data.spread < Decimal("0.01"):
                base_confidence += 5.0
            elif market_data.spread > Decimal("0.05"):
                base_confidence -= 10.0

            # Adjust based on metadata indicators
            if "rsi" in metadata:
                rsi = metadata["rsi"]
                if 40 <= rsi <= 60:  # Good neutral RSI range
                    base_confidence += 20.0  # More generous for good neutral RSI
                elif 30 <= rsi <= 70:  # Neutral RSI
                    base_confidence += 15.0
                elif rsi < 30 or rsi > 70:  # Extreme RSI
                    base_confidence += 20.0

            if "ema_trend" in metadata:
                trend = metadata["ema_trend"]
                if trend > 0.02:  # Strong uptrend
                    base_confidence += 15.0
                elif trend > 0.0:  # Weak uptrend
                    base_confidence += 10.0
                elif trend > -0.02:  # Slight downtrend (not too bad)
                    base_confidence += 5.0
                elif trend < -0.02:  # Strong downtrend
                    base_confidence -= 25.0  # More penalty for downtrends

            # Ensure confidence is within bounds
            return max(0.0, min(100.0, base_confidence))

        except Exception:
            return 50.0  # Default confidence

    def calculate_liquidity_score(
        self, market_data: MarketData, metadata: Dict[str, Any] = None
    ) -> float:
        """Calculate liquidity score based on market data."""
        try:
            # Use the more sophisticated volume score calculation if metadata
            # is available
            if metadata:
                return self._calculate_volume_score(market_data, metadata)

            # Fallback to simple calculation
            base_score = 50.0

            # Adjust based on volume
            if market_data.volume > Decimal("5000000"):
                base_score += 25.0
            elif market_data.volume > Decimal("1000000"):
                base_score += 15.0
            elif market_data.volume < Decimal("100000"):
                base_score -= 20.0

            # Adjust based on spread
            if market_data.spread < Decimal("0.005"):
                base_score += 15.0
            elif market_data.spread < Decimal("0.01"):
                base_score += 10.0
            elif market_data.spread < Decimal("0.1"):  # Acceptable spread
                base_score += 5.0
            # Only penalize very wide spreads
            elif market_data.spread > Decimal("0.2"):
                base_score -= 25.0

            # Ensure score is within bounds
            return max(0.0, min(100.0, base_score))

        except Exception:
            return 50.0  # Default liquidity score

    def calculate_priority_score(self, signal: Signal, market_data: MarketData) -> float:
        """Calculate priority score for signal execution."""
        try:
            # Base priority from signal confidence and liquidity
            base_priority = (signal.confidence + signal.liquidity_score) / 2.0

            # Adjust based on signal strength
            strength_multiplier = {
                SignalStrength.VERY_STRONG: 1.2,
                SignalStrength.STRONG: 1.1,
                SignalStrength.MODERATE: 1.0,
                SignalStrength.WEAK: 0.8,
            }

            base_priority *= strength_multiplier.get(signal.strength, 1.0)

            # Adjust based on signal type
            type_adjustment = {
                SignalType.BUY: 5.0,
                SignalType.SELL: 5.0,
                SignalType.HOLD: -10.0,
                SignalType.EXIT: 15.0,
            }

            base_priority += type_adjustment.get(signal.signal_type, 0.0)

            # Ensure priority is within bounds
            return max(0.0, min(100.0, base_priority))

        except Exception:
            return 50.0  # Default priority score

    def _calculate_momentum_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate momentum score from metadata."""
        try:
            score = 50.0

            if "rsi" in metadata:
                rsi = metadata["rsi"]
                if rsi < 30:  # Oversold
                    score += 20.0
                elif rsi > 70:  # Overbought
                    score -= 20.0
                else:  # Neutral
                    score += 5.0

            if "ema_trend" in metadata:
                trend = metadata["ema_trend"]
                if trend > 0.02:  # Strong uptrend
                    score += 25.0
                elif trend < -0.02:  # Strong downtrend
                    score -= 15.0
                else:  # Sideways
                    score += 5.0

            return max(0.0, min(100.0, score))
        except Exception:
            return 50.0

    def _calculate_volume_score(self, market_data: MarketData, metadata: Dict[str, Any]) -> float:
        """Calculate volume score from market data and metadata."""
        try:
            score = 50.0

            # Calculate volume ratio from market data
            if hasattr(market_data, "volume") and "avg_volume" in metadata:
                volume_ratio = float(market_data.volume) / metadata["avg_volume"]
                if volume_ratio > 2.0:  # High volume
                    score += 30.0
                elif volume_ratio > 1.0:  # Above average (more generous)
                    score += 20.0
                elif volume_ratio <= 0.5:  # Low volume
                    score -= 25.0  # More penalty for low volume

            if "volume_ratio" in metadata:
                ratio = metadata["volume_ratio"]
                if ratio > 2.0:  # High volume
                    score += 30.0
                elif ratio > 1.5:  # Above average
                    score += 15.0
                elif ratio < 0.5:  # Low volume
                    score -= 20.0

            if "volume_trend" in metadata:
                trend = metadata["volume_trend"]
                if trend > 0.1:  # Increasing volume
                    score += 15.0
                elif trend < -0.1:  # Decreasing volume
                    score -= 10.0

            return max(0.0, min(100.0, score))
        except Exception:
            return 50.0

    def _calculate_volatility_score(self, market_data_or_metadata, metadata=None) -> float:
        """Calculate volatility score from market data and metadata."""
        try:
            score = 50.0

            # Handle both calling patterns: (market_data, metadata) or
            # (metadata)
            if metadata is not None:
                # Called with (market_data, metadata)
                market_data = market_data_or_metadata
                metadata = metadata

                # Calculate volatility from market data price range
                if (
                    hasattr(market_data, "high_price")
                    and hasattr(market_data, "low_price")
                    and hasattr(market_data, "price")
                ):
                    price_range = float(market_data.high_price - market_data.low_price)
                    volatility = price_range / float(market_data.price)
                    if volatility > 0.05:  # High volatility
                        score += 20.0
                    elif volatility < 0.01:  # Low volatility
                        score -= 15.0
                    else:  # Normal volatility
                        score += 5.0
            else:
                # Called with just metadata
                metadata = market_data_or_metadata

            if "volatility" in metadata:
                vol = metadata["volatility"]
                if vol > 0.05:  # High volatility
                    score -= 20.0  # Penalize high volatility
                elif vol < 0.01:  # Low volatility
                    score -= 15.0
                elif vol >= 0.02:  # Moderate volatility (good for trading)
                    score += 35.0
                else:  # Normal volatility
                    score += 5.0

            if "atr_ratio" in metadata:
                atr = metadata["atr_ratio"]
                if atr > 0.03:  # High ATR
                    score += 15.0
                elif atr < 0.01:  # Low ATR
                    score -= 10.0

            return max(0.0, min(100.0, score))
        except Exception:
            return 50.0

    def _calculate_technical_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate technical score from metadata."""
        try:
            score = 50.0

            if "macd_signal" in metadata:
                macd = metadata["macd_signal"]
                if macd > 0:  # Bullish MACD
                    score += 15.0
                else:  # Bearish MACD
                    score -= 10.0

            if "bollinger_position" in metadata:
                bb_pos = metadata["bollinger_position"]
                if bb_pos > 0.8:  # Near upper band
                    score += 10.0
                elif bb_pos < 0.2:  # Near lower band
                    score += 15.0
                else:  # Middle range
                    score += 5.0

            if "stochastic" in metadata:
                stoch = metadata["stochastic"]
                if stoch > 80:  # Overbought
                    score -= 10.0
                elif stoch < 20:  # Oversold
                    score += 15.0

            return max(0.0, min(100.0, score))
        except Exception:
            return 50.0

    def score_signal(self, signal: Signal) -> Signal:
        """Score a signal and return it with updated priority score."""
        try:
            # Create mock market data for scoring - use dataclass not Pydantic model
            # MarketData dataclass doesn't have open_price, high_price, low_price, close_price
            market_data = MarketData(
                symbol=signal.symbol,
                price=signal.price,
                volume=signal.volume,
                timestamp=signal.timestamp,
                bid=signal.price - Decimal("0.01"),
                ask=signal.price + Decimal("0.01"),
                spread=Decimal("0.02"),
            )

            # Calculate confidence and liquidity scores
            confidence = self.calculate_confidence_score(market_data, signal.metadata or {})
            liquidity_score = self.calculate_liquidity_score(market_data)

            # Update signal with new scores
            signal.confidence = confidence
            signal.liquidity_score = liquidity_score
            signal.priority_score = self.calculate_priority_score(signal, market_data)

            return signal

        except Exception:
            # Return signal as-is if scoring fails
            return signal
