"""
Portfolio Construction & Optimization - T7.1 (PortfolioConstructor) + T18.1 Extensions

Provides:
- T7.1: PortfolioConstructor - Mean-variance and risk parity optimization
- T18.1.3: AllocationRecommender - Smart allocation recommendations
"""

from app.services.portfolio_construction.allocation_recommender import (
    AllocationRecommendation,
    AllocationRecommender,
    get_allocation_recommender,
)
from app.services.portfolio_construction.portfolio_constructor import (
    OptimizationMethod,
    PortfolioAllocation,
    PortfolioConstructor,
)

__all__ = [
    "AllocationMetrics",
    "AllocationRecommendation",
    "AllocationRecommender",
    "OptimizationMethod",
    "PortfolioAllocation",
    "PortfolioConstructor",
    "RebalancingFrequency",
    "get_allocation_recommender",
]
