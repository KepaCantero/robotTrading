"""
Stationarity and Cointegration Analyzer

This module implements Ernest Chan's methodologies from "Algorithmic Trading: A Practitioner's Guide"
for analyzing stationarity and cointegration in financial time series.

Key Concepts from Ernest Chan:
1. Stationarity testing using Augmented Dickey-Fuller (ADF) test
2. Cointegration testing for pair trading strategies
3. Half-life of mean reversion
4. Hurst exponent for trend/stationarity detection
5. Optimal lookback periods for mean reversion

Reference:
    "Algorithmic Trading" by Ernest P. Chan (2013)
    Chapter 2: Stationarity and Cointegration
    Chapter 6: Mean Reversion Strategies
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class StationarityTestResult:
    """Results from ADF stationarity test."""

    is_stationary: bool
    adf_statistic: float
    p_value: float
    critical_values: Dict[str, float]
    confidence_level: float
    half_life: Optional[float] = None
    hurst_exponent: Optional[float] = None
    interpretation: str = ""


@dataclass
class CointegrationTestResult:
    """Results from cointegration test."""

    is_cointegrated: bool
    test_statistic: float
    p_value: float
    critical_values: Dict[str, float]
    hedge_ratio: float
    spread_half_life: float
    confidence_level: float
    interpretation: str = ""
    mean_reversion_speed: str = ""


@dataclass
class MeanReversionParameters:
    """Optimal parameters for mean reversion strategy."""

    optimal_lookback: int
    optimal_entry_threshold: float
    optimal_exit_threshold: float
    expected_half_life: float
    sharpe_ratio_estimate: float
    recommended_stop_loss: float
    recommended_position_size: float


class StationarityAnalyzer:
    """
    Analyzer for stationarity and mean reversion properties.

    Implements Ernest Chan's methodologies for:
    1. Augmented Dickey-Fuller (ADF) test for stationarity
    2. Calculation of half-life of mean reversion
    3. Hurst exponent calculation
    4. Optimal lookback period determination
    """

    # Default confidence level for tests
    DEFAULT_CONFIDENCE_LEVEL = 0.95

    # Default parameters for ADF test
    DEFAULT_ADF_LAG = 1
    DEFAULT_ADF_REGRESSION = "c"  # Constant only

    def __init__(
        self,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        min_observations: int = 30,
    ):
        """
        Initialize the stationarity analyzer.

        Args:
            confidence_level: Confidence level for hypothesis tests (default: 0.95)
            min_observations: Minimum number of observations required for tests
        """
        self.confidence_level = confidence_level
        self.min_observations = min_observations

    def test_stationarity(
        self,
        prices: Union[pd.Series, np.ndarray, List[float]],
        asset_name: Optional[str] = None,
        calculate_half_life: bool = True,
        calculate_hurst: bool = True,
    ) -> StationarityTestResult:
        """
        Test if a price series is stationary using the Augmented Dickey-Fuller test.

        Ernest Chan's methodology:
        - ADF test with lag-1 difference (for daily data)
        - Focus on p-value < 0.05 for stationarity
        - Calculate half-life of mean reversion
        - Use Hurst exponent to confirm (H < 0.5 indicates mean reversion)

        Args:
            prices: Price series to test
            asset_name: Optional name for logging
            calculate_half_life: Whether to calculate half-life
            calculate_hurst: Whether to calculate Hurst exponent

        Returns:
            StationarityTestResult with test statistics and interpretation

        Examples:
            >>> analyzer = StationarityAnalyzer()
            >>> prices = pd.Series([100, 101, 99, 100, 102, 98, 100])
            >>> result = analyzer.test_stationarity(prices, "AAPL")
            >>> print(f"Is stationary: {result.is_stationary}")
            >>> print(f"Half-life: {result.half_life:.2f} days")
        """
        try:
            # Convert to numpy array
            if isinstance(prices, (list, pd.Series)):
                price_array = np.array(prices, dtype=np.float64)
            else:
                price_array = prices.astype(np.float64)

            # Validate input
            if len(price_array) < self.min_observations:
                logger.warning(
                    f"Insufficient data for stationarity test: {len(price_array)} < {self.min_observations}"
                )
                return self._create_non_stationary_result(
                    adf_statistic=0.0,
                    p_value=1.0,
                    reason="Insufficient data",
                )

            # Remove NaN values
            price_array = price_array[~np.isnan(price_array)]

            if len(price_array) < self.min_observations:
                return self._create_non_stationary_result(
                    adf_statistic=0.0,
                    p_value=1.0,
                    reason="Insufficient valid data after NaN removal",
                )

            # Calculate log returns for better stationarity
            log_prices = np.log(price_array)
            np.diff(log_prices)

            # Perform ADF test on log prices
            adf_result = self._adf_test(log_prices)

            # Calculate half-life if requested
            half_life = None
            if calculate_half_life and adf_result["is_stationary"]:
                half_life = self.calculate_half_life(log_prices)

            # Calculate Hurst exponent if requested
            hurst_exponent = None
            if calculate_hurst:
                hurst_exponent = self.calculate_hurst_exponent(price_array)

            # Interpret results
            interpretation = self._interpret_stationarity_result(
                adf_result["is_stationary"],
                adf_result["p_value"],
                half_life,
                hurst_exponent,
            )

            result = StationarityTestResult(
                is_stationary=adf_result["is_stationary"],
                adf_statistic=adf_result["statistic"],
                p_value=adf_result["p_value"],
                critical_values=adf_result["critical_values"],
                confidence_level=self.confidence_level,
                half_life=half_life,
                hurst_exponent=hurst_exponent,
                interpretation=interpretation,
            )

            if asset_name:
                logger.info(
                    f"Stationarity test for {asset_name}: "
                    f"{'Stationary' if result.is_stationary else 'Non-stationary'}, "
                    f"p-value={result.p_value:.4f}, "
                    f"half-life={result.half_life:.1f} days"
                    if result.half_life
                    else "half-life=N/A"
                )

            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error in stationarity test: {e}")
            return self._create_non_stationary_result(
                adf_statistic=0.0,
                p_value=1.0,
                reason=f"Test error: {e}",
            )

    def _adf_test(self, series: np.ndarray) -> Dict[str, Any]:
        """
        Perform Augmented Dickey-Fuller test for stationarity.

        Ernest Chan uses the ADF test with:
        - Lag-1 differences (default for daily data)
        - Constant term only (no trend)
        - Focus on p-value interpretation

        Returns:
            Dictionary with test statistic, p-value, critical values, and result
        """
        try:
            # Use statsmodels with fallback for ADF test
            from app.core.statsmodels_fallback import adfuller

            adf_result = adfuller(
                series,
                maxlag=1,  # Ernest Chan: lag-1 for daily data
                regression="c",  # Constant only
                store=False,
            )

            return {
                "statistic": float(adf_result[0]),
                "p_value": float(adf_result[1]),
                "critical_values": {
                    "1%": float(adf_result[4]["1%"]),
                    "5%": float(adf_result[4]["5%"]),
                    "10%": float(adf_result[4]["10%"]),
                },
                "is_stationary": float(adf_result[1]) < (1.0 - self.confidence_level),
            }

        except ImportError:
            logger.warning("statsmodels not available, using simplified ADF test")
            return self._simplified_adf_test(series)

    def _simplified_adf_test(self, series: np.ndarray) -> Dict[str, Any]:
        """
        Simplified ADF test implementation when statsmodels is not available.

        This uses a simplified regression-based approach to estimate
        the ADF statistic.
        """
        try:
            # Calculate first differences
            y_diff = np.diff(series)
            y_lag = series[:-1]

            # Regression: y_diff = alpha + beta * y_lag + epsilon
            # Beta close to 0 indicates stationarity
            if len(y_lag) < 2 or np.std(y_lag) == 0:
                return {
                    "statistic": 0.0,
                    "p_value": 1.0,
                    "critical_values": {"1%": -3.43, "5%": -2.86, "10%": -2.57},
                    "is_stationary": False,
                }

            # Simple OLS regression
            beta = np.cov(y_lag, y_diff)[0, 1] / np.var(y_lag)

            # ADF statistic is approximately beta / std_error
            # Simplified: use beta directly (more negative = more stationary)
            adf_statistic = beta * 100  # Scale for interpretability

            # Critical values for simplified test (approximate)
            critical_values = {"1%": -3.43, "5%": -2.86, "10%": -2.57}

            # Determine stationarity based on statistic
            is_stationary = adf_statistic < critical_values["5%"]

            # Approximate p-value
            if adf_statistic < -3.5:
                p_value = 0.001
            elif adf_statistic < -3.0:
                p_value = 0.01
            elif adf_statistic < -2.5:
                p_value = 0.05
            else:
                p_value = 0.10

            return {
                "statistic": float(adf_statistic),
                "p_value": float(p_value),
                "critical_values": critical_values,
                "is_stationary": is_stationary,
            }

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Error in simplified ADF test: {e}")
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "critical_values": {"1%": -3.43, "5%": -2.86, "10%": -2.57},
                "is_stationary": False,
            }

    def calculate_half_life(
        self,
        series: Union[pd.Series, np.ndarray, List[float]],
    ) -> float:
        """
        Calculate the half-life of mean reversion.

        Ernest Chan's formula:
        half_life = -ln(2) / theta

        Where theta is the coefficient from the Ornstein-Uhlenbeck process:
        dy = theta * (mu - y) * dt + sigma * dW

        Shorter half-life = faster mean reversion = better for mean reversion strategies

        Args:
            series: Price series (preferably log prices)

        Returns:
            Half-life in time periods (days for daily data)
        """
        try:
            # Convert to numpy array
            if isinstance(series, (list, pd.Series)):
                y = np.array(series, dtype=np.float64)
            else:
                y = series.astype(np.float64)

            # Remove NaN
            y = y[~np.isnan(y)]

            # Calculate lagged values and differences
            y_lag = y[:-1]
            y_diff = np.diff(y)

            if len(y_lag) < 10:
                return float("inf")

            # Calculate mean
            np.mean(y)

            # Regression: dy = theta * (mu - y) + epsilon
            # dy = theta * mu - theta * y + epsilon
            # dy = -theta * y + theta * mu + epsilon

            # Reshape for regression
            X = y_lag.reshape(-1, 1)
            Y = y_diff

            # Add constant
            X_with_const = np.column_stack([np.ones(len(X)), X])

            # OLS regression
            try:
                coeffs = np.linalg.lstsq(X_with_const, Y, rcond=None)[0]
                theta = -coeffs[1]  # Slope coefficient
            except np.linalg.LinAlgError:
                return float("inf")

            # Calculate half-life
            if theta <= 0:
                return float("inf")  # No mean reversion

            half_life = -np.log(2) / theta

            return float(max(0, half_life))

        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.error(f"Error calculating half-life: {e}")
            return float("inf")

    def calculate_hurst_exponent(
        self,
        series: Union[pd.Series, np.ndarray, List[float]],
        max_lag: int = 20,
    ) -> float:
        """
        Calculate the Hurst exponent to determine trend vs. mean reversion.

        Ernest Chan's interpretation:
        - H < 0.5: Mean reverting (stationary)
        - H = 0.5: Random walk
        - H > 0.5: Trending

        Uses R/S analysis (Rescaled Range analysis)

        Args:
            series: Price series
            max_lag: Maximum lag to consider

        Returns:
            Hurst exponent (0-1)
        """
        try:
            # Convert to numpy array
            if isinstance(series, (list, pd.Series)):
                y = np.array(series, dtype=np.float64)
            else:
                y = series.astype(np.float64)

            # Remove NaN
            y = y[~np.isnan(y)]

            if len(y) < 50:
                return 0.5  # Default to random walk for short series

            # Calculate cumulative deviations
            mean_y = np.mean(y)
            y_dev = y - mean_y
            np.cumsum(y_dev)

            # Calculate range for different lags
            lags = range(5, min(max_lag, len(y) // 2))
            R_S = []

            for lag in lags:
                # Split into sub-series
                n = len(y) // lag

                if n < 2:
                    continue

                ranges = []
                stds = []

                for i in range(n):
                    sub_y = y[i * lag : (i + 1) * lag]
                    if len(sub_y) < 2:
                        continue

                    # Range
                    sub_mean = np.mean(sub_y)
                    sub_dev = sub_y - sub_mean
                    sub_z = np.cumsum(sub_dev)
                    R = np.max(sub_z) - np.min(sub_z)

                    # Standard deviation
                    S = np.std(sub_y)

                    if S > 0:
                        ranges.append(R)
                        stds.append(S)

                if ranges and stds:
                    R_S.append(np.mean(ranges) / np.mean(stds))

            if not R_S:
                return 0.5

            # Regress log(R/S) on log(lag)
            log_lags = np.log(list(lags[: len(R_S)]))
            log_RS = np.log(R_S)

            # Simple linear regression
            coeffs = np.polyfit(log_lags, log_RS, 1)
            hurst = coeffs[0]

            return float(hurst)

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating Hurst exponent: {e}")
            return 0.5

    def find_optimal_lookback(
        self,
        prices: Union[pd.Series, np.ndarray, List[float]],
        max_lookback: int = 100,
        min_lookback: int = 5,
    ) -> int:
        """
        Find the optimal lookback period for mean reversion strategy.

        Ernest Chan's methodology:
        - Test different lookback periods
        - Find period with fastest mean reversion (lowest half-life)
        - Balance between signal strength and responsiveness

        Args:
            prices: Price series
            max_lookback: Maximum lookback to test
            min_lookback: Minimum lookback to test

        Returns:
            Optimal lookback period
        """
        try:
            if isinstance(prices, (list, pd.Series)):
                price_array = np.array(prices, dtype=np.float64)
            else:
                price_array = prices.astype(np.float64)

            price_array = price_array[~np.isnan(price_array)]

            if len(price_array) < max_lookback * 2:
                max_lookback = len(price_array) // 2

            best_lookback = min_lookback
            best_half_life = float("inf")

            for lookback in range(min_lookback, max_lookback + 1, 5):
                if lookback >= len(price_array):
                    break

                # Test half-life with this lookback
                window = price_array[-lookback:]
                half_life = self.calculate_half_life(window)

                # Penalize very short lookbacks (noise) and very long (slow)
                penalty = abs(lookback - 20) / 100  # Prefer around 20 days

                adjusted_half_life = half_life * (1 + penalty)

                if adjusted_half_life < best_half_life:
                    best_half_life = adjusted_half_life
                    best_lookback = lookback

            return best_lookback

        except (ValueError, TypeError) as e:
            logger.error(f"Error finding optimal lookback: {e}")
            return 20  # Default

    def _interpret_stationarity_result(
        self,
        is_stationary: bool,
        p_value: float,
        half_life: Optional[float],
        hurst_exponent: Optional[float],
    ) -> str:
        """Interpret stationarity test results."""
        parts = []

        if is_stationary:
            parts.append(f"Series is stationary (p={p_value:.4f})")

            if half_life is not None:
                if half_life < 10:
                    parts.append(f"Fast mean reversion (half-life: {half_life:.1f} periods)")
                elif half_life < 50:
                    parts.append(f"Moderate mean reversion (half-life: {half_life:.1f} periods)")
                else:
                    parts.append(f"Slow mean reversion (half-life: {half_life:.1f} periods)")

            if hurst_exponent is not None:
                if hurst_exponent < 0.4:
                    parts.append(f"Strong mean reversion (Hurst: {hurst_exponent:.3f})")
                elif hurst_exponent < 0.5:
                    parts.append(f"Moderate mean reversion (Hurst: {hurst_exponent:.3f})")
                elif hurst_exponent < 0.6:
                    parts.append(f"Random walk behavior (Hurst: {hurst_exponent:.3f})")
                else:
                    parts.append(f"Trending behavior (Hurst: {hurst_exponent:.3f})")
        else:
            parts.append(f"Series is non-stationary (p={p_value:.4f})")

        return ". ".join(parts)

    def _create_non_stationary_result(
        self,
        adf_statistic: float,
        p_value: float,
        reason: str,
    ) -> StationarityTestResult:
        """Create a non-stationary result with explanation."""
        return StationarityTestResult(
            is_stationary=False,
            adf_statistic=adf_statistic,
            p_value=p_value,
            critical_values={"1%": -3.43, "5%": -2.86, "10%": -2.57},
            confidence_level=self.confidence_level,
            interpretation=f"Non-stationary: {reason}",
        )


class CointegrationAnalyzer:
    """
    Analyzer for cointegration between multiple price series.

    Implements Ernest Chan's methodologies for pair trading:
    1. Engle-Granger cointegration test
    2. Hedge ratio calculation via OLS regression
    3. Spread half-life calculation
    4. Optimal entry/exit thresholds
    """

    def __init__(
        self,
        confidence_level: float = 0.95,
        min_observations: int = 30,
    ):
        """
        Initialize the cointegration analyzer.

        Args:
            confidence_level: Confidence level for tests
            min_observations: Minimum observations required
        """
        self.confidence_level = confidence_level
        self.min_observations = min_observations
        self.stationarity_analyzer = StationarityAnalyzer(
            confidence_level=confidence_level,
            min_observations=min_observations,
        )

    def test_cointegration(
        self,
        y1: Union[pd.Series, np.ndarray, List[float]],
        y2: Union[pd.Series, np.ndarray, List[float]],
        asset1_name: str = "Asset1",
        asset2_name: str = "Asset2",
    ) -> CointegrationTestResult:
        """
        Test if two price series are cointegrated using Engle-Granger test.

        Ernest Chan's methodology:
        1. Calculate hedge ratio via OLS: y2 = alpha + beta * y1
        2. Calculate spread: spread = y2 - beta * y1
        3. Test spread for stationarity using ADF
        4. Calculate half-life of mean reversion

        Args:
            y1: First price series (independent variable)
            y2: Second price series (dependent variable)
            asset1_name: Name of first asset
            asset2_name: Name of second asset

        Returns:
            CointegrationTestResult with test statistics and parameters

        Examples:
            >>> analyzer = CointegrationAnalyzer()
            >>> result = analyzer.test_cointegration(prices_A, prices_B, "AAPL", "MSFT")
            >>> if result.is_cointegrated:
            >>>     print(f"Hedge ratio: {result.hedge_ratio:.4f}")
            >>>     print(f"Spread half-life: {result.spread_half_life:.1f} days")
        """
        try:
            # Convert to numpy arrays
            if isinstance(y1, (list, pd.Series)):
                y1_array = np.array(y1, dtype=np.float64)
            else:
                y1_array = y1.astype(np.float64)

            if isinstance(y2, (list, pd.Series)):
                y2_array = np.array(y2, dtype=np.float64)
            else:
                y2_array = y2.astype(np.float64)

            # Remove NaN
            valid_mask = ~(np.isnan(y1_array) | np.isnan(y2_array))
            y1_array = y1_array[valid_mask]
            y2_array = y2_array[valid_mask]

            # Validate length
            min_len = min(len(y1_array), len(y2_array))
            if min_len < self.min_observations:
                logger.warning(
                    f"Insufficient data for cointegration test: {min_len} < {self.min_observations}"
                )
                return self._create_non_cointegrated_result(
                    hedge_ratio=1.0,
                    spread_half_life=float("inf"),
                    reason="Insufficient data",
                )

            y1_array = y1_array[:min_len]
            y2_array = y2_array[:min_len]

            # Step 1: Calculate hedge ratio via OLS
            hedge_ratio, intercept = self._calculate_hedge_ratio(y1_array, y2_array)

            # Step 2: Calculate spread
            spread = y2_array - intercept - hedge_ratio * y1_array

            # Step 3: Test spread for stationarity
            spread_result = self.stationarity_analyzer.test_stationarity(
                spread,
                calculate_half_life=True,
                calculate_hurst=False,
            )

            # Step 4: Interpret results
            is_cointegrated = spread_result.is_stationary

            # Determine mean reversion speed
            if spread_result.half_life is not None:
                if spread_result.half_life < 5:
                    speed = "Very fast"
                elif spread_result.half_life < 15:
                    speed = "Fast"
                elif spread_result.half_life < 30:
                    speed = "Moderate"
                elif spread_result.half_life < 60:
                    speed = "Slow"
                else:
                    speed = "Very slow"
            else:
                speed = "Unknown"

            interpretation = self._interpret_cointegration_result(
                is_cointegrated,
                spread_result.p_value,
                hedge_ratio,
                spread_result.half_life,
                asset1_name,
                asset2_name,
            )

            result = CointegrationTestResult(
                is_cointegrated=is_cointegrated,
                test_statistic=spread_result.adf_statistic,
                p_value=spread_result.p_value,
                critical_values=spread_result.critical_values,
                hedge_ratio=float(hedge_ratio),
                spread_half_life=spread_result.half_life or float("inf"),
                confidence_level=self.confidence_level,
                interpretation=interpretation,
                mean_reversion_speed=speed,
            )

            logger.info(
                f"Cointegration test {asset1_name}-{asset2_name}: "
                f"{'Cointegrated' if is_cointegrated else 'Not cointegrated'}, "
                f"hedge_ratio={result.hedge_ratio:.4f}, "
                f"half_life={result.spread_half_life:.1f}"
            )

            return result

        except (ValueError, TypeError) as e:
            logger.error(f"Error in cointegration test: {e}")
            return self._create_non_cointegrated_result(
                hedge_ratio=1.0,
                spread_half_life=float("inf"),
                reason=f"Test error: {e}",
            )

    def _calculate_hedge_ratio(
        self,
        y1: np.ndarray,
        y2: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Calculate hedge ratio using OLS regression.

        Ernest Chan: y2 = alpha + beta * y1
        Beta is the hedge ratio (how much of y2 per unit of y1)
        """
        try:
            # OLS regression: y2 = alpha + beta * y1
            X = np.column_stack([np.ones(len(y1)), y1])
            y = y2

            coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)

            intercept = float(coeffs[0])
            hedge_ratio = float(coeffs[1])

            return hedge_ratio, intercept

        except np.linalg.LinAlgError:
            logger.warning("OLS regression failed, using simple ratio")
            # Fallback: use simple ratio
            ratio = np.mean(y2) / np.mean(y1) if np.mean(y1) != 0 else 1.0
            return float(ratio), 0.0

    def calculate_optimal_position_sizes(
        self,
        cointegration_result: CointegrationTestResult,
        price1: float,
        price2: float,
        capital: float,
        risk_per_trade: float = 0.02,
    ) -> Tuple[float, float]:
        """
        Calculate optimal position sizes for a pairs trade.

        Ernest Chan's formula:
        - Size based on hedge ratio and capital allocation
        - Risk adjustment based on spread volatility

        Args:
            cointegration_result: Cointegration test results
            price1: Current price of asset 1
            price2: Current price of asset 2
            capital: Total capital available
            risk_per_trade: Fraction of capital to risk (default: 2%)

        Returns:
            Tuple of (position_size_1, position_size_2) in dollar terms
        """
        try:
            hedge_ratio = cointegration_result.hedge_ratio

            # Base position size
            base_size = capital * risk_per_trade

            # Adjust for hedge ratio
            # If hedge_ratio > 1, need more of asset 2 per unit of asset 1
            size1 = base_size
            size2 = base_size * hedge_ratio

            # Adjust for prices to get shares
            # (in practice, you'd round to whole shares)
            shares1 = size1 / price1 if price1 > 0 else 0
            shares2 = size2 / price2 if price2 > 0 else 0

            # Convert back to dollar amounts
            dollar_size1 = shares1 * price1
            dollar_size2 = shares2 * price2

            return float(dollar_size1), float(dollar_size2)

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculating position sizes: {e}")
            return 0.0, 0.0

    def calculate_entry_exit_thresholds(
        self,
        spread: np.ndarray,
        confidence_multiplier: float = 2.0,
    ) -> Tuple[float, float]:
        """
        Calculate optimal entry and exit thresholds for pairs trading.

        Ernest Chan's methodology:
        - Entry: when spread deviates by >2 standard deviations
        - Exit: when spread returns to mean (or within 1 std dev)

        Args:
            spread: Spread series
            confidence_multiplier: Multiplier for entry threshold (default: 2.0)

        Returns:
            Tuple of (entry_threshold, exit_threshold)
        """
        try:
            spread = spread[~np.isnan(spread)]

            if len(spread) < 10:
                return 2.0, 0.5  # Default thresholds

            np.mean(spread)
            spread_std = np.std(spread)

            entry_threshold = confidence_multiplier * spread_std
            exit_threshold = 0.5 * spread_std

            return float(entry_threshold), float(exit_threshold)

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating thresholds: {e}")
            return 2.0, 0.5

    def _interpret_cointegration_result(
        self,
        is_cointegrated: bool,
        p_value: float,
        hedge_ratio: float,
        half_life: float,
        asset1_name: str,
        asset2_name: str,
    ) -> str:
        """Interpret cointegration test results."""
        parts = []

        if is_cointegrated:
            parts.append(f"{asset1_name} and {asset2_name} are cointegrated (p={p_value:.4f})")
            parts.append(
                f"Hedge ratio: {hedge_ratio:.4f} (long 1 unit of {asset1_name}, short {hedge_ratio:.4f} units of {asset2_name})"
            )

            if half_life < float("inf"):
                parts.append(f"Spread mean reverts with half-life of {half_life:.1f} periods")
        else:
            parts.append(f"{asset1_name} and {asset2_name} are not cointegrated (p={p_value:.4f})")
            parts.append("Not suitable for pairs trading")

        return ". ".join(parts)

    def _create_non_cointegrated_result(
        self,
        hedge_ratio: float,
        spread_half_life: float,
        reason: str,
    ) -> CointegrationTestResult:
        """Create a non-cointegrated result with explanation."""
        return CointegrationTestResult(
            is_cointegrated=False,
            test_statistic=0.0,
            p_value=1.0,
            critical_values={"1%": -3.43, "5%": -2.86, "10%": -2.57},
            hedge_ratio=hedge_ratio,
            spread_half_life=spread_half_life,
            confidence_level=self.confidence_level,
            interpretation=f"Not cointegrated: {reason}",
            mean_reversion_speed="Unknown",
        )


