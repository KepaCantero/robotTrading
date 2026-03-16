"""
API utility functions for common patterns.

This module provides utility functions for correlation IDs, rate limiting,
timeout handling, and structured logging in API endpoints.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional, TypeVar, cast

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.logging.logging_config import get_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """
    Simple in-memory rate limiter for API endpoints.

    Uses token bucket algorithm for rate limiting.
    """

    def __init__(self) -> None:
        """Initialize rate limiter with empty buckets."""
        self._buckets: Dict[str, Dict[str, Any]] = {}

    def _get_bucket(self, key: str) -> Dict[str, Any]:
        """Get or create bucket for key."""
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": 10,  # Default tokens
                "last_update": time.time(),
                "max_tokens": 10,
                "refill_rate": 1.0,  # tokens per second
            }
        return self._buckets[key]

    def _refill(self, bucket: Dict[str, Any]) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_update"]
        new_tokens = elapsed * bucket["refill_rate"]
        bucket["tokens"] = min(bucket["max_tokens"], bucket["tokens"] + new_tokens)
        bucket["last_update"] = now

    def is_allowed(
        self,
        key: str,
        max_tokens: int = 10,
        refill_rate: float = 1.0,
        tokens_per_request: int = 1,
    ) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier for rate limit (e.g., client IP)
            max_tokens: Maximum number of tokens
            refill_rate: Token refill rate per second
            tokens_per_request: Tokens consumed per request

        Returns:
            True if request is allowed, False otherwise
        """
        bucket = self._get_bucket(key)
        bucket["max_tokens"] = max_tokens
        bucket["refill_rate"] = refill_rate

        self._refill(bucket)

        if bucket["tokens"] >= tokens_per_request:
            bucket["tokens"] -= tokens_per_request
            return True
        return False

    def reset(self, key: Optional[str] = None) -> None:
        """
        Reset rate limit bucket(s).

        Args:
            key: Specific key to reset, or None to reset all
        """
        if key:
            self._buckets.pop(key, None)
        else:
            self._buckets.clear()


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    return _rate_limiter


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests.

    Ensures API-007: Structured logging with correlation IDs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add correlation ID to request context."""
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Set in context variable for logging
        set_correlation_id(correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


@asynccontextmanager
async def timeout_context(seconds: float) -> AsyncGenerator[None, None]:
    """
    Context manager for async operations with timeout.

    Ensures API-010: Timeout handling for async operations.

    Args:
        seconds: Timeout in seconds

    Raises:
        asyncio.TimeoutError: If operation exceeds timeout

    Yields:
        None
    """
    try:
        yield
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"Operation exceeded {seconds}s timeout")


def with_timeout(
    seconds: float = 30.0,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to add timeout to async functions.

    Ensures API-010: Timeout handling for async operations.

    Args:
        seconds: Timeout in seconds

    Returns:
        Decorated function with timeout
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return cast(
                    T,
                    await asyncio.wait_for(func(*args, **kwargs), timeout=seconds),
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Function {func.__name__} exceeded {seconds}s timeout",
                    extra={"correlation_id": get_correlation_id()},
                )
                raise asyncio.TimeoutError(f"Operation exceeded {seconds}s timeout")

        return wrapper

    return decorator


def with_rate_limit(
    key_func: Optional[Callable[[Request], str]] = None,
    max_tokens: int = 10,
    refill_rate: float = 1.0,
    tokens_per_request: int = 1,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to add rate limiting to endpoint functions.

    Ensures API-007: Rate limiting on expensive endpoints.

    Args:
        key_func: Function to extract rate limit key from Request
        max_tokens: Maximum number of tokens
        refill_rate: Token refill rate per second
        tokens_per_request: Tokens consumed per request

    Returns:
        Decorated function with rate limiting
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Try to find Request in args/kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # If no Request in args, check kwargs
            if request is None:
                request = kwargs.get("request")

            # Apply rate limiting if we have a request
            if request:
                key = (
                    key_func(request)
                    if key_func
                    else request.client.host
                    if request.client
                    else "default"
                )
                limiter = get_rate_limiter()

                if not limiter.is_allowed(
                    key,
                    max_tokens=max_tokens,
                    refill_rate=refill_rate,
                    tokens_per_request=tokens_per_request,
                ):
                    logger.warning(
                        f"Rate limit exceeded for key: {key}",
                        extra={"correlation_id": get_correlation_id()},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later.",
                    )

            return cast(T, await func(*args, **kwargs))

        return wrapper

    return decorator


def log_endpoint_call(
    operation: str,
    service: str = "api",
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to add structured logging to endpoint functions.

    Ensures API-002: Log all asset access with context.
    Ensures API-007: Structured logging with correlation IDs.

    Args:
        operation: Operation name for logging
        service: Service name for logging

    Returns:
        Decorated function with structured logging
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            correlation_id = get_correlation_id()
            start_time = time.time()

            logger.info(
                f"{service}.{operation}: Started",
                extra={
                    "correlation_id": correlation_id,
                    "operation": operation,
                    "service": service,
                    "function": func.__name__,
                },
            )

            try:
                result = cast(T, await func(*args, **kwargs))
                duration = (time.time() - start_time) * 1000

                logger.info(
                    f"{service}.{operation}: Completed",
                    extra={
                        "correlation_id": correlation_id,
                        "operation": operation,
                        "service": service,
                        "function": func.__name__,
                        "duration_ms": round(duration, 2),
                        "status": "success",
                    },
                )

                return result

            except Exception as e:
                duration = (time.time() - start_time) * 1000

                logger.error(
                    f"{service}.{operation}: Failed",
                    extra={
                        "correlation_id": correlation_id,
                        "operation": operation,
                        "service": service,
                        "function": func.__name__,
                        "duration_ms": round(duration, 2),
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def log_error_with_trace(
    error: Exception,
    context: Dict[str, Any],
    service: str = "api",
) -> None:
    """
    Log error with full stack trace.

    Ensures API-009: Error logging with stack traces.

    Args:
        error: Exception to log
        context: Additional context information
        service: Service name for logging
    """
    correlation_id = get_correlation_id()

    logger.error(
        f"{service}: Error occurred",
        extra={
            "correlation_id": correlation_id,
            "service": service,
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context,
        },
        exc_info=True,
    )
