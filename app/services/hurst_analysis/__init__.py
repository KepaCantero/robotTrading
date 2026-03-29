"""
Hurst Analysis Module

A refactored, SOLID-compliant module for Hurst Exponent analysis and market regime detection.

This module follows SOLID principles:
- Single Responsibility: Each class has one reason to change
- Open/Closed: Extensible through protocols/interfaces
- Liskov Substitution: All calculators are substitutable
- Interface Segregation: Focused, minimal interfaces
- Dependency Inversion: Depend on abstractions, not concrete implementations

Architecture:
    Protocols: Abstract interfaces for all components
    Calculators: Separate implementations for each calculation method
    Services: Business logic components (classifier, recommender, etc.)
    Orchestrator: Coordinates all components

Example:
    >>> from app.services.hurst_analysis import HurstExponentAnalyzer, create_default_analyzer
    >>> analyzer = create_default_analyzer()
    >>> result = analyzer.analyze(price_series)
    >>> print(f"Hurst: {result.hurst_exponent:.3f}")

Author: Algorithmic Trading Team
Date: 2026-01-30
Version: 3.0.0 - SOLID Refactored
Compliance: SOLID Principles, Type Hints (Strict), Clean Architecture
"""

from app.services.hurst_analysis.change_detector import RegimeChangeDetector
from app.services.hurst_analysis.confidence_calculator import ConfidenceCalculator
from app.services.hurst_analysis.factory import create_custom_analyzer, create_default_analyzer
from app.services.hurst_analysis.historian import HistoricalDataTracker
from app.services.hurst_analysis.models import (
    HurstResult,
    MarketRegime,
    RegimeChange,
    StrategyRecommendation,
)
from app.services.hurst_analysis.orchestrator import HurstExponentAnalyzer
from app.services.hurst_analysis.protocols import (
    ChangeDetectorProtocol,
    ConfidenceCalculatorProtocol,
    HistoricalTrackerProtocol,
    HurstCalculator,
    RegimeClassifierProtocol,
    StrategyRecommenderProtocol,
)
from app.services.hurst_analysis.regime_classifier import RegimeClassifier
from app.services.hurst_analysis.rs_calculator import RSMethodCalculator
from app.services.hurst_analysis.strategy_recommender import StrategyRecommender
from app.services.hurst_analysis.variance_calculator import (
    AggregatedVarianceCalculator,
    VarianceMethodCalculator,
)

__all__ = [
    "AggregatedVarianceCalculator",
    "ChangeDetectorProtocol",
    "ConfidenceCalculator",
    "ConfidenceCalculatorProtocol",
    "HistoricalDataTracker",
    "HistoricalTrackerProtocol",
    # Protocols
    "HurstCalculator",
    # Main orchestrator and factories
    "HurstExponentAnalyzer",
    "HurstResult",
    # Models
    "MarketRegime",
    # Calculator implementations
    "RSMethodCalculator",
    "RegimeChange",
    "RegimeChangeDetector",
    # Service implementations
    "RegimeClassifier",
    "RegimeClassifierProtocol",
    "StrategyRecommendation",
    "StrategyRecommender",
    "StrategyRecommenderProtocol",
    "VarianceMethodCalculator",
    "create_custom_analyzer",
    "create_default_analyzer",
]

__version__ = "3.0.0"
