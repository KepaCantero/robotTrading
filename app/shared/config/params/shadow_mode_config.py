"""
Shadow Mode Configuration

Extracted from shadow_mode.py for centralized configuration management.
Contains all configuration parameters for shadow mode execution.

TASK-10: Centralizacion de Configuracion
TASK-24: SRP Refactoring
"""

import logging
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ShadowModeConfigParams(BaseModel):
    """
    Centralized shadow mode configuration.

    This is THE SINGLE SOURCE OF TRUTH for all shadow mode parameters.
    All hardcoded values in shadow_mode.py should reference this config.

    Usage:
        from app.shared.config.centralized_config import get_config
        config = get_config()
        slippage_bps = config.shadow_mode.slippage_bps
        max_orders = config.shadow_mode.max_shadow_orders_per_day
    """

    # ========== SIMULATION SETTINGS ==========
    # Used in ShadowModeConfig dataclass defaults

    slippage_bps: int = Field(
        default=5,
        ge=0,
        description="Default slippage in basis points (5 = 0.05%)",
    )
    fill_delay_ms: int = Field(
        default=100,
        ge=0,
        description="Simulated fill delay in milliseconds",
    )
    partial_fill_probability: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Probability of partial fill (0.1 = 10%)",
    )
    rejection_probability: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Probability of rejection (0.01 = 1%)",
    )

    # ========== SAFETY LIMITS ==========
    # Used for daily order limits

    max_shadow_orders_per_day: int = Field(
        default=1000,
        gt=0,
        description="Maximum number of shadow orders per day (safety limit)",
    )

    # ========== PRICE FALLBACK SETTINGS ==========
    # Used when broker ticker is unavailable

    fallback_price: Decimal = Field(
        default=Decimal("100.00"),
        gt=0,
        description="Fallback price when ticker unavailable (for simulation only)",
    )
    enable_fallback_price: bool = Field(
        default=False,
        description="Allow fallback price when broker ticker fails",
    )

    # ========== COMPARISON SETTINGS ==========
    # Used for shadow vs real comparison

    comparison_window_minutes: int = Field(
        default=60,
        gt=0,
        description="Time window for shadow vs real comparisons",
    )

    # ========== ADVANCED SIMULATION PARAMETERS ==========
    # Used in simulate_fill method

    fill_delay_jitter_min_ms: int = Field(
        default=-20,
        description="Minimum random jitter added to fill delay (can be negative)",
    )
    fill_delay_jitter_max_ms: int = Field(
        default=50,
        description="Maximum random jitter added to fill delay",
    )
    partial_fill_min_pct: float = Field(
        default=0.5,
        gt=0.0,
        lt=1.0,
        description="Minimum partial fill percentage (0.5 = 50%)",
    )
    partial_fill_max_pct: float = Field(
        default=0.9,
        gt=0.0,
        lt=1.0,
        description="Maximum partial fill percentage (0.9 = 90%)",
    )

    @field_validator("partial_fill_min_pct", "partial_fill_max_pct")
    @classmethod
    def validate_partial_fill_range(cls, v: float) -> float:
        """Ensure partial fill percentages are valid."""
        if not 0 < v < 1:
            raise ValueError("Partial fill percentage must be between 0 and 1 (exclusive)")
        return v

    @field_validator("partial_fill_max_pct")
    @classmethod
    def validate_partial_fill_order(cls, v: float, info) -> float:
        """Ensure max is greater than min."""
        if "partial_fill_min_pct" in info.data:
            min_pct = info.data["partial_fill_min_pct"]
            if v <= min_pct:
                raise ValueError(
                    f"partial_fill_max_pct ({v}) must be greater than "
                    f"partial_fill_min_pct ({min_pct})"
                )
        return v
