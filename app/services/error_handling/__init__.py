"""
Error Handling & Robustness Services - T12.1

Provides error handling, fallback strategies, and graceful degradation for all services.
"""

from app.services.error_handling.error_handler import (
    BacktestError,
    ConfigurationError,
    ConservativeBacktestFallback,
    ConservativeRecommendationFallback,
    EqualWeightPortfolioFallback,
    ErrorHandler,
    FallbackStrategy,
    ParameterizationError,
    PortfolioError,
    RecommendationError,
    ServiceException,
    ValidationError,
    service_error_handler,
)

__all__ = [
    "BacktestError",
    "ConfigurationError",
    "ConservativeBacktestFallback",
    "ConservativeRecommendationFallback",
    "EqualWeightPortfolioFallback",
    "ErrorHandler",
    "FallbackStrategy",
    "ParameterizationError",
    "PortfolioError",
    "RecommendationError",
    "ServiceException",
    "ValidationError",
    "service_error_handler",
]