def find_cointegrated_pairs(
    price_data: Dict[str, Union[pd.Series, np.ndarray, List[float]]],
    confidence_level: float = 0.95,
    min_half_life: float = 30.0,
    max_half_life: float = 100.0,
) -> List[Tuple[str, str, CointegrationTestResult]]:
    """
    Find cointegrated pairs from a universe of assets.

    Implements Ernest Chan's methodology for pair selection:
    1. Test all possible pairs for cointegration
    2. Filter by half-life (not too fast, not too slow)
    3. Rank by cointegration strength

    Args:
        price_data: Dictionary mapping asset names to price series
        confidence_level: Confidence level for tests
        min_half_life: Minimum half-life for filtering
        max_half_life: Maximum half-life for filtering

    Returns:
        List of (asset1, asset2, cointegration_result) tuples

    Examples:
        >>> prices = {
        >>>     "AAPL": [...],
        >>>     "MSFT": [...],
        >>>     "GOOGL": [...],
        >>> }
        >>> pairs = find_cointegrated_pairs(prices)
        >>> for asset1, asset2, result in pairs:
        >>>     print(f"{asset1}-{asset2}: half-life={result.spread_half_life:.1f}")
    """
    analyzer = CointegrationAnalyzer(confidence_level=confidence_level)
    cointegrated_pairs = []

    assets = list(price_data.keys())

    for i, asset1 in enumerate(assets):
        for asset2 in assets[i + 1 :]:
            try:
                result = analyzer.test_cointegration(
                    price_data[asset1],
                    price_data[asset2],
                    asset1,
                    asset2,
                )

                # Filter by cointegration and half-life
                if (
                    result.is_cointegrated
                    and min_half_life <= result.spread_half_life <= max_half_life
                ):
                    cointegrated_pairs.append((asset1, asset2, result))

            except Exception as e:
                logger.warning(f"Error testing pair {asset1}-{asset2}: {e}")
                continue

    # Sort by half-life (shorter = faster mean reversion)
    cointegrated_pairs.sort(key=lambda x: x[2].spread_half_life)

    return cointegrated_pairs
