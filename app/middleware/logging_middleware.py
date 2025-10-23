"""
FastAPI Logging Integration
TASK-3: Configuración de logging centralizado
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.services.centralized_logging import (
    centralized_logger,
    LogService,
    LogLevel,
    log_performance
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Log HTTP requests and responses."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Log request
        centralized_logger.info(
            LogService.FASTAPI,
            f"Request started: {request.method} {request.url.path}",
            metadata={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length"),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = (time.time() - start_time) * 1000
            
            # Log response
            centralized_logger.info(
                LogService.FASTAPI,
                f"Request completed: {request.method} {request.url.path}",
                metadata={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration,
                    "response_size": response.headers.get("content-length"),
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = (time.time() - start_time) * 1000
            
            # Log error
            centralized_logger.error(
                LogService.FASTAPI,
                f"Request failed: {request.method} {request.url.path}",
                metadata={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration,
                    "error_type": type(e).__name__,
                },
                error_message=str(e)
            )
            
            raise


class TradingLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging trading-specific requests."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Log trading-specific requests."""
        # Check if this is a trading endpoint
        if request.url.path.startswith("/api/trading/"):
            # Log trading request
            centralized_logger.info(
                LogService.TRADING,
                f"Trading request: {request.method} {request.url.path}",
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Log trading response
        if request.url.path.startswith("/api/trading/"):
            centralized_logger.info(
                LogService.TRADING,
                f"Trading response: {request.method} {request.url.path}",
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                }
            )
        
        return response


class PortfolioLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging portfolio-specific requests."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Log portfolio-specific requests."""
        # Check if this is a portfolio endpoint
        if request.url.path.startswith("/api/portfolio/"):
            # Log portfolio request
            centralized_logger.info(
                LogService.PORTFOLIO,
                f"Portfolio request: {request.method} {request.url.path}",
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Log portfolio response
        if request.url.path.startswith("/api/portfolio/"):
            centralized_logger.info(
                LogService.PORTFOLIO,
                f"Portfolio response: {request.method} {request.url.path}",
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                }
            )
        
        return response


class MarketDataLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging market data requests."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Log market data requests."""
        # Check if this is a market data endpoint
        if request.url.path.startswith("/api/market-data/"):
            # Log market data request
            centralized_logger.info(
                LogService.MARKET_DATA,
                f"Market data request: {request.method} {request.url.path}",
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Log market data response
        if request.url.path.startswith("/api/market-data/"):
            centralized_logger.info(
                LogService.MARKET_DATA,
                f"Market data response: {request.method} {request.url.path}",
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                }
            )
        
        return response


# Performance logging decorators
def log_trading_performance(operation: str):
    """Decorator for logging trading performance."""
    return log_performance(LogService.TRADING, operation)


def log_portfolio_performance(operation: str):
    """Decorator for logging portfolio performance."""
    return log_performance(LogService.PORTFOLIO, operation)


def log_market_data_performance(operation: str):
    """Decorator for logging market data performance."""
    return log_performance(LogService.MARKET_DATA, operation)


def log_fastapi_performance(operation: str):
    """Decorator for logging FastAPI performance."""
    return log_performance(LogService.FASTAPI, operation)
