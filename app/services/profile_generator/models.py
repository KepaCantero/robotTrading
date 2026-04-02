"""
T2.1: Investment Profile Models

Dataclasses for investment profiles and related structures.
Uses centralized configuration for default values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


# Helper functions to get defaults from centralized config
def _get_default_max_leverage() -> Decimal:
    return Decimal("1.0")  # No leverage by default


def _get_default_max_position_size() -> Decimal:
    return Decimal("5.0")  # 5% of portfolio


def _get_default_max_daily_loss() -> Decimal:
    from app.shared.config.centralized_config import get_config

    return Decimal(str(get_config().trading_thresholds.circuit_breaker_daily_loss))


def _get_default_max_concentration() -> Decimal:
    return Decimal("30.0")  # 30% in single asset


class CapitalTier(str, Enum):
    """Capital tier classification."""

    MICRO = "micro"  # < €25k
    SMALL = "small"  # €25k - €100k
    MEDIUM = "medium"  # €100k - €500k
    LARGE = "large"  # > €500k


class InvestmentObjective(str, Enum):
    """Investment objectives."""

    MAXIMIZAR_CAPITAL = "maximizar_capital"  # Capital maximization
    MAXIMIZAR_DIVIDENDOS = "maximizar_dividendos"  # Dividend maximization
    CAPITAL_PRESERVATION = "capital_preservation"  # Capital preservation
    BALANCED_GROWTH = "balanced_growth"  # Balanced growth
    INCOME_GENERATION = "income_generation"  # Income generation


class RiskProfile(str, Enum):
    """User risk tolerance."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class ModuleConfig:
    """Configuration for a single module."""

    name: str
    enabled: bool
    priority: int  # 0 = highest, 10 = lowest
    cost_estimate_usd: Decimal
    estimated_improvement_pct: Decimal  # Expected return improvement %


