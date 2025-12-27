"""
T4.1 Capacity Fade Validation Models

Data structures for capacity fade analysis and validation.
Used to validate that strategy alpha remains sustainable as capital scales.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FeasibilityDecision(Enum):
    """Feasibility gate decision."""

    APPROVED = "approved"  # Alpha sufficient at target capital
    CONDITIONAL = "conditional"  # Alpha marginal, needs monitoring
    REJECTED = "rejected"  # Alpha insufficient at target capital


class LiquidityReport(BaseModel):
    """Liquidity headroom analysis."""

    position_size_usd: Decimal = Field(gt=Decimal("0"))
    daily_volume_usd: Decimal = Field(gt=Decimal("0"))
    percent_of_volume: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    headroom_available: bool  # True if headroom > 5%
    recommended_max_position: Decimal  # Max position given daily volume
    rationale: str


class CapacityFadeAnalysis(BaseModel):
    """Capacity fade analysis results."""

    base_alpha_pct: Decimal = Field(ge=Decimal("0"))  # Strategy alpha at current capital
    current_capital_usd: Decimal = Field(gt=Decimal("0"))
    target_capital_usd: Decimal = Field(gt=Decimal("0"))

    # Fade analysis
    capacity_fade_ratio: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))  # How much alpha decays
    estimated_alpha_at_target: Decimal = Field(ge=Decimal("0"))  # Projected alpha at target capital
    fade_model: str = "sqrt(capacity)"  # Model used (e.g., sqrt, linear, empirical)

    # Required alpha for profitability
    required_alpha_pct: Decimal = Field(ge=Decimal("0"))  # Minimum alpha needed
    alpha_sufficient: bool  # True if estimated_alpha >= required_alpha

    # Liquidity constraints
    liquidity_report: Optional[LiquidityReport] = None
    liquidity_constrained: bool = False

    # Fade factors
    factors: dict = Field(
        default_factory=dict
    )  # {"model_decay": 0.15, "liquidity_penalty": 0.05, ...}

    # Timestamps
    analysis_timestamp: datetime = Field(default_factory=datetime.now)


class FeasibilityGate(BaseModel):
    """Final feasibility decision gate."""

    decision: FeasibilityDecision
    approved: bool  # True if APPROVED or CONDITIONAL
    hard_gate: bool  # True if hard rejection (REJECTED)

    # Analysis that led to decision
    analysis: CapacityFadeAnalysis
    validation_message: str

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)

    # Timestamp
    created_at: datetime = Field(default_factory=datetime.now)


class CapacityFadeRequest(BaseModel):
    """Request for capacity fade validation."""

    profile_id: str
    input_id: str

    # Backtest results
    base_alpha_pct: Decimal = Field(
        ge=Decimal("0"), le=Decimal("100")
    )  # Achieved return % in backtest
    backtest_capital_usd: Decimal = Field(gt=Decimal("0"))  # Capital used in backtest
    backtest_duration_years: Decimal = Field(gt=Decimal("0"))

    # Current state
    current_capital_usd: Decimal = Field(gt=Decimal("0"))

    # Target deployment
    target_capital_usd: Decimal = Field(gt=Decimal("0"))
    target_monthly_return_usd: Optional[Decimal] = None  # e.g., €800/month

    # Average position size (for liquidity calculation)
    avg_position_size_usd: Decimal = Field(gt=Decimal("0"))

    # Market data (for liquidity headroom)
    avg_daily_volume_multiplier: Decimal = Field(
        gt=Decimal("0"), default=Decimal("1.0")
    )  # 1.0 = 1x avg volume

    # Fade model configuration
    fade_model: str = "sqrt"  # "sqrt", "linear", or "empirical"
    confidence_level: str = "conservative"  # "conservative", "moderate", "aggressive"


class CapacityFadeResponse(BaseModel):
    """Response from capacity fade validation."""

    success: bool
    feasibility_gate: FeasibilityGate
    analysis: CapacityFadeAnalysis

    # Summary for decision makers
    summary: str
    details: dict = Field(default_factory=dict)

    error_message: Optional[str] = None
