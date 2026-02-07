"""
Performance Metrics - Ernest Chan Methodologies

This module implements Ernest Chan's performance metrics from
"Algorithmic Trading: A Practitioner's Guide".

Key Concepts:
1. Sharpe ratio optimization
2. Maximum drawdown analysis
3. Calmar ratio calculation
4. Return distribution analysis
5. Strategy comparison metrics

Reference:
    "Algorithmic Trading" by Ernest P. Chan (2013)
    Chapter 3: Backtesting
    Chapter 8: Risk and Performance Metrics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SharpeRatioResult:
    """Results from Sharpe ratio calculation."""

    sharpe_ratio: float
    annualized_sharpe: float
    daily_mean_return: float
    daily_std_return: float
    skewness: float
    excess_kurtosis: float
    confidence_interval_low: float
    confidence_interval_high: float
    is_statistically_significant: bool


@dataclass
class DrawdownResult:
    """Results from drawdown analysis."""

    max_drawdown: float
    max_drawdown_percentage: float
    max_drawdown_duration_days: int
    average_drawdown: float
    recovery_factor: float
    drawdown_distribution: Dict[str, float]
    drawdown_periods: List[Dict[str, Any]]


@dataclass
class CalmarRatioResult:
    """Results from Calmar ratio calculation."""

    calmar_ratio: float
    annual_return: float
    max_drawdown: float
    interpretation: str


@dataclass
class ReturnDistributionMetrics:
    """Metrics for return distribution analysis."""

    mean_return: float
    median_return: float
    std_return: float
    positive_return_pct: float
    negative_return_pct: float
    best_day_return: float
    worst_day_return: float
    up_capture_ratio: float
    down_capture_ratio: float
    tail_ratio: float


@dataclass
class StrategyComparisonResult:
    """Results from strategy comparison."""

    strategy1_sharpe: float
    strategy2_sharpe: float
    sharpe_difference: float
    is_significant: bool
    tracking_error: float
    information_ratio: float
    recommended_strategy: str


class ChanSharpeRatioCalculator:
    """
    Sharpe ratio calculator per Ernest Chan.

    Chan's approach:
    1. Use daily returns for calculation
    2. Annualize by multiplying by sqrt(252)
    3. Subtract risk-free rate
    4. Calculate confidence intervals
    5. Test for statistical significance
    """

    # Default risk-free rate (Ernest Chan uses Treasury yield)
    DEFAULT_RISK_FREE_RATE = 0.02  # 2%

    # Trading days per year (Chan uses 252)
    TRADING_DAYS_PER_YEAR = 252

    def __init__(
        self,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        trading_days: int = TRADING_DAYS_PER_YEAR,
    ):
        """
        Initialize Sharpe ratio calculator.

        Args:
            risk_free_rate: Annual risk-free rate
            trading_days: Number of trading days per year
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days

    def calculate_sharpe_ratio(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        confidence_level: float = 0.95,
    ) -> SharpeRatioResult:
        """
        Calculate Sharpe ratio with confidence intervals.

        Ernest Chan's formula:
        Sharpe = (mean_return - risk_free) / std_return
        Annualized Sharpe = daily_sharpe * sqrt(252)

        Args:
            returns: Return series (daily returns)
            confidence_level: Confidence level for CI calculation

        Returns:
            SharpeRatioResult with comprehensive statistics

        Examples:
            >>> calc = ChanSharpeRatioCalculator()
            >>> returns = pd.Series([0.01, -0.005, 0.02, ...])
            >>> result = calc.calculate_sharpe_ratio(returns)
            >>> print(f"Annualized Sharpe: {result.annualized_sharpe:.2f}")
        """
        try:
            returns_array = self._convert_and_clean_returns(returns)
            if len(returns_array) < 2:
                logger.warning("Insufficient data for Sharpe ratio calculation")
                return self._empty_sharpe_result()

            daily_mean, daily_std = self._calculate_daily_statistics(returns_array)
            daily_sharpe, annualized_sharpe = self._calculate_sharpe_values(daily_mean, daily_std)

            skewness = float(self._calculate_skewness(returns_array))
            excess_kurtosis = float(self._calculate_excess_kurtosis(returns_array))

            ci_low, ci_high = self._calculate_sharpe_confidence_interval(
                daily_sharpe,
                len(returns_array),
                confidence_level,
            )

            is_significant = self._test_sharpe_significance(
                daily_sharpe,
                len(returns_array),
                confidence_level,
            )

            return SharpeRatioResult(
                sharpe_ratio=float(daily_sharpe),
                annualized_sharpe=float(annualized_sharpe),
                daily_mean_return=daily_mean,
                daily_std_return=daily_std,
                skewness=skewness,
                excess_kurtosis=excess_kurtosis,
                confidence_interval_low=float(ci_low),
                confidence_interval_high=float(ci_high),
                is_statistically_significant=is_significant,
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return self._empty_sharpe_result()

    def _convert_and_clean_returns(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
    ) -> np.ndarray:
        """Convert returns to numpy array and remove NaN values."""
        if isinstance(returns, (list, pd.Series)):
            returns_array = np.array(returns, dtype=np.float64)
        else:
            returns_array = returns.astype(np.float64)
        return returns_array[~np.isnan(returns_array)]

    def _calculate_daily_statistics(self, returns_array: np.ndarray) -> Tuple[float, float]:
        """Calculate daily mean and standard deviation."""
        daily_mean = float(np.mean(returns_array))
        daily_std = float(np.std(returns_array, ddof=1))
        return daily_mean, daily_std

    def _calculate_sharpe_values(
        self,
        daily_mean: float,
        daily_std: float,
    ) -> Tuple[float, float]:
        """Calculate daily and annualized Sharpe ratios."""
        daily_rf = self.risk_free_rate / self.trading_days

        if daily_std == 0:
            daily_sharpe = 0.0
        else:
            daily_sharpe = (daily_mean - daily_rf) / daily_std

        annualized_sharpe = daily_sharpe * np.sqrt(self.trading_days)
        return daily_sharpe, annualized_sharpe

    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns."""
        try:
            if len(returns) < 3:
                return 0.0

            mean = np.mean(returns)
            std = np.std(returns, ddof=1)

            if std == 0:
                return 0.0

            # Third moment
            skew = np.mean(((returns - mean) / std) ** 3)
            return float(skew)

        except (ValueError, ZeroDivisionError):
            return 0.0

    def _calculate_excess_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate excess kurtosis of returns."""
        try:
            if len(returns) < 4:
                return 0.0

            mean = np.mean(returns)
            std = np.std(returns, ddof=1)

            if std == 0:
                return 0.0

            # Fourth moment minus 3 (excess kurtosis)
            kurt = np.mean(((returns - mean) / std) ** 4) - 3
            return float(kurt)

        except (ValueError, ZeroDivisionError):
            return 0.0

    def _calculate_sharpe_confidence_interval(
        self,
        sharpe: float,
        n_obs: int,
        confidence_level: float,
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for Sharpe ratio.

        Ernest Chan uses the standard error approach:
        SE = sqrt((1 + 0.5 * Sharpe^2) / n)

        CI = Sharpe +/- z * SE
        """
        try:
            # Standard error
            se = np.sqrt((1 + 0.5 * sharpe**2) / n_obs)

            # Z-score for confidence level
            from scipy import stats

            z = stats.norm.ppf((1 + confidence_level) / 2)

            # Confidence interval
            ci_low = sharpe - z * se
            ci_high = sharpe + z * se

            return float(ci_low), float(ci_high)

        except (ValueError, ImportError):
            # Fallback without scipy
            return sharpe * 0.8, sharpe * 1.2

    def _test_sharpe_significance(
        self,
        sharpe: float,
        n_obs: int,
        confidence_level: float,
    ) -> bool:
        """
        Test if Sharpe ratio is statistically significant.

        Ernest Chan: Sharpe should be > 2 * SE for significance
        """
        try:
            se = np.sqrt((1 + 0.5 * sharpe**2) / n_obs)

            # Sharpe is significant if it's more than 2 SEs from zero
            return abs(sharpe) > 2 * se

        except (ValueError, ZeroDivisionError):
            return False

    def _empty_sharpe_result(self) -> SharpeRatioResult:
        """Return empty Sharpe ratio result."""
        return SharpeRatioResult(
            sharpe_ratio=0.0,
            annualized_sharpe=0.0,
            daily_mean_return=0.0,
            daily_std_return=0.0,
            skewness=0.0,
            excess_kurtosis=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            is_statistically_significant=False,
        )


class ChanDrawdownAnalyzer:
    """
    Drawdown analyzer per Ernest Chan.

    Chan's metrics:
    1. Maximum drawdown
    2. Average drawdown
    3. Drawdown duration
    4. Recovery factor
    5. Drawdown distribution
    """

    def __init__(self):
        """Initialize drawdown analyzer."""

    def analyze_drawdown(
        self,
        equity_curve: Union[pd.Series, np.ndarray, List[float]],
        dates: Optional[Union[pd.DatetimeIndex, List[datetime]]] = None,
    ) -> DrawdownResult:
        """
        Analyze drawdown characteristics.

        Ernest Chan's approach:
        1. Calculate rolling peak
        2. Calculate drawdown from peak
        3. Analyze drawdown periods
        4. Calculate recovery metrics

        Args:
            equity_curve: Equity or portfolio value series
            dates: Optional date series for duration calculation

        Returns:
            DrawdownResult with comprehensive analysis

        Examples:
            >>> analyzer = ChanDrawdownAnalyzer()
            >>> equity = pd.Series([100000, 102000, 98000, 105000, ...])
            >>> result = analyzer.analyze_drawdown(equity)
            >>> print(f"Max DD: {result.max_drawdown_percentage:.2f}%")
        """
        try:
            equity_array = self._convert_and_clean_equity(equity_curve)
            if len(equity_array) < 2:
                logger.warning("Insufficient data for drawdown analysis")
                return self._empty_drawdown_result()

            drawdown, running_peak = self._calculate_drawdown_from_peak(equity_array)
            max_dd, max_dd_pct, max_dd_idx, peak_idx = self._find_max_drawdown(
                drawdown, equity_array
            )
            duration_days = self._calculate_drawdown_duration(dates, max_dd_idx, peak_idx)
            avg_drawdown = self._calculate_average_drawdown(drawdown)
            recovery_factor = self._calculate_recovery_factor(equity_array, running_peak, max_dd)

            dd_distribution = self._calculate_drawdown_distribution(drawdown)
            drawdown_periods = self._identify_drawdown_periods(drawdown, dates)

            return DrawdownResult(
                max_drawdown=max_dd,
                max_drawdown_percentage=max_dd_pct,
                max_drawdown_duration_days=duration_days,
                average_drawdown=avg_drawdown,
                recovery_factor=float(recovery_factor),
                drawdown_distribution=dd_distribution,
                drawdown_periods=drawdown_periods,
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error analyzing drawdown: {e}")
            return self._empty_drawdown_result()

    def _convert_and_clean_equity(
        self,
        equity_curve: Union[pd.Series, np.ndarray, List[float]],
    ) -> np.ndarray:
        """Convert equity curve to numpy array and remove NaN values."""
        if isinstance(equity_curve, (list, pd.Series)):
            equity_array = np.array(equity_curve, dtype=np.float64)
        else:
            equity_array = equity_curve.astype(np.float64)
        return equity_array[~np.isnan(equity_array)]

    def _calculate_drawdown_from_peak(
        self,
        equity_array: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate drawdown from running peak."""
        running_peak = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_peak) / running_peak
        return drawdown, running_peak

    def _find_max_drawdown(
        self,
        drawdown: np.ndarray,
        equity_array: np.ndarray,
    ) -> Tuple[float, float, int, int]:
        """Find maximum drawdown and its location."""
        max_dd = float(drawdown.min())
        max_dd_pct = max_dd * 100
        max_dd_idx = int(np.argmin(drawdown))
        peak_idx = int(np.argmax(equity_array[: max_dd_idx + 1]))
        return max_dd, max_dd_pct, max_dd_idx, peak_idx

    def _calculate_drawdown_duration(
        self,
        dates: Optional[Union[pd.DatetimeIndex, List[datetime]]],
        max_dd_idx: int,
        peak_idx: int,
    ) -> int:
        """Calculate duration of maximum drawdown in days."""
        if dates is not None and len(dates) > max_dd_idx:
            if isinstance(dates, pd.DatetimeIndex):
                peak_date = dates[peak_idx]
                trough_date = dates[max_dd_idx]
                return (trough_date - peak_date).days
            else:
                return max_dd_idx - peak_idx
        return max_dd_idx - peak_idx

    def _calculate_average_drawdown(self, drawdown: np.ndarray) -> float:
        """Calculate average of negative drawdowns."""
        negative_drawdowns = drawdown[drawdown < 0]
        if len(negative_drawdowns) > 0:
            return float(negative_drawdowns.mean())
        return 0.0

    def _calculate_recovery_factor(
        self,
        equity_array: np.ndarray,
        running_peak: np.ndarray,
        max_dd: float,
    ) -> float:
        """Calculate recovery factor."""
        final_value = equity_array[-1]
        peak_value = running_peak.max()
        if max_dd != 0:
            return (final_value - peak_value) / abs(max_dd)
        return 0.0

    def _calculate_drawdown_distribution(self, drawdown: np.ndarray) -> Dict[str, float]:
        """Calculate distribution of drawdowns."""
        try:
            negative_dd = drawdown[drawdown < 0]

            if len(negative_dd) == 0:
                return {
                    "p5": 0.0,
                    "p25": 0.0,
                    "p50": 0.0,
                    "p75": 0.0,
                    "p95": 0.0,
                }

            return {
                "p5": float(np.percentile(negative_dd, 5)),
                "p25": float(np.percentile(negative_dd, 25)),
                "p50": float(np.percentile(negative_dd, 50)),
                "p75": float(np.percentile(negative_dd, 75)),
                "p95": float(np.percentile(negative_dd, 95)),
            }

        except (ValueError, IndexError):
            return {"p5": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0}

    def _identify_drawdown_periods(
        self,
        drawdown: np.ndarray,
        dates: Optional[pd.DatetimeIndex] = None,
    ) -> List[Dict[str, Any]]:
        """Identify significant drawdown periods."""
        try:
            periods = []
            in_drawdown = False
            start_idx = 0

            for i, dd in enumerate(drawdown):
                if dd < 0 and not in_drawdown:
                    in_drawdown = True
                    start_idx = i
                elif dd >= 0 and in_drawdown:
                    in_drawdown = False

                    peak_idx = int(np.argmax(drawdown[start_idx:i])) + start_idx
                    trough_idx = int(np.argmin(drawdown[start_idx:i])) + start_idx

                    duration = self._calculate_period_duration(
                        dates, peak_idx, trough_idx, start_idx, i
                    )

                    periods.append(
                        {
                            "start_idx": peak_idx,
                            "end_idx": trough_idx,
                            "drawdown": float(drawdown[trough_idx]),
                            "duration_days": duration,
                        }
                    )

            return periods

        except (ValueError, IndexError):
            return []

    def _calculate_period_duration(
        self,
        dates: Optional[pd.DatetimeIndex],
        peak_idx: int,
        trough_idx: int,
        start_idx: int,
        end_idx: int,
    ) -> int:
        """Calculate duration of a drawdown period."""
        if dates is not None and len(dates) > trough_idx:
            start_date = dates[peak_idx]
            end_date = dates[trough_idx]
            if hasattr(end_date - start_date, "days"):
                return (end_date - start_date).days
            else:
                return trough_idx - peak_idx
        return trough_idx - peak_idx

    def _empty_drawdown_result(self) -> DrawdownResult:
        """Return empty drawdown result."""
        return DrawdownResult(
            max_drawdown=0.0,
            max_drawdown_percentage=0.0,
            max_drawdown_duration_days=0,
            average_drawdown=0.0,
            recovery_factor=0.0,
            drawdown_distribution={},
            drawdown_periods=[],
        )


class ChanCalmarRatioCalculator:
    """
    Calmar ratio calculator per Ernest Chan.

    Chan's formula:
    Calmar = Annual Return / Max Drawdown

    Higher is better. Good strategies have Calmar > 1.
    """

    def __init__(self, trading_days: int = 252):
        """
        Initialize Calmar ratio calculator.

        Args:
            trading_days: Trading days per year
        """
        self.trading_days = trading_days

    def calculate_calmar_ratio(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        equity_curve: Optional[Union[pd.Series, np.ndarray, List[float]]] = None,
    ) -> CalmarRatioResult:
        """
        Calculate Calmar ratio.

        Args:
            returns: Return series
            equity_curve: Optional equity curve for drawdown calculation

        Returns:
            CalmarRatioResult with ratio and interpretation

        Examples:
            >>> calc = ChanCalmarRatioCalculator()
            >>> result = calc.calculate_calmar_ratio(returns)
            >>> print(f"Calmar: {result.calmar_ratio:.2f}")
        """
        try:
            returns_array = self._convert_and_clean_returns(returns)
            if len(returns_array) < 2:
                logger.warning("Insufficient data for Calmar ratio")
                return self._insufficient_data_result()

            annual_return = self._calculate_annual_return(returns_array)
            max_dd = self._calculate_max_drawdown(returns_array, equity_curve)
            calmar_ratio = self._compute_calmar_ratio(annual_return, max_dd)
            interpretation = self._interpret_calmar_ratio(calmar_ratio)

            return CalmarRatioResult(
                calmar_ratio=float(calmar_ratio),
                annual_return=float(annual_return),
                max_drawdown=float(max_dd),
                interpretation=interpretation,
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return CalmarRatioResult(
                calmar_ratio=0.0,
                annual_return=0.0,
                max_drawdown=0.0,
                interpretation=f"Calculation error: {e}",
            )

    def _convert_and_clean_returns(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
    ) -> np.ndarray:
        """Convert returns to numpy array and remove NaN values."""
        if isinstance(returns, (list, pd.Series)):
            returns_array = np.array(returns, dtype=np.float64)
        else:
            returns_array = returns.astype(np.float64)
        return returns_array[~np.isnan(returns_array)]

    def _calculate_annual_return(self, returns_array: np.ndarray) -> float:
        """Calculate annualized return."""
        mean_daily_return = float(np.mean(returns_array))
        return mean_daily_return * self.trading_days

    def _calculate_max_drawdown(
        self,
        returns_array: np.ndarray,
        equity_curve: Optional[Union[pd.Series, np.ndarray, List[float]]],
    ) -> float:
        """Calculate maximum drawdown from equity curve or returns."""
        if equity_curve is not None:
            equity_array = self._convert_equity_array(equity_curve)
            running_peak = np.maximum.accumulate(equity_array)
            drawdown = (equity_array - running_peak) / running_peak
            return float(drawdown.min())
        else:
            cumulative = (1 + returns_array).cumprod()
            running_peak = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_peak) / running_peak
            return float(drawdown.min())

    def _convert_equity_array(
        self,
        equity_curve: Union[pd.Series, np.ndarray, List[float]],
    ) -> np.ndarray:
        """Convert equity curve to numpy array."""
        if isinstance(equity_curve, (list, pd.Series)):
            equity_array = np.array(equity_curve, dtype=np.float64)
        else:
            equity_array = equity_curve.astype(np.float64)
        return equity_array[~np.isnan(equity_array)]

    def _compute_calmar_ratio(self, annual_return: float, max_dd: float) -> float:
        """Compute Calmar ratio from annual return and max drawdown."""
        if max_dd == 0:
            return 0.0
        return annual_return / abs(max_dd)

    def _interpret_calmar_ratio(self, calmar_ratio: float) -> str:
        """Interpret Calmar ratio value."""
        if calmar_ratio > 3:
            return "Excellent (Calmar > 3)"
        elif calmar_ratio > 1:
            return "Good (Calmar > 1)"
        elif calmar_ratio > 0.5:
            return "Fair (Calmar > 0.5)"
        else:
            return "Poor (Calmar < 0.5)"

    def _insufficient_data_result(self) -> CalmarRatioResult:
        """Return result for insufficient data case."""
        return CalmarRatioResult(
            calmar_ratio=0.0,
            annual_return=0.0,
            max_drawdown=0.0,
            interpretation="Insufficient data",
        )


class ChanReturnDistributionAnalyzer:
    """
    Return distribution analyzer per Ernest Chan.

    Analyzes the characteristics of return distributions:
    1. Central tendency (mean, median)
    2. Dispersion (std deviation)
    3. Asymmetry (skewness)
    4. Tail behavior (kurtosis, tail ratio)
    5. Up/down capture ratios
    """

    def analyze_return_distribution(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        benchmark_returns: Optional[Union[pd.Series, np.ndarray, List[float]]] = None,
    ) -> ReturnDistributionMetrics:
        """
        Analyze return distribution characteristics.

        Args:
            returns: Strategy return series
            benchmark_returns: Optional benchmark returns for capture ratios

        Returns:
            ReturnDistributionMetrics with comprehensive analysis
        """
        try:
            returns_array = self._convert_and_clean_returns(returns)
            if len(returns_array) < 2:
                logger.warning("Insufficient data for distribution analysis")
                return self._empty_distribution_result()

            mean_return, median_return, std_return = self._calculate_basic_statistics(returns_array)
            positive_pct, negative_pct = self._calculate_win_loss_ratios(returns_array)
            best_day, worst_day = self._calculate_extreme_returns(returns_array)

            up_capture, down_capture = self._calculate_capture_ratios(
                returns_array, benchmark_returns
            )
            tail_ratio = self._calculate_tail_ratio(returns_array)

            return ReturnDistributionMetrics(
                mean_return=mean_return,
                median_return=median_return,
                std_return=std_return,
                positive_return_pct=float(positive_pct),
                negative_return_pct=float(negative_pct),
                best_day_return=best_day,
                worst_day_return=worst_day,
                up_capture_ratio=up_capture,
                down_capture_ratio=down_capture,
                tail_ratio=tail_ratio,
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error analyzing return distribution: {e}")
            return self._empty_distribution_result()

    def _convert_and_clean_returns(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
    ) -> np.ndarray:
        """Convert returns to numpy array and remove NaN values."""
        if isinstance(returns, (list, pd.Series)):
            returns_array = np.array(returns, dtype=np.float64)
        else:
            returns_array = returns.astype(np.float64)
        return returns_array[~np.isnan(returns_array)]

    def _calculate_basic_statistics(
        self,
        returns_array: np.ndarray,
    ) -> Tuple[float, float, float]:
        """Calculate basic return statistics."""
        mean_return = float(np.mean(returns_array))
        median_return = float(np.median(returns_array))
        std_return = float(np.std(returns_array, ddof=1))
        return mean_return, median_return, std_return

    def _calculate_win_loss_ratios(
        self,
        returns_array: np.ndarray,
    ) -> Tuple[float, float]:
        """Calculate win/loss ratios."""
        positive_returns = returns_array[returns_array > 0]
        negative_returns = returns_array[returns_array < 0]

        positive_pct = len(positive_returns) / len(returns_array) if len(returns_array) > 0 else 0
        negative_pct = len(negative_returns) / len(returns_array) if len(returns_array) > 0 else 0
        return positive_pct, negative_pct

    def _calculate_extreme_returns(
        self,
        returns_array: np.ndarray,
    ) -> Tuple[float, float]:
        """Calculate best and worst day returns."""
        best_day = float(returns_array.max())
        worst_day = float(returns_array.min())
        return best_day, worst_day

    def _calculate_capture_ratios(
        self,
        returns_array: np.ndarray,
        benchmark_returns: Optional[Union[pd.Series, np.ndarray, List[float]]],
    ) -> Tuple[float, float]:
        """Calculate up/down capture ratios."""
        up_capture = 0.0
        down_capture = 0.0

        if benchmark_returns is not None:
            returns_aligned, bench_aligned = self._align_benchmark_returns(
                returns_array, benchmark_returns
            )
            up_capture = self._calculate_up_capture(returns_aligned, bench_aligned)
            down_capture = self._calculate_down_capture(returns_aligned, bench_aligned)

        return up_capture, down_capture

    def _align_benchmark_returns(
        self,
        returns_array: np.ndarray,
        benchmark_returns: Union[pd.Series, np.ndarray, List[float]],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Align returns with benchmark returns."""
        if isinstance(benchmark_returns, (list, pd.Series)):
            bench_array = np.array(benchmark_returns, dtype=np.float64)
        else:
            bench_array = benchmark_returns.astype(np.float64)

        min_len = min(len(returns_array), len(bench_array))
        return returns_array[:min_len], bench_array[:min_len]

    def _calculate_up_capture(
        self,
        returns_aligned: np.ndarray,
        bench_aligned: np.ndarray,
    ) -> float:
        """Calculate up capture ratio."""
        up_mask = bench_aligned > 0
        if up_mask.sum() > 0:
            if bench_aligned[up_mask].mean() != 0:
                return float(returns_aligned[up_mask].mean() / bench_aligned[up_mask].mean())
        return 0.0

    def _calculate_down_capture(
        self,
        returns_aligned: np.ndarray,
        bench_aligned: np.ndarray,
    ) -> float:
        """Calculate down capture ratio."""
        down_mask = bench_aligned < 0
        if down_mask.sum() > 0:
            if bench_aligned[down_mask].mean() != 0:
                return float(returns_aligned[down_mask].mean() / bench_aligned[down_mask].mean())
        return 0.0

    def _calculate_tail_ratio(self, returns_array: np.ndarray) -> float:
        """Calculate tail ratio (95th percentile / 5th percentile)."""
        p95 = float(np.percentile(returns_array, 95))
        p5 = float(np.percentile(returns_array, 5))
        return abs(p95 / p5) if p5 != 0 else 0.0

    def _empty_distribution_result(self) -> ReturnDistributionMetrics:
        """Return empty distribution result."""
        return ReturnDistributionMetrics(
            mean_return=0.0,
            median_return=0.0,
            std_return=0.0,
            positive_return_pct=0.0,
            negative_return_pct=0.0,
            best_day_return=0.0,
            worst_day_return=0.0,
            up_capture_ratio=0.0,
            down_capture_ratio=0.0,
            tail_ratio=0.0,
        )


class ChanStrategyComparator:
    """
    Strategy comparison tools per Ernest Chan.

    Compares two strategies using:
    1. Sharpe ratio difference
    2. Statistical significance testing
    3. Tracking error
    4. Information ratio
    """

    def compare_strategies(
        self,
        returns1: Union[pd.Series, np.ndarray, List[float]],
        returns2: Union[pd.Series, np.ndarray, List[float]],
        confidence_level: float = 0.95,
    ) -> StrategyComparisonResult:
        """
        Compare two strategies.

        Args:
            returns1: First strategy returns
            returns2: Second strategy returns
            confidence_level: Confidence level for significance testing

        Returns:
            StrategyComparisonResult with comparison metrics
        """
        try:
            sharpe1, sharpe2 = self._calculate_strategy_sharpe(returns1, returns2)
            sharpe_diff = sharpe1 - sharpe2

            is_significant = self._test_sharpe_difference(returns1, returns2, confidence_level)
            tracking_error = self._calculate_tracking_error(returns1, returns2)
            info_ratio = self._calculate_information_ratio(returns1, returns2)

            recommended = self._determine_recommended_strategy(sharpe1, sharpe2, is_significant)

            return StrategyComparisonResult(
                strategy1_sharpe=float(sharpe1),
                strategy2_sharpe=float(sharpe2),
                sharpe_difference=float(sharpe_diff),
                is_significant=is_significant,
                tracking_error=float(tracking_error),
                information_ratio=float(info_ratio),
                recommended_strategy=recommended,
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error comparing strategies: {e}")
            return StrategyComparisonResult(
                strategy1_sharpe=0.0,
                strategy2_sharpe=0.0,
                sharpe_difference=0.0,
                is_significant=False,
                tracking_error=0.0,
                information_ratio=0.0,
                recommended_strategy="Error",
            )

    def _calculate_strategy_sharpe(
        self,
        returns1: Union[pd.Series, np.ndarray, List[float]],
        returns2: Union[pd.Series, np.ndarray, List[float]],
    ) -> Tuple[float, float]:
        """Calculate Sharpe ratios for both strategies."""
        sharpe_calc = ChanSharpeRatioCalculator()

        sharpe1_result = sharpe_calc.calculate_sharpe_ratio(returns1)
        sharpe2_result = sharpe_calc.calculate_sharpe_ratio(returns2)

        return sharpe1_result.annualized_sharpe, sharpe2_result.annualized_sharpe

    def _determine_recommended_strategy(
        self,
        sharpe1: float,
        sharpe2: float,
        is_significant: bool,
    ) -> str:
        """Determine recommended strategy based on Sharpe comparison."""
        if sharpe1 > sharpe2 and is_significant:
            return "Strategy 1"
        elif sharpe2 > sharpe1 and is_significant:
            return "Strategy 2"
        else:
            return "No significant difference"

    def _test_sharpe_difference(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
        confidence_level: float,
    ) -> bool:
        """Test if Sharpe ratio difference is significant."""
        try:
            sharpe_calc = ChanSharpeRatioCalculator()

            result1 = sharpe_calc.calculate_sharpe_ratio(returns1, confidence_level)
            result2 = sharpe_calc.calculate_sharpe_ratio(returns2, confidence_level)

            # Check for overlap
            return (
                result1.confidence_interval_low > result2.confidence_interval_high
                or result2.confidence_interval_low > result1.confidence_interval_high
            )

        except (ValueError, TypeError):
            return False

    def _calculate_tracking_error(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
    ) -> float:
        """Calculate tracking error between strategies."""
        try:
            min_len = min(len(returns1), len(returns2))
            r1 = returns1[:min_len]
            r2 = returns2[:min_len]

            diff = r1 - r2
            return float(np.std(diff, ddof=1) * np.sqrt(252))

        except (ValueError, TypeError):
            return 0.0

    def _calculate_information_ratio(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
    ) -> float:
        """Calculate information ratio (Strategy 1 vs Strategy 2)."""
        try:
            min_len = min(len(returns1), len(returns2))
            r1 = returns1[:min_len]
            r2 = returns2[:min_len]

            excess = r1 - r2

            mean_excess = np.mean(excess)
            std_excess = np.std(excess, ddof=1)

            if std_excess == 0:
                return 0.0

            return float(mean_excess / std_excess * np.sqrt(252))

        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0


# Convenience functions
def calculate_sharpe_ratio(
    returns: Union[pd.Series, np.ndarray, List[float]],
    risk_free_rate: float = 0.02,
) -> float:
    """Convenience function to calculate Sharpe ratio."""
    calc = ChanSharpeRatioCalculator(risk_free_rate=risk_free_rate)
    result = calc.calculate_sharpe_ratio(returns)
    return result.annualized_sharpe


def calculate_max_drawdown(
    equity_curve: Union[pd.Series, np.ndarray, List[float]],
) -> float:
    """Convenience function to calculate maximum drawdown."""
    analyzer = ChanDrawdownAnalyzer()
    result = analyzer.analyze_drawdown(equity_curve)
    return result.max_drawdown_percentage


def calculate_calmar_ratio(
    returns: Union[pd.Series, np.ndarray, List[float]],
) -> float:
    """Convenience function to calculate Calmar ratio."""
    calc = ChanCalmarRatioCalculator()
    result = calc.calculate_calmar_ratio(returns)
    return result.calmar_ratio
