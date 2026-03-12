"""
Equity Curve Tracker service for backtesting.

This service is responsible for tracking portfolio value over time
and calculating drawdown metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple

from app.backtesting.services.position_manager import PositionManager

logger = logging.getLogger(__name__)


class EquityCurveTracker:
    """
    Track and return equity curve data.

    This service handles:
    - Equity curve state management
    - Peak equity tracking
    - Drawdown calculation
    - Portfolio value calculation with unrealized P&L

    Dependencies:
    - PositionManager: To get current positions
    - last_known_prices: To get current prices for unrealized P&L
    """

    def __init__(
        self,
        position_manager: PositionManager,
        initial_capital: Decimal,
    ):
        """
        Initialize the Equity Curve Tracker.

        Args:
            position_manager: PositionManager instance
            initial_capital: Initial capital for backtest
        """
        self.position_manager = position_manager
        self.initial_capital = initial_capital

        # State
        self.equity_curve: List[Tuple[datetime, Decimal]] = []
        self.max_drawdown = Decimal("0")
        self.peak_equity = initial_capital

    def update_equity_curve(
        self,
        timestamp: datetime,
        capital: Decimal,
        last_known_prices: Dict[str, Decimal],
    ) -> None:
        """
        Update equity curve with current portfolio value.

        Args:
            timestamp: Current timestamp
            capital: Current cash capital
            last_known_prices: Last known prices for each symbol
        """
        # Calculate current portfolio value
        portfolio_value = capital

        # Add unrealized P&L from open positions using actual tracked prices
        positions = self.position_manager.get_all_positions()

        for symbol, quantity in positions.items():
            if quantity > 0:
                # Use the last known price for this symbol
                if symbol in last_known_prices:
                    current_price = last_known_prices[symbol]
                    portfolio_value += quantity * current_price
                else:
                    # Fallback: try to get price from trades or raise error
                    logger.warning(
                        f"No tracked price for {symbol}, using entry price for equity curve"
                    )
                    # This is a fallback that should rarely happen
                    price = self._get_entry_price_fallback(symbol, last_known_prices)
                    portfolio_value += quantity * price

        self.equity_curve.append((timestamp, portfolio_value))

        # Update drawdown
        self._update_drawdown(portfolio_value)

    def _update_drawdown(self, portfolio_value: Decimal) -> None:
        """
        Update drawdown metrics based on current portfolio value.

        Args:
            portfolio_value: Current portfolio value
        """
        if portfolio_value > self.peak_equity:
            self.peak_equity = portfolio_value

        # Calculate drawdown as negative absolute value (not percentage)
        # max_drawdown must be <= 0 per Pydantic validation
        if self.peak_equity > 0:
            current_drawdown = portfolio_value - self.peak_equity  # Negative or zero
            if current_drawdown < self.max_drawdown:
                self.max_drawdown = current_drawdown

    def get_equity_curve(self) -> List[Tuple[datetime, Decimal]]:
        """
        Get the equity curve.

        Returns:
            List of (timestamp, portfolio_value) tuples
        """
        return list(self.equity_curve)

    def get_max_drawdown(self) -> Decimal:
        """
        Get maximum drawdown.

        Returns:
            Maximum drawdown (negative value)
        """
        return self.max_drawdown

    def get_max_drawdown_percentage(self) -> Decimal:
        """
        Get maximum drawdown as percentage.

        Returns:
            Maximum drawdown percentage (negative value)
        """
        if self.peak_equity > 0:
            return min(
                Decimal("0"),
                (self.max_drawdown / self.peak_equity * 100),
            )
        return Decimal("0")

    def get_peak_equity(self) -> Decimal:
        """
        Get peak equity value.

        Returns:
            Peak equity value
        """
        return self.peak_equity

    def get_current_portfolio_value(
        self,
        capital: Decimal,
        last_known_prices: Dict[str, Decimal],
    ) -> Decimal:
        """
        Calculate current portfolio value including unrealized P&L.

        Args:
            capital: Current cash capital
            last_known_prices: Last known prices for each symbol

        Returns:
            Total portfolio value
        """
        portfolio_value = capital

        positions = self.position_manager.get_all_positions()

        for symbol, quantity in positions.items():
            if quantity > 0:
                if symbol in last_known_prices:
                    current_price = last_known_prices[symbol]
                    portfolio_value += quantity * current_price

        return portfolio_value

    def reset(self) -> None:
        """Reset equity curve state."""
        self.equity_curve.clear()
        self.max_drawdown = Decimal("0")
        self.peak_equity = self.initial_capital

    def _get_entry_price_fallback(
        self, symbol: str, last_known_prices: Dict[str, Decimal]
    ) -> Decimal:
        """
        Get fallback entry price for a symbol (rarely used).

        Args:
            symbol: Trading symbol
            last_known_prices: Dictionary of last known prices

        Returns:
            Fallback price from last_known_prices if available

        Raises:
            ValueError: If no price is available for the symbol
        """
        # Check if we have any price in last_known_prices for this symbol
        if symbol in last_known_prices and last_known_prices[symbol] > 0:
            logger.warning(
                f"Using last known price for {symbol} as fallback: {last_known_prices[symbol]}"
            )
            return last_known_prices[symbol]

        # No price available - raise exception to prevent incorrect calculations
        logger.error(
            f"CRITICAL: No price available for {symbol} in equity curve calculation. "
            f"This indicates a bug in price tracking."
        )
        raise ValueError(f"No entry price found for {symbol} and no last known price available")

    def calculate_returns(self) -> List[Decimal]:
        """
        Calculate period-over-period returns from equity curve.

        Returns:
            List of returns as decimals
        """
        if len(self.equity_curve) < 2:
            return []

        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_value = self.equity_curve[i - 1][1]
            curr_value = self.equity_curve[i][1]

            if prev_value > 0:
                ret = (curr_value - prev_value) / prev_value
                returns.append(ret)

        return returns

    def get_total_return(self) -> Decimal:
        """
        Calculate total return from start to end.

        Returns:
            Total return as percentage
        """
        if not self.equity_curve:
            return Decimal("0")

        start_value = self.equity_curve[0][1]
        end_value = self.equity_curve[-1][1]

        if start_value == 0:
            return Decimal("0")

        return ((end_value - start_value) / start_value) * 100
