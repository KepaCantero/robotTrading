"""
Half-Life Calculator for Mean Reversion Strategies

This module implements Ornstein-Uhlenbeck half-life calculation as described
in Ernest Chan's "Quantitative Trading" (Chapter 2).

Half-life measures the expected time for a mean-reverting process to return
to its mean. It's critical for:
- Position sizing (shorter half-life = larger positions)
- Stop loss timing
- Strategy selection
- Risk management

Key Features:
- Ornstein-Uhlenbeck process fitting
- Half-life calculation with confidence intervals
- Mean reversion speed estimation
- Statistical significance testing

Reference:
    "Quantitative Trading" by Ernest P. Chan
    Chapter 2: Basic Statistical Strategies
    Section: Mean Reversion
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class HalfLifeResult:
    """Result of half-life calculation."""

    half_life_days: float
    half_life_hours: Optional[float]  # For intraday data
    mean_reversion_rate: float  # Theta in OU process
    mean_level: float  # Long-term mean
    mean_reversion_speed: str  # 'fast', 'medium', 'slow'
    is_mean_reverting: bool
    p_value: float  # Statistical significance
    confidence_interval: Tuple[float, float]  # 95% CI for half-life
    hurst_exponent: Optional[float]  # Hurst exponent for confirmation
    stationarity_test: Optional[str]  # ADF test result


@dataclass
class OUProcessParams:
    """Parameters of Ornstein-Uhlenbeck process."""

    theta: float  # Mean reversion rate
    mu: float  # Long-term mean
    sigma: float  # Volatility
    half_life: float  # Half-life in same units as data frequency


class HalfLifeCalculator:
    """
    Calculates half-life for mean-reverting processes using
    Ornstein-Uhlenbeck process estimation.

    The OU process is described by:
    dx = theta * (mu - x) * dt + sigma * dW

    Where:
    - theta: Mean reversion rate (higher = faster reversion)
    - mu: Long-term mean
    - sigma: Volatility
    - Half-life = ln(2) / theta

    This implements Ernest Chan's methodology from "Quantitative Trading".
    """

    def __init__(self, min_samples: int = 30, confidence_level: float = 0.95):
        """
        Initialize the half-life calculator.

        Args:
            min_samples: Minimum samples required for calculation
            confidence_level: Confidence level for intervals (default 95%)
        """
        self.min_samples = min_samples
        self.confidence_level = confidence_level

        logger.info(
            f"HalfLifeCalculator initialized: min_samples={min_samples}, "
            f"confidence_level={confidence_level}"
        )

    def calculate_half_life(
        self,
        prices: pd.Series | np.ndarray | List[float],
        data_frequency: str = "D",
        confidence_interval: bool = True,
        adf_test: bool = True,
    ) -> HalfLifeResult:
        """
        Calculate half-life for a price series using OU process.

        This implements the regression-based method from Ernest Chan:
        1. Calculate lagged returns: y(t) - y(t-1)
        2. Regress against deviation from mean: y(t-1) - mean
        3. Extract theta (mean reversion rate) from slope
        4. Calculate half-life = ln(2) / theta

        Args:
            prices: Price series (any format convertible to numpy array)
            data_frequency: Frequency of data ('D'=daily, 'H'=hourly, 'M'=monthly)
            confidence_interval: Calculate confidence intervals
            adf_test: Perform Augmented Dickey-Fuller test

        Returns:
            HalfLifeResult with calculated metrics
        """
        try:
            # Convert to numpy array
            if isinstance(prices, pd.Series):
                price_array = prices.values
            elif isinstance(prices, list):
                price_array = np.array(prices)
            else:
                price_array = prices

            # Validate input
            if len(price_array) < self.min_samples:
                logger.warning(
                    f"Insufficient data for half-life calculation: "
                    f"{len(price_array)} < {self.min_samples}"
                )
                return self._create_invalid_result()

            # Check for constant or NaN values
            if np.all(np.isnan(price_array)) or np.std(price_array) == 0:
                logger.warning("Price series is constant or contains NaN")
                return self._create_invalid_result()

            # Calculate OU process parameters
            ou_params = self._fit_ou_process(price_array)

            if ou_params is None:
                return self._create_invalid_result()

            # Calculate half-life
            half_life = -np.log(2) / ou_params.theta if ou_params.theta > 0 else float("inf")

            # Classify mean reversion speed
            if data_frequency == "D":
                # Daily data
                if half_life < 5:
                    speed = "fast"
                elif half_life < 20:
                    speed = "medium"
                else:
                    speed = "slow"
            elif data_frequency == "H":
                # Hourly data
                if half_life < 24:
                    speed = "fast"
                elif half_life < 120:
                    speed = "medium"
                else:
                    speed = "slow"
            else:
                # Default classification
                speed = "medium"

            # Calculate confidence interval if requested
            ci = (0.0, 0.0)
            p_value = 0.0
            if confidence_interval:
                ci, p_value = self._calculate_confidence_interval(price_array, ou_params.theta)

            # Perform ADF test if requested
            adf_result = None
            if adf_test:
                adf_result = self._perform_adf_test(price_array)

            # Calculate Hurst exponent for confirmation
            hurst = self._calculate_hurst_exponent(price_array)

            # Determine if series is mean-reverting
            is_mean_reverting = (
                ou_params.theta > 0
                and half_life < float("inf")
                and (adf_result is None or "stationary" in adf_result.lower())
            )

            result = HalfLifeResult(
                half_life_days=half_life if data_frequency == "D" else half_life * 24,
                half_life_hours=half_life if data_frequency == "H" else None,
                mean_reversion_rate=ou_params.theta,
                mean_level=ou_params.mu,
                mean_reversion_speed=speed,
                is_mean_reverting=is_mean_reverting,
                p_value=p_value,
                confidence_interval=ci,
                hurst_exponent=hurst,
                stationarity_test=adf_result,
            )

            logger.info(
                f"Half-life calculated: {half_life:.2f} periods, "
                f"theta={ou_params.theta:.6f}, "
                f"speed={speed}, "
                f"mean_reverting={is_mean_reverting}"
            )

            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating half-life: {e}")
            return self._create_invalid_result()

    def _fit_ou_process(self, prices: np.ndarray) -> Optional[OUProcessParams]:
        """
        Fit Ornstein-Uhlenbeck process to price series.

        Uses regression method from Ernest Chan:
        - Regress (y[t] - y[t-1]) on (y[t-1] - mean)
        - Slope = -theta (mean reversion rate)
        """
        try:
            # Calculate lagged differences
            y_lag = prices[:-1]
            y_diff = np.diff(prices)

            # Calculate mean
            mu = np.mean(y_lag)

            # Calculate deviation from mean
            y_deviation = y_lag - mu

            # Perform regression: y_diff = -theta * y_deviation + noise
            # If std is 0, can't fit
            if np.std(y_deviation) == 0:
                return None

            slope, intercept, r_value, p_value, std_err = stats.linregress(y_deviation, y_diff)

            # Theta is negative of slope (since slope = -theta)
            theta = -slope

            # Estimate sigma (volatility) from residuals
            predicted = intercept + slope * y_deviation
            residuals = y_diff - predicted
            sigma = np.std(residuals)

            # Validate theta (should be positive for mean reversion)
            if theta <= 0:
                logger.warning(f"Negative theta ({theta:.6f}) - series may not be mean-reverting")
                # Still return result, but theta indicates non-mean-reverting

            # Calculate half-life
            half_life = -np.log(2) / theta if theta > 0 else float("inf")

            return OUProcessParams(
                theta=theta,
                mu=mu,
                sigma=sigma,
                half_life=half_life,
            )

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error fitting OU process: {e}")
            return None

    def _calculate_confidence_interval(
        self, prices: np.ndarray, theta: float
    ) -> Tuple[Tuple[float, float], float]:
        """
        Calculate confidence interval for half-life.

        Uses delta method to estimate CI for half-life from theta CI.
        """
        try:
            # Bootstrap for confidence interval
            n_bootstrap = 1000
            half_lives = []

            for _ in range(n_bootstrap):
                # Resample with replacement
                bootstrap_sample = np.random.choice(prices, size=len(prices), replace=True)

                # Fit OU process
                ou_params = self._fit_ou_process(bootstrap_sample)

                if ou_params and ou_params.theta > 0:
                    hl = -np.log(2) / ou_params.theta
                    half_lives.append(hl)

            if len(half_lives) == 0:
                return ((0.0, 0.0), 1.0)

            # Calculate percentiles
            alpha = 1 - self.confidence_level
            lower = np.percentile(half_lives, alpha / 2 * 100)
            upper = np.percentile(half_lives, (1 - alpha / 2) * 100)

            # P-value: test if theta is significantly different from 0
            # (i.e., is series mean-reverting?)
            p_value = self._calculate_theta_significance(prices)

            return ((lower, upper), p_value)

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating confidence interval: {e}")
            return ((0.0, 0.0), 1.0)

    def _calculate_theta_significance(self, prices: np.ndarray) -> float:
        """
        Calculate p-value for theta (mean reversion rate).

        Tests H0: theta = 0 (no mean reversion) vs H1: theta > 0 (mean reversion)
        """
        try:
            # Perform regression and get p-value from scipy
            y_lag = prices[:-1]
            y_diff = np.diff(prices)
            mu = np.mean(y_lag)
            y_deviation = y_lag - mu

            if np.std(y_deviation) == 0:
                return 1.0

            slope, intercept, r_value, p_value, std_err = stats.linregress(y_deviation, y_diff)

            # One-tailed test (theta > 0 means slope < 0)
            # p-value from linregress is two-tailed
            p_value_one_tailed = p_value / 2 if slope < 0 else 1 - p_value / 2

            return p_value_one_tailed

        except (ValueError, TypeError):
            return 1.0

    def _perform_adf_test(self, prices: np.ndarray) -> Optional[str]:
        """
        Perform Augmented Dickey-Fuller test for stationarity.

        Returns description of test result.
        """
        try:
            from app.shared.performance.statsmodels_fallback import adfuller

            result = adfuller(prices, maxlag=10, regression="c")

            result[0]
            p_value = result[1]
            result[4]

            if p_value < 0.01:
                return "stationary (p<0.01) - strong evidence of mean reversion"
            elif p_value < 0.05:
                return "stationary (p<0.05) - evidence of mean reversion"
            elif p_value < 0.10:
                return "stationary (p<0.10) - weak evidence of mean reversion"
            else:
                return "non-stationary - no evidence of mean reversion"

        except ImportError:
            logger.warning("statsmodels not available for ADF test")
            return None
        except Exception as e:
            logger.error(f"Error performing ADF test: {e}")
            return None

    def _calculate_hurst_exponent(self, prices: np.ndarray) -> Optional[float]:
        """
        Calculate Hurst exponent for confirmation.

        H < 0.5: Mean-reverting
        H = 0.5: Random walk
        H > 0.5: Trending
        """
        try:
            # Calculate Hurst using R/S analysis
            lags = range(2, min(20, len(prices) // 2))

            tau = [
                np.std(
                    np.subtract(
                        prices[lag:], prices[:-lag] if lag > 0 else prices[: len(prices) - lag]
                    )
                )
                for lag in lags
            ]

            # Fit log-log plot
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            hurst = poly[0] / 2.0

            return hurst

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating Hurst exponent: {e}")
            return None

    def _create_invalid_result(self) -> HalfLifeResult:
        """Create invalid result for error cases."""
        return HalfLifeResult(
            half_life_days=float("inf"),
            half_life_hours=None,
            mean_reversion_rate=0.0,
            mean_level=0.0,
            mean_reversion_speed="unknown",
            is_mean_reverting=False,
            p_value=1.0,
            confidence_interval=(0.0, 0.0),
            hurst_exponent=None,
            stationarity_test=None,
        )

    def compare_half_lives(self, results: List[HalfLifeResult]) -> Dict[str, Any]:
        """
        Compare multiple half-life results.

        Useful for selecting best pairs for pairs trading or
        comparing different mean reversion strategies.

        Args:
            results: List of HalfLifeResult objects

        Returns:
            Dictionary with comparison metrics
        """
        try:
            valid_results = [r for r in results if r.is_mean_reverting]

            if not valid_results:
                return {"error": "No valid mean-reverting series"}

            half_lives = [r.half_life_days for r in valid_results]

            return {
                "count": len(valid_results),
                "min_half_life": min(half_lives),
                "max_half_life": max(half_lives),
                "mean_half_life": np.mean(half_lives),
                "median_half_life": np.median(half_lives),
                "std_half_life": np.std(half_lives),
                "fastest": min(valid_results, key=lambda r: r.half_life_days),
                "slowest": max(valid_results, key=lambda r: r.half_life_days),
            }

        except (ValueError, TypeError) as e:
            logger.error(f"Error comparing half-lives: {e}")
            return {"error": str(e)}


def calculate_half_life(
    prices: List[float] | pd.Series,
    data_frequency: str = "D",
    min_samples: int = 30,
) -> HalfLifeResult:
    """
    Convenience function to calculate half-life for mean reversion.

    Args:
        prices: Price series
        data_frequency: Data frequency ('D', 'H', 'M')
        min_samples: Minimum samples required

    Returns:
        HalfLifeResult with calculated metrics
    """
    calculator = HalfLifeCalculator(min_samples=min_samples)
    return calculator.calculate_half_life(prices, data_frequency)
