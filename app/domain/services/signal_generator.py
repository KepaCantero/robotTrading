"""
Signal Generator Domain Service - Trading signal generation

SignalGenerator provides domain logic for generating trading signals
based on various strategies and indicators.

Reference: Rule 05-architecture.md, Rule 03-solid-principles.md
"""

# mypy: ignore-errors
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.shared.config.centralized_config import get_config


class SignalType(str, Enum):
    """Signal type enumeration."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class SignalStrength(str, Enum):
    """Signal strength levels."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass(frozen=True)
class Signal:
    """
    Trading signal for a symbol.

    Contains signal type, strength, and metadata.
    """

    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: Decimal  # 0-1
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy signal."""
        return self.signal_type == SignalType.BUY

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell signal."""
        return self.signal_type == SignalType.SELL

    @property
    def is_actionable(self) -> bool:
        """Check if signal is actionable (buy or sell)."""
        return self.signal_type in (SignalType.BUY, SignalType.SELL)


@dataclass
class IndicatorValues:
    """Common indicator values for signal generation."""

    price: Decimal
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    ema_12: Optional[Decimal] = None
    ema_26: Optional[Decimal] = None
    rsi: Optional[Decimal] = None
    macd: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    bollinger_upper: Optional[Decimal] = None
    bollinger_lower: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    volume_ma: Optional[Decimal] = None


