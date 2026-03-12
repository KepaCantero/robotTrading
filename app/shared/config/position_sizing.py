"""
Position Sizing and Portfolio Configuration Module

Contains configuration for position sizing, portfolio allocation,
rebalancing, and related parameters.
"""

import logging
from decimal import Decimal
from typing import Dict

from pydantic import Field, field_validator

from app.shared.config.base import ConfigBase

logger = logging.getLogger(__name__)


class PositionSizingThresholds(ConfigBase):
    """Configuration for position sizing parameters."""

    # Position size limits
    max_position_size: float = Field(default=0.1, description="Maximum position size (0-1)")
    min_position_size: float = Field(default=0.01, description="Minimum position size (0-1)")

    # ATR Volatility Filter
    min_atr_threshold: float = Field(
        default=0.015, description="Minimum ATR threshold for volatility filtering (0-1)"
    )
    atr_filter_enabled: bool = Field(
        default=True, description="Enable ATR volatility filter to avoid choppy markets"
    )

    # Trailing stop
    trailing_stop_distance_pct: float = Field(
        default=0.02, description="Trailing stop distance percentage (0-1)"
    )
    trailing_stop_enabled: bool = Field(
        default=True, description="Enable trailing stop for dynamic exits"
    )

    # Trailing stop R-multiple
    trailing_stop_r_multiple_activation: float = Field(
        default=1.5, ge=0.5, le=5.0, description="R-multiple profit level to activate trailing stop"
    )
    trailing_stop_r_multiple_distance: float = Field(
        default=1.0, ge=0.5, le=3.0, description="R-multiple distance for trailing stop"
    )

    @field_validator(
        "max_position_size", "min_position_size", "min_atr_threshold", "trailing_stop_distance_pct"
    )
    @classmethod
    def validate_percentage_0_1(cls, v):
        logger.debug("Validating position sizing percentage value", extra={"value": v})
        if not 0 <= v <= 1:
            logger.error("Position sizing percentage validation failed: must be between 0 and 1", extra={"value": v})
            raise ValueError("Percentage values must be between 0 and 1")
        logger.debug("Position sizing percentage validation passed", extra={"value": v})
        return v


class PortfolioAllocationThresholds(ConfigBase):
    """Configuration for portfolio allocation parameters."""

    # Multi-Strategy Allocation (TASK-PA-1, PA-2)
    momentum_target_weight: float = Field(
        default=0.50, description="Momentum strategy target weight"
    )
    mean_reversion_target_weight: float = Field(
        default=0.25, description="Mean reversion strategy target weight"
    )
    pairs_trading_target_weight: float = Field(
        default=0.25, description="Pairs trading strategy target weight"
    )

    # Portfolio Rebalancing (TASK-REB-1, REB-2)
    rebalance_frequency_days: int = Field(default=30, description="Rebalancing frequency in days")
    rebalance_drift_threshold: float = Field(
        default=0.05, description="Rebalance drift threshold (0-1)"
    )
    min_allocation_weight: float = Field(
        default=0.10, description="Minimum allocation weight (0-1)"
    )
    max_allocation_weight: float = Field(
        default=0.70, description="Maximum allocation weight (0-1)"
    )

    @field_validator(
        "momentum_target_weight",
        "mean_reversion_target_weight",
        "pairs_trading_target_weight",
        "rebalance_drift_threshold",
        "min_allocation_weight",
        "max_allocation_weight",
    )
    @classmethod
    def validate_percentage_0_1(cls, v):
        logger.debug("Validating portfolio allocation percentage value", extra={"value": v})
        if not 0 <= v <= 1:
            logger.error("Portfolio allocation percentage validation failed: must be between 0 and 1", extra={"value": v})
            raise ValueError("Percentage values must be between 0 and 1")
        logger.debug("Portfolio allocation percentage validation passed", extra={"value": v})
        return v


class AccountConfiguration(ConfigBase):
    """Configuration for account parameters."""

    # Account configuration
    account_cash: float = Field(default=100000.0, description="Initial account cash")
    account_portfolio_value: float = Field(default=100000.0, description="Initial portfolio value")

    # Tax optimization
    tax_loss_harvesting_enabled: bool = Field(
        default=True, description="Enable tax loss harvesting"
    )
    tax_loss_harvesting_threshold: float = Field(
        default=0.01, description="Tax loss harvesting threshold (0-1)"
    )
    short_term_capital_gain_rate: float = Field(
        default=0.35, description="Short term capital gains rate"
    )
    long_term_capital_gain_rate: float = Field(
        default=0.15, description="Long term capital gains rate"
    )

    # Crypto fallback prices (used when API is unavailable)
    crypto_fallback_prices: Dict[str, Decimal] = Field(
        default_factory=lambda: {
            "BTC": Decimal("95000"),
            "ETH": Decimal("3500"),
            "BNB": Decimal("650"),
            "SOL": Decimal("200"),
            "XRP": Decimal("1.20"),
            "ADA": Decimal("0.60"),
            "DOGE": Decimal("0.15"),
            "DOT": Decimal("8.00"),
            "MATIC": Decimal("0.50"),
            "LINK": Decimal("15.00"),
        },
        description="Fallback crypto prices when API is unavailable",
    )
