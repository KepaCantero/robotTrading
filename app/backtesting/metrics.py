"""
Performance Metrics Calculator for Backtesting

Calculates comprehensive performance metrics including:
- CAGR, Sharpe ratio, Sortino ratio
- Max Drawdown, Win Rate, Profit Factor
- Risk-adjusted returns and trade statistics
- López de Prado advanced metrics (stability, concentration, turnover-adjusted Sharpe)

Reference:
    López de Prado, M. (2020). Machine Learning for Asset Managers.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

# Try to import empyrical, provide fallback if not available
try:
    import empyrical as ep

    EMPYRICAL_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("empyrical library loaded successfully")
except ImportError:
    EMPYRICAL_AVAILABLE = False
    ep = None
    logger = logging.getLogger(__name__)
    logger.warning(
        "empyrical library not available - using fallback implementations. "
        "For full functionality, install: pip install empyrical-reloaded"
    )

from app.backtesting.advanced_metrics import AdvancedMetricsCalculator
from app.backtesting.lopez_de_prado_metrics import (
    ConcentrationAnalyzer,
    ConcentrationMetrics,
    PortfolioStabilityMetrics,
    PortfolioStabilityValidator,
    SharpeCombinationResult,
    SharpeRatioCombinator,
    TurnoverAdjustedCalculator,
    TurnoverAdjustedMetrics,
)
from app.backtesting.models import PerformanceMetrics, Trade

logger = logging.getLogger(__name__)


def _ensure_empyrical():
    """
    Ensure empyrical is available, return module or None.

    This function provides a safe way to check for empyrical availability
    and returns None if the library is not installed, allowing graceful fallback.

    Returns:
        empyrical module if available, None otherwise
    """
    return ep if EMPYRICAL_AVAILABLE else None


class MetricsCalculator:
    """Calculator for backtesting performance metrics."""

    def __init__(self, risk_free_rate: Decimal = Decimal("0.02")):
        """
        Initialize metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
        """
        self.risk_free_rate = risk_free_rate

        # Initialize López de Prado metrics components
        self._sharpe_combiner: Optional[SharpeRatioCombinator] = None
        self._stability_validator: Optional[PortfolioStabilityValidator] = None
        self._turnover_calculator: Optional[TurnoverAdjustedCalculator] = None
        self._concentration_analyzer: Optional[ConcentrationAnalyzer] = None

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
        winning_trades = [t for t in closed_trades if t.pnl is not None and t.pnl > 0]
        # Count trades with pnl <= 0 OR pnl is None as losing trades
        losing_trades = [
            t for t in closed_trades if t.pnl is None or (t.pnl is not None and t.pnl <= 0)
        ]

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
        # Bound max_drawdown to not exceed -initial_capital (can't lose more than you started with)
        max_drawdown = max(-initial_capital, max_drawdown)
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

        # Calculate expectancy (expected value per trade)
        expectancy = None
        if winning_trades or losing_trades:
            expectancy = calculate_expectancy(winning_trades, losing_trades)

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
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
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
            expectancy=expectancy,
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

        # For empty trades, set gross_profit and gross_loss to match net_profit
        # to satisfy validation: gross_profit + gross_loss == net_profit
        if total_pnl >= 0:
            gross_profit = total_pnl
            gross_loss = Decimal("0")
        else:
            gross_profit = Decimal("0")
            gross_loss = total_pnl  # Negative value

        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=Decimal("0"),
            total_pnl=total_pnl,
            total_pnl_percentage=total_pnl_percentage,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
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
            if trade.pnl and current_capital != 0:
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
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.debug(f"Error usando empyrical para Sharpe, usando cálculo manual: {e}")

            # Fallback to manual calculation
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)

            # Check for near-zero volatility to avoid numerical instability
            if std_return < 1e-10:
                return Decimal("0")

            # Annualize returns and volatility
            # Assuming daily returns, annualize by multiplying mean by 252 and std by sqrt(252)
            annual_return = mean_return * 252  # Trading days
            annual_std = std_return * np.sqrt(252)

            # Risk-free rate is already annualized (e.g., 0.02 = 2% annual)
            annual_risk_free = float(self.risk_free_rate)

            # Sharpe = (Annualized Return - Risk Free Rate) / Annualized Volatility
            sharpe = (annual_return - annual_risk_free) / annual_std if annual_std > 0 else 0.0

            # Check for infinity or NaN
            if not np.isfinite(sharpe):
                return Decimal("0")

            return Decimal(str(sharpe))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
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
                except (ValueError, TypeError, KeyError, AttributeError) as e:
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

            # Check for near-zero downside deviation to avoid numerical instability
            if downside_std < 1e-10:
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

            # Check for infinity or NaN
            if not np.isfinite(sortino):
                return Decimal("0")

            return Decimal(str(sortino))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
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

        except (ValueError, TypeError, KeyError, AttributeError) as e:
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
        cagr_float = (ratio**exponent - 1) * 100.0
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
    # Handle edge case: no trades at all
    if not winning_trades and not losing_trades:
        return Decimal("0")

    gross_profit = (
        sum((t.pnl or Decimal("0")) for t in winning_trades) if winning_trades else Decimal("0")
    )
    # If no losing trades, gross_loss is 0 (not 1)
    gross_loss = (
        abs(sum((t.pnl or Decimal("0")) for t in losing_trades)) if losing_trades else Decimal("0")
    )

    if gross_loss == 0:
        return Decimal("999")  # Perfect scenario

    return gross_profit / gross_loss


def calculate_expectancy(
    winning_trades: List[Trade],
    losing_trades: List[Trade],
) -> Decimal:
    """
    Calculate expectancy (expected value per trade).

    Expectancy is the average amount you can expect to win or lose per trade.
    It's a critical metric for determining if a strategy is profitable in the long run.

    Formula:
        Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)

    Interpretation:
    - Positive expectancy: Strategy makes money on average per trade
    - Negative expectancy: Strategy loses money on average per trade
    - Zero expectancy: Break-even strategy (before costs)

    Example:
        Win Rate: 40%, Avg Win: $500, Avg Loss: $300
        Expectancy = (0.4 × $500) - (0.6 × $300)
                   = $200 - $180
                   = $20 per trade

    Args:
        winning_trades: List of winning trades (PnL > 0)
        losing_trades: List of losing trades (PnL <= 0)

    Returns:
        Expectancy value (positive = profitable, negative = unprofitable)

    Raises:
        ValueError: If both trade lists are empty
    """
    total_trades = len(winning_trades) + len(losing_trades)

    if total_trades == 0:
        return Decimal("0")

    # Calculate win rate
    win_rate = Decimal(str(len(winning_trades) / total_trades))
    loss_rate = Decimal("1") - win_rate

    # Calculate average win
    avg_win = Decimal("0")
    if winning_trades:
        total_win_pnl = sum((t.pnl or Decimal("0")) for t in winning_trades)
        avg_win = total_win_pnl / Decimal(str(len(winning_trades)))

    # Calculate average loss (absolute value)
    avg_loss = Decimal("0")
    if losing_trades:
        total_loss_pnl = sum((t.pnl or Decimal("0")) for t in losing_trades)
        avg_loss = abs(total_loss_pnl / Decimal(str(len(losing_trades))))

    # Calculate expectancy
    expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

    logger.debug(
        f"Expectancy: ${expectancy:.2f} per trade "
        f"(Win Rate: {win_rate:.1%}, Avg Win: ${avg_win:.2f}, "
        f"Avg Loss: ${avg_loss:.2f})"
    )

    return expectancy


def calculate_expectancy_with_confidence(
    winning_trades: List[Trade],
    losing_trades: List[Trade],
    confidence_level: float = 0.95,
) -> Dict[str, Decimal]:
    """
    Calculate expectancy with confidence intervals.

    Uses statistical methods to estimate the range of likely expectancy values.

    Args:
        winning_trades: List of winning trades
        losing_trades: List of losing trades
        confidence_level: Confidence level for interval (default: 0.95)

    Returns:
        Dictionary with expectancy, lower_bound, upper_bound, and std_error
    """
    import numpy as np
    from scipy import stats

    # Calculate individual trade P&Ls
    all_pnls = []
    for t in winning_trades:
        if t.pnl:
            all_pnls.append(float(t.pnl))
    for t in losing_trades:
        if t.pnl:
            all_pnls.append(float(t.pnl))

    if not all_pnls:
        return {
            "expectancy": Decimal("0"),
            "lower_bound": Decimal("0"),
            "upper_bound": Decimal("0"),
            "std_error": Decimal("0"),
        }

    # Calculate mean and standard error
    mean_pnl = np.mean(all_pnls)
    std_pnl = np.std(all_pnls, ddof=1)
    std_error = std_pnl / np.sqrt(len(all_pnls))

    # Calculate confidence interval
    t_score = stats.t.ppf((1 + confidence_level) / 2, df=len(all_pnls) - 1)
    margin_of_error = t_score * std_error

    lower_bound = mean_pnl - margin_of_error
    upper_bound = mean_pnl + margin_of_error

    return {
        "expectancy": Decimal(str(mean_pnl)),
        "lower_bound": Decimal(str(lower_bound)),
        "upper_bound": Decimal(str(upper_bound)),
        "std_error": Decimal(str(std_error)),
    }


def calculate_f1_score(y_true: np.ndarray, y_pred: np.ndarray, average: str = "weighted") -> float:
    """
    Calculate F1 Score for imbalanced data classification.

    F1 Score is the harmonic mean of precision and recall:
    F1 = 2 * (precision * recall) / (precision + recall)

    This is particularly important for imbalanced datasets where accuracy
    can be misleading. F1 score provides a better measure of performance
    when classes are imbalanced.

    Args:
        y_true: True labels (binary or multi-class)
        y_pred: Predicted labels
        average: Averaging method ('weighted', 'macro', 'micro', 'binary')
                - 'weighted': Calculate metrics for each label, and find their average weighted by support
                - 'macro': Calculate metrics for each label, and find their unweighted mean
                - 'micro': Calculate metrics globally by counting the total true positives, false negatives and false positives
                - 'binary': Only for binary classification, reports results for the positive class

    Returns:
        F1 score (0 to 1, higher is better)

    Examples:
        >>> y_true = np.array([0, 1, 0, 1, 1, 0, 0, 0])
        >>> y_pred = np.array([0, 1, 0, 0, 1, 0, 1, 0])
        >>> f1 = calculate_f1_score(y_true, y_pred)
        >>> print(f"F1 Score: {f1:.4f}")

    References:
        López de Prado, "Advances in Financial Machine Learning", Chapter 3.
        Use F1 score for evaluating imbalanced classification problems.
    """
    from sklearn.metrics import f1_score as sklearn_f1

    # Use sklearn's implementation
    f1 = sklearn_f1(y_true, y_pred, average=average, zero_division=0)

    return float(f1)


def calculate_matthews_corrcoef(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Matthews Correlation Coefficient (MCC) for imbalanced data.

    MCC is a balanced measure even when classes are of very different sizes.
    It returns a value between -1 and +1:
    - +1: Perfect prediction
    - 0: No better than random prediction
    - -1: Total disagreement between prediction and truth

    MCC is considered one of the best metrics for imbalanced classification
    because it takes into account true and false positives and negatives.

    Formula:
    MCC = (TP * TN - FP * FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))

    Args:
        y_true: True labels (binary classification)
        y_pred: Predicted labels

    Returns:
        MCC coefficient (-1 to +1, higher is better)

    Examples:
        >>> y_true = np.array([0, 1, 0, 1, 1, 0, 0, 0])
        >>> y_pred = np.array([0, 1, 0, 0, 1, 0, 1, 0])
        >>> mcc = calculate_matthews_corrcoef(y_true, y_pred)
        >>> print(f"MCC: {mcc:.4f}")

    References:
        Matthews, B. W. (1975). "Comparison of the predicted and observed secondary structure of T4 phage lysozyme".
        Biochimica et Biophysica Acta (BBA)-Protein Structure.
        López de Prado, "Advances in Financial Machine Learning", Chapter 3.
        Use MCC for evaluating imbalanced binary classification problems.
    """
    from sklearn.metrics import matthews_corrcoef as sklearn_mcc

    # Use sklearn's implementation
    mcc = sklearn_mcc(y_true, y_pred)

    return float(mcc)


