"""
API Rate Limiting Middleware

This module provides rate limiting for FastAPI endpoints using
a token bucket algorithm with in-memory storage.

For production use with multiple workers, consider using Redis-backed
rate limiting.

SEC-004: Rate limiting to prevent abuse
SEC-005: Per-IP and per-user rate limiting
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    burst_size: int = 10  # Allow short bursts
    enabled: bool = True

    # Rate limits for different endpoint types
    default_rate: int = 60  # requests per minute
    read_rate: int = 120  # for read operations
    write_rate: int = 30  # for write operations
    expensive_rate: int = 10  # for expensive operations


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    tokens: float = field(default=60.0)
    last_update: float = field(default_factory=time.time)
    rate: float = field(default=1.0)  # tokens per second
    capacity: float = field(default=60.0)

    def consume(self, tokens: int = 1) -> bool:
        """
        Consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False otherwise
        """
        now = time.time()
        elapsed = now - self.last_update

        # Refill tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate wait time to acquire tokens.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        now = time.time()
        elapsed = now - self.last_update

        # Refill tokens based on elapsed time
        current_tokens = min(self.capacity, self.tokens + elapsed * self.rate)

        if current_tokens >= tokens:
            return 0.0

        # Calculate time needed to get enough tokens
        tokens_needed = tokens - current_tokens
        return tokens_needed / self.rate


class InMemoryRateLimiter:
    """
    In-memory rate limiter using token bucket algorithm.

    Note: This implementation is for single-process deployments.
    For multi-process deployments, use Redis-backed rate limiting.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                tokens=config.default_rate,
                capacity=config.default_rate,
                rate=config.default_rate / 60.0,  # Convert to per-second
            )
        )
        self._lock = asyncio.Lock()

    def _get_key(self, request: Request) -> str:
        """
        Get rate limit key for request.

        Uses IP address as the key. In production, you might want to use
        user ID for authenticated requests.
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    def _get_rate_for_path(self, path: str, method: str) -> int:
        """Get rate limit for a specific path and method."""
        # Expensive operations
        if "/historical" in path or "/backtest" in path or "/validate" in path:
            return self.config.expensive_rate

        # Write operations
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            return self.config.write_rate

        # Read operations
        return self.config.read_rate

    async def check_rate_limit(self, request: Request) -> tuple[bool, Optional[TokenBucket]]:
        """
        Check if request is within rate limit.

        Args:
            request: FastAPI request

        Returns:
            Tuple of (is_allowed, bucket)
        """
        if not self.config.enabled:
            return True, None

        async with self._lock:
            key = self._get_key(request)
            rate = self._get_rate_for_path(request.url.path, request.method)

            # Get or create bucket for this key
            bucket = self._buckets[key]

            # Update bucket rate if it's a new bucket
            if bucket.rate != rate / 60.0:
                bucket = TokenBucket(
                    tokens=rate,
                    capacity=rate,
                    rate=rate / 60.0,
                )
                self._buckets[key] = bucket

            # Try to consume a token
            allowed = bucket.consume(1)

            if not allowed:
                wait_time = bucket.wait_time(1)
                logger.warning(
                    f"Rate limit exceeded for {key} "
                    f"(wait_time={wait_time:.2f}s, path={request.url.path})"
                )

            return allowed, bucket

    def get_rate_limit_headers(self, bucket: Optional[TokenBucket]) -> dict[str, str]:
        """
        Get rate limit headers for response.

        Args:
            bucket: Token bucket (if rate limited)

        Returns:
            Dictionary of headers
        """
        if bucket is None:
            return {}

        return {
            "X-RateLimit-Limit": str(int(bucket.capacity)),
            "X-RateLimit-Remaining": str(int(bucket.tokens)),
            "X-RateLimit-Reset": str(int(bucket.last_update + 60)),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.

    Applies rate limiting to all API endpoints.
    """

    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.limiter = InMemoryRateLimiter(self.config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health checks
        if request.url.path.endswith("/health") or request.url.path.endswith("/health-check"):
            return await call_next(request)

        # Check rate limit
        allowed, bucket = await self.limiter.check_rate_limit(request)

        if not allowed:
            # Calculate retry time
            retry_after = 60  # Default to 60 seconds
            if bucket:
                retry_after = int(bucket.wait_time(1)) + 1

            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Retry after {retry_after} seconds.",
                    "retry_after": retry_after,
                },
            )
            response.headers["Retry-After"] = str(retry_after)

            # Add rate limit info headers
            if bucket:
                response.headers.update(self.limiter.get_rate_limit_headers(bucket))

            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        if bucket:
            response.headers.update(self.limiter.get_rate_limit_headers(bucket))

        return response


class RateLimitDecorator:
    """
    Decorator for rate limiting specific endpoints.

    Usage:
        @router.get("/expensive-endpoint")
        @rate_limit_decorator(requests_per_minute=10)
        async def expensive_endpoint():
            ...
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.key_func = key_func or self._default_key_func
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                tokens=requests_per_minute,
                capacity=requests_per_minute + burst_size,
                rate=requests_per_minute / 60.0,
            )
        )
        self._lock = asyncio.Lock()

    def _default_key_func(self, request: Request) -> str:
        """Default key function for rate limiting."""
        # Try to get user ID from request state
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""
        key = self.key_func(request)

        async with self._lock:
            bucket = self._buckets[key]

            if not bucket.consume(1):
                wait_time = bucket.wait_time(1)
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {int(wait_time) + 1} seconds.",
                    headers={"Retry-After": str(int(wait_time) + 1)},
                )

        return await call_next(request)


def rate_limit(requests_per_minute: int = 60, burst_size: int = 10):
    """
    Decorator factory for rate limiting endpoints.

    Usage:
        @router.get("/endpoint")
        @rate_limit(requests_per_minute=10)
        async def endpoint():
            ...

    Note: This is a simplified version. For production use,
    consider using the middleware approach with Redis backing.
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from kwargs (if available) or skip
            request = kwargs.get("request")

            if request:
                limiter = InMemoryRateLimiter(
                    RateLimitConfig(requests_per_minute=requests_per_minute)
                )
                allowed, _ = await limiter.check_rate_limit(request)

                if not allowed:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
