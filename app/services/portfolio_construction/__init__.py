"""
Portfolio Construction & Optimization - T7.1 (PortfolioConstructor) + T18.1 Extensions

Provides:
- T7.1: PortfolioConstructor - Mean-variance and risk parity optimization
- T18.1.1: AllocationManager - Portfolio allocation tracking and management
- T18.1.2: RebalancingEngine - Dynamic rebalancing based on thresholds
- T18.1.3: AllocationRecommender - Smart allocation recommendations
"""

from app.services.portfolio_construction.portfolio_constructor import (
    PortfolioConstructor,
    PortfolioAllocation,
    OptimizationMethod,
)
from app.services.portfolio_construction.allocation_manager import (
    AllocationManager,
    get_allocation_manager,
    AllocationSnapshot,
    AllocationMetrics,
)
from app.services.portfolio_construction.rebalancing_engine import (
    RebalancingEngine,
    get_rebalancing_engine,
    RebalancingEvent,
    RebalancingTrade,
    RebalancingFrequency,
)
from app.services.portfolio_construction.allocation_recommender import (
    AllocationRecommender,
    get_allocation_recommender,
    AllocationRecommendation,
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
