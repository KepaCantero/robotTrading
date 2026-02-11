# pylint: disable=import-error,unsupported-binary-operation
# mypy: ignore-errors
"""
Order Flow Imbalance (OFI) Calculator.

This module implements OFI calculations from order book data following
the methodology in Cont & Kukanov (2017) and related literature.

OFI measures the imbalance between buy and sell order flow and is a
strong predictor of short-term price movements.

References:
- Cont, R., & Kukanov, A. (2017) "Order Flow Imbalance and Price Movement"
- Aldridge, I. (2013) "High-Frequency Trading"
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import numpy as np

from app.market_microstructure.ofi.models import (
    CumulativeOFI,
    OFIConfig,
    OFIStatistics,
    OrderBookSnapshot,
)

logger = logging.getLogger(__name__)


class InvalidPriceError(ValueError):
    """Raised when an invalid price is provided."""


@dataclass
class OFIResult:
    """
    Result of OFI calculation.

    Attributes:
        ofi: Order Flow Imbalance value
        bid_volume: Total bid volume
        ask_volume: Total ask volume
        total_volume: Total volume
        timestamp: Calculation timestamp
        is_valid: Whether OFI is valid (passes volume/spread checks)
        reason: Reason if invalid
    """

    ofi: float
    bid_volume: int
    ask_volume: int
    total_volume: int
    timestamp: datetime
    is_valid: bool
    reason: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "ofi": self.ofi,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "total_volume": self.total_volume,
            "timestamp": self.timestamp.isoformat(),
            "is_valid": self.is_valid,
            "reason": self.reason,
        }


class OFICalculator:
    """
    Calculate Order Flow Imbalance from order book data.

    OFI is calculated as:
        OFI = (bid_volume - ask_volume) / (bid_volume + ask_volume)

    Range: [-1, 1]
    - OFI > 0: Buying pressure (more bids)
    - OFI < 0: Selling pressure (more asks)
    - OFI ≈ 0: Balanced flow

    The calculator supports:
    1. Basic OFI from order book snapshots
    2. Volume-weighted OFI
    3. Top-level OFI (best bid/ask only)
    4. Cumulative OFI (COFI)
    5. OFI momentum
    6. Smoothed OFI

    Example:
        >>> calculator = OFICalculator(config=OFIConfig())
        >>> result = calculator.calculate_ofi(order_book_snapshot)
        >>> print(f"OFI: {result.ofi:.3f}")
        >>> cofi = calculator.calculate_cumulative_ofi([0.1, 0.2, 0.15])
    """

    def __init__(self, config: OFIConfig | None = None):
        """
        Initialize OFI Calculator.

        Args:
            config: OFI configuration (uses defaults if None)
        """
        self.config = config or OFIConfig()
        self._ofi_history: deque[float] = deque(maxlen=self.config.lookback_periods)
        self._cofi_tracker: CumulativeOFI | None = None

    def calculate_ofi(self, order_book: OrderBookSnapshot) -> OFIResult:
        """
        Calculate OFI from order book snapshot.

        Args:
            order_book: Order book snapshot with bids and asks

        Returns:
            OFIResult with calculated OFI and validation status

        Example:
            >>> snapshot = OrderBookSnapshot(
            ...     'AAPL', datetime.now(),
            ...     [(Decimal('100.50'), 100)],
            ...     [(Decimal('100.51'), 50)]
            ... )
            >>> result = calculator.calculate_ofi(snapshot)
            >>> print(f"OFI: {result.ofi:.3f}")  # Expected: (100-50)/(150) = 0.333
        """
        timestamp = order_book.timestamp

        # Get volumes based on configuration
        if self.config.use_weighted_ofi:
            bid_vol, ask_vol = self._calculate_weighted_volumes(order_book)
        else:
            bid_vol = order_book.bid_volume
            ask_vol = order_book.ask_volume

        total_vol = bid_vol + ask_vol

        # Validate minimum volume
        if total_vol < self.config.min_volume:
            return OFIResult(
                ofi=0.0,
                bid_volume=bid_vol,
                ask_volume=ask_vol,
                total_volume=total_vol,
                timestamp=timestamp,
                is_valid=False,
                reason=f"Volume below minimum: {total_vol} < {self.config.min_volume}",
            )

        # Validate spread
        spread_bps = order_book.spread_bps
        if spread_bps is not None and spread_bps > self.config.max_spread_bps:
            return OFIResult(
                ofi=0.0,
                bid_volume=bid_vol,
                ask_volume=ask_vol,
                total_volume=total_vol,
                timestamp=timestamp,
                is_valid=False,
                reason=f"Spread too wide: {spread_bps:.1f} bps > {self.config.max_spread_bps}",
            )

        # Calculate OFI
        if total_vol == 0:
            ofi = 0.0
        else:
            ofi = (bid_vol - ask_vol) / total_vol

        # Clamp to configured range for numerical stability
        ofi = max(self.config.ofi_min_value, min(self.config.ofi_max_value, ofi))

        # Store in history
        self._ofi_history.append(ofi)

        return OFIResult(
            ofi=ofi,
            bid_volume=bid_vol,
            ask_volume=ask_vol,
            total_volume=total_vol,
            timestamp=timestamp,
            is_valid=True,
        )

    def _validate_price(self, price: Decimal | None) -> None:
        """
        Validate price for OFI calculations.

        Args:
            price: Price to validate

        Raises:
            InvalidPriceError: If price is invalid (negative, zero, or NaN)
        """
        if price is None:
            return  # None is handled separately by callers

        # Check if price is negative
        if price < 0:
            raise InvalidPriceError(f"Price cannot be negative: {price}")

        # Check if price is zero
        if price == 0:
            raise InvalidPriceError("Price cannot be zero")

        # Check if price is NaN (using comparison with itself)
        if price != price:  # pylint: disable=comparison-with-itself; NaN != NaN is True
            raise InvalidPriceError(f"Price cannot be NaN: {price}")

    def _calculate_weighted_volumes(self, order_book: OrderBookSnapshot) -> tuple[int, int]:
        """
        Calculate volume-weighted bid and ask volumes.

        Weighting gives more importance to orders closer to the mid price,
        as they are more likely to be executed.

        Args:
            order_book: Order book snapshot

        Returns:
            Tuple of (weighted_bid_volume, weighted_ask_volume)

        Raises:
            InvalidPriceError: If mid_price is invalid
        """
        mid_price = order_book.mid_price
        if mid_price is not None:
            self._validate_price(mid_price)

        if mid_price is None or mid_price == 0:
            return order_book.bid_volume, order_book.ask_volume

        # Weight bids by proximity to mid (closer = higher weight)
        weighted_bid_vol = 0
        for price, qty in order_book.bids[: self.config.top_levels]:
            self._validate_price(price)
            distance = float((mid_price - price) / mid_price)
            weight = max(
                self.config.weight_min,
                self.config.weight_max - distance * self.config.distance_multiplier
            )  # Decay weight with distance
            weighted_bid_vol += int(qty * weight)

        # Weight asks by proximity to mid
        weighted_ask_vol = 0
        for price, qty in order_book.asks[: self.config.top_levels]:
            self._validate_price(price)
            distance = float((price - mid_price) / mid_price)
            weight = max(
                self.config.weight_min,
                self.config.weight_max - distance * self.config.distance_multiplier
            )
            weighted_ask_vol += int(qty * weight)

        return weighted_bid_vol, weighted_ask_vol

    def calculate_top_level_ofi(self, order_book: OrderBookSnapshot) -> float | None:
        """
        Calculate OFI using only top-level (best bid/ask) volumes.

        Top-level OFI is more sensitive to immediate order flow pressure.

        Args:
            order_book: Order book snapshot

        Returns:
            Top-level OFI or None if no top level
        """
        if not order_book.bids or not order_book.asks:
            return None

        best_bid_vol = order_book.bids[0][1]  # (price, quantity)
        best_ask_vol = order_book.asks[0][1]
        total = best_bid_vol + best_ask_vol

        if total == 0:
            return 0.0

        return (best_bid_vol - best_ask_vol) / total

    def calculate_cumulative_ofi(self, ofi_history: list[float]) -> list[float]:
        """
        Calculate cumulative OFI (COFI).

        COFI[t] = sum(OFI[0:t])

        Cumulative OFI helps identify sustained buying/selling pressure
        and potential mean reversion opportunities.

        Args:
            ofi_history: List of OFI values

        Returns:
            List of cumulative OFI values (same length as input)

        Example:
            >>> calculator = OFICalculator()
            >>> cofi = calculator.calculate_cumulative_ofi([0.1, 0.2, -0.1])
            >>> print(cofi)  # [0.1, 0.3, 0.2]
        """
        if not ofi_history:
            return []

        cofi = []
        running_sum = 0.0
        for ofi in ofi_history:
            running_sum += ofi
            cofi.append(running_sum)

        return cofi

    def calculate_ofi_momentum(self, ofi_history: list[float], window: int = 10) -> float:
        """
        Calculate OFI momentum (rate of change).

        Momentum is calculated as the difference between the average
        OFI in the recent window vs. the previous window.

        Args:
            ofi_history: List of OFI values
            window: Window size for momentum calculation

        Returns:
            Momentum value (positive = increasing buying pressure)

        Example:
            >>> calculator = OFICalculator()
            >>> momentum = calculator.calculate_ofi_momentum([0.1, 0.2, 0.3, 0.25])
            >>> # Positive momentum indicates increasing buying pressure
        """
        if len(ofi_history) < window * self.config.window_size_multiplier:
            return 0.0

        recent = np.mean(ofi_history[-window:])
        previous = np.mean(
            ofi_history[
                -(window * self.config.window_size_multiplier) : -window
            ]
        )

        return float(recent - previous)

    def calculate_ofi_velocity(self, ofi_history: list[float], window: int = 5) -> float:
        """
        Calculate OFI velocity (first derivative).

        Velocity measures how quickly OFI is changing.

        Args:
            ofi_history: List of OFI values
            window: Window for velocity calculation

        Returns:
            Velocity (positive = OFI increasing)
        """
        if len(ofi_history) < 2:
            return 0.0

        # Simple velocity: change over last window
        if len(ofi_history) >= window:
            return ofi_history[-1] - ofi_history[-window]
        else:
            return ofi_history[-1] - ofi_history[0]

    def calculate_smoothed_ofi(
        self, ofi_history: list[float], window: int | None = None
    ) -> list[float]:
        """
        Calculate exponentially-weighted moving average of OFI.

        Smoothing helps reduce noise in OFI signals.

        Args:
            ofi_history: List of OFI values
            window: Smoothing window (uses config default if None)

        Returns:
            List of smoothed OFI values
        """
        if not ofi_history:
            return []

        window = window or self.config.smoothing_window

        # Convert to numpy array
        ofi_array = np.array(ofi_history)

        # Calculate exponential weights using specialized formula
        alpha = self.config.ema_alpha_numerator / (window + 1)
        smoothed = np.zeros_like(ofi_array)
        smoothed[0] = ofi_array[0]

        for i in range(1, len(ofi_array)):
            smoothed[i] = alpha * ofi_array[i] + (1 - alpha) * smoothed[i - 1]

        return smoothed.tolist()

    def calculate_ofi_std_score(self, ofi: float, ofi_history: list[float]) -> float | None:
        """
        Calculate z-score of OFI relative to history.

        Args:
            ofi: Current OFI value
            ofi_history: Historical OFI values

        Returns:
            Z-score or None if insufficient history
        """
        if len(ofi_history) < 2:
            return None

        mean = float(np.mean(ofi_history))
        std = float(np.std(ofi_history))

        if std == 0:
            return None

        return (ofi - mean) / std

    def detect_ofi_regime(self, ofi_history: list[float], window: int = 20) -> str:
        """
        Detect the current OFI regime.

        Regimes:
        - 'bullish_flow': Sustained positive OFI
        - 'bearish_flow': Sustained negative OFI
        - 'balanced': OFI oscillating around zero

        Args:
            ofi_history: List of OFI values
            window: Window for regime detection

        Returns:
            Regime string
        """
        if len(ofi_history) < window:
            return "insufficient_data"

        recent = ofi_history[-window:]
        mean_ofi = float(np.mean(recent))
        std_ofi = float(np.std(recent))

        # Use mean and variability to determine regime
        if (
            mean_ofi > self.config.regime_bullish_mean_threshold
            and std_ofi < self.config.regime_stable_std_threshold
        ):
            return "bullish_flow"
        elif (
            mean_ofi < self.config.regime_bearish_mean_threshold
            and std_ofi < self.config.regime_stable_std_threshold
        ):
            return "bearish_flow"
        elif std_ofi > self.config.regime_volatile_std_threshold:
            return "volatile"
        else:
            return "balanced"

    def calculate_ofi_autocorrelation(
        self, ofi_history: list[float], max_lag: int = 10
    ) -> list[float]:
        """
        Calculate autocorrelation of OFI at various lags.

        OFI autocorrelation indicates persistence of order flow.

        Args:
            ofi_history: List of OFI values
            max_lag: Maximum lag to calculate

        Returns:
            List of autocorrelation values
        """
        if len(ofi_history) < max_lag + self.config.max_lag_offset:
            return []

        ofi_array = np.array(ofi_history)
        ofi_array = ofi_array - np.mean(ofi_array)  # Remove mean

        autocorr = []
        for lag in range(1, max_lag + 1):
            if len(ofi_array) > lag:
                corr = np.corrcoef(ofi_array[:-lag], ofi_array[lag:])[0, 1]
                autocorr.append(float(corr) if not np.isnan(corr) else 0.0)
            else:
                autocorr.append(0.0)

        return autocorr

    def calculate_ofi_statistics(
        self,
        ofi_history: list[float],
        returns_history: Optional[list[float]] = None,
        symbol: str = "",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> OFIStatistics | None:
        """
        Calculate comprehensive OFI statistics.

        Args:
            ofi_history: List of OFI values
            returns_history: Optional list of corresponding returns
            symbol: Trading symbol
            period_start: Period start time
            period_end: Period end time

        Returns:
            OFIStatistics object or None if insufficient data
        """
        if len(ofi_history) < 5:
            logger.debug(
                "Insufficient OFI history for statistics calculation",
                extra={
                    "symbol": symbol,
                    "history_length": len(ofi_history),
                    "minimum_required": 5,
                },
            )
            return None

        try:
            ofi_array = np.array(ofi_history)

            # Basic statistics
            mean_ofi = float(np.mean(ofi_array))
            std_ofi = float(np.std(ofi_array))
            max_ofi = float(np.max(ofi_array))
            min_ofi = float(np.min(ofi_array))
            median_ofi = float(np.median(ofi_array))

            # Higher moments
            from scipy.stats import kurtosis, skew

            skewness = float(skew(ofi_array))
            kurt = float(kurtosis(ofi_array))

            # Autocorrelation at lag 1
            if len(ofi_history) > 10:
                autocorr_1 = float(np.corrcoef(ofi_array[:-1], ofi_array[1:])[0, 1])
                if np.isnan(autocorr_1):
                    autocorr_1 = 0.0
            else:
                autocorr_1 = 0.0

            # Predictive power (correlation with future returns)
            predictive_power = 0.0
            if returns_history and len(returns_history) == len(ofi_history):
                returns_array = np.array(returns_history)
                corr = np.corrcoef(ofi_array, returns_array)[0, 1]
                predictive_power = float(corr) if not np.isnan(corr) else 0.0

            logger.info(
                "OFI statistics calculated successfully",
                extra={
                    "symbol": symbol,
                    "mean_ofi": mean_ofi,
                    "std_ofi": std_ofi,
                    "history_length": len(ofi_history),
                },
            )

            return OFIStatistics(
                symbol=symbol,
                period_start=period_start or datetime.now(timezone.utc),
                period_end=period_end or datetime.now(timezone.utc),
                mean_ofi=mean_ofi,
                std_ofi=std_ofi,
                max_ofi=max_ofi,
                min_ofi=min_ofi,
                median_ofi=median_ofi,
                skewness=skewness,
                kurtosis=kurt,
                autocorr_1=autocorr_1,
                predictive_power=predictive_power,
            )

        except Exception as e:
            logger.error(
                "Failed to calculate OFI statistics",
                exc_info=True,
                extra={
                    "symbol": symbol,
                    "history_length": len(ofi_history),
                    "returns_length": len(returns_history) if returns_history else 0,
                    "error_type": type(e).__name__,
                },
            )
            return None

    def get_cofi_tracker(self, symbol: str, start_time: datetime) -> CumulativeOFI:
        """
        Get or create a cumulative OFI tracker.

        Args:
            symbol: Trading symbol
            start_time: Start time for tracking

        Returns:
            CumulativeOFI instance
        """
        if self._cofi_tracker is None or self._cofi_tracker.symbol != symbol:
            self._cofi_tracker = CumulativeOFI(symbol=symbol, start_time=start_time)
        return self._cofi_tracker

    def update_cofi(self, ofi_value: float, timestamp: datetime) -> float:
        """
        Update cumulative OFI with new value.

        Args:
            ofi_value: New OFI value
            timestamp: Timestamp of update

        Returns:
            Updated cumulative OFI value
        """
        if self._cofi_tracker is None:
            logger.warning(
                "COFI tracker not initialized. Call get_cofi_tracker first.",
                extra={"ofi_value": ofi_value},
            )
            return 0.0

        self._cofi_tracker = self._cofi_tracker.update(ofi_value, timestamp)
        return self._cofi_tracker.current_cofi

    def get_ofi_history(self) -> list[float]:
        """
        Get current OFI history.

        Returns:
            List of historical OFI values
        """
        return list(self._ofi_history)

    def reset_history(self) -> None:
        """Reset OFI history."""
        self._ofi_history.clear()
        self._cofi_tracker = None
        logger.info(
            "OFI history reset",
            extra={"had_tracker": self._cofi_tracker is not None},
        )

    def calculate_predictive_power(
        self, ofi_history: list[float], returns_history: list[float]
    ) -> dict:
        """
        Calculate the predictive power of OFI for returns.

        Tests correlation at different lags to find optimal prediction horizon.

        Args:
            ofi_history: List of OFI values
            returns_history: List of corresponding returns

        Returns:
            Dictionary with predictive power metrics
        """
        if (
            len(ofi_history) != len(returns_history)
            or len(ofi_history) < self.config.min_predictive_power_samples
        ):
            return {"error": "Insufficient or mismatched data"}

        ofi_array = np.array(ofi_history)
        returns_array = np.array(returns_history)

        results = {
            "contemporaneous": 0.0,
            "lead_1": 0.0,
            "lead_5": 0.0,
            "lead_10": 0.0,
            "max_correlation": 0.0,
            "best_lag": 0,
        }

        # Contemporaneous correlation
        corr = np.corrcoef(ofi_array, returns_array)[0, 1]
        results["contemporaneous"] = float(corr) if not np.isnan(corr) else 0.0

        # Lead correlations (OFI predicting future returns)
        for lag in [1, 5, 10]:
            if len(ofi_array) > lag:
                corr = np.corrcoef(ofi_array[:-lag], returns_array[lag:])[0, 1]
                results[f"lead_{lag}"] = float(corr) if not np.isnan(corr) else 0.0

        # Find best lag
        best_corr = 0.0
        best_lag = 0
        for lag in range(
            1, min(self.config.default_max_lag, len(ofi_array) // 2)
        ):
            corr = np.corrcoef(ofi_array[:-lag], returns_array[lag:])[0, 1]
            if not np.isnan(corr) and abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        results["max_correlation"] = float(best_corr)
        results["best_lag"] = best_lag

        return results
