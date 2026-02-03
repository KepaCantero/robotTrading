"""
Exit Condition Monitor service for backtesting.

This service is responsible for monitoring stop-loss and take-profit
conditions and triggering position closures when they are hit.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from app.backtesting.models import BacktestConfig, Trade, TradeStatus
from app.backtesting.services.position_manager import PositionManager

logger = logging.getLogger(__name__)


class ExitConditionMonitor:
    """
    Monitor and trigger stop-loss and take-profit exits.

    This service handles:
    - Stop-loss monitoring
    - Take-profit monitoring
    - Intraday extreme price checks (high/low)
    - Pessimistic execution (SL priority when both hit)

    Dependencies:
    - config: Backtest configuration for SL/TP percentages
    - PositionManager: To check current positions
    """

    def __init__(
        self,
        config: BacktestConfig,
        position_manager: PositionManager,
        apply_slippage_func: Callable[[Decimal, bool, Optional[Decimal]], Decimal],
    ):
        """
        Initialize the Exit Condition Monitor.

        Args:
            config: Backtest configuration
            position_manager: PositionManager instance
            apply_slippage_func: Function to apply slippage to prices
        """
        self.config = config
        self.position_manager = position_manager
        self.apply_slippage = apply_slippage_func

    def check_exit_conditions(
        self,
        market_data: Any,
        trades: List[Trade],
        close_position_func: Callable[[str, Any, str, Decimal], None],
    ) -> bool:
        """
        Check for stop loss and take profit conditions.

        CRITICAL FIX: Checks both close price AND intraday extremes (low/high).
        This ensures stop-loss and take-profit trigger correctly even if the close
        price doesn't reflect the intraday extremes.

        PESSIMISTIC EXECUTION: When both SL and TP are hit in the same bar,
        stop-loss takes priority (worst-case scenario for risk management).

        Args:
            market_data: Current market data
            trades: List of all trades
            close_position_func: Function to close positions

        Returns:
            True if a position was closed, False otherwise
        """
        from app.backtesting.engine import get_price

        if not self.position_manager.has_open_position(market_data.symbol):
            return False

        current_position = self.position_manager.get_position(market_data.symbol)
        if current_position <= 0:
            return False

        # Find the most recent buy trade for this symbol
        recent_trades = [
            t
            for t in trades
            if t.symbol == market_data.symbol
            and t.side == "buy"
            and t.status == TradeStatus.OPEN
        ]

        if not recent_trades:
            return False

        # Use the most recent trade's entry price
        entry_price = recent_trades[-1].entry_price

        # Calculate stop loss and take profit prices
        stop_loss_price = None
        take_profit_price = None
        stop_loss_triggered = False
        take_profit_triggered = False

        # Check stop loss
        if self.config.stop_loss_percentage:
            stop_loss_price = entry_price * (
                Decimal("1") - self.config.stop_loss_percentage / Decimal("100")
            )

        # Check take profit
        if self.config.take_profit_percentage:
            take_profit_price = entry_price * (
                Decimal("1") + self.config.take_profit_percentage / Decimal("100")
            )

        # Get close price
        close_price = get_price(market_data)

        # Check if stop loss was hit using low price (intraday low)
        if stop_loss_price is not None:
            if hasattr(market_data, "low") and market_data.low is not None:
                # Use intraday low for stop-loss check
                if market_data.low <= stop_loss_price:
                    stop_loss_triggered = True
            elif close_price <= stop_loss_price:
                # Fallback to close price if low not available
                stop_loss_triggered = True

        # Check if take profit was hit using high price (intraday high)
        if take_profit_price is not None:
            if hasattr(market_data, "high") and market_data.high is not None:
                # Use intraday high for take-profit check
                if market_data.high >= take_profit_price:
                    take_profit_triggered = True
            elif close_price >= take_profit_price:
                # Fallback to close price if high not available
                take_profit_triggered = True

        # PESSIMISTIC EXECUTION: If both triggered, prioritize stop-loss
        if stop_loss_triggered and take_profit_triggered:
            # Both hit - use stop-loss price for execution (pessimistic)
            exit_price = (
                stop_loss_price
                if hasattr(market_data, "low") and market_data.low is not None
                else close_price
            )
            close_position_func(
                market_data.symbol, market_data.timestamp, "stop_loss", exit_price
            )
            return True
        elif stop_loss_triggered:
            # Only stop-loss hit
            exit_price = (
                stop_loss_price
                if hasattr(market_data, "low") and market_data.low is not None
                else close_price
            )
            close_position_func(market_data.symbol, market_data.timestamp, "stop_loss", exit_price)
            return True
        elif take_profit_triggered:
            # Only take-profit hit
            exit_price = (
                take_profit_price
                if hasattr(market_data, "high") and market_data.high is not None
                else close_price
            )
            close_position_func(
                market_data.symbol, market_data.timestamp, "take_profit", exit_price
            )
            return True

        return False

    def check_all_symbols_exit_conditions(
        self,
        market_data: Any,
        trades: List[Trade],
        close_position_func: Callable[[str, Any, str, Decimal], None],
    ) -> int:
        """
        Check exit conditions for all symbols with open positions.

        Args:
            market_data: Current market data
            trades: List of all trades
            close_position_func: Function to close positions

        Returns:
            Number of positions closed
        """
        # This method is called when market_data is for a specific symbol
        # The main backtest loop will call check_exit_conditions for each symbol
        return 0

    def calculate_stop_loss_price(self, entry_price: Decimal) -> Optional[Decimal]:
        """
        Calculate stop-loss price from entry price.

        Args:
            entry_price: Entry price

        Returns:
            Stop-loss price or None if not configured
        """
        if self.config.stop_loss_percentage is None:
            return None

        return entry_price * (
            Decimal("1") - self.config.stop_loss_percentage / Decimal("100")
        )

    def calculate_take_profit_price(self, entry_price: Decimal) -> Optional[Decimal]:
        """
        Calculate take-profit price from entry price.

        Args:
            entry_price: Entry price

        Returns:
            Take-profit price or None if not configured
        """
        if self.config.take_profit_percentage is None:
            return None

        return entry_price * (
            Decimal("1") + self.config.take_profit_percentage / Decimal("100")
        )

    def is_stop_loss_hit(
        self, market_data: Any, stop_loss_price: Decimal
    ) -> tuple[bool, Optional[Decimal]]:
        """
        Check if stop-loss is hit based on market data.

        Args:
            market_data: Current market data
            stop_loss_price: Stop-loss price to check

        Returns:
            Tuple of (is_hit, execution_price)
        """
        from app.backtesting.engine import get_price

        close_price = get_price(market_data)

        if hasattr(market_data, "low") and market_data.low is not None:
            # Use intraday low for stop-loss check
            if market_data.low <= stop_loss_price:
                return True, stop_loss_price
        elif close_price <= stop_loss_price:
            # Fallback to close price if low not available
            return True, close_price

        return False, None

    def is_take_profit_hit(
        self, market_data: Any, take_profit_price: Decimal
    ) -> tuple[bool, Optional[Decimal]]:
        """
        Check if take-profit is hit based on market data.

        Args:
            market_data: Current market data
            take_profit_price: Take-profit price to check

        Returns:
            Tuple of (is_hit, execution_price)
        """
        from app.backtesting.engine import get_price

        close_price = get_price(market_data)

        if hasattr(market_data, "high") and market_data.high is not None:
            # Use intraday high for take-profit check
            if market_data.high >= take_profit_price:
                return True, take_profit_price
        elif close_price >= take_profit_price:
            # Fallback to close price if high not available
            return True, close_price

        return False, None
