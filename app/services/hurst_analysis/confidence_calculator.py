"""
Confidence calculator for Hurst exponent estimates.

This module implements the Single Responsibility Principle by focusing
solely on calculating confidence levels for Hurst exponent estimates.

In production, this should use bootstrapping for proper confidence intervals
following López de Prado's methods (Rule 3). The current implementation
uses a simplified approach based on sample size and distance from random walk.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    Calculates confidence in Hurst exponent estimates.

    This class follows the Single Responsibility Principle - it only
    calculates confidence values. It does not calculate Hurst exponents
    or classify regimes.

    The confidence calculation is based on:
    1. Sample size (more data = higher confidence)
    2. Distance from 0.5 (more extreme values are more confident)

    In production, use bootstrapping for proper confidence intervals.

    Attributes:
        min_samples: Minimum samples for reasonable confidence
        good_samples: Threshold for good confidence
        excellent_samples: Threshold for excellent confidence

    Example:
        >>> calculator = ConfidenceCalculator()
        >>> confidence = calculator.calculate_confidence(series, 0.65)
        >>> print(f"Confidence: {confidence:.2%}")
    """

    def __init__(
        self,
        min_samples: int = 100,
        good_samples: int = 500,
        excellent_samples: int = 1000,
    ) -> None:
        """
        Initialize confidence calculator.

        Args:
            min_samples: Minimum samples for baseline confidence (default 100)
            good_samples: Threshold for good confidence (default 500)
            excellent_samples: Threshold for excellent confidence (default 1000)
        """
        if min_samples < 1:
            raise ValueError(f"min_samples must be >= 1, got {min_samples}")
        if good_samples <= min_samples:
            raise ValueError(f"good_samples must be > min_samples, got {good_samples}")
        if excellent_samples <= good_samples:
            raise ValueError(f"excellent_samples must be > good_samples, got {excellent_samples}")

        self.min_samples = min_samples
        self.good_samples = good_samples
        self.excellent_samples = excellent_samples

    def calculate_confidence(self, series: np.ndarray, hurst_exponent: float) -> float:
        """
        Calculate confidence in Hurst exponent estimate.

        This is a simplified confidence calculation.
        In production, use bootstrapping for proper confidence intervals
        (Rule 3 - López de Prado).

        Base confidence on sample size:
        - n < min_samples: 0.5 (low confidence)
        - min_samples <= n < good_samples: 0.7 (moderate confidence)
        - good_samples <= n < excellent_samples: 0.85 (good confidence)
        - n >= excellent_samples: 0.95 (excellent confidence)

        Adjustment based on distance from 0.5:
        - More extreme values (closer to 0 or 1) increase confidence
        - Maximum adjustment: +0.1

        Args:
            series: Time series analyzed
            hurst_exponent: Calculated Hurst exponent

        Returns:
            Confidence value [0, 1]

        Example:
            >>> calculator = ConfidenceCalculator()
            >>> series = np.random.randn(1000)
            >>> confidence = calculator.calculate_confidence(series, 0.65)
            >>> print(f"Confidence: {confidence:.2%}")
        """
        # Base confidence on sample size
        n = len(series)

        if n < self.min_samples:
            base_confidence = 0.5
        elif n < self.good_samples:
            base_confidence = 0.7
        elif n < self.excellent_samples:
            base_confidence = 0.85
        else:
            base_confidence = 0.95

        # Adjust based on distance from 0.5
        # More extreme values are more confident
        distance_from_random = abs(hurst_exponent - 0.5)
        adjustment = min(0.1, distance_from_random * 0.2)

        confidence = min(1.0, base_confidence + adjustment)

        return confidence
