"""
T7.1: PortfolioConstructor Models

Data structures for portfolio construction and allocation.
"""

import logging
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PortfolioConstructionRequest(BaseModel):
    """Request for portfolio construction."""

    profile_id: str
    input_id: str
    capital_eur: Decimal
    risk_profile: str  # aggressive/balanced/conservative
    investment_objective: str  # maximizar_capital, balanced_growth, etc.
    enabled_modules: list[str]  # List of enabled trading modules
    target_annual_return_pct: Decimal
    max_acceptable_drawdown_pct: Decimal


class AllocationWeight(BaseModel):
    """Weight allocation for a single module."""

    module_name: str
    weight_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    capital_allocation_eur: Decimal
    rationale: str  # Why this module got this weight


class PortfolioAllocation(BaseModel):
    """Portfolio allocation across modules."""

    success: bool = True
    profile_id: str
    total_capital_eur: Decimal
    allocations: list[AllocationWeight]
    allocation_method: str  # "equal_weight", "efficient_frontier", "risk_parity"
    expected_portfolio_return_pct: Decimal
    expected_portfolio_sharpe: Decimal
    expected_portfolio_drawdown_pct: Decimal
    diversification_ratio: Decimal
    optimization_notes: str = ""
    error_message: Optional[str] = None


class RiskScalingRequest(BaseModel):
    """Request for conditional risk scaling application."""

    profile_id: str
    input_id: str
    base_portfolio: PortfolioAllocation
    portfolio_allocation: PortfolioAllocation
    market_regime: str  # bull/sideways/bear
    volatility_level: str  # low/normal/high
    drawdown_current_pct: Decimal
    max_acceptable_drawdown_pct: Decimal
    phase3_enabled: bool = False  # Whether PHASE 3 risk scaling is available


class RiskAdjustedPortfolio(BaseModel):
    """Portfolio after conditional risk scaling application."""

    success: bool = True
    profile_id: str
    base_allocation: PortfolioAllocation
    adjusted_allocation: Optional[PortfolioAllocation] = None
    risk_scaling_applied: bool = False
    scaling_factor: Decimal = Decimal("1.0")
    market_regime: str
    volatility_level: str
    adjustment_rationale: str = ""
    error_message: Optional[str] = None


logger.debug(
    "PortfolioConstructor models loaded",
    extra={
        "component": "portfolio_constructor_models",
        "operation": "module_init",
        "models": [
            "PortfolioConstructionRequest",
            "AllocationWeight",
            "PortfolioAllocation",
            "RiskScalingRequest",
            "RiskAdjustedPortfolio",
        ],
    },
)
