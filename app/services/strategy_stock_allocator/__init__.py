"""Strategy stock allocator module."""

from __future__ import annotations

# Import StrategyStockAllocator from the private implementation module
# (underscore-prefixed to avoid shadowing by this package's __init__.py)
from app.services._strategy_stock_allocator import StrategyStockAllocator

# Re-export domain models for backward compatibility
from app.services.strategy_stock_allocator.domain_models import (
    AllocationConfig,
    AllocationResult,
    PairMetrics,
    StockCategory,
    StockMetrics,
    StrategyType,
)

__all__ = [
    "AllocationConfig",
    "AllocationResult",
    "PairMetrics",
    "StockCategory",
    "StockMetrics",
    "StrategyStockAllocator",
    "StrategyType",
]