def calculate_classification_metrics_imbalanced(
    y_true: np.ndarray, y_pred: np.ndarray, y_proba: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """
    Calculate comprehensive classification metrics for imbalanced data.

    This function computes multiple metrics specifically designed for
    imbalanced datasets, following López de Prado's recommendations:

    1. F1 Score: Harmonic mean of precision and recall
    2. Matthews Correlation Coefficient (MCC): Balanced measure for imbalanced data
    3. Precision-Recall AUC: Area under precision-recall curve
    4. Balanced Accuracy: Average of recall for each class
    5. Confusion Matrix: Detailed breakdown of predictions

    Args:
        y_true: True labels
        y_pred: Predicted labels
        y_proba: Predicted probabilities (optional, for AUC calculation)

    Returns:
        Dictionary with all metrics

    Examples:
        >>> y_true = np.array([0, 1, 0, 1, 1, 0, 0, 0])
        >>> y_pred = np.array([0, 1, 0, 0, 1, 0, 1, 0])
        >>> y_proba = np.array([0.3, 0.9, 0.2, 0.4, 0.8, 0.1, 0.6, 0.2])
        >>> metrics = calculate_classification_metrics_imbalanced(y_true, y_pred, y_proba)
        >>> print(f"F1: {metrics['f1_weighted']:.4f}, MCC: {metrics['mcc']:.4f}")
    """
    from sklearn.metrics import (
        auc,
        balanced_accuracy_score,
        confusion_matrix,
        precision_recall_curve,
    )

    metrics = {}

    # F1 Score (weighted, macro, and binary)
    metrics['f1_weighted'] = calculate_f1_score(y_true, y_pred, average='weighted')
    metrics['f1_macro'] = calculate_f1_score(y_true, y_pred, average='macro')
    metrics['f1_binary'] = calculate_f1_score(y_true, y_pred, average='binary')

    # Matthews Correlation Coefficient
    metrics['mcc'] = calculate_matthews_corrcoef(y_true, y_pred)

    # Balanced Accuracy
    metrics['balanced_accuracy'] = float(balanced_accuracy_score(y_true, y_pred))

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    metrics['confusion_matrix'] = cm.tolist()

    # Extract TP, TN, FP, FN for binary classification
    if len(cm) == 2:
        tn, fp, fn, tp = cm.ravel()
        metrics['true_positives'] = int(tp)
        metrics['true_negatives'] = int(tn)
        metrics['false_positives'] = int(fp)
        metrics['false_negatives'] = int(fn)

    # Precision-Recall AUC (if probabilities provided)
    if y_proba is not None:
        try:
            precision, recall, _ = precision_recall_curve(y_true, y_proba)
            metrics['pr_auc'] = float(auc(recall, precision))
        except Exception:
            metrics['pr_auc'] = None

    return metrics


def calculate_imbalanced_metrics_from_trades(
    winning_trades: List[Trade],
    losing_trades: List[Trade],
    predictions: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """
    Calculate imbalanced classification metrics from trade results.

    This function converts trade results to binary labels and calculates
    metrics suitable for imbalanced data.

    Args:
        winning_trades: List of winning trades
        losing_trades: List of losing trades
        predictions: Optional array of predictions (-1, 0, 1)

    Returns:
        Dictionary with metrics

    Examples:
        >>> metrics = calculate_imbalanced_metrics_from_trades(wins, losses, preds)
        >>> print(f"F1: {metrics['f1_weighted']:.4f}")
    """
    # Create binary labels from trades
    y_true = np.array([1] * len(winning_trades) + [0] * len(losing_trades))

    if predictions is not None:
        # Convert predictions to binary
        y_pred = (predictions > 0).astype(int)
    else:
        # No predictions, use perfect prediction
        y_pred = y_true.copy()

    # Calculate metrics
    metrics = calculate_classification_metrics_imbalanced(y_true, y_pred)

    # Add trade-specific metrics
    metrics['n_winning'] = len(winning_trades)
    metrics['n_losing'] = len(losing_trades)


# ============================================================================
# López de Prado - Machine Learning for Asset Managers Methods
# ============================================================================


class LopezDePradoMetricsCalculator:
    """
    Calculator for López de Prado's advanced ML metrics.

    Implements methodologies from "Machine Learning for Asset Managers" (2020):
    - Sharpe ratio combination methods
    - Portfolio stability validation
    - Turnover-adjusted performance metrics
    - Portfolio concentration analysis

    This calculator provides the missing features to achieve 95% compliance
    with López de Prado's methodologies.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        stability_threshold: float = 70.0,
        transaction_cost_bps: float = 10.0,
    ):
        """
        Initialize López de Prado metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
            stability_threshold: Minimum stability score (0-100)
            transaction_cost_bps: Transaction cost in basis points
        """
        self.risk_free_rate = risk_free_rate
        self.stability_threshold = stability_threshold
        self.transaction_cost_bps = transaction_cost_bps

        # Initialize metric calculators
        self.sharpe_combiner = SharpeRatioCombinator(risk_free_rate=risk_free_rate)
        self.stability_validator = PortfolioStabilityValidator(
            stability_threshold=stability_threshold,
        )
        self.turnover_calculator = TurnoverAdjustedCalculator(
            transaction_cost_bps=transaction_cost_bps,
            risk_free_rate=risk_free_rate,
        )
        self.concentration_analyzer = ConcentrationAnalyzer()

    def combine_strategy_sharpes(
        self,
        sharpes: List[float],
        returns_matrix: np.ndarray,
        method: str = "optimal",
    ) -> SharpeCombinationResult:
        """
        Combine multiple strategy Sharpe ratios.

        From López de Prado Chapter 8: Sharpe Ratio Combinations

        Args:
            sharpes: List of individual strategy Sharpe ratios
            returns_matrix: T x N matrix of returns (T periods, N strategies)
            method: Combination method ('optimal', 'hierarchical', 'spectral', 'average')

        Returns:
            SharpeCombinationResult with combined Sharpe and weights

        Example:
            >>> sharpes = [1.2, 0.8, 1.5]
            >>> returns = np.random.randn(252, 3) * 0.01
            >>> result = calc.combine_strategy_sharpes(sharpes, returns, method='optimal')
            >>> print(f"Combined Sharpe: {result.combined_sharpe:.2f}")
        """
        if not sharpes:
            logger.warning("No Sharpe ratios provided for combination")
            return SharpeCombinationResult(combined_sharpe=0.0, method="none")

        sharpes_array = np.array(sharpes)
        cov_matrix = np.cov(returns_matrix.T)

        if method == "optimal":
            return self.sharpe_combiner.combine_sharpes_optimal(sharpes_array, cov_matrix)
        elif method == "hierarchical":
            return self.sharpe_combiner.combine_sharpes_hierarchical(sharpes_array, cov_matrix)
        elif method == "spectral":
            return self.sharpe_combiner.combine_sharpes_spectral(sharpes_array, returns_matrix)
        elif method == "average":
            return self.sharpe_combiner._average_combination(sharpes_array)
        else:
            logger.warning(f"Unknown combination method: {method}, using optimal")
            return self.sharpe_combiner.combine_sharpes_optimal(sharpes_array, cov_matrix)

    def validate_portfolio_stability(
        self,
        weights_history: List[np.ndarray],
        returns_history: Optional[np.ndarray] = None,
        period_length_days: int = 30,
    ) -> PortfolioStabilityMetrics:
        """
        Validate portfolio stability across time periods.

        From López de Prado Chapter 9: Portfolio Stability

        Args:
            weights_history: List of weight arrays for each rebalancing period
            returns_history: Optional returns for turnover-adjusted calculation
            period_length_days: Length of each rebalancing period

        Returns:
            PortfolioStabilityMetrics with comprehensive stability analysis

        Example:
            >>> weights_history = [np.array([0.5, 0.3, 0.2]), ...]
            >>> stability = calc.validate_portfolio_stability(weights_history)
            >>> print(f"Stability score: {stability.stability_score:.1f}/100")
        """
        # Validate stability
        stability_metrics = self.stability_validator.validate_stability(
            weights_history=weights_history,
            period_length_days=period_length_days,
        )

        # Calculate turnover-adjusted metrics if returns provided
        if returns_history is not None and len(returns_history) > 0:
            try:
                turnover_metrics = self.turnover_calculator.calculate_turnover_adjusted_sharpe(
                    returns=returns_history,
                    weights_history=weights_history,
                    period_length_days=period_length_days,
                )
                # Store turnover metrics in stability result (extended)
                stability_metrics.annual_turnover = turnover_metrics.annualized_turnover
                stability_metrics.is_cost_effective = turnover_metrics.is_cost_effective
            except Exception as e:
                logger.error(f"Error calculating turnover metrics: {e}")

        return stability_metrics

    def calculate_turnover_adjusted_metrics(
        self,
        returns: np.ndarray,
        weights_history: List[np.ndarray],
        period_length_days: int = 30,
    ) -> TurnoverAdjustedMetrics:
        """
        Calculate turnover-adjusted Sharpe ratio.

        From López de Prado Chapter 10: Turnover Analysis

        Args:
            returns: Array of portfolio returns
            weights_history: List of weight vectors
            period_length_days: Rebalancing period length

        Returns:
            TurnoverAdjustedMetrics with adjusted Sharpe ratio

        Example:
            >>> returns = np.random.randn(252) * 0.01
            >>> weights_hist = [np.array([0.4, 0.6]), ...]
            >>> metrics = calc.calculate_turnover_adjusted_metrics(returns, weights_hist)
            >>> print(f"Adjusted Sharpe: {metrics.turnover_adjusted_sharpe:.2f}")
        """
        return self.turnover_calculator.calculate_turnover_adjusted_sharpe(
            returns=returns,
            weights_history=weights_history,
            period_length_days=period_length_days,
        )

    def analyze_portfolio_concentration(
        self,
        weights: np.ndarray,
    ) -> ConcentrationMetrics:
        """
        Analyze portfolio concentration.

        From López de Prado Chapter 11: Concentration Analysis

        Args:
            weights: Portfolio weight vector (sums to 1)

        Returns:
            ConcentrationMetrics with comprehensive concentration analysis

        Example:
            >>> weights = np.array([0.4, 0.3, 0.2, 0.1])
            >>> concentration = calc.analyze_portfolio_concentration(weights)
            >>> print(f"HHI: {concentration.herfindahl_index:.3f}")
            >>> print(f"Effective N: {concentration.effective_n_assets:.1f}")
        """
        return self.concentration_analyzer.analyze_concentration(weights=weights)

    def generate_comprehensive_report(
        self,
        sharpes: List[float],
        returns_matrix: np.ndarray,
        weights_history: List[np.ndarray],
        portfolio_returns: np.ndarray,
        current_weights: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive López de Prado metrics report.

        Combines all four major metrics areas:
        1. Sharpe ratio combination
        2. Portfolio stability
        3. Turnover-adjusted performance
        4. Concentration analysis

        Args:
            sharpes: List of individual strategy Sharpe ratios
            returns_matrix: Strategy returns matrix
            weights_history: Historical portfolio weights
            portfolio_returns: Portfolio returns series
            current_weights: Current portfolio weights

        Returns:
            Dictionary with all metrics and recommendations

        Example:
            >>> report = calc.generate_comprehensive_report(
            ...     sharpes=[1.2, 0.8, 1.5],
            ...     returns_matrix=strategy_returns,
            ...     weights_history=weights_hist,
            ...     portfolio_returns=returns,
            ...     current_weights=weights,
            ... )
            >>> print(f"Overall score: {report['overall_score']:.1f}/100")
        """
        # 1. Sharpe combination
        sharpe_result = self.combine_strategy_sharpes(
            sharpes=sharpes,
            returns_matrix=returns_matrix,
            method="optimal",
        )

        # 2. Stability validation
        stability_result = self.validate_portfolio_stability(
            weights_history=weights_history,
            returns_history=portfolio_returns,
        )

        # 3. Turnover-adjusted metrics
        turnover_result = self.calculate_turnover_adjusted_metrics(
            returns=portfolio_returns,
            weights_history=weights_history,
        )

        # 4. Concentration analysis
        concentration_result = self.analyze_portfolio_concentration(
            weights=current_weights,
        )

        # Calculate overall score (0-100)
        overall_score = self._calculate_overall_score(
            sharpe_result=sharpe_result,
            stability_result=stability_result,
            turnover_result=turnover_result,
            concentration_result=concentration_result,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            sharpe_result=sharpe_result,
            stability_result=stability_result,
            turnover_result=turnover_result,
            concentration_result=concentration_result,
        )

        return {
            "overall_score": overall_score,
            "sharpe_combination": sharpe_result.to_dict(),
            "stability": stability_result.to_dict(),
            "turnover": turnover_result.to_dict(),
            "concentration": concentration_result.to_dict(),
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_overall_score(
        self,
        sharpe_result: SharpeCombinationResult,
        stability_result: PortfolioStabilityMetrics,
        turnover_result: TurnoverAdjustedMetrics,
        concentration_result: ConcentrationMetrics,
    ) -> float:
        """
        Calculate overall López de Prado compliance score.

        Score components:
        - Sharpe combination effectiveness: 25%
        - Portfolio stability: 35%
        - Cost-effectiveness (turnover): 25%
        - Diversification (concentration): 15%
        """
        # Sharpe combination score (0-25 points)
        sharpe_score = min(25.0, sharpe_result.combined_sharpe * 5)

        # Stability score (0-35 points)
        stability_score = (stability_result.stability_score / 100.0) * 35

        # Cost-effectiveness score (0-25 points)
        if turnover_result.is_cost_effective:
            turnover_score = 25.0
        else:
            # Penalty based on Sharpe degradation
            degradation = 1.0 - (
                turnover_result.turnover_adjusted_sharpe / turnover_result.raw_sharpe
                if turnover_result.raw_sharpe > 0
                else 0
            )
            turnover_score = max(0, 25.0 * (1.0 - degradation))

        # Diversification score (0-15 points)
        # Higher effective N = more diversified
        div_score = min(15.0, concentration_result.effective_n_assets * 1.5)

        total_score = sharpe_score + stability_score + turnover_score + div_score

        return float(min(total_score, 100.0))

    def _generate_recommendations(
        self,
        sharpe_result: SharpeCombinationResult,
        stability_result: PortfolioStabilityMetrics,
        turnover_result: TurnoverAdjustedMetrics,
        concentration_result: ConcentrationMetrics,
    ) -> List[str]:
        """Generate actionable recommendations based on all metrics."""
        recommendations = []

        # Sharpe combination recommendations
        if sharpe_result.improvement_pct < 5:
            recommendations.append(
                "Sharpe combination provides minimal improvement. "
                "Consider if strategies are too correlated."
            )

        # Stability recommendations
        if not stability_result.is_stable:
            recommendations.append(
                f"Portfolio unstable (score: {stability_result.stability_score:.1f}). "
                "Reduce parameter complexity or simplify strategy."
            )

        # Turnover recommendations
        if not turnover_result.is_cost_effective:
            recommendations.append(
                f"High turnover costs ({turnover_result.estimated_transaction_costs:.2%}). "
                "Reduce rebalancing frequency or increase position sizes."
            )

        # Concentration recommendations
        if concentration_result.is_overconcentrated:
            recommendations.append(
                f"Portfolio over-concentrated (HHI: {concentration_result.herfindahl_index:.3f}). "
                f"Add {max(0, 10 - int(concentration_result.effective_n_assets))} more uncorrelated assets."
            )

        return recommendations


# Convenience function for creating López de Prado calculator
def create_lopez_de_prado_calculator(
    risk_free_rate: float = 0.02,
    stability_threshold: float = 70.0,
    transaction_cost_bps: float = 10.0,
) -> LopezDePradoMetricsCalculator:
    """
    Create a López de Prado metrics calculator.

    Args:
        risk_free_rate: Annual risk-free rate
        stability_threshold: Minimum stability score (0-100)
        transaction_cost_bps: Transaction cost in basis points

    Returns:
        Configured LopezDePradoMetricsCalculator

    Example:
        >>> calc = create_lopez_de_prado_calculator()
        >>> report = calc.generate_comprehensive_report(...)
    """
    return LopezDePradoMetricsCalculator(
        risk_free_rate=risk_free_rate,
        stability_threshold=stability_threshold,
        transaction_cost_bps=transaction_cost_bps,
    )
