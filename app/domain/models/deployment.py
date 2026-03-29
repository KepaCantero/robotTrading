"""
Deployment Models - For PHASE 4 End-to-End Pipeline Integration

Models for the complete deployment decision pipeline:
T4.1 (Capacity Fade) → T8.1 (Risk Scaling) → T9.1 (Reporting) → T10.1 (DeployDecisionOrchestrator)

TODO: Complete implementation in PHASE 4
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class DeploymentInput(BaseModel):
    """Complete input for deployment decision pipeline."""

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
    validation_failures: list[str] = Field(
        default_factory=list, description="Validation failure reasons"
    )
    validation_warnings: list[str] = Field(default_factory=list, description="Validation warnings")

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
    capacity_fade_feasible: Optional[bool] = Field(
        default=None, description="T4.1 capacity fade feasibility"
    )
    estimated_alpha_at_scale: Optional[Decimal] = Field(
        default=None, description="T4.1 estimated alpha at target capital"
    )
    capacity_fade_assessment: Optional[str] = Field(
        default=None, description="T4.1 capacity fade assessment details"
    )
    current_capital: Optional[Decimal] = Field(
        default=None, description="Current capital (for capacity fade analysis)"
    )
    target_capital: Optional[Decimal] = Field(
        default=None, description="Target capital (for capacity fade analysis)"
    )

    execution_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Decision timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "decision_id": "dec_001",
                "profile_id": "prof_001",
                "input_id": "input_001",
                "strategy_name": "Momentum Strategy",
                "feasibility_ratio": "1.1",
                "annual_return_pct": "15.0",
                "max_drawdown_pct": "20.0",
                "sharpe_ratio": "1.8",
                "win_rate_pct": "58.0",
                "validation_passed": True,
                "validation_failures": [],
                "validation_warnings": [],
                "recommendation_score": "75",
                "recommendation_status": "STRONG_BUY",
                "recommendation_confidence": "high",
                "num_modules": 5,
                "top_allocation_pct": "25.0",
                "diversification_ratio": "0.85",
                "target_annual_return_pct": "20.0",
                "max_acceptable_drawdown_pct": "25.0",
                "capacity_fade_feasible": True,
                "estimated_alpha_at_scale": "18.5",
                "capacity_fade_assessment": "Alpha sustainable at scale",
                "current_capital": "100000",
                "target_capital": "250000",
            }
        }
    }


class DeploymentDecision(BaseModel):
    """Output deployment decision."""

    decision_id: str = Field(..., description="Decision identifier")
    status: str = Field(..., description="Decision status: APPROVED, REJECTED, CONDITIONAL")
    reason: str = Field(..., description="Reason for decision")
    recommendation: str = Field(..., description="Deployment recommendation")
    timestamp: str = Field(..., description="Decision timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "decision_id": "dec_001",
                "status": "APPROVED",
                "reason": "Strategy meets all deployment criteria",
                "recommendation": "Deploy immediately with standard parameters",
                "timestamp": "2025-12-27T14:30:00Z",
            }
        }
    }
