"""
Spain Tax Engine - Spain-specific tax calculation.

Spain tax rules:
- Progressive capital gains: 19% / 21% / 23%
- No distinction between LT/ST gains
- Dividends taxed same as capital gains
- No wash sale rule
- EU dividends: 0% withholding tax
- Modelo 720: €50k foreign assets reporting threshold

Uses centralized configuration from SpainTaxConfig.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from app.shared.config.centralized_config import get_config
from app.core.decimal_utils import to_decimal

from .base import TaxEngine

logger = logging.getLogger(__name__)


class SpainTaxEngine(TaxEngine):
    """
    Spain-specific tax calculation.

    Progressive rates (2024/2025):
    - 19%: Gains ≤ €33,007.99
    - 21%: Gains €33,008 - €53,407.99
    - 23%: Gains > €53,408

    Key differences from US:
    - No distinction between long-term and short-term gains
    - Dividends taxed at same progressive rates as capital gains
    - No wash sale rule
    - EU dividends: 0% withholding (Parent-Subsidiary Directive)
    - Losses can offset gains with 4-year carryforward

    All tax rates and thresholds are loaded from centralized configuration.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Spain tax engine with centralized configuration.

        Args:
            config: Optional configuration with custom tax rates (overrides centralized config)
        """
        super().__init__(config)

        # Load Spain tax configuration from centralized config
        spain_tax = get_config().spain_tax

        # Use config values as defaults, allow override via parameter
        self.BRACKET_1_LIMIT = to_decimal(config.get("bracket_1_limit", "33007.99")) if config else Decimal("33007.99")
        self.BRACKET_2_LIMIT = to_decimal(config.get("bracket_2_limit", "53407.99")) if config else Decimal("53407.99")

        self.RATE_1 = to_decimal(config.get("rate_1", spain_tax.irpf_rate_19)) if config else Decimal(str(spain_tax.irpf_rate_19))
        self.RATE_2 = to_decimal(config.get("rate_2", spain_tax.irpf_rate_21)) if config else Decimal(str(spain_tax.irpf_rate_21))
        self.RATE_3 = to_decimal(config.get("rate_3", spain_tax.irpf_rate_23)) if config else Decimal(str(spain_tax.irpf_rate_23))

        self.MODELO_720_THRESHOLD = to_decimal(str(spain_tax.modelo_720_threshold_eur))
        self.LOSS_CARRYFORWARD_YEARS = int(spain_tax.capital_loss_carry_forward_years)

    def calculate_capital_gains_tax(
        self,
        gain: Decimal,
        holding_period_days: int = 0,
    ) -> Decimal:
        """
        Calculate capital gains tax for Spain.

        Spain uses progressive rates with no LT/ST distinction.
        Holding period is irrelevant for Spanish tax calculations.

        Args:
            gain: Capital gain amount
            holding_period_days: Holding period (not used in Spain)

        Returns:
            Tax amount
        """
        if gain <= 0:
            return Decimal("0")

        rate = self._get_progressive_rate(gain)
        tax = gain * rate

        logger.debug(f"Spain tax on gain €{gain:,.2f}: rate={rate:.0%}, tax=€{tax:,.2f}")

        return tax

    def _get_progressive_rate(self, gain: Decimal) -> Decimal:
        """
        Get progressive tax rate based on gain amount.

        Spain uses a progressive tax bracket system for savings income
        (capital gains + dividends).

        Args:
            gain: Capital gain amount

        Returns:
            Tax rate (0.19, 0.21, or 0.23)
        """
        if gain <= self.BRACKET_1_LIMIT:
            return self.RATE_1
        elif gain <= self.BRACKET_2_LIMIT:
            return self.RATE_2
        else:
            return self.RATE_3

    def calculate_dividend_tax(self, dividend: Decimal) -> Decimal:
        """
        Calculate dividend tax for Spain.

        Spain: Dividends taxed same as capital gains (progressive).
        No distinction between qualified/non-qualified dividends.

        Args:
            dividend: Dividend amount

        Returns:
            Tax amount
        """
        return self.calculate_capital_gains_tax(dividend)

    def applies_wash_sale(self) -> bool:
        """
        Spain: No wash sale rule.

        Unlike US, Spain does not have a wash sale rule.
        Investors can sell and repurchase same security immediately
        without triggering wash sale disallowance.

        Returns:
            False (wash sale rule doesn't apply)
        """
        return False

    def get_tax_rate_by_gain(self, gain: Decimal) -> tuple[Decimal, Decimal]:
        """
        Get tax rate and bracket info for a gain amount.

        Useful for display and reporting purposes.

        Args:
            gain: Capital gain amount

        Returns:
            Tuple of (rate, bracket_limit)
        """
        if gain <= self.BRACKET_1_LIMIT:
            return self.RATE_1, self.BRACKET_1_LIMIT
        elif gain <= self.BRACKET_2_LIMIT:
            return self.RATE_2, self.BRACKET_2_LIMIT
        else:
            return self.RATE_3, Decimal("Infinity")

    def calculate_tax_with_deductions(
        self,
        gain: Decimal,
        deductions: Decimal = Decimal("0"),
    ) -> Decimal:
        """
        Calculate tax with allowable deductions.

        Spain allows some deductions (e.g., brokerage fees, legal expenses)
        to be subtracted from gains before taxation.

        Args:
            gain: Capital gain before deductions
            deductions: Allowable deductions

        Returns:
            Tax amount
        """
        taxable_gain = max(gain - deductions, Decimal("0"))
        return self.calculate_capital_gains_tax(taxable_gain)

    def get_withholding_tax_rate(self, country: str) -> Decimal:
        """
        Get withholding tax rate for foreign dividends.

        Uses centralized configuration for dividend withholding rates.

        EU dividends: 0% withholding (Parent-Subsidiary Directive)
        US/UK/CH dividends: 15% (tax treaties)
        Other countries: Default from config (typically 19%)

        Args:
            country: Country code (e.g., "US", "FR", "DE")

        Returns:
            Withholding tax rate
        """
        # Load withholding rates from config
        spain_tax = get_config().spain_tax
        eu_withholding = Decimal(str(spain_tax.eu_dividend_withholding_pct))
        non_eu_withholding = Decimal(str(spain_tax.non_eu_dividend_withholding_pct))

        # EU/EEA countries with 0% withholding (Parent-Subsidiary Directive)
        eu_countries = {
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI",
            "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
            "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
        }

        country_upper = country.upper()

        if country_upper in eu_countries:
            return eu_withholding  # EU: 0% withholding from config
        elif country_upper in ("US", "UK", "CH"):
            return Decimal("0.15")  # US/UK/CH: 15% per tax treaty
        else:
            return non_eu_withholding  # Default from config

    def calculate_total_tax_liability(
        self,
        capital_gains: Decimal,
        dividends: Decimal,
        other_income: Decimal = Decimal("0"),
        deductions: Decimal = Decimal("0"),
    ) -> Decimal:
        """
        Calculate total tax liability for a year.

        Spain taxes capital gains and dividends together at progressive rates.
        Other income (employment, etc.) is taxed under general IRPF brackets.

        Args:
            capital_gains: Total capital gains
            dividends: Total dividends received
            other_income: Other taxable income (not savings income)
            deductions: Allowable deductions

        Returns:
            Total tax liability from savings income (capital gains + dividends)
        """
        # Spain: Capital gains and dividends taxed together as "ahorro"
        total_savings_income = capital_gains + dividends
        taxable_income = max(total_savings_income - deductions, Decimal("0"))

        return self.calculate_capital_gains_tax(taxable_income)

    def get_tax_brackets(self) -> List[Dict]:
        """
        Get all tax brackets for display purposes.

        Returns:
            List of tax bracket dictionaries
        """
        return [
            {
                "bracket": 1,
                "rate": float(self.RATE_1),
                "limit": float(self.BRACKET_1_LIMIT),
                "description": "Gains ≤ €33,007.99",
            },
            {
                "bracket": 2,
                "rate": float(self.RATE_2),
                "limit": float(self.BRACKET_2_LIMIT),
                "description": "Gains €33,008 - €53,407.99",
            },
            {
                "bracket": 3,
                "rate": float(self.RATE_3),
                "limit": float("inf"),
                "description": "Gains > €53,408",
            },
        ]

    def check_modelo_720_threshold(
        self,
        foreign_assets_value: Decimal,
    ) -> Dict:
        """
        Check if foreign assets exceed Modelo 720 reporting threshold.

        Modelo 720 requires reporting of foreign assets worth > €50k
        (per category: accounts, investments, real estate).

        Args:
            foreign_assets_value: Total value of foreign assets

        Returns:
            Dictionary with threshold check results
        """
        exceeds_threshold = foreign_assets_value > self.MODELO_720_THRESHOLD

        return {
            "threshold": float(self.MODELO_720_THRESHOLD),
            "value": float(foreign_assets_value),
            "exceeds": exceeds_threshold,
            "filing_required": exceeds_threshold,
            "form": "Modelo 720",
            "deadline": "March 31st (following year)",
        }

    def calculate_compensated_tax(
        self,
        gains: List[Decimal],
        losses: List[Decimal],
    ) -> Decimal:
        """
        Calculate tax with gain/loss compensation.

        Spain allows losses to offset gains in same tax year.
        Excess losses can be carried forward for 4 years.

        Args:
            gains: List of capital gains
            losses: List of capital losses (as positive numbers)

        Returns:
            Tax liability after compensation
        """
        total_gains = sum(gains)
        total_losses = sum(abs(loss) for loss in losses)
        net_gain = max(total_gains - total_losses, Decimal("0"))

        logger.info(
            f"Gain compensation: gains={total_gains}, losses={total_losses}, "
            f"net={net_gain}"
        )

        return self.calculate_capital_gains_tax(net_gain)

    def estimate_annual_tax(
        self,
        unrealized_gains: Decimal,
        estimated_dividends: Decimal = Decimal("0"),
    ) -> Dict:
        """
        Estimate annual tax liability based on current positions.

        Args:
            unrealized_gains: Current unrealized gains
            estimated_dividends: Expected dividends for year

        Returns:
            Dictionary with tax estimate breakdown
        """
        total_savings_income = unrealized_gains + estimated_dividends

        return {
            "unrealized_gains": float(unrealized_gains),
            "estimated_dividends": float(estimated_dividends),
            "total_income": float(total_savings_income),
            "estimated_tax": float(
                self.calculate_total_tax_liability(
                    capital_gains=unrealized_gains,
                    dividends=estimated_dividends,
                )
            ),
            "effective_rate": float(
                self.calculate_total_tax_liability(
                    capital_gains=unrealized_gains,
                    dividends=estimated_dividends,
                )
                / total_savings_income
                if total_savings_income > 0
                else Decimal("0")
            ),
            "currency": "EUR",
        }

    def __repr__(self) -> str:
        return (
            f"SpainTaxEngine(rates={self.RATE_1}/{self.RATE_2}/{self.RATE_3}, "
            f"brackets={self.BRACKET_1_LIMIT}/{self.BRACKET_2_LIMIT})"
        )
