"""
Security utilities for API endpoints.

This module provides decorators and middleware for:
- Rate limiting (in-memory, suitable for single-instance deployments)
- Authentication/authorization (placeholder for future JWT integration)
- Audit logging for sensitive operations

GAP Fixes:
- API-005: Added security decorators (rate_limit, require_auth, audit_log)
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from collections import defaultdict
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from . import audit_logger, get_correlation_id

logger = logging.getLogger(__name__)


# ============================================================================
# Rate Limiting
# ============================================================================


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    This implementation is suitable for single-instance deployments.
    For multi-instance deployments, consider using Redis-based rate limiting.

    Thread-safety: This implementation uses asyncio.Lock for concurrency safety.
    """

    def __init__(self, default_max_requests: int = 100, default_window_seconds: int = 60):
        """
        Initialize the rate limiter.

        Args:
            default_max_requests: Default maximum requests per window
            default_window_seconds: Default time window in seconds
        """
        self.default_max_requests = default_max_requests
        self.default_window_seconds = default_window_seconds

        # Store request timestamps by key: {key: [timestamp1, timestamp2, ...]}
        self._requests: Dict[str, List[float]] = defaultdict(list)

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    def _get_client_key(self, request: Request) -> str:
        """
        Extract a unique key for rate limiting from the request.

        Args:
            request: FastAPI Request object

        Returns:
            str: Unique key for the client
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Try to get API key from headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Fall back to client IP
        # Handle proxies by checking X-Forwarded-For or X-Real-IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            client_ip = real_ip if real_ip else request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    async def is_allowed(
        self,
        key: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed under rate limiting rules.

        Args:
            key: Unique key for the client
            max_requests: Maximum requests allowed (uses default if None)
            window_seconds: Time window in seconds (uses default if None)

        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        max_requests = max_requests or self.default_max_requests
        window_seconds = window_seconds or self.default_window_seconds

        current_time = time.time()
        window_start = current_time - window_seconds

        async with self._lock:
            # Get existing requests for this key
            requests = self._requests[key]

            # Filter out requests outside the current window
            requests = [ts for ts in requests if ts > window_start]
            self._requests[key] = requests

            # Check if limit is exceeded
            request_count = len(requests)
            is_allowed = request_count < max_requests

            # Add current request if allowed
            if is_allowed:
                requests.append(current_time)

            # Calculate rate limit info for headers
            reset_time = max(requests) if requests else current_time
            reset_at = datetime.fromtimestamp(reset_time + window_seconds).isoformat()

            return is_allowed, {
                "limit": max_requests,
                "remaining": max_requests - request_count,
                "reset": reset_at,
                "window": window_seconds,
            }

    async def cleanup_old_entries(self, older_than_seconds: int = 3600):
        """
        Clean up old entries to prevent memory leaks.

        Args:
            older_than_seconds: Remove entries older than this
        """
        cutoff_time = time.time() - older_than_seconds

        async with self._lock:
            keys_to_remove = []

            for key, timestamps in self._requests.items():
                # Filter old timestamps
                self._requests[key] = [ts for ts in timestamps if ts > cutoff_time]

                # Mark empty keys for removal
                if not self._requests[key]:
                    keys_to_remove.append(key)

            # Remove empty keys
            for key in keys_to_remove:
                del self._requests[key]

            if keys_to_remove:
                logger.debug(f"Cleaned up {len(keys_to_remove)} old rate limit entries")


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """
    Decorator to apply rate limiting to an endpoint.

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
        key_func: Optional function to extract rate limit key from request

    Returns:
        Decorator function

    Example:
        @router.get("/api/data")
        @rate_limit(max_requests=10, window_seconds=60)
        async def get_data():
            return {"data": "..."}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to extract Request from kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                # No request object, skip rate limiting
                return await func(*args, **kwargs)

            rate_limiter = get_rate_limiter()

            # Get rate limit key
            if key_func:
                key = key_func(request)
            else:
                key = rate_limiter._get_client_key(request)

            # Check if allowed
            is_allowed, info = await rate_limiter.is_allowed(key, max_requests, window_seconds)

            # Set rate limit headers
            # Note: These will be attached to the response if possible
            if hasattr(request.state, "rate_limit_info"):
                request.state.rate_limit_info = info

            if not is_allowed:
                correlation_id = get_correlation_id()
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "correlation_id": correlation_id,
                        "key": key,
                        "limit": info["limit"],
                        "window": info["window"],
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": info["limit"],
                        "window": info["window"],
                        "reset": info["reset"],
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": info["reset"],
                        "Retry-After": str(window_seconds),
                    },
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to all requests.

    This middleware adds rate limit headers to responses and handles
    rate limit checking globally or per-route.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the rate limit middleware.

        Args:
            app: The ASGI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response with rate limit headers
        """
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        rate_limiter = get_rate_limiter()
        key = rate_limiter._get_client_key(request)

        # Check rate limit
        is_allowed, info = await rate_limiter.is_allowed(
            key, self.max_requests, self.window_seconds
        )

        # Store info in request state for access in endpoints
        request.state.rate_limit_info = info

        if not is_allowed:
            correlation_id = get_correlation_id()
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "correlation_id": correlation_id,
                    "key": key,
                    "path": request.url.path,
                    "limit": info["limit"],
                },
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": info["limit"],
                    "window": info["window"],
                    "reset": info["reset"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": info["reset"],
                    "Retry-After": str(self.window_seconds),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = info["reset"]

        return response


# ============================================================================
# Authentication & Authorization
# ============================================================================


class SecurityConfig:
    """Security configuration settings."""

    # NOTE: Move these to environment variables or config file
    AUTH_ENABLED = False  # Set to True when JWT/OAuth is implemented
    AUTH_REQUIRED_BY_DEFAULT = False
    ADMIN_ROLE_REQUIRED = False


def get_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extract user information from the request.

    This is a placeholder implementation that should be replaced with
    proper JWT/OAuth authentication.

    Args:
        request: FastAPI Request object

    Returns:
        Optional[Dict]: User information if authenticated, None otherwise
    """
    # Placeholder: Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # NOTE: Validate API key against database
        return {"id": "api_user", "type": "api_key", "key": api_key[:8] + "..."}

    # Placeholder: Check for JWT token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # NOTE: Validate and decode JWT token
        # For now, return None to indicate no valid auth
        pass

    # Check request state for user set by middleware
    if hasattr(request.state, "user"):
        return request.state.user

    return None


