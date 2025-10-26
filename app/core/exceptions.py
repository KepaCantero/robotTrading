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


class DatabaseError(AlgoTradingError):
    """Exception raised for database errors."""


class APIError(AlgoTradingError):
    """Exception raised for API errors."""


def raise_configuration_error(
    message: str, error_code: str = None, details: Dict[str, Any] = None
):
    """Helper function to raise configuration errors."""
    raise ConfigurationError(message, error_code, details)


def raise_validation_error(
    message: str, error_code: str = None, details: Dict[str, Any] = None
):
    """Helper function to raise validation errors."""
    raise ValidationError(message, error_code, details)


def raise_business_logic_error(
    message: str, error_code: str = None, details: Dict[str, Any] = None
):
    """Helper function to raise business logic errors."""
    raise BusinessLogicError(message, error_code, details)


def raise_market_data_error(
    message: str, error_code: str = None, details: Dict[str, Any] = None
):
    """Helper function to raise market data errors."""
    raise MarketDataError(message, error_code, details)


def raise_trading_error(
    message: str, error_code: str = None, details: Dict[str, Any] = None
):
    """Helper function to raise trading errors."""
    raise TradingError(message, error_code, details)


def raise_database_error(
    message: str, error_code: str = None, details: Dict[str, Any] = None
):
    """Helper function to raise database errors."""
    raise DatabaseError(message, error_code, details)
