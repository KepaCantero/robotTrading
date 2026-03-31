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
    ServiceError,
    ValidationError,
    service_error_handler,
)

# Backward-compatible alias for code that references ServiceException
ServiceException = ServiceError

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
    "ServiceError",
    "ServiceException",
    "ValidationError",
    "service_error_handler",
]
