"""
Performance Metrics Calculator service for backtesting.

This service is responsible for calculating comprehensive performance
metrics including Sharpe ratio, win rate, and drawdown statistics.
"""

from __future__ import annotations

import logging
import math
from decimal import Decimal
from typing import List, Optional

from app.backtesting.models import BacktestConfig, PerformanceMetrics, Trade, TradeStatus
from app.shared.utils.decimal_utils import safe_mean, safe_variance

logger = logging.getLogger(__name__)


class PerformanceMetricsCalculator:
    """
    Calculate comprehensive performance metrics.

    This service handles:
    - Win rate calculation
    - P&L metrics (gross profit, gross loss, net profit)
    - Sharpe ratio calculation
    - Drawdown calculation
    - Trade duration statistics

    This is a pure calculation service with no external dependencies.
    """

    def __init__(self, config: BacktestConfig):
        """
        Initialize the Performance Metrics Calculator.

        Args:
            config: Backtest configuration
        """
        self.config = config

    def calculate_performance_metrics(
        self,
        trades: List[Trade],
        max_drawdown: Decimal,
        initial_capital: Optional[Decimal] = None,
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.

        Args:
            trades: List of all trades
            max_drawdown: Maximum drawdown observed
            initial_capital: Initial capital (defaults to config)

        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        capital = initial_capital or self.config.initial_capital

        if not trades:
            return self._create_empty_metrics(capital)

        # Separate winning and losing trades
        winning_trades = []
        losing_trades = []

        for trade in trades:
            if trade.status == TradeStatus.CLOSED and trade.pnl is not None:
                if trade.pnl > 0:
                    winning_trades.append(trade)
                else:
                    losing_trades.append(trade)

        total_trades = len(winning_trades) + len(losing_trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)

        # Calculate win rate (ensure between 0-100)
        if total_trades > 0:
            win_rate = Decimal(str((winning_count / total_trades) * 100))
            win_rate = min(Decimal("100"), max(Decimal("0"), win_rate))
        else:
            win_rate = Decimal("0")

        # Calculate P&L metrics
        total_pnl = sum(trade.pnl for trade in winning_trades + losing_trades)
        gross_profit = (
            sum(trade.pnl for trade in winning_trades) if winning_trades else Decimal("0")
        )
        gross_loss = sum(trade.pnl for trade in losing_trades) if losing_trades else Decimal("0")
        net_profit = gross_profit + gross_loss

        # Calculate trade statistics
        avg_win = gross_profit / winning_count if winning_count > 0 else Decimal("0")
        avg_loss = gross_loss / losing_count if losing_count > 0 else Decimal("0")
        largest_win = max(trade.pnl for trade in winning_trades) if winning_trades else Decimal("0")
        largest_loss = min(trade.pnl for trade in losing_trades) if losing_trades else Decimal("0")

        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(trades)

        # Calculate time metrics
        if trades:
            first_trade = min(trades, key=lambda t: t.entry_time)
            last_trade = max(trades, key=lambda t: t.exit_time or t.entry_time)
            last_time = last_trade.exit_time or last_trade.entry_time
            total_days = (last_time - first_trade.entry_time).days
            avg_trade_duration = total_days / total_trades if total_trades > 0 else Decimal("0")
        else:
            total_days = 0
            avg_trade_duration = Decimal("0")

        # Ensure max_drawdown is <= 0 as per validation
        max_drawdown = min(Decimal("0"), max_drawdown)

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percentage=(total_pnl / capital * 100),
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            max_drawdown=max_drawdown,
            max_drawdown_percentage=min(
                Decimal("0"),
                ((max_drawdown / capital * 100) if capital > 0 else Decimal("0")),
            ),
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=None,  # Not implemented yet
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_days=total_days,
            avg_trade_duration=avg_trade_duration,
        )

    def _calculate_sharpe_ratio(self, trades: List[Trade]) -> Optional[Decimal]:
        """
        Calculate Sharpe ratio from realized trade P&L using proper time-series returns.

        CRITICAL BUG FIX: The previous implementation calculated returns relative to
        cumulative capital, which is INCORRECT for time-series analysis. This led to
        distorted Sharpe ratios because returns were normalized against changing capital.

        The CORRECT implementation:
        1. Build equity curve from closed trades
        2. Calculate period-over-period returns from equity curve
        3. These returns compound properly (r1, r2, r3...)
        4. Annualize and calculate Sharpe from the return series

        Formula: Sharpe = (Rp - Rf) / σp
        - Rp: Portfolio return (annualized)
        - Rf: Risk-free rate
        - σp: Standard deviation of portfolio returns (annualized)

        Args:
            trades: List of all trades

        Returns:
            Sharpe ratio or None if insufficient data
        """
        if not trades or len(trades) < 2:
            return None

        # Calculate returns from closed trades
        closed_trades = [t for t in trades if t.pnl is not None and t.exit_time is not None]
        closed_trades.sort(key=lambda t: t.exit_time)

        if len(closed_trades) < 2:
            return None

        # Build equity curve from trades (CORRECT approach)
        current_capital = self.config.initial_capital
        equity_values = [self.config.initial_capital]

        for trade in closed_trades:
            current_capital += trade.pnl
            equity_values.append(current_capital)

        # Calculate returns from equity curve (time-series returns)
        returns = []
        for i in range(1, len(equity_values)):
            ret = (equity_values[i] - equity_values[i - 1]) / equity_values[i - 1]
            returns.append(ret)

        if not returns or len(returns) < 2:
            return None

        # Calculate mean and standard deviation
        mean_return = safe_mean(returns)
        variance = safe_variance(returns)
        std_dev = Decimal(str(math.sqrt(float(variance))))

        # CRITICAL FIX: Add volatility floor to prevent extreme Sharpe values
        # When all trades have similar P&L (e.g., all stopped out at same %),
        # std_dev is very small but not zero, causing Sharpe to explode.
        # Minimum 15% annualized volatility is a reasonable floor for any trading strategy.
        # This prevents unrealistic Sharpe ratios when few trades have similar outcomes.
        MIN_ANNUAL_VOLATILITY = Decimal("0.15")  # 15% minimum annualized volatility

        # Annualize (252 trading days)
        annual_mean = mean_return * Decimal("252")
        annual_std = std_dev * Decimal(str(math.sqrt(252)))

        # Apply volatility floor
        annual_std = max(annual_std, MIN_ANNUAL_VOLATILITY)

        if annual_std == 0:
            return None

        excess_return = annual_mean - self.config.risk_free_rate
        sharpe = excess_return / annual_std

        return sharpe

    def _create_empty_metrics(
        self, initial_capital: Optional[Decimal] = None
    ) -> PerformanceMetrics:
        """
        Create empty performance metrics.

        Args:
            initial_capital: Initial capital for percentage calculations

        Returns:
            PerformanceMetrics with all zeros
        """
        initial_capital or self.config.initial_capital

        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=Decimal("0"),
            total_pnl=Decimal("0"),
            total_pnl_percentage=Decimal("0"),
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
            net_profit=Decimal("0"),
            max_drawdown=Decimal("0"),
            max_drawdown_percentage=Decimal("0"),
            sharpe_ratio=None,
            sortino_ratio=None,
            avg_win=Decimal("0"),
            avg_loss=Decimal("0"),
            largest_win=Decimal("0"),
            largest_loss=Decimal("0"),
            total_days=0,
            avg_trade_duration=Decimal("0"),
        )

    def calculate_win_rate(self, trades: List[Trade]) -> Decimal:
        """
        Calculate win rate from trades.

        Args:
            trades: List of all trades

        Returns:
            Win rate as percentage (0-100)
        """
        if not trades:
            return Decimal("0")

        winning_trades = [
            t for t in trades if t.status == TradeStatus.CLOSED and t.pnl and t.pnl > 0
        ]
        losing_trades = [
            t for t in trades if t.status == TradeStatus.CLOSED and t.pnl and t.pnl <= 0
        ]

        total_trades = len(winning_trades) + len(losing_trades)

        if total_trades == 0:
            return Decimal("0")

        win_rate = Decimal(str((len(winning_trades) / total_trades) * 100))
        return min(Decimal("100"), max(Decimal("0"), win_rate))

    def calculate_profit_factor(self, trades: List[Trade]) -> Decimal:
        """
        Calculate profit factor (gross profit / |gross loss|).

        Args:
            trades: List of all trades

        Returns:
            Profit factor or 0 if no losing trades
        """
        gross_profit = Decimal("0")
        gross_loss = Decimal("0")

        for trade in trades:
            if trade.status == TradeStatus.CLOSED and trade.pnl:
                if trade.pnl > 0:
                    gross_profit += trade.pnl
                else:
                    gross_loss += abs(trade.pnl)

        if gross_loss == 0:
            return Decimal("0")

        return gross_profit / gross_loss

    def calculate_expectancy(self, trades: List[Trade]) -> Decimal:
        """
        Calculate expectancy (average P&L per trade).

        Args:
            trades: List of all trades

        Returns:
            Expectancy per trade
        """
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED and t.pnl is not None]

        if not closed_trades:
            return Decimal("0")

        total_pnl = sum(t.pnl for t in closed_trades)
        return total_pnl / len(closed_trades)
