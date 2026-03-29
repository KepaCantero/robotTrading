"""
Compliance Module - Re-exports from domain layer

This module provides backward compatibility by re-exporting
compliance components from their canonical location in the domain layer.

DEPRECATED: Import directly from app.domain.services.compliance instead.
"""

from app.domain.services.compliance.portfolio_optimizer import PortfolioComplianceOptimizer
from app.domain.services.compliance.post_trade_checker import PostTradeComplianceChecker
from app.domain.services.compliance.pre_trade_checker import PreTradeComplianceChecker
from app.domain.services.compliance.protocols import (
    AlphaGeneratable,
    ComplianceService,
    CrossValidationService,
    ExecutionAlgorithm,
    LiquidityAnalyzable,
    MetaLabelingService,
    Optimizable,
    PostTradeCheckable,
    PreTradeCheckable,
    RegimeDetectable,
    RiskCalculable,
    TransactionCostModel,
)

# Re-export from domain layer for backward compatibility
from app.domain.services.compliance.results import (
    CheckResult,
    ComprehensivePostTradeAnalysis,
    ComprehensivePreTradeAnalysis,
    OptimizeResult,
    PortfolioOptimizationResult,
    PostTradeCheckResult,
    PreTradeCheckResult,
)
from app.domain.services.compliance.service_registry import (
    ComplianceServiceRegistry,
    get_service,
    get_service_registry,
)

__all__ = [
    "AlphaGeneratable",
    # Results
    "CheckResult",
    # Protocols
    "ComplianceService",
    # Registry
    "ComplianceServiceRegistry",
    "ComprehensivePostTradeAnalysis",
    "ComprehensivePreTradeAnalysis",
    "CrossValidationService",
    "ExecutionAlgorithm",
    "LiquidityAnalyzable",
    "MetaLabelingService",
    "Optimizable",
    "OptimizeResult",
    "PortfolioComplianceOptimizer",
    "PortfolioOptimizationResult",
    "PostTradeCheckResult",
    "PostTradeCheckable",
    "PostTradeComplianceChecker",
    "PreTradeCheckResult",
    "PreTradeCheckable",
    # Coordinators
    "PreTradeComplianceChecker",
    "RegimeDetectable",
    "RiskCalculable",
    "TransactionCostModel",
    "get_service",
    "get_service_registry",
]
