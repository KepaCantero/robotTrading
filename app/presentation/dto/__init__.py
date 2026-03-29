"""
Data Transfer Objects for Presentation Layer

DTOs define the shape of data entering and leaving the system via API.
"""

from .requests import CreatePortfolioRequest, ExecuteStrategyRequest
from .responses import HealthResponse, PortfolioResponse, StrategyResponse

__all__ = [
    "CreatePortfolioRequest",
    "ExecuteStrategyRequest",
    "HealthResponse",
    "PortfolioResponse",
    "StrategyResponse",
]
