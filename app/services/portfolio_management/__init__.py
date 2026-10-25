"""Portfolio management (robo-advisor mode): profile → target portfolio →
drift-band, cash-flow-first, tax-aware rebalancing on the live order path.

Public surface used by the dashboard page and the daily runner.
"""

from __future__ import annotations

from .drift import compute_drift, cooldown_ends_at, in_cooldown
from .executor import ExecutionOutcome, RebalanceExecutor
from .models import (
    ASSET_CLASS,
    OBJECTIVES,
    RISK_SETTINGS,
    DriftStatus,
    Holding,
    LotSnapshot,
    PlannedTrade,
    PlanStatus,
    ProfileAnswers,
    RebalancePlan,
    RebalanceTrigger,
    SellTaxImpact,
    TargetPortfolio,
)
from .planner import PlanContext, plan_rebalance
from .store import PortfolioManagementStore
from .tax import SpainRebalanceTax
from .winner_adoption import adopt_target, build_target, latest_winner, seed_target

__all__ = [
    "ASSET_CLASS",
    "ExecutionOutcome",
    "Holding",
    "LotSnapshot",
    "OBJECTIVES",
    "PlanContext",
    "PlanStatus",
    "PlannedTrade",
    "PortfolioManagementStore",
    "ProfileAnswers",
    "RISK_SETTINGS",
    "RebalanceExecutor",
    "RebalancePlan",
    "RebalanceTrigger",
    "SellTaxImpact",
    "SpainRebalanceTax",
    "TargetPortfolio",
    "DriftStatus",
    "adopt_target",
    "build_target",
    "compute_drift",
    "cooldown_ends_at",
    "in_cooldown",
    "latest_winner",
    "plan_rebalance",
    "seed_target",
]
