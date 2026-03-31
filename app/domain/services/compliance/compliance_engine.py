"""Backward-compatibility re-export. Canonical module: app.services.compliance.compliance_engine."""

from app.services.compliance.compliance_engine import (
    ComplianceConfig,
    ComplianceEngine,
    CycleResult,
    PortfolioOptimization,
    PostTradeAnalysis,
    PreTradeAnalysis,
    SystemAvailability,
    SystemBus,
    TradeResult,
    get_compliance_engine,
    get_execution_plan,
    quick_check,
)

__all__ = [
    "ComplianceConfig",
    "ComplianceEngine",
    "CycleResult",
    "PortfolioOptimization",
    "PostTradeAnalysis",
    "PreTradeAnalysis",
    "SystemAvailability",
    "SystemBus",
    "TradeResult",
    "get_compliance_engine",
    "get_execution_plan",
    "quick_check",
]