@dataclass
class InvestmentProfile:
    """Complete investment profile for a user."""

    # Required identifiers
    input_id: str
    capital_tier: CapitalTier
    initial_capital: Decimal
    min_monthly_return_eur: Decimal

    # Investment parameters
    objective: InvestmentObjective
    risk_profile: RiskProfile
    time_horizon_months: int  # 3, 12, 24, 36, 60+

    # Identifiers with defaults
    profile_id: str = field(
        default_factory=lambda: f"PROF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

    # Module configuration
    enabled_modules: list[ModuleConfig] = field(default_factory=list)

    # MAESTRO PHASE 1 Integration: Absolute Return Optimization
    required_annual_return_pct: Decimal | None = None  # From EUR target
    required_alpha_pct: Decimal | None = None  # After tax and commission
    capacity_fade_adjusted_alpha: Decimal | None = None  # Alpha at this capital scale
    position_size_pct: Decimal | None = None  # Optimized position size
    concurrent_positions: int | None = None  # Optimized concurrent positions
    feasibility_validation: dict | None = None  # AbsoluteReturnValidation results

    # Risk and leverage - use centralized config for defaults
    max_leverage: Decimal = field(default_factory=_get_default_max_leverage)
    max_position_size_pct: Decimal = field(
        default_factory=_get_default_max_position_size
    )  # % of portfolio
    max_daily_loss_pct: Decimal = field(default_factory=_get_default_max_daily_loss)  # Uses config
    max_portfolio_concentration_pct: Decimal = field(
        default_factory=_get_default_max_concentration
    )  # % in single asset

    # Dynamic adjustment
    rebalance_frequency_days: int = 30
    risk_scaling_enabled: bool = False
    adaptive_position_sizing: bool = True

    # Metadata
    created_timestamp: datetime = field(default_factory=datetime.utcnow)
    comments: str = ""

    def __post_init__(self):
        """Validate profile after initialization."""
        logger.debug(
            "Validating investment profile",
            extra={
                "input_id": self.input_id,
                "capital_tier": self.capital_tier.value,
                "initial_capital": str(self.initial_capital),
            },
        )
        if self.initial_capital <= Decimal("0"):
            logger.error(
                "Profile validation failed: invalid initial capital",
                extra={
                    "input_id": self.input_id,
                    "initial_capital": str(self.initial_capital),
                    "validation_error": "Initial capital must be positive",
                },
            )
            raise ValueError("Initial capital must be positive")
        if self.max_leverage < Decimal("1.0") or self.max_leverage > Decimal("3.0"):
            logger.error(
                "Profile validation failed: invalid leverage",
                extra={
                    "input_id": self.input_id,
                    "max_leverage": str(self.max_leverage),
                    "validation_error": "Leverage must be between 1.0 and 3.0",
                },
            )
            raise ValueError("Leverage must be between 1.0 and 3.0")
        if self.min_monthly_return_eur < Decimal("0"):
            logger.error(
                "Profile validation failed: invalid minimum return",
                extra={
                    "input_id": self.input_id,
                    "min_monthly_return_eur": str(self.min_monthly_return_eur),
                    "validation_error": "Minimum return must be non-negative",
                },
            )
            raise ValueError("Minimum return must be non-negative")
        logger.info(
            "Investment profile validated successfully",
            extra={
                "input_id": self.input_id,
                "profile_id": self.profile_id,
                "capital_tier": self.capital_tier.value,
                "objective": self.objective.value,
                "risk_profile": self.risk_profile.value,
            },
        )

    def to_dict(self) -> dict:
        """Convert profile to dictionary."""
        logger.debug(
            "Converting profile to dictionary",
            extra={
                "input_id": self.input_id,
                "profile_id": self.profile_id,
            },
        )
        return {
            "input_id": self.input_id,
            "profile_id": self.profile_id,
            "capital_tier": self.capital_tier.value,
            "initial_capital": str(self.initial_capital),
            "min_monthly_return_eur": str(self.min_monthly_return_eur),
            "objective": self.objective.value,
            "risk_profile": self.risk_profile.value,
            "time_horizon_months": self.time_horizon_months,
            "enabled_modules": [
                {
                    "name": m.name,
                    "enabled": m.enabled,
                    "priority": m.priority,
                    "cost_estimate_usd": str(m.cost_estimate_usd),
                    "estimated_improvement_pct": str(m.estimated_improvement_pct),
                }
                for m in self.enabled_modules
            ],
            # MAESTRO PHASE 1 fields
            "required_annual_return_pct": (
                str(self.required_annual_return_pct) if self.required_annual_return_pct else None
            ),
            "required_alpha_pct": str(self.required_alpha_pct) if self.required_alpha_pct else None,
            "capacity_fade_adjusted_alpha": (
                str(self.capacity_fade_adjusted_alpha)
                if self.capacity_fade_adjusted_alpha
                else None
            ),
            "position_size_pct": str(self.position_size_pct) if self.position_size_pct else None,
            "concurrent_positions": self.concurrent_positions,
            "feasibility_validation": self.feasibility_validation,
            # Risk parameters
            "max_leverage": str(self.max_leverage),
            "max_position_size_pct": str(self.max_position_size_pct),
            "max_daily_loss_pct": str(self.max_daily_loss_pct),
            "max_portfolio_concentration_pct": str(self.max_portfolio_concentration_pct),
            "rebalance_frequency_days": self.rebalance_frequency_days,
            "risk_scaling_enabled": self.risk_scaling_enabled,
            "adaptive_position_sizing": self.adaptive_position_sizing,
            "created_timestamp": self.created_timestamp.isoformat(),
            "comments": self.comments,
        }


@dataclass
class ProfileGenerationRequest:
    """Request to generate an investment profile."""

    input_id: str
    capital_initial: Decimal
    objective: InvestmentObjective
    risk_tolerance: RiskProfile
    target_monthly_return_eur: Decimal
    time_horizon_months: int = 12


@dataclass
class ProfileGenerationResult:
    """Result of profile generation."""

    success: bool
    profile: InvestmentProfile | None = None
    error_message: str = ""
    warnings: list[str] = field(default_factory=list)
    generation_time_ms: float = 0.0
