"""
T3.1: Module Parametrizer Models

Dataclasses for module-level parameter generation and configuration.
Uses centralized configuration for default values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# Helper functions to get defaults from centralized config
def _get_default_max_position_size() -> Decimal:
    from app.shared.config.centralized_config import get_config

    return Decimal(str(get_config().trading_thresholds.max_position_size))


def _get_default_stop_loss() -> Decimal:
    from app.shared.config.centralized_config import get_config

    return Decimal(str(get_config().trading_thresholds.stop_loss_pct))


def _get_default_take_profit() -> Decimal:
    from app.shared.config.centralized_config import get_config

    return Decimal(str(get_config().trading_thresholds.take_profit_pct))


class ParameterizationPreset(str, Enum):
    """Risk-based preset for module parameters."""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class ModuleParameterConfig:
    """Configuration parameters for a single trading module - uses centralized config for defaults."""

    # Module identification
    module_name: str
    enabled: bool = True
    priority: int = 0  # 0 = highest, 10 = lowest

    # Common risk parameters (shared across most modules) - use centralized config
    max_position_size: Decimal = field(
        default_factory=_get_default_max_position_size
    )  # Uses config
    stop_loss_pct: Decimal = field(default_factory=_get_default_stop_loss)  # Uses config
    take_profit_pct: Decimal = field(default_factory=_get_default_take_profit)  # Uses config
    max_exposure: Decimal = field(default=Decimal("0.25"))  # % of capital
    max_positions: int = 5
    risk_adjustment: Decimal = field(default=Decimal("1.0"))  # 0.5 = half risk, 1.5 = 1.5x risk

    # Module-specific parameters (vary by module type)
    module_specific: dict[str, Any] = field(default_factory=dict)

    # Metadata
    preset: ParameterizationPreset = ParameterizationPreset.BALANCED
    description: str = ""
    cost_estimate_usd: Decimal = field(default=Decimal("50"))  # Estimated cost in USD
    estimated_improvement_pct: Decimal = field(default=Decimal("1.5"))  # Expected improvement %


@dataclass
class ModuleParameterSet:
    """Collection of parameters for all enabled modules in a profile."""

    # Reference identifiers
    profile_id: str
    input_id: str

    # Module parameters indexed by module name
    module_parameters: dict[str, ModuleParameterConfig] = field(default_factory=dict)

    # Summary metrics
    total_modules_enabled: int = 0
    high_priority_modules: list[str] = field(default_factory=list)  # Modules with priority 0-2
    medium_priority_modules: list[str] = field(default_factory=list)  # Modules with priority 3-6
    low_priority_modules: list[str] = field(default_factory=list)  # Modules with priority 7-10

    # Capital-tier-specific metadata
    capital_tier: str = ""  # micro, small, medium, large
    objective: str = ""  # Investment objective
    risk_profile: str = ""  # conservative, moderate, aggressive

    # Validation metadata
    total_max_exposure: Decimal = field(
        default=Decimal("0.0")
    )  # Sum of max_exposure across modules
    total_estimated_cost_usd: Decimal = field(default=Decimal("0.0"))  # Sum of module costs
    total_estimated_improvement_pct: Decimal = field(default=Decimal("0.0"))  # Average improvement

    def to_dict(self) -> dict:
        """Convert parameter set to dictionary."""
        return {
            "profile_id": self.profile_id,
            "input_id": self.input_id,
            "module_parameters": {
                name: {
                    "module_name": config.module_name,
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "max_position_size": str(config.max_position_size),
                    "stop_loss_pct": str(config.stop_loss_pct),
                    "take_profit_pct": str(config.take_profit_pct),
                    "max_exposure": str(config.max_exposure),
                    "max_positions": config.max_positions,
                    "risk_adjustment": str(config.risk_adjustment),
                    "module_specific": config.module_specific,
                    "preset": config.preset.value,
                }
                for name, config in self.module_parameters.items()
            },
            "total_modules_enabled": self.total_modules_enabled,
            "capital_tier": self.capital_tier,
            "objective": self.objective,
            "risk_profile": self.risk_profile,
            "total_max_exposure": str(self.total_max_exposure),
            "total_estimated_cost_usd": str(self.total_estimated_cost_usd),
            "total_estimated_improvement_pct": str(self.total_estimated_improvement_pct),
        }


@dataclass
class ParameterizationRequest:
    """Request to parametrize modules based on investment profile."""

    profile_id: str
    input_id: str
    capital_tier: str  # micro, small, medium, large
    objective: str  # Investment objective
    risk_profile: str  # conservative, moderate, aggressive
    enabled_modules: list[str]  # List of module names to parametrize
    initial_capital: Decimal  # For capital-tier validation


@dataclass
class ParameterizationResult:
    """Result of module parametrization."""

    success: bool
    parameter_set: ModuleParameterSet | None = None
    error_message: str = ""
    warnings: list[str] = field(default_factory=list)
    disabled_modules: list[str] = field(
        default_factory=list
    )  # Modules disabled due to capital tier
    parametrization_time_ms: float = 0.0


logger.debug(
    "ModuleParametrizer models loaded",
    extra={
        "component": "module_parametrizer_models",
        "operation": "module_init",
        "models": [
            "ParameterizationPreset",
            "ModuleParameterConfig",
            "ModuleParameterSet",
            "ParameterizationRequest",
            "ParameterizationResult",
        ],
    },
)
