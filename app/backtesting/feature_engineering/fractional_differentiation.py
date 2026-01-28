"""
Fractional Differentiation (Fixed Window) Implementation.

Based on López de Prado, "Advances in Financial Machine Learning", Chapter 3, Section 3.4.

This module implements fractional differentiation to achieve stationarity while preserving
memory in financial time series - a critical feature for machine learning applications.

Key Concepts:
- Integer differentiation (d=1) creates stationarity but destroys all memory
- Fractional differentiation (0<d<1) achieves stationarity with minimal memory loss
- Fixed window method expands the window until stationarity is achieved

Author: Advanced Financial Machine Learning Implementation
"""

from typing import Tuple, Optional, Union, List, Dict
from functools import lru_cache
import warnings

import numpy as np
import pandas as pd
from scipy import stats

# Optional import for statsmodels
try:
    from statsmodels.tsa.stattools import adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    adfuller = None

warnings.filterwarnings('ignore')


class FractionalDifferentiation:
    """
    Fractional Differentiation for Stationary Features with Memory Preservation.

    This class implements the fixed-window fractional differentiation method from
    López de Prado, which allows us to find the minimum differentiation order d
    that achieves stationarity while preserving maximum memory.

    Example:
        >>> fd = FractionalDifferentiation()
        >>> series = pd.Series(np.random.randn(1000).cumsum())
        >>> optimal_d, p_value = fd.find_optimal_d(series)
        >>> frac_diff_series = fd.fractional_diff(series, d=optimal_d)
    """

    def __init__(
        self,
        threshold: float = 1e-3,
        adfuller_alpha: float = 0.05,
        max_lookback: int = None
    ):
        """
        Initialize FractionalDifferentiation.

        Args:
            threshold: Weight cutoff threshold for expanding window (default: 1e-3)
                       Note: 1e-3 is practical for typical financial series (1000-5000 points)
                       Use 1e-5 for longer series (>10000 points)
            adfuller_alpha: Significance level for ADF test (default: 0.05)
            max_lookback: Maximum window size (None = use threshold)
        """
        self.threshold = threshold
        self.adfuller_alpha = adfuller_alpha
        self.max_lookback = max_lookback
        self._weights_cache: Dict[float, np.ndarray] = {}

        if not STATSMODELS_AVAILABLE:
            import warnings
            warnings.warn(
                "statsmodels not available. Stationarity tests will be disabled. "
                "Install with: pip install statsmodels"
            )

    def get_weights(self, d: float, threshold: float = None) -> np.ndarray:
        """
        Calculate weights for fractional differentiation.

        Uses the expanding window method from López de Prado (Section 3.4).
        The weights are calculated using the binomial expansion:
        w_k = -w_{k-1} * ((d - k + 1) / k)

        Args:
            d: Differentiation order (0 < d < 1)
            threshold: Weight cutoff threshold (default: self.threshold)

        Returns:
            Array of weights for fractional differentiation

        Example:
            >>> fd = FractionalDifferentiation()
            >>> weights = fd.get_weights(d=0.5, threshold=1e-5)
            >>> print(f"Calculated {len(weights)} weights")
        """
        if threshold is None:
            threshold = self.threshold

        # Check cache
        cache_key = (d, threshold)
        if cache_key in self._weights_cache:
            return self._weights_cache[cache_key]

        # Calculate weights using binomial expansion
        weights = [1.0]  # First weight is always 1

        k = 1
        while True:
            # Calculate weight using recursive formula
            w_k = -weights[-1] * ((d - k + 1) / k)
            weights.append(w_k)

            # Check if we've reached the threshold
            if abs(w_k) < threshold:
                break

            k += 1

            # Safety limit
            if k > 10000:
                warnings.warn(
                    f"Weight calculation reached 10000 iterations for d={d}, "
                    f"threshold={threshold}. Consider increasing threshold."
                )
                break

        weights_array = np.array(weights)
        self._weights_cache[cache_key] = weights_array

        return weights_array

    def fractional_diff(
        self,
        series: Union[pd.Series, np.ndarray],
        d: float,
        threshold: float = None
    ) -> pd.Series:
        """
        Apply fractional differentiation to a series.

        This implements the fixed-window fractional differentiation from López de Prado.
        The window expands until the weights fall below the threshold.

        Args:
            series: Time series to differentiate (Series or 1D array)
            d: Differentiation order (0 < d < 1)
            threshold: Weight cutoff threshold (default: self.threshold)

        Returns:
            Fractionally differentiated series with same index as input

        Example:
            >>> fd = FractionalDifferentiation()
            >>> series = pd.Series([1, 2, 3, 4, 5])
            >>> frac_diff = fd.fractional_diff(series, d=0.5)
            >>> print(frac_diff)
        """
        if threshold is None:
            threshold = self.threshold

        # Convert to pandas Series if needed
        if isinstance(series, np.ndarray):
            series = pd.Series(series)
        elif not isinstance(series, pd.Series):
            raise TypeError("series must be pd.Series or np.ndarray")

        # Get weights
        weights = self.get_weights(d, threshold)

        # Apply fixed window fractional differentiation
        # Use expanding window until we have enough data points
        result = np.full(len(series), np.nan)

        for i in range(len(weights), len(series)):
            # Apply weighted sum of past values
            window = series.iloc[i - len(weights) + 1:i + 1].values
            result[i] = np.dot(weights, window)

        # Return as Series with same index
        return pd.Series(result, index=series.index)

    def fractional_diff_ffd(
        self,
        series: Union[pd.Series, np.ndarray],
        d: float,
        threshold: float = None
    ) -> pd.Series:
        """
        Apply Fractionally Fitted Differentiation (FFD).

        This is an alternative implementation that uses a fixed-width window
        and filters out small weights. More efficient for large datasets.

        Args:
            series: Time series to differentiate
            d: Differentiation order (0 < d < 1)
            threshold: Weight cutoff threshold

        Returns:
            Fractionally differentiated series
        """
        if threshold is None:
            threshold = self.threshold

        if isinstance(series, np.ndarray):
            series = pd.Series(series)

        # Calculate weights
        weights = self.get_weights(d, threshold)

        # Filter weights by threshold
        weights_filtered = weights[np.abs(weights) >= threshold]

        # Apply convolution with filtered weights
        result = np.full(len(series), np.nan)

        for i in range(len(weights_filtered), len(series)):
            window = series.iloc[i - len(weights_filtered) + 1:i + 1].values
            result[i] = np.dot(weights_filtered, window)

        return pd.Series(result, index=series.index)

    def find_optimal_d(
        self,
        series: Union[pd.Series, np.ndarray],
        min_d: float = 0.0,
        max_d: float = 1.0,
        step: float = 0.05,
        adfuller_alpha: float = None,
        method: str = 'binary'
    ) -> Tuple[float, float, Dict]:
        """
        Find minimum d that achieves stationarity.

        This function searches for the minimum differentiation order that makes
        the series stationary according to the Augmented Dickey-Fuller test.

        Args:
            series: Time series to analyze
            min_d: Minimum d value to test (default: 0.0)
            max_d: Maximum d value to test (default: 1.0)
            step: Step size for grid search (default: 0.05)
            adfuller_alpha: Significance level for ADF test (default: self.adfuller_alpha)
            method: Search method - 'binary' or 'grid' (default: 'binary')

        Returns:
            Tuple of (optimal_d, p_value, metadata_dict) where:
            - optimal_d: The smallest d that gives p-value < alpha
            - p_value: The p-value from the ADF test at optimal_d
            - metadata: Dictionary with search details

        Example:
            >>> fd = FractionalDifferentiation()
            >>> series = pd.Series(np.random.randn(1000).cumsum())
            >>> optimal_d, p_value, meta = fd.find_optimal_d(series)
            >>> print(f"Optimal d: {optimal_d:.3f}, p-value: {p_value:.4f}")
        """
        if adfuller_alpha is None:
            adfuller_alpha = self.adfuller_alpha

        if isinstance(series, np.ndarray):
            series = pd.Series(series)

        # Remove any NaN values
        series_clean = series.dropna()

        if len(series_clean) < 100:
            warnings.warn(
                f"Series length ({len(series_clean)}) < 100. "
                "ADF test results may be unreliable."
            )

        # Test different d values
        if method == 'binary':
            return self._binary_search_d(series_clean, min_d, max_d, adfuller_alpha)
        else:
            return self._grid_search_d(series_clean, min_d, max_d, step, adfuller_alpha)

    def _binary_search_d(
        self,
        series: pd.Series,
        min_d: float,
        max_d: float,
        alpha: float
    ) -> Tuple[float, float, Dict]:
        """Binary search for optimal d (more efficient)."""
        metadata = {
            'method': 'binary_search',
            'iterations': 0,
            'test_history': []
        }

        # First, check if max_d achieves stationarity
        diff_max = self.fractional_diff(series, d=max_d)
        diff_max_clean = diff_max.dropna()

        if len(diff_max_clean) < 50:
            warnings.warn("Insufficient data points after differentiation")

        if not STATSMODELS_AVAILABLE:
            raise ImportError(
                "statsmodels is required for find_optimal_d. "
                "Install with: pip install statsmodels"
            )

        try:
            adf_result = adfuller(diff_max_clean, maxlag=1)
            p_value_max = adf_result[1]
        except Exception:
            p_value_max = 1.0

        metadata['test_history'].append({
            'd': max_d,
            'p_value': p_value_max,
            'stationary': p_value_max < alpha
        })

        # If even d=1 doesn't achieve stationarity, return max_d
        if p_value_max >= alpha:
            return max_d, p_value_max, metadata

        # Binary search for minimum d
        low, high = min_d, max_d
        best_d, best_p = max_d, p_value_max

        while high - low > 0.01:
            metadata['iterations'] += 1
            mid = (low + high) / 2

            diff_mid = self.fractional_diff(series, d=mid)
            diff_mid_clean = diff_mid.dropna()

            try:
                adf_result = adfuller(diff_mid_clean, maxlag=1)
                p_value = adf_result[1]
            except:
                p_value = 1.0

            metadata['test_history'].append({
                'd': mid,
                'p_value': p_value,
                'stationary': p_value < alpha
            })

            if p_value < alpha:
                best_d, best_p = mid, p_value
                high = mid
            else:
                low = mid

            if metadata['iterations'] > 50:
                break

        return best_d, best_p, metadata

    def _grid_search_d(
        self,
        series: pd.Series,
        min_d: float,
        max_d: float,
        step: float,
        alpha: float
    ) -> Tuple[float, float, Dict]:
        """Grid search for optimal d (more thorough)."""
        metadata = {
            'method': 'grid_search',
            'test_values': np.arange(min_d, max_d + step, step),
            'test_history': []
        }

        best_d, best_p = max_d, 1.0

        for d in metadata['test_values']:
            diff_series = self.fractional_diff(series, d=d)
            diff_clean = diff_series.dropna()

            if len(diff_clean) < 50:
                continue

            try:
                adf_result = adfuller(diff_clean, maxlag=1)
                p_value = adf_result[1]
            except:
                p_value = 1.0

            metadata['test_history'].append({
                'd': d,
                'p_value': p_value,
                'stationary': p_value < alpha
            })

            # Update best if stationary and smaller d
            if p_value < alpha and d < best_d:
                best_d, best_p = d, p_value

        return best_d, best_p, metadata

    def calculate_memory_loss(
        self,
        original: pd.Series,
        frac_diff: pd.Series,
        lags: int = 20
    ) -> Dict[str, float]:
        """
        Calculate memory loss after fractional differentiation.

        Memory loss is measured as the reduction in autocorrelation.

        Args:
            original: Original time series
            frac_diff: Fractionally differentiated series
            lags: Number of lags to calculate autocorrelation

        Returns:
            Dictionary with memory metrics
        """
        # Remove NaN values
        orig_clean = original.dropna()
        diff_clean = frac_diff.dropna()

        # Calculate autocorrelations
        orig_acf = [orig_clean.autocorr(lag=i) if i < len(orig_clean) else np.nan
                    for i in range(1, lags + 1)]
        diff_acf = [diff_clean.autocorr(lag=i) if i < len(diff_clean) else np.nan
                    for i in range(1, lags + 1)]

        # Calculate metrics
        orig_acf_mean = np.nanmean(np.abs(orig_acf))
        diff_acf_mean = np.nanmean(np.abs(diff_acf))

        memory_preservation = diff_acf_mean / (orig_acf_mean + 1e-10)

        return {
            'original_acf_mean': orig_acf_mean,
            'diff_acf_mean': diff_acf_mean,
            'memory_preservation_ratio': memory_preservation,
            'memory_loss_pct': (1 - memory_preservation) * 100
        }

    def compare_d_values(
        self,
        series: pd.Series,
        d_values: List[float] = None
    ) -> pd.DataFrame:
        """
        Compare different d values on the same series.

        Args:
            series: Time series to analyze
            d_values: List of d values to test (default: [0.0, 0.3, 0.5, 0.7, 1.0])

        Returns:
            DataFrame with comparison metrics
        """
        if d_values is None:
            d_values = [0.0, 0.3, 0.5, 0.7, 1.0]

        results = []

        for d in d_values:
            if d == 0.0:
                diff_series = series
            else:
                diff_series = self.fractional_diff(series, d=d)

            diff_clean = diff_series.dropna()

            # ADF test
            try:
                adf_result = adfuller(diff_clean, maxlag=1)
                adf_stat = adf_result[0]
                p_value = adf_result[1]
                critical_values = adf_result[4]
            except:
                adf_stat, p_value = np.nan, 1.0
                critical_values = {}

            # Memory metrics
            memory_metrics = self.calculate_memory_loss(series, diff_series)

            results.append({
                'd': d,
                'adf_statistic': adf_stat,
                'p_value': p_value,
                'is_stationary': p_value < self.adfuller_alpha,
                'memory_preservation': memory_metrics['memory_preservation_ratio'],
                'memory_loss_pct': memory_metrics['memory_loss_pct'],
                'n_obs': len(diff_clean),
            })

        return pd.DataFrame(results)


