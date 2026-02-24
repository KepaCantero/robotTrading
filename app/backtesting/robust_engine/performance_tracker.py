"""
Performance Tracker for Robust Backtesting Engine.

This module provides comprehensive performance tracking for long-term
backtests over 25+ year periods.

Features:
- Year-by-year performance breakdown
- Rolling metrics (3-year, 5-year, 10-year)
- Regime analysis (bull/bear markets)
- Drawdown analysis with recovery periods
- Risk-adjusted returns (Sharpe, Sortino, Calmar)
- Win rate and profit factor statistics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Import canonical PerformanceMetrics from the single source of truth
from app.backtesting.models import PerformanceMetrics
from app.shared.config.centralized_config import CentralizedConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class YearlyBreakdown:
    """
    Performance breakdown for a single year.

    Attributes:
        year: Calendar year
        total_return: Total return for the year
        cagr: Compound annual growth rate
        volatility: Annualized volatility
        max_drawdown: Maximum drawdown for the year
        sharpe_ratio: Sharpe ratio for the year
        trades: Number of trades executed
        win_rate: Win rate percentage
        best_month: Best month return
        worst_month: Worst month return
    """

    year: int = field(default=0)
    total_return: float = field(default=0.0)
    cagr: float = field(default=0.0)
    volatility: float = field(default=0.0)
    max_drawdown: float = field(default=0.0)
    sharpe_ratio: Optional[float] = field(default=None)
    trades: int = field(default=0)
    win_rate: float = field(default=0.0)
    best_month: float = field(default=0.0)
    worst_month: float = field(default=0.0)


@dataclass
class RollingMetrics:
    """
    Rolling performance metrics over different windows.

    Attributes:
        window_1y: 1-year rolling metrics
        window_3y: 3-year rolling metrics
        window_5y: 5-year rolling metrics
        window_10y: 10-year rolling metrics
    """

    window_1y: Dict[str, float] = field(default_factory=dict)
    window_3y: Dict[str, float] = field(default_factory=dict)
    window_5y: Dict[str, float] = field(default_factory=dict)
    window_10y: Dict[str, float] = field(default_factory=dict)


@dataclass
class RegimeAnalysis:
    """
    Analysis of performance across market regimes.

    Attributes:
        bull_market_return: Return during bull markets
        bear_market_return: Return during bear markets
        sideways_market_return: Return during sideways markets
        bull_market_periods: List of bull market periods
        bear_market_periods: List of bear market periods
    """

    bull_market_return: float = field(default=0.0)
    bear_market_return: float = field(default=0.0)
    sideways_market_return: float = field(default=0.0)
    bull_market_periods: List[Tuple[date, date]] = field(default_factory=list)
    bear_market_periods: List[Tuple[date, date]] = field(default_factory=list)


# NOTE: PerformanceMetrics is now imported from app.backtesting.models
# This is the canonical source of truth for all performance metrics.


class PerformanceTracker:
    """
    Tracks and calculates comprehensive performance metrics.

    This class provides:
    1. Real-time performance tracking during backtest
    2. Year-by-year breakdown
    3. Rolling metrics over different windows
    4. Regime analysis (bull/bear/sideways)
    5. Drawdown analysis with recovery periods

    Example:
        ```python
        tracker = PerformanceTracker(
            initial_capital=Decimal("100000"),
            risk_free_rate=get_config().backtesting.default_risk_free_rate
        )

        # Update tracker with new equity value
        tracker.update(current_date, current_capital)

        # Get metrics
        metrics = tracker.calculate_metrics()
        ```
    """

    def __init__(
        self,
        initial_capital: Decimal,
        risk_free_rate: Decimal = None,
    ):
        """
        Initialize the performance tracker.

        Args:
            initial_capital: Starting capital for the backtest
            risk_free_rate: Annual risk-free rate for Sharpe ratio (default: from CentralizedConfig)
        """
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate if risk_free_rate is not None else get_config().backtesting.default_risk_free_rate

        # Equity curve tracking
        self.equity_curve: List[Tuple[date, Decimal]] = []
        self._peak_equity: Decimal = initial_capital
        self._current_drawdown: Decimal = Decimal("0")

        # Trade tracking
        self._trades: List[Dict[str, Any]] = []
        self._winning_trades: List[float] = []
        self._losing_trades: List[float] = []

        # Drawdown tracking
        self._drawdowns: List[Tuple[date, date, Decimal]] = []
        self._in_drawdown: bool = False
        self._drawdown_start: Optional[date] = None

        # Streaks
        self._current_winning_streak: int = 0
        self._current_losing_streak: int = 0
        self._max_winning_streak: int = 0
        self._max_losing_streak: int = 0

    def update(
        self,
        current_date: date,
        current_capital: Decimal,
        trades: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Update tracker with new equity value.

        Args:
            current_date: Current simulation date
            current_capital: Current capital/equity
            trades: Optional list of trades executed
        """
        self.equity_curve.append((current_date, current_capital))

        # Track trades
        if trades:
            self._trades.extend(trades)
            for trade in trades:
                pnl = float(trade.get("pnl", 0))
                if pnl > 0:
                    self._winning_trades.append(pnl)
                    self._current_winning_streak += 1
                    self._current_losing_streak = 0
                elif pnl < 0:
                    self._losing_trades.append(pnl)
                    self._current_losing_streak += 1
                    self._current_winning_streak = 0

                # Update streaks
                self._max_winning_streak = max(
                    self._max_winning_streak, self._current_winning_streak
                )
                self._max_losing_streak = max(self._max_losing_streak, self._current_losing_streak)

        # Update peak and drawdown
        if current_capital >= self._peak_equity:
            self._peak_equity = current_capital

            # Drawdown ended
            if self._in_drawdown and self._drawdown_start:
                self._drawdowns.append((self._drawdown_start, current_date, self._current_drawdown))
                self._in_drawdown = False
                self._drawdown_start = None
                self._current_drawdown = Decimal("0")
        else:
            # In drawdown
            drawdown = (current_capital - self._peak_equity) / self._peak_equity
            self._current_drawdown = min(self._current_drawdown, drawdown)

            if not self._in_drawdown and drawdown < 0:
                self._in_drawdown = True
                self._drawdown_start = current_date

    def calculate_metrics(self) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.

        Returns:
            PerformanceMetrics with all calculated metrics
        """
        if len(self.equity_curve) < 2:
            return PerformanceMetrics()

        # Convert equity curve to series with DatetimeIndex
        dates, values = zip(*self.equity_curve)
        # Create a DatetimeIndex to support .year accessor
        if isinstance(dates[0], date):
            dates = pd.DatetimeIndex(dates)
        equity_series = pd.Series([float(v) for v in values], index=dates)

        # Calculate returns
        returns = equity_series.pct_change().dropna()

        # Calculate basic metrics
        total_return = equity_series.iloc[-1] / equity_series.iloc[0] - 1

        # Calculate years
        total_days = (dates[-1] - dates[0]).days
        years = total_days / 365.25

        # CAGR
        if years > 0:
            cagr = (equity_series.iloc[-1] / equity_series.iloc[0]) ** (1 / years) - 1
        else:
            cagr = 0.0

        # Get trading days from config
        annual_trading_days = get_config().backtesting.annual_trading_days

        # Volatility
        volatility = returns.std() * np.sqrt(annual_trading_days) if len(returns) > 0 else 0.0

        # Sharpe ratio
        if len(returns) > 0 and volatility > 0:
            excess_return = returns.mean() * annual_trading_days - float(self.risk_free_rate)
            sharpe = float(excess_return / volatility) if volatility > 0 else None
        else:
            sharpe = None

        # Maximum drawdown
        max_drawdown = self._calculate_max_drawdown(equity_series)

        # Sortino ratio
        sortino = self._calculate_sortino_ratio(returns)

        # Calmar ratio
        calmar = abs(cagr / max_drawdown) if max_drawdown != 0 else None

        # Trade statistics
        total_trades = len(self._winning_trades) + len(self._losing_trades)
        win_rate = len(self._winning_trades) / total_trades if total_trades > 0 else 0

        avg_win = np.mean(self._winning_trades) if self._winning_trades else 0.0
        avg_loss = np.mean(self._losing_trades) if self._losing_trades else 0.0

        gross_profit = sum(self._winning_trades)
        gross_loss = abs(sum(self._losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

        expectancy = ((gross_profit - gross_loss)) / total_trades if total_trades > 0 else None

        # Yearly breakdown
        yearly_returns = self._calculate_yearly_returns(equity_series)

        # Distribution metrics
        if len(returns) > 3:
            skewness = float(stats.skew(returns))
            kurtosis = float(stats.kurtosis(returns))
        else:
            skewness = None
            kurtosis = None

        # VaR and CVaR
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else None
        cvar_95 = (
            np.mean(returns[returns <= var_95])
            if var_95 is not None and len(returns[returns <= var_95]) > 0
            else None
        )

        # Recovery factor
        recovery_factor = total_return / abs(max_drawdown) if max_drawdown != 0 else None

        # Helper function to convert to Decimal
        def to_decimal(val):
            if val is None:
                return None
            return Decimal(str(val))

        return PerformanceMetrics(
            total_return=to_decimal(total_return),
            cagr=to_decimal(cagr),
            annualized_return=to_decimal(float(returns.mean() * annual_trading_days) if len(returns) > 0 else 0.0),
            volatility=to_decimal(volatility),
            max_drawdown=to_decimal(max_drawdown),
            max_drawdown_duration=self._max_drawdown_duration(),
            calmar_ratio=to_decimal(calmar),
            ulcer_index=to_decimal(self._calculate_ulcer_index(equity_series)),
            sharpe_ratio=to_decimal(sharpe),
            sortino_ratio=to_decimal(sortino),
            omega_ratio=to_decimal(self._calculate_omega_ratio(returns)),
            total_trades=total_trades,
            winning_trades=len(self._winning_trades),
            losing_trades=len(self._losing_trades),
            win_rate=to_decimal(win_rate * 100),
            avg_win=to_decimal(avg_win),
            avg_loss=to_decimal(avg_loss),
            profit_factor=to_decimal(profit_factor),
            expectancy=to_decimal(expectancy),
            best_year=to_decimal(max(yearly_returns.values()) if yearly_returns else 0.0),
            worst_year=to_decimal(min(yearly_returns.values()) if yearly_returns else 0.0),
            avg_yearly_return=to_decimal(np.mean(list(yearly_returns.values())) if yearly_returns else 0.0),
            skewness=to_decimal(skewness),
            kurtosis=to_decimal(kurtosis),
            var_95=to_decimal(var_95),
            cvar_95=to_decimal(cvar_95),
            recovery_factor=to_decimal(recovery_factor),
            tail_ratio=to_decimal(self._calculate_tail_ratio(returns)),
            winning_streak=self._max_winning_streak,
            losing_streak=self._max_losing_streak,
        )

    def get_yearly_breakdown(self) -> List[YearlyBreakdown]:
        """
        Get year-by-year performance breakdown.

        Returns:
            List of YearlyBreakdown for each year
        """
        if len(self.equity_curve) < 2:
            return []

        dates, values = zip(*self.equity_curve)
        # Create a DatetimeIndex to support .year accessor
        if isinstance(dates[0], date):
            dates = pd.DatetimeIndex(dates)
        equity_series = pd.Series([float(v) for v in values], index=dates)

        yearly_breakdowns = []

        for year in range(dates[0].year, dates[-1].year + 1):
            year_data = equity_series[equity_series.index.year == year]

            if len(year_data) < 2:
                continue

            annual_trading_days = get_config().backtesting.annual_trading_days
            year_return = year_data.iloc[-1] / year_data.iloc[0] - 1
            year_vol = year_data.pct_change().std() * np.sqrt(annual_trading_days)

            # Max drawdown for the year
            cummax = year_data.cummax()
            drawdown = (year_data - cummax) / cummax
            max_dd = drawdown.min()

            # Sharpe for the year
            returns = year_data.pct_change().dropna()
            sharpe = None
            if len(returns) > 0 and year_vol > 0:
                excess_return = returns.mean() * annual_trading_days - float(self.risk_free_rate)
                sharpe = excess_return / year_vol

            # Monthly breakdown
            monthly_returns = []
            for month in range(1, 13):
                month_data = year_data[year_data.index.month == month]
                if len(month_data) >= 2:
                    monthly_returns.append((month_data.iloc[-1] / month_data.iloc[0] - 1))

            best_month = max(monthly_returns) if monthly_returns else 0.0
            worst_month = min(monthly_returns) if monthly_returns else 0.0

            # Count trades for this year
            year_trades = 0
            for t in self._trades:
                trade_date = t.get("date")
                if trade_date:
                    # Handle different date types
                    if isinstance(trade_date, date):
                        trade_year = trade_date.year
                    elif isinstance(trade_date, str):
                        try:
                            trade_year = date.fromisoformat(trade_date).year
                        except (ValueError, AttributeError):
                            # Try parsing the date string differently
                            trade_year = pd.to_datetime(trade_date).year
                    else:
                        # Try using pandas for other date types
                        trade_year = pd.to_datetime(trade_date).year

                    if trade_year == year:
                        year_trades += 1

            yearly_breakdowns.append(
                YearlyBreakdown(
                    year=year,
                    total_return=year_return,
                    cagr=year_return,  # For single year, CAGR = total return
                    volatility=year_vol,
                    max_drawdown=max_dd,
                    sharpe_ratio=sharpe,
                    trades=year_trades,
                    win_rate=0.0,  # Would need separate tracking
                    best_month=best_month,
                    worst_month=worst_month,
                )
            )

        return yearly_breakdowns

    def get_rolling_metrics(
        self,
        windows: List[int] = None,  # Default calculated from annual_trading_days
    ) -> RollingMetrics:
        """
        Calculate rolling metrics over different windows.

        Args:
            windows: List of window sizes in days (default: 1, 3, 5, 10 years based on annual_trading_days)

        Returns:
            RollingMetrics with calculated rolling metrics
        """
        annual_trading_days = get_config().backtesting.annual_trading_days
        if windows is None:
            windows = [annual_trading_days, annual_trading_days * 3, annual_trading_days * 5, annual_trading_days * 10]

        if len(self.equity_curve) < 2:
            return RollingMetrics()

        dates, values = zip(*self.equity_curve)
        equity_series = pd.Series([float(v) for v in values], index=dates)
        returns = equity_series.pct_change().dropna()

        metrics = {}

        for window in windows:
            if len(returns) < window:
                continue

            # Rolling metrics
            rolling_return = returns.rolling(window=window).apply(lambda x: (1 + x).prod() - 1)
            rolling_vol = returns.rolling(window=window).std() * np.sqrt(annual_trading_days)
            rolling_sharpe = (
                returns.rolling(window=window).mean() * annual_trading_days - float(self.risk_free_rate)
            ) / rolling_vol

            # Use latest values
            window_label = f"window_{window // annual_trading_days}y"
            metrics[window_label] = {
                "return": float(rolling_return.iloc[-1]),
                "volatility": float(rolling_vol.iloc[-1]),
                "sharpe": (
                    float(rolling_sharpe.iloc[-1]) if not pd.isna(rolling_sharpe.iloc[-1]) else None
                ),
            }

        return RollingMetrics(
            window_1y=metrics.get("window_1y", {}),
            window_3y=metrics.get("window_3y", {}),
            window_5y=metrics.get("window_5y", {}),
            window_10y=metrics.get("window_10y", {}),
        )

    def _calculate_max_drawdown(self, equity_series: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        return float(drawdown.min())

    def _max_drawdown_duration(self) -> int:
        """Calculate maximum drawdown duration in days."""
        if not self._drawdowns:
            return 0

        max_duration = 0
        for start, end, _ in self._drawdowns:
            duration = (end - start).days
            max_duration = max(max_duration, duration)

        return max_duration

    def _calculate_sortino_ratio(self, returns: pd.Series) -> Optional[float]:
        """Calculate Sortino ratio (downside deviation)."""
        if len(returns) < 2:
            return None

        annual_trading_days = get_config().backtesting.annual_trading_days
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            # No downside volatility, return a high positive value or None
            # Return None if all returns are non-negative (no downside risk)
            return None

        downside_deviation = downside_returns.std() * np.sqrt(annual_trading_days)
        if downside_deviation is None or downside_deviation == 0:
            return None

        excess_return = returns.mean() * annual_trading_days - float(self.risk_free_rate)
        return float(excess_return / downside_deviation)

    def _calculate_omega_ratio(self, returns: pd.Series, threshold: float = 0.0) -> Optional[float]:
        """Calculate Omega ratio."""
        if len(returns) < 2:
            return None

        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns <= threshold]

        if len(losses) == 0 or losses.sum() == 0:
            return None

        return float(gains.sum() / losses.sum())

    def _calculate_ulcer_index(self, equity_series: pd.Series) -> Optional[float]:
        """Calculate Ulcer Index."""
        cummax = equity_series.cummax()
        drawdown = ((equity_series - cummax) / cummax) ** 2
        return float(np.sqrt(drawdown.mean())) if len(drawdown) > 0 else None

    def _calculate_tail_ratio(self, returns: pd.Series) -> Optional[float]:
        """Calculate tail ratio (95th percentile / 5th percentile)."""
        if len(returns) < 10:
            return None

        percentile_95 = np.percentile(returns, 95)
        percentile_5 = np.percentile(returns, 5)

        if percentile_5 == 0:
            return None

        return float(abs(percentile_95 / percentile_5))

    def _calculate_yearly_returns(self, equity_series: pd.Series) -> Dict[int, float]:
        """Calculate returns by year."""
        yearly_returns = {}

        for year in equity_series.index.year.unique():
            year_data = equity_series[equity_series.index.year == year]
            if len(year_data) >= 2:
                yearly_returns[year] = float(year_data.iloc[-1] / year_data.iloc[0] - 1)

        return yearly_returns
