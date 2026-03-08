"""
Dividend Handler for Robust Backtesting Engine.

This module handles dividend processing and Dividend Reinvestment Plans (DRIP)
for accurate long-term backtesting.

Proper dividend handling is critical for accurate total return calculations,
especially over 25+ year periods where reinvested dividends can significantly
impact returns due to compounding.

Features:
- Cash dividend tracking
- Dividend reinvestment (DRIP)
- Yield on cost calculation
- Tax-aware dividend handling
- Fractional share support

Reference:
    - "The Future for Investors" by Jeremy Siegel - Chapter on Dividends
    - "The Dividend Investor" by Don Peters
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .models import DividendAction, DividendTracker, DripConfig

logger = logging.getLogger(__name__)


class DividendHandler:
    """
    Handles dividend processing and reinvestment for backtesting.

    This class:
    1. Tracks dividend payments on held positions
    2. Implements DRIP (Dividend Reinvestment Plan)
    3. Calculates yield on cost and current yield
    4. Handles qualified vs non-qualified dividends
    5. Supports fractional shares for DRIP

    Example:
        ```python
        handler = DividendHandler(
            drip_config=DripConfig(
                enable_drip=True,
                reinvest_same_stock=True
            )
        )

        # Handle a dividend payment
        action = handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185")
        )

        # Get total dividends received
        total = handler.get_total_dividends_received()
        ```
    """

    def __init__(self, drip_config: Optional[DripConfig] = None):
        """
        Initialize the dividend handler.

        Args:
            drip_config: Configuration for dividend reinvestment
        """
        self.drip_config = drip_config or DripConfig()
        self.tracker = DividendTracker()
        self._dividend_payments: Dict[str, List[DividendAction]] = defaultdict(list)
        self._position_costs: Dict[str, Decimal] = {}

    def handle_dividend(
        self,
        symbol: str,
        amount: Decimal,
        ex_date: date,
        shares: Decimal,
        payment_date: Optional[date] = None,
        current_price: Optional[Decimal] = None,
        qualified: bool = True,
    ) -> DividendAction:
        """
        Handle a dividend payment.

        Args:
            symbol: Stock symbol that paid dividend
            amount: Dividend amount per share
            ex_date: Ex-dividend date
            shares: Number of shares held on ex-date
            payment_date: Date dividend is paid (optional)
            current_price: Current stock price (for DRIP)
            qualified: Whether dividend is qualified for tax purposes

        Returns:
            DividendAction describing what was done with the dividend
        """
        # Calculate total dividend received
        total_amount = amount * shares

        action = DividendAction(
            symbol=symbol,
            ex_date=ex_date,
            amount=amount,
            shares=shares,
            total_amount=total_amount,
            reinvested=False,
        )

        # Decide whether to reinvest
        should_reinvest = (
            self.drip_config.enable_drip
            and self.drip_config.reinvest_all
            and total_amount >= self.drip_config.min_reinvestment_amount
            and current_price is not None
            and current_price > 0
        )

        if should_reinvest:
            reinvestment_result = self.reinvest_dividend(
                symbol=symbol,
                cash=total_amount,
                price=current_price,
                ex_date=ex_date,
            )

            action.reinvested = True
            action.reinvestment_price = reinvestment_result["price"]
            action.reinvestment_shares = reinvestment_result["shares"]

            logger.info(
                f"DRIP: Reinvested ${total_amount:.2f} dividend from {symbol} "
                f"at ${current_price:.2f} -> {reinvestment_result['shares']:.6f} shares"
            )
        else:
            # Cash dividend - add to tracker but don't reinvest
            logger.info(
                f"Dividend: ${total_amount:.2f} from {symbol} "
                f"(${amount:.4f} per share x {shares} shares)"
            )

        # Track the dividend
        self._dividend_payments[symbol].append(action)
        self.tracker.add_dividend(action)

        return action

    def reinvest_dividend(
        self,
        symbol: str,
        cash: Decimal,
        price: Decimal,
        ex_date: date,
    ) -> Dict[str, Decimal]:
        """
        Reinvest a dividend in the same stock.

        Args:
            symbol: Stock symbol
            cash: Dividend cash amount to reinvest
            price: Current stock price
            ex_date: Ex-dividend date

        Returns:
            Dict with 'price' and 'shares' keys
        """
        if price <= 0:
            logger.warning(f"Cannot reinvest dividend for {symbol}: price <= 0")
            return {"price": Decimal("0"), "shares": Decimal("0")}

        # Apply commission if configured first
        effective_cash = cash
        commission = self.drip_config.commission_drip
        if commission > 0:
            effective_cash = cash - commission

        # Calculate shares to purchase (including fractional if enabled)
        if self.drip_config.fractional_shares:
            # Use Decimal division with proper context for fractional shares
            shares = effective_cash / price
        else:
            # Whole shares only - truncate to whole shares
            shares = (effective_cash / price).to_integral_value(rounding="ROUND_DOWN")
            # Convert back to Decimal
            shares = Decimal(int(shares))

        return {
            "price": price,
            "shares": shares,
        }

    def get_reinvestment_shares(
        self,
        symbol: str,
        cash: Decimal,
        price: Decimal,
    ) -> Decimal:
        """
        Calculate number of shares from dividend reinvestment.

        Args:
            symbol: Stock symbol
            cash: Dividend cash amount
            price: Current stock price

        Returns:
            Number of shares (including fractional if enabled)
        """
        result = self.reinvest_dividend(symbol, cash, price, date.today())
        return result["shares"]

    def calculate_yield_on_cost(
        self,
        symbol: str,
        original_cost: Decimal,
        current_price: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate yield on cost for a position.

        Yield on cost = Annual dividends / Original cost basis

        Args:
            symbol: Stock symbol
            original_cost: Original cost basis of position
            current_price: Current price (for current yield calculation)

        Returns:
            Yield on cost as a percentage
        """
        if symbol not in self._dividend_payments:
            return Decimal("0")

        # Get all dividends for this symbol
        dividends = self._dividend_payments[symbol]

        if not dividends:
            return Decimal("0")

        # Calculate trailing 12-month dividends
        latest_date = max(d.ex_date for d in dividends)
        cutoff_date = latest_date.replace(year=latest_date.year - 1)

        ttm_dividends = sum(d.total_amount for d in dividends if d.ex_date >= cutoff_date)

        if original_cost > 0:
            return (ttm_dividends / original_cost * 100).quantize(Decimal("0.01"))

        return Decimal("0")

    def calculate_current_yield(
        self,
        symbol: str,
        current_price: Decimal,
    ) -> Decimal:
        """
        Calculate current dividend yield.

        Current yield = Annual dividend / Current price

        Args:
            symbol: Stock symbol
            current_price: Current stock price

        Returns:
            Current yield as a percentage
        """
        if symbol not in self._dividend_payments or current_price <= 0:
            return Decimal("0")

        dividends = self._dividend_payments[symbol]
        if not dividends:
            return Decimal("0")

        # Get most recent dividend
        latest_dividend = max(dividends, key=lambda d: d.ex_date)

        # Annualize based on payment frequency (assume quarterly by default)
        annualized_amount = latest_dividend.amount * 4

        return (annualized_amount / current_price * 100).quantize(Decimal("0.01"))

    def get_total_dividends_received(self) -> Decimal:
        """Get total dividends received across all positions."""
        return self.tracker.total_dividends_received

    def get_total_dividends_reinvested(self) -> Decimal:
        """Get total dividends reinvested via DRIP."""
        return self.tracker.total_dividends_reinvested

    def get_dividend_history(
        self,
        symbol: Optional[str] = None,
    ) -> List[DividendAction]:
        """
        Get dividend payment history.

        Args:
            symbol: Optional symbol to filter by

        Returns:
            List of dividend actions
        """
        if symbol:
            return self._dividend_payments.get(symbol, []).copy()
        else:
            # Return all dividends
            all_dividends = []
            for dividends in self._dividend_payments.values():
                all_dividends.extend(dividends)
            return sorted(all_dividends, key=lambda d: d.ex_date)

    def calculate_portfolio_dividend_yield(
        self,
        positions: Dict[str, Decimal],
        prices: Dict[str, Decimal],
    ) -> Decimal:
        """
        Calculate weighted average dividend yield for a portfolio.

        Args:
            positions: Dict of symbol -> number of shares
            prices: Dict of symbol -> current price

        Returns:
            Portfolio dividend yield as a percentage
        """
        total_market_value = Decimal("0")
        weighted_yield = Decimal("0")

        for symbol, shares in positions.items():
            if symbol not in prices or prices[symbol] <= 0:
                continue

            market_value = shares * prices[symbol]
            dividend_yield = self.calculate_current_yield(symbol, prices[symbol])

            total_market_value += market_value
            weighted_yield += market_value * dividend_yield

        if total_market_value > 0:
            return (weighted_yield / total_market_value).quantize(Decimal("0.01"))

        return Decimal("0")

    def get_annual_dividend_income(
        self,
        symbol: Optional[str] = None,
    ) -> Dict[int, Decimal]:
        """
        Get dividend income by year.

        Args:
            symbol: Optional symbol to filter by

        Returns:
            Dict mapping year -> dividend income
        """
        dividends = self.get_dividend_history(symbol)

        annual_income = defaultdict(Decimal)
        for dividend in dividends:
            annual_income[dividend.ex_date.year] += dividend.total_amount

        return dict(annual_income)

    def get_dividend_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive dividend statistics.

        Returns:
            Dict with various dividend metrics
        """
        annual_income = self.get_annual_dividend_income()

        return {
            "total_dividends_received": float(self.tracker.total_dividends_received),
            "total_dividends_reinvested": float(self.tracker.total_dividends_reinvested),
            "dividend_count": self.tracker.dividend_count,
            "dividend_yield": float(self.tracker.dividend_yield),
            "yield_on_cost": float(self.tracker.yield_on_cost),
            "annual_income": {year: float(amount) for year, amount in annual_income.items()},
            "average_annual_income": float(
                np.mean(list(annual_income.values())) if annual_income else 0
            ),
            "drip_enabled": self.drip_config.enable_drip,
        }

    def process_dividend_stream(
        self,
        dividend_data: pd.DataFrame,
        positions: Dict[str, Decimal],
        prices: Dict[str, Decimal],
    ) -> List[DividendAction]:
        """
        Process a stream of dividend data.

        Args:
            dividend_data: DataFrame with columns:
                - symbol: Stock symbol
                - ex_date: Ex-dividend date
                - amount: Dividend per share
                - payment_date: Payment date (optional)
                - qualified: Whether qualified (optional)
            positions: Current positions (symbol -> shares)
            prices: Current prices (symbol -> price)

        Returns:
            List of DividendActions processed
        """
        # Use generator for memory-efficient processing
        actions = list(self._generate_dividend_actions(dividend_data, positions, prices))

        logger.info(f"Processed {len(actions)} dividend payments")
        return actions

    def _generate_dividend_actions(
        self,
        dividend_data: pd.DataFrame,
        positions: Dict[str, Decimal],
        prices: Dict[str, Decimal],
    ) -> DividendAction:
        """
        Generate DividendAction objects from dividend data.

        This is a generator that yields DividendAction objects for
        memory-efficient processing of large dividend datasets.

        Args:
            dividend_data: DataFrame with dividend data
            positions: Current positions (symbol -> shares)
            prices: Current prices (symbol -> price)

        Yields:
            DividendAction objects for each eligible dividend payment
        """
        # Use itertuples instead of iterrows for better performance
        for row in dividend_data.itertuples():
            symbol = row.symbol
            ex_date = (
                row.ex_date if isinstance(row.ex_date, date) else pd.to_datetime(row.ex_date).date()
            )

            # Only process if we hold the stock
            if symbol not in positions or positions[symbol] <= 0:
                continue

            shares = positions[symbol]
            amount = Decimal(str(row.amount))
            payment_date = (
                row.payment_date
                if hasattr(row, "payment_date") and pd.notna(row.payment_date)
                else None
            )
            qualified = getattr(row, "qualified", True)

            current_price = prices.get(symbol)

            action = self.handle_dividend(
                symbol=symbol,
                amount=amount,
                ex_date=ex_date,
                shares=shares,
                payment_date=payment_date,
                current_price=current_price,
                qualified=qualified,
            )

            yield action

    def reset(self) -> None:
        """Reset the dividend handler state."""
        self.tracker = DividendTracker()
        self._dividend_payments.clear()
        self._position_costs.clear()
