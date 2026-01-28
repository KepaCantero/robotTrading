"""
Tax Residence Value Object - Tax configuration for investors

TaxResidence represents the tax jurisdiction and configuration
for an investor, critical for multi-market trading.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class RegulatoryRegion(str, Enum):
    """Major regulatory regions for compliance."""

    EUROPEAN_UNION = "eu"
    UNITED_STATES = "us"
    UNITED_KINGDOM = "uk"
    SWITZERLAND = "ch"
    ASIA_PACIFIC = "apac"
    OTHER = "other"


@dataclass(frozen=True)
class TaxResidence:
    """
    Tax residence configuration for the investor.

    Critical for:
    - Tax rate calculation
    - Withholding tax optimization
    - Country-specific regulations
    - Currency hedging decisions
    """

    # Country identification
    country_code: str
    country_name: Optional[str] = None
    region: RegulatoryRegion = RegulatoryRegion.OTHER

    # Tax rates (can be overridden with custom values)
    capital_gains_rate_short: Decimal = Decimal("0.19")
    capital_gains_rate_long: Decimal = Decimal("0.19")
    dividend_tax_rate: Decimal = Decimal("0.19")
    withholding_tax_domestic: Decimal = Decimal("0.19")
    withholding_tax_eu: Decimal = Decimal("0.00")
    withholding_tax_us: Decimal = Decimal("0.30")

    # Country-specific rules
    applies_wash_sale_rule: bool = False
    allows_loss_carryforward: bool = True
    loss_carryforward_years: Optional[int] = 4

    # Currency
    base_currency: str = "EUR"

    # Regulatory
    requires_currency_hedging: bool = False
    regulatory_authority: Optional[str] = None

    def __post_init__(self):
        """Validate tax residence invariants."""
        # Validate country code format (ISO 3166-1 alpha-2)
        if not self.country_code or len(self.country_code) != 2:
            raise ValueError("Country code must be ISO 3166-1 alpha-2 (2 letters)")

        # Validate tax rates are in [0, 1]
        for rate_field in [
            "capital_gains_rate_short",
            "capital_gains_rate_long",
            "dividend_tax_rate",
            "withholding_tax_domestic",
            "withholding_tax_eu",
            "withholding_tax_us",
        ]:
            rate = getattr(self, rate_field)
            if not (Decimal("0") <= rate <= Decimal("1")):
                raise ValueError(f"{rate_field} must be between 0 and 1")

        # Validate loss carryforward years
        if self.loss_carryforward_years is not None and self.loss_carryforward_years < 0:
            raise ValueError("Loss carryforward years must be non-negative")

    @property
    def is_eu_resident(self) -> bool:
        """Check if resident is in EU."""
        return self.region == RegulatoryRegion.EUROPEAN_UNION

    @property
    def is_us_resident(self) -> bool:
        """Check if resident is in US."""
        return self.region == RegulatoryRegion.UNITED_STATES

    @property
    def has_tax_treaty_with_us(self) -> bool:
        """Check if country has tax treaty with US (reduced withholding)."""
        # Most major economies have treaties; this is simplified
        treaty_countries = {
            "EU", "UK", "CH", "JP", "CA", "AU"
        }
        return self.region.value in treaty_countries

    def get_capital_gains_rate(self, is_long_term: bool = False) -> Decimal:
        """
        Get applicable capital gains tax rate.

        Args:
            is_long_term: Whether the gain is long-term

        Returns:
            Applicable tax rate
        """
        return self.capital_gains_rate_long if is_long_term else self.capital_gains_rate_short

    def get_withholding_tax_rate(self, target_region: str) -> Decimal:
        """
        Get withholding tax rate for dividends from target region.

        Args:
            target_region: Target region code (us, eu, domestic)

        Returns:
            Applicable withholding tax rate
        """
        if target_region == "us":
            # Apply reduced rate if tax treaty exists
            return Decimal("0.15") if self.has_tax_treaty_with_us else self.withholding_tax_us
        elif target_region == "eu":
            return self.withholding_tax_eu
        else:
            return self.withholding_tax_domestic

    @classmethod
    def spain(cls) -> TaxResidence:
        """Factory for Spanish tax residence."""
        return cls(
            country_code="ES",
            country_name="Spain",
            region=RegulatoryRegion.EUROPEAN_UNION,
            base_currency="EUR",
            capital_gains_rate_short=Decimal("0.19"),
            capital_gains_rate_long=Decimal("0.21"),
            dividend_tax_rate=Decimal("0.19"),
            regulatory_authority="CNMV",
        )

    @classmethod
    def usa(cls) -> TaxResidence:
        """Factory for US tax residence."""
        return cls(
            country_code="US",
            country_name="United States",
            region=RegulatoryRegion.UNITED_STATES,
            base_currency="USD",
            capital_gains_rate_short=Decimal("0.24"),  # Short-term rates (ordinary income)
            capital_gains_rate_long=Decimal("0.15"),    # Long-term rates
            dividend_tax_rate=Decimal("0.15"),
            applies_wash_sale_rule=True,
            regulatory_authority="SEC",
        )

    @classmethod
    def uk(cls) -> TaxResidence:
        """Factory for UK tax residence."""
        return cls(
            country_code="UK",
            country_name="United Kingdom",
            region=RegulatoryRegion.UNITED_KINGDOM,
            base_currency="GBP",
            capital_gains_rate_short=Decimal("0.20"),
            capital_gains_rate_long=Decimal("0.10"),
            dividend_tax_rate=Decimal("0.0875"),  # Dividend allowance
            regulatory_authority="FCA",
        )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.country_name or self.country_code} ({self.base_currency})"

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"TaxResidence(country_code='{self.country_code}', "
            f"region='{self.region.value}', base_currency='{self.base_currency}')"
        )
