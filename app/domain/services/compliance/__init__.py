"""
Compliance Module
=================

Refactored compliance integration following SOLID principles.

Architecture:
    - ServiceRegistry: Central registration for all 12 services
    - PreTradeChecker: Coordinates pre-trade checks
    - PostTradeChecker: Coordinates post-trade analysis
    - PortfolioOptimizer: Coordinates portfolio optimization
    - Facade: Simplified interface for clients

This module addresses SOL-001 violation by separating concerns:
    - Single Responsibility: Each class has one job
    - Open/Closed: Easy to add new services via registry
    - Liskov Substitution: All services implement protocols
    - Interface Segregation: Focused protocol interfaces
    - Dependency Inversion: Depend on abstractions (protocols)

Author: Compliance Integration System
Date: 2026-02-03
"""

from .portfolio_optimizer import PortfolioComplianceOptimizer
from .post_trade_checker import PostTradeComplianceChecker
from .pre_trade_checker import PreTradeComplianceChecker
from .protocols import (
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
from .results import (
    CheckResult,
    ComprehensivePostTradeAnalysis,
    ComprehensivePreTradeAnalysis,
    OptimizeResult,
    PortfolioOptimizationResult,
    PostTradeCheckResult,
    PreTradeCheckResult,
)
from .service_registry import (
    ComplianceServiceRegistry,
    get_service,
    get_service_registry,
)

__all__ = [
    # Protocols
    "ComplianceService",
    "PreTradeCheckable",
    "PostTradeCheckable",
    "Optimizable",
    "RegimeDetectable",
    "AlphaGeneratable",
    "RiskCalculable",
    "LiquidityAnalyzable",
    "ExecutionAlgorithm",
    "TransactionCostModel",
    "MetaLabelingService",
    "CrossValidationService",
    # Results
    "CheckResult",
    "PreTradeCheckResult",
    "PostTradeCheckResult",
    "OptimizeResult",
    "ComprehensivePreTradeAnalysis",
    "ComprehensivePostTradeAnalysis",
    "PortfolioOptimizationResult",
    # Registry
    "ComplianceServiceRegistry",
    "get_service_registry",
    "get_service",
    # Coordinators
    "PreTradeComplianceChecker",
    "PostTradeComplianceChecker",
    "PortfolioComplianceOptimizer",
]
