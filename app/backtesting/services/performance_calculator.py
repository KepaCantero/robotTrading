"""
Performance Metrics Calculator service for backtesting.

This service is responsible for calculating comprehensive performance
metrics including Sharpe ratio, win rate, and drawdown statistics.
"""

from __future__ import annotations

import logging
import math
from decimal import Decimal
from typing import cast

from app.backtesting.metrics import bounded_drawdown_fraction, build_daily_equity_series
from app.backtesting.models import BacktestConfig, PerformanceMetrics, Trade, TradeStatus
from app.shared.config.centralized_config import get_config
from app.shared.utils.decimal_utils import safe_mean, safe_variance

logger = logging.getLogger(__name__)

# Get centralized backtesting configuration
_backtest_config = get_config().backtesting


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
        trades: list[Trade],
        max_drawdown: Decimal,
        initial_capital: Decimal | None = None,
        equity_returns: list[Decimal] | None = None,
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.

        Args:
            trades: List of all trades
            max_drawdown: Maximum drawdown observed (decimal fraction from peak,
                e.g. -0.25 for a 25% drawdown; must be <= 0)
            initial_capital: Initial capital (defaults to config)
            equity_returns: Per-bar returns from the equity curve. When provided,
                Sharpe/Sortino are computed from this series (correct time base);
                otherwise they fall back to the legacy trade-based estimate.

        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        capital = initial_capital or self.config.initial_capital

        if not trades:
            return self._create_empty_metrics(capital)

        # Separate winning and losing trades
        winning_pnls: list[Decimal] = []
        losing_pnls: list[Decimal] = []

        for trade in trades:
            if trade.status == TradeStatus.CLOSED and trade.pnl is not None:
                if trade.pnl > 0:
                    winning_pnls.append(trade.pnl)
                else:
                    losing_pnls.append(trade.pnl)

        total_trades = len(winning_pnls) + len(losing_pnls)
        winning_count = len(winning_pnls)
        losing_count = len(losing_pnls)

        # Calculate win rate (ensure between 0-100)
        if total_trades > 0:
            win_rate = Decimal(str((winning_count / total_trades) * 100))
            win_rate = min(Decimal("100"), max(Decimal("0"), win_rate))
        else:
            win_rate = Decimal("0")

        # Calculate P&L metrics
        total_pnl = sum(winning_pnls + losing_pnls, Decimal(0))
        gross_profit = sum(winning_pnls, Decimal(0))
        gross_loss = sum(losing_pnls, Decimal(0))
        net_profit = gross_profit + gross_loss

        # Calculate trade statistics
        avg_win = gross_profit / winning_count if winning_count > 0 else Decimal("0")
        avg_loss = gross_loss / losing_count if losing_count > 0 else Decimal("0")
        largest_win = max(winning_pnls) if winning_pnls else Decimal("0")
        largest_loss = min(losing_pnls) if losing_pnls else Decimal("0")

        # Calculate Sharpe/Sortino ratios. Prefer the per-bar equity-curve series:
        # it has the correct time base (one observation per bar, not per trade),
        # so annualization by trading days is meaningful.
        if equity_returns is not None and len(equity_returns) >= 2:
            sharpe_ratio = self._calculate_sharpe_from_returns(equity_returns)
            sortino_ratio = self._calculate_sortino_from_returns(equity_returns)
        else:
            sharpe_ratio = self._calculate_sharpe_ratio(trades)
            sortino_ratio = None

        # Calculate time metrics
        if trades:
            first_trade = min(trades, key=lambda t: t.entry_time)
            last_trade = max(trades, key=lambda t: t.exit_time or t.entry_time)
            last_time = last_trade.exit_time or last_trade.entry_time
            total_days = (last_time - first_trade.entry_time).days
            avg_trade_duration = (
                cast("Decimal", total_days / total_trades) if total_trades > 0 else Decimal("0")
            )
        else:
            total_days = 0
            avg_trade_duration = Decimal("0")

        # Ensure max_drawdown is a valid peak-relative fraction in [-1, 0].
        # A drawdown below -100% of the peak is impossible without negative
        # equity; bounded_drawdown_fraction clamps it defensively with a
        # one-time warning (impossible values must never reach the reports).
        max_drawdown = bounded_drawdown_fraction(max_drawdown)

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
            max_drawdown_percentage=min(Decimal("0"), max_drawdown * Decimal("100")),
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_days=total_days,
            avg_trade_duration=avg_trade_duration,
        )

    def _calculate_sharpe_ratio(self, trades: list[Trade]) -> Decimal | None:
        """
        Calculate Sharpe ratio from REAL daily returns (fallback path).

        Fallback used when no per-bar equity returns are available: the dated
        daily equity curve is built from closed trades (all trades closing on
        the same day aggregate into a single end-of-day return, days without
        trades are skipped) via ``app.backtesting.metrics.build_daily_equity_series``.
        A per-trade return series is NOT a daily series and distorts the
        annualized Sharpe (a trade is not a day), which is why the previous
        per-trade implementation was replaced by the shared daily computation.

        Formula: Sharpe = (Rp - Rf) / sigmap
        - Rp: Portfolio return (annualized)
        - Rf: Risk-free rate
        - sigmap: Standard deviation of portfolio returns (annualized)

        Args:
            trades: List of all trades

        Returns:
            Sharpe ratio or None if insufficient data
        """
        if not trades or len(trades) < 2:
            return None

        # Real daily returns from the date-stamped equity curve (shared
        # computation with MetricsCalculator in app.backtesting.metrics)
        _, _, returns = build_daily_equity_series(trades, self.config.initial_capital)

        if not returns or len(returns) < 2:
            return None

        # Calculate mean and standard deviation
        mean_return = safe_mean(returns)
        variance = safe_variance(returns)
        if mean_return is None or variance is None:
            return None
        std_dev = Decimal(str(math.sqrt(float(variance))))

        # CRITICAL FIX: Add volatility floor to prevent extreme Sharpe values
        # When all trades have similar P&L (e.g., all stopped out at same %),
        # std_dev is very small but not zero, causing Sharpe to explode.
        # Minimum 15% annualized volatility is a reasonable floor for any trading strategy.
        # This prevents unrealistic Sharpe ratios when few trades have similar outcomes.
        MIN_ANNUAL_VOLATILITY = _backtest_config.min_annual_volatility

        # Annualize using config trading days
        annual_mean = mean_return * Decimal(str(_backtest_config.annual_trading_days))
        annual_std = std_dev * Decimal(str(math.sqrt(_backtest_config.annual_trading_days)))

        # Apply volatility floor
        annual_std = max(annual_std, MIN_ANNUAL_VOLATILITY)

        if annual_std == 0:
            return None

        excess_return = annual_mean - self.config.risk_free_rate
        sharpe = excess_return / annual_std

        return sharpe

    def _calculate_sharpe_from_returns(self, returns: list[Decimal]) -> Decimal | None:
        """
        Calculate annualized Sharpe ratio from a per-bar return series.

        One observation per bar annualized with the configured number of
        trading days. A minimum annualized volatility floor is applied so
        near-constant return series do not produce extreme ratios.

        Args:
            returns: Period-over-period returns (one per bar)

        Returns:
            Annualized Sharpe ratio, or None if not computable
        """
        if len(returns) < 2:
            return None

        mean_return = safe_mean(returns)
        variance = safe_variance(returns)
        if mean_return is None or variance is None:
            return None
        std_dev = Decimal(str(math.sqrt(float(variance))))

        MIN_ANNUAL_VOLATILITY = _backtest_config.min_annual_volatility
        annual_mean = mean_return * Decimal(str(_backtest_config.annual_trading_days))
        annual_std = std_dev * Decimal(str(math.sqrt(_backtest_config.annual_trading_days)))
        annual_std = max(annual_std, MIN_ANNUAL_VOLATILITY)

        if annual_std == 0:
            return None

        return (annual_mean - self.config.risk_free_rate) / annual_std

    def _calculate_sortino_from_returns(self, returns: list[Decimal]) -> Decimal | None:
        """
        Calculate annualized Sortino ratio from a per-bar return series.

        Downside deviation uses the full lower semi-deviation against a
        zero target (MAR = 0): sqrt(mean(min(r, 0)^2)).

        Args:
            returns: Period-over-period returns (one per bar)

        Returns:
            Annualized Sortino ratio, or None if not computable (no downside)
        """
        if len(returns) < 2:
            return None

        downside = [r for r in returns if r < 0]
        if not downside:
            return None

        downside_var = sum(r * r for r in downside) / Decimal(len(returns))
        downside_dev = Decimal(str(math.sqrt(float(downside_var))))
        if downside_dev == 0:
            return None

        MIN_ANNUAL_VOLATILITY = _backtest_config.min_annual_volatility
        mean_return = safe_mean(returns)
        if mean_return is None:
            return None
        annual_mean = mean_return * Decimal(str(_backtest_config.annual_trading_days))
        annual_downside = downside_dev * Decimal(
            str(math.sqrt(_backtest_config.annual_trading_days))
        )
        annual_downside = max(annual_downside, MIN_ANNUAL_VOLATILITY)

        return (annual_mean - self.config.risk_free_rate) / annual_downside

    def _create_empty_metrics(self, initial_capital: Decimal | None = None) -> PerformanceMetrics:
        """
        Create empty performance metrics.

        Args:
            initial_capital: Initial capital for percentage calculations

        Returns:
            PerformanceMetrics with all zeros
        """
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

    def calculate_win_rate(self, trades: list[Trade]) -> Decimal:
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

    def calculate_profit_factor(self, trades: list[Trade]) -> Decimal:
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

    def calculate_expectancy(self, trades: list[Trade]) -> Decimal:
        """
        Calculate expectancy (average P&L per trade).

        Args:
            trades: List of all trades

        Returns:
            Expectancy per trade
        """
        closed_pnls = [
            t.pnl for t in trades if t.status == TradeStatus.CLOSED and t.pnl is not None
        ]

        if not closed_pnls:
            return Decimal("0")

        return cast("Decimal", sum(closed_pnls) / len(closed_pnls))
