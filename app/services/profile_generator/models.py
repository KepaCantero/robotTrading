"""
T2.1: Investment Profile Models

Dataclasses for investment profiles and related structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


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
    enabled_modules: List[ModuleConfig] = field(default_factory=list)

    # MAESTRO PHASE 1 Integration: Absolute Return Optimization
    required_annual_return_pct: Optional[Decimal] = None  # From EUR target
    required_alpha_pct: Optional[Decimal] = None  # After tax and commission
    capacity_fade_adjusted_alpha: Optional[Decimal] = None  # Alpha at this capital scale
    position_size_pct: Optional[Decimal] = None  # Optimized position size
    concurrent_positions: Optional[int] = None  # Optimized concurrent positions
    feasibility_validation: Optional[Dict] = None  # AbsoluteReturnValidation results

    # Risk and leverage
    max_leverage: Decimal = field(default=Decimal("1.0"))
    max_position_size_pct: Decimal = field(default=Decimal("5.0"))  # % of portfolio
    max_daily_loss_pct: Decimal = field(default=Decimal("1.0"))
    max_portfolio_concentration_pct: Decimal = field(default=Decimal("30.0"))  # % in single asset

    # Dynamic adjustment
    rebalance_frequency_days: int = 30
    risk_scaling_enabled: bool = False
    adaptive_position_sizing: bool = True

    # Metadata
    created_timestamp: datetime = field(default_factory=datetime.utcnow)
    comments: str = ""

    def __post_init__(self):
        """Validate profile after initialization."""
        if self.initial_capital <= Decimal("0"):
            raise ValueError("Initial capital must be positive")
        if self.max_leverage < Decimal("1.0") or self.max_leverage > Decimal("3.0"):
            raise ValueError("Leverage must be between 1.0 and 3.0")
        if self.min_monthly_return_eur < Decimal("0"):
            raise ValueError("Minimum return must be non-negative")

    def to_dict(self) -> Dict:
        """Convert profile to dictionary."""
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
    profile: Optional[InvestmentProfile] = None
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    generation_time_ms: float = 0.0