def require_auth(
    allow_api_key: bool = True,
    roles: Optional[List[str]] = None,
    require_verified: bool = False,
):
    """
    Decorator to require authentication for an endpoint.

    This decorator checks for authenticated users and optionally verifies roles.

    Args:
        allow_api_key: Whether to allow API key authentication
        roles: Optional list of required roles (user must have at least one)
        require_verified: Whether to require email verification

    Returns:
        Decorator function

    Example:
        @router.post("/api/trade")
        @require_auth(roles=["trader", "admin"])
        async def execute_trade():
            return {"status": "executed"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract Request from args or kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                logger.warning("Authentication check failed: No request object")
                if SecurityConfig.AUTH_ENABLED:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "error": "Authentication required",
                            "message": "Valid authentication credentials required",
                        },
                    )
                # Auth not enabled, allow request
                return await func(*args, **kwargs)

            # Check if auth is enabled
            if not SecurityConfig.AUTH_ENABLED:
                logger.warning(
                    "Authentication required but not configured",
                    extra={"endpoint": func.__name__},
                )
                # Log that this endpoint would require auth if enabled
                # For now, allow the request but log a warning
                return await func(*args, **kwargs)

            # Get user from request
            user = get_user_from_request(request)

            if not user:
                correlation_id = get_correlation_id()
                logger.warning(
                    "Authentication failed: No valid credentials",
                    extra={"correlation_id": correlation_id, "endpoint": func.__name__},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "Authentication required",
                        "message": "Valid authentication credentials required",
                    },
                    headers={
                        "WWW-Authenticate": 'Bearer realm="algotrading"',
                    },
                )

            # Check role requirements
            if roles:
                user_roles = user.get("roles", [])
                if not any(role in user_roles for role in roles):
                    correlation_id = get_correlation_id()
                    logger.warning(
                        "Authorization failed: Insufficient permissions",
                        extra={
                            "correlation_id": correlation_id,
                            "user_id": user.get("id"),
                            "required_roles": roles,
                            "user_roles": user_roles,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "Insufficient permissions",
                            "message": f"This endpoint requires one of the following roles: {', '.join(roles)}",
                            "required_roles": roles,
                        },
                    )

            # Check verification requirement
            if require_verified and not user.get("is_verified", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Email verification required",
                        "message": "Please verify your email address to access this resource",
                    },
                )

            # Store user in request state for access in endpoint
            request.state.user = user

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role for an endpoint.

    This is a shorthand for @require_auth(roles=["admin"]).

    Args:
        func: The function to decorate

    Returns:
        Callable: Wrapped function requiring admin role

    Example:
        @router.delete("/api/users/{user_id}")
        @require_admin
        async def delete_user(user_id: str):
            return {"message": "User deleted"}
    """
    return require_auth(roles=["admin"])(func)


