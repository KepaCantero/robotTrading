"""
T5.1: ValidationEngine - Models

Data models for validation requests and results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class ModuleViabilityAnalysis:
    """Analysis of module viability."""

    module_name: str
    enabled: bool
    reason: str
    recommendation: str
    cost_monthly: Optional[Decimal] = None
    cost_ratio: Optional[Decimal] = None


@dataclass
class CapitalViabilityAnalysis:
    """Analysis of capital viability for profit goals."""

    is_viable: bool
    required_alpha_pct: Decimal
    expected_alpha_pct: Decimal
    reason: str
    recommendation: str
    severity: str


@dataclass
class LearningViabilityAnalysis:
    """Analysis of learning module viability."""

    learning_recommended: bool
    reason: str
    recommendation: str
    severity: str
    capital_tier: str
    learning_cost_monthly: Decimal
    cost_benefit_ratio: Decimal


@dataclass
class FeasibilityAnalysis:
    """Analysis of feasibility ratio."""

    feasibility_ratio: Decimal
    feasibility_status: str  # APPROVED, CONDITIONAL, REJECTED
    is_viable: bool
    reason: str


@dataclass
class ValidationRequest:
    """Request for validation."""

    profile_id: str
    input_id: str
    initial_capital: Decimal
    target_monthly_return_eur: Decimal
    module_parameter_set_id: Optional[str] = None
    backtest_feasibility_ratio: Optional[Decimal] = None
    backtest_sharpe_ratio: Optional[Decimal] = None
    backtest_max_drawdown_pct: Optional[Decimal] = None
    expected_trades_per_month: int = 10
    tax_rate: Decimal = Decimal("0.35")
    commission_per_trade: Decimal = Decimal("15")
    learning_enabled: bool = True


@dataclass
class ValidationResult:
    """Result of validation."""

    success: bool
    profile_id: str
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)

    # Core validations
    passed: bool = False
    critical_failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Detailed analyses
    capital_viability: Optional[CapitalViabilityAnalysis] = None
    feasibility: Optional[FeasibilityAnalysis] = None
    learning_viability: Optional[LearningViabilityAnalysis] = None
    module_viabilities: Dict[str, ModuleViabilityAnalysis] = field(default_factory=dict)

    # Overall recommendation
    overall_recommendation: str = "PENDING"  # APPROVE, CONDITIONAL, REJECT, REVIEW_REQUIRED
    confidence_level: str = "high"  # high, medium, low
    error_message: Optional[str] = None
