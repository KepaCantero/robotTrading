from __future__ import annotations

"""Tax Configuration model.

Optimizes tax treatment based on investor's tax residence.
References López de Prado's tax optimization for asset managers.

Reference:
- López de Prado: Machine Learning for Asset Managers (46-lopez-de-prado-machine-learning-asset-managers.md)
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TaxConfig(BaseModel):
    """Tax configuration derived from tax residence.

    Optimizes trading decisions based on:
    - Short-term vs long-term capital gains rates
    - Dividend taxation
    - Withholding tax on foreign securities
    - Wash sale rules (US-specific)
    - Loss carryforward provisions

    References:
    - López de Prado: Tax-aware optimization
    - Country-specific regulations
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Identification
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code",
    )

    base_currency: str = Field(
        default="EUR",
        description="Base currency for calculations",
    )

    # Tax rates
    capital_gains_rate_short: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Short-term capital gains tax rate",
    )

    capital_gains_rate_long: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Long-term capital gains tax rate",
    )

    dividend_tax_rate: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Dividend tax rate",
    )

    # Withholding tax optimization
    withholding_tax_domestic: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Domestic withholding tax rate",
    )

    withholding_tax_eu: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="EU withholding tax rate",
    )

    withholding_tax_us: Decimal = Field(
        default=Decimal("0.30"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="US withholding tax rate (standard 30%)",
    )

    # Country-specific rules
    applies_wash_sale_rule: bool = Field(
        default=False,
        description="Whether wash sale rule applies (US-specific)",
    )

    allows_loss_carryforward: bool = Field(
        default=True,
        description="Whether losses can be carried forward",
    )

    loss_carryforward_years: int | None = Field(
        default=None,
        ge=0,
        description="Years losses can be carried forward",
    )

    # Optimization preferences
    prefer_long_term: bool = Field(
        default=True,
        description="Prefer long-term holdings for tax efficiency",
    )

    min_holding_period_days: int | None = Field(
        default=None,
        ge=1,
        description="Minimum holding period to qualify for long-term rate",
    )

    # Currency hedging
    requires_currency_hedging: bool = Field(
        default=False,
        description="Whether currency hedging is recommended",
    )

    hedging_instruments: list[str] = Field(
        default_factory=list,
        description="Available currency hedging instruments",
    )

    @property
    def has_long_term_advantage(self) -> bool:
        """Check if long-term holdings have tax advantage."""
        return self.capital_gains_rate_long < self.capital_gains_rate_short

    @property
    def long_term_advantage(self) -> Decimal:
        """Calculate the tax advantage of long-term holdings."""
        return self.capital_gains_rate_short - self.capital_gains_rate_long

    @property
    def is_tax_friendly(self) -> bool:
        """Check if jurisdiction is tax-friendly for trading."""
        return self.capital_gains_rate_long < Decimal("0.20") and self.dividend_tax_rate < Decimal(
            "0.20"
        )
