"""
PHASE 3: Volatility Monitor - ATR-Based Position Scaling

Monitors Average True Range (ATR) to scale positions based on volatility.
Lower volatility → larger positions (up to 1.5x)
Higher volatility → smaller positions (down to 0.5x)

Formula:
- ATR = Average of True Range over 14 periods
- True Range = max(high-low, |high-close_prev|, |low-close_prev|)
- Volatility Scale = base_scale / (current_ATR / average_ATR)
"""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """OHLC price data for volatility calculation."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def true_range(self, prev_close: Optional[Decimal] = None) -> Decimal:
        """Calculate true range for this candle."""
        high_low = self.high - self.low

        if prev_close is None:
            return high_low

        high_prev_close = abs(self.high - prev_close)
        low_prev_close = abs(self.low - prev_close)

        return max(high_low, high_prev_close, low_prev_close)


class VolatilityMonitor:
    """
    Monitors ATR (Average True Range) for volatility-based position scaling.

    Logic:
    - Low ATR (< 14-day avg) → scale UP to 1.5x (lower risk environment)
    - Normal ATR → scale = 1.0x (baseline)
    - High ATR (> 14-day avg) → scale DOWN to 0.5x (higher risk environment)

    Usage:
        monitor = VolatilityMonitor()
        current_atr = monitor.calculate_atr(prices, period=14)
        avg_atr = monitor.calculate_average_atr(symbol)
        scale = monitor.calculate_volatility_scale(symbol, current_atr, avg_atr)
    """

    def __init__(self, atr_period: int = 14):
        """
        Initialize volatility monitor.

        Args:
            atr_period: Number of periods for ATR calculation (default 14)
        """
        self.atr_period = atr_period
        self.atr_history: Dict[str, List[Decimal]] = {}  # symbol -> list of ATRs
        self.volatility_spikes: Dict[str, List[datetime]] = {}  # symbol -> spike times

    def calculate_atr(
        self,
        prices: List[PriceData],
        period: Optional[int] = None,
    ) -> Decimal:
        """
        Calculate Average True Range from price data.

        Args:
            prices: List of OHLC price data (must be in chronological order)
            period: ATR period (default self.atr_period = 14)

        Returns:
            ATR as Decimal
        """
        if period is None:
            period = self.atr_period

        if len(prices) < period:
            raise ValueError(f"Need at least {period} price points, got {len(prices)}")

        true_ranges: List[Decimal] = []

        for i, price in enumerate(prices):
            if i == 0:
                prev_close = price.close
            else:
                prev_close = prices[i - 1].close

            tr = price.true_range(prev_close)
            true_ranges.append(tr)

        # Calculate SMA of true ranges (simple moving average for last 'period' values)
        atr = sum(true_ranges[-period:]) / Decimal(period)

        return atr.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def calculate_average_atr(
        self,
        symbol: str,
        prices: Optional[List[PriceData]] = None,
        lookback_periods: int = 60,
    ) -> Decimal:
        """
        Calculate historical average ATR for symbol.

        Args:
            symbol: Trading symbol
            prices: Price data (if None, uses cached history)
            lookback_periods: How many periods back to average (default 60)

        Returns:
            Average ATR as Decimal
        """
        if symbol not in self.atr_history or not self.atr_history[symbol]:
            if prices is None:
                raise ValueError(f"No ATR history for {symbol} and no prices provided")

            # Calculate ATR for each period in lookback window
            atrs: List[Decimal] = []
            for i in range(self.atr_period, len(prices)):
                atr = self.calculate_atr(
                    prices[i - self.atr_period : i + 1], period=self.atr_period
                )
                atrs.append(atr)

            self.atr_history[symbol] = atrs
        else:
            atrs = self.atr_history[symbol]

        if not atrs:
            raise ValueError(f"No ATR data for {symbol}")

        # Use last lookback_periods ATRs to calculate average
        lookback = atrs[-lookback_periods:] if len(atrs) >= lookback_periods else atrs
        avg_atr = sum(lookback) / Decimal(len(lookback))

        return avg_atr.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def calculate_volatility_scale(
        self,
        symbol: str,
        current_atr: Decimal,
        average_atr: Decimal,
        base_scale: Decimal = Decimal("1.0"),
    ) -> Decimal:
        """
        Return position sizing scale based on ATR ratio.

        Formula: scale = base_scale / (current_ATR / average_ATR)

        If current < historical: scale > 1.0 (lower vol, larger positions)
        If current > historical: scale < 1.0 (higher vol, smaller positions)

        Args:
            symbol: Trading symbol (for logging)
            current_atr: Current ATR value
            average_atr: Historical average ATR
            base_scale: Base scaling factor (default 1.0)

        Returns:
            Scaling factor (0.5 to 1.5), quantized to 3 decimals
        """
        if average_atr == Decimal("0"):
            logger.warning(f"{symbol}: Average ATR is 0, returning base scale")
            return base_scale

        # Calculate ratio: current / average
        atr_ratio = current_atr / average_atr

        # Scale = base / ratio
        # If ratio < 1: scale > base (low vol → larger positions)
        # If ratio > 1: scale < base (high vol → smaller positions)
        scale = base_scale / atr_ratio

        # Enforce bounds: 0.5x minimum, 1.5x maximum
        scale = max(Decimal("0.5"), min(scale, Decimal("1.5")))

        scale = scale.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

        logger.debug(
            f"{symbol}: ATR ratio={atr_ratio:.3f}, scale={scale:.3f} "
            f"(current_atr={current_atr:.4f}, avg_atr={average_atr:.4f})"
        )

        return scale

    def is_volatility_spike(
        self,
        symbol: str,
        current_atr: Decimal,
        average_atr: Decimal,
        std_dev: Optional[Decimal] = None,
        threshold_multiplier: Decimal = Decimal("2.0"),
    ) -> bool:
        """
        Check if ATR > mean + 2σ (volatility spike).

        A spike indicates extreme volatility requiring position reduction.

        Args:
            symbol: Trading symbol
            current_atr: Current ATR
            average_atr: Average ATR
            std_dev: Standard deviation of ATR (calculated if None)
            threshold_multiplier: Multiplier for spike detection (default 2.0 = 2σ)

        Returns:
            True if volatility spike detected
        """
        if std_dev is None:
            # Use a simple heuristic: if current > 1.5x average, it's a spike
            spike_threshold = average_atr * Decimal("1.5")
        else:
            # Use standard deviation approach
            spike_threshold = average_atr + (std_dev * threshold_multiplier)

        is_spike = current_atr > spike_threshold

        if is_spike:
            logger.warning(
                f"{symbol}: VOLATILITY SPIKE DETECTED! "
                f"Current ATR {current_atr:.4f} > spike threshold {spike_threshold:.4f}"
            )

            if symbol not in self.volatility_spikes:
                self.volatility_spikes[symbol] = []
            self.volatility_spikes[symbol].append(datetime.now())

        return is_spike

    def get_volatility_regime(
        self,
        current_atr: Decimal,
        average_atr: Decimal,
    ) -> str:
        """
        Classify volatility into regime.

        Args:
            current_atr: Current ATR
            average_atr: Average ATR

        Returns:
            Regime: "very_low", "low", "normal", "high", "very_high"
        """
        ratio = current_atr / average_atr if average_atr > Decimal("0") else Decimal("1")

        if ratio < Decimal("0.75"):
            return "very_low"
        elif ratio < Decimal("0.90"):
            return "low"
        elif ratio <= Decimal("1.10"):
            return "normal"
        elif ratio < Decimal("1.50"):
            return "high"
        else:
            return "very_high"

    def get_recent_volatility_spikes(
        self,
        symbol: str,
        lookback_minutes: int = 60,
    ) -> List[datetime]:
        """
        Get recent volatility spikes for symbol.

        Args:
            symbol: Trading symbol
            lookback_minutes: How far back to look (default 60 minutes)

        Returns:
            List of spike timestamps within lookback window
        """
        if symbol not in self.volatility_spikes:
            return []

        cutoff = datetime.now() - __import__("datetime").timedelta(minutes=lookback_minutes)
        return [spike for spike in self.volatility_spikes[symbol] if spike > cutoff]

    def calculate_atr_std_dev(
        self,
        symbol: str,
        lookback_periods: int = 30,
    ) -> Decimal:
        """
        Calculate standard deviation of ATR values.

        Used for spike detection with statistical approach.

        Args:
            symbol: Trading symbol
            lookback_periods: Number of periods to use (default 30)

        Returns:
            Standard deviation as Decimal
        """
        if symbol not in self.atr_history or not self.atr_history[symbol]:
            raise ValueError(f"No ATR history for {symbol}")

        atrs = self.atr_history[symbol]
        lookback = atrs[-lookback_periods:] if len(atrs) >= lookback_periods else atrs

        if len(lookback) < 2:
            return Decimal("0")

        # Calculate standard deviation
        float_atrs = [float(atr) for atr in lookback]
        std = statistics.stdev(float_atrs)

        return Decimal(str(std)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
