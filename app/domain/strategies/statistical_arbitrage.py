"""
Statistical Arbitrage Strategy Domain Service

Implements mean reversion strategies based on statistical analysis
of price deviations from fundamental values.

Reference: Rule 11-gray-vogel-quantitative-momentum.md (mean reversion concepts)
Paper: Balakrishnan, D., et al. (2018). "Machine Learning for Statistical Arbitrage"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ReversionState(str, Enum):
    """State for mean reversion signals."""

    OVERBOUGHT = "overbought"  # Price above mean, expect decline
    OVERSOLD = "oversold"  # Price below mean, expect rise
    NEUTRAL = "neutral"
    MEAN_CROSSING = "mean_crossing"  # Price crossing mean


@dataclass
class ZScoreSignal:
    """Signal based on Z-score analysis."""

    symbol: str
    z_score: float  # Standard deviations from mean
    state: ReversionState
    confidence: float  # 0-1
    expected_reversion_target: float  # Expected price after reversion
    stop_loss: Optional[float] = None  # Stop loss price
    take_profit: Optional[float] = None  # Take profit price

    @property
    def is_long(self) -> bool:
        """Check if signal is long (oversold)."""
        return self.state == ReversionState.OVERSOLD

    @property
    def is_short(self) -> bool:
        """Check if signal is short (overbought)."""
        return self.state == ReversionState.OVERBOUGHT


@dataclass
class BollingerBandSignal:
    """Signal based on Bollinger Bands."""

    symbol: str
    price: float
    upper_band: float
    middle_band: float  # Moving average
    lower_band: float
    bandwidth: float  # (upper - lower) / middle
    percent_b: float  # (price - lower) / (upper - lower)
    state: ReversionState
    strength: float  # 0-1


@dataclass
class MeanReversionMetrics:
    """Metrics for mean reversion strategy."""

    half_life: float  # Expected time to revert to mean (days)
    mean_reversion_speed: float  # Speed of reversion (0-1)
    stationarity_test: float  # Augmented Dickey-Fuller test statistic
    is_stationary: bool  # Whether series is stationary
    hit_rate: float  # Historical success rate
    average_reversion_time: float  # Average days for reversion


class StatisticalArbitrage:
    """
    Statistical arbitrage / mean reversion strategy.

    Identifies assets that have deviated significantly from their
    historical mean and expects them to revert.

    This is a pure domain service that can be used with any data source.

    Reference: Balakrishnan, D., et al. (2018)
    """

    def __init__(
        self,
        lookback_period: int = 20,  # Days for mean/std calculation
        z_score_threshold: float = 2.0,  # Standard deviations for signal
        entry_threshold: float = 2.0,  # Z-score for entry
        exit_threshold: float = 0.5,  # Z-score for exit
        min_half_life: float = 5.0,  # Minimum half-life for trading
        max_half_life: float = 60.0,  # Maximum half-life
        confidence_level: float = 0.95,  # For statistical tests
    ):
        """
        Initialize statistical arbitrage strategy.

        Args:
            lookback_period: Period for moving statistics
            z_score_threshold: Z-score threshold for signals
            entry_threshold: Z-score level to enter position
            exit_threshold: Z-score level to exit position
            min_half_life: Minimum acceptable half-life
            max_half_life: Maximum acceptable half-life
            confidence_level: Statistical confidence level
        """
        self._lookback = lookback_period
        self._z_score_threshold = z_score_threshold
        self._entry_threshold = entry_threshold
        self._exit_threshold = exit_threshold
        self._min_half_life = min_half_life
        self._max_half_life = max_half_life
        self._confidence = confidence_level

    def generate_zscore_signal(
        self,
        prices: np.ndarray,
        symbol: str,
    ) -> ZScoreSignal:
        """
        Generate Z-score based mean reversion signal.

        Args:
            prices: Price history (most recent last)
            symbol: Asset symbol

        Returns:
            ZScoreSignal with trading recommendation
        """
        # Input validation - check for empty prices
        if len(prices) == 0:
            logger.warning(f"Empty prices array for symbol {symbol}")
            return ZScoreSignal(
                symbol=symbol,
                z_score=0.0,
                state=ReversionState.NEUTRAL,
                confidence=0.0,
                expected_reversion_target=0.0,
            )

        # Handle NaN and inf values
        valid_mask = ~np.isnan(prices) & ~np.isinf(prices) & (prices > 0)
        prices_clean = prices[valid_mask]

        if len(prices_clean) < len(prices):
            n_filtered = len(prices) - len(prices_clean)
            logger.warning(f"Filtered out {n_filtered} NaN/inf/non-positive values from prices for {symbol}")

        if len(prices_clean) < self._lookback + 1:
            # Not enough data
            logger.warning(f"Insufficient data points for {symbol}: {len(prices_clean)} < {self._lookback + 1}")
            return ZScoreSignal(
                symbol=symbol,
                z_score=0.0,
                state=ReversionState.NEUTRAL,
                confidence=0.0,
                expected_reversion_target=float(prices_clean[-1]) if len(prices_clean) > 0 else 0.0,
            )

        # Calculate rolling statistics
        window_prices = prices_clean[-self._lookback:]

        # Validate window prices
        if len(window_prices) == 0:
            logger.warning(f"Empty window prices for {symbol}")
            return ZScoreSignal(
                symbol=symbol,
                z_score=0.0,
                state=ReversionState.NEUTRAL,
                confidence=0.0,
                expected_reversion_target=float(prices_clean[-1]) if len(prices_clean) > 0 else 0.0,
            )

        mean = float(np.mean(window_prices))
        std = float(np.std(window_prices))
        current_price = float(prices_clean[-1])

        # Validate calculated values
        if not np.isfinite(mean) or not np.isfinite(std) or not np.isfinite(current_price):
            logger.warning(f"Non-finite values for {symbol}: mean={mean}, std={std}, price={current_price}")
            return ZScoreSignal(
                symbol=symbol,
                z_score=0.0,
                state=ReversionState.NEUTRAL,
                confidence=0.0,
                expected_reversion_target=float(prices_clean[-1]),
            )

        if std < 1e-10 or current_price <= 0:
            return ZScoreSignal(
                symbol=symbol,
                z_score=0.0,
                state=ReversionState.NEUTRAL,
                confidence=0.0,
                expected_reversion_target=current_price if current_price > 0 else mean,
            )

        # Calculate Z-score
        z_score = (current_price - mean) / std

        # Validate z_score
        if not np.isfinite(z_score):
            logger.warning(f"Non-finite z_score for {symbol}, using 0")
            z_score = 0.0

        # Determine state and signal
        if z_score > self._entry_threshold:
            state = ReversionState.OVERBOUGHT
            confidence = min(1.0, (z_score - self._entry_threshold) / 2.0)
            target = mean - (mean - current_price) * 0.5  # Expect 50% reversion
        elif z_score < -self._entry_threshold:
            state = ReversionState.OVERSOLD
            confidence = min(1.0, (abs(z_score) - self._entry_threshold) / 2.0)
            target = mean + (current_price - mean) * 0.5
        else:
            state = ReversionState.NEUTRAL
            confidence = 0.0
            target = mean

        # Validate target
        if not np.isfinite(target) or target <= 0:
            target = mean

        # Calculate risk levels
        atr = self._calculate_atr(prices_clean[-20:]) if len(prices_clean) >= 20 else std * 2

        if state == ReversionState.OVERBOUGHT:
            stop_loss = current_price * (1 + 0.02)  # 2% above
            take_profit = mean
        elif state == ReversionState.OVERSOLD:
            stop_loss = current_price * (1 - 0.02)  # 2% below
            take_profit = mean
        else:
            stop_loss = None
            take_profit = None

        return ZScoreSignal(
            symbol=symbol,
            z_score=z_score,
            state=state,
            confidence=confidence,
            expected_reversion_target=target,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    def generate_bollinger_signal(
        self,
        prices: np.ndarray,
        symbol: str,
        num_std: float = 2.0,
    ) -> BollingerBandSignal:
        """
        Generate Bollinger Bands based signal.

        Args:
            prices: Price history (most recent last)
            symbol: Asset symbol
            num_std: Number of standard deviations for bands

        Returns:
            BollingerBandSignal with recommendation
        """
        if len(prices) < self._lookback:
            # Not enough data
            return BollingerBandSignal(
                symbol=symbol,
                price=float(prices[-1]) if len(prices) > 0 else 0.0,
                upper_band=0.0,
                middle_band=0.0,
                lower_band=0.0,
                bandwidth=0.0,
                percent_b=0.5,
                state=ReversionState.NEUTRAL,
                strength=0.0,
            )

        window_prices = prices[-self._lookback:]
        middle_band = float(np.mean(window_prices))
        std = float(np.std(window_prices))

        upper_band = middle_band + num_std * std
        lower_band = middle_band - num_std * std
        current_price = float(prices[-1])

        # Calculate metrics
        bandwidth = (upper_band - lower_band) / middle_band if middle_band > 0 else 0
        percent_b = (
            (current_price - lower_band) / (upper_band - lower_band)
            if (upper_band - lower_band) > 0
            else 0.5
        )

        # Determine state
        if percent_b >= 1.0:
            state = ReversionState.OVERBOUGHT
            strength = min(1.0, (percent_b - 1.0) * 2.0)
        elif percent_b <= 0.0:
            state = ReversionState.OVERSOLD
            strength = min(1.0, (0.0 - percent_b) * 2.0)
        else:
            state = ReversionState.NEUTRAL
            strength = 0.0

        return BollingerBandSignal(
            symbol=symbol,
            price=current_price,
            upper_band=upper_band,
            middle_band=middle_band,
            lower_band=lower_band,
            bandwidth=bandwidth,
            percent_b=percent_b,
            state=state,
            strength=strength,
        )

    def calculate_half_life(
        self,
        prices: np.ndarray,
    ) -> float:
        """
        Calculate mean reversion half-life using Ornstein-Uhlenbeck process.

        Half-life = ln(2) / theta
        where theta is the mean reversion speed from OU process: dx = theta * (mu - x) * dt + sigma * dW

        Args:
            prices: Price history

        Returns:
            Half-life in days (time to revert 50% to mean)
        """
        if len(prices) < 10:
            return 0.0

        # Calculate log returns
        log_prices = np.log(prices)

        # Calculate deviations from mean
        deviations = log_prices - np.mean(log_prices)

        # Lagged values
        lagged_deviations = deviations[:-1]
        current_deviations = deviations[1:]

        if len(lagged_deviations) < 2:
            return 0.0

        # OLS regression: x_t - x_{t-1} = theta * (mu - x_{t-1}) * dt + epsilon
        # Simplified: delta_x = -theta * x_{t-1} + epsilon
        delta_x = current_deviations - lagged_deviations

        # Linear regression
        slope, _ = np.polyfit(lagged_deviations, delta_x, 1)

        # Theta is negative of slope (since slope = -theta)
        theta = -slope

        if theta <= 0:
            # No mean reversion (random walk or explosive)
            return float('inf')

        # Half-life = ln(2) / theta
        half_life = np.log(2) / theta

        return float(half_life)

    def test_stationarity(
        self,
        prices: np.ndarray,
    ) -> Tuple[bool, float]:
        """
        Test if price series is stationary using Augmented Dickey-Fuller test.

        Args:
            prices: Price history

        Returns:
            Tuple of (is_stationary, test_statistic)
        """
        try:
            from statsmodels.tsa.stattools import adfuller

            # Use log prices for stationarity test
            log_prices = np.log(prices[prices > 0]) if np.all(prices > 0) else prices

            # Perform ADF test
            result = adfuller(log_prices, maxlag=1)

            # Test statistic
            test_statistic = result[0]

            # p-value
            p_value = result[1]

            # Critical values at 5% level
            critical_value = result[4]['5%']

            # Stationary if test_statistic < critical_value
            is_stationary = test_statistic < critical_value

            return is_stationary, test_statistic

        except Exception:
            # Fallback: simple variance ratio test
            if len(prices) < 20:
                return False, 0.0

            # Variance ratio: Var(long-term) / Var(short-term) * n
            short_var = np.var(np.diff(prices[:10]))
            long_var = np.var(np.diff(prices[:10]) - np.diff(prices[:10]).mean())

            if short_var < 1e-10:
                return False, 0.0

            variance_ratio = long_var / short_var

            # Rough approximation
            is_stationary = variance_ratio < 1.0

            return is_stationary, float(variance_ratio)

    def calculate_mean_reversion_metrics(
        self,
        prices: np.ndarray,
    ) -> MeanReversionMetrics:
        """
        Calculate comprehensive mean reversion metrics.

        Args:
            prices: Price history

        Returns:
            MeanReversionMetrics with various statistics
        """
        # Half-life
        half_life = self.calculate_half_life(prices)

        # Stationarity test
        is_stationary, adf_stat = self.test_stationarity(prices)

        # Mean reversion speed (normalized)
        if half_life > 0 and half_life < float('inf'):
            mean_reversion_speed = 1.0 / (1.0 + half_life / 10.0)
        else:
            mean_reversion_speed = 0.0

        # Simulated historical metrics
        hit_rate = 0.65 if is_stationary else 0.50
        average_reversion_time = half_life * 2 if half_life < 100 else 20.0

        return MeanReversionMetrics(
            half_life=half_life,
            mean_reversion_speed=mean_reversion_speed,
            stationarity_test=adf_stat,
            is_stationary=is_stationary,
            hit_rate=hit_rate,
            average_reversion_time=average_reversion_time,
        )

    def should_trade(
        self,
        signal: ZScoreSignal,
        metrics: MeanReversionMetrics,
    ) -> bool:
        """
        Determine if signal should be traded based on metrics.

        Args:
            signal: Z-score signal
            metrics: Mean reversion metrics

        Returns:
            True if signal should be traded
        """
        # Check if state is tradeable
        if signal.state not in (ReversionState.OVERBOUGHT, ReversionState.OVERSOLD):
            return False

        # Check confidence
        if signal.confidence < 0.3:
            return False

        # Check half-life is in acceptable range
        if metrics.half_life < self._min_half_life:
            return False  # Reverts too quickly
        if metrics.half_life > self._max_half_life:
            return False  # Takes too long to revert

        # Check stationarity
        if not metrics.is_stationary:
            return False

        # Check reversion speed
        if metrics.mean_reversion_speed < 0.2:
            return False

        return True

    def calculate_position_size(
        self,
        signal: ZScoreSignal,
        metrics: MeanReversionMetrics,
        max_position: float = 0.1,
    ) -> float:
        """
        Calculate position size based on signal strength and metrics.

        Args:
            signal: Z-score signal
            metrics: Mean reversion metrics
            max_position: Maximum position size

        Returns:
            Position size as fraction of capital
        """
        # Base size from confidence
        base_size = signal.confidence * max_position

        # Adjust by Z-score magnitude
        z_score_factor = min(abs(signal.z_score) / self._entry_threshold, 2.0) / 2.0

        # Adjust by reversion speed
        speed_factor = metrics.mean_reversion_speed

        # Adjust by hit rate
        hit_rate_factor = metrics.hit_rate

        # Combined size
        position_size = base_size * z_score_factor * speed_factor * hit_rate_factor

        return min(position_size, max_position)

    def _calculate_atr(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(prices) < 2:
            return 0.0

        high_low = np.abs(np.diff(prices))
        atr = np.mean(high_low[-period:]) if len(high_low) >= period else np.mean(high_low)

        return float(atr)

    def generate_portfolio_signals(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> List[ZScoreSignal]:
        """
        Generate signals for multiple assets.

        Args:
            price_data: Dictionary of symbol -> price history

        Returns:
            List of ZScoreSignal for each asset
        """
        signals = []

        for symbol, prices in price_data.items():
            signal = self.generate_zscore_signal(prices, symbol)
            metrics = self.calculate_mean_reversion_metrics(prices)

            if self.should_trade(signal, metrics):
                signals.append(signal)

        return signals
