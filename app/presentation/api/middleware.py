"""
Security and observability middleware for AlgoTrading API.

Authentication is NOT handled here anymore (Fase 1, hallazgos A02/A15):
the AuthMiddleware that accepted a hard-coded development key and answered
500 to missing credentials was deleted at the root. Protect-by-default
authentication and role-based authorization now live in
app/presentation/api/security.py as FastAPI dependencies
(get_current_principal / require_roles) mounted on the routers in main.py.

Remaining middleware provides:
- Correlation ID tracking (API-006)
- Security headers
- Request logging
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests.

    This middleware:
    1. Generates or extracts a correlation ID for each request
    2. Adds it to the request state for access in endpoints
    3. Includes it in the response headers for traceability

    Correlation IDs are used to trace requests across the system,
    connecting logs, errors, and responses for debugging and monitoring.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add correlation ID tracking.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response with correlation ID headers
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Store in request state for access in endpoints
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds security headers for:
    - XSS protection
    - Content type sniffing prevention
    - Frame options (clickjacking protection)
    - HSTS (HTTP Strict Transport Security)
    - Content Security Policy
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response with security headers
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy (basic version)
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request logging.

    Logs information about incoming requests including:
    - Method and path
    - Client IP
    - User agent
    - Correlation ID
    - Authentication status
    """

    def __init__(self, app: ASGIApp, log_level: int = logging.INFO) -> None:
        """
        Initialize the request logging middleware.

        Args:
            app: The ASGI application
            log_level: Logging level to use
        """
        super().__init__(app)
        self.log_level = log_level
        self.logger = logging.getLogger("app.api.requests")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response from the route handler
        """
        # Extract request information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        correlation_id = getattr(
            request.state, "correlation_id", request.headers.get("X-Correlation-ID", "unknown")
        )
        user_id = getattr(request.state, "user_id", "anonymous")
        auth_method = getattr(request.state, "auth_method", None)

        # Log request
        self.logger.log(
            self.log_level,
            f"{request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "correlation_id": correlation_id,
                "user_id": user_id,
                "auth_method": auth_method,
            },
        )

        # Process request
        return await call_next(request)


__all__ = [
    "CorrelationIdMiddleware",
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",
]