class FractionalDiffTransformer:
    """
    Scikit-learn compatible transformer for fractional differentiation.

    This transformer can be used in sklearn pipelines for feature engineering.

    Example:
        >>> from sklearn.pipeline import Pipeline
        >>> transformer = FractionalDiffTransformer(d=0.5)
        >>> X_transformed = transformer.fit_transform(X)
    """

    def __init__(
        self,
        d: float = 0.5,
        threshold: float = 1e-5,
        auto_find_d: bool = False,
        adfuller_alpha: float = 0.05
    ):
        """
        Initialize transformer.

        Args:
            d: Differentiation order (ignored if auto_find_d=True)
            threshold: Weight cutoff threshold
            auto_find_d: If True, automatically find optimal d during fit
            adfuller_alpha: Significance level for ADF test
        """
        self.d = d
        self.threshold = threshold
        self.auto_find_d = auto_find_d
        self.adfuller_alpha = adfuller_alpha
        self.fd = FractionalDifferentiation(
            threshold=threshold,
            adfuller_alpha=adfuller_alpha
        )
        self.optimal_d_ = None
        self.feature_names_in_ = None

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y=None):
        """
        Fit the transformer.

        If auto_find_d=True, this will find the optimal d for each feature.

        Args:
            X: Input data
            y: Ignored (present for sklearn compatibility)

        Returns:
            self
        """
        if isinstance(X, np.ndarray):
            X = pd.DataFrame(X)

        self.feature_names_in_ = X.columns.tolist()

        if self.auto_find_d:
            # Find optimal d for first feature (can be extended)
            optimal_d, _, _ = self.fd.find_optimal_d(
                X.iloc[:, 0],
                adfuller_alpha=self.adfuller_alpha
            )
            self.optimal_d_ = optimal_d
        else:
            self.optimal_d_ = self.d

        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> pd.DataFrame:
        """
        Transform features using fractional differentiation.

        Args:
            X: Input data

        Returns:
            Transformed data
        """
        if isinstance(X, np.ndarray):
            X = pd.DataFrame(X)

        result = pd.DataFrame(index=X.index)

        for col in X.columns:
            result[col] = self.fd.fractional_diff(
                X[col],
                d=self.optimal_d_,
                threshold=self.threshold
            )

        return result

    def fit_transform(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y=None,
        **fit_params
    ) -> pd.DataFrame:
        """
        Fit and transform in one step.

        Args:
            X: Input data
            y: Ignored
            **fit_params: Additional fit parameters

        Returns:
            Transformed data
        """
        return self.fit(X, y).transform(X)

    def get_feature_names_out(self, input_features=None):
        """
        Get output feature names for transformation.

        Args:
            input_features: Input feature names (optional)

        Returns:
            Array of output feature names
        """
        if input_features is None:
            input_features = self.feature_names_in_

        return np.array([f"{f}_fracdiff" for f in input_features])


