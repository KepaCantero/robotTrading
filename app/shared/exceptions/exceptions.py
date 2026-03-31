"""
Core Exceptions for AlgoTrading
Independent exception definitions to avoid circular imports
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
        logger.debug(
            "AlgoTradingError created",
            extra={"message": message, "error_code": error_code, "details": details},
        )


class ConfigurationError(AlgoTradingError):
    """Exception raised for configuration-related errors."""


class ValidationError(AlgoTradingError):
    """Exception raised for validation errors."""


class BusinessLogicError(AlgoTradingError):
    """Exception raised for business logic errors."""


class MarketDataError(AlgoTradingError):
    """Exception raised for market data errors."""


class TradingError(AlgoTradingError):
    """Exception raised for trading-related errors."""


class PortfolioError(AlgoTradingError):
    """Exception raised for portfolio-related errors."""


class SignalError(AlgoTradingError):
    """Exception raised for signal-related errors."""


class BacktestError(AlgoTradingError):
    """Exception raised for backtesting errors."""


class AlgoTradingDatabaseError(AlgoTradingError):
    """Exception raised for database errors."""


class APIError(AlgoTradingError):
    """Exception raised for API errors."""


class AuthenticationError(AlgoTradingError):
    """Exception raised for authentication errors."""


def _raise_error(
    exc_class: type[AlgoTradingError],
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Raise a typed error after validating the message."""
    logger.debug(
        f"Raising {exc_class.__name__}",
        extra={"message": message, "error_code": error_code},
    )
    if not message or not message.strip():
        logger.error(f"{exc_class.__name__} message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        f"{exc_class.__name__} raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise exc_class(message, error_code, details)


def raise_configuration_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise configuration errors."""
    _raise_error(ConfigurationError, message, error_code, details)


def raise_validation_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise validation errors."""
    _raise_error(ValidationError, message, error_code, details)


def raise_business_logic_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise business logic errors."""
    _raise_error(BusinessLogicError, message, error_code, details)


def raise_market_data_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise market data errors."""
    _raise_error(MarketDataError, message, error_code, details)


def raise_trading_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise trading errors."""
    _raise_error(TradingError, message, error_code, details)


def raise_database_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise database errors."""
    _raise_error(AlgoTradingDatabaseError, message, error_code, details)


def raise_authentication_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise authentication errors."""
    _raise_error(AuthenticationError, message, error_code, details)
