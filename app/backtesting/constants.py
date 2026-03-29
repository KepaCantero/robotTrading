"""
Backtesting Constants Configuration

DEPRECATED: This file is now a thin wrapper around CentralizedConfig.
All values are now managed in app/shared/config/centralized_config.py::BacktestingConfig.

This file remains for backwards compatibility only.
New code should use:
    from app.shared.config.centralized_config import get_config
    config = get_config()
    slippage = config.backtesting.base_slippage_bps

Migration Guide:
    OLD: from app.backtesting.constants import BACKTESTING_CONSTANTS
    NEW: from app.shared.config.centralized_config import get_config
         backtesting_config = get_config().backtesting
"""

import warnings
from decimal import Decimal

# Import from centralized config
from app.shared.config.centralized_config import BacktestingConfig, get_config

# =============================================================================
# DEPRECATION WARNING
# =============================================================================

warnings.warn(
    "app.backtesting.constants is deprecated. "
    "Use app.shared.config.centralized_config.get_config().backtesting instead.",
    DeprecationWarning,
    stacklevel=2,
)


# =============================================================================
# BACKWARDS COMPATIBILITY LAYER
# =============================================================================


def _get_backtesting_config() -> BacktestingConfig:
    """Get backtesting config from centralized config."""
    return get_config().backtesting


# TypedDict definitions kept for backwards compatibility
from typing import TypedDict, Union


class FixedCommissionModel(TypedDict):
    """Fixed commission model."""

    type: str
    cost: Decimal
    description: str


class HybridCommissionModel(TypedDict):
    """Hybrid commission model."""

    type: str
    min_cost: Decimal
    rate: Decimal
    description: str


class TierBracket(TypedDict):
    """Single tier bracket for tiered commission."""

    volume_max: Union[int, float]
    rate: Decimal
    min: Decimal


class TieredCommissionModel(TypedDict):
    """Tiered commission model."""

    type: str
    brackets: list[TierBracket]
    description: str


CommissionModel = Union[FixedCommissionModel, HybridCommissionModel, TieredCommissionModel]


# =============================================================================
# COMPATIBILITY CLASSES - delegate to CentralizedConfig
# =============================================================================


class CapitalScaleConstants:
    """
    DEPRECATED: Use get_config().backtesting instead.

    This class provides backwards compatibility by delegating to CentralizedConfig.
    """

    @property
    def default_capital_levels(self) -> list[Decimal]:
        return _get_backtesting_config().default_capital_levels

    @property
    def adv_limit_pct_default(self) -> Decimal:
        return _get_backtesting_config().adv_limit_pct

    @property
    def adv_fill_ratio_reject_threshold(self) -> Decimal:
        return _get_backtesting_config().adv_fill_ratio_reject_threshold

    @property
    def commission_impact_warning_threshold(self) -> Decimal:
        return _get_backtesting_config().commission_impact_warning_threshold

    @property
    def commission_impact_critical_threshold(self) -> Decimal:
        return _get_backtesting_config().commission_impact_critical_threshold

    @property
    def commission_impact_optimal_threshold(self) -> Decimal:
        return _get_backtesting_config().commission_impact_warning_threshold

    @property
    def alpha_degradation_threshold(self) -> Decimal:
        return _get_backtesting_config().alpha_degradation_threshold

    @property
    def commission_models(self) -> dict[Decimal, CommissionModel]:
        """Build commission models from centralized config."""
        config = _get_backtesting_config()
        return {
            Decimal("1000"): {
                "type": "fixed",
                "cost": config.default_commission_fixed,
                "description": "Micro account - high fixed fees",
            },
            Decimal("5000"): {
                "type": "fixed",
                "cost": Decimal("3.0"),
                "description": "Small account - reduced fixed fees",
            },
            Decimal("10000"): {
                "type": "hybrid",
                "min_cost": config.min_commission,
                "rate": config.default_commission_rate,
                "description": "Medium account - hybrid structure",
            },
            Decimal("50000"): {
                "type": "tiered",
                "brackets": [
                    {
                        "volume_max": 50000,
                        "rate": config.default_commission_rate,
                        "min": Decimal("0.50"),
                    },
                    {
                        "volume_max": 500000,
                        "rate": config.default_commission_rate / 5,
                        "min": Decimal("0.10"),
                    },
                    {
                        "volume_max": float("inf"),
                        "rate": config.default_commission_rate / 100,
                        "min": Decimal("0.01"),
                    },
                ],
                "description": "Pro account - tiered pricing",
            },
            Decimal("100000"): {
                "type": "tiered",
                "brackets": [
                    {
                        "volume_max": 100000,
                        "rate": config.default_commission_rate / 2,
                        "min": Decimal("0.50"),
                    },
                    {
                        "volume_max": 500000,
                        "rate": config.default_commission_rate / 20,
                        "min": Decimal("0.05"),
                    },
                    {
                        "volume_max": float("inf"),
                        "rate": config.default_commission_rate / 500,
                        "min": Decimal("0.01"),
                    },
                ],
                "description": "Fund account - institutional pricing",
            },
        }

    @property
    def scalability_alpha_degradation_max_points(self) -> Decimal:
        return _get_backtesting_config().scalability_alpha_max_points

    @property
    def scalability_commission_max_points(self) -> Decimal:
        return _get_backtesting_config().scalability_commission_max_points

    @property
    def scalability_stability_max_points(self) -> Decimal:
        return _get_backtesting_config().scalability_stability_max_points

    @property
    def commission_impact_excellent_threshold(self) -> Decimal:
        return Decimal("0.10")

    @property
    def commission_impact_good_threshold(self) -> Decimal:
        return _get_backtesting_config().commission_impact_warning_threshold

    @property
    def commission_impact_poor_threshold(self) -> Decimal:
        return _get_backtesting_config().commission_impact_warning_threshold

    @property
    def win_rate_stability_penalty_factor(self) -> Decimal:
        return Decimal("100")


