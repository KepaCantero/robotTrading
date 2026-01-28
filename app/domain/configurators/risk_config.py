"""
Risk Config Value Object - Concrete risk parameters based on risk tolerance.

This module defines the RiskConfig value object that contains all the
concrete risk parameters derived from a user's risk tolerance level.

Reference: AUDIT_PLAN_COMPLETO.md Section 4.2 - Brecha #2
Reference: rules/trading/papers/13-john-hull-risk-management.md
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskConfig(BaseModel):
    """
    Risk Configuration value object.

    Contains concrete risk parameters derived from risk tolerance.
    This is a frozen value object - immutable after creation.

    Risk Tolerance Mapping:
    - BAJO:   Drawdown < 15%, Position limit 5%, No leverage
    - MEDIO:  Drawdown < 25%, Position limit 10%, Leverage 1.5x
    - ALTO:   Drawdown < 40%, Position limit 20%, Leverage 2.0x

    Reference: Hull Chapter 18 - Risk Management limits
    """

    model_config = ConfigDict(
        frozen=True,  # Immutable value object
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Portfolio-level risk limits
    max_drawdown: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Maximum allowed portfolio drawdown (e.g., 0.15 = 15%)",
    )

    max_daily_loss: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Daily circuit breaker - maximum loss per day (e.g., 0.05 = 5%)",
    )

    # Position-level risk limits
    max_position_size: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Maximum size of any single position (e.g., 0.05 = 5% of portfolio)",
    )

    # VaR-based risk limits
    portfolio_var_limit: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Maximum Value-at-Risk as portfolio percentage (e.g., 0.02 = 2%)",
    )

    # Leverage controls
    leverage_allowed: bool = Field(
        ...,
        description="Whether leverage is permitted for this risk level",
    )

    max_leverage: Decimal = Field(
        ...,
        ge=Decimal("1.0"),
        le=Decimal("3.0"),
        description="Maximum leverage multiplier (1.0 = no leverage, 2.0 = 2x)",
    )

    # Stop loss parameters (ATR-based)
    stop_loss_atr_multiplier: Decimal = Field(
        ...,
        ge=Decimal("0.5"),
        le=Decimal("5.0"),
        description="Stop loss distance as ATR multiplier (e.g., 2.0 = 2x ATR)",
    )

    trailing_stop_atr_multiplier: Decimal = Field(
        ...,
        ge=Decimal("1.0"),
        le=Decimal("10.0"),
        description="Trailing stop distance as ATR multiplier (e.g., 3.0 = 3x ATR)",
    )

    @field_validator("max_leverage")
    @classmethod
    def validate_leverage_consistency(cls, v: Decimal, info) -> Decimal:
        """Ensure max_leverage is 1.0 when leverage not allowed."""
        if "leverage_allowed" in info.data and not info.data["leverage_allowed"]:
            if v != Decimal("1.0"):
                raise ValueError("max_leverage must be 1.0 when leverage_allowed is False")
        return v

    @field_validator("trailing_stop_atr_multiplier")
    @classmethod
    def validate_trailing_stop_greater_than_stop_loss(cls, v: Decimal, info) -> Decimal:
        """Ensure trailing stop is wider than stop loss."""
        if "stop_loss_atr_multiplier" in info.data:
            stop_loss = info.data["stop_loss_atr_multiplier"]
            if v <= stop_loss:
                raise ValueError(
                    f"trailing_stop_atr_multiplier ({v}) must be greater than "
                    f"stop_loss_atr_multiplier ({stop_loss})"
                )
        return v

    @property
    def is_conservative(self) -> bool:
        """Check if this is a conservative (bajo) risk configuration."""
        return not self.leverage_allowed and self.max_position_size <= Decimal("0.05")

    @property
    def is_aggressive(self) -> bool:
        """Check if this is an aggressive (alto) risk configuration."""
        return self.max_position_size >= Decimal("0.15") and self.leverage_allowed

    @property
    def risk_level(self) -> str:
        """Get the risk level label."""
        if self.is_conservative:
            return "BAJO"
        if self.is_aggressive:
            return "ALTO"
        return "MEDIO"

    def get_position_limit_for_capital(self, capital: Decimal) -> Decimal:
        """
        Calculate maximum position value in currency units.

        Args:
            capital: Total capital in base currency

        Returns:
            Maximum position value in currency units
        """
        return capital * self.max_position_size

    def get_var_limit_for_capital(self, capital: Decimal) -> Decimal:
        """
        Calculate VaR limit in currency units.

        Args:
            capital: Total capital in base currency

        Returns:
            VaR limit in currency units
        """
        return capital * self.portfolio_var_limit

    def get_daily_loss_limit_for_capital(self, capital: Decimal) -> Decimal:
        """
        Calculate daily loss limit in currency units.

        Args:
            capital: Total capital in base currency

        Returns:
            Daily loss limit in currency units
        """
        return capital * self.max_daily_loss
