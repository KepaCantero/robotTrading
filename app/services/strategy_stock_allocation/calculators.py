"""
Statistical calculation modules.

Provides specialized calculators for Hurst exponent, half-life, and
stationarity testing following Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from app.shared.config.params.strategy_config import StockAllocationSettings

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from statsmodels.regression.linear_model import OLS as sm_OLS
    from statsmodels.tsa.stattools import adfuller, kpss

    STATSMODELS_AVAILABLE = True

    def OLS(*args, **kwargs):
        return sm_OLS(*args, **kwargs)

except ImportError:
    STATSMODELS_AVAILABLE = False

    def OLS(*args, **kwargs):
        """Fallback OLS when statsmodels is not available."""
        import warnings

        warnings.warn(
            "statsmodels not installed - OLS regression not available. "
            "Install statsmodels: pip install statsmodels",
            ImportWarning,
        )
        return None

    # Provide fallback implementations
    def adfuller(*args, **kwargs):
        """
        Fallback adfuller function when statsmodels is not available.

        Returns a tuple indicating stationarity test failed.
        """
        import warnings

        warnings.warn(
            "statsmodels not installed - ADF test not available. "
            "Install statsmodels for stationarity testing: pip install statsmodels",
            ImportWarning,
        )
        # Return p-value of 1.0 (fail to reject null hypothesis of non-stationarity)
        return (None, 1.0, None, None, None, None, None)

    def kpss(*args, **kwargs):
        """
        Fallback kpss function when statsmodels is not available.

        Returns a tuple indicating stationarity test failed.
        """
        import warnings

        warnings.warn(
            "statsmodels not installed - KPSS test not available. "
            "Install statsmodels for stationarity testing: pip install statsmodels",
            ImportWarning,
        )
        # Return p-value of 0.0 (reject null hypothesis of stationarity)
        return (None, 0.0, None, None)


class HurstCalculator:
    """
    Calculates Hurst exponent using R/S (Rescaled Range) method.

    The Hurst exponent measures the long-term memory of a time series:
    - H > 0.55: Momentum/trending behavior
    - H < 0.45: Mean reverting behavior
    - H ≈ 0.5: Random walk
    """

    def __init__(self, config: StockAllocationSettings) -> None:
        """
        Initialize Hurst calculator with configuration.

        Args:
            config: Stock allocation configuration
        """
        self.config = config

    def calculate(self, prices: np.ndarray, max_lag: int | None = None) -> float | None:
        """
        Calculate Hurst exponent using R/S (Rescaled Range) method.

        Args:
            prices: Price series as numpy array
            max_lag: Maximum lag for calculation (default: len(prices) // 2)

        Returns:
            Hurst exponent (0 < H < 1), or None if calculation fails
        """
        if len(prices) < 50:
            logger.warning(f"Insufficient data for Hurst: {len(prices)} < 50")
            return None

        try:
            # Convert prices to returns (log returns)
            returns = np.diff(np.log(prices))

            if len(returns) < 10:
                return None

            # Set max_lag if not provided
            if max_lag is None:
                max_lag = len(returns) // 2

            max_lag = min(max_lag, len(returns) // 2)
            lags = range(10, max_lag, max(1, max_lag // 20))

            if len(lags) < 3:
                return None

            rs_values = []

            for lag in lags:
                n = lag
                if n >= len(returns):
                    continue

                # Split into non-overlapping windows
                num_windows = len(returns) // n
                if num_windows < 2:
                    continue

                rs_window = []

                for i in range(num_windows):
                    window_returns = returns[i * n : (i + 1) * n]

                    if len(window_returns) < 2:
                        continue

                    # Calculate mean
                    mean_return = np.mean(window_returns)

                    # Calculate deviations from mean
                    deviations = window_returns - mean_return

                    # Calculate cumulative deviations
                    cum_deviations = np.cumsum(deviations)

                    # Calculate range (R)
                    R = np.max(cum_deviations) - np.min(cum_deviations)

                    # Calculate standard deviation (S)
                    S = np.std(window_returns)

                    # Avoid division by zero
                    if S == 0 or R == 0:
                        continue

                    # R/S ratio
                    rs_ratio = R / S
                    if np.isfinite(rs_ratio) and rs_ratio > 0:
                        rs_window.append(rs_ratio)

                if rs_window:
                    avg_rs = np.mean(rs_window)
                    rs_values.append((n, avg_rs))

            if len(rs_values) < 3:
                logger.warning("Insufficient R/S values for Hurst calculation")
                return None

            # Extract lags and RS values
            lags_arr = np.array([x[0] for x in rs_values])
            rs_arr = np.array([x[1] for x in rs_values])

            # Log-log regression: log(R/S) = H * log(n) + c
            log_lags = np.log(lags_arr)
            log_rs = np.log(rs_arr)

            # Remove any infinite or NaN values
            valid_mask = np.isfinite(log_lags) & np.isfinite(log_rs)
            if np.sum(valid_mask) < 3:
                return None

            log_lags = log_lags[valid_mask]
            log_rs = log_rs[valid_mask]

            # Linear regression
            slope, intercept = np.polyfit(log_lags, log_rs, 1)

            # Hurst exponent is the slope
            hurst = float(slope)

            # Sanity check: Hurst should be between 0 and 1
            if 0 < hurst < 1:
                logger.debug(f"Hurst exponent calculated: {hurst:.4f} from {len(rs_values)} points")
                return hurst
            else:
                logger.warning(f"Hurst out of bounds: {hurst:.4f}")
                return None

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Hurst exponent: {e}", exc_info=True)
            return None


class HalfLifeCalculator:
    """
    Calculates half-life from Ornstein-Uhlenbeck model.

    Half-life represents how long it takes for a spread to revert
    half-way to its mean after a deviation.
    """

    def __init__(self, config: StockAllocationSettings) -> None:
        """
        Initialize half-life calculator with configuration.

        Args:
            config: Stock allocation configuration
        """
        self.config = config

    def calculate(self, spread: pd.Series) -> float | None:
        """
        Calculate half-life (τ) from Ornstein-Uhlenbeck model.

        Args:
            spread: Spread series (e.g., price1 - beta * price2)

        Returns:
            Half-life in days, or None if calculation fails
        """
        if len(spread) < 20:
            logger.warning(f"Insufficient data for half-life: {len(spread)} < 20")
            return None

        try:
            # Remove NaNs
            clean_spread = spread.dropna()
            if len(clean_spread) < 20:
                return None

            # O-U model: dy(t) = -θ * (y(t) - μ) * dt + σ * dW(t)
            # Estimate using linear regression

            y = clean_spread.values
            y_lag = y[:-1]
            y_diff = np.diff(y)

            # Remove any infinite or NaN values
            valid_mask = np.isfinite(y_lag) & np.isfinite(y_diff)
            if np.sum(valid_mask) < 10:
                return None

            y_lag = y_lag[valid_mask]
            y_diff = y_diff[valid_mask]

            # Estimate mean (μ)
            mu = np.mean(y_lag)

            # Calculate deviation from mean
            y_deviation = y_lag - mu

            # Linear regression: y_diff = -θ * y_deviation + ε
            if np.std(y_deviation) > 0:
                coeffs = np.polyfit(y_deviation, y_diff, 1)
                theta = -float(coeffs[0])
            else:
                return None

            # Half-life: τ = -ln(2) / θ
            if theta > 1e-10:
                half_life = -np.log(2) / theta
                half_life = float(half_life)

                # Sanity check: half-life must be positive and reasonable
                if np.isfinite(half_life) and 0 < half_life < 1000:
                    logger.debug(f"Half-life calculated: {half_life:.2f} days (theta={theta:.6f})")
                    return half_life
                elif not np.isfinite(half_life) or half_life <= 0:
                    logger.debug(
                        f"Half-life invalid (non-finite or negative): {half_life:.2f} (theta={theta:.6f})"
                    )
                    return None
                else:
                    logger.debug(f"Half-life out of bounds: {half_life:.2f} (theta={theta:.6f})")
                    return None
            else:
                logger.debug(f"Theta too small or negative ({theta:.6f}), not mean-reverting")
                return None

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error calculating half-life: {e}", exc_info=True)
            return None


class StationarityTester:
    """
    Tests time series for stationarity using ADF and KPSS tests.

    Dual testing approach:
    - ADF Test: Null hypothesis is non-stationary
    - KPSS Test: Null hypothesis is stationary
    """

    def __init__(self, config: StockAllocationSettings) -> None:
        """
        Initialize stationarity tester with configuration.

        Args:
            config: Stock allocation configuration
        """
        self.config = config

    def test(self, series: pd.Series) -> dict[str, Any]:
        """
        Dual stationarity test: ADF + KPSS.

        Args:
            series: Time series to test

        Returns:
            Dictionary with test results and stationarity type
        """
        result = {
            "adf_pvalue": None,
            "adf_stationary": False,
            "kpss_pvalue": None,
            "kpss_stationary": False,
            "stationarity_type": "unknown",
            "is_stationary": False,
        }

        if len(series) < 10:
            logger.warning("Insufficient data for stationarity tests")
            return result

        try:
            # Remove NaNs
            clean_series = series.dropna()
            if len(clean_series) < 10:
                return result

            # Check if statsmodels is available
            if not STATSMODELS_AVAILABLE:
                logger.debug("statsmodels not available - stationarity test skipped")
                return result

            # ADF Test (null hypothesis: non-stationary)
            adf_result = adfuller(clean_series, autolag='AIC')
            adf_pvalue = adf_result[1]
            result["adf_pvalue"] = float(adf_pvalue)
            result["adf_stationary"] = adf_pvalue < self.config.ADF_P_VALUE_THRESHOLD

            # KPSS Test (null hypothesis: stationary)
            try:
                kpss_result = kpss(clean_series, regression='ct', nlags='auto')
                kpss_pvalue = kpss_result[1]
                result["kpss_pvalue"] = float(kpss_pvalue)
                result["kpss_stationary"] = kpss_pvalue > self.config.KPSS_P_VALUE_THRESHOLD
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.debug(f"KPSS test failed: {e}, using ADF result only")
                result["kpss_stationary"] = result["adf_stationary"]

            # Determine stationarity type
            if result["adf_stationary"] and result["kpss_stationary"]:
                result["is_stationary"] = True
                result["stationarity_type"] = "strict_stationary"
            elif result["adf_stationary"] and not result["kpss_stationary"]:
                result["is_stationary"] = True
                result["stationarity_type"] = "trend_stationary"
            elif not result["adf_stationary"]:
                result["is_stationary"] = False
                result["stationarity_type"] = "non_stationary"

            logger.debug(f"Stationarity test: {result}")
            return result

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error in stationarity test: {e}", exc_info=True)
            return result
