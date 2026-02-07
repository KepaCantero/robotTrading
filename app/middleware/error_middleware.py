"""
Error Handling Middleware for FastAPI
TASK-4: Sistema de manejo de errores unificado
"""

# pylint: disable=import-error
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions.error_handler import error_handler
from app.services.centralized_logging import LogLevel, LogService, centralized_logger


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and adding request context."""

    def __init__(self, app, enable_request_logging: bool = True):
        super().__init__(app)
        self.enable_request_logging = enable_request_logging
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle errors."""

        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.request_id = request_id  # type: ignore

        # Record start time
        start_time = time.time()

        try:
            # Log request start
            if self.enable_request_logging:
                await self._log_request_start(request)

            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log request completion
            if self.enable_request_logging:
                await self._log_request_completion(request, response, process_time)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            # Calculate processing time
            process_time = time.time() - start_time

            # Log request error
            await self._log_request_error(request, exc, process_time)

            # Handle the exception
            return await self._handle_exception(request, exc)

    async def _log_request_start(self, request: Request) -> None:
        """Log request start."""
        metadata = {
            "request_id": request.request_id,  # type: ignore
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }

        centralized_logger.info(
            LogService.FASTAPI,
            f"Request started: {request.method} {request.url.path}",
            metadata,
        )

    async def _log_request_completion(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """Log request completion."""
        metadata = {
            "request_id": request.request_id,  # type: ignore
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": process_time,
            "response_size": response.headers.get("content-length"),
        }

        # Determine log level based on status code and processing time
        if response.status_code >= 500:
            log_level = LogLevel.ERROR
        elif response.status_code >= 400:
            log_level = LogLevel.WARNING
        elif process_time > 5.0:  # Slow requests
            log_level = LogLevel.WARNING
        else:
            log_level = LogLevel.INFO

        if log_level == LogLevel.INFO:
            centralized_logger.info(
                LogService.FASTAPI,
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                metadata,
            )
        elif log_level == LogLevel.WARNING:
            centralized_logger.warning(
                LogService.FASTAPI,
                f"Request completed with warning: {request.method} {request.url.path} - {response.status_code}",
                metadata,
            )
        elif log_level == LogLevel.ERROR:
            centralized_logger.error(
                LogService.FASTAPI,
                f"Request completed with error: {request.method} {request.url.path} - {response.status_code}",
                metadata,
            )

    async def _log_request_error(
        self, request: Request, exc: Exception, process_time: float
    ) -> None:
        """Log request error."""
        metadata = {
            "request_id": request.request_id,  # type: ignore
            "method": request.method,
            "path": request.url.path,
            "process_time": process_time,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }

        centralized_logger.error(
            LogService.FASTAPI,
            f"Request failed: {request.method} {request.url.path}",
            metadata,
            str(exc),
        )

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle exception and return appropriate response."""

        # Add request context to exception if it's an AlgoTradingError
        if hasattr(exc, "details") and isinstance(exc.details, dict):
            exc.details.update(
                {
                    "request_id": request.request_id,  # type: ignore
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                }
            )

        # Use the global error handler
        return error_handler.handle_generic_exception(exc, request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware for adding request context to all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request context."""

        # Add request ID if not already present
        if not hasattr(request, "request_id"):
            request.request_id = str(uuid.uuid4())  # type: ignore

        # Add request start time
        request.start_time = time.time()  # type: ignore

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request.request_id  # type: ignore

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    def __init__(self, app, enable_cors: bool = True):
        super().__init__(app)
        self.enable_cors = enable_cors

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers."""

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosnif"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if self.enable_cors:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # type: ignore
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries
        self._cleanup_old_entries(current_time)

        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            centralized_logger.warning(
                LogService.FASTAPI,
                f"Rate limit exceeded for client {client_ip}",
                {
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "method": request.method,
                    "rate_limit": self.requests_per_minute,
                },
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "details": {
                            "rate_limit": self.requests_per_minute,
                            "retry_after": 60,
                        },
                    }
                },
                headers={"Retry-After": "60"},
            )

        # Record request
        self._record_request(client_ip, current_time)

        # Process request
        response = await call_next(request)

        return response

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old request entries."""
        cutoff_time = current_time - 60  # 1 minute ago
        self.request_counts = {
            ip: timestamps
            for ip, timestamps in self.request_counts.items()
            if any(t > cutoff_time for t in timestamps)
        }

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited."""
        if client_ip not in self.request_counts:
            return False

        # Count requests in the last minute
        cutoff_time = current_time - 60
        recent_requests = [t for t in self.request_counts[client_ip] if t > cutoff_time]

        return len(recent_requests) >= self.requests_per_minute

    def _record_request(self, client_ip: str, current_time: float) -> None:
        """Record a request."""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        self.request_counts[client_ip].append(current_time)


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Middleware for health check endpoints."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle health check requests."""

        # Skip middleware processing for health check endpoints
        if request.url.path in ["/health", "/healthz", "/ready", "/live"]:
            return await call_next(request)

        # Process other requests normally
        return await call_next(request)
