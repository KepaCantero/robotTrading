"""
AlgoTrading MVP - Main FastAPI Application

Main entry point for the AlgoTrading MVP system.
Implements health checks, CORS configuration, and basic error handling.

Author: AlgoTrading MVP Team
Version: 1.0.0
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings, get_cors_config
from app.api.portfolio import router as portfolio_router
from app.api.signals import router as signals_router
from app.api.momentum import router as momentum_router
from app.api.assets import router as assets_router
from app.api.market_data import router as market_data_router
from app.api.paper_trading import router as paper_trading_router
from app.api.portfolio_analytics import router as portfolio_analytics_router
from app.api.cost_analysis import router as cost_analysis_router
from app.api.optimization import router as optimization_router

# Get application settings (lazy loading to avoid validation issues during import)
settings = None

# Configure logging (will be updated when settings are loaded)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_app_settings():
    """Get application settings with lazy loading."""
    global settings
    if settings is None:
        settings = get_settings()
        # Update logging configuration
        logging.getLogger().setLevel(getattr(logging, settings.log_level))
    return settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Get settings
    app_settings = get_app_settings()
    
    # Startup
    logger.info(f"Starting {app_settings.app_name} v{app_settings.app_version}")
    logger.info(f"Debug mode: {app_settings.debug}")
    logger.info(f"Log level: {app_settings.log_level}")
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown initiated")
    logger.info("Application shutdown complete")


# Create FastAPI application instance
app = FastAPI(
    title="AlgoTrading MVP",  # Default title, will be updated
    description="Algorithmic Trading System MVP",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS middleware (will be updated when settings are loaded)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(portfolio_router)
app.include_router(signals_router)
app.include_router(momentum_router)
app.include_router(assets_router)
app.include_router(market_data_router)
app.include_router(paper_trading_router)
app.include_router(portfolio_analytics_router)
app.include_router(cost_analysis_router)
app.include_router(optimization_router)


@app.get("/", tags=["Root"])
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
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Dict with status information
    """
    return {"status": "ok"}


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint with system information.
    
    Returns:
        Dict with detailed health information
    """
    import platform
    import sys
    from datetime import datetime
    
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": get_app_settings().app_version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "system": {
            "name": platform.system(),
            "release": platform.release(),
            "machine": platform.machine()
        }
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 error handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 error handler."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
