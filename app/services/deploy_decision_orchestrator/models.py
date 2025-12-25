"""
T10.1: DeployDecisionOrchestrator - Models for master deployment decision

Orchestrates final decision to deploy strategy or not based on:
- Feasibility ratio from backtesting
- Validation gate results
- Strategy recommendation score
- Portfolio metrics
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime


class DeploymentInput(BaseModel):
    """Complete input for deployment decision."""

    decision_id: str = Field(..., description="Unique decision identifier")
    profile_id: str = Field(..., description="Investment profile ID")
    input_id: str = Field(..., description="User input ID")
    strategy_name: str = Field(..., description="Strategy name")

    # From backtest results
    feasibility_ratio: Decimal = Field(
        ..., description="Feasibility ratio (actual/target return)"
    )
    annual_return_pct: Decimal = Field(..., description="Annual return %")
    max_drawdown_pct: Decimal = Field(..., description="Max drawdown %")
    sharpe_ratio: Decimal = Field(..., description="Sharpe ratio")
    win_rate_pct: Decimal = Field(..., description="Win rate %")

    # From validation engine
    validation_passed: bool = Field(..., description="Validation gates passed")
    validation_failures: List[str] = Field(
        default=[], description="Validation failure reasons"
    )
    validation_warnings: List[str] = Field(
        default=[], description="Validation warnings"
    )

    # From strategy recommender
    recommendation_score: Decimal = Field(
        ..., description="Recommendation score (0-100)"
    )
    recommendation_status: str = Field(
        ..., description="Status: STRONG_BUY/BUY/HOLD/REVIEW/NOT_RECOMMENDED"
    )
    recommendation_confidence: str = Field(
        ..., description="Confidence level: high/medium/low"
    )

    # From portfolio constructor
    num_modules: int = Field(..., description="Number of modules in portfolio")
    top_allocation_pct: Decimal = Field(
        ..., description="Largest allocation % (concentration)"
    )
    diversification_ratio: Decimal = Field(
        ..., description="Portfolio diversification ratio"
    )

    # User targets
    target_annual_return_pct: Decimal = Field(..., description="User target return %")
    max_acceptable_drawdown_pct: Decimal = Field(
        ..., description="User max acceptable drawdown %"
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
    diversification_assessment: str = Field(
        ..., description="Diversification assessment"
    )
    overall_assessment: str = Field(..., description="Overall decision rationale")

    critical_factors: List[str] = Field(
        ..., description="Critical factors influencing decision"
    )
    improvement_areas: List[str] = Field(
        ..., description="Areas for improvement if applicable"
    )
    conditions: List[str] = Field(
        default=[], description="Conditions for conditional approval"
    )


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
    confidence_level: str = Field(
        ..., description="Decision confidence: high/medium/low"
    )

    # Scoring components (0-100)
    feasibility_score: Decimal = Field(..., description="Feasibility score (0-100)")
    validation_score: Decimal = Field(..., description="Validation score (0-100)")
    recommendation_score: Decimal = Field(
        ..., description="Recommendation score (0-100)"
    )
    risk_score: Decimal = Field(..., description="Risk assessment score (0-100)")
    overall_score: Decimal = Field(..., description="Overall decision score (0-100)")

    # Detailed rationale
    rationale: DeploymentRationale = Field(..., description="Decision rationale")

    # Summary metrics
    key_metrics: Dict[str, Decimal] = Field(
        ..., description="Key metrics for decision"
    )

    # Recommendation for user
    recommendation_text: str = Field(
        ..., description="Human-readable recommendation"
    )

    # Next steps if conditional
    next_steps: List[str] = Field(
        default=[], description="Suggested next steps"
    )

    decision_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Decision time"
    )

    error_message: Optional[str] = Field(None, description="Error if any")
