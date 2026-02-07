"""
Market regime classifier based on Hurst exponent.

This module implements the Single Responsibility Principle by focusing
solely on classifying market regimes based on Hurst exponent values.

According to Ernest Chan (Algorithmic Trading, Rule 2.2):
- H < 0.5: Mean-reverting (anti-persistent)
- H ≈ 0.5: Random walk (efficient market)
- H > 0.5: Trending (persistent)
"""

import logging


from app.services.hurst_analysis.models import MarketRegime

logger = logging.getLogger(__name__)


class RegimeClassifier:
    """
    Classifies market regime based on Hurst exponent.

    This class follows the Single Responsibility Principle - it only
    classifies regimes based on Hurst values. It does not calculate
    Hurst exponents, recommend strategies, or detect changes.

    Attributes:
        tolerance: Tolerance band around 0.5 for random walk classification

    Example:
        >>> classifier = RegimeClassifier(tolerance=0.05)
        >>> regime = classifier.classify(0.3)
        >>> print(regime)  # MarketRegime.MEAN_REVERTING
    """

    def __init__(self, tolerance: float = 0.05) -> None:
        """
        Initialize regime classifier.

        Args:
            tolerance: Tolerance band around 0.5 (default 5%)
                        Values within (0.5 - tolerance, 0.5 + tolerance)
                        are classified as RANDOM_WALK
        """
        if not 0 < tolerance < 0.5:
            raise ValueError(f"Tolerance must be between 0 and 0.5, got {tolerance}")

        self.tolerance = tolerance

    def classify(self, hurst_exponent: float) -> MarketRegime:
        """
        Classify market regime based on Hurst exponent.

        Classification rules (Ernest Chan Rule 2.2):
        - H < 0.5 - tolerance: MEAN_REVERTING
        - 0.5 - tolerance <= H <= 0.5 + tolerance: RANDOM_WALK
        - H > 0.5 + tolerance: TRENDING

        Args:
            hurst_exponent: Calculated Hurst exponent value

        Returns:
            MarketRegime classification

        Raises:
            ValueError: If hurst_exponent is not in valid range [0, 1]

        Example:
            >>> classifier = RegimeClassifier()
            >>> classifier.classify(0.3)  # MarketRegime.MEAN_REVERTING
            >>> classifier.classify(0.5)  # MarketRegime.RANDOM_WALK
            >>> classifier.classify(0.7)  # MarketRegime.TRENDING
        """
        if not 0 <= hurst_exponent <= 1:
            raise ValueError(f"Hurst exponent must be in range [0, 1], got {hurst_exponent}")

        if hurst_exponent < 0.5 - self.tolerance:
            return MarketRegime.MEAN_REVERTING
        elif hurst_exponent > 0.5 + self.tolerance:
            return MarketRegime.TRENDING
        else:
            return MarketRegime.RANDOM_WALK
