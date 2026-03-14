"""
Custom Exceptions for AlgoTrading
TASK-4: Sistema de manejo de errores unificado
"""

# mypy: ignore-errors
import logging
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors."""

    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    PERFORMANCE = "performance"
    SYSTEM = "system"


class AlgoTradingError(Exception):
    """Base exception for all AlgoTrading errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

        logger.debug(
            "AlgoTradingError created",
            extra={
                "error_code": error_code,
                "category": category.value,
                "severity": severity.value,
                "message": message,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class ValidationError(AlgoTradingError):
    """Error for validation failures."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details={
                "field": field,
                "value": str(value) if value is not None else None,
                **(details or {}),
            },
        )

        logger.warning(
            "Validation error occurred",
            extra={
                "error_type": "ValidationError",
                "field": field,
                "value": str(value)[:100] if value is not None else None,  # Truncate for logging
            },
        )


class BusinessLogicError(AlgoTradingError):
    """Error for business logic violations."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = f"BUSINESS_ERROR_{operation.upper()}" if operation else "BUSINESS_ERROR"
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details={"operation": operation, **(details or {})},
        )


class ExternalAPIError(AlgoTradingError):
    """Error for external API failures."""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = f"API_ERROR_{api_name.upper()}"
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.HIGH,
            details={
                "api_name": api_name,
                "status_code": status_code,
                **(details or {}),
            },
        )

        logger.error(
            "External API error occurred",
            extra={
                "error_type": "ExternalAPIError",
                "api_name": api_name,
                "status_code": status_code,
                "message": message,
            },
        )


class AlgoTradingDatabaseError(AlgoTradingError):
    """Error for database operations."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = f"DB_ERROR_{operation.upper()}" if operation else "DB_ERROR"
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details={"operation": operation, "table": table, **(details or {})},
        )


class NetworkError(AlgoTradingError):
    """Error for network-related issues."""

    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            details={"endpoint": endpoint, "timeout": timeout, **(details or {})},
        )


class ConfigurationError(AlgoTradingError):
    """Error for configuration issues."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = f"CONFIG_ERROR_{config_key.upper()}" if config_key else "CONFIG_ERROR"
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            details={"config_key": config_key, **(details or {})},
        )


class SecurityError(AlgoTradingError):
    """Error for security violations."""

    def __init__(
        self,
        message: str,
        violation_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = (
            f"SECURITY_ERROR_{violation_type.upper()}" if violation_type else "SECURITY_ERROR"
        )
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.CRITICAL,
            details={"violation_type": violation_type, **(details or {})},
        )

        logger.critical(
            "Security error occurred",
            extra={
                "error_type": "SecurityError",
                "violation_type": violation_type,
                "message": message,
            },
        )


class PerformanceError(AlgoTradingError):
    """Error for performance issues."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        duration: Optional[float] = None,
        threshold: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = f"PERF_ERROR_{operation.upper()}" if operation else "PERF_ERROR"
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.PERFORMANCE,
            severity=ErrorSeverity.MEDIUM,
            details={
                "operation": operation,
                "duration": duration,
                "threshold": threshold,
                **(details or {}),
            },
        )


class SystemError(AlgoTradingError):
    """Error for system-level issues."""

    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_code = f"SYSTEM_ERROR_{component.upper()}" if component else "SYSTEM_ERROR"
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            details={"component": component, **(details or {})},
        )


# Trading-specific exceptions
class TradingError(BusinessLogicError):
    """Error for trading operations."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            operation=operation,
            details={"symbol": symbol, **(details or {})},
        )


class SignalError(BusinessLogicError):
    """Error for signal generation."""

    def __init__(
        self,
        message: str,
        signal_type: Optional[str] = None,
        strategy: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            operation="signal_generation",
            details={
                "signal_type": signal_type,
                "strategy": strategy,
                **(details or {}),
            },
        )


class PortfolioError(BusinessLogicError):
    """Error for portfolio operations."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            operation=operation,
            details={"portfolio_id": portfolio_id, **(details or {})},
        )


class RiskManagementError(BusinessLogicError):
    """Error for risk management violations."""

    def __init__(
        self,
        message: str,
        risk_type: Optional[str] = None,
        limit: Optional[float] = None,
        current_value: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            operation="risk_management",
            details={
                "risk_type": risk_type,
                "limit": limit,
                "current_value": current_value,
                **(details or {}),
            },
        )


class MarketDataError(ExternalAPIError):
    """Error for market data operations."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        data_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            api_name="market_data",
            details={"symbol": symbol, "data_type": data_type, **(details or {})},
        )


class BrokerError(ExternalAPIError):
    """Error for broker operations."""

    def __init__(
        self,
        message: str,
        broker: Optional[str] = None,
        operation: Optional[str] = None,
        order_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            api_name=broker or "broker",
            details={
                "broker": broker,
                "operation": operation,
                "order_id": order_id,
                **(details or {}),
            },
        )
