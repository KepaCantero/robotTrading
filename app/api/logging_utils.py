"""
Logging utilities for API endpoints with correlation ID support.

This module provides helper functions for structured logging with correlation IDs
to enable request tracking throughout the application.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Request


logger = logging.getLogger(__name__)


def get_correlation_id_from_request(request: Request) -> str:
    """
    Extract correlation ID from request state.

    Args:
        request: The FastAPI Request object

    Returns:
        str: The correlation ID for the current request, or "unknown" if not set
    """
    return getattr(request.state, "correlation_id", "unknown")


def log_with_context(
    request: Request,
    message: str,
    level: str = "info",
    **kwargs: Any,
) -> None:
    """
    Log message with correlation ID context.

    Args:
        request: The FastAPI Request object
        message: The log message
        level: The log level (debug, info, warning, error, critical)
        **kwargs: Additional context to include in the log

    Example:
        ```python
        @router.get("/endpoint")
        async def endpoint(request: Request):
            log_with_context(
                request,
                "Endpoint called",
                "info",
                endpoint="my_endpoint",
                user_id="123"
            )
        ```
    """
    correlation_id = get_correlation_id_from_request(request)
    log_func = getattr(logger, level.lower(), logger.info)

    log_data = {
        "correlation_id": correlation_id,
        **kwargs,
    }

    log_func(message, extra=log_data)


def log_info(
    request: Request,
    message: str,
    **kwargs: Any,
) -> None:
    """
    Log info level message with correlation ID.

    Args:
        request: The FastAPI Request object
        message: The log message
        **kwargs: Additional context to include in the log
    """
    log_with_context(request, message, "info", **kwargs)


def log_warning(
    request: Request,
    message: str,
    **kwargs: Any,
) -> None:
    """
    Log warning level message with correlation ID.

    Args:
        request: The FastAPI Request object
        message: The log message
        **kwargs: Additional context to include in the log
    """
    log_with_context(request, message, "warning", **kwargs)


def log_error(
    request: Request,
    message: str,
    exception: Optional[Exception] = None,
    **kwargs: Any,
) -> None:
    """
    Log error level message with correlation ID and optional exception details.

    Args:
        request: The FastAPI Request object
        message: The log message
        exception: Optional exception to log
        **kwargs: Additional context to include in the log
    """
    log_data = kwargs.copy()

    if exception:
        log_data.update(
            {
                "error_type": type(exception).__name__,
                "error_message": str(exception),
            }
        )

    log_with_context(request, message, "error", **log_data)


def log_debug(
    request: Request,
    message: str,
    **kwargs: Any,
) -> None:
    """
    Log debug level message with correlation ID.

    Args:
        request: The FastAPI Request object
        message: The log message
        **kwargs: Additional context to include in the log
    """
    log_with_context(request, message, "debug", **kwargs)


__all__ = [
    "get_correlation_id_from_request",
    "log_with_context",
    "log_info",
    "log_warning",
    "log_error",
    "log_debug",
]
