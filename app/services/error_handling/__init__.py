"""
Error Handling & Robustness Services - T12.1

Provides error handling, fallback strategies, and graceful degradation for all services.
"""

from app.services.error_handling.error_handler import (
    BacktestException,
    ConfigurationException,
    ConservativeBacktestFallback,
    ConservativeRecommendationFallback,
    EqualWeightPortfolioFallback,
    ErrorHandler,
    FallbackStrategy,
    ParameterizationException,
    PortfolioException,
    RecommendationException,
    ServiceException,
    ValidationException,
    service_error_handler,
)

__all__ = [
    "ServiceException",
    "BacktestException",
    "ValidationException",
    "ConfigurationException",
    "ParameterizationException",
    "RecommendationException",
    "PortfolioException",
    "FallbackStrategy",
    "ConservativeBacktestFallback",
    "EqualWeightPortfolioFallback",
    "ConservativeRecommendationFallback",
    "ErrorHandler",
    "service_error_handler",
]
