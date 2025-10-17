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

# Application metadata (avoiding circular import)
__version__ = "1.0.0"
APP_NAME = "AlgoTrading MVP"
APP_DESCRIPTION = "Algorithmic Trading System MVP"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {APP_NAME} v{__version__}")
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown initiated")
    logger.info("Application shutdown complete")


# Create FastAPI application instance
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing basic application information.
    
    Returns:
        Dict containing application metadata
    """
    return {
        "name": APP_NAME,
        "version": __version__,
        "description": APP_DESCRIPTION,
        "status": "running",
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
        "version": __version__,
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
