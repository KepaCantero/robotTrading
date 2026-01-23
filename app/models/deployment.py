"""
Deployment Models - For PHASE 4 End-to-End Pipeline Integration

Models for the complete deployment decision pipeline:
T4.1 (Capacity Fade) → T8.1 (Risk Scaling) → T9.1 (Reporting) → T10.1 (DeployDecisionOrchestrator)

TODO: Complete implementation in PHASE 4
"""

from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field


class DeploymentInput(BaseModel):
    """Input for deployment decision pipeline."""

    decision_id: str = Field(..., description="Unique decision identifier")
    profile_id: str = Field(..., description="Investment profile ID")
    input_id: str = Field(..., description="User input ID")
    strategy_name: str = Field(..., description="Name of the strategy to deploy")
    annual_return_pct: Decimal = Field(..., ge=0, description="Expected annual return %")
    max_drawdown_pct: Decimal = Field(..., ge=0, le=100, description="Maximum drawdown %")
    sharpe_ratio: Decimal = Field(..., description="Sharpe ratio of strategy")
    win_rate_pct: Decimal = Field(..., ge=0, le=100, description="Win rate %")
    feasibility_ratio: Decimal = Field(
        ..., ge=0, description="Feasibility ratio (alpha sustainability)"
    )
    validation_passed: bool = Field(..., description="Whether validation passed")
    validation_failures: List[str] = Field(
        default_factory=list, description="List of validation failures"
    )
    recommendation_score: Decimal = Field(
        ..., ge=0, le=100, description="Recommendation score 0-100"
    )
    recommendation_status: str = Field(
        ..., description="Recommendation status (strong_buy, buy, hold, etc.)"
    )
    current_capital: Decimal = Field(..., gt=0, description="Current capital in EUR")
    target_capital: Decimal = Field(..., gt=0, description="Target capital in EUR")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "decision_id": "dec_001",
                "profile_id": "prof_001",
                "input_id": "input_001",
                "strategy_name": "Momentum Strategy",
                "annual_return_pct": Decimal("15.0"),
                "max_drawdown_pct": Decimal("20.0"),
                "sharpe_ratio": Decimal("1.8"),
                "win_rate_pct": Decimal("58.0"),
                "feasibility_ratio": Decimal("1.1"),
                "validation_passed": True,
                "validation_failures": [],
                "recommendation_score": Decimal("75"),
                "recommendation_status": "strong_buy",
                "current_capital": Decimal("100000"),
                "target_capital": Decimal("250000"),
            }
        }


class DeploymentDecision(BaseModel):
    """Output deployment decision."""

    decision_id: str = Field(..., description="Decision identifier")
    status: str = Field(..., description="Decision status: APPROVED, REJECTED, CONDITIONAL")
    reason: str = Field(..., description="Reason for decision")
    recommendation: str = Field(..., description="Deployment recommendation")
    timestamp: str = Field(..., description="Decision timestamp")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "decision_id": "dec_001",
                "status": "APPROVED",
                "reason": "Strategy meets all deployment criteria",
                "recommendation": "Deploy immediately with standard parameters",
                "timestamp": "2025-12-27T14:30:00Z",
            }
        }
