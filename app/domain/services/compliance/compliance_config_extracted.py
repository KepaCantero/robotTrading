"""
Compliance Configuration
Extracted from compliance_engine.py for SRP compliance.
TASK-24: SRP Refactoring
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ComplianceConfig(BaseModel):
    """
    Configuration for compliance engine thresholds and limits.

    All trading-related thresholds are centralized here for easy adjustment
    and validation. This addresses GAP-CFG-002: Hardcoded thresholds.
    """

    # Position Limits (Chan Rule 1)
    max_position_ratio: float = Field(
        default=0.10,
        ge=0.01,
        le=1.0,
        description="Maximum position size as ratio of portfolio value",
    )

    # Drawdown Limits (Chan Rule 1)
    max_drawdown_ratio: float = Field(
        default=0.25,
        ge=0.01,
        le=1.0,
        description="Maximum drawdown as ratio of peak portfolio value",
    )

    # Leverage Limits
    max_leverage_ratio: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Maximum gross leverage ratio",
    )

    # Kill Switch (Hull Rule 13.1)
    kill_switch_threshold: float = Field(
        default=-0.05,
        ge=-1.0,
        le=0.0,
        description="Daily loss threshold that triggers trading halt (negative)",
    )

    # Data Quality
    min_data_quality_score: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Minimum data quality score to allow trading",
    )

    max_data_age_days: float = Field(
        default=1.0,
        ge=0.0,
        description="Maximum age of price data in days",
    )

    # Portfolio VaR
    max_portfolio_volatility: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Maximum annualized portfolio volatility",
    )

    # Hull VaR
    max_daily_var_95: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Maximum 1-day 95% VaR",
    )

    # SLO Thresholds
    slo_latency_ms: float = Field(
        default=100.0,
        ge=1.0,
        description="Maximum acceptable latency in milliseconds",
    )

    # Data Quality Deductions
    data_quality_nan_penalty: float = Field(
        default=15.0,
        ge=0.0,
        le=100.0,
        description="Quality score deduction for NaN values",
    )

    data_quality_stale_penalty: float = Field(
        default=20.0,
        ge=0.0,
        le=100.0,
        description="Quality score deduction for stale data",
    )

    @field_validator("kill_switch_threshold")
    @classmethod
    def kill_switch_must_be_negative(cls, v: float) -> float:
        """Kill switch threshold must be negative (loss)."""
        if v > 0:
            raise ValueError("Kill switch threshold must be negative (representing a loss)")
        return v


# =============================================================================
# SYSTEMS AVAILABILITY TRACKING
# =============================================================================
