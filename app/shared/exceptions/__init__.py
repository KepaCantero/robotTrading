"""
FastAPI Error Handling Integration
TASK-4: Sistema de manejo de errores unificado

REFACTORED: Uses lazy imports and TYPE_CHECKING to avoid circular dependencies.
All imports from potentially circular modules are now deferred or type-only.
"""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Direct import from independent exceptions module (no circular dependency)
from app.shared.exceptions.exceptions import AlgoTradingError


def _get_error_handlers() -> (
    tuple[
        Callable,
        Callable,
        Callable,
        Callable,
    ]
):
    """
    Lazily import error handlers to avoid circular dependencies.

    Returns:
        Tuple of error handler functions
    """
    # Lazy import - only loaded when actually needed
    from app.shared.exceptions.error_handler import (
        algotrading_exception_handler,
        generic_exception_handler,
        starlette_http_exception_handler,
        validation_exception_handler,
    )

    return (
        algotrading_exception_handler,
        generic_exception_handler,
        starlette_http_exception_handler,
        validation_exception_handler,
    )


def _get_middleware_classes() -> (
    tuple[
        type,
        type,
        type,
        type,
        type,
    ]
):
    """
    Lazily import middleware classes to avoid circular dependencies.

    Returns:
        Tuple of middleware classes
    """
    from app.infrastructure.middleware.error_middleware import (
        ErrorHandlingMiddleware,
        HealthCheckMiddleware,
        RateLimitingMiddleware,
        RequestContextMiddleware,
        SecurityHeadersMiddleware,
    )

    return (
        ErrorHandlingMiddleware,
        HealthCheckMiddleware,
        RateLimitingMiddleware,
        RequestContextMiddleware,
        SecurityHeadersMiddleware,
    )


def setup_error_handling(app: FastAPI) -> None:
    """
    Setup error handling for FastAPI application.

    Uses lazy imports internally to avoid circular dependencies at module load time.
    """
    from typing import Callable, Union

    # Lazily load error handlers (avoids circular import at module load)
    (
        algotrading_handler,
        generic_handler,
        starlette_handler,
        validation_handler,
    ) = _get_error_handlers()

    # Define proper type for exception handlers
    ExceptionHandlerType = Callable[
        [type[Exception], Union[Exception, RequestValidationError]], None
    ]

    # Add exception handlers with proper type annotations
    handler_algotrading: ExceptionHandlerType = algotrading_handler
    handler_validation: ExceptionHandlerType = validation_handler
    handler_starlette: ExceptionHandlerType = starlette_handler
    handler_generic: ExceptionHandlerType = generic_handler

    app.add_exception_handler(AlgoTradingError, handler_algotrading)
    app.add_exception_handler(RequestValidationError, handler_validation)
    app.add_exception_handler(StarletteHTTPException, handler_starlette)
    app.add_exception_handler(Exception, handler_generic)

    # Lazily load middleware classes (avoids circular import at module load)
    (
        error_handling_middleware,
        health_check_middleware,
        rate_limiting_middleware,
        request_context_middleware,
        security_headers_middleware,
    ) = _get_middleware_classes()

    # Add middleware (order matters!)
    app.add_middleware(health_check_middleware)
    app.add_middleware(security_headers_middleware, enable_cors=True)
    app.add_middleware(rate_limiting_middleware, requests_per_minute=100)
    app.add_middleware(request_context_middleware)
    app.add_middleware(error_handling_middleware, enable_request_logging=True)


def create_error_handling_app() -> FastAPI:
    """Create FastAPI app with error handling configured."""

    app = FastAPI(
        title="AlgoTrading API",
        description="Algorithmic Trading API with comprehensive error handling",
        version="1.0.0",
    )

    # Setup error handling
    setup_error_handling(app)

    return app

    # Export main classes and functions

    # Main classes
