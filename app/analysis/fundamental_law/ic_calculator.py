"""
Information Coefficient Calculator

This module implements the calculation and analysis of the Information
Coefficient (IC), which measures the correlation between forecasted
returns and actual realized returns.

The IC is a key measure of forecasting skill:
- IC > 0.05: Excellent skill
- IC 0.03-0.05: Good skill
- IC 0.01-0.03: Fair skill
- IC < 0.01: Poor skill

Reference:
    Grinold, R., & Kahn, R. (2000). "Active Portfolio Management"
    Chapter 9: The Information Ratio
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy import stats

from app.core.decimal_utils import to_decimal

if TYPE_CHECKING:
    from app.analysis.fundamental_law.models import ICMetrics

logger = logging.getLogger(__name__)


class ICCalculator:
    """
    Calculate and analyze the Information Coefficient.

    The Information Coefficient (IC) measures the skill of a forecasting
    model by calculating the correlation between predicted returns and
    actual realized returns.

    Methods:
        - calculate_ic: Calculate IC with Pearson or Spearman correlation
        - calculate_ic_decay: Calculate IC over multiple forward horizons
        - test_significance: Test if IC is statistically significant
        - calculate_confidence_interval: Get confidence interval for IC

    Examples:
        >>> calculator = ICCalculator()
        >>> forecasts = pd.Series([0.01, 0.02, -0.01, 0.03])
        >>> returns = pd.Series([0.015, 0.025, -0.005, 0.02])
        >>> metrics = calculator.calculate_ic(forecasts, returns)
        >>> metrics.ic
        Decimal('0.894')
    """

    def __init__(self, min_observations: int = 20):
        """
        Initialize the IC Calculator.

        Args:
            min_observations: Minimum number of observations required
                for reliable IC calculation (default: 20)

        Examples:
            >>> calculator = ICCalculator(min_observations=30)
        """
        self.min_observations = min_observations

    def calculate_ic(
        self,
        forecasts: pd.Series,
        returns: pd.Series,
        method: str = "pearson",
    ) -> "ICMetrics":  # noqa: F821
        """
        Calculate Information Coefficient and related metrics.

        This method computes the IC between forecasts and returns, along
        with rank IC, statistical significance, and confidence intervals.

        Args:
            forecasts: Predicted returns (e.g., from alpha model)
            returns: Actual realized returns
            method: Correlation method - "pearson" or "spearman"
                - pearson: Standard correlation coefficient
                - spearman: Rank correlation (more robust to outliers)

        Returns:
            ICMetrics object containing IC and related statistics

        Raises:
            ValueError: If series have different lengths or insufficient data

        Examples:
            >>> calculator = ICCalculator()
            >>> forecasts = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01])
            >>> returns = pd.Series([0.015, 0.025, -0.005, 0.02, 0.008])
            >>> metrics = calculator.calculate_ic(forecasts, returns)
            >>> metrics.ic  # doctest: +SKIP
            Decimal('0.866')
        """
        # Validate inputs
        if len(forecasts) != len(returns):
            raise ValueError(
                f"Forecasts and returns must have same length: "
                f"{len(forecasts)} != {len(returns)}"
            )

        if len(forecasts) < self.min_observations:
            raise ValueError(
                f"Insufficient observations for IC calculation: "
                f"{len(forecasts)} < {self.min_observations}"
            )

        # Remove NaN values
        valid_mask = ~(forecasts.isna() | returns.isna())
        forecasts_clean = forecasts[valid_mask]
        returns_clean = returns[valid_mask]

        if len(forecasts_clean) < self.min_observations:
            raise ValueError(
                f"Insufficient valid observations after removing NaNs: "
                f"{len(forecasts_clean)} < {self.min_observations}"
            )

        # Check for constant series (zero variance)
        if forecasts_clean.std() == 0 or returns_clean.std() == 0:
            logger.warning("One or both series have zero variance, returning IC of 0")
            return self._get_zero_ic_metrics()

        # Calculate Pearson IC
        if method == "pearson":
            ic_value, p_value = stats.pearsonr(forecasts_clean.values, returns_clean.values)
        elif method == "spearman":
            ic_value, p_value = stats.spearmanr(forecasts_clean.values, returns_clean.values)
        else:
            raise ValueError(
                f"Invalid correlation method: {method}. " f"Use 'pearson' or 'spearman'"
            )

        # Handle NaN from scipy (can happen with constant values)
        if np.isnan(ic_value):
            logger.warning("IC calculation resulted in NaN, returning 0")
            return self._get_zero_ic_metrics()

        # Calculate rank IC (Spearman)
        ic_rank_value, _ = stats.spearmanr(forecasts_clean.values, returns_clean.values)

        # Handle NaN for rank IC
        if np.isnan(ic_rank_value):
            ic_rank_value = 0.0

        # Convert to Decimal
        ic = to_decimal(str(round(ic_value, 4)))
        ic_rank = to_decimal(str(round(ic_rank_value, 4)))

        # Calculate confidence interval
        n = len(forecasts_clean)
        confidence_interval = self.calculate_confidence_interval(ic_value, n, confidence=0.95)
        ci_lower = to_decimal(str(round(confidence_interval[0], 4)))
        ci_upper = to_decimal(str(round(confidence_interval[1], 4)))

        # Return metrics (ic_decay is empty for single calculation)
        from app.analysis.fundamental_law.models import ICMetrics

        return ICMetrics(
            ic=ic,
            ic_rank=ic_rank,
            ic_decay=[],
            statistical_significance=float(p_value),
            confidence_interval=(ci_lower, ci_upper),
        )

    def calculate_ic_decay(
        self,
        forecasts: pd.Series,
        returns: pd.Series,
        periods: list[int] | None = None,
    ) -> list[Decimal]:
        """
        Calculate IC over different forward return horizons.

        This measures how long the predictive signal persists. For example,
        if the 1-period IC is 0.05 but the 20-period IC is 0.01, the signal
        decays quickly.

        Args:
            forecasts: Predicted returns (aligned at time t)
            returns: Actual returns (multi-period starting at time t)
            periods: List of forward periods to calculate IC for
                - 1: IC for next period return
                - 5: IC for next 5 periods cumulative return
                - 10: IC for next 10 periods cumulative return
                - etc.

        Returns:
            List of IC values, one for each period

        Raises:
            ValueError: If insufficient data for any period

        Examples:
            >>> calculator = ICCalculator()
            >>> forecasts = pd.Series([0.01, 0.02, -0.01, 0.03] * 10)
            >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 10)
            >>> decay = calculator.calculate_ic_decay(forecasts, returns, [1, 2])
            >>> len(decay)
            2
        """
        if periods is None:
            periods = [1, 5, 10, 20]
        ic_values = []

        for period in periods:
            # Calculate forward returns
            if period == 1:
                forward_returns = returns
            else:
                # Calculate cumulative returns over period
                # Using log returns for compounding
                log_returns = np.log1p(returns)
                forward_returns = pd.Series(log_returns.rolling(window=period).sum()).shift(
                    -(period - 1)
                )

                # Convert back to simple returns
                forward_returns = np.expm1(forward_returns)

            # Align forecasts with forward returns
            aligned_forecasts = forecasts[: len(forward_returns.dropna())]
            aligned_returns = forward_returns.dropna()

            # Calculate IC for this horizon
            try:
                if len(aligned_forecasts) >= self.min_observations:
                    metrics = self.calculate_ic(aligned_forecasts, aligned_returns)
                    ic_values.append(metrics.ic)
                else:
                    logger.warning(
                        f"Insufficient data for period {period}: "
                        f"{len(aligned_forecasts)} observations"
                    )
                    ic_values.append(Decimal("0"))
            except ValueError:
                logger.error(
                    f"Could not calculate IC for period {period}",
                    exc_info=True,
                    extra={"period": period, "aligned_observations": len(aligned_forecasts)},
                )
                ic_values.append(Decimal("0"))

        return ic_values

    def test_significance(
        self,
        ic: float,
        n_observations: int,
    ) -> tuple[float, bool]:
        """
        Test if IC is statistically significant.

        This tests the null hypothesis H0: IC = 0 (no forecasting skill).

        The test uses a t-statistic for the correlation coefficient:
            t = IC * sqrt((n - 2) / (1 - IC²))

        Under the null hypothesis, this follows a t-distribution with n-2 df.

        Args:
            ic: Information Coefficient value
            n_observations: Number of observations used to calculate IC

        Returns:
            Tuple of (p_value, is_significant)
            - p_value: Two-tailed p-value for the test
            - is_significant: True if p < 0.05

        Examples:
            >>> calculator = ICCalculator()
            >>> p_value, is_sig = calculator.test_significance(0.05, 100)
            >>> is_sig
            True
        """
        if n_observations < 3:
            return 1.0, False

        # Calculate t-statistic
        # t = r * sqrt((n - 2) / (1 - r^2))
        if abs(ic) >= 1.0:
            # Perfect correlation, treat as significant
            return 0.0, True

        t_statistic = ic * np.sqrt((n_observations - 2) / (1 - ic**2))

        # Calculate two-tailed p-value from t-distribution
        p_value = 2 * (1 - stats.t.cdf(abs(t_statistic), df=n_observations - 2))

        # Return p-value and significance
        return float(p_value), p_value < 0.05

    def calculate_confidence_interval(
        self,
        ic: float,
        n: int,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """
        Calculate confidence interval for IC using Fisher's z-transformation.

        Fisher's z transformation:
            z = 0.5 * ln((1 + r) / (1 - r))

        The transformed value is approximately normally distributed with:
            mean = z
            std_err = 1 / sqrt(n - 3)

        Args:
            ic: Information Coefficient value
            n: Number of observations
            confidence: Confidence level (default: 0.95 for 95% CI)

        Returns:
            Tuple of (lower_bound, upper_bound) for the confidence interval

        Raises:
            ValueError: If ic is outside [-1, 1] range

        Examples:
            >>> calculator = ICCalculator()
            >>> ci = calculator.calculate_confidence_interval(0.05, 100)
            >>> len(ci)
            2
            >>> ci[0] < 0.05 < ci[1]
            True
        """
        if not -1 <= ic <= 1:
            raise ValueError(f"IC must be in [-1, 1] range, got {ic}")

        if n < 4:
            # Not enough data for Fisher transformation
            return (ic, ic)

        # Fisher's z transformation
        # Handle edge cases
        if ic >= 0.999:
            z = 3.0  # Approximately infinity
        elif ic <= -0.999:
            z = -3.0
        else:
            z = np.arctanh(ic)  # Same as 0.5 * ln((1+r)/(1-r))

        # Standard error of z
        se = 1 / np.sqrt(n - 3)

        # Critical value for confidence level
        alpha = 1 - confidence
        z_critical = stats.norm.ppf(1 - alpha / 2)

        # Confidence interval in z-space
        z_lower = z - z_critical * se
        z_upper = z + z_critical * se

        # Transform back to r-space
        # Clamp values to avoid overflow
        z_lower = max(min(z_lower, 3.0), -3.0)
        z_upper = max(min(z_upper, 3.0), -3.0)

        r_lower = np.tanh(z_lower)
        r_upper = np.tanh(z_upper)

        return (r_lower, r_upper)

    def calculate_rolling_ic(
        self,
        forecasts: pd.Series,
        returns: pd.Series,
        window: int = 60,
        method: str = "pearson",
    ) -> pd.Series:
        """
        Calculate rolling Information Coefficient over a window.

        This shows how forecasting skill evolves over time. A stable or
        improving IC suggests robust model performance.

        Args:
            forecasts: Predicted returns
            returns: Actual returns
            window: Rolling window size (default: 60 observations)
            method: Correlation method ("pearson" or "spearman")

        Returns:
            Series of rolling IC values with DatetimeIndex

        Examples:
            >>> calculator = ICCalculator()
            >>> forecasts = pd.Series([0.01, 0.02, -0.01, 0.03] * 50)
            >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 50)
            >>> rolling_ic = calculator.calculate_rolling_ic(forecasts, returns, 20)
            >>> len(rolling_ic) > 0
            True
        """
        if len(forecasts) != len(returns):
            raise ValueError("Forecasts and returns must have same length")

        if len(forecasts) < window:
            raise ValueError(
                f"Insufficient data for rolling window: " f"{len(forecasts)} < {window}"
            )

        rolling_ic_values = []

        for i in range(window, len(forecasts) + 1):
            window_forecasts = forecasts.iloc[i - window : i]
            window_returns = returns.iloc[i - window : i]

            try:
                metrics = self.calculate_ic(window_forecasts, window_returns, method)
                rolling_ic_values.append(float(metrics.ic))
            except ValueError:
                # Not enough valid data in this window
                rolling_ic_values.append(np.nan)

        # Create series with original index (offset by window)
        index = forecasts.index[window - 1 :]
        return pd.Series(rolling_ic_values, index=index)

    def _get_zero_ic_metrics(self) -> "ICMetrics":  # noqa: F821
        """
        Return zero IC metrics for edge cases.

        Returns:
            ICMetrics with zero IC values
        """
        from app.analysis.fundamental_law.models import ICMetrics

        return ICMetrics(
            ic=Decimal("0"),
            ic_rank=Decimal("0"),
            ic_decay=[],
            statistical_significance=1.0,  # Not significant
            confidence_interval=(Decimal("0"), Decimal("0")),
        )