class ExecutionEngineConstants:
    """
    DEPRECATED: Use get_config().backtesting instead.

    This class provides backwards compatibility by delegating to CentralizedConfig.
    """

    @property
    def base_slippage_bps(self) -> Decimal:
        return _get_backtesting_config().base_slippage_bps

    @property
    def optimistic_slippage_bps(self) -> Decimal:
        return _get_backtesting_config().optimistic_slippage_bps

    @property
    def stop_slippage_multiplier(self) -> Decimal:
        return _get_backtesting_config().stop_slippage_multiplier

    @property
    def volatility_multiplier(self) -> Decimal:
        return _get_backtesting_config().volatility_multiplier

    @property
    def enable_next_day_execution(self) -> bool:
        return _get_backtesting_config().enable_next_day_execution


class BacktestingConstants:
    """
    DEPRECATED: Use get_config().backtesting instead.

    Main container for all backtesting constants.

    Usage (OLD - deprecated):
        from app.backtesting.constants import BACKTESTING_CONSTANTS
        capital_levels = BACKTESTING_CONSTANTS.capital_scale.DEFAULT_CAPITAL_LEVELS
        base_slippage = BACKTESTING_CONSTANTS.execution.base_slippage_bps

    Usage (NEW - recommended):
        from app.shared.config.centralized_config import get_config
        config = get_config()
        capital_levels = config.backtesting.default_capital_levels
        base_slippage = config.backtesting.base_slippage_bps
    """

    @property
    def capital_scale(self) -> CapitalScaleConstants:
        return CapitalScaleConstants()

    @property
    def execution(self) -> ExecutionEngineConstants:
        return ExecutionEngineConstants()


# Singleton instance for easy import (backwards compatibility)
BACKTESTING_CONSTANTS = BacktestingConstants()


# Convenience functions for backward compatibility
def get_default_capital_levels() -> list[Decimal]:
    """Get default capital levels for scale analysis."""
    return _get_backtesting_config().default_capital_levels.copy()


def get_commission_models() -> dict[Decimal, CommissionModel]:
    """Get commission models by capital level."""
    return CapitalScaleConstants().commission_models.copy()


def get_base_slippage_bps() -> Decimal:
    """Get base slippage in basis points."""
    return _get_backtesting_config().base_slippage_bps


def get_adv_limit_pct() -> Decimal:
    """Get default ADV limit as percentage."""
    return _get_backtesting_config().adv_limit_pct
