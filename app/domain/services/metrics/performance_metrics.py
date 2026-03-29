"""
Performance Metrics Calculator

Centralized implementation of performance metrics, consolidating:
- Sharpe ratio (from metrics.py, chan_metrics.py, bias_correctors.py, risk_calculator.py)
- Sortino ratio (from metrics.py, chan_metrics.py, risk_calculator.py, advanced_metrics.py)
- Calmar ratio (from chan_metrics.py, advanced_metrics.py)
- Omega ratio (from advanced_metrics.py)
- Max drawdown (from metrics.py, chan_metrics.py, risk_calculator.py)
- Ulcer index (from advanced_metrics.py)

Uses quantstats/empyrical as backend when available for industry-standard calculations.

Reference:
    - Lopez de Prado, M. (2020). Machine Learning for Asset Managers.
    - Chan, E.P. (2013). Algorithmic Trading.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import pandas as pd

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)

# Constants - get default from CentralizedConfig
DEFAULT_RISK_FREE_RATE = float(get_config().backtesting.default_risk_free_rate)

# Try to import empyrical for industry-standard calculations
try:
    import empyrical as ep

    EMPYRICAL_AVAILABLE = True
except ImportError:
    EMPYRICAL_AVAILABLE = False
    ep = None
    logger.debug(
        "empyrical not available - using native implementations. "
        "Install with: pip install empyrical-reloaded"
    )

# Try to import quantstats as alternative
try:
    import quantstats as qs

    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False
    qs = None


def _to_array(returns: pd.Series | np.ndarray | list[Decimal] | list[float]) -> np.ndarray:
    """Convert returns to numpy array, handling various input types."""
    if isinstance(returns, pd.Series):
        arr = returns.values.astype(np.float64)
    elif isinstance(returns, list):
        if len(returns) > 0 and isinstance(returns[0], Decimal):
            arr = np.array([float(r) for r in returns], dtype=np.float64)
        else:
            arr = np.array(returns, dtype=np.float64)
    else:
        arr = np.asarray(returns, dtype=np.float64)

    # Remove NaN values
    return arr[~np.isnan(arr)]


def _to_decimal(value: float | np.floating | Decimal) -> Decimal:
    """Convert value to Decimal for precision."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(float(value)))


@dataclass
class SharpeRatioResult:
    """Comprehensive Sharpe ratio result with confidence intervals."""

    sharpe_ratio: float
    annualized_sharpe: float
    daily_mean_return: float
    daily_std_return: float
    skewness: float | None = None
    excess_kurtosis: float | None = None
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    is_statistically_significant: bool | None = None


@dataclass
class DrawdownResult:
    """Comprehensive drawdown analysis result."""

    max_drawdown: float  # As decimal (e.g., -0.20 for -20%)
    max_drawdown_pct: float  # As percentage (e.g., -20.0)
    max_drawdown_duration: int  # In periods
    average_drawdown: float
    recovery_factor: float
    drawdown_distribution: dict | None = None


@dataclass
class PerformanceResult:
    """Complete performance metrics result."""

    # Return metrics
    total_return: float
    cagr: float
    annual_return: float

    # Risk-adjusted metrics
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float | None
    omega_ratio: float | None

    # Risk metrics
    max_drawdown: float
    volatility: float

    # Distribution metrics
    skewness: float | None
    kurtosis: float | None

    # Additional metrics
    var_95: float | None
    cvar_95: float | None