class SignalGenerator:
    """
    Domain service for generating trading signals.

    Provides pure domain logic for signal generation based on:
    - Technical indicators
    - Price action
    - Momentum
    - Mean reversion
    """

    def __init__(self, confidence_threshold: Decimal = Decimal("0.6")):
        """
        Initialize signal generator.

        Args:
            confidence_threshold: Minimum confidence for actionable signals
        """
        self._confidence_threshold = confidence_threshold

        # Load RSI thresholds from config
        config = get_config()
        self._rsi_oversold = Decimal(str(config.trading.rsi_oversold))  # Default 30
        self._rsi_overbought = Decimal(str(config.trading.rsi_overbought))  # Default 70

    def generate_ma_crossover_signal(
        self,
        indicators: IndicatorValues,
        symbol: str = "",
    ) -> Signal:
        """
        Generate signal based on moving average crossover.

        Strategy:
        - BUY: Fast MA crosses above slow MA
        - SELL: Fast MA crosses below slow MA
        - HOLD: No crossover

        Args:
            indicators: Indicator values
            symbol: Trading symbol

        Returns:
            Generated signal
        """
        if indicators.sma_20 is None or indicators.sma_50 is None:
            return self._hold_signal(symbol, "Insufficient MA data")

        fast_ma = indicators.sma_20
        slow_ma = indicators.sma_50
        price = indicators.price

        # Calculate distances
        fast_above_slow = fast_ma > slow_ma
        price_above_fast = price > fast_ma

        # Determine signal
        if fast_above_slow and price_above_fast:
            # Bullish: price > fast > slow
            strength = self._calculate_ma_strength(fast_ma, slow_ma)
            confidence = min(strength.value / Decimal("100"), Decimal("1"))

            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=strength,
                confidence=confidence,
                reason=f"Price above fast MA ({fast_ma}), which is above slow MA ({slow_ma})",
                metadata={"fast_ma": str(fast_ma), "slow_ma": str(slow_ma)},
            )

        elif not fast_above_slow and not price_above_fast:
            # Bearish: price < fast < slow
            # pylint: disable=arguments-out-of-order
            strength = self._calculate_ma_strength(slow_ma, fast_ma)
            confidence = min(strength.value / Decimal("100"), Decimal("1"))

            return Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=strength,
                confidence=confidence,
                reason=f"Price below fast MA ({fast_ma}), which is below slow MA ({slow_ma})",
                metadata={"fast_ma": str(fast_ma), "slow_ma": str(slow_ma)},
            )

        else:
            # Mixed signals - hold
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=Decimal("0.5"),
                reason="MA alignment unclear - waiting for confirmation",
            )

    def generate_rsi_signal(
        self,
        indicators: IndicatorValues,
        symbol: str = "",
    ) -> Signal:
        """
        Generate signal based on RSI.

        Strategy:
        - BUY: RSI < oversold threshold (default 30)
        - SELL: RSI > overbought threshold (default 70)
        - HOLD: RSI in neutral zone

        Args:
            indicators: Indicator values
            symbol: Trading symbol

        Returns:
            Generated signal
        """
        if indicators.rsi is None:
            return self._hold_signal(symbol, "RSI not available")

        rsi = indicators.rsi
        rsi_oversold = self._rsi_oversold
        rsi_overbought = self._rsi_overbought

        if rsi < rsi_oversold:
            # Oversold - potential buy
            strength = (
                SignalStrength.STRONG
                if rsi < (rsi_oversold - Decimal("10"))
                else SignalStrength.MODERATE
            )
            confidence = (rsi_oversold - rsi) / rsi_oversold

            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=strength,
                confidence=confidence,
                reason=f"RSI oversold at {rsi}",
                metadata={"rsi": str(rsi)},
            )

        elif rsi > rsi_overbought:
            # Overbought - potential sell
            strength = (
                SignalStrength.STRONG
                if rsi > (rsi_overbought + Decimal("10"))
                else SignalStrength.MODERATE
            )
            confidence = (rsi - rsi_overbought) / (Decimal("100") - rsi_overbought)

            return Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=strength,
                confidence=confidence,
                reason=f"RSI overbought at {rsi}",
                metadata={"rsi": str(rsi)},
            )

        else:
            # Neutral zone
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=Decimal("0.5"),
                reason=f"RSI in neutral zone at {rsi}",
                metadata={"rsi": str(rsi)},
            )

    def generate_bollinger_signal(
        self,
        indicators: IndicatorValues,
        symbol: str = "",
    ) -> Signal:
        """
        Generate signal based on Bollinger Bands.

        Strategy:
        - BUY: Price touches/penetrates lower band
        - SELL: Price touches/penetrates upper band
        - HOLD: Price within bands

        Args:
            indicators: Indicator values
            symbol: Trading symbol

        Returns:
            Generated signal
        """
        if (
            indicators.bollinger_upper is None
            or indicators.bollinger_lower is None
            or indicators.price is None
        ):
            return self._hold_signal(symbol, "Bollinger Bands not available")

        price = indicators.price
        upper = indicators.bollinger_upper
        lower = indicators.bollinger_lower

        # Calculate position within bands
        band_width = upper - lower
        if band_width == 0:
            return self._hold_signal(symbol, "Bollinger Bands have zero width")

        position = (price - lower) / band_width

        if position < Decimal("0.1"):
            # Near or below lower band - oversold
            strength = SignalStrength.VERY_STRONG if position < 0 else SignalStrength.STRONG
            confidence = Decimal("1") - position

            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=strength,
                confidence=confidence,
                reason=f"Price near lower Bollinger Band ({lower})",
                metadata={"price": str(price), "lower_band": str(lower)},
            )

        elif position > Decimal("0.9"):
            # Near or above upper band - overbought
            strength = (
                SignalStrength.VERY_STRONG if position > Decimal("1") else SignalStrength.STRONG
            )
            confidence = position

            return Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=strength,
                confidence=confidence,
                reason=f"Price near upper Bollinger Band ({upper})",
                metadata={"price": str(price), "upper_band": str(upper)},
            )

        else:
            # Within bands - hold
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=Decimal("0.5"),
                reason=f"Price within Bollinger Bands ({lower:.2f} - {upper:.2f})",
            )

    def generate_macd_signal(
        self,
        indicators: IndicatorValues,
        symbol: str = "",
    ) -> Signal:
        """
        Generate signal based on MACD.

        Strategy:
        - BUY: MACD crosses above signal line
        - SELL: MACD crosses below signal line
        - HOLD: No crossover

        Args:
            indicators: Indicator values
            symbol: Trading symbol

        Returns:
            Generated signal
        """
        if indicators.macd is None or indicators.macd_signal is None:
            return self._hold_signal(symbol, "MACD not available")

        macd = indicators.macd
        signal_line = indicators.macd_signal

        # Calculate histogram
        histogram = macd - signal_line

        if macd > signal_line and histogram > Decimal("0"):
            # Bullish momentum
            strength = self._calculate_macd_strength(histogram)
            confidence = min(abs(histogram) / Decimal("1"), Decimal("1"))

            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=strength,
                confidence=confidence,
                reason=f"MACD ({macd}) above signal ({signal_line})",
                metadata={"macd": str(macd), "signal": str(signal_line)},
            )

        elif macd < signal_line and histogram < Decimal("0"):
            # Bearish momentum
            strength = self._calculate_macd_strength(abs(histogram))
            confidence = min(abs(histogram) / Decimal("1"), Decimal("1"))

            return Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=strength,
                confidence=confidence,
                reason=f"MACD ({macd}) below signal ({signal_line})",
                metadata={"macd": str(macd), "signal": str(signal_line)},
            )

        else:
            # Neutral
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=Decimal("0.5"),
                reason="MACD around signal line - no clear trend",
            )

    def combine_signals(
        self,
        signals: List[Signal],
        symbol: str = "",
    ) -> Signal:
        """
        Combine multiple signals into one consensus signal.

        Args:
            signals: List of signals to combine
            symbol: Trading symbol

        Returns:
            Consensus signal
        """
        if not signals:
            return self._hold_signal(symbol, "No signals to combine")

        # Count buy/sell/hold signals
        buy_count = sum(1 for s in signals if s.signal_type == SignalType.BUY)
        sell_count = sum(1 for s in signals if s.signal_type == SignalType.SELL)
        hold_count = sum(1 for s in signals if s.signal_type == SignalType.HOLD)

        # Calculate weighted confidence
        buy_confidence = sum(s.confidence for s in signals if s.signal_type == SignalType.BUY)
        sell_confidence = sum(s.confidence for s in signals if s.signal_type == SignalType.SELL)

        # Determine consensus
        if buy_count > sell_count and buy_count > hold_count:
            strength = self._calculate_consensus_strength(
                [s for s in signals if s.signal_type == SignalType.BUY]
            )
            avg_confidence = buy_confidence / buy_count if buy_count > 0 else Decimal("0")

            reasons = [s.reason for s in signals if s.signal_type == SignalType.BUY]
            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=strength,
                confidence=avg_confidence,
                reason=f"Consensus BUY ({buy_count}/{len(signals)} signals)",
                metadata={"signals": reasons},
            )

        elif sell_count > buy_count and sell_count > hold_count:
            strength = self._calculate_consensus_strength(
                [s for s in signals if s.signal_type == SignalType.SELL]
            )
            avg_confidence = sell_confidence / sell_count if sell_count > 0 else Decimal("0")

            reasons = [s.reason for s in signals if s.signal_type == SignalType.SELL]
            return Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=strength,
                confidence=avg_confidence,
                reason=f"Consensus SELL ({sell_count}/{len(signals)} signals)",
                metadata={"signals": reasons},
            )

        else:
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=Decimal("0.5"),
                reason="No clear consensus - HOLD",
            )

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    def _hold_signal(self, symbol: str, reason: str) -> Signal:
        """Create a HOLD signal."""
        return Signal(
            symbol=symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=Decimal("0"),
            reason=reason,
        )

    def _calculate_ma_strength(self, fast_ma: Decimal, slow_ma: Decimal) -> SignalStrength:
        """Calculate signal strength based on MA distance."""
        diff_pct = abs((fast_ma - slow_ma) / slow_ma * Decimal("100"))

        if diff_pct > Decimal("5"):
            return SignalStrength.VERY_STRONG
        elif diff_pct > Decimal("3"):
            return SignalStrength.STRONG
        elif diff_pct > Decimal("1"):
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def _calculate_macd_strength(self, histogram: Decimal) -> SignalStrength:
        """Calculate signal strength based on MACD histogram."""
        abs_hist = abs(histogram)

        if abs_hist > Decimal("2"):
            return SignalStrength.VERY_STRONG
        elif abs_hist > Decimal("1"):
            return SignalStrength.STRONG
        elif abs_hist > Decimal("0.5"):
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def _calculate_consensus_strength(self, signals: List[Signal]) -> SignalStrength:
        """Calculate consensus strength from multiple signals."""
        if not signals:
            return SignalStrength.WEAK

        strong_count = sum(
            1 for s in signals if s.strength in (SignalStrength.STRONG, SignalStrength.VERY_STRONG)
        )

        if strong_count >= len(signals):
            return SignalStrength.VERY_STRONG
        elif strong_count >= len(signals) / 2:
            return SignalStrength.STRONG
        else:
            return SignalStrength.MODERATE
