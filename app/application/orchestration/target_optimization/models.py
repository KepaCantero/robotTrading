"""
PHASE 1: Capital-Tier Aware Strategy Orchestration - Data Models

Defines:
- CapitalTier enum and tier thresholds
- StrategyConfig with tier-specific parameters
- RiskProfile with capital-aware settings
- AbsoluteReturnTarget with feasibility validation
"""

from __future__ import annotations

import logging
from decimal import Decimal
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CapitalTier(str, Enum):
    """Capital tier classification."""

    MICRO = "micro"  # < €15k
    SMALL = "small"  # €15k - €50k
    MEDIUM = "medium"  # €50k - €250k
    LARGE = "large"  # €250k+


class CapitalTierThresholds(BaseModel):
    """Capital threshold definitions."""

    MICRO_MAX: ClassVar[Decimal] = Decimal("15000")
    SMALL_MIN: ClassVar[Decimal] = Decimal("15000")
    SMALL_MAX: ClassVar[Decimal] = Decimal("50000")
    MEDIUM_MIN: ClassVar[Decimal] = Decimal("50000")
    MEDIUM_MAX: ClassVar[Decimal] = Decimal("250000")
    LARGE_MIN: ClassVar[Decimal] = Decimal("250000")


class RiskProfile(BaseModel):
    """Risk profile for given capital tier."""

    risk_level: int = Field(..., ge=1, le=7, description="Risk level 1-7")
    max_position_size: Decimal = Field(
        ..., ge=Decimal("0.01"), le=Decimal("1.0"), description="Max position as % of capital"
    )
    max_drawdown_acceptable: Decimal = Field(
        ..., ge=Decimal("0.01"), le=Decimal("0.50"), description="Max acceptable drawdown"
    )
    leverage_allowed: Decimal = Field(
        ..., ge=Decimal("0"), le=Decimal("3.0"), description="Max leverage multiplier"
    )
    max_daily_loss: Decimal = Field(..., ge=Decimal("0"), description="Max daily loss in EUR")
    diversification_min: int = Field(..., ge=1, le=50, description="Minimum concurrent positions")
    pain_tolerance: str = Field(..., description="VERY_LOW / LOW / MEDIUM / HIGH / VERY_HIGH")


class StrategyFeatures(BaseModel):
    """Strategy features that can be enabled/disabled."""

    momentum: bool = True
    mean_reversion: bool = False
    machine_learning: bool = False
    deep_learning: bool = False
    ensemble: bool = False
    synthetic_data: bool = False
    regime_detection: bool = False
    volatility_targeting: bool = False
    currency_hedging: bool = False

    class Config:
        json_schema_extra: ClassVar[dict] = {
            "example": {
                "momentum": True,
                "mean_reversion": True,
                "machine_learning": True,
                "deep_learning": False,
                "ensemble": True,
                "synthetic_data": False,
                "regime_detection": True,
                "volatility_targeting": True,
                "currency_hedging": False,
            }
        }

    def enabled_modules(self) -> list[str]:
        """Return list of enabled module names."""
        modules = [k for k, v in self.dict().items() if v]
        logger.debug(
            "Getting enabled strategy modules",
            extra={"enabled_modules": modules, "total_count": len(modules)},
        )
        return modules


class CapitalTierConfig(BaseModel):
    """Complete configuration for a capital tier."""

    tier: CapitalTier = Field(..., description="Capital tier")
    capital_range: tuple = Field(..., description="(min, max) capital in EUR")
    risk_profile: RiskProfile = Field(..., description="Risk settings for tier")
    enabled_features: StrategyFeatures = Field(..., description="Enabled strategy features")
    strategy_type: str = Field(..., description="CONSERVATIVE / BALANCED / AGGRESSIVE")
    expected_alpha_range: tuple = Field(..., description="(min, max) expected annual return %")


class AbsoluteReturnTarget(BaseModel):
    """Target return specification for validation."""

    target_euros_monthly: Decimal = Field(..., gt=0, description="Target return in EUR per month")
    capital: Decimal = Field(..., gt=0, description="Available capital in EUR")
    time_horizon_months: int = Field(..., ge=1, le=240, description="Time horizon in months")
    risk_free_rate: Decimal = Field(
        default=Decimal("0.04"), ge=0, le=1, description="Risk-free rate annually"
    )
    tax_rate: Decimal = Field(default=Decimal("0.19"), ge=0, le=1, description="Tax rate")
    commission_per_trade: Decimal = Field(
        default=Decimal("10"), ge=0, description="Commission per trade in EUR"
    )
    expected_trades_per_month: int = Field(
        default=10, ge=0, le=1000, description="Expected trades per month"
    )

    class Config:
        json_schema_extra: ClassVar[dict] = {
            "example": {
                "target_euros_monthly": Decimal("800"),
                "capital": Decimal("250000"),
                "time_horizon_months": 24,
                "risk_free_rate": Decimal("0.04"),
                "tax_rate": Decimal("0.19"),
                "commission_per_trade": Decimal("10"),
                "expected_trades_per_month": 10,
            }
        }

    def target_annual_return_pct(self) -> Decimal:
        """Calculate required annual return as percentage."""
        annual_target = self.target_euros_monthly * 12
        result = (annual_target / self.capital * 100).quantize(Decimal("0.01"))
        logger.debug(
            "Calculated target annual return percentage",
            extra={
                "target_monthly_euros": float(self.target_euros_monthly),
                "annual_target_euros": float(annual_target),
                "capital": float(self.capital),
                "annual_return_pct": float(result),
            },
        )
        return result

    def required_alpha_monthly(self) -> Decimal:
        """Calculate required monthly alpha after tax and commission."""
        monthly_total_cost = (self.commission_per_trade * self.expected_trades_per_month) + (
            self.target_euros_monthly * self.tax_rate
        )
        result = self.target_euros_monthly + monthly_total_cost
        logger.debug(
            "Calculated required monthly alpha",
            extra={
                "target_monthly_euros": float(self.target_euros_monthly),
                "monthly_total_cost": float(monthly_total_cost),
                "required_alpha_monthly": float(result),
            },
        )
        return result


class AbsoluteReturnValidation(BaseModel):
    """Validation result for absolute return target."""

    is_feasible: bool = Field(..., description="Is target feasible?")
    required_alpha_pct: Decimal = Field(..., description="Required alpha as % of capital annually")
    capacity_fade_adjusted_alpha: Decimal | None = Field(
        None, description="Alpha after capacity fade estimate"
    )
    recommendation: str = Field(..., description="Recommendation text")
    confidence_level: str = Field(..., description="HIGH / MEDIUM / LOW confidence in feasibility")
    monthly_costs: dict[str, Decimal] = Field(default={}, description="Breakdown of monthly costs")


class CapitalTierResult(BaseModel):
    """Result of capital tier analysis."""

    tier: CapitalTier = Field(..., description="Detected capital tier")
    capital: Decimal = Field(..., description="Capital amount")
    risk_profile: RiskProfile = Field(..., description="Assigned risk profile")
    enabled_features: StrategyFeatures = Field(..., description="Enabled strategy features")
    strategy_type: str = Field(..., description="Recommended strategy type")
    expected_annual_return_pct_range: tuple = Field(..., description="(min, max) expected return %")
    modules_enabled: list[str] = Field(..., description="List of enabled modules")
    leverage_multiplier: Decimal = Field(..., description="Leverage allowed")
    max_position_size_eur: Decimal = Field(..., description="Max position size in EUR")
