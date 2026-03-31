"""
T9.1 QuantStatsIntegrator - Advanced metrics calculation wrapper

Wraps quantstats library to calculate advanced performance metrics beyond basic set.

Responsibilities:
- Calculate advanced statistical metrics (Calmar, Stability, Tail Ratio)
- Generate statistics reports with full metric coverage
- Provide stability and risk analysis
- Metric aggregation and formatting
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class AdvancedMetrics:
    """Container for advanced performance metrics."""

    def __init__(
        self,
        calmar_ratio: Decimal,
        stability_index: Decimal,
        tail_ratio: Decimal,
        var_95: Decimal,
        cvar_95: Decimal,
        omega_ratio: Decimal,
        sortino_ratio: Decimal,
        information_ratio: Optional[Decimal] = None,
        kurtosis: Optional[Decimal] = None,
        skewness: Optional[Decimal] = None,
    ):
        """Initialize advanced metrics."""
        self.calmar_ratio = calmar_ratio
        self.stability_index = stability_index
        self.tail_ratio = tail_ratio
        self.var_95 = var_95  # Value at Risk at 95% confidence
        self.cvar_95 = cvar_95  # Conditional VaR (Expected Shortfall)
        self.omega_ratio = omega_ratio  # Probability-weighted ratio of gains to losses
        self.sortino_ratio = sortino_ratio
        self.information_ratio = information_ratio
        self.kurtosis = kurtosis  # Tail heaviness
        self.skewness = skewness  # Distribution asymmetry

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "calmar_ratio": float(self.calmar_ratio),
            "stability_index": float(self.stability_index),
            "tail_ratio": float(self.tail_ratio),
            "var_95": float(self.var_95),
            "cvar_95": float(self.cvar_95),
            "omega_ratio": float(self.omega_ratio),
            "sortino_ratio": float(self.sortino_ratio),
            "information_ratio": float(self.information_ratio) if self.information_ratio else None,
            "kurtosis": float(self.kurtosis) if self.kurtosis else None,
            "skewness": float(self.skewness) if self.skewness else None,
        }


class StatisticsReport:
    """Comprehensive statistics report."""

    def __init__(
        self,
        report_date: datetime,
        total_return_pct: Decimal,
        annual_return_pct: Decimal,
        annual_volatility_pct: Decimal,
        sharpe_ratio: Decimal,
        max_drawdown_pct: Decimal,
        win_rate_pct: Decimal,
        advanced_metrics: AdvancedMetrics,
        num_trades: int,
        best_day_pct: Decimal,
        worst_day_pct: Decimal,
        best_month_pct: Decimal,
        worst_month_pct: Decimal,
        monthly_return_distribution: Optional[dict] = None,
    ):
        """Initialize statistics report."""
        self.report_date = report_date
        self.total_return_pct = total_return_pct
        self.annual_return_pct = annual_return_pct
        self.annual_volatility_pct = annual_volatility_pct
        self.sharpe_ratio = sharpe_ratio
        self.max_drawdown_pct = max_drawdown_pct
        self.win_rate_pct = win_rate_pct
        self.advanced_metrics = advanced_metrics
        self.num_trades = num_trades
        self.best_day_pct = best_day_pct
        self.worst_day_pct = worst_day_pct
        self.best_month_pct = best_month_pct
        self.worst_month_pct = worst_month_pct
        self.monthly_return_distribution = monthly_return_distribution or {}

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "report_date": self.report_date.isoformat(),
            "total_return_pct": float(self.total_return_pct),
            "annual_return_pct": float(self.annual_return_pct),
            "annual_volatility_pct": float(self.annual_volatility_pct),
            "sharpe_ratio": float(self.sharpe_ratio),
            "max_drawdown_pct": float(self.max_drawdown_pct),
            "win_rate_pct": float(self.win_rate_pct),
            "advanced_metrics": self.advanced_metrics.to_dict(),
            "num_trades": self.num_trades,
            "best_day_pct": float(self.best_day_pct),
            "worst_day_pct": float(self.worst_day_pct),
            "best_month_pct": float(self.best_month_pct),
            "worst_month_pct": float(self.worst_month_pct),
            "monthly_return_distribution": {
                k: float(v) for k, v in self.monthly_return_distribution.items()
            },
        }


class QuantStatsIntegrator:
    """
    Wrapper around quantstats library for advanced metrics calculation.

    Provides methods for:
    - Advanced metric calculation
    - Statistics report generation
    - Risk analysis (VaR, CVaR, tail ratio)
    - Stability and distribution analysis
    - Metric aggregation and formatting
    """

    def __init__(self):
        """Initialize quantstats integrator."""
        self.reports_generated = 0
        logger.info("✅ QuantStatsIntegrator initialized")

    # ========================================================================
    # Advanced Metrics Calculation
    # ========================================================================

    def calculate_advanced_metrics(
        self,
        returns: list[Decimal],
        benchmark_returns: Optional[list[Decimal]] = None,
        max_drawdown_pct: Optional[Decimal] = None,
    ) -> AdvancedMetrics:
        """
        Calculate advanced performance metrics.

        Args:
            returns: Series of returns (e.g., daily returns)
            benchmark_returns: Optional benchmark returns for comparison
            max_drawdown_pct: Maximum drawdown for Calmar calculation

        Returns:
            AdvancedMetrics with calculated values
        """
        # Convert to numpy array, handling both Decimal and float inputs
        if returns and isinstance(returns[0], Decimal):
            returns_array = np.array([float(r) for r in returns])
        else:
            returns_array = np.array(returns)

        # Calculate Calmar ratio
        calmar = self._calculate_calmar_ratio(returns_array, max_drawdown_pct)

        # Calculate stability index
        stability = self._calculate_stability_index(returns_array)

        # Calculate tail ratio
        tail_ratio = self._calculate_tail_ratio(returns_array)

        # Calculate Value at Risk (95%)
        var_95 = self._calculate_var(returns_array, confidence=0.95)

        # Calculate Conditional VaR / Expected Shortfall
        cvar_95 = self._calculate_cvar(returns_array, confidence=0.95)

        # Calculate Omega ratio
        omega = self._calculate_omega_ratio(returns_array)

        # Calculate Sortino ratio (downside deviation)
        sortino = self._calculate_sortino_ratio(returns_array)

        # Calculate Information Ratio if benchmark provided
        info_ratio = None
        if benchmark_returns is not None:
            if isinstance(benchmark_returns[0], Decimal):
                benchmark_array = np.array([float(r) for r in benchmark_returns])
            else:
                benchmark_array = np.array(benchmark_returns)
            info_ratio = self._calculate_information_ratio(returns_array, benchmark_array)

        # Calculate kurtosis and skewness using scipy
        try:
            kurtosis_val = stats.kurtosis(returns_array)
            kurtosis = Decimal(str(kurtosis_val))
        except (ValueError, TypeError, KeyError, AttributeError):
            kurtosis = Decimal("0")

        try:
            skewness_val = stats.skew(returns_array)
            skewness = Decimal(str(skewness_val))
        except (ValueError, TypeError, KeyError, AttributeError):
            skewness = Decimal("0")

        metrics = AdvancedMetrics(
            calmar_ratio=calmar,
            stability_index=stability,
            tail_ratio=tail_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            omega_ratio=omega,
            sortino_ratio=sortino,
            information_ratio=info_ratio,
            kurtosis=kurtosis,
            skewness=skewness,
        )

        logger.info("✅ Calculated advanced metrics")
        return metrics

    def generate_statistics_report(
        self,
        returns: list[Decimal],
        annual_return_pct: Decimal,
        annual_volatility_pct: Decimal,
        sharpe_ratio: Decimal,
        max_drawdown_pct: Decimal,
        win_rate_pct: Decimal,
        num_trades: int,
        benchmark_returns: Optional[list[Decimal]] = None,
    ) -> StatisticsReport:
        """
        Generate comprehensive statistics report.

        Args:
            returns: Historical returns
            annual_return_pct: Annual return percentage
            annual_volatility_pct: Annual volatility
            sharpe_ratio: Sharpe ratio
            max_drawdown_pct: Maximum drawdown
            win_rate_pct: Win rate percentage
            num_trades: Number of trades
            benchmark_returns: Optional benchmark returns

        Returns:
            StatisticsReport with comprehensive metrics
        """
        # Convert to numpy for calculations
        returns_array = np.array([float(r) for r in returns])

        # Calculate advanced metrics
        advanced_metrics = self.calculate_advanced_metrics(
            returns, benchmark_returns, max_drawdown_pct
        )

        # Calculate cumulative return
        cumulative_return = Decimal(str(np.prod(1 + returns_array) - 1)) * Decimal("100")

        # Find best/worst days
        best_day = Decimal(str(np.max(returns_array) * 100))
        worst_day = Decimal(str(np.min(returns_array) * 100))

        # Calculate monthly returns distribution
        monthly_dist = self._calculate_monthly_distribution(returns_array)
        best_month = (
            Decimal(str(np.max(list(monthly_dist.values())) * 100))
            if monthly_dist
            else Decimal("0")
        )
        worst_month = (
            Decimal(str(np.min(list(monthly_dist.values())) * 100))
            if monthly_dist
            else Decimal("0")
        )

        report = StatisticsReport(
            report_date=datetime.utcnow(),
            total_return_pct=cumulative_return,
            annual_return_pct=annual_return_pct,
            annual_volatility_pct=annual_volatility_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_drawdown_pct,
            win_rate_pct=win_rate_pct,
            advanced_metrics=advanced_metrics,
            num_trades=num_trades,
            best_day_pct=best_day,
            worst_day_pct=worst_day,
            best_month_pct=best_month,
            worst_month_pct=worst_month,
            monthly_return_distribution=monthly_dist,
        )

        self.reports_generated += 1
        logger.info(f"✅ Generated statistics report #{self.reports_generated}")
        return report

    # ========================================================================
    # Individual Metric Calculations
    # ========================================================================

    def _calculate_calmar_ratio(
        self,
        returns: np.ndarray,
        max_drawdown_pct: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate Calmar ratio (annual return / max drawdown).

        Args:
            returns: Return series
            max_drawdown_pct: Maximum drawdown percentage

        Returns:
            Calmar ratio
        """
        if max_drawdown_pct is None or max_drawdown_pct <= 0:
            return Decimal("0")

        annual_return = np.mean(returns) * 252  # Annualized
        max_dd = float(max_drawdown_pct) / 100

        if max_dd == 0:
            return Decimal("0")

        calmar = annual_return / max_dd
        return Decimal(str(max(0, calmar)))  # Ensure non-negative

    def _calculate_stability_index(self, returns: np.ndarray) -> Decimal:
        """
        Calculate stability index (R² of linear regression of returns over time).

        Higher values indicate more stable/smooth returns.

        Args:
            returns: Return series

        Returns:
            Stability index (0-1)
        """
        n = len(returns)
        if n < 2:
            return Decimal("0")

        # Linear regression: y = mx + b
        x = np.arange(n)
        y = np.cumsum(returns)

        # Calculate R² (coefficient of determination)
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        y_pred = np.polyfit(x, y, 1)[0] * x + np.polyfit(x, y, 1)[1]
        ss_res = np.sum((y - y_pred) ** 2)

        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        return Decimal(str(max(0, min(1, r_squared))))

    def _calculate_tail_ratio(self, returns: np.ndarray) -> Decimal:
        """
        Calculate tail ratio (probability of extreme gains vs extreme losses).

        Ratio of positive returns exceeding 2 std devs vs negative returns.

        Args:
            returns: Return series

        Returns:
            Tail ratio
        """
        std_dev = np.std(returns)
        if std_dev == 0:
            return Decimal("1")

        threshold = 2 * std_dev
        positive_tails = np.sum(returns > threshold)
        negative_tails = np.sum(returns < -threshold)

        if negative_tails == 0:
            return Decimal("1")

        ratio = positive_tails / negative_tails
        return Decimal(str(ratio))

    def _calculate_var(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
    ) -> Decimal:
        """
        Calculate Value at Risk (VaR) at given confidence level.

        Args:
            returns: Return series
            confidence: Confidence level (default 95%)

        Returns:
            VaR as a percentage
        """
        var = np.percentile(returns, (1 - confidence) * 100)
        return Decimal(str(var * 100))  # Convert to percentage

    def _calculate_cvar(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
    ) -> Decimal:
        """
        Calculate Conditional VaR / Expected Shortfall.

        Average of returns worse than VaR.

        Args:
            returns: Return series
            confidence: Confidence level (default 95%)

        Returns:
            CVaR as a percentage
        """
        var_threshold = np.percentile(returns, (1 - confidence) * 100)
        cvar = np.mean(returns[returns <= var_threshold])
        return Decimal(str(cvar * 100))

    def _calculate_omega_ratio(self, returns: np.ndarray) -> Decimal:
        """
        Calculate Omega ratio.

        Probability-weighted ratio of gains to losses relative to threshold.

        Args:
            returns: Return series

        Returns:
            Omega ratio
        """
        threshold = 0  # Break-even point
        excess_positive = returns[returns > threshold] - threshold
        excess_negative = threshold - returns[returns < threshold]

        sum_positive = np.sum(excess_positive) if len(excess_positive) > 0 else 0
        sum_negative = np.sum(excess_negative) if len(excess_negative) > 0 else 0

        if sum_negative == 0:
            return Decimal("1")

        omega = sum_positive / sum_negative
        return Decimal(str(max(0, omega)))

    def _calculate_sortino_ratio(self, returns: np.ndarray) -> Decimal:
        """
        Calculate Sortino ratio (return / downside deviation).

        Only penalizes downside volatility.

        Args:
            returns: Return series

        Returns:
            Sortino ratio
        """
        annual_return = np.mean(returns) * 252

        # Downside deviation (only negative returns)
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            # No downside returns, Sortino is infinite (use 0 as fallback)
            return Decimal("0")

        downside_variance = np.mean(downside_returns**2)
        downside_deviation = np.sqrt(downside_variance)

        if downside_deviation == 0 or np.isnan(downside_deviation):
            return Decimal("0")

        sortino = annual_return / downside_deviation
        if np.isnan(sortino):
            return Decimal("0")
        return Decimal(str(max(0, sortino)))

    def _calculate_information_ratio(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray,
    ) -> Decimal:
        """
        Calculate Information ratio (excess return / tracking error).

        Args:
            returns: Strategy returns
            benchmark_returns: Benchmark returns

        Returns:
            Information ratio
        """
        excess_returns = returns - benchmark_returns
        tracking_error = np.std(excess_returns)

        if tracking_error == 0:
            return Decimal("0")

        annual_excess = np.mean(excess_returns) * 252
        info_ratio = annual_excess / tracking_error
        return Decimal(str(info_ratio))

    def _calculate_monthly_distribution(
        self,
        returns: np.ndarray,
    ) -> dict[str, float]:
        """
        Calculate monthly return distribution.

        Args:
            returns: Daily return series

        Returns:
            Dictionary of monthly returns
        """
        if len(returns) < 21:  # Minimum ~1 month of daily data
            return {}

        # Assume 252 trading days per year, 21 per month
        monthly_returns = {}
        months_count = len(returns) // 21

        for month_idx in range(months_count):
            start_idx = month_idx * 21
            end_idx = min((month_idx + 1) * 21, len(returns))

            monthly_return = np.prod(1 + returns[start_idx:end_idx]) - 1
            monthly_returns[f"month_{month_idx + 1}"] = float(monthly_return)

        return monthly_returns

    # ========================================================================
    # Status & Configuration
    # ========================================================================

    def get_integrator_status(self) -> dict:
        """Get integrator operational status."""
        return {
            "reports_generated": self.reports_generated,
            "status": "operational",
            "last_update": datetime.utcnow().isoformat(),
        }


# Singleton instance
_integrator: Optional[QuantStatsIntegrator] = None


def get_quantstats_integrator() -> QuantStatsIntegrator:
    """Get or create singleton QuantStatsIntegrator."""
    global _integrator
    if _integrator is None:
        _integrator = QuantStatsIntegrator()

    return _integrator
