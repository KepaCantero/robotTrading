"""
Dividend Strategy Configuration

This module contains all configuration parameters for the dividend strategy.
Centralized from dividend/dividend_strategy.py hardcoded values.
"""

import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DividendStrategyConfig(BaseModel):
    """Configuration parameters for Dividend Strategy."""

    # Dividend yield thresholds
    min_yield_default: float = Field(
        default=3.0, ge=0.5, le=10.0, description="Default minimum dividend yield (3%)"
    )
    max_yield_default: float = Field(
        default=15.0, ge=5.0, le=50.0, description="Default maximum dividend yield (15%)"
    )

    # Portfolio construction
    portfolio_size_default: int = Field(
        default=25, ge=10, le=100, description="Default portfolio size (25 stocks)"
    )
    max_sector_weight_default: float = Field(
        default=0.30, ge=0.10, le=0.50, description="Default max sector weight (30%)"
    )
    max_single_position_default: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Default max single position (5%)"
    )

    # Payout ratio thresholds
    max_payout_ratio_default: float = Field(
        default=70.0, ge=40.0, le=100.0, description="Default max payout ratio (70%)"
    )
    payout_ratio_critical: float = Field(
        default=100.0, ge=80.0, le=150.0, description="Critical payout ratio threshold (100%)"
    )

    # Dividend coverage
    min_coverage_ratio: float = Field(
        default=0.8, ge=0.5, le=1.5, description="Minimum dividend coverage ratio (0.8)"
    )

    # Quality score thresholds
    quality_multiplier: float = Field(
        default=0.7, ge=0.5, le=0.9, description="Quality score multiplier for deterioration (70%)"
    )
    default_quality_score: float = Field(
        default=70.0, ge=50.0, le=100.0, description="Default quality score for signals (70%)"
    )

    # Dividend capture
    min_days_before_ex_dividend: int = Field(
        default=5, ge=1, le=20, description="Minimum days before ex-dividend for capture (5)"
    )

    # Signal strength thresholds
    strong_yield_threshold: float = Field(
        default=5.0, ge=4.0, le=10.0, description="Yield threshold for strong signal (5%)"
    )
    moderate_yield_threshold: float = Field(
        default=4.0, ge=3.0, le=5.0, description="Yield threshold for moderate signal (4%)"
    )

    # Priority calculation
    priority_confidence_weight: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Confidence weight for priority (60%)"
    )
    priority_yield_weight: float = Field(
        default=5.0, ge=1.0, le=10.0, description="Yield weight for priority (5x)"
    )

    # Default scores
    default_liquidity_score: float = Field(
        default=80.0, ge=50.0, le=100.0, description="Default liquidity score (80%)"
    )
    sell_confidence: float = Field(
        default=70.0, ge=50.0, le=100.0, description="Default confidence for sell signals (70%)"
    )
    sell_priority: float = Field(
        default=60.0, ge=30.0, le=90.0, description="Default priority for sell signals (60%)"
    )

    def __init__(self, **data):
        """Initialize Dividend Strategy configuration with logging."""
        super().__init__(**data)
        logger.info(
            "DividendStrategyConfig initialized",
            extra={
                "component": "DividendStrategyConfig",
                "min_yield_default": self.min_yield_default,
                "max_yield_default": self.max_yield_default,
                "portfolio_size_default": self.portfolio_size_default,
                "max_single_position_default": self.max_single_position_default,
            },
        )
