"""
Core Exceptions for AlgoTrading Application

This module provides centralized exception definitions for the application.
"""

from __future__ import annotations

import logging
from typing import Any, NoReturn, Optional

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


class APIError(AlgoTradingError):
    """Exception raised for API-related errors."""

    pass


class BusinessLogicError(AlgoTradingError):
    """Exception raised for business logic errors."""

    pass


# ---------------------------------------------------------------------------
# Helper functions with input validation
# ---------------------------------------------------------------------------


def _validate_message(message: object) -> str:
    """Validate that message is a non-empty, non-whitespace-only string.

    Rejects messages that are empty, consist only of whitespace, or contain
    only invisible Unicode characters (zero-width spaces, BOMs, etc.).
    """
    if not isinstance(message, str):
        raise ValueError("message must be a non-empty string")
    import unicodedata

    # Strip all characters that are whitespace or Unicode format/control
    # characters (category C*), leaving only visible meaningful content.
    stripped = "".join(
        ch
        for ch in message
        if not ch.isspace() and unicodedata.category(ch)[0] != "C"  # Cc, Cf, Cs, Co, Cn
    )
    if not stripped:
        raise ValueError("message must be a non-empty string")
    return message


def _raise_error(
    exc_class: type[AlgoTradingError],
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise a typed error after validating the message."""
    _validate_message(message)
    logger.debug(
        f"Raising {exc_class.__name__}",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise exc_class(message, error_code=error_code, details=details)


# Convenience aliases -- callers import by name, not from the internal _raise_error.


def raise_configuration_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise a ConfigurationError after validating the message."""
    _raise_error(ConfigurationError, message, error_code, details)


def raise_validation_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise a ValidationError after validating the message."""
    _raise_error(ValidationError, message, error_code, details)


def raise_business_logic_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise a BusinessLogicError after validating the message."""
    _raise_error(BusinessLogicError, message, error_code, details)


def raise_market_data_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise a MarketDataError after validating the message."""
    _raise_error(MarketDataError, message, error_code, details)


def raise_trading_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise a TradingError after validating the message."""
    _raise_error(TradingError, message, error_code, details)


def raise_database_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise an AlgoTradingDatabaseError after validating the message."""
    _raise_error(AlgoTradingDatabaseError, message, error_code, details)


def raise_authentication_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise an AuthenticationError after validating the message."""
    _raise_error(AuthenticationError, message, error_code, details)
