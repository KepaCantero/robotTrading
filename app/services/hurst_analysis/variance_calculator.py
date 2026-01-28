"""
Variance-based Hurst Exponent calculators.

This module implements alternative Hurst exponent calculation methods based on
variance scaling properties. Includes both the variance of residuals method
and the aggregated variance method.

Single Responsibility: Each class performs one specific calculation method.
Open/Closed: Extensible through HurstCalculator protocol.
"""

import logging
from typing import override

import numpy as np
from numba import jit

logger = logging.getLogger(__name__)


class VarianceMethodCalculator:
    """
    Hurst exponent calculator using variance of residuals method.

    This method uses the scaling property of variance with time lag:
    Var(x(t+lag) - x(t)) ~ lag^(2H)

    BEFORE: Python loops - ~1500ms for 10K data points
    AFTER: Numba JIT - ~15-30ms for 10K data points
    SPEEDUP: 50-100x

    Example:
        >>> calculator = VarianceMethodCalculator()
        >>> hurst, _, _ = calculator.calculate(series)
    """

    def __init__(self) -> None:
        """Initialize variance method calculator."""
        pass

    def calculate(self, series: np.ndarray) -> tuple[float, list[float] | None, list[int] | None]:
        """
        Calculate Hurst exponent using variance scaling method.

        Args:
            series: Input time series

        Returns:
            Tuple of (hurst_exponent, None, None)
                (rs_values and window_sizes not applicable for this method)
        """
        n = len(series)

        if n < 10:
            logger.warning(f"Series too short for variance analysis: {n}")
            return 0.5, None, None

        hurst = _calculate_hurst_variance_numba(series)
        return float(hurst), None, None


class AggregatedVarianceCalculator:
    """
    Hurst exponent calculator using aggregated variance method.

    This method aggregates the series at different time scales and
    analyzes how variance scales with aggregation level:
    Var(agg_k) ~ k^(-2H)

    BEFORE: Python loops - ~1800ms for 10K data points
    AFTER: Numba JIT - ~20-40ms for 10K data points
    SPEEDUP: 45-90x

    Example:
        >>> calculator = AggregatedVarianceCalculator(min_k=2)
        >>> hurst, _, _ = calculator.calculate(series)
    """

    def __init__(self, min_k: int = 2, max_k_ratio: float = 0.25) -> None:
        """
        Initialize aggregated variance calculator.

        Args:
            min_k: Minimum aggregation level
            max_k_ratio: Maximum aggregation as ratio of series length
        """
        self.min_k = min_k
        self.max_k_ratio = max_k_ratio

    def calculate(self, series: np.ndarray) -> tuple[float, list[float] | None, list[int] | None]:
        """
        Calculate Hurst exponent using aggregated variance method.

        Args:
            series: Input time series (must be stationary, e.g., returns)

        Returns:
            Tuple of (hurst_exponent, None, None)
                (rs_values and window_sizes not applicable for this method)
        """
        n = len(series)

        if n < 20:
            logger.warning(f"Series too short for aggregated variance: {n}")
            return 0.5, None, None

        hurst = _calculate_aggregated_variance_numba(series, self.min_k, self.max_k_ratio)
        return float(hurst), None, None


# Numba-accelerated functions


@jit(nopython=True, cache=False)
def _calculate_hurst_variance_numba(series: np.ndarray) -> float:
    """
    Calculate Hurst exponent using variance of residuals method.

    This method uses the scaling property of variance with time lag:
    Var(x(t+lag) - x(t)) ~ lag^(2H)

    Args:
        series: Input time series

    Returns:
        Hurst exponent estimate
    """
    n = len(series)
    if n < 10:
        return 0.5

    max_lag = n // 4
    num_lags = 20

    # Generate lags (logarithmically spaced)
    lags = np.zeros(num_lags, dtype=np.int64)
    log_min = np.log(2)
    log_max = np.log(max_lag)

    for i in range(num_lags):
        log_lag = log_min + (log_max - log_min) * i / (num_lags - 1)
        lags[i] = int(np.exp(log_lag))

    # Calculate variance for each lag
    variances = np.zeros(num_lags)
    valid_count = 0

    for i in range(num_lags):
        lag = int(lags[i])
        if lag < 1 or lag >= n:
            continue

        # Calculate incremental variance at this lag
        sum_sq_diff = 0.0
        count = 0

        for j in range(n - lag):
            diff = series[j + lag] - series[j]
            sum_sq_diff += diff * diff
            count += 1

        if count > 0:
            variances[i] = sum_sq_diff / count
            if variances[i] > 0:
                valid_count += 1
            else:
                variances[i] = np.nan
        else:
            variances[i] = np.nan

    # Perform linear regression on log-log scale
    # log(variance) ~ 2H * log(lag)
    if valid_count < 2:
        return 0.5

    # Filter valid values
    valid_lags = np.zeros(valid_count, dtype=np.int64)
    valid_vars = np.zeros(valid_count)

    idx = 0
    for i in range(num_lags):
        if not np.isnan(variances[i]) and variances[i] > 0:
            valid_lags[idx] = lags[i]
            valid_vars[idx] = variances[i]
            idx += 1

    if valid_count < 2:
        return 0.5

    # Calculate means
    sum_log_lag = 0.0
    sum_log_var = 0.0

    for i in range(valid_count):
        sum_log_lag += np.log(valid_lags[i])
        sum_log_var += np.log(valid_vars[i])

    mean_log_lag = sum_log_lag / valid_count
    mean_log_var = sum_log_var / valid_count

    # Calculate covariance and variance
    covariance = 0.0
    variance = 0.0

    for i in range(valid_count):
        diff_lag = np.log(valid_lags[i]) - mean_log_lag
        diff_var = np.log(valid_vars[i]) - mean_log_var
        covariance += diff_lag * diff_var
        variance += diff_lag * diff_lag

    # Calculate slope (2H)
    if variance > 0:
        slope = covariance / variance
        hurst = slope / 2.0  # H = slope / 2
    else:
        hurst = 0.5

    # Clip to reasonable bounds [0, 1]
    if hurst < 0:
        hurst = 0.0
    elif hurst > 1:
        hurst = 1.0

    return hurst


