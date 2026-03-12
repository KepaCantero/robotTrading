from decimal import Decimal
from typing import List, Optional

import logging
from pydantic import BaseModel, Field

from app.services.portfolio_constructor import AllocationWeight, PortfolioAllocation

logger = logging.getLogger(__name__)

"""
T8.1: RiskScalingApplication Models

Data structures for conditional risk scaling application.
"""


class RiskScalingRequest(BaseModel):
    """Request for conditional risk scaling application."""

    profile_id: str
    input_id: str
    base_portfolio: "PortfolioAllocation"  # From T7.1
    market_regime: str  # bull/sideways/bear
    volatility_level: str  # low/normal/high
    current_drawdown_pct: Decimal = Field(ge=Decimal("0"))
    max_acceptable_drawdown_pct: Decimal = Field(gt=Decimal("0"))
    phase3_enabled: bool = False  # Whether PHASE 3 risk scaling is available


class AdjustedAllocationWeight(BaseModel):
    """Adjusted weight allocation after risk scaling."""

    module_name: str
    original_weight_pct: Decimal
    adjusted_weight_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    adjustment_factor: Decimal
    rationale: str


class RiskAdjustedPortfolio(BaseModel):
    """Portfolio after conditional risk scaling application."""

    success: bool = True
    profile_id: str
    base_allocation_method: str  # From base portfolio
    risk_scaling_applied: bool = False
    scaling_factor: Decimal = Decimal("1.0")
    market_regime: str
    volatility_level: str
    current_drawdown_pct: Decimal
    max_acceptable_drawdown_pct: Decimal

    # Original allocations
    original_allocations: List["AllocationWeight"] = Field(default_factory=list)

    # Adjusted allocations (if scaling applied)
    adjusted_allocations: Optional[List[AdjustedAllocationWeight]] = None

    adjustment_rationale: str = ""
    expected_return_adjustment_pct: Decimal = Decimal("0")  # Impact on expected return
    error_message: Optional[str] = None


# Import from T7.1 models for type hints

# Update forward references
RiskScalingRequest.model_rebuild()
RiskAdjustedPortfolio.model_rebuild()


logger.debug(
    "RiskScalingApplication models loaded",
    extra={
        "component": "risk_scaling_application_models",
        "operation": "module_init",
        "models": [
            "RiskScalingRequest",
            "AdjustedAllocationWeight",
            "RiskAdjustedPortfolio",
        ],
    }
)
