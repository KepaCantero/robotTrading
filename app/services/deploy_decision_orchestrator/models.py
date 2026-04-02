"""
T10.1: DeployDecisionOrchestrator - Models for master deployment decision

Orchestrates final decision to deploy strategy or not based on:
- Feasibility ratio from backtesting
- Validation gate results
- Strategy recommendation score
- Portfolio metrics
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from decimal import Decimal

logger = logging.getLogger(__name__)


class DeploymentInput(BaseModel):
    """Complete input for deployment decision."""

    decision_id: str = Field(..., description="Unique decision identifier")
    profile_id: str = Field(..., description="Investment profile ID")
    input_id: str = Field(..., description="User input ID")
    strategy_name: str = Field(..., description="Strategy name")

    # From backtest results
    feasibility_ratio: Decimal = Field(..., description="Feasibility ratio (actual/target return)")
    annual_return_pct: Decimal = Field(..., description="Annual return %")
    max_drawdown_pct: Decimal = Field(..., description="Max drawdown %")
    sharpe_ratio: Decimal = Field(..., description="Sharpe ratio")
    win_rate_pct: Decimal = Field(..., description="Win rate %")

    # From validation engine
    validation_passed: bool = Field(..., description="Validation gates passed")
    validation_failures: list[str] = Field(default=[], description="Validation failure reasons")
    validation_warnings: list[str] = Field(default=[], description="Validation warnings")

    # From strategy recommender
    recommendation_score: Decimal = Field(..., description="Recommendation score (0-100)")
    recommendation_status: str = Field(
        ..., description="Status: STRONG_BUY/BUY/HOLD/REVIEW/NOT_RECOMMENDED"
    )
    recommendation_confidence: str = Field(..., description="Confidence level: high/medium/low")

    # From portfolio constructor
    num_modules: int = Field(..., description="Number of modules in portfolio")
    top_allocation_pct: Decimal = Field(..., description="Largest allocation % (concentration)")
    diversification_ratio: Decimal = Field(..., description="Portfolio diversification ratio")

    # User targets
    target_annual_return_pct: Decimal = Field(..., description="User target return %")
    max_acceptable_drawdown_pct: Decimal = Field(..., description="User max acceptable drawdown %")

    # T4.1: Capacity fade validation results (optional, added in PHASE 6)
    capacity_fade_feasible: bool | None = Field(
        default=None, description="T4.1 capacity fade feasibility"
    )
    estimated_alpha_at_scale: Decimal | None = Field(
        default=None, description="T4.1 estimated alpha at target capital"
    )
    capacity_fade_assessment: str | None = Field(
        default=None, description="T4.1 capacity fade assessment details"
    )
    current_capital: Decimal | None = Field(
        default=None, description="Current capital (for capacity fade analysis)"
    )
    target_capital: Decimal | None = Field(
        default=None, description="Target capital (for capacity fade analysis)"
    )

    execution_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Decision timestamp"
    )


class DeploymentRationale(BaseModel):
    """Detailed rationale for deployment decision."""

    feasibility_assessment: str = Field(..., description="Feasibility analysis")
    validation_assessment: str = Field(..., description="Validation analysis")
    recommendation_assessment: str = Field(..., description="Recommendation analysis")
    risk_assessment: str = Field(..., description="Risk assessment")
    diversification_assessment: str = Field(..., description="Diversification assessment")
    capacity_fade_assessment: str | None = Field(
        default=None, description="T4.1 capacity fade analysis (PHASE 6)"
    )
    overall_assessment: str = Field(..., description="Overall decision rationale")

    critical_factors: list[str] = Field(..., description="Critical factors influencing decision")
    improvement_areas: list[str] = Field(..., description="Areas for improvement if applicable")
    conditions: list[str] = Field(default=[], description="Conditions for conditional approval")


class DeploymentDecision(BaseModel):
    """Final deployment decision."""

    success: bool = Field(default=True, description="Decision success")
    decision_id: str = Field(..., description="Decision ID")
    profile_id: str = Field(..., description="Profile ID")
    strategy_name: str = Field(..., description="Strategy name")

    # Decision status
    status: str = Field(
        ...,
        description="Deployment status: APPROVED/CONDITIONAL/REJECTED",
    )
    confidence_level: str = Field(..., description="Decision confidence: high/medium/low")

    # Scoring components (0-100)
    feasibility_score: Decimal = Field(..., description="Feasibility score (0-100)")
    validation_score: Decimal = Field(..., description="Validation score (0-100)")
    recommendation_score: Decimal = Field(..., description="Recommendation score (0-100)")
    risk_score: Decimal = Field(..., description="Risk assessment score (0-100)")
    capacity_fade_score: Decimal | None = Field(
        default=None, description="T4.1 Capacity fade score (0-100, PHASE 6)"
    )
    overall_score: Decimal = Field(..., description="Overall decision score (0-100)")

    # Detailed rationale
    rationale: DeploymentRationale = Field(..., description="Decision rationale")

    # Summary metrics
    key_metrics: dict[str, Decimal] = Field(..., description="Key metrics for decision")

    # Recommendation for user
    recommendation_text: str = Field(..., description="Human-readable recommendation")

    # Next steps if conditional
    next_steps: list[str] = Field(default=[], description="Suggested next steps")

    decision_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Decision time"
    )

    error_message: str | None = Field(None, description="Error if any")


logger.debug(
    "DeployDecisionOrchestrator models loaded",
    extra={
        "component": "deploy_decision_orchestrator_models",
        "operation": "module_init",
        "models": [
            "DeploymentInput",
            "DeploymentRationale",
            "DeploymentDecision",
        ],
    },
)
