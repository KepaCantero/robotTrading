"""
Backtesting Constants Configuration

Centralized configuration for all hardcoded constants in backtesting modules.
This file replaces magic numbers scattered across capital_scale_analyzer.py,
execution_engine.py, and other backtesting modules.

All values are configurable and documented for easy maintenance.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict, Union


# ============================================================================
# TYPED DICT DEFINITIONS
# ============================================================================

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
    brackets: List[TierBracket]
    description: str


CommissionModel = Union[FixedCommissionModel, HybridCommissionModel, TieredCommissionModel]


@dataclass(frozen=True)
class CapitalScaleConstants:
    """Constants for capital scale analyzer."""

    # Default capital levels for multi-scale analysis
    DEFAULT_CAPITAL_LEVELS: List[Decimal] = field(
        default_factory=lambda: [
            Decimal("1000"),  # Micro
            Decimal("5000"),  # Small
            Decimal("10000"),  # Medium
            Decimal("50000"),  # Pro
            Decimal("100000"),  # Fund
        ]
    )

    # ADV (Average Daily Volume) limit settings
    ADV_LIMIT_PCT_DEFAULT: Decimal = Decimal("0.02")  # 2% ADV rule
    ADV_FILL_RATIO_REJECT_THRESHOLD: Decimal = Decimal("0.5")  # Reject if fill < 50%

    # Commission impact thresholds (as decimals, e.g., 0.15 = 15%)
    COMMISSION_IMPACT_WARNING_THRESHOLD: Decimal = Decimal("0.15")  # 15% - trigger warning
    COMMISSION_IMPACT_CRITICAL_THRESHOLD: Decimal = Decimal("0.20")  # 20% - reject strategy
    COMMISSION_IMPACT_OPTIMAL_THRESHOLD: Decimal = Decimal(
        "0.15"
    )  # 15% - for optimal capital selection

    # Alpha degradation threshold (as decimal, e.g., 0.50 = 50%)
    ALPHA_DEGRADATION_THRESHOLD: Decimal = Decimal("0.50")  # 50% degradation max acceptable

    # Commission models by capital level (€ per trade or %)
    # Each model has: type, cost/rate, description
    COMMISSION_MODELS: Dict[Decimal, CommissionModel] = field(
        default_factory=lambda: {
            Decimal("1000"): {
                "type": "fixed",
                "cost": Decimal("5.0"),  # €5 per trade (high impact on €1K)
                "description": "Micro account - high fixed fees",
            },
            Decimal("5000"): {
                "type": "fixed",
                "cost": Decimal("3.0"),  # €3 per trade
                "description": "Small account - reduced fixed fees",
            },
            Decimal("10000"): {
                "type": "hybrid",
                "min_cost": Decimal("1.0"),
                "rate": Decimal("0.001"),  # 0.1% with €1 minimum
                "description": "Medium account - hybrid structure",
            },
            Decimal("50000"): {
                "type": "tiered",
                "brackets": [
                    {"volume_max": 50000, "rate": Decimal("0.001"), "min": Decimal("0.50")},
                    {"volume_max": 500000, "rate": Decimal("0.0002"), "min": Decimal("0.10")},
                    {
                        "volume_max": float("inf"),
                        "rate": Decimal("0.00001"),
                        "min": Decimal("0.01"),
                    },
                ],
                "description": "Pro account - tiered pricing",
            },
            Decimal("100000"): {
                "type": "tiered",
                "brackets": [
                    {"volume_max": 100000, "rate": Decimal("0.0005"), "min": Decimal("0.50")},
                    {"volume_max": 500000, "rate": Decimal("0.00005"), "min": Decimal("0.05")},
                    {
                        "volume_max": float("inf"),
                        "rate": Decimal("0.000002"),
                        "min": Decimal("0.01"),
                    },
                ],
                "description": "Fund account - institutional pricing",
            },
        }
    )

    # Scalability score weights (0-100 points total)
    SCALABILITY_ALPHA_DEGRADATION_MAX_POINTS: Decimal = Decimal("40")  # Alpha degradation score
    SCALABILITY_COMMISSION_MAX_POINTS: Decimal = Decimal("30")  # Commission impact score
    SCALABILITY_STABILITY_MAX_POINTS: Decimal = Decimal("30")  # Win rate stability score

    # Commission impact score thresholds
    COMMISSION_IMPACT_EXCELLENT_THRESHOLD: Decimal = Decimal("0.10")  # < 10% = excellent
    COMMISSION_IMPACT_GOOD_THRESHOLD: Decimal = Decimal("0.15")  # < 15% = good
    COMMISSION_IMPACT_POOR_THRESHOLD: Decimal = Decimal("0.15")  # >= 15% = poor

    # Win rate stability penalty factor
    WIN_RATE_STABILITY_PENALTY_FACTOR: Decimal = Decimal("100")  # Multiplier for std dev penalty


@dataclass(frozen=True)
class ExecutionEngineConstants:
    """Constants for pessimistic execution engine."""

    # Slippage settings (in basis points)
    BASE_SLIPPAGE_BPS: Decimal = Decimal("5")  # 5 bps base slippage
    OPTIMISTIC_SLIPPAGE_BPS: Decimal = Decimal("2")  # 2 bps for optimistic mode
    STOP_SLIPPAGE_MULTIPLIER: Decimal = Decimal("2")  # 2x slippage on stops

    # Volatility multiplier for slippage calculation
    VOLATILITY_MULTIPLIER: Decimal = Decimal("2")  # 2x slippage for high volatility

    # Execution timing settings
    ENABLE_NEXT_DAY_EXECUTION: bool = True  # Signal at close t, execute at open t+1


@dataclass(frozen=True)
class BacktestingConstants:
    """
    Main container for all backtesting constants.

    Usage:
        from app.backtesting.constants import BACKTESTING_CONSTANTS

        # Access capital scale constants
        capital_levels = BACKTESTING_CONSTANTS.capital_scale.DEFAULT_CAPITAL_LEVELS

        # Access execution engine constants
        base_slippage = BACKTESTING_CONSTANTS.execution.BASE_SLIPPAGE_BPS
    """

    capital_scale: CapitalScaleConstants = field(default_factory=CapitalScaleConstants)
    execution: ExecutionEngineConstants = field(default_factory=ExecutionEngineConstants)


# Singleton instance for easy import
BACKTESTING_CONSTANTS = BacktestingConstants()


# Convenience functions for backward compatibility
def get_default_capital_levels() -> List[Decimal]:
    """Get default capital levels for scale analysis."""
    return BACKTESTING_CONSTANTS.capital_scale.DEFAULT_CAPITAL_LEVELS.copy()


def get_commission_models() -> Dict[Decimal, CommissionModel]:
    """Get commission models by capital level."""
    return BACKTESTING_CONSTANTS.capital_scale.COMMISSION_MODELS.copy()


def get_base_slippage_bps() -> Decimal:
    """Get base slippage in basis points."""
    return BACKTESTING_CONSTANTS.execution.BASE_SLIPPAGE_BPS


def get_adv_limit_pct() -> Decimal:
    """Get default ADV limit as percentage."""
    return BACKTESTING_CONSTANTS.capital_scale.ADV_LIMIT_PCT_DEFAULT
