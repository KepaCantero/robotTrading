"""
Dividend Handler

Handles dividend payments and reinvestment in backtesting:
- Track dividend payments
- Calculate dividend yield
- Reinvest dividends (DRIP)
- Handle special dividends
- Tax treatment of dividends

Reference: Rule 11-lopez-de-prado-advances-in-financial-machine-learning.md
- Dividends significantly affect total return
- DRIP can compound returns significantly
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple


class DividendType(str, Enum):
    """Type of dividend."""

    REGULAR = "regular"  # Regular quarterly dividend
    SPECIAL = "special"  # One-time special dividend
    FINAL = "final"  # Final dividend before liquidation
    INTERIM = "interim"  # Interim dividend
    STOCK = "stock"  # Stock dividend


class DividendReinvestmentStrategy(str, Enum):
    """Dividend reinvestment strategy."""

    REINVEST = "reinvest"  # Reinvest all dividends
    CASH = "cash"  # Keep dividends as cash
    THRESHOLD = "threshold"  # Reinvest only above threshold
    MANUAL = "manual"  # Manual reinvestment


@dataclass
class DividendPayment:
    """Record of a dividend payment."""

    symbol: str
    ex_date: date
    record_date: date
    payable_date: date
    amount_per_share: Decimal
    dividend_type: DividendType
    frequency: Optional[int] = None  # Number of times per year

    @property
    def annualized_amount(self) -> Decimal:
        """Calculate annualized dividend amount."""
        if self.frequency:
            return self.amount_per_share * Decimal(str(self.frequency))
        # Assume quarterly if not specified
        return self.amount_per_share * Decimal("4")


@dataclass
class DividendReinvestment:
    """Record of dividend reinvestment."""

    symbol: str
    reinvestment_date: date
    dividend_amount: Decimal
    shares_purchased: Decimal
    price_per_share: Decimal
    fractional_shares: bool = True


class DividendHandler:
    """
    Handles dividend payments and reinvestment.

    Features:
    - Track dividend announcements
    - Calculate dividend yield
    - Reinvest dividends (DRIP)
    - Handle special dividends
    - Tax withholding on dividends
    """

    def __init__(
        self,
        reinvestment_strategy: DividendReinvestmentStrategy = DividendReinvestmentStrategy.REINVEST,
        reinvestment_threshold: Optional[Decimal] = None,
        fractional_shares: bool = True,
        tax_withholding_rate: float = 0.0,  # Varies by jurisdiction
    ):
        """
        Initialize dividend handler.

        Args:
            reinvestment_strategy: How to handle dividends
            reinvestment_threshold: Minimum amount for reinvestment
            fractional_shares: Allow fractional share purchases
            tax_withholding_rate: Tax withholding rate on dividends
        """
        if reinvestment_threshold is None:
            reinvestment_threshold = Decimal("10")
        self._strategy = reinvestment_strategy
        self._threshold = reinvestment_threshold
        self._fractional_shares = fractional_shares
        self._tax_rate = Decimal(str(tax_withholding_rate))

        self._dividends: Dict[str, List[DividendPayment]] = {}
        self._reinvestments: List[DividendReinvestment] = []

    def add_dividend(self, dividend: DividendPayment) -> None:
        """
        Add a dividend payment.

        Args:
            dividend: Dividend to add
        """
        if dividend.symbol not in self._dividends:
            self._dividends[dividend.symbol] = []
        self._dividends[dividend.symbol].append(dividend)

    def get_dividend(
        self,
        symbol: str,
        as_of_date: date,
    ) -> Optional[DividendPayment]:
        """
        Get most recent dividend for symbol before date.

        Args:
            symbol: Symbol to check
            as_of_date: Date to check

        Returns:
            Most recent DividendPayment or None
        """
        dividends = self._dividends.get(symbol, [])
        # Filter dividends before as_of_date
        past_dividends = [d for d in dividends if d.ex_date <= as_of_date]

        if not past_dividends:
            return None

        return sorted(past_dividends, key=lambda d: d.ex_date)[-1]

    def calculate_dividend_yield(
        self,
        symbol: str,
        current_price: Decimal,
        as_of_date: date,
    ) -> float:
        """
        Calculate dividend yield.

        Args:
            symbol: Symbol
            current_price: Current price
            as_of_date: Date to calculate as of

        Returns:
            Dividend yield as percentage (e.g., 0.04 for 4%)
        """
        dividend = self.get_dividend(symbol, as_of_date)
        if not dividend or current_price == 0:
            return 0.0

        annualized = float(dividend.annualized_amount)
        price = float(current_price)

        return annualized / price

    def process_dividend_payment(
        self,
        symbol: str,
        quantity: Decimal,
        payment_date: date,
        current_price: Decimal,
    ) -> Tuple[Decimal, Optional[DividendReinvestment]]:
        """
        Process dividend payment for a position.

        Args:
            symbol: Symbol
            quantity: Number of shares owned
            payment_date: Payment date
            current_price: Current share price

        Returns:
            Tuple of (dividend_amount, reinvestment_info)
        """
        # Find dividend payable on this date
        dividends = self._dividends.get(symbol, [])
        payable_dividends = [d for d in dividends if d.payable_date == payment_date]

        if not payable_dividends:
            return Decimal("0"), None

        # Sum all dividends payable
        gross_dividend = sum(d.amount_per_share * quantity for d in payable_dividends)

        # Apply tax withholding
        net_dividend = gross_dividend * (Decimal("1") - self._tax_rate)

        # Handle based on strategy
        reinvestment = None

        if self._strategy == DividendReinvestmentStrategy.REINVEST or self._strategy == DividendReinvestmentStrategy.THRESHOLD and net_dividend >= self._threshold:
            reinvestment = self._reinvest_dividend(
                symbol, net_dividend, payment_date, current_price
            )

        return net_dividend, reinvestment

    def _reinvest_dividend(
        self,
        symbol: str,
        dividend_amount: Decimal,
        reinvestment_date: date,
        price: Decimal,
    ) -> DividendReinvestment:
        """Reinvest dividend in shares."""
        if price == 0:
            # Can't reinvest at zero price
            return DividendReinvestment(
                symbol=symbol,
                reinvestment_date=reinvestment_date,
                dividend_amount=dividend_amount,
                shares_purchased=Decimal("0"),
                price_per_share=price,
                fractional_shares=False,
            )

        if self._fractional_shares:
            shares = dividend_amount / price
        else:
            shares = dividend_amount // price

        reinvestment = DividendReinvestment(
            symbol=symbol,
            reinvestment_date=reinvestment_date,
            dividend_amount=dividend_amount,
            shares_purchased=shares,
            price_per_share=price,
            fractional_shares=self._fractional_shares,
        )

        self._reinvestments.append(reinvestment)
        return reinvestment

    def calculate_annual_dividend_income(
        self,
        positions: Dict[str, Decimal],
        prices: Dict[str, Decimal],
        as_of_date: date,
    ) -> Decimal:
        """
        Calculate expected annual dividend income from positions.

        Args:
            positions: Dictionary of symbol -> quantity
            prices: Dictionary of symbol -> current price
            as_of_date: Date to calculate as of

        Returns:
            Expected annual dividend income
        """
        total_income = Decimal("0")

        for symbol, quantity in positions.items():
            dividend = self.get_dividend(symbol, as_of_date)
            if dividend:
                annual_dividend = dividend.annualized_amount * quantity
                total_income += annual_dividend

        return total_income

    def calculate_portfolio_dividend_yield(
        self,
        positions: Dict[str, Decimal],
        prices: Dict[str, Decimal],
        as_of_date: date,
    ) -> float:
        """
        Calculate portfolio dividend yield.

        Args:
            positions: Dictionary of symbol -> quantity
            prices: Dictionary of symbol -> current price
            as_of_date: Date to calculate as of

        Returns:
            Portfolio dividend yield as percentage
        """
        total_value = Decimal("0")
        total_annual_dividends = Decimal("0")

        for symbol, quantity in positions.items():
            price = prices.get(symbol, Decimal("0"))
            value = quantity * price
            total_value += value

            dividend = self.get_dividend(symbol, as_of_date)
            if dividend:
                total_annual_dividends += dividend.annualized_amount * quantity

        if total_value == 0:
            return 0.0

        return float(total_annual_dividends / total_value)

    def estimate_next_dividend_date(
        self,
        symbol: str,
        as_of_date: date,
    ) -> Optional[date]:
        """
        Estimate next dividend date for symbol.

        Args:
            symbol: Symbol
            as_of_date: Current date

        Returns:
            Estimated next ex-dividend date
        """
        dividends = self._dividends.get(symbol, [])
        if not dividends:
            return None

        # Get most recent dividend
        past_dividends = [d for d in dividends if d.ex_date <= as_of_date]
        if not past_dividends:
            return None

        last_dividend = sorted(past_dividends, key=lambda d: d.ex_date)[-1]

        # Estimate based on frequency
        if last_dividend.frequency:
            days_between = 365 // last_dividend.frequency
        else:
            days_between = 91  # Quarterly default

        return last_dividend.ex_date + timedelta(days=days_between)

    def get_dividend_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[DividendPayment]:
        """
        Get dividend history for symbol in date range.

        Args:
            symbol: Symbol
            start_date: Start date
            end_date: End date

        Returns:
            List of DividendPayment in range
        """
        dividends = self._dividends.get(symbol, [])
        return [d for d in dividends if start_date <= d.ex_date <= end_date]

    def calculate_dividend_growth_rate(
        self,
        symbol: str,
        years: int = 5,
    ) -> float:
        """
        Calculate dividend growth rate over period.

        Args:
            symbol: Symbol
            years: Number of years to look back

        Returns:
            Annualized dividend growth rate
        """
        dividends = self._dividends.get(symbol, [])
        if len(dividends) < 8:  # Need at least 2 years of quarterly data
            return 0.0

        # Sort by date
        sorted_dividends = sorted(dividends, key=lambda d: d.ex_date)

        # Get oldest and newest dividend amounts
        oldest = sorted_dividends[0].amount_per_share
        newest = sorted_dividends[-1].amount_per_share

        if oldest == 0:
            return 0.0

        # Calculate periods (quarters)
        periods = min(len(sorted_dividends) // 4, years * 4)

        if periods == 0:
            return 0.0

        # Calculate CAGR
        growth_rate = (float(newest / oldest) ** (1 / periods)) - 1

        # Annualize
        return growth_rate * 4

    def get_total_reinvested(self) -> Decimal:
        """Get total amount of dividends reinvested."""
        return sum((r.dividend_amount for r in self._reinvestments), Decimal("0"))

    def get_total_shares_from_reinvestment(self, symbol: str) -> Decimal:
        """Get total shares acquired from dividend reinvestment."""
        return sum(
            (r.shares_purchased for r in self._reinvestments if r.symbol == symbol), Decimal("0")
        )
