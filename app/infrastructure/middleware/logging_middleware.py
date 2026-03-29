"""
FastAPI Logging Integration
TASK-3: Configuración de logging centralizado
"""

from __future__ import annotations

import functools
import time
import uuid
from typing import TYPE_CHECKING, Callable, TypeVar

from starlette.middleware.base import BaseHTTPMiddleware
from typing_extensions import ParamSpec

from app.infrastructure.logging.logging_config import LogService, get_logger

if TYPE_CHECKING:
    import logging
    from collections.abc import Awaitable

    from fastapi import Request, Response
    from starlette.types import ASGIApp

logger = get_logger(__name__)
centralized_logger: logging.Logger = logger

# Type variables for generic decorator typing
P = ParamSpec("P")
T = TypeVar("T")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log request and response."""
        request_id = str(uuid.uuid4())

        # Start timing
        start_time = time.time()

        # Log request
        centralized_logger.info(
            f"[{LogService.FASTAPI}] Request started: {request.method} {request.url.path} | "
            f"request_id={request_id} client={request.client.host if request.client else None}"
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = (time.time() - start_time) * 1000

            # Log response
            centralized_logger.info(
                f"[{LogService.FASTAPI}] Request completed: {request.method} {request.url.path} | "
                f"request_id={request_id} status={response.status_code} duration_ms={duration:.2f}"
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except (ConnectionError, TimeoutError) as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000

            # Log error with stack trace (LOG-004)
            centralized_logger.error(
                f"[{LogService.FASTAPI}] Request failed: {request.method} {request.url.path} | "
                f"request_id={request_id} error_type={type(e).__name__} duration_ms={duration:.2f} | "
                f"error={e!s}",
                exc_info=True,  # LOG-004: Include stack trace
            )

            raise


class TradingLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging trading-specific requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log trading-specific requests."""
        # Check if this is a trading endpoint
        if request.url.path.startswith("/api/trading/"):
            centralized_logger.info(
                f"[{LogService.TRADING}] Trading request: {request.method} {request.url.path}"
            )

        # Process request
        response = await call_next(request)

        # Log trading response
        if request.url.path.startswith("/api/trading/"):
            centralized_logger.info(
                f"[{LogService.TRADING}] Trading response: {request.method} {request.url.path} status={response.status_code}"
            )

        return response


class PortfolioLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging portfolio-specific requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log portfolio-specific requests."""
        # Check if this is a portfolio endpoint
        if request.url.path.startswith("/api/portfolio/"):
            centralized_logger.info(
                f"[{LogService.PORTFOLIO}] Portfolio request: {request.method} {request.url.path}"
            )

        # Process request
        response = await call_next(request)

        # Log portfolio response
        if request.url.path.startswith("/api/portfolio/"):
            centralized_logger.info(
                f"[{LogService.PORTFOLIO}] Portfolio response: {request.method} {request.url.path} status={response.status_code}"
            )

        return response


class MarketDataLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging market data requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log market data requests."""
        # Check if this is a market data endpoint
        if request.url.path.startswith("/api/market-data/"):
            centralized_logger.info(
                f"[{LogService.MARKET_DATA}] Market data request: {request.method} {request.url.path}"
            )

        # Process request
        response = await call_next(request)

        # Log market data response
        if request.url.path.startswith("/api/market-data/"):
            centralized_logger.info(
                f"[{LogService.MARKET_DATA}] Market data response: {request.method} {request.url.path} status={response.status_code}"
            )

        return response


# Performance logging decorators
def log_trading_performance(
    operation: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for logging trading performance."""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                centralized_logger.info(
                    f"[{LogService.TRADING}] {operation} completed | duration_ms={duration:.2f}"
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                centralized_logger.error(
                    f"[{LogService.TRADING}] {operation} failed | error_type={type(e).__name__} duration_ms={duration:.2f} | error={e!s}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def log_portfolio_performance(
    operation: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for logging portfolio performance."""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                centralized_logger.info(
                    f"[{LogService.PORTFOLIO}] {operation} completed | duration_ms={duration:.2f}"
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                centralized_logger.error(
                    f"[{LogService.PORTFOLIO}] {operation} failed | error_type={type(e).__name__} duration_ms={duration:.2f} | error={e!s}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def log_market_data_performance(
    operation: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for logging market data performance."""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                centralized_logger.info(
                    f"[{LogService.MARKET_DATA}] {operation} completed | duration_ms={duration:.2f}"
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                centralized_logger.error(
                    f"[{LogService.MARKET_DATA}] {operation} failed | error_type={type(e).__name__} duration_ms={duration:.2f} | error={e!s}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def log_fastapi_performance(
    operation: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for logging FastAPI performance."""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                centralized_logger.info(
                    f"[{LogService.FASTAPI}] {operation} completed | duration_ms={duration:.2f}"
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                centralized_logger.error(
                    f"[{LogService.FASTAPI}] {operation} failed | error_type={type(e).__name__} duration_ms={duration:.2f} | error={e!s}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator
