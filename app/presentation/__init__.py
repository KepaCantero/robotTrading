"""
Presentation Layer - API Controllers, Views, and DTOs

This layer handles:
- HTTP API endpoints
- WebSocket connections
- Request/Response DTOs
- Dashboard views

Dependencies: Can depend on Application and Domain layers
"""

from . import controllers, dto, views
from .controllers import dashboard_router, portfolio_router, strategy_router
from .dto import (
    CreatePortfolioRequest,
    ExecuteStrategyRequest,
    HealthResponse,
    PortfolioResponse,
    StrategyResponse,
)

__all__ = [
    "CreatePortfolioRequest",
    "ExecuteStrategyRequest",
    "HealthResponse",
    "PortfolioResponse",
    "StrategyResponse",
    "controllers",
    "dashboard_router",
    "dto",
    "portfolio_router",
    "strategy_router",
    "views",
]
