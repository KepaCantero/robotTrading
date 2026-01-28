"""Risk Configuration model.

Defines risk parameters based on user risk tolerance.
References John Hull's risk management principles.

Reference:
- John Hull: Risk Management (13-john-hull-risk-management.md)
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RiskConfig(BaseModel):
    """Risk configuration parameters derived from risk tolerance.

    Based on John Hull's risk management principles:
    - Value at Risk (VaR) limits
    - Expected Shortfall (ES) controls
    - Position sizing limits
    - Leverage constraints

    Mapping from RiskTolerance:
    - BAJO: Conservative - max 15% drawdown, no leverage
    - MEDIO: Moderate - max 25% drawdown, limited leverage
    - ALTO: Aggressive - max 40% drawdown, higher leverage allowed
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Drawdown controls (Hull: VaR and ES)
    max_drawdown: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Maximum allowed drawdown (e.g., 0.15 = 15%)",
    )

    var_confidence: Decimal = Field(
        default=Decimal("0.95"),
        ge=Decimal("0.90"),
        le=Decimal("0.99"),
        description="Value at Risk confidence level",
    )

    # Position sizing (Hull: Concentration risk)
    max_position_size: Decimal = Field(
        ...,
        ge=Decimal("0.01"),
        le=Decimal("1"),
        description="Maximum position size as fraction of portfolio",
    )

    max_sector_exposure: Decimal = Field(
        default=Decimal("0.30"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Maximum exposure to any single sector",
    )

    # Leverage controls (Hull: Leverage risk)
    leverage_allowed: bool = Field(
        default=False,
        description="Whether leverage is permitted for this risk profile",
    )

    max_leverage: Decimal = Field(
        default=Decimal("1.0"),
        ge=Decimal("1.0"),
        le=Decimal("3.0"),
        description="Maximum leverage multiplier (e.g., 2.0 = 2x)",
    )

    # Portfolio controls (Hull: Diversification)
    min_positions: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Minimum number of positions required",
    )

    max_positions: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of positions allowed",
    )

    # Risk management triggers (Hull: Stop-loss)
    stop_loss_enabled: bool = Field(
        default=True,
        description="Whether automatic stop-loss is enabled",
    )

    stop_loss_atr_multiplier: Decimal = Field(
        default=Decimal("2.0"),
        ge=Decimal("1.0"),
        le=Decimal("5.0"),
        description="ATR multiplier for stop-loss placement",
    )

    trailing_stop_enabled: bool = Field(
        default=False,
        description="Whether trailing stop-loss is enabled",
    )

    # Volatility controls (Hull: Volatility risk)
    max_portfolio_volatility: Decimal = Field(
        default=Decimal("0.20"),
        ge=Decimal("0.05"),
        le=Decimal("0.50"),
        description="Maximum annualized portfolio volatility",
    )

    volatility_target: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.05"),
        le=Decimal("0.50"),
        description="Target volatility (None = no targeting)",
    )

    @property
    def is_conservative(self) -> bool:
        """Check if this is a conservative risk configuration."""
        return self.max_drawdown <= Decimal("0.20") and not self.leverage_allowed

    @property
    def is_aggressive(self) -> bool:
        """Check if this is an aggressive risk configuration."""
        return self.max_drawdown >= Decimal("0.30") or (
            self.leverage_allowed and self.max_leverage >= Decimal("1.5")
        )

    @property
    def effective_max_leverage(self) -> Decimal:
        """Get the effective maximum leverage (1.0 if leverage not allowed)."""
        return self.max_leverage if self.leverage_allowed else Decimal("1.0")