def apply_frac_diff_to_dataframe(
    df: pd.DataFrame,
    d: float = 0.5,
    columns: List[str] = None,
    threshold: float = 1e-5
) -> pd.DataFrame:
    """
    Apply fractional differentiation to selected DataFrame columns.

    Args:
        df: Input DataFrame
        d: Differentiation order
        columns: Columns to transform (None = all numeric)
        threshold: Weight cutoff threshold

    Returns:
        DataFrame with fractionally differentiated columns

    Example:
        >>> df = pd.DataFrame({'price': [1, 2, 3, 4, 5], 'volume': [100, 110, 90, 105, 95]})
        >>> df_fracdiff = apply_frac_diff_to_dataframe(df, d=0.3, columns=['price'])
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()

    result = df.copy()
    fd = FractionalDifferentiation(threshold=threshold)

    for col in columns:
        if col in df.columns:
            result[f'{col}_fracdiff'] = fd.fractional_diff(df[col], d=d)

    return result


# Convenience functions for backward compatibility
def get_weights(d: float, threshold: float = 1e-5) -> np.ndarray:
    """Calculate fractional differentiation weights."""
    fd = FractionalDifferentiation(threshold=threshold)
    return fd.get_weights(d, threshold)


def fractional_diff(
    series: Union[pd.Series, np.ndarray],
    d: float,
    threshold: float = 1e-5
) -> pd.Series:
    """Apply fractional differentiation to a series."""
    fd = FractionalDifferentiation(threshold=threshold)
    return fd.fractional_diff(series, d, threshold)


def find_optimal_d(
    series: Union[pd.Series, np.ndarray],
    min_d: float = 0.0,
    max_d: float = 1.0,
    step: float = 0.05,
    adfuller_alpha: float = 0.05
) -> Tuple[float, float]:
    """Find optimal d for stationarity."""
    fd = FractionalDifferentiation(adfuller_alpha=adfuller_alpha)
    optimal_d, p_value, _ = fd.find_optimal_d(
        series, min_d, max_d, step, adfuller_alpha
    )
    return optimal_d, p_value
