"""
Portfolio, Signal, and Asset API endpoints.

This module exports FastAPI routers for portfolio, signal, and asset management.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable, Dict, Optional, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variable for correlation ID (per-request)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """
    Get the current request's correlation ID.

    Returns:
        str: The correlation ID for the current request
    """
    return _correlation_id.get() or "unknown"


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current request.

    Args:
        correlation_id: The correlation ID to set
    """
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """
    Generate a new unique correlation ID.

    Returns:
        str: A unique correlation ID
    """
    return str(uuid.uuid4())


class AuditLogger:
    """
    Audit logger for tracking API requests and responses.

    Provides structured logging with correlation IDs for audit trails.
    """

    def __init__(self, logger_name: str = "app.api.audit"):
        """
        Initialize the audit logger.

        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)

    def log_request(
        self,
        method: str,
        path: str,
        client_id: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None,
        path_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an incoming API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            client_id: Optional client identifier
            query_params: Query parameters
            path_params: Path parameters
        """
        correlation_id = get_correlation_id()
        self.logger.info(
            "API request",
            extra={
                "event_type": "api_request",
                "correlation_id": correlation_id,
                "method": method,
                "path": path,
                "client_id": client_id,
                "query_params": query_params,
                "path_params": path_params,
            },
        )

    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_id: Optional[str] = None,
    ) -> None:
        """
        Log an API response.

        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            client_id: Optional client identifier
        """
        correlation_id = get_correlation_id()
        self.logger.info(
            "API response",
            extra={
                "event_type": "api_response",
                "correlation_id": correlation_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_id": client_id,
            },
        )

    def log_error(
        self,
        method: str,
        path: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        status_code: Optional[int] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """
        Log an API error.

        Args:
            method: HTTP method
            path: Request path
            error_type: Type of error
            error_message: Error message
            stack_trace: Optional stack trace
            status_code: Optional HTTP status code
            client_id: Optional client identifier
        """
        correlation_id = get_correlation_id()
        log_data = {
            "event_type": "api_error",
            "correlation_id": correlation_id,
            "method": method,
            "path": path,
            "error_type": error_type,
            "error_message": error_message,
            "client_id": client_id,
        }
        if status_code is not None:
            log_data["status_code"] = status_code
        if stack_trace is not None:
            log_data["stack_trace"] = stack_trace

        self.logger.error(
            "API error",
            extra=log_data,
            exc_info=True,
        )

    def log_action(
        self,
        action: str,
        method: str,
        path: str,
        details: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """
        Log a specific action (e.g., config change, trade execution).

        Args:
            action: Action description
            method: HTTP method
            path: Request path
            details: Optional action details
            client_id: Optional client identifier
        """
        correlation_id = get_correlation_id()
        self.logger.info(
            "API action",
            extra={
                "event_type": "api_action",
                "correlation_id": correlation_id,
                "action": action,
                "method": method,
                "path": path,
                "details": details or {},
                "client_id": client_id,
            },
        )


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs and audit logging to all requests.

    This middleware:
    1. Generates or extracts a correlation ID for each request
    2. Logs all incoming requests
    3. Logs all outgoing responses
    4. Logs any errors that occur
    """

    def __init__(
        self,
        app: "ASGIApp",
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        """
        Initialize the audit middleware.

        Args:
            app: The ASGI application
            audit_logger: Optional audit logger instance
        """
        super().__init__(app)
        self.audit_logger = audit_logger or AuditLogger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add audit logging.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response from the route handler
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        set_correlation_id(correlation_id)

        # Add correlation ID to request state for access in endpoints
        request.state.correlation_id = correlation_id

        # Extract client ID if available (from JWT or API key)
        client_id = getattr(request.state, "user_id", None) or request.headers.get(
            "X-Client-ID"
        )

        # Log request
        self.audit_logger.log_request(
            method=request.method,
            path=request.url.path,
            client_id=client_id,
            query_params=dict(request.query_params) if request.query_params else None,
            path_params=dict(request.path_params) if request.path_params else None,
        )

        # Process request and time it
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            # Log response
            self.audit_logger.log_response(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_id=client_id,
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log error with stack trace
            import traceback

            self.audit_logger.log_error(
                method=request.method,
                path=request.url.path,
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                client_id=client_id,
            )

            raise


# Global audit logger instance
audit_logger = AuditLogger()


def log_endpoint_error(
    func: Callable,
) -> Callable:
    """
    Decorator to log errors from endpoints with full context.

    Args:
        func: The function to decorate

    Returns:
        Callable: Wrapped function with error logging
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Try to get request context - typically in kwargs for FastAPI
            request = kwargs.get("request")

            if request:
                import traceback

                audit_logger.log_error(
                    method=request.method,
                    path=request.url.path,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                )
            raise

    return wrapper


__all__ = [
    "AuditLogger",
    "AuditMiddleware",
    "audit_logger",
    "get_correlation_id",
    "set_correlation_id",
    "generate_correlation_id",
    "log_endpoint_error",
]
