"""
Multi-Asset Portfolio Support Module

This module provides comprehensive support for managing portfolios across multiple asset classes
including equities, fixed income, crypto, forex, commodities, real estate, and cash.

FASE 7.2 - Multi-Asset Portfolio Support

Key Features:
- Asset class definition and management
- Multi-asset portfolio construction
- Strategic and tactical allocation
- Risk parity allocation
- Multi-asset rebalancing
- Risk contribution analysis
- Correlation-aware allocation

Example Usage:
    >>> from app.portfolio.multi_asset import (
    ...     MultiAssetPortfolioManager,
    ...     MultiAssetConfig,
    ...     AssetClass,
    ...     AssetClassType
    ... )
    >>>
    >>> # Define asset classes
    >>> equity_class = AssetClass(
    ...     name="US Equities",
    ...     type=AssetClassType.EQUITY,
    ...     expected_return=Decimal("0.08"),
    ...     volatility=Decimal("0.15")
    ... )
    >>>
    >>> # Create portfolio manager
    >>> config = MultiAssetConfig(
    ...     asset_classes=[equity_class, ...],
    ...     rebalance_threshold=Decimal("0.05")
    ... )
    >>> manager = MultiAssetPortfolioManager(config)
    >>>
    >>> # Construct portfolio
    >>> portfolio = manager.construct_portfolio(
    ...     target_weights={"equity": Decimal("0.6"), "bonds": Decimal("0.4")},
    ...     market_data=market_data
    ... )
"""

from .allocation import (
    AllocationResult,
    MarketRegime,
    MultiAssetAllocator,
    RiskParityAllocationParams,
    StrategicAllocationParams,
    TacticalAllocationParams,
)
from .asset_class import (
    AssetClass,
    AssetClassConfig,
    AssetClassMetrics,
    AssetClassReturns,
    AssetClassType,
    RebalanceFrequency,
)
from .models import (
    AllocationStrategy,
    MultiAssetAllocation,
    MultiAssetPortfolio,
    PortfolioMetrics,
    RiskTolerance,
    Trade,
)
from .multi_asset_portfolio import (
    MultiAssetConfig,
    MultiAssetPortfolioManager,
    PortfolioConstructionResult,
    RebalanceResult,
)
from .rebalancer import (
    CostEstimate,
    MultiAssetRebalancer,
    RebalancePlan,
    RebalancePriority,
    RebalanceTrade,
)

__all__ = [
    # Asset classes
    "AssetClass",
    "AssetClassType",
    "AssetClassConfig",
    "AssetClassMetrics",
    "AssetClassReturns",
    "RebalanceFrequency",
    # Models
    "MultiAssetAllocation",
    "MultiAssetPortfolio",
    "PortfolioMetrics",
    "Trade",
    "RiskTolerance",
    "AllocationStrategy",
    # Portfolio Manager
    "MultiAssetPortfolioManager",
    "MultiAssetConfig",
    "PortfolioConstructionResult",
    "RebalanceResult",
    # Allocation
    "MultiAssetAllocator",
    "StrategicAllocationParams",
    "TacticalAllocationParams",
    "RiskParityAllocationParams",
    "AllocationResult",
    "MarketRegime",
    # Rebalancing
    "MultiAssetRebalancer",
    "RebalanceTrade",
    "RebalancePriority",
    "CostEstimate",
    "RebalancePlan",
]

__version__ = "1.0.0"
__author__ = "AlgoTrading Team"
