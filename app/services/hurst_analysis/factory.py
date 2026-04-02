"""
Factory functions for creating Hurst Analysis components.

This module provides convenient factory functions for creating configured
instances of Hurst analysis components with sensible defaults.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.hurst_analysis.change_detector import RegimeChangeDetector
from app.services.hurst_analysis.confidence_calculator import ConfidenceCalculator
from app.services.hurst_analysis.historian import HistoricalDataTracker
from app.services.hurst_analysis.orchestrator import HurstExponentAnalyzer
from app.services.hurst_analysis.regime_classifier import RegimeClassifier
from app.services.hurst_analysis.rs_calculator import RSMethodCalculator
from app.services.hurst_analysis.strategy_recommender import StrategyRecommender

if TYPE_CHECKING:
    from app.services.hurst_analysis.protocols import (
        ChangeDetectorProtocol,
        ConfidenceCalculatorProtocol,
        HistoricalTrackerProtocol,
        HurstCalculator,
        RegimeClassifierProtocol,
        StrategyRecommenderProtocol,
    )

logger = logging.getLogger(__name__)


def create_default_analyzer(
    method: str = "rs",
    use_returns: bool = True,
) -> HurstExponentAnalyzer:
    """
    Create a HurstExponentAnalyzer with default components.

    Factory function for easy analyzer creation with sensible defaults.

    Args:
        method: Calculation method ('rs', 'variance', 'agg_var')
        use_returns: Whether to analyze log returns

    Returns:
        Configured HurstExponentAnalyzer

    Example:
        >>> analyzer = create_default_analyzer(method="rs")
        >>> result = analyzer.analyze(price_series)
    """
    calculator = _create_calculator(method)
    classifier = RegimeClassifier(tolerance=0.05)
    recommender = StrategyRecommender()
    confidence_calc = ConfidenceCalculator()
    historian = HistoricalDataTracker(max_history_per_symbol=100)
    change_detector = RegimeChangeDetector(classifier=classifier, threshold=0.1)

    return HurstExponentAnalyzer(
        calculator=calculator,
        classifier=classifier,
        recommender=recommender,
        confidence_calc=confidence_calc,
        historian=historian,
        change_detector=change_detector,
        use_returns=use_returns,
    )


def create_custom_analyzer(
    calculator: HurstCalculator,
    classifier: RegimeClassifierProtocol,
    recommender: StrategyRecommenderProtocol,
    confidence_calc: ConfidenceCalculatorProtocol,
    historian: HistoricalTrackerProtocol,
    change_detector: ChangeDetectorProtocol,
    use_returns: bool = True,
) -> HurstExponentAnalyzer:
    """
    Create a HurstExponentAnalyzer with custom components.

    Use this when you need full control over component configuration.

    Args:
        calculator: Hurst exponent calculator
        classifier: Market regime classifier
        recommender: Strategy recommender
        confidence_calc: Confidence calculator
        historian: Historical data tracker
        change_detector: Regime change detector
        use_returns: Whether to analyze log returns

    Returns:
        Configured HurstExponentAnalyzer

    Example:
        >>> calculator = RSMethodCalculator(min_window=20, num_windows=30)
        >>> classifier = RegimeClassifier(tolerance=0.03)
        >>> analyzer = create_custom_analyzer(
        ...     calculator=calculator,
        ...     classifier=classifier,
        ...     recommender=StrategyRecommender(),
        ...     confidence_calc=ConfidenceCalculator(),
        ...     historian=HistoricalDataTracker(200),
        ...     change_detector=RegimeChangeDetector(classifier, 0.15)
        ... )
    """
    return HurstExponentAnalyzer(
        calculator=calculator,
        classifier=classifier,
        recommender=recommender,
        confidence_calc=confidence_calc,
        historian=historian,
        change_detector=change_detector,
        use_returns=use_returns,
    )


def _create_calculator(method: str) -> HurstCalculator:
    """
    Create a calculator based on method name.

    Args:
        method: Calculation method ('rs', 'variance', 'agg_var')

    Returns:
        Configured calculator

    Raises:
        ValueError: If method is unknown
    """
    if method == "rs":
        return RSMethodCalculator(min_window=10, num_windows=20)
    elif method == "variance":
        from app.services.hurst_analysis.variance_calculator import VarianceMethodCalculator

        return VarianceMethodCalculator()
    elif method == "agg_var":
        from app.services.hurst_analysis.variance_calculator import AggregatedVarianceCalculator

        return AggregatedVarianceCalculator()
    else:
        logger.warning(f"Unknown method: {method}, using R/S")
        return RSMethodCalculator(min_window=10, num_windows=20)
