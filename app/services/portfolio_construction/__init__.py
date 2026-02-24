"""
Portfolio Construction & Optimization - T7.1 (PortfolioConstructor) + T18.1 Extensions

Provides:
- T7.1: PortfolioConstructor - Mean-variance and risk parity optimization
- T18.1.1: AllocationManager - Portfolio allocation tracking and management
- T18.1.2: RebalancingEngine - Dynamic rebalancing based on thresholds
- T18.1.3: AllocationRecommender - Smart allocation recommendations
"""

from app.services.portfolio_construction.allocation_manager import (
    AllocationManager,
    AllocationMetrics,
    AllocationSnapshot,
    get_allocation_manager,
)
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
from app.services.portfolio_construction.rebalancing_engine import (
    RebalancingEngine,
    RebalancingEvent,
    RebalancingFrequency,
    RebalancingTrade,
    get_rebalancing_engine,
)

__all__ = [
    "PortfolioConstructor",
    "PortfolioAllocation",
    "OptimizationMethod",
    "AllocationManager",
    "get_allocation_manager",
    "AllocationSnapshot",
    "AllocationMetrics",
    "RebalancingEngine",
    "get_rebalancing_engine",
    "RebalancingEvent",
    "RebalancingTrade",
    "RebalancingFrequency",
    "AllocationRecommender",
    "get_allocation_recommender",
    "AllocationRecommendation",
]
