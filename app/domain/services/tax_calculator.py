"""
Tax Calculator Domain Service - Tax calculations for trades

TaxCalculator provides domain logic for calculating tax liabilities
based on tax residence and trade characteristics.

Reference: Rule 05-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Optional

from app.domain.entities.trade import Trade, ExitReason
from app.domain.entities.position import Position
from app.domain.value_objects.tax_residence import TaxResidence


@dataclass
class TaxLiability:
    """Tax liability for a trade or period."""

    gross_profit: Decimal
    taxable_profit: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    net_profit: Decimal

    # Breakdown
    short_term_gains: Decimal
    long_term_gains: Decimal
    short_term_tax: Decimal
    long_term_tax: Decimal


@dataclass
class TaxLot:
    """Tax lot for tracking cost basis."""

    symbol: str
    quantity: Decimal
    cost_basis: Decimal
    acquisition_date: datetime
    is_long_term: bool


class TaxCalculator:
    """
    Domain service for calculating tax liabilities.

    Pure domain logic for tax calculations based on:
    - Tax residence (country, rates)
    - Holding period (short/long term)
    - Trade type (capital gains, dividends)
    """

    # Standard holding period for long-term classification (1 year)
    LONG_TERM_HOLDING_DAYS = 365

    def __init__(self, tax_residence: TaxResidence):
        """
        Initialize tax calculator with tax residence.

        Args:
            tax_residence: Tax residence configuration
        """
        self._tax_residence = tax_residence

    def calculate_trade_tax(self, trade: Trade) -> TaxLiability:
        """
        Calculate tax liability for a single trade.

        Args:
            trade: Completed trade

        Returns:
            TaxLiability with calculated taxes
        """
        gross_profit = trade.get_net_pnl().amount
        profit = max(gross_profit, Decimal("0"))

        # Determine if short or long term
        is_long_term = self._is_long_term(trade)

        # Apply appropriate tax rate
        if is_long_term:
            tax_rate = self._tax_residence.capital_gains_rate_long
            long_term_gains = profit
            short_term_gains = Decimal("0")
            long_term_tax = profit * tax_rate
            short_term_tax = Decimal("0")
        else:
            tax_rate = self._tax_residence.capital_gains_rate_short
            short_term_gains = profit
            long_term_gains = Decimal("0")
            short_term_tax = profit * tax_rate
            long_term_tax = Decimal("0")

        total_tax = short_term_tax + long_term_tax

        return TaxLiability(
            gross_profit=gross_profit,
            taxable_profit=profit,
            tax_rate=tax_rate,
            tax_amount=total_tax,
            net_profit=gross_profit - total_tax,
            short_term_gains=short_term_gains,
            long_term_gains=long_term_gains,
            short_term_tax=short_term_tax,
            long_term_tax=long_term_tax,
        )

    def calculate_period_tax(
        self,
        trades: List[Trade],
        start_date: datetime,
        end_date: datetime,
    ) -> TaxLiability:
        """
        Calculate tax liability for a period.

        Args:
            trades: List of trades in period
            start_date: Period start
            end_date: Period end

        Returns:
            Aggregated TaxLiability for the period
        """
        # Filter trades by date
        period_trades = [t for t in trades if t.exit_date and start_date <= t.exit_date <= end_date]

        # Calculate totals
        total_short_gains = Decimal("0")
        total_long_gains = Decimal("0")

        for trade in period_trades:
            profit = max(trade.get_net_pnl().amount, Decimal("0"))
            if self._is_long_term(trade):
                total_long_gains += profit
            else:
                total_short_gains += profit

        # Calculate taxes
        short_tax = total_short_gains * self._tax_residence.capital_gains_rate_short
        long_tax = total_long_gains * self._tax_residence.capital_gains_rate_long

        total_gross = total_short_gains + total_long_gains
        total_tax = short_tax + long_tax
        total_net = total_gross - total_tax

        return TaxLiability(
            gross_profit=total_gross,
            taxable_profit=total_gross,
            tax_rate=self._tax_residence.capital_gains_rate_short,  # Effective rate
            tax_amount=total_tax,
            net_profit=total_net,
            short_term_gains=total_short_gains,
            long_term_gains=total_long_gains,
            short_term_tax=short_tax,
            long_term_tax=long_tax,
        )

    def calculate_dividend_tax(
        self,
        dividend_amount: Decimal,
        source_region: str = "domestic",
    ) -> Decimal:
        """
        Calculate tax on dividends.

        Args:
            dividend_amount: Gross dividend amount
            source_region: Source region (domestic, eu, us)

        Returns:
            Tax amount
        """
        withholding_rate = self._tax_residence.get_withholding_tax_rate(source_region)
        return dividend_amount * withholding_rate

    def create_tax_lots_from_position(
        self,
        position: Position,
    ) -> List[TaxLot]:
        """
        Create tax lots from a position.

        Args:
            position: Position to create lots from

        Returns:
            List of TaxLot objects
        """
        is_long_term = (datetime.utcnow() - position.entry_date).days >= self.LONG_TERM_HOLDING_DAYS

        return [
            TaxLot(
                symbol=position.symbol,
                quantity=position.quantity,
                cost_basis=position.get_cost_basis().amount,
                acquisition_date=position.entry_date,
                is_long_term=is_long_term,
            )
        ]

    def optimize_tax_loss_harvesting(
        self,
        open_positions: List[Position],
        current_prices: Dict[str, Decimal],
    ) -> List[str]:
        """
        Identify positions for tax-loss harvesting.

        Args:
            open_positions: List of open positions
            current_prices: Current prices by symbol

        Returns:
            List of symbols recommended for harvesting
        """
        harvest_candidates = []

        for position in open_positions:
            if position.symbol not in current_prices:
                continue

            # Check if position has unrealized loss
            unrealized_pnl = position.get_unrealized_pnl().amount

            if unrealized_pnl < 0:
                # Check if wash sale rule applies
                if self._tax_residence.applies_wash_sale_rule:
                    # Check if position is held long enough to avoid wash sale
                    holding_days = position.get_age_days()
                    if holding_days >= 30:  # 30-day wash sale period
                        harvest_candidates.append(position.symbol)
                else:
                    # No wash sale restriction, recommend harvest
                    harvest_candidates.append(position.symbol)

        return harvest_candidates

    def estimate_year_end_tax(
        self,
        year_trades: List[Trade],
        open_positions: List[Position],
        current_prices: Dict[str, Decimal],
    ) -> TaxLiability:
        """
        Estimate year-end tax liability including unrealized gains.

        Args:
            year_trades: Trades executed in the year
            open_positions: Currently open positions
            current_prices: Current prices for open positions

        Returns:
            Estimated tax liability
        """
        # Realized gains/losses from closed trades
        realized_tax = self.calculate_period_tax(
            year_trades,
            datetime(year_trades[0].exit_date.year, 1, 1) if year_trades else datetime.utcnow(),
            datetime.utcnow(),
        )

        # Add unrealized gains from open positions
        unrealized_gains = Decimal("0")
        for position in open_positions:
            if position.symbol in current_prices:
                unrealized = position.get_unrealized_pnl().amount
                if unrealized > 0:
                    # Assume short-term rate for conservative estimate
                    unrealized_gains += unrealized

        unrealized_tax = unrealized_gains * self._tax_residence.capital_gains_rate_short

        total_tax = realized_tax.tax_amount + unrealized_tax

        return TaxLiability(
            gross_profit=realized_tax.gross_profit + unrealized_gains,
            taxable_profit=realized_tax.taxable_profit + unrealized_gains,
            tax_rate=realized_tax.tax_rate,
            tax_amount=total_tax,
            net_profit=realized_tax.net_profit - unrealized_tax,
            short_term_gains=realized_tax.short_term_gains,
            long_term_gains=realized_tax.long_term_gains,
            short_term_tax=realized_tax.short_term_tax,
            long_term_tax=realized_tax.long_term_tax,
        )

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    def _is_long_term(self, trade: Trade) -> bool:
        """Check if trade qualifies for long-term treatment."""
        if trade.exit_date is None:
            return False

        holding_days = (trade.exit_date - trade.entry_date).days
        return holding_days >= self.LONG_TERM_HOLDING_DAYS
