"""
FastAPI Error Handling Integration
TASK-4: Sistema de manejo de errores unificado
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.error_handler import (
    algotrading_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    starlette_http_exception_handler,
    generic_exception_handler
)
from app.exceptions.trading_exceptions import AlgoTradingError
from app.middleware.error_middleware import (
    ErrorHandlingMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    RateLimitingMiddleware,
    HealthCheckMiddleware
)


def setup_error_handling(app: FastAPI) -> None:
    """Setup error handling for FastAPI application."""
    
    # Add exception handlers
    app.add_exception_handler(AlgoTradingError, algotrading_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
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
        version="1.0.0"
    )
    
    # Setup error handling
    setup_error_handling(app)
    
    return app


# Export main classes and functions
from app.exceptions.trading_exceptions import (
    AlgoTradingError,
    ValidationError,
    BusinessLogicError,
    ExternalAPIError,
    DatabaseError,
    NetworkError,
    ConfigurationError,
    SecurityError,
    PerformanceError,
    SystemError,
    ErrorSeverity,
    ErrorCategory,
    TradingError,
    SignalError,
    PortfolioError,
    RiskManagementError,
    MarketDataError,
    BrokerError
)

from app.exceptions.error_handler import (
    ErrorHandler,
    error_handler,
    create_error_response,
    raise_validation_error,
    raise_business_logic_error,
    raise_external_api_error,
    raise_database_error,
    raise_configuration_error
)

__all__ = [
    # Main classes
    "AlgoTradingError",
    "ValidationError",
    "BusinessLogicError",
    "ExternalAPIError",
    "DatabaseError",
    "NetworkError",
    "ConfigurationError",
    "SecurityError",
    "PerformanceError",
    "SystemError",
    "TradingError",
    "SignalError",
    "PortfolioError",
    "RiskManagementError",
    "MarketDataError",
    "BrokerError",
    
    # Enums
    "ErrorSeverity",
    "ErrorCategory",
    
    # Handler
    "ErrorHandler",
    "error_handler",
    
    # Functions
    "create_error_response",
    "raise_validation_error",
    "raise_business_logic_error",
    "raise_external_api_error",
    "raise_database_error",
    "raise_configuration_error",
    
    # FastAPI integration
    "setup_error_handling",
    "create_error_handling_app"
]
