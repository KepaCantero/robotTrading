"""
Core Exceptions for AlgoTrading Application

This module provides centralized exception definitions for the application.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AlgoTradingError(Exception):
    """Base exception for all AlgoTrading errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

        # Log exception creation with structured context
        logger.debug(
            f"Exception created: {self.__class__.__name__}",
            extra={
                "exception_type": self.__class__.__name__,
                "error_code": error_code,
                "message": message,
            },
        )


class BacktestError(AlgoTradingError):
    """Exception raised for backtest-related errors."""

    pass


class ValidationError(AlgoTradingError):
    """Exception raised for validation errors."""

    pass


class ConfigurationError(AlgoTradingError):
    """Exception raised for configuration-related errors."""

    pass


class DataError(AlgoTradingError):
    """Exception raised for data-related errors."""

    pass


class TradingError(AlgoTradingError):
    """Exception raised for trading-related errors."""

    pass


class PortfolioError(AlgoTradingError):
    """Exception raised for portfolio-related errors."""

    pass


class SignalError(AlgoTradingError):
    """Exception raised for signal-related errors."""

    pass


class BrokerError(AlgoTradingError):
    """Exception raised for broker-related errors."""

    pass


class MarketDataError(AlgoTradingError):
    """Exception raised for market data errors."""

    pass


class StrategyError(AlgoTradingError):
    """Exception raised for strategy-related errors."""

    pass


class OptimizationError(AlgoTradingError):
    """Exception raised for optimization-related errors."""

    pass


class DeploymentError(AlgoTradingError):
    """Exception raised for deployment-related errors."""

    pass


class AuthenticationError(AlgoTradingError):
    """Exception raised for authentication errors."""

    pass


class AuthorizationError(AlgoTradingError):
    """Exception raised for authorization errors."""

    pass


class RateLimitError(AlgoTradingError):
    """Exception raised when rate limits are exceeded."""

    pass


class TradingTimeoutError(AlgoTradingError):
    """Exception raised for timeout errors."""

    pass


class TradingConnectionError(AlgoTradingError):
    """Exception raised for connection errors."""

    pass


class AlgoTradingDatabaseError(AlgoTradingError):
    """Exception raised for database errors."""

    pass
