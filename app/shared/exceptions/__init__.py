"""
FastAPI Error Handling Integration
TASK-4: Sistema de manejo de errores unificado
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import from core exceptions to avoid circular dependencies
from app.core.exceptions import AlgoTradingError
from app.exceptions.error_handler import (
    algotrading_exception_handler,
    generic_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
)
from app.infrastructure.middleware.error_middleware import (
    ErrorHandlingMiddleware,
    HealthCheckMiddleware,
    RateLimitingMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)


def setup_error_handling(app: FastAPI) -> None:
    """Setup error handling for FastAPI application."""

    # Add exception handlers
    app.add_exception_handler(AlgoTradingError, algotrading_exception_handler)  # type: ignore
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)  # type: ignore
    app.add_exception_handler(Exception, generic_exception_handler)

    # Add middleware (order matters!)
    app.add_middleware(HealthCheckMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, enable_cors=True)
    app.add_middleware(RateLimitingMiddleware, requests_per_minute=100)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(ErrorHandlingMiddleware, enable_request_logging=True)


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
