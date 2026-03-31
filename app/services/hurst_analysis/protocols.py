from __future__ import annotations

"""Protocol interfaces for Hurst Analysis components.

This module defines all Protocol interfaces used throughout the hurst_analysis module.
Following the Interface Segregation Principle (ISP), each protocol is focused and minimal.
Following the Dependency Inversion Principle (DIP), high-level modules depend on these
abstractions rather than concrete implementations.

All protocols use structural subtyping (duck typing) - any class implementing
the required methods automatically satisfies the protocol.
"""


import logging
from typing import TYPE_CHECKING, Protocol

logger = logging.getLogger(__name__)

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from datetime import datetime

    import numpy as np

    from app.services.hurst_analysis.models import (
        MarketRegime,
        RegimeChange,
        StrategyRecommendation,
    )


class HurstCalculator(Protocol):
    """
    Protocol for Hurst exponent calculation methods.


    Any class that implements calculate() can be used as a Hurst calculator.
    This follows the Open/Closed Principle - new calculation methods can be
    added without modifying existing code.
    """

    def calculate(self, series: np.ndarray) -> tuple[float, list[float] | None, list[int] | None]:
        """
        Calculate Hurst exponent from time series.

        Args:
            series: Input time series as numpy array

        Returns:
            Tuple of (hurst_exponent, rs_values, window_sizes)
        """
        ...


class RegimeClassifierProtocol(Protocol):
    """Protocol for market regime classification."""

    def classify(self, hurst_exponent: float) -> MarketRegime:
        """Classify market regime based on Hurst exponent."""
        ...


class StrategyRecommenderProtocol(Protocol):
    """Protocol for trading strategy recommendations."""

    def recommend(self, regime: MarketRegime, hurst_exponent: float) -> StrategyRecommendation:
        """Recommend trading strategy based on regime."""
        ...


class ConfidenceCalculatorProtocol(Protocol):
    """Protocol for confidence calculation."""

    def calculate_confidence(self, series: np.ndarray, hurst_exponent: float) -> float:
        """Calculate confidence in Hurst estimate."""
        ...


class HistoricalTrackerProtocol(Protocol):
    """Protocol for historical data tracking."""

    def store(self, symbol: str, timestamp: datetime, value: float) -> None:
        """Store a historical Hurst value."""
        ...

    def get_history(self, symbol: str) -> list[tuple[datetime, float]]:
        """Get historical Hurst values for a symbol."""
        ...


class ChangeDetectorProtocol(Protocol):
    """Protocol for regime change detection."""

    def detect_change(
        self,
        symbol: str,
        get_history_func: callable,
        lookback_periods: int = 10,
        threshold: float = 0.1,
    ) -> RegimeChange | None:
        """Detect regime change for a symbol."""
        ...


logger.debug(
    "HurstAnalysis protocols loaded",
    extra={
        "component": "hurst_analysis_protocols",
        "operation": "module_init",
        "protocols": [
            "HurstCalculator",
            "RegimeClassifierProtocol",
            "StrategyRecommenderProtocol",
            "ConfidenceCalculatorProtocol",
            "HistoricalTrackerProtocol",
            "ChangeDetectorProtocol",
        ],
    },
)
