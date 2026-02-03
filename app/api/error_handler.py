"""
Comprehensive Error Handler for API Operations

This module provides centralized error logging and handling for all API endpoints.
It implements API-008 GAP fix - comprehensive error logging with context.

Features:
- HTTP exception logging with full context
- Validation error logging
- Generic exception logging
- Structured logging with correlation IDs
- Stack trace capture for debugging

Author: AlgoTrading MVP Team
Version: 1.0.0
GAP Fix: API-008
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import get_correlation_id

logger = logging.getLogger(__name__)


def log_exception_context(
    error_type: str,
    error_message: str,
    request: Request,
    status_code: Optional[int] = None,
    exc: Optional[Exception] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log exception with full context including correlation ID.

    Args:
        error_type: Type/class name of the error
        error_message: Error message/description
        request: FastAPI Request object
        status_code: Optional HTTP status code
        exc: Optional exception object for stack trace
        additional_context: Optional additional context data
    """
    correlation_id = get_correlation_id()

    log_data: Dict[str, Any] = {
        "event_type": "api_exception",
        "correlation_id": correlation_id,
        "error_type": error_type,
        "error_message": error_message,
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params) if request.query_params else None,
        "path_params": dict(request.path_params) if request.path_params else None,
        "client_host": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }

    if status_code is not None:
        log_data["status_code"] = status_code

    if additional_context:
        log_data.update(additional_context)

    # Add stack trace if exception provided
    exc_info = exc if exc else None

    logger.error(
        f"API exception: {error_type}",
        extra=log_data,
        exc_info=exc_info,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Log HTTP exceptions with full context.

    This handler captures all HTTPException (4xx, 5xx client and server errors)
    and logs them with correlation IDs and request context for debugging.

    Args:
        request: FastAPI Request object
        exc: HTTPException that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    log_exception_context(
        error_type="HTTPException",
        error_message=exc.detail,
        request=request,
        status_code=exc.status_code,
        exc=exc,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Log Starlette HTTP exceptions with full context.

    Args:
        request: FastAPI Request object
        exc: StarletteHTTPException that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    log_exception_context(
        error_type="StarletteHTTPException",
        error_message=exc.detail,
        request=request,
        status_code=exc.status_code,
        exc=exc,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Log validation errors with full context.

    This handler captures Pydantic validation errors and logs them with
    detailed field-level error information for debugging API input issues.

    Args:
        request: FastAPI Request object
        exc: RequestValidationError containing validation errors

    Returns:
        JSONResponse: Formatted validation error response
    """
    # Format validation errors for logging
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "loc": " -> ".join(str(loc) for loc in error["loc"]),
            "type": error["type"],
            "msg": error["msg"],
            "input": error.get("input"),
        })

    log_exception_context(
        error_type="RequestValidationError",
        error_message=f"Validation failed for {len(validation_errors)} field(s)",
        request=request,
        status_code=422,
        additional_context={
            "validation_errors": validation_errors,
            "body": getattr(exc, "body", None),
        },
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "validation_errors": exc.errors(),
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Log Pydantic validation errors with full context.

    Args:
        request: FastAPI Request object
        exc: ValidationError from Pydantic

    Returns:
        JSONResponse: Formatted validation error response
    """
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "loc": " -> ".join(str(loc) for loc in error["loc"]),
            "type": error["type"],
            "msg": error["msg"],
            "input": error.get("input"),
        })

    log_exception_context(
        error_type="PydanticValidationError",
        error_message=f"Pydantic validation failed for {len(validation_errors)} field(s)",
        request=request,
        status_code=422,
        additional_context={
            "validation_errors": validation_errors,
        },
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Data validation failed",
                "validation_errors": exc.errors(),
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Log unexpected exceptions with full context and stack trace.

    This is a catch-all handler for any unhandled exceptions. It logs
    the full stack trace for debugging while returning a generic error
    message to the client (to avoid exposing sensitive information).

    Args:
        request: FastAPI Request object
        exc: Unhandled exception

    Returns:
        JSONResponse: Generic error response
    """
    log_exception_context(
        error_type=type(exc).__name__,
        error_message=str(exc),
        request=request,
        status_code=500,
        exc=exc,
    )

    # Return generic error message to avoid exposing internal details
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An internal server error occurred",
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Log ValueError exceptions with context.

    Args:
        request: FastAPI Request object
        exc: ValueError that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    log_exception_context(
        error_type="ValueError",
        error_message=str(exc),
        request=request,
        status_code=400,
        exc=exc,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "type": "ValueError",
                "message": str(exc),
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    """
    Log KeyError exceptions with context.

    Args:
        request: FastAPI Request object
        exc: KeyError that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    log_exception_context(
        error_type="KeyError",
        error_message=f"Missing required key: {str(exc)}",
        request=request,
        status_code=400,
        exc=exc,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "type": "KeyError",
                "message": f"Missing required field: {str(exc)}",
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def type_error_handler(request: Request, exc: TypeError) -> JSONResponse:
    """
    Log TypeError exceptions with context.

    Args:
        request: FastAPI Request object
        exc: TypeError that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    log_exception_context(
        error_type="TypeError",
        error_message=str(exc),
        request=request,
        status_code=400,
        exc=exc,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "type": "TypeError",
                "message": "Invalid type provided",
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def attribute_error_handler(request: Request, exc: AttributeError) -> JSONResponse:
    """
    Log AttributeError exceptions with context.

    Args:
        request: FastAPI Request object
        exc: AttributeError that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    log_exception_context(
        error_type="AttributeError",
        error_message=str(exc),
        request=request,
        status_code=500,
        exc=exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "AttributeError",
                "message": "An internal error occurred",
                "correlation_id": get_correlation_id(),
            }
        },
    )


async def index_error_handler(request: Request, exc: IndexError) -> JSONResponse:
    """
    Log IndexError exceptions with context.

    Args:
        request: FastAPI Request object
        exc: IndexError that was raised

    Returns:
        JSONResponse: Formatted error response
    """
    log_exception_context(
        error_type="IndexError",
        error_message=str(exc),
        request=request,
        status_code=400,
        exc=exc,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "type": "IndexError",
                "message": "Invalid index provided",
                "correlation_id": get_correlation_id(),
            }
        },
    )


# Import JSONResponse
from fastapi.responses import JSONResponse


__all__ = [
    "http_exception_handler",
    "starlette_http_exception_handler",
    "validation_exception_handler",
    "pydantic_validation_exception_handler",
    "generic_exception_handler",
    "value_error_handler",
    "key_error_handler",
    "type_error_handler",
    "attribute_error_handler",
    "index_error_handler",
    "log_exception_context",
]
