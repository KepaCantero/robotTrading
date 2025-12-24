"""
PHASE 2 T2.1 - Smart Order Routing Engine

Intelligent routing for large orders (€25k+) to minimize execution costs
while maintaining optimal execution prices.

Components:
- BrokerNegotiationEngine: Commission rate negotiation by volume
- OrderSplittingOptimizer: VWAP/TWAP/POI order splitting
- MarketImpactEstimator: Market impact & slippage prediction
- ExecutionCostMonitor: Real-time cost tracking
- SmartOrderRouter: Main orchestrator
"""

from .models import (
    ExecutionPlan,
    OrderTranche,
    MarketImpactEstimate,
    ExecutionMonitoring,
)

__all__ = [
    "ExecutionPlan",
    "OrderTranche",
    "MarketImpactEstimate",
    "ExecutionMonitoring",
]