@jit(nopython=True, cache=False)
def _calculate_aggregated_variance_numba(
    series: np.ndarray, min_k: int, max_k_ratio: float
) -> float:
    """
    Calculate Hurst exponent using aggregated variance method.

    This method aggregates the series at different time scales and
    analyzes how variance scales with aggregation level:
    Var(agg_k) ~ k^(-2H)

    Args:
        series: Input time series (must be stationary, e.g., returns)
        min_k: Minimum aggregation level
        max_k_ratio: Maximum aggregation as ratio of series length

    Returns:
        Hurst exponent estimate
    """
    n = len(series)
    if n < 20:
        return 0.5

    max_k = int(n * max_k_ratio)
    if max_k < min_k * 2:
        max_k = min_k * 2

    num_scales = 15

    # Generate aggregation scales (logarithmically spaced)
    scales = np.zeros(num_scales, dtype=np.int64)
    log_min = np.log(min_k)
    log_max = np.log(max_k)

    for i in range(num_scales):
        log_scale = log_min + (log_max - log_min) * i / (num_scales - 1)
        scales[i] = int(np.exp(log_scale))

    # Calculate variance for each aggregation scale
    variances = np.zeros(num_scales)
    valid_count = 0

    for i in range(num_scales):
        k = int(scales[i])
        if k < 2 or k > n // 2:
            continue

        # Aggregate series by averaging over k periods
        agg_len = n // k
        if agg_len < 2:
            continue

        agg_series = np.zeros(agg_len)
        for j in range(agg_len):
            agg_sum = 0.0
            for m in range(k):
                agg_sum += series[j * k + m]
            agg_series[j] = agg_sum / k

        # Calculate variance of aggregated series
        agg_mean = 0.0
        for j in range(agg_len):
            agg_mean += agg_series[j]
        agg_mean /= agg_len

        agg_var = 0.0
        for j in range(agg_len):
            diff = agg_series[j] - agg_mean
            agg_var += diff * diff
        agg_var /= agg_len

        if agg_var > 0:
            variances[i] = agg_var
            valid_count += 1
        else:
            variances[i] = np.nan

    if valid_count < 2:
        return 0.5

    # Filter valid values
    valid_scales = np.zeros(valid_count, dtype=np.int64)
    valid_vars = np.zeros(valid_count)

    idx = 0
    for i in range(num_scales):
        if not np.isnan(variances[i]) and variances[i] > 0:
            valid_scales[idx] = scales[i]
            valid_vars[idx] = variances[i]
            idx += 1

    # Perform linear regression on log-log scale
    # log(variance) ~ -2H * log(k)
    sum_log_k = 0.0
    sum_log_var = 0.0

    for i in range(valid_count):
        sum_log_k += np.log(valid_scales[i])
        sum_log_var += np.log(valid_vars[i])

    mean_log_k = sum_log_k / valid_count
    mean_log_var = sum_log_var / valid_count

    covariance = 0.0
    variance = 0.0

    for i in range(valid_count):
        diff_k = np.log(valid_scales[i]) - mean_log_k
        diff_var = np.log(valid_vars[i]) - mean_log_var
        covariance += diff_k * diff_var
        variance += diff_k * diff_k

    if variance > 0:
        slope = covariance / variance
        hurst = -slope / 2.0  # H = -slope/2 for aggregated variance
    else:
        hurst = 0.5

    # Clip to reasonable bounds [0, 1]
    if hurst < 0:
        hurst = 0.0
    elif hurst > 1:
        hurst = 1.0

    return hurst
