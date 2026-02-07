import logging
import os
import platform
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# API-009 FIX: Import AuditMiddleware for request/response logging with correlation IDs
from app.api import AuditMiddleware

# ============================================================================
# CRITICAL: Enforce Numba availability BEFORE any other imports
# This ensures 100% Numba acceleration for all performance-critical code
# ============================================================================
try:
    from app.core.numba_enforcer import enforce_numba_available

    enforce_numba_available()  # Will raise RuntimeError if Numba not available
except RuntimeError as e:
    # Log the error and exit immediately
    logger.debug(str(e), file=sys.stderr)
    sys.exit(1)

import asyncio

from app.api.assets import router as assets_router
from app.api.capa2_endpoints import router as capa2_router
from app.api.cost_analysis import router as cost_analysis_router
from app.api.error_handler import (
    attribute_error_handler,
    generic_exception_handler,
    http_exception_handler,
    index_error_handler,
    key_error_handler,
    pydantic_validation_exception_handler,
    starlette_http_exception_handler,
    type_error_handler,
    validation_exception_handler,
    value_error_handler,
)
from app.api.health import router as health_router
from app.api.live_trading import router as live_trading_router
from app.api.market_data import router as market_data_router

# API-006 FIX: Import authentication and security middleware
from app.api.middleware import (
    AuthMiddleware,
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.momentum import router as momentum_router
from app.api.optimization import router as optimization_router
from app.api.paper_trading import router as paper_trading_router
from app.api.portfolio import router as portfolio_router
from app.api.portfolio_analytics import router as portfolio_analytics_router
from app.api.signals import router as signals_router
from app.api.trading_error_handler import router as trading_error_handler_router
from app.core.config import get_settings
from app.core.database import close_database, init_database

# AlgoTrading MVP - Main FastAPI Application
#
# Main entry point for the AlgoTrading MVP system.
# Implements health checks, CORS configuration, and basic error handling.
#
# Author: AlgoTrading MVP Team
# Version: 1.0.0

# ============================================================================
# SOLUCIÓN DEFINITIVA: Configurar variables de entorno ANTES de cualquier import
# Esto previene bloqueos de threading con mutex.cc
# Debe ir ANTES de importar numpy, pandas, torch, o cualquier otra librería
# ============================================================================

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCH_USE_CUDA_DSA'] = '0'


# IMPORTANT: Import logging_config FIRST to ensure all warnings/errors go to files
# Get application settings (lazy loading to avoid validation issues during
# import)
settings = None

# Logging is already configured by logging_config module
# Just get the logger
logger = logging.getLogger(__name__)


def get_app_settings():
    """Get application settings with lazy loading."""
    global settings  # pylint: disable=global-statement
    if settings is None:
        settings = get_settings()
        # Update logging configuration
        logging.getLogger().setLevel(getattr(logging, settings.log_level))
    return settings


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Get settings
    app_settings = get_app_settings()

    # Startup
    logger.info(f"Starting {app_settings.app_name} v{app_settings.app_version}")
    logger.info(f"Debug mode: {app_settings.debug}")
    logger.info(f"Log level: {app_settings.log_level}")

    # Initialize database and live trading tables
    try:
        await init_database()
        logger.info("Database and live trading tables initialized")
    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        logger.warning(f"Database initialization failed: {e}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Application shutdown initiated")

    # Close database connections
    try:
        await close_database()
        logger.info("Database connections closed")
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        logger.warning(f"Error closing database connections: {e}")

    logger.info("Application shutdown complete")


# Create FastAPI application instance
app = FastAPI(
    title="AlgoTrading MVP",  # Default title, will be updated
    description="Algorithmic Trading System MVP",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS middleware (will be updated when settings are loaded)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API-009 FIX: Add AuditMiddleware for request/response logging with correlation IDs
# This middleware logs all API requests and responses with:
# - Correlation IDs for request tracking
# - Request duration in milliseconds
# - Error logging with stack traces
# - Client identification
app.add_middleware(AuditMiddleware)

# API-006 FIX: Add authentication and security middleware
# These middleware provide:
# - Authentication for sensitive operations (deployment, strategies, optimization)
# - Correlation ID tracking for all requests
# - Security headers for all responses
# - Request logging for debugging and monitoring
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
# Note: AuthMiddleware is added last (executed first) to check auth before other middleware
# Authentication is enabled in production, can be disabled via environment variable
app.add_middleware(
    AuthMiddleware,
    require_auth=not get_app_settings().debug,  # Require auth in production only
    debug_mode=get_app_settings().debug,
)

# ============================================================================
# API-008: Comprehensive Exception Handlers with Error Logging
# ============================================================================
# These handlers provide centralized error logging with full context including:
# - Correlation IDs for request tracking
# - Stack traces for debugging
# - Request context (method, path, params)
# - Proper error responses to clients

from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# HTTP Exceptions (4xx, 5xx)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)

# Validation Errors
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)

# Common Python Exceptions with specific handlers
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(KeyError, key_error_handler)
app.add_exception_handler(TypeError, type_error_handler)
app.add_exception_handler(AttributeError, attribute_error_handler)
app.add_exception_handler(IndexError, index_error_handler)

# Generic catch-all for unhandled exceptions
app.add_exception_handler(Exception, generic_exception_handler)

# Include API routers
app.include_router(health_router)
app.include_router(capa2_router)
app.include_router(portfolio_router)
app.include_router(signals_router)
app.include_router(momentum_router)
app.include_router(assets_router)
app.include_router(market_data_router)
app.include_router(paper_trading_router)
app.include_router(portfolio_analytics_router)
app.include_router(cost_analysis_router)
app.include_router(optimization_router)
app.include_router(live_trading_router)
app.include_router(
    trading_error_handler_router,
    prefix="/trading-error-handler",
    tags=["Trading Error Handler"],
)

# SRE Error Budget System (Rule 20)


async def root() -> Dict[str, Any]:
    """
    Root endpoint providing basic application information.

    Returns:
        Dict containing application metadata
    """
    app_settings = get_app_settings()
    return {
        "name": app_settings.app_name,
        "version": app_settings.app_version,
        "description": app_settings.app_description,
        "status": "running",
        "debug": app_settings.debug,
        "docs": "/docs",
        "health": "/health",
        "health_detailed": "/health?detailed=true",
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint with system information.

    Returns:
        Dict with detailed health information
    """

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": get_app_settings().app_version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "system": {
            "name": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 error handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 error handler."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"  # nosec B104
    )
