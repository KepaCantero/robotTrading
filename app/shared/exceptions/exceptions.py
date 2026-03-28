"""
Core Exceptions for AlgoTrading
Independent exception definitions to avoid circular imports
"""

import logging
from typing import Any, Dict, NoReturn, Optional

logger = logging.getLogger(__name__)


class AlgoTradingError(Exception):
    """Base exception for all AlgoTrading errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
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


def raise_configuration_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise configuration errors."""
    logger.debug(
        "Raising configuration error", extra={"message": message, "error_code": error_code}
    )
    if not message or not message.strip():
        logger.error("Configuration error message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        "Configuration error raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise ConfigurationError(message, error_code, details)


def raise_validation_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise validation errors."""
    logger.debug("Raising validation error", extra={"message": message, "error_code": error_code})
    if not message or not message.strip():
        logger.error("Validation error message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        "Validation error raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise ValidationError(message, error_code, details)


def raise_business_logic_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise business logic errors."""
    logger.debug(
        "Raising business logic error", extra={"message": message, "error_code": error_code}
    )
    if not message or not message.strip():
        logger.error("Business logic error message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        "Business logic error raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise BusinessLogicError(message, error_code, details)


def raise_market_data_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise market data errors."""
    logger.debug("Raising market data error", extra={"message": message, "error_code": error_code})
    if not message or not message.strip():
        logger.error("Market data error message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        "Market data error raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise MarketDataError(message, error_code, details)


def raise_trading_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise trading errors."""
    logger.debug("Raising trading error", extra={"message": message, "error_code": error_code})
    if not message or not message.strip():
        logger.error("Trading error message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        "Trading error raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise TradingError(message, error_code, details)


def raise_database_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise database errors."""
    logger.debug("Raising database error", extra={"message": message, "error_code": error_code})
    if not message or not message.strip():
        logger.error("Database error message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        "Database error raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise AlgoTradingDatabaseError(message, error_code, details)


def raise_authentication_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Helper function to raise authentication errors."""
    logger.debug(
        "Raising authentication error", extra={"message": message, "error_code": error_code}
    )
    if not message or not message.strip():
        logger.error("Authentication error message validation failed: message is empty")
        raise ValueError("message must be a non-empty string")
    logger.error(
        "Authentication error raised",
        extra={"message": message, "error_code": error_code, "details": details},
    )
    raise AuthenticationError(message, error_code, details)
