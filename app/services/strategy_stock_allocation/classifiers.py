"""
Market regime classification module.

Classifies market regimes based on Hurst exponent analysis
across different time horizons.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from app.core.centralized_config import StockAllocationSettings

from .calculators import HurstCalculator

logger = logging.getLogger(__name__)


class RegimeClassifier:
    """
    Classifies market regime using Hurst exponent analysis.

    Regimes:
    - momentum: H > 0.55 (trending behavior)
    - mean_reversion: H < 0.45 (reverting behavior)
    - neutral: 0.45 <= H <= 0.55 (random walk)
    """

    def __init__(
        self,
        config: StockAllocationSettings,
        hurst_calculator: HurstCalculator,
    ) -> None:
        """
        Initialize regime classifier.

        Args:
            config: Stock allocation configuration
            hurst_calculator: Hurst exponent calculator
        """
        self.config = config
        self.hurst_calculator = hurst_calculator

    def classify(self, prices: np.ndarray) -> dict[str, float | None]:
        """
        Classify market regime using Hurst exponent (short and long horizons).

        Args:
            prices: Price series

        Returns:
            Dictionary with H_short, H_long, and regime classification
        """
        if len(prices) < 250:
            logger.warning(f"Insufficient data for regime classification: {len(prices)} < 250")
            return {"H_short": None, "H_long": None, "regime": "unknown"}

        # Calculate H_short (50 days)
        prices_short = prices[-50:] if len(prices) >= 50 else prices
        h_short = self.hurst_calculator.calculate(prices_short)

        # Calculate H_long (250 days)
        prices_long = prices[-250:] if len(prices) >= 250 else prices
        h_long = self.hurst_calculator.calculate(prices_long)

        # Classify regime
        regime = "unknown"
        if h_long is not None:
            if h_long > self.config.HURST_MOMENTUM_THRESHOLD:
                regime = "momentum"
            elif h_long < self.config.HURST_MEAN_REVERSION_THRESHOLD:
                regime = "mean_reversion"
            else:
                regime = "neutral"
        elif h_short is not None:
            if h_short > 0.55:
                regime = "momentum"
            elif h_short < 0.45:
                regime = "mean_reversion"
            else:
                regime = "neutral"

        result = {"H_short": h_short, "H_long": h_long, "regime": regime}

        logger.debug(f"Regime classification: {result}")
        return result
