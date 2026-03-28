"""
Global Error Handler for AlgoTrading
TASK-4: Sistema de manejo de errores unificado
"""

import logging
import traceback
from typing import Any, Dict, NoReturn, Optional, Union

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.centralized_logging import LogLevel, LogService, centralized_logger
from app.shared.exceptions.trading_exceptions import (
    AlgoTradingDatabaseError as DatabaseError,
    AlgoTradingError,
    BusinessLogicError,
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    ExternalAPIError,
    SystemError,
    ValidationError,
)


class ErrorHandler:
    """Global error handler for AlgoTrading application."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def handle_algotrading_error(
        self, error: AlgoTradingError, request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle AlgoTrading custom errors."""

        # Log the error
        self._log_error(error, request)

        # Determine HTTP status code based on severity
        status_code = self._get_http_status_code(error.severity)

        # Create error response
        error_response = {
            "error": {
                "code": error.error_code,
                "message": error.message,
                "category": error.category.value,
                "severity": error.severity.value,
                "details": error.details,
                "timestamp": error.details.get("timestamp"),
                "request_id": getattr(request, "request_id", None) if request else None,
            }
        }

        return JSONResponse(status_code=status_code, content=error_response)

    def handle_validation_error(
        self, error: RequestValidationError, request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle FastAPI validation errors."""

        # Convert to AlgoTrading validation error
        algotrading_error = ValidationError(
            message="Request validation failed",
            details={
                "validation_errors": error.errors(),
                "body": str(error.body) if hasattr(error, "body") else None,
            },
        )

        return self.handle_algotrading_error(algotrading_error, request)

    def handle_http_exception(
        self, error: Union[HTTPException, StarletteHTTPException], request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle HTTP exceptions (FastAPI or Starlette)."""

        # Determine category based on status code
        category = self._get_category_from_status_code(error.status_code)
        severity = self._get_severity_from_status_code(error.status_code)

        algotrading_error = AlgoTradingError(
            message=error.detail,
            error_code=f"HTTP_{error.status_code}",
            category=category,
            severity=severity,
            details={
                "status_code": error.status_code,
                "headers": dict(error.headers) if error.headers else None,
            },
        )

        return self.handle_algotrading_error(algotrading_error, request)

    def handle_generic_exception(
        self, error: Exception, request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle generic exceptions."""

        # Log the full traceback
        self.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)

        # Create system error
        algotrading_error = SystemError(
            message="An unexpected error occurred",
            component="system",
            details={
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "traceback": traceback.format_exc(),
            },
        )

        return self.handle_algotrading_error(algotrading_error, request)

    def _log_error(self, error: AlgoTradingError, request: Optional[Request] = None) -> None:
        """Log error using centralized logging."""

        # Determine log level based on severity
        log_level = self._get_log_level(error.severity)

        # Determine service based on category
        service = self._get_service_from_category(error.category)

        # Prepare metadata
        metadata = {
            "error_code": error.error_code,
            "category": error.category.value,
            "severity": error.severity.value,
            "details": error.details,
        }

        if request:
            metadata.update(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "request_id": getattr(request, "request_id", None),
                }
            )

        # Log the error
        if log_level == LogLevel.DEBUG:
            centralized_logger.debug(service, error.message, metadata)
        elif log_level == LogLevel.INFO:
            centralized_logger.info(service, error.message, metadata)
        elif log_level == LogLevel.WARNING:
            centralized_logger.warning(service, error.message, metadata)
        elif log_level == LogLevel.ERROR:
            centralized_logger.error(service, error.message, metadata, str(error.original_error))
        elif log_level == LogLevel.CRITICAL:
            centralized_logger.critical(service, error.message, metadata, str(error.original_error))

    def _get_http_status_code(self, severity: ErrorSeverity) -> int:
        """Get HTTP status code based on error severity."""
        severity_mapping = {
            ErrorSeverity.LOW: 400,
            ErrorSeverity.MEDIUM: 400,
            ErrorSeverity.HIGH: 500,
            ErrorSeverity.CRITICAL: 500,
        }
        return severity_mapping.get(severity, 500)

    def _get_log_level(self, severity: ErrorSeverity) -> LogLevel:
        """Get log level based on error severity."""
        severity_mapping = {
            ErrorSeverity.LOW: LogLevel.INFO,
            ErrorSeverity.MEDIUM: LogLevel.WARNING,
            ErrorSeverity.HIGH: LogLevel.ERROR,
            ErrorSeverity.CRITICAL: LogLevel.CRITICAL,
        }
        return severity_mapping.get(severity, LogLevel.ERROR)

    def _get_service_from_category(self, category: ErrorCategory) -> LogService:
        """Get logging service based on error category."""
        category_mapping = {
            ErrorCategory.VALIDATION: LogService.FASTAPI,
            ErrorCategory.BUSINESS_LOGIC: LogService.TRADING,
            ErrorCategory.EXTERNAL_API: LogService.MARKET_DATA,
            ErrorCategory.DATABASE: LogService.FASTAPI,
            ErrorCategory.NETWORK: LogService.MARKET_DATA,
            ErrorCategory.CONFIGURATION: LogService.FASTAPI,
            ErrorCategory.SECURITY: LogService.FASTAPI,
            ErrorCategory.PERFORMANCE: LogService.PERFORMANCE_MONITOR,
            ErrorCategory.SYSTEM: LogService.ERROR_HANDLER,
        }
        return category_mapping.get(category, LogService.ERROR_HANDLER)

    def _get_category_from_status_code(self, status_code: int) -> ErrorCategory:
        """Get error category based on HTTP status code."""
        if 400 <= status_code < 500:
            return ErrorCategory.VALIDATION
        elif 500 <= status_code < 600:
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.SYSTEM

    def _get_severity_from_status_code(self, status_code: int) -> ErrorSeverity:
        """Get error severity based on HTTP status code."""
        if status_code < 400:
            return ErrorSeverity.LOW
        elif 400 <= status_code < 500:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.HIGH


# Global error handler instance
error_handler = ErrorHandler()


# FastAPI exception handlers
async def algotrading_exception_handler(request: Request, exc: AlgoTradingError) -> JSONResponse:
    """Handle AlgoTrading custom exceptions."""
    return error_handler.handle_algotrading_error(exc, request)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI validation exceptions."""
    return error_handler.handle_validation_error(exc, request)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return error_handler.handle_http_exception(exc, request)


async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle Starlette HTTP exceptions."""
    return error_handler.handle_http_exception(exc, request)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions."""
    return error_handler.handle_generic_exception(exc, request)


# Error response templates
def create_error_response(
    error_code: str,
    message: str,
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    details: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None,
) -> JSONResponse:
    """Create a standardized error response."""

    if status_code is None:
        status_code = error_handler._get_http_status_code(severity)

    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "category": category.value,
            "severity": severity.value,
            "details": details or {},
        }
    }

    return JSONResponse(status_code=status_code, content=error_response)


# Utility functions for common error scenarios
def raise_validation_error(
    message: str,
    field: Optional[str] = None,
    value: Optional[Any] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Raise a validation error."""
    raise ValidationError(message, field, value, details)


def raise_business_logic_error(
    message: str,
    operation: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Raise a business logic error."""
    raise BusinessLogicError(message, operation, details)


def raise_external_api_error(
    message: str,
    api_name: str,
    status_code: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Raise an external API error."""
    raise ExternalAPIError(message, api_name, status_code, details)


def raise_database_error(
    message: str,
    operation: Optional[str] = None,
    table: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Raise a database error."""
    raise DatabaseError(message, operation, table, details)


def raise_configuration_error(
    message: str,
    config_key: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    """Raise a configuration error."""
    raise ConfigurationError(message, config_key, details)
