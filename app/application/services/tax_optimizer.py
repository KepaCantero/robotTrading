"""
Tax Optimization Service

Provides tax optimization based on tax residence.
Implements different tax strategies for different jurisdictions.

Reference: Rule 46-lopez-de-prado-machine-learning-asset-managers.md
Reference: Tax optimization for algorithmic trading
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum


logger = logging.getLogger(__name__)


class TaxMethod(str, Enum):
    """Tax lot accounting methods."""

    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    HIFO = "hifo"  # Highest In, First Out (minimizes taxes)
    MIN_TAX = "min_tax"  # Minimize current tax liability
    MAX_TAX = "max_tax"  # Maximize current tax liability (tax loss harvesting)


class TaxJurisdiction(str, Enum):
    """Supported tax jurisdictions."""

    SPAIN = "spain"
    USA = "usa"
    UK = "uk"
    GERMANY = "germany"
    FRANCE = "france"
    DEFAULT = "default"


@dataclass
class TaxLot:
    """A single tax lot for position tracking."""

    lot_id: str
    symbol: str
    quantity: Decimal
    acquisition_date: date
    acquisition_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    holding_period_days: int

    @property
    def is_long_term(self) -> bool:
        """Check if lot qualifies for long-term treatment."""
        return self.holding_period_days >= 365

    @property
    def realized_pnl(self) -> Decimal:
        """Calculate realized P&L if sold now."""
        return (self.current_price - self.acquisition_price) * self.quantity


@dataclass
class TaxCalculation:
    """Tax calculation result."""

    short_term_gains: Decimal  # Short-term capital gains
    long_term_gains: Decimal  # Long-term capital gains
    dividend_income: Decimal  # Dividend income
    short_term_tax: Decimal  # Tax on short-term gains
    long_term_tax: Decimal  # Tax on long-term gains
    dividend_tax: Decimal  # Tax on dividends
    total_tax: Decimal  # Total tax liability
    effective_tax_rate: float  # Effective tax rate
    tax_los_harvesting_opportunity: Decimal  # Losses available to harvest


class TaxOptimizer:
    """
    Tax optimization service.

    Provides tax optimization strategies based on jurisdiction:
    - Tax lot accounting (FIFO, LIFO, HIFO, Min Tax)
    - Tax loss harvesting
    - Dividend tax optimization
    - Wash sale avoidance

    Reference: López de Prado tax optimization techniques
    """

    def __init__(self):
        """Initialize tax optimizer."""
        # Tax rates by jurisdiction (simplified)
        self._tax_rates = {
            TaxJurisdiction.SPAIN: {
                "short_term": Decimal("0.28"),  # 28% for <1 year
                "long_term": Decimal("0.21"),  # 21% for >1 year (new rates)
                "dividend": Decimal("0.19"),  # 19% withholding
                "withholding": Decimal("0.19"),
            },
            TaxJurisdiction.USA: {
                "short_term": Decimal("0.35"),  # Ordinary income rate
                "long_term": Decimal("0.15"),  # 15% for >1 year
                "dividend": Decimal("0.15"),  # 15% qualified dividends
                "withholding": Decimal("0.0"),
            },
            TaxJurisdiction.UK: {
                "short_term": Decimal("0.20"),  # 20% basic rate
                "long_term": Decimal("0.10"),  # 10% (no distinction in UK)
                "dividend": Decimal("0.0875"),  # 8.75% dividend tax
                "withholding": Decimal("0.0"),
            },
            TaxJurisdiction.DEFAULT: {
                "short_term": Decimal("0.25"),
                "long_term": Decimal("0.15"),
                "dividend": Decimal("0.15"),
                "withholding": Decimal("0.15"),
            },
        }

        # Wash sale periods by jurisdiction (days)
        self._wash_sale_periods = {
            TaxJurisdiction.USA: 30,  # 30 days for US wash sale rule
            TaxJurisdiction.DEFAULT: 0,  # No wash sale rule
        }

    def configure_for_residence(
        self,
        country: str,
    ) -> dict[str, object]:
        """
        Get tax configuration for residence.

        Args:
            country: Country code (ISO 3166-1 alpha-2 format)

        Returns:
            Dictionary with tax configuration

        Raises:
            ValueError: If country code is invalid or empty
        """
        if not country or not isinstance(country, str):
            raise ValueError("country must be a non-empty string")

        logger.info("Configuring tax residence", country=country)
        try:
            jurisdiction = TaxJurisdiction(country.lower())
        except ValueError:
            jurisdiction = TaxJurisdiction.DEFAULT

        rates = self._tax_rates.get(jurisdiction, self._tax_rates[TaxJurisdiction.DEFAULT])

        return {
            "jurisdiction": jurisdiction.value,
            "short_term_rate": float(rates["short_term"]),
            "long_term_rate": float(rates["long_term"]),
            "dividend_rate": float(rates["dividend"]),
            "withholding_rate": float(rates["withholding"]),
            "tax_method": self._get_default_method(jurisdiction),
            "wash_sale_period": self._wash_sale_periods.get(jurisdiction, 0),
        }

    def _get_default_method(self, jurisdiction: TaxJurisdiction) -> TaxMethod:
        """Get default tax lot accounting method for jurisdiction."""
        if jurisdiction == TaxJurisdiction.USA:
            return TaxMethod.HIFO  # Minimize taxes
        elif jurisdiction in (TaxJurisdiction.SPAIN, TaxJurisdiction.UK):
            return TaxMethod.FIFO  # Common in Europe
        else:
            return TaxMethod.FIFO

    def calculate_tax_liability(
        self,
        tax_lots: list[TaxLot],
        sold_quantity: Decimal,
        sale_price: Decimal,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
        method: TaxMethod = TaxMethod.FIFO,
    ) -> tuple[TaxCalculation, list[TaxLot]]:
        """
        Calculate tax liability for a sale using specified method.

        Args:
            tax_lots: Available tax lots
            sold_quantity: Quantity to sell (must be positive)
            sale_price: Sale price per share (must be positive)
            jurisdiction: Tax jurisdiction
            method: Tax lot accounting method

        Returns:
            Tuple of (TaxCalculation, remaining_lots)

        Raises:
            ValueError: If validation fails
        """
        if sold_quantity <= 0:
            raise ValueError("sold_quantity must be positive")

        if sale_price <= 0:
            raise ValueError("sale_price must be positive")

        if not tax_lots:
            raise ValueError("tax_lots cannot be empty")

        logger.info(
            "Calculating tax liability",
            jurisdiction=jurisdiction.value,
            method=method.value,
            quantity=str(sold_quantity),
        )
        # Select lots to sell based on method
        lots_to_sell, remaining_lots = self._select_lots(tax_lots, sold_quantity, method)

        # Calculate gains/losses
        short_term_gains = Decimal("0")
        long_term_gains = Decimal("0")

        for lot in lots_to_sell:
            pnl = lot.realized_pnl
            if lot.is_long_term:
                long_term_gains += pnl
            else:
                short_term_gains += pnl

        # Get tax rates
        rates = self._tax_rates.get(jurisdiction, self._tax_rates[TaxJurisdiction.DEFAULT])

        # Calculate taxes
        short_term_tax = max(Decimal("0"), short_term_gains) * rates["short_term"]
        long_term_tax = max(Decimal("0"), long_term_gains) * rates["long_term"]

        # Handle losses (can offset up to $3000 or carry forward)
        total_gains = short_term_gains + long_term_gains

        if total_gains < 0:
            # Loss - can use to offset other gains or carry forward
            tax_los_harvesting = abs(total_gains)
            total_tax = Decimal("0")
        else:
            tax_los_harvesting = Decimal("0")
            total_tax = short_term_tax + long_term_tax

        tax_calc = TaxCalculation(
            short_term_gains=short_term_gains,
            long_term_gains=long_term_gains,
            dividend_income=Decimal("0"),
            short_term_tax=short_term_tax,
            long_term_tax=long_term_tax,
            dividend_tax=Decimal("0"),
            total_tax=total_tax,
            effective_tax_rate=float(total_tax / total_gains) if total_gains > 0 else 0.0,
            tax_los_harvesting_opportunity=tax_los_harvesting,
        )

        return tax_calc, remaining_lots

    def _select_lots(
        self,
        tax_lots: list[TaxLot],
        quantity: Decimal,
        method: TaxMethod,
    ) -> tuple[list[TaxLot], list[TaxLot]]:
        """
        Select tax lots to sell based on method.

        Args:
            tax_lots: Available tax lots
            quantity: Quantity to sell
            method: Selection method

        Returns:
            Tuple of (selected_lots, remaining_lots)
        """
        lots_to_sell = []
        remaining_quantity = quantity

        if method == TaxMethod.FIFO:
            # Sort by acquisition date (oldest first)
            sorted_lots = sorted(tax_lots, key=lambda l: l.acquisition_date)
        elif method == TaxMethod.LIFO:
            # Sort by acquisition date (newest first)
            sorted_lots = sorted(tax_lots, key=lambda l: l.acquisition_date, reverse=True)
        elif method == TaxMethod.HIFO:
            # Sort by acquisition price (highest first - minimize gains)
            sorted_lots = sorted(tax_lots, key=lambda l: l.acquisition_price, reverse=True)
        elif method == TaxMethod.MIN_TAX:
            # Sort by tax impact (long-term losses first)
            sorted_lots = sorted(
                tax_lots,
                key=lambda l: (
                    not l.is_long_term,  # Long-term first
                    l.realized_pnl,  # Losses first
                ),
            )
        else:  # MAX_TAX
            # Sort to maximize taxes (harvest gains)
            sorted_lots = sorted(
                tax_lots,
                key=lambda l: (
                    l.is_long_term,  # Short-term first
                    -l.realized_pnl,  # Gains first
                ),
            )

        # Select lots
        for lot in sorted_lots:
            if remaining_quantity <= 0:
                lots_to_sell.append(lot)
                continue

            if lot.quantity <= remaining_quantity:
                # Sell entire lot
                lots_to_sell.append(lot)
                remaining_quantity -= lot.quantity
            else:
                # Partial sale - split the lot
                sold_lot = TaxLot(
                    lot_id=f"{lot.lot_id}_partial",
                    symbol=lot.symbol,
                    quantity=remaining_quantity,
                    acquisition_date=lot.acquisition_date,
                    acquisition_price=lot.acquisition_price,
                    current_price=lot.current_price,
                    unrealized_pnl=lot.unrealized_pnl * (remaining_quantity / lot.quantity),
                    holding_period_days=lot.holding_period_days,
                )
                lots_to_sell.append(sold_lot)

                # Update remaining lot
                remaining_lot = TaxLot(
                    lot_id=lot.lot_id,
                    symbol=lot.symbol,
                    quantity=lot.quantity - remaining_quantity,
                    acquisition_date=lot.acquisition_date,
                    acquisition_price=lot.acquisition_price,
                    current_price=lot.current_price,
                    unrealized_pnl=lot.unrealized_pnl
                    * ((lot.quantity - remaining_quantity) / lot.quantity),
                    holding_period_days=lot.holding_period_days,
                )
                remaining_lots = [remaining_lot]
                remaining_quantity = Decimal("0")
                break

        # Add lots not touched
        if remaining_quantity > 0:
            for lot in sorted_lots:
                if lot not in lots_to_sell:
                    remaining_lots.append(lot)
        else:
            for lot in sorted_lots:
                if lot not in lots_to_sell and lot.lot_id not in [l.lot_id for l in lots_to_sell]:
                    remaining_lots.append(lot)

        return lots_to_sell, remaining_lots

    def find_tax_loss_harvesting_opportunities(
        self,
        tax_lots: list[TaxLot],
        jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
        min_loss: Decimal = Decimal("1000"),
    ) -> list[tuple[TaxLot, Decimal]]:
        """
        Find tax loss harvesting opportunities.

        Args:
            tax_lots: Current tax lots
            jurisdiction: Tax jurisdiction
            min_loss: Minimum loss to consider harvesting

        Returns:
            List of (lot, potential_tax_savings)
        """
        opportunities = []

        rates = self._tax_rates.get(jurisdiction, self._tax_rates[TaxJurisdiction.DEFAULT])

        for lot in tax_lots:
            if lot.unrealized_pnl < -min_loss:
                # Loss opportunity
                potential_savings = abs(lot.unrealized_pnl) * rates["short_term"]

                # If long-term, savings are less
                if lot.is_long_term:
                    potential_savings = abs(lot.unrealized_pnl) * rates["long_term"]

                opportunities.append((lot, potential_savings))

        # Sort by potential savings (highest first)
        opportunities.sort(key=lambda x: x[1], reverse=True)

        return opportunities

    def should_harvest_loss(
        self,
        lot: TaxLot,
        current_date: date,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
    ) -> bool:
        """
        Determine if should harvest loss from a lot.

        Checks wash sale rules and other constraints.

        Args:
            lot: Tax lot to consider
            current_date: Current date
            jurisdiction: Tax jurisdiction

        Returns:
            True if should harvest loss
        """
        if lot.unrealized_pnl >= 0:
            return False  # No loss to harvest

        # Check wash sale period
        wash_period = self._wash_sale_periods.get(jurisdiction, 0)

        if wash_period > 0:
            # Cannot buy same stock within wash period
            # This is a simplified check
            recent_purchase = current_date - timedelta(days=wash_period)
            if lot.acquisition_date >= recent_purchase:
                return False  # Would trigger wash sale

        # Loss is significant enough?
        if abs(lot.unrealized_pnl) < Decimal("100"):
            return False  # Too small to matter

        return True

    def optimize_dividend_tax(
        self,
        dividend_income: Decimal,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
        has_tax_treaty: bool = True,
    ) -> Decimal:
        """
        Optimize dividend tax based on jurisdiction and treaties.

        Args:
            dividend_income: Gross dividend income
            jurisdiction: Tax jurisdiction
            has_tax_treaty: Whether tax treaty applies

        Returns:
            Optimized tax amount
        """
        rates = self._tax_rates.get(jurisdiction, self._tax_rates[TaxJurisdiction.DEFAULT])

        base_rate = rates["dividend"]

        # Apply treaty reductions if applicable
        if has_tax_treaty and jurisdiction == TaxJurisdiction.USA:
            # Many treaties reduce US withholding to 15%
            base_rate = min(base_rate, Decimal("0.15"))

        return dividend_income * base_rate

    def calculate_after_tax_return(
        self,
        pre_tax_return: Decimal,
        holding_period_days: int,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
    ) -> Decimal:
        """
        Calculate after-tax return considering short vs long-term rates.

        Args:
            pre_tax_return: Pre-tax return
            holding_period_days: Holding period in days
            jurisdiction: Tax jurisdiction

        Returns:
            After-tax return
        """
        rates = self._tax_rates.get(jurisdiction, self._tax_rates[TaxJurisdiction.DEFAULT])

        if holding_period_days >= 365:
            tax_rate = rates["long_term"]
        else:
            tax_rate = rates["short_term"]

        if pre_tax_return > 0:
            tax = pre_tax_return * tax_rate
            return pre_tax_return - tax
        else:
            # Loss - can deduct
            return pre_tax_return * (Decimal("1") - tax_rate)
