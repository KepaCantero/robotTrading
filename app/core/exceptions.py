"""
Core Exceptions for AlgoTrading
Independent exception definitions to avoid circular imports
"""

from typing import Any, Dict, Optional


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
) -> None:
    """Helper function to raise configuration errors."""
    if not message or not message.strip():
        raise ValueError("message must be a non-empty string")
    raise ConfigurationError(message, error_code, details)


def raise_validation_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper function to raise validation errors."""
    if not message or not message.strip():
        raise ValueError("message must be a non-empty string")
    raise ValidationError(message, error_code, details)


def raise_business_logic_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper function to raise business logic errors."""
    if not message or not message.strip():
        raise ValueError("message must be a non-empty string")
    raise BusinessLogicError(message, error_code, details)


def raise_market_data_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper function to raise market data errors."""
    if not message or not message.strip():
        raise ValueError("message must be a non-empty string")
    raise MarketDataError(message, error_code, details)


def raise_trading_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper function to raise trading errors."""
    if not message or not message.strip():
        raise ValueError("message must be a non-empty string")
    raise TradingError(message, error_code, details)


def raise_database_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper function to raise database errors."""
    if not message or not message.strip():
        raise ValueError("message must be a non-empty string")
    raise AlgoTradingDatabaseError(message, error_code, details)


def raise_authentication_error(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper function to raise authentication errors."""
    if not message or not message.strip():
        raise ValueError("message must be a non-empty string")
    raise AuthenticationError(message, error_code, details)
