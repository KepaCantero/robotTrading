"""
Profit and Loss Calculator service for backtesting.

This service is responsible for calculating trade profitability
including average entry prices, commission costs, and P&L percentages.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from app.backtesting.models import BacktestConfig, Trade, TradeStatus

logger = logging.getLogger(__name__)


class ProfitAndLossCalculator:
    """
    Calculate trade profitability metrics.

    This service handles:
    - Average entry price calculation
    - Commission cost calculation
    - P&L calculation for sell trades
    - P&L calculation for position closes
    - P&L percentage calculation

    This is a pure calculation service with no external dependencies.
    """

    def __init__(self, config: BacktestConfig):
        """
        Initialize the P&L Calculator.

        Args:
            config: Backtest configuration for commission parameters
        """
        self.config = config

    def calculate_sell_pnl(
        self,
        trades: List[Trade],
        symbol: str,
        sell_quantity: Decimal,
        execution_price: Decimal,
        commission: Decimal,
    ) -> Dict[str, Any]:
        """
        Calculate P&L for a sell trade.

        Args:
            trades: List of all trades
            symbol: Trading symbol
            sell_quantity: Quantity being sold
            execution_price: Execution price
            commission: Commission for this sell trade

        Returns:
            Dictionary with:
                - pnl: Calculated P&L
                - pnl_percentage: P&L as percentage
                - avg_buy_price: Average buy price
                - buy_trades: List of matching buy trades
                - entry_time: Entry time of first buy trade
        """
        # Find matching buy trades
        buy_trades = [
            t
            for t in trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]

        logger.debug(f"SELL {symbol}: found {len(buy_trades)} open buy trades")

        # Calculate P&L
        pnl = Decimal("0")
        avg_buy_price = execution_price
        entry_time = None

        if buy_trades:
            avg_buy_price = sum(t.entry_price * t.quantity for t in buy_trades) / sum(
                t.quantity for t in buy_trades
            )
            total_cost = avg_buy_price * sell_quantity + commission
            proceeds = sell_quantity * execution_price - commission
            pnl = proceeds - total_cost
            entry_time = buy_trades[-1].entry_time

            logger.info(
                f"PnL CALCULATION {symbol}: "
                f"avg_buy_price={avg_buy_price:.2f}, execution_price={execution_price:.2f}, "
                f"sell_quantity={sell_quantity:.6f}, proceeds={proceeds:.2f}, "
                f"total_cost={total_cost:.2f}, pnl={pnl:.2f}"
            )
        else:
            logger.warning(f"SELL {symbol}: NO buy_trades found! " f"PnL will be 0.")

        # Calculate P&L percentage (handle zero quantity)
        pnl_percentage = (
            (pnl / (avg_buy_price * sell_quantity) * 100)
            if buy_trades and sell_quantity > 0
            else Decimal("0")
        )

        return {
            "pnl": pnl,
            "pnl_percentage": pnl_percentage,
            "avg_buy_price": avg_buy_price,
            "buy_trades": buy_trades,
            "entry_time": entry_time,
        }

    def calculate_close_position_pnl(
        self,
        symbol: str,
        quantity: Decimal,
        exit_price: Decimal,
        trades: List[Trade],
    ) -> Dict[str, Any]:
        """
        Calculate P&L when closing a position (stop-loss, take-profit, etc.).

        Args:
            symbol: Trading symbol
            quantity: Quantity being closed
            exit_price: Exit price
            trades: List of all trades

        Returns:
            Dictionary with:
                - pnl: Calculated P&L
                - pnl_percentage: P&L as percentage
                - avg_entry_price: Average entry price
                - total_commission: Total commission (buy + sell)
                - entry_time: Entry time of first buy trade
        """
        # Find OPEN buy trades for this symbol
        buy_trades = [
            t
            for t in trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]

        if not buy_trades:
            return {
                "pnl": Decimal("0"),
                "pnl_percentage": Decimal("0"),
                "avg_entry_price": exit_price,
                "total_commission": Decimal("0"),
                "entry_time": None,
            }

        # Calculate average entry price and cost for the quantity being closed
        total_buy_quantity = sum(t.quantity for t in buy_trades)
        buy_cost = sum(t.quantity * t.entry_price for t in buy_trades)
        avg_entry_price = (
            buy_cost / total_buy_quantity if total_buy_quantity > 0 else buy_trades[-1].entry_price
        )

        # Calculate cost basis for the quantity being closed (not all open trades)
        cost_basis = avg_entry_price * quantity

        # Calculate commission
        avg_commission_per_buy = (
            np.mean([t.commission for t in buy_trades if t.commission])
            if buy_trades and any(t.commission for t in buy_trades)
            else self.config.commission_per_trade
        )

        # Estimate sell commission
        sell_trade_value = quantity * exit_price
        commission_sell = avg_commission_per_buy

        # Check if percentage-based commission
        if buy_trades and any(
            t.commission > self.config.commission_per_trade * Decimal("1.5") for t in buy_trades
        ):
            commission_rate = (
                avg_commission_per_buy / (buy_trades[0].quantity * buy_trades[0].entry_price)
                if buy_trades[0].quantity * buy_trades[0].entry_price > 0
                else Decimal("0")
            )
            commission_sell = sell_trade_value * commission_rate

        # Commission for this position close only (proportional to quantity)
        proportion_of_trades = (
            quantity / total_buy_quantity if total_buy_quantity > 0 else Decimal("1")
        )
        buy_commission = sum(t.commission for t in buy_trades) * proportion_of_trades
        total_commission = buy_commission + commission_sell

        # Calculate P&L for the quantity being closed
        total_sell_proceeds = quantity * exit_price
        pnl = total_sell_proceeds - cost_basis - total_commission

        pnl_percentage = (pnl / cost_basis * 100) if cost_basis > 0 else Decimal("0")

        entry_time = buy_trades[0].entry_time if buy_trades else None

        return {
            "pnl": pnl,
            "pnl_percentage": pnl_percentage,
            "avg_entry_price": avg_entry_price,
            "total_commission": total_commission,
            "entry_time": entry_time,
        }

    def calculate_average_entry_price(self, trades: List[Trade], symbol: str) -> Optional[Decimal]:
        """
        Calculate average entry price for a symbol's open positions.

        Args:
            trades: List of all trades
            symbol: Trading symbol

        Returns:
            Average entry price or None if no open positions
        """
        buy_trades = [
            t
            for t in trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]

        if not buy_trades:
            return None

        total_cost = sum(t.entry_price * t.quantity for t in buy_trades)
        total_quantity = sum(t.quantity for t in buy_trades)

        if total_quantity == 0:
            return None

        return total_cost / total_quantity

    def calculate_round_trip_commission(self, trades: List[Trade], symbol: str) -> Decimal:
        """
        Calculate round-trip commission for a symbol.

        Args:
            trades: List of all trades
            symbol: Trading symbol

        Returns:
            Total round-trip commission
        """
        symbol_trades = [t for t in trades if t.symbol == symbol and t.commission]
        return sum(t.commission for t in symbol_trades)

    def calculate_commission_ratio(
        self, position_value: Decimal, trades: List[Trade], symbol: str
    ) -> Decimal:
        """
        Calculate commission ratio as percentage of position value.

        Args:
            position_value: Current position value
            trades: List of all trades
            symbol: Trading symbol

        Returns:
            Commission ratio (as Decimal, e.g., 0.01 for 1%)
        """
        round_trip_commission = self.calculate_round_trip_commission(trades, symbol)

        if position_value > 0:
            return round_trip_commission / position_value
        return Decimal("0")