class PerformanceMetricsCalculator:
    """
    Unified performance metrics calculator.

    This class consolidates all performance metric calculations from:
    - app/backtesting/metrics.py (MetricsCalculator)
    - app/backtesting/chan_metrics.py (ChanSharpeRatioCalculator)
    - app/backtesting/advanced_metrics.py (AdvancedMetricsCalculator)
    - app/domain/services/risk_calculator.py (RiskCalculator)

    Uses empyrical/quantstats as backend when available for industry-standard
    calculations, with fallback to native implementations.
    """

    def __init__(
        self,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        trading_days: int | None = None,
        use_empyrical: bool = True,
    ):
        """
        Initialize performance metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
            trading_days: Number of trading days per year (default: from CentralizedConfig)
            use_empyrical: Whether to use empyrical library when available
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = (
            trading_days
            if trading_days is not None
            else get_config().backtesting.annual_trading_days
        )
        self.use_empyrical = use_empyrical and EMPYRICAL_AVAILABLE

    # =========================================================================
    # SHARPE RATIO
    # =========================================================================

    def sharpe_ratio(
        self,
        returns: pd.Series | np.ndarray | list[Decimal] | list[float],
        risk_free_rate: float | None = None,
        annualize: bool = True,
        periods: int | None = None,
    ) -> float:
        """
        Calculate Sharpe ratio.

        Consolidated from:
        - metrics.py:_calculate_sharpe_ratio
        - chan_metrics.py:ChanSharpeRatioCalculator.calculate_sharpe_ratio
        - bias_correctors.py:BacktestValidator._calculate_sharpe_ratio
        - risk_calculator.py:RiskCalculator.calculate_sharpe_ratio

        Args:
            returns: Return series (daily returns by default)
            risk_free_rate: Annual risk-free rate (default: self.risk_free_rate)
            annualize: Whether to annualize the ratio
            periods: Periods per year (default: self.trading_days)

        Returns:
            Sharpe ratio (annualized if annualize=True)

        Example:
            >>> calc = PerformanceMetricsCalculator()
            >>> returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015])
            >>> sharpe = calc.sharpe_ratio(returns)
            >>> print(f"Sharpe: {sharpe:.2f}")
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return 0.0

        rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate
        periods_per_year = periods if periods is not None else self.trading_days

        # Try empyrical first
        if self.use_empyrical and ep is not None:
            try:
                daily_rf = rf / periods_per_year
                result = ep.sharpe_ratio(
                    returns_array,
                    risk_free=daily_rf,
                    period="daily",
                    annualization=periods_per_year,
                )
                if np.isfinite(result):
                    return float(result)
            except Exception as e:
                logger.debug(f"empyrical sharpe_ratio failed: {e}")

        # Native implementation
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array, ddof=1)

        if std_return < 1e-10:  # Near-zero volatility
            return 0.0

        # Daily Sharpe
        daily_rf = rf / periods_per_year
        daily_sharpe = (mean_return - daily_rf) / std_return

        if annualize:
            return float(daily_sharpe * np.sqrt(periods_per_year))

        return float(daily_sharpe)

    def sharpe_ratio_with_confidence(
        self,
        returns: pd.Series | np.ndarray | list[float],
        confidence_level: float = 0.95,
    ) -> SharpeRatioResult:
        """
        Calculate Sharpe ratio with confidence intervals.

        From Ernest Chan: Uses the standard error approach.
        SE = sqrt((1 + 0.5 * Sharpe^2) / n)

        Args:
            returns: Return series
            confidence_level: Confidence level for CI calculation

        Returns:
            SharpeRatioResult with comprehensive statistics
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return SharpeRatioResult(
                sharpe_ratio=0.0,
                annualized_sharpe=0.0,
                daily_mean_return=0.0,
                daily_std_return=0.0,
            )

        daily_mean = float(np.mean(returns_array))
        daily_std = float(np.std(returns_array, ddof=1))

        if daily_std < 1e-10:
            return SharpeRatioResult(
                sharpe_ratio=0.0,
                annualized_sharpe=0.0,
                daily_mean_return=daily_mean,
                daily_std_return=daily_std,
            )

        # Daily Sharpe
        daily_rf = self.risk_free_rate / self.trading_days
        daily_sharpe = (daily_mean - daily_rf) / daily_std
        annualized_sharpe = daily_sharpe * np.sqrt(self.trading_days)

        # Calculate higher moments
        skewness = self._calculate_skewness(returns_array)
        kurtosis = self._calculate_kurtosis(returns_array)

        # Confidence interval using Chan's formula
        n = len(returns_array)
        se = np.sqrt((1 + 0.5 * daily_sharpe**2) / n)

        # Z-score for confidence level
        try:
            from scipy import stats

            z = stats.norm.ppf((1 + confidence_level) / 2)
            ci_low = daily_sharpe - z * se
            ci_high = daily_sharpe + z * se
            is_significant = abs(daily_sharpe) > 2 * se
        except ImportError:
            ci_low = daily_sharpe * 0.8
            ci_high = daily_sharpe * 1.2
            is_significant = False

        return SharpeRatioResult(
            sharpe_ratio=daily_sharpe,
            annualized_sharpe=annualized_sharpe,
            daily_mean_return=daily_mean,
            daily_std_return=daily_std,
            skewness=skewness,
            excess_kurtosis=kurtosis,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            is_statistically_significant=is_significant,
        )

    # =========================================================================
    # SORTINO RATIO
    # =========================================================================

    def sortino_ratio(
        self,
        returns: pd.Series | np.ndarray | list[Decimal] | list[float],
        risk_free_rate: float | None = None,
        target_return: float = 0.0,
        annualize: bool = True,
    ) -> float:
        """
        Calculate Sortino ratio (downside deviation-based).

        Consolidated from:
        - metrics.py:_calculate_sortino_ratio
        - advanced_metrics.py:calculate_sortino_modified
        - risk_calculator.py:RiskCalculator.calculate_sortino_ratio

        Args:
            returns: Return series
            risk_free_rate: Annual risk-free rate
            target_return: Target/minimum acceptable return (MAR)
            annualize: Whether to annualize the ratio

        Returns:
            Sortino ratio (annualized if annualize=True)
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return 0.0

        rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate

        # Try empyrical first
        if self.use_empyrical and ep is not None:
            try:
                daily_rf = rf / self.trading_days
                result = ep.sortino_ratio(
                    returns_array,
                    risk_free=daily_rf,
                    period="daily",
                    annualization=self.trading_days,
                )
                if np.isfinite(result):
                    return float(result)
            except Exception as e:
                logger.debug(f"empyrical sortino_ratio failed: {e}")

        # Native implementation
        mean_return = np.mean(returns_array)
        daily_rf = rf / self.trading_days

        # Calculate downside deviation
        # Use target_return if specified, otherwise use daily risk-free rate
        threshold = target_return if target_return != 0.0 else daily_rf
        downside_diff = np.minimum(returns_array - threshold, 0)
        downside_squared = downside_diff**2

        if np.sum(downside_squared) == 0:
            return 999.0 if mean_return > threshold else 0.0

        downside_std = np.sqrt(np.mean(downside_squared))

        if downside_std < 1e-10:
            return 0.0

        # Sortino ratio
        sortino = (mean_return - daily_rf) / downside_std

        if annualize:
            # Annualize: multiply by sqrt(252) for daily returns
            sortino *= np.sqrt(self.trading_days)

        return float(sortino)

    # =========================================================================
    # CALMAR RATIO
    # =========================================================================

    def calmar_ratio(
        self,
        returns: pd.Series | np.ndarray | list[float],
        equity_curve: pd.Series | np.ndarray | list[float] | None = None,
        cagr: float | None = None,
        max_drawdown: float | None = None,
    ) -> float | None:
        """
        Calculate Calmar ratio (CAGR / |Max Drawdown|).

        Consolidated from:
        - chan_metrics.py:ChanCalmarRatioCalculator.calculate_calmar_ratio
        - advanced_metrics.py:calculate_calmar_ratio
        - numba_metrics.py:calculate_calmar_ratio_numba

        Args:
            returns: Return series
            equity_curve: Optional equity curve for drawdown calculation
            cagr: Pre-calculated CAGR (optional)
            max_drawdown: Pre-calculated max drawdown as negative decimal (optional)

        Returns:
            Calmar ratio or None if calculation not possible
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return None

        # Calculate CAGR if not provided
        if cagr is None:
            cumulative_return = (1 + returns_array).prod() - 1
            years = len(returns_array) / self.trading_days
            if years > 0 and cumulative_return > -1:
                cagr = float((1 + cumulative_return) ** (1 / years) - 1)
            else:
                cagr = float(np.mean(returns_array) * self.trading_days)

        # Calculate max drawdown if not provided
        if max_drawdown is None:
            if equity_curve is not None:
                dd_result = self.max_drawdown_analysis(equity_curve)
                max_dd = abs(dd_result.max_drawdown)
            else:
                dd_result = self.max_drawdown_analysis(returns_array, from_returns=True)
                max_dd = abs(dd_result.max_drawdown)
        else:
            max_dd = abs(max_drawdown)

        if max_dd < 1e-10:
            return None

        return float(cagr / max_dd)

    # =========================================================================
    # OMEGA RATIO
    # =========================================================================

    def omega_ratio(
        self,
        returns: pd.Series | np.ndarray | list[Decimal] | list[float],
        threshold: float = 0.0,
    ) -> float:
        """
        Calculate Omega ratio.

        From advanced_metrics.py:calculate_omega_ratio
        Formula: E[max(R - threshold, 0)] / E[max(threshold - R, 0)]

        Args:
            returns: Return series
            threshold: Target return threshold (default: 0%)

        Returns:
            Omega ratio (>1.0 indicates more upside than downside)
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return 1.0

        # Try empyrical first
        if self.use_empyrical and ep is not None:
            try:
                result = ep.omega_ratio(returns_array, risk_free=threshold, required_return=0.0)
                if np.isfinite(result):
                    return float(result)
            except Exception as e:
                logger.debug(f"empyrical omega_ratio failed: {e}")

        # Native implementation
        excess_above = np.maximum(returns_array - threshold, 0)
        excess_below = np.maximum(threshold - returns_array, 0)

        avg_gain = np.mean(excess_above)
        avg_loss = np.mean(excess_below)

        if avg_loss < 1e-10:
            return 999999.0 if avg_gain > 0 else 1.0

        return float(avg_gain / avg_loss)

    # =========================================================================
    # MAX DRAWDOWN
    # =========================================================================

    def max_drawdown(
        self,
        equity_curve: pd.Series | np.ndarray | list[Decimal] | list[float],
        as_percentage: bool = False,
    ) -> float:
        """
        Calculate maximum drawdown.

        Consolidated from:
        - metrics.py:_calculate_max_drawdown
        - chan_metrics.py:ChanDrawdownAnalyzer
        - risk_calculator.py

        Args:
            equity_curve: Equity or portfolio value series
            as_percentage: If True, return as percentage (e.g., -20.0)

        Returns:
            Maximum drawdown (negative value, e.g., -0.20 or -20.0)
        """
        result = self.max_drawdown_analysis(equity_curve)
        return result.max_drawdown_pct if as_percentage else result.max_drawdown

    def max_drawdown_analysis(
        self,
        equity_curve: pd.Series | np.ndarray | list[float],
        from_returns: bool = False,
    ) -> DrawdownResult:
        """
        Comprehensive drawdown analysis.

        Args:
            equity_curve: Equity curve or returns (if from_returns=True)
            from_returns: If True, treat input as returns and compute cumulative

        Returns:
            DrawdownResult with comprehensive analysis
        """
        equity_array = _to_array(equity_curve)

        if len(equity_array) < 2:
            return DrawdownResult(
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                max_drawdown_duration=0,
                average_drawdown=0.0,
                recovery_factor=0.0,
            )

        # Convert returns to equity curve if needed
        if from_returns:
            equity_array = (1 + equity_array).cumprod()

        # Calculate running peak
        running_peak = np.maximum.accumulate(equity_array)

        # Calculate drawdown
        drawdowns = (equity_array - running_peak) / running_peak

        # Max drawdown
        max_dd = float(drawdowns.min())
        max_dd_pct = max_dd * 100

        # Find max drawdown duration
        max_dd_idx = int(np.argmin(drawdowns))
        peak_idx = int(np.argmax(equity_array[: max_dd_idx + 1]))
        max_duration = max_dd_idx - peak_idx

        # Average drawdown (only negative values)
        negative_drawdowns = drawdowns[drawdowns < 0]
        avg_drawdown = float(negative_drawdowns.mean()) if len(negative_drawdowns) > 0 else 0.0

        # Recovery factor
        final_value = equity_array[-1]
        peak_value = running_peak.max()
        recovery = (final_value - peak_value) / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

        # Drawdown distribution
        if len(negative_drawdowns) > 0:
            dd_dist = {
                "p5": float(np.percentile(negative_drawdowns, 5)),
                "p25": float(np.percentile(negative_drawdowns, 25)),
                "p50": float(np.percentile(negative_drawdowns, 50)),
                "p75": float(np.percentile(negative_drawdowns, 75)),
                "p95": float(np.percentile(negative_drawdowns, 95)),
            }
        else:
            dd_dist = {}

        return DrawdownResult(
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_duration=max_duration,
            average_drawdown=avg_drawdown,
            recovery_factor=float(recovery),
            drawdown_distribution=dd_dist,
        )

    # =========================================================================
    # ULCER INDEX
    # =========================================================================

    def ulcer_index(
        self,
        equity_curve: pd.Series | np.ndarray | list[Decimal] | list[float],
    ) -> float:
        """
        Calculate Ulcer Index.

        From advanced_metrics.py:calculate_ulcer_index
        Penalizes the duration and magnitude of underwater periods.

        Formula: sqrt(mean(max(0, (Peak - Price) / Peak)^2))

        Args:
            equity_curve: Portfolio equity values over time

        Returns:
            Ulcer Index (lower is better)
        """
        equity_array = _to_array(equity_curve)

        if len(equity_array) < 2:
            return 0.0

        # Calculate rolling maximum (peak)
        rolling_max = np.maximum.accumulate(equity_array)

        # Calculate drawdown percentage from peak
        drawdowns = (rolling_max - equity_array) / rolling_max

        # Ulcer = sqrt(mean(drawdown^2))
        ulcer = np.sqrt(np.mean(np.square(drawdowns)))

        return float(ulcer)

    # =========================================================================
    # CAGR
    # =========================================================================

    def cagr(
        self,
        returns: pd.Series | np.ndarray | list[float],
        periods_per_year: int | None = None,
    ) -> float:
        """
        Calculate Compound Annual Growth Rate.

        Args:
            returns: Return series
            periods_per_year: Periods per year (default: self.trading_days)

        Returns:
            CAGR as decimal (e.g., 0.10 for 10%)
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 1:
            return 0.0

        ppy = periods_per_year or self.trading_days

        # Try empyrical first
        if self.use_empyrical and ep is not None:
            try:
                result = ep.cagr(returns_array, period="daily", annualization=ppy)
                if np.isfinite(result):
                    return float(result)
            except Exception:
                pass

        # Native implementation
        cumulative_return = (1 + returns_array).prod() - 1
        years = len(returns_array) / ppy

        if years <= 0 or cumulative_return <= -1:
            return 0.0

        return float((1 + cumulative_return) ** (1 / years) - 1)

    # =========================================================================
    # VOLATILITY
    # =========================================================================

    def volatility(
        self,
        returns: pd.Series | np.ndarray | list[float],
        annualize: bool = True,
    ) -> float:
        """
        Calculate volatility.

        Args:
            returns: Return series
            annualize: Whether to annualize

        Returns:
            Volatility (annualized if annualize=True)
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return 0.0

        daily_vol = np.std(returns_array, ddof=1)

        if annualize:
            return float(daily_vol * np.sqrt(self.trading_days))

        return float(daily_vol)

    # =========================================================================
    # COMPREHENSIVE CALCULATION
    # =========================================================================

    def calculate_all(
        self,
        returns: pd.Series | np.ndarray | list[float],
        equity_curve: pd.Series | np.ndarray | list[float] | None = None,
    ) -> PerformanceResult:
        """
        Calculate all performance metrics at once.

        Args:
            returns: Return series
            equity_curve: Optional equity curve (computed from returns if not provided)

        Returns:
            PerformanceResult with all metrics
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return PerformanceResult(
                total_return=0.0,
                cagr=0.0,
                annual_return=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=None,
                omega_ratio=None,
                max_drawdown=0.0,
                volatility=0.0,
                skewness=None,
                kurtosis=None,
                var_95=None,
                cvar_95=None,
            )

        # Compute equity curve if not provided
        if equity_curve is None:
            equity_array = (1 + returns_array).cumprod()
        else:
            equity_array = _to_array(equity_curve)

        # Calculate all metrics
        total_return = float((1 + returns_array).prod() - 1)
        cagr_val = self.cagr(returns_array)
        annual_return = float(np.mean(returns_array) * self.trading_days)

        sharpe = self.sharpe_ratio(returns_array)
        sortino = self.sortino_ratio(returns_array)

        dd_result = self.max_drawdown_analysis(equity_array)
        calmar = self.calmar_ratio(
            returns_array, equity_array, cagr=cagr_val, max_drawdown=dd_result.max_drawdown
        )
        omega = self.omega_ratio(returns_array)

        vol = self.volatility(returns_array)

        # Distribution metrics
        skewness = self._calculate_skewness(returns_array)
        kurtosis = self._calculate_kurtosis(returns_array)

        # VaR/CVaR
        var_95 = self._calculate_var(returns_array, 0.95)
        cvar_95 = self._calculate_cvar(returns_array, 0.95)

        return PerformanceResult(
            total_return=total_return,
            cagr=cagr_val,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            omega_ratio=omega,
            max_drawdown=dd_result.max_drawdown,
            volatility=vol,
            skewness=skewness,
            kurtosis=kurtosis,
            var_95=var_95,
            cvar_95=cvar_95,
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _calculate_skewness(self, returns: np.ndarray) -> float | None:
        """Calculate skewness of returns."""
        if len(returns) < 3:
            return None

        try:
            from scipy import stats

            return float(stats.skew(returns))
        except ImportError:
            # Manual calculation
            mean = np.mean(returns)
            std = np.std(returns, ddof=1)
            if std < 1e-10:
                return 0.0
            return float(np.mean(((returns - mean) / std) ** 3))

    def _calculate_kurtosis(self, returns: np.ndarray) -> float | None:
        """Calculate excess kurtosis of returns."""
        if len(returns) < 4:
            return None

        try:
            from scipy import stats

            return float(stats.kurtosis(returns))  # Returns excess kurtosis
        except ImportError:
            # Manual calculation
            mean = np.mean(returns)
            std = np.std(returns, ddof=1)
            if std < 1e-10:
                return 0.0
            return float(np.mean(((returns - mean) / std) ** 4) - 3)

    def _calculate_var(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """Calculate Value at Risk using historical method."""
        return float(np.percentile(returns, (1 - confidence) * 100))

    def _calculate_cvar(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """Calculate Conditional VaR (Expected Shortfall)."""
        var = self._calculate_var(returns, confidence)
        tail_returns = returns[returns <= var]
        if len(tail_returns) == 0:
            return var
        return float(np.mean(tail_returns))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_sharpe_ratio(
    returns: pd.Series | np.ndarray | list[float],
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    annualize: bool = True,
) -> float:
    """
    Convenience function to calculate Sharpe ratio.

    Args:
        returns: Return series
        risk_free_rate: Annual risk-free rate
        annualize: Whether to annualize

    Returns:
        Sharpe ratio
    """
    calc = PerformanceMetricsCalculator(risk_free_rate=risk_free_rate)
    return calc.sharpe_ratio(returns, annualize=annualize)


def get_sortino_ratio(
    returns: pd.Series | np.ndarray | list[float],
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    annualize: bool = True,
) -> float:
    """
    Convenience function to calculate Sortino ratio.

    Args:
        returns: Return series
        risk_free_rate: Annual risk-free rate
        annualize: Whether to annualize

    Returns:
        Sortino ratio
    """
    calc = PerformanceMetricsCalculator(risk_free_rate=risk_free_rate)
    return calc.sortino_ratio(returns, annualize=annualize)


def get_calmar_ratio(
    returns: pd.Series | np.ndarray | list[float],
    equity_curve: pd.Series | np.ndarray | list[float] | None = None,
) -> float | None:
    """
    Convenience function to calculate Calmar ratio.

    Args:
        returns: Return series
        equity_curve: Optional equity curve

    Returns:
        Calmar ratio
    """
    calc = PerformanceMetricsCalculator()
    return calc.calmar_ratio(returns, equity_curve)


def get_omega_ratio(
    returns: pd.Series | np.ndarray | list[float],
    threshold: float = 0.0,
) -> float:
    """
    Convenience function to calculate Omega ratio.

    Args:
        returns: Return series
        threshold: Target return threshold

    Returns:
        Omega ratio
    """
    calc = PerformanceMetricsCalculator()
    return calc.omega_ratio(returns, threshold)


def get_max_drawdown(
    equity_curve: pd.Series | np.ndarray | list[float],
    as_percentage: bool = False,
) -> float:
    """
    Convenience function to calculate maximum drawdown.

    Args:
        equity_curve: Equity curve
        as_percentage: If True, return as percentage

    Returns:
        Maximum drawdown
    """
    calc = PerformanceMetricsCalculator()
    return calc.max_drawdown(equity_curve, as_percentage)


def get_ulcer_index(
    equity_curve: pd.Series | np.ndarray | list[float],
) -> float:
    """
    Convenience function to calculate Ulcer Index.

    Args:
        equity_curve: Equity curve

    Returns:
        Ulcer Index
    """
    calc = PerformanceMetricsCalculator()
    return calc.ulcer_index(equity_curve)
