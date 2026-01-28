"""
Regime change detector for market regime transitions.

This module implements the Single Responsibility Principle by focusing
solely on detecting regime changes in time series data.

Compares current Hurst values with historical values to detect
significant changes in market regime that may require strategy adjustments.
"""

import logging
from datetime import datetime

from app.services.hurst_analysis.models import MarketRegime, RegimeChange
from app.services.hurst_analysis.protocols import (
    HistoricalTrackerProtocol,
    RegimeClassifierProtocol,
)

logger = logging.getLogger(__name__)


class RegimeChangeDetector:
    """
    Detects regime changes in market conditions.

    This class follows the Single Responsibility Principle - it only
    detects regime changes. It does not calculate Hurst exponents,
    classify regimes, or store historical data (those are handled by
    other components).

    Attributes:
        classifier: Regime classifier for regime determination
        threshold: Minimum Hurst difference to consider as change

    Example:
        >>> detector = RegimeChangeDetector(classifier, threshold=0.1)
        >>> change = detector.detect_change("AAPL", tracker.get_history)
        >>> if change:
        ...     print(f"Regime changed: {change.old_regime} -> {change.new_regime}")
    """

    def __init__(
        self,
        classifier: RegimeClassifierProtocol,
        threshold: float = 0.1,
    ) -> None:
        """
        Initialize regime change detector.

        Args:
            classifier: Regime classifier for determining regimes
            threshold: Minimum Hurst difference for change detection (default 0.1)

        Raises:
            ValueError: If threshold is not positive
        """
        if threshold <= 0:
            raise ValueError(f"Threshold must be positive, got {threshold}")

        self.classifier = classifier
        self.threshold = threshold

    def detect_change(
        self,
        symbol: str,
        get_history_func: callable,
        lookback_periods: int = 10,
    ) -> RegimeChange | None:
        """
        Detect if there has been a regime change for a symbol.

        Compares current Hurst value with historical values to detect
        significant changes in market regime.

        Detection logic:
        1. Retrieve historical values
        2. Compare current vs lookback-periods-ago value
        3. Check if Hurst difference exceeds threshold
        4. Verify that regime actually changed (not just crossed threshold)

        Args:
            symbol: Symbol to check
            get_history_func: Callable that returns list of (timestamp, hurst) tuples
            lookback_periods: Number of historical periods to compare (default 10)

        Returns:
            RegimeChange object if change detected, None otherwise

        Example:
            >>> detector = RegimeChangeDetector(classifier)
            >>> change = detector.detect_change("AAPL", tracker.get_history)
            >>> if change:
            ...     print(f"Regime changed: {change.old_regime} -> {change.new_regime}")
        """
        # Get historical data
        history = get_history_func(symbol)

        if not history or len(history) < lookback_periods + 1:
            logger.debug(
                f"Insufficient history for {symbol}: {len(history) if history else 0} "
                f"< {lookback_periods + 1} required"
            )
            return None

        # Get current and previous Hurst values
        current_ts, current_hurst = history[-1]
        previous_ts, previous_hurst = history[-lookback_periods - 1]

        # Calculate absolute difference
        hurst_diff = abs(current_hurst - previous_hurst)

        # Check if difference exceeds threshold
        if hurst_diff < self.threshold:
            logger.debug(
                f"No significant change for {symbol}: "
                f"Hurst diff {hurst_diff:.4f} < threshold {self.threshold}"
            )
            return None

        # Classify regimes
        old_regime = self.classifier.classify(previous_hurst)
        new_regime = self.classifier.classify(current_hurst)

        # Only report if regime actually changed
        if old_regime == new_regime:
            logger.debug(
                f"Hurst changed but regime same for {symbol}: "
                f"{old_regime.value} (diff: {hurst_diff:.4f})"
            )
            return None

        # Calculate confidence based on difference magnitude
        confidence = min(1.0, hurst_diff / self.threshold)

        change = RegimeChange(
            timestamp=current_ts,
            old_regime=old_regime,
            new_regime=new_regime,
            old_hurst=previous_hurst,
            new_hurst=current_hurst,
            confidence=confidence,
        )

        logger.warning(
            f"REGIME CHANGE DETECTED for {symbol}: "
            f"{old_regime.value} -> {new_regime.value} "
            f"(H: {previous_hurst:.3f} -> {current_hurst:.3f}, "
            f"confidence: {confidence:.2f})"
        )

        return change
