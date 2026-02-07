"""
Time-Series Momentum Strategy Domain Service

Implements time-series momentum (trend following) where
individual assets are traded based on their own past performance.

Reference: Rule 11-gray-vogel-quantitative-momentum.md
Paper: Moskowitz, O., & Grinblatt, M. (1999). "Do Industries Explain
       Momentum Profits?"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class TrendState(str, Enum):
    """Trend state for time-series momentum."""

    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


@dataclass
class TimeSeriesSignal:
    """Signal for a single asset based on time-series momentum."""

    symbol: str
    state: TrendState
    strength: float  # Signal strength (0-1)
    position_size: float  # Suggested position size (-1 to 1)
    stop_loss: Optional[float] = None  # Stop loss price
    take_profit: Optional[float] = None  # Take profit price

    @property
    def is_long(self) -> bool:
        """Check if signal is long."""
        return self.state == TrendState.UPTREND and self.position_size > 0

    @property
    def is_short(self) -> bool:
        """Check if signal is short."""
        return self.state == TrendState.DOWNTREND and self.position_size < 0


class TimeSeriesMomentum:
    """
    Time-series momentum (trend following) strategy.

    Generates trading signals based on:
    - Moving average crossovers
    - Breakout signals
    - Volatility-adjusted momentum

    This is a pure domain service that can be used with any data source.

    Reference: Moskowitz, O., et al. (2012). "Time Series Momentum"
    """

    def __init__(
        self,
        fast_period: int = 12,  # Fast MA period (months)
        slow_period: int = 24,  # Slow MA period (months)
        volatility_period: int = 20,  # Volatility lookback
        volatility_threshold: float = 1.5,  # Volatility threshold for signals
        position_sizing: str = "volatility_target",  # volatility_target, kelly, fixed
    ):
        """
        Initialize time-series momentum.

        Args:
            fast_period: Fast moving average period
            slow_period: Slow moving average period
            volatility_period: Volatility calculation period
            volatility_threshold: Minimum volatility for signals
            position_sizing: Position sizing method
        """
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._volatility_period = volatility_period
        self._volatility_threshold = volatility_threshold
        self._position_sizing = position_sizing

    def generate_signal(
        self,
        prices: np.ndarray,
        symbol: str,
    ) -> TimeSeriesSignal:
        """
        Generate time-series momentum signal for a single asset.

        Args:
            prices: Price history (most recent last)
            symbol: Asset symbol

        Returns:
            TimeSeriesSignal with trading recommendation
        """
        # Input validation - check for empty or invalid prices
        if len(prices) == 0:
            logger.warning(f"Empty prices array for symbol {symbol}")
            return TimeSeriesSignal(
                symbol=symbol,
                state=TrendState.NEUTRAL,
                strength=0.0,
                position_size=0.0,
            )

        # Handle NaN and inf values
        valid_mask = ~np.isnan(prices) & ~np.isinf(prices) & (prices > 0)
        prices_clean = prices[valid_mask]

        if len(prices_clean) < len(prices):
            n_filtered = len(prices) - len(prices_clean)
            logger.warning(
                f"Filtered out {n_filtered} NaN/inf/non-positive values from prices for {symbol}"
            )

        if len(prices_clean) < self._slow_period + 1:
            # Not enough data
            logger.warning(
                f"Insufficient data points for {symbol}: {len(prices_clean)} < {self._slow_period + 1}"
            )
            return TimeSeriesSignal(
                symbol=symbol,
                state=TrendState.NEUTRAL,
                strength=0.0,
                position_size=0.0,
            )

        # Calculate moving averages
        fast_ma = self._calculate_ma(prices_clean, self._fast_period)
        slow_ma = self._calculate_ma(prices_clean, self._slow_period)

        # Validate MA values
        if not (np.isfinite(fast_ma) and np.isfinite(slow_ma) and fast_ma > 0 and slow_ma > 0):
            logger.warning(
                f"Invalid moving averages for {symbol}: fast_ma={fast_ma}, slow_ma={slow_ma}"
            )
            return TimeSeriesSignal(
                symbol=symbol,
                state=TrendState.NEUTRAL,
                strength=0.0,
                position_size=0.0,
            )

        # Calculate volatility
        returns = np.diff(prices_clean[-self._volatility_period :])
        volatility = np.std(returns) if len(returns) > 0 else 0

        # Handle invalid volatility
        if not np.isfinite(volatility) or volatility < 0:
            volatility = 0
            logger.warning(f"Invalid volatility for {symbol}, using 0")

        # Normalize volatility
        price_mean = np.mean(prices_clean[-self._volatility_period :])
        if price_mean > 0 and np.isfinite(price_mean):
            normalized_vol: float = float(volatility) / float(price_mean)
        else:
            normalized_vol = 0.0
            logger.warning(f"Invalid price mean for {symbol}, using normalized_vol=0")

        # Validate normalized_vol
        if not np.isfinite(normalized_vol):
            normalized_vol = 0.0

        # Determine trend
        current_price = float(prices_clean[-1])

        if not np.isfinite(current_price) or current_price <= 0:
            logger.warning(f"Invalid current price for {symbol}: {current_price}")
            return TimeSeriesSignal(
                symbol=symbol,
                state=TrendState.NEUTRAL,
                strength=0.0,
                position_size=0.0,
            )

        if fast_ma > slow_ma and normalized_vol > self._volatility_threshold / 100:
            # Uptrend with sufficient volatility
            strength = self._calculate_signal_strength(
                fast_ma, slow_ma, current_price, normalized_vol
            )
            position_size = self._calculate_position_size(strength, normalized_vol, 1)

            state = TrendState.UPTREND

            # Calculate stop loss and take profit
            atr = self._calculate_atr(prices_clean[-20:]) if len(prices_clean) >= 20 else None
            stop_loss = current_price * (1 - 0.02) if atr else None  # 2% stop
            take_profit = current_price * (1 + 0.06) if atr else None  # 6% target

            return TimeSeriesSignal(
                symbol=symbol,
                state=state,
                strength=strength,
                position_size=min(position_size, 1.0),
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        elif fast_ma < slow_ma and normalized_vol > self._volatility_threshold / 100:
            # Downtrend
            strength = self._calculate_signal_strength(
                slow_ma, fast_ma, current_price, normalized_vol
            )
            position_size = self._calculate_position_size(strength, normalized_vol, -1)

            state = TrendState.DOWNTREND

            atr = self._calculate_atr(prices_clean[-20:]) if len(prices_clean) >= 20 else None
            stop_loss = current_price * (1 + 0.02) if atr else None
            take_profit = current_price * (1 - 0.06) if atr else None

            return TimeSeriesSignal(
                symbol=symbol,
                state=state,
                strength=strength,
                position_size=max(position_size, -1.0),
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        else:
            # Neutral or low volatility
            return TimeSeriesSignal(
                symbol=symbol,
                state=TrendState.NEUTRAL,
                strength=0.0,
                position_size=0.0,
            )

    def _calculate_ma(self, prices: np.ndarray, period: int) -> float:
        """Calculate simple moving average."""
        if len(prices) < period:
            return float(np.mean(prices))
        return float(np.mean(prices[-period:]))

    def _calculate_signal_strength(
        self,
        fast_ma: float,
        slow_ma: float,
        current_price: float,
        volatility: float,
    ) -> float:
        """
        Calculate signal strength (0-1).

        Based on:
        - Distance between MAs
        - Price position relative to MAs
        - Volatility (normalized)
        """
        # MA separation as percentage
        ma_separation = abs(fast_ma - slow_ma) / slow_ma

        # Price position relative to MAs
        if fast_ma > slow_ma:
            # Uptrend: price above MAs strengthens signal
            price_position = (current_price - fast_ma) / fast_ma if fast_ma > 0 else 0
        else:
            # Downtrend: price below MAs strengthens signal
            price_position = (fast_ma - current_price) / fast_ma if fast_ma > 0 else 0

        # Combine metrics
        strength = min(1.0, ma_separation * 2 + abs(price_position))
        strength = max(0.0, min(1.0, strength))

        return strength

    def _calculate_position_size(
        self,
        strength: float,
        volatility: float,
        direction: int,  # 1 for long, -1 for short
    ) -> float:
        """
        Calculate position size based on signal strength and volatility.

        Args:
            strength: Signal strength (0-1)
            volatility: Normalized volatility
            direction: Trade direction

        Returns:
            Position size (scaled by -1 to 1)
        """
        if self._position_sizing == "volatility_target":
            # Inverse volatility sizing
            target_vol = 0.15  # 15% annual volatility target
            size = strength * target_vol / (volatility + 0.01)

        elif self._position_sizing == "fixed":
            size = strength * 0.5  # Max 50% position

        else:  # default
            size = strength * 0.3

        return direction * min(size, 1.0)

    def _calculate_atr(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(prices) < 2:
            return 0.0

        high_low = np.abs(np.diff(prices))
        high_close = np.abs(np.diff(prices))
        low_close = np.abs(np.diff(prices))

        true_ranges = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = np.mean(true_ranges[-period:]) if len(true_ranges) >= period else np.mean(true_ranges)

        return float(atr)

    def calculate_portfolio_signals(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> List[TimeSeriesSignal]:
        """
        Generate signals for multiple assets.

        Args:
            price_data: Dictionary of symbol -> price history

        Returns:
            List of TimeSeriesSignal for each asset
        """
        signals = []

        for symbol, prices in price_data.items():
            signal = self.generate_signal(prices, symbol)
            if signal.state in (TrendState.UPTREND, TrendState.DOWNTREND):
                signals.append(signal)

        return signals
