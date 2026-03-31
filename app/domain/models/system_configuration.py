from __future__ import annotations

"""System Configuration model.

Complete configuration derived from InputProfile.
Combines strategy selection, risk parameters, and tax optimization.

This is the output of InputProfileRouter and serves as the complete
configuration for the trading system.
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.risk_config import RiskConfig
from app.domain.models.strategy_type import StrategyType
from app.domain.models.tax_config import TaxConfig


class SystemConfiguration(BaseModel):
    """Complete system configuration derived from InputProfile.

    This model encapsulates all configuration needed to run the trading system:
    - Strategy type (what to trade)
    - Risk parameters (how much risk to take)
    - Tax optimization (how to optimize after-tax returns)

    The InputProfileRouter creates this configuration based on the user's
    InputProfile, mapping their investment objectives, risk tolerance,
    and tax residence to concrete system parameters.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Strategy selection
    strategy_type: StrategyType = Field(
        ...,
        description="Selected trading strategy type",
    )

    # Risk configuration
    risk_config: RiskConfig = Field(
        ...,
        description="Risk parameters derived from risk tolerance",
    )

    # Tax configuration
    tax_config: Optional[TaxConfig] = Field(
        default=None,
        description="Tax optimization parameters (if tax residence provided)",
    )

    # Capital allocation
    initial_capital: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Initial capital allocated",
    )

    capital_buffer: Decimal = Field(
        default=Decimal("0.05"),
        ge=Decimal("0"),
        le=Decimal("0.20"),
        description="Capital buffer kept as cash (e.g., 0.05 = 5%)",
    )

    # Investment horizon
    investment_horizon_months: int = Field(
        ...,
        ge=1,
        description="Investment horizon in months",
    )

    rebalance_frequency_days: int = Field(
        default=30,
        ge=1,
        description="Rebalancing frequency in days",
    )

    # Optional constraints
    sector_limits: Optional[dict[str, Decimal]] = Field(
        default=None,
        description="Optional sector-specific limits",
    )

    exclude_symbols: Optional[set[str]] = Field(
        default=None,
        description="Symbols to exclude from trading",
    )

    # Metadata
    config_version: str = Field(
        default="1.0",
        description="Configuration version",
    )

    @property
    def deployable_capital(self) -> Decimal:
        """Calculate capital available for deployment after buffer."""
        buffer_amount = self.initial_capital * self.capital_buffer
        return self.initial_capital - buffer_amount

    @property
    def requires_long_term_focus(self) -> bool:
        """Check if strategy prefers long-term holdings."""
        return self.strategy_type in {StrategyType.DIVIDEND, StrategyType.LOW_VOLATILITY} or bool(
            self.tax_config and self.tax_config.prefer_long_term
        )

    @property
    def is_complex_strategy(self) -> bool:
        """Check if strategy requires complex execution."""
        return self.strategy_type in {
            StrategyType.MULTI_FACTOR,
            StrategyType.COVERED_CALL,
        }

    @property
    def expected_volatility(self) -> Decimal:
        """Get expected annualized volatility based on strategy."""
        volatilities = {
            StrategyType.LOW_VOLATILITY: Decimal("0.10"),
            StrategyType.DIVIDEND: Decimal("0.15"),
            StrategyType.MULTI_FACTOR: Decimal("0.18"),
            StrategyType.COVERED_CALL: Decimal("0.12"),
            StrategyType.MOMENTUM: Decimal("0.25"),
        }
        return volatilities.get(self.strategy_type, Decimal("0.20"))

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for logging."""
        return {
            "strategy_type": self.strategy_type.value,
            "max_drawdown": str(self.risk_config.max_drawdown),
            "leverage_allowed": self.risk_config.leverage_allowed,
            "max_leverage": str(self.risk_config.max_leverage),
            "initial_capital": str(self.initial_capital),
            "deployable_capital": str(self.deployable_capital),
            "investment_horizon_months": self.investment_horizon_months,
            "tax_optimization": self.tax_config is not None,
            "expected_volatility": str(self.expected_volatility),
        }
