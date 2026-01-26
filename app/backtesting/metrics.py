"""
Performance Metrics Calculator for Backtesting

Calculates comprehensive performance metrics including:
- CAGR, Sharpe ratio, Sortino ratio
- Max Drawdown, Win Rate, Profit Factor
- Risk-adjusted returns and trade statistics
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import numpy as np

from app.backtesting.advanced_metrics import AdvancedMetricsCalculator
from app.backtesting.models import PerformanceMetrics, Trade

logger = logging.getLogger(__name__)

# Optional: empyrical-reloaded for standard financial metrics
# Note: empyrical imports yfinance which uses Python 3.10+ union syntax
# We use lazy import to avoid this issue at module load time
_ep = None
EMPYRICAL_AVAILABLE = False


def _ensure_empyrical():
    """Lazy import empyrical to avoid Python version compatibility issues."""
    global _ep, EMPYRICAL_AVAILABLE
    if _ep is None:
        try:
            import empyrical as ep_module

            _ep = ep_module
            EMPYRICAL_AVAILABLE = True
        except (ImportError, TypeError) as e:
            # TypeError occurs on Python 3.9 due to yfinance dependency
            EMPYRICAL_AVAILABLE = False
            _ep = None
            logger.debug(f"empyrical-reloaded not available: {e}")
    return _ep


class MetricsCalculator:
    """Calculator for backtesting performance metrics."""

    def __init__(self, risk_free_rate: Decimal = Decimal("0.02")):
        """
        Initialize metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_all_metrics(
        self,
        trades: List[Trade],
        initial_capital: Decimal,
        final_capital: Decimal,
        start_date: datetime,
        end_date: datetime,
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.

        Args:
            trades: List of completed trades
            initial_capital: Starting capital
            final_capital: Ending capital
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            PerformanceMetrics object
        """
        # Filter only closed trades
        closed_trades = [t for t in trades if t.status.value == "closed"]

        if not closed_trades:
            logger.warning("No closed trades to calculate metrics")
            return self._empty_metrics(initial_capital, final_capital, start_date, end_date)

        # Basic metrics
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl and t.pnl <= 0]

        # Calculate win rate (asegurar que esté entre 0-100)
        if total_trades > 0:
            win_rate = Decimal(str((len(winning_trades) / total_trades) * 100))
            # Asegurar que no exceda 100 (por redondeos)
            win_rate = min(Decimal("100"), max(Decimal("0"), win_rate))
        else:
            win_rate = Decimal("0")

        # P&L metrics
        total_pnl = sum((t.pnl or Decimal("0")) for t in closed_trades)

        # Validate initial_capital before division
        if initial_capital <= 0:
            raise ValueError(f"initial_capital must be positive, got {initial_capital}")

        total_pnl_percentage = (total_pnl / initial_capital) * Decimal("100")

        gross_profit = (
            sum((t.pnl or Decimal("0")) for t in winning_trades) if winning_trades else Decimal("0")
        )
        gross_loss = (
            sum((t.pnl or Decimal("0")) for t in losing_trades) if losing_trades else Decimal("0")
        )
        net_profit = gross_profit + gross_loss

        # Risk metrics
        equity_curve = self._build_equity_curve(closed_trades, initial_capital)
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        # Asegurar que max_drawdown sea <= 0 (validación Pydantic)
        max_drawdown = min(Decimal("0"), max_drawdown)
        max_drawdown_percentage = min(
            Decimal("0"),
            (
                (max_drawdown / initial_capital) * Decimal("100")
                if initial_capital > 0
                else Decimal("0")
            ),
        )

        # Calculate returns for Sharpe/Sortino
        daily_returns = self._calculate_daily_returns(closed_trades, initial_capital)
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns) if daily_returns else None
        sortino_ratio = self._calculate_sortino_ratio(daily_returns) if daily_returns else None

        # Risk/Reward Ratio (TASK-MET-2: Average risk/reward per trade, target ≥1:3)
        risk_reward_ratio = (
            self._calculate_risk_reward_ratio(closed_trades) if closed_trades else None
        )

        # Trade statistics
        avg_win = (
            (sum((t.pnl or Decimal("0")) for t in winning_trades) / len(winning_trades))
            if winning_trades
            else Decimal("0")
        )
        avg_loss = (
            (sum((t.pnl or Decimal("0")) for t in losing_trades) / len(losing_trades))
            if losing_trades
            else Decimal("0")
        )
        largest_win = (
            max((t.pnl or Decimal("0")) for t in winning_trades) if winning_trades else Decimal("0")
        )
        largest_loss = (
            min((t.pnl or Decimal("0")) for t in losing_trades) if losing_trades else Decimal("0")
        )

        # Time metrics
        total_days = (end_date - start_date).days
        avg_trade_duration = self._calculate_avg_trade_duration(closed_trades)

        # Calculate advanced metrics (PHASE 4 MODULE 7)
        advanced_metrics = {}
        try:
            if daily_returns and equity_curve and total_days > 0:
                # Calculate CAGR for Calmar and Recovery Factor
                cagr = self.calculate_cagr(initial_capital, final_capital, start_date, end_date)

                # Initialize advanced metrics calculator
                adv_calc = AdvancedMetricsCalculator(risk_free_rate=self.risk_free_rate)

                # Calculate all advanced metrics
                advanced_metrics = adv_calc.calculate_all_advanced_metrics(
                    returns=daily_returns,
                    equity_curve=equity_curve,
                    cagr=cagr,
                    max_drawdown=max_drawdown,
                    total_pnl=total_pnl,
                    gross_profit=gross_profit,
                    gross_loss=abs(gross_loss),  # Use absolute value for loss
                )
                logger.debug(f"Advanced metrics calculated: {list(advanced_metrics.keys())}")
            else:
                logger.debug("Insufficient data for advanced metrics calculation")
        except Exception as e:
            logger.error(f"Error calculating advanced metrics: {e}")

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percentage=total_pnl_percentage,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            max_drawdown=max_drawdown,
            max_drawdown_percentage=max_drawdown_percentage,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            risk_reward_ratio=risk_reward_ratio,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_days=total_days,
            avg_trade_duration=avg_trade_duration,
            # Advanced metrics
            calmar_ratio=advanced_metrics.get("calmar_ratio"),
            omega_ratio=advanced_metrics.get("omega_ratio"),
            ulcer_index=advanced_metrics.get("ulcer_index"),
            volatility_annualized=advanced_metrics.get("volatility_annualized"),
            recovery_factor=advanced_metrics.get("recovery_factor"),
            profit_factor=advanced_metrics.get("profit_factor"),
            skewness=advanced_metrics.get("skewness"),
            kurtosis=advanced_metrics.get("kurtosis"),
            var_95=advanced_metrics.get("var_95"),
            cvar_95=advanced_metrics.get("cvar_95"),
        )

    def _empty_metrics(
        self,
        initial_capital: Decimal,
        final_capital: Decimal,
        start_date: datetime,
        end_date: datetime,
    ) -> PerformanceMetrics:
        """Return empty metrics for no trades scenario."""
        total_days = (end_date - start_date).days
        total_pnl = final_capital - initial_capital

        # Validate initial_capital before division
        if initial_capital <= 0:
            raise ValueError(f"initial_capital must be positive, got {initial_capital}")

        total_pnl_percentage = (total_pnl / initial_capital) * Decimal("100")

        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=Decimal("0"),
            total_pnl=total_pnl,
            total_pnl_percentage=total_pnl_percentage,
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
            net_profit=total_pnl,
            max_drawdown=Decimal("0"),
            max_drawdown_percentage=Decimal("0"),
            sharpe_ratio=None,
            sortino_ratio=None,
            risk_reward_ratio=None,
            avg_win=Decimal("0"),
            avg_loss=Decimal("0"),
            largest_win=Decimal("0"),
            largest_loss=Decimal("0"),
            total_days=total_days,
            avg_trade_duration=Decimal("0"),
            # Advanced metrics (all None for no trades)
            calmar_ratio=None,
            omega_ratio=None,
            ulcer_index=None,
            volatility_annualized=None,
            recovery_factor=None,
            profit_factor=None,
            skewness=None,
            kurtosis=None,
            var_95=None,
            cvar_95=None,
        )

    def _build_equity_curve(self, trades: List[Trade], initial_capital: Decimal) -> List[Decimal]:
        """Build equity curve from trades."""
        equity = [initial_capital]
        current = initial_capital

        for trade in sorted(trades, key=lambda t: t.entry_time):
            if trade.pnl:
                current += trade.pnl
            equity.append(current)

        return equity

    def _calculate_max_drawdown(self, equity_curve: List[Decimal]) -> Decimal:
        """Calculate maximum drawdown."""
        if len(equity_curve) < 2:
            return Decimal("0")

        peak = equity_curve[0]
        max_dd = Decimal("0")

        for equity in equity_curve[1:]:
            if equity > peak:
                peak = equity
            dd = equity - peak
            if dd < max_dd:
                max_dd = dd

        return max_dd

    def _calculate_daily_returns(
        self, trades: List[Trade], initial_capital: Decimal
    ) -> List[Decimal]:
        """Calculate daily returns from trades."""
        # Simplified: convert trade P&L to daily returns
        returns = []
        current_capital = initial_capital

        for trade in sorted(trades, key=lambda t: t.entry_time):
            if trade.pnl:
                daily_return = trade.pnl / current_capital
                returns.append(daily_return)
                current_capital += trade.pnl

        return returns

    def _calculate_sharpe_ratio(self, returns: List[Decimal]) -> Optional[Decimal]:
        """Calculate Sharpe ratio using empyrical if available, otherwise manual."""
        if not returns or len(returns) < 2:
            return None

        try:
            returns_array = np.array([float(r) for r in returns])

            # Use empyrical if available (industry standard)
            ep_module = _ensure_empyrical()
            if ep_module is not None:
                try:
                    # Convert annual risk-free rate to daily for empyrical
                    # (empyrical expects daily rate when period='daily')
                    daily_risk_free = float(self.risk_free_rate) / 252
                    sharpe = ep_module.sharpe_ratio(
                        returns_array, risk_free=daily_risk_free, period='daily', annualization=252
                    )
                    # Handle NaN
                    if np.isnan(sharpe) or np.isinf(sharpe):
                        return Decimal("0")
                    return Decimal(str(sharpe))
                except Exception as e:
                    logger.debug(f"Error usando empyrical para Sharpe, usando cálculo manual: {e}")

            # Fallback to manual calculation
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)

            if std_return == 0:
                return Decimal("0")

            # Annualize returns and volatility
            # Assuming daily returns, annualize by multiplying mean by 252 and std by sqrt(252)
            annual_return = mean_return * 252  # Trading days
            annual_std = std_return * np.sqrt(252)

            # Risk-free rate is already annualized (e.g., 0.02 = 2% annual)
            annual_risk_free = float(self.risk_free_rate)

            # Sharpe = (Annualized Return - Risk Free Rate) / Annualized Volatility
            sharpe = (annual_return - annual_risk_free) / annual_std if annual_std > 0 else 0.0
            return Decimal(str(sharpe))

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return None

    def _calculate_sortino_ratio(self, returns: List[Decimal]) -> Optional[Decimal]:
        """Calculate Sortino ratio using empyrical if available, otherwise manual."""
        if not returns or len(returns) < 2:
            return None

        try:
            returns_array = np.array([float(r) for r in returns])

            # Use empyrical if available (industry standard)
            ep_module = _ensure_empyrical()
            if ep_module is not None:
                try:
                    # Convert annual risk-free rate to daily for empyrical
                    daily_risk_free = float(self.risk_free_rate) / 252
                    sortino = ep_module.sortino_ratio(
                        returns_array, risk_free=daily_risk_free, period='daily', annualization=252
                    )
                    # Handle NaN
                    if np.isnan(sortino) or np.isinf(sortino):
                        return Decimal("0")
                    return Decimal(str(sortino))
                except Exception as e:
                    logger.debug(f"Error usando empyrical para Sortino, usando cálculo manual: {e}")

            # Fallback to manual calculation
            mean_return = np.mean(returns_array)

            # Calculate downside deviation (correct formula)
            # Target is daily risk-free rate, not zero
            daily_risk_free = float(self.risk_free_rate) / 252
            target_return = daily_risk_free

            # Downside deviation: sqrt(mean(min(r - target, 0)^2))
            # Only count returns below target, penalizing them by squared distance
            downside_diff = np.minimum(returns_array - target_return, 0)
            downside_squared = downside_diff**2

            if len(downside_squared) == 0 or np.sum(downside_squared) == 0:
                return Decimal("0")

            # Downside deviation (target-based semi-deviation)
            downside_std = np.sqrt(np.mean(downside_squared))

            if downside_std == 0:
                return Decimal("0")

            # Annualize
            annual_return = mean_return * 252
            annual_risk_free = float(self.risk_free_rate)
            annual_downside_std = downside_std * np.sqrt(252)

            # Sortino = (Annualized Return - Risk Free) / Annualized Downside Deviation
            sortino = (
                (annual_return - annual_risk_free) / annual_downside_std
                if annual_downside_std > 0
                else 0.0
            )
            return Decimal(str(sortino))

        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return None

    def _calculate_risk_reward_ratio(self, trades: List[Trade]) -> Optional[Decimal]:
        """
        Calculate average risk/reward ratio per trade (TASK-MET-2).

        Risk/Reward = Average Win / Average Loss (absolute values)
        Target: ≥1:3 (for every $1 risked, expect $3 reward)
        """
        try:
            if not trades:
                return None

            # Get winning and losing trades
            wins = [t for t in trades if t.pnl and t.pnl > 0]
            losses = [t for t in trades if t.pnl and t.pnl < 0]

            if not wins or not losses:
                return None

            # Calculate average win and average loss (absolute values)
            avg_win = sum(abs(t.pnl or Decimal("0")) for t in wins) / len(wins)
            avg_loss = abs(sum(t.pnl or Decimal("0") for t in losses) / len(losses))

            if avg_loss == 0:
                return None

            # Risk/Reward = Avg Win / Avg Loss
            # Example: $300 avg win / $100 avg loss = 3:1 ratio
            risk_reward = avg_win / avg_loss

            return Decimal(str(risk_reward))

        except Exception as e:
            logger.error(f"Error calculating risk/reward ratio: {e}")
            return None

    def _calculate_avg_trade_duration(self, trades: List[Trade]) -> Decimal:
        """Calculate average trade duration in days."""
        durations = []
        for trade in trades:
            if trade.exit_time and trade.entry_time:
                duration = (trade.exit_time - trade.entry_time).days
                durations.append(Decimal(str(duration)))

        if not durations:
            return Decimal("0")

        return sum(durations) / len(durations)

    def calculate_cagr(
        self,
        initial_capital: Decimal,
        final_capital: Decimal,
        start_date: datetime,
        end_date: datetime,
    ) -> Decimal:
        """
        Calculate Compound Annual Growth Rate.

        Args:
            initial_capital: Starting capital (must be > 0)
            final_capital: Ending capital (must be > 0)
            start_date: Start date
            end_date: End date (must be after start_date)

        Returns:
            CAGR as percentage

        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        if initial_capital <= 0:
            raise ValueError(f"initial_capital must be positive, got {initial_capital}")

        if final_capital <= 0:
            raise ValueError(f"final_capital must be positive, got {final_capital}")

        if start_date >= end_date:
            raise ValueError(f"start_date ({start_date}) must be before end_date ({end_date})")

        years = (end_date - start_date).days / 365.25

        if years <= 0:
            raise ValueError(f"Time period must be positive, got {years:.4f} years")

        # Convert to float for exponentiation, then back to Decimal
        ratio = float(final_capital) / float(initial_capital)
        exponent = 1.0 / years
        cagr_float = (ratio ** exponent - 1) * 100.0
        cagr = Decimal(str(round(cagr_float, 4)))
        return cagr


def calculate_profit_factor(winning_trades: List[Trade], losing_trades: List[Trade]) -> Decimal:
    """
    Calculate profit factor.

    Args:
        winning_trades: List of winning trades
        losing_trades: List of losing trades

    Returns:
        Profit factor
    """
    gross_profit = (
        sum((t.pnl or Decimal("0")) for t in winning_trades) if winning_trades else Decimal("0")
    )
    gross_loss = (
        abs(sum((t.pnl or Decimal("0")) for t in losing_trades)) if losing_trades else Decimal("1")
    )

    if gross_loss == 0:
        return Decimal("999")  # Perfect scenario

    return gross_profit / gross_loss