# ============================================================================
# Audit Logging
# ============================================================================


def audit_log(
    operation: str,
    log_args: bool = False,
    log_result: bool = False,
    sensitive_params: Optional[List[str]] = None,
):
    """
    Decorator to add comprehensive audit logging to an endpoint.

    Args:
        operation: Name of the operation for audit trail
        log_args: Whether to log function arguments
        log_result: Whether to log function return values
        sensitive_params: List of parameter names to redact from logs

    Returns:
        Decorator function

    Example:
        @router.post("/api/trade")
        @audit_log("trade_execution", log_args=True, sensitive_params=["api_key"])
        async def execute_trade(symbol: str, quantity: int):
            return {"status": "executed"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            correlation_id = get_correlation_id()
            start_time = time.time()

            # Extract request for context
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            # Prepare audit log data
            audit_data = {
                "operation": operation,
                "function": func.__name__,
                "correlation_id": correlation_id,
                "start_time": datetime.utcnow().isoformat(),
            }

            # Add request context if available
            if request:
                audit_data["method"] = request.method
                audit_data["path"] = request.url.path
                client_id = getattr(request.state, "user_id", None) or request.headers.get(
                    "X-Client-ID"
                )
                if client_id:
                    audit_data["client_id"] = client_id

            # Log arguments if requested
            if log_args:
                args_to_log = {}
                for key, value in kwargs.items():
                    # Redact sensitive parameters
                    if sensitive_params and key in sensitive_params:
                        args_to_log[key] = "***REDACTED***"
                    elif not key.startswith("_"):  # Skip private params
                        # Convert to string safely
                        try:
                            args_to_log[key] = str(value)[:1000]  # Limit length
                        except Exception:
                            args_to_log[key] = "<unable to serialize>"
                audit_data["args"] = args_to_log

            # Log operation start
            logger.info("Audit: Operation started", extra={"audit": audit_data})

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                audit_data["duration_ms"] = round(duration_ms, 2)
                audit_data["status"] = "success"

                # Log result if requested
                if log_result and result is not None:
                    try:
                        audit_data["result"] = str(result)[:1000]  # Limit length
                    except Exception:
                        audit_data["result"] = "<unable to serialize>"

                # Log success
                logger.info("Audit: Operation completed", extra={"audit": audit_data})

                # Also log via audit_logger if request available
                if request:
                    audit_logger.log_action(
                        action=operation,
                        method=request.method,
                        path=request.url.path,
                        details={"duration_ms": duration_ms, "status": "success"},
                    )

                return result

            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                audit_data["duration_ms"] = round(duration_ms, 2)
                audit_data["status"] = "failed"
                audit_data["error"] = {
                    "type": type(e).__name__,
                    "message": str(e),
                    "stack_trace": traceback.format_exc(),
                }

                # Log failure
                logger.error(
                    "Audit: Operation failed",
                    extra={"audit": audit_data},
                    exc_info=True,
                )

                # Also log via audit_logger if request available
                if request:
                    audit_logger.log_error(
                        method=request.method,
                        path=request.url.path,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        stack_trace=traceback.format_exc(),
                    )

                raise

        return wrapper

    return decorator


# ============================================================================
# Security Headers
# ============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds headers like:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
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
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


# ============================================================================
# CORS Configuration
# ============================================================================


def get_cors_config() -> Dict[str, Any]:
    """
    Get CORS configuration for FastAPI.

    Returns:
        Dict: CORS configuration

    TODO: Move to environment variables or config file
    """
    return {
        "allow_origins": [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Client-ID",
            "X-Correlation-ID",
        ],
        "expose_headers": [
            "X-Correlation-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 600,
    }


__all__ = [
    # Rate limiting
    "RateLimiter",
    "get_rate_limiter",
    "rate_limit",
    "RateLimitMiddleware",
    # Authentication
    "require_auth",
    "require_admin",
    "get_user_from_request",
    "SecurityConfig",
    # Audit logging
    "audit_log",
    # Security headers
    "SecurityHeadersMiddleware",
    # CORS
    "get_cors_config",
]
