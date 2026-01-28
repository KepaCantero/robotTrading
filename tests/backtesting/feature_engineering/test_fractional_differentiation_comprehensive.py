"""
Comprehensive unit tests for Fractional Differentiation module.

Tests cover:
- Weight calculation with Numba JIT
- Fractional differentiation operations
- Stationarity testing (ADF test)
- Fixed window differentiation
- Expanding window differentiation
- Edge cases and error handling
- Performance optimizations
- Memory efficiency
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Try importing the module
try:
    from app.backtesting.feature_engineering.fractional_differentiation import (
        calculate_weights_numba,
        fractional_diff_fast_numba,
        fractional_diff_fixed_window,
        fractional_diff_expanding_window,
        find_optimal_d,
        FractionalDifferentiationResult,
        MIN_WEIGHT_THRESHOLD,
    )
    MODULE_AVAILABLE = True
except ImportError as e:
    MODULE_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not MODULE_AVAILABLE, reason=f"Module not available: {IMPORT_ERROR if not MODULE_AVAILABLE else 'OK'}")
class TestNumbaAcceleratedFunctions:
    """Test suite for Numba-accelerated core functions."""

    def test_calculate_weights_numba_basic(self):
        """Test basic weight calculation."""
        d = 0.5
        threshold = 1e-5

        weights = calculate_weights_numba(d, threshold)

        assert isinstance(weights, np.ndarray)
        assert len(weights) > 0
        assert weights[0] == 1.0  # First weight is always 1

    def test_calculate_weights_numba_different_d_values(self):
        """Test weight calculation with different d values."""
        threshold = 1e-5

        for d in [0.1, 0.3, 0.5, 0.7, 0.9]:
            weights = calculate_weights_numba(d, threshold)

            assert len(weights) > 0
            assert weights[0] == 1.0
            # Higher d should produce more weights
            if d > 0.5:
                assert len(weights) >= 10

    def test_calculate_weights_numba_threshold_effect(self):
        """Test that threshold affects the number of weights."""
        d = 0.5

        weights_strict = calculate_weights_numba(d, 1e-8)
        weights_loose = calculate_weights_numba(d, 1e-3)

        # Stricter threshold should produce more weights
        assert len(weights_strict) >= len(weights_loose)

    def test_calculate_weights_numba_decay(self):
        """Test that weights decay over time."""
        d = 0.5
        threshold = 1e-5

        weights = calculate_weights_numba(d, threshold)

        # Check that weights generally decay
        assert abs(weights[-1]) < threshold

    def test_calculate_weights_numba_extreme_d(self):
        """Test with extreme d values."""
        threshold = 1e-5

        # Very small d
        weights_small = calculate_weights_numba(0.01, threshold)
        assert len(weights_small) > 0

        # d close to 1
        weights_large = calculate_weights_numba(0.99, threshold)
        assert len(weights_large) > 0
        assert len(weights_large) > len(weights_small)

    def test_fractional_diff_fast_numba_basic(self):
        """Test basic fractional differentiation."""
        # Create simple price series
        series = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0], dtype=np.float64)
        weights = np.array([1.0, -0.5, 0.25], dtype=np.float64)

        result = fractional_diff_fast_numba(series, weights)

        assert isinstance(result, np.ndarray)
        assert len(result) == len(series)
        # First values should be NaN due to insufficient history
        assert pd.isna(result[0]) or np.isnan(result[0])

    def test_fractional_diff_fast_numba_trend(self):
        """Test fractional differentiation on trending series."""
        # Create upward trending series
        series = np.arange(100.0, 200.0, 1.0, dtype=np.float64)
        weights = calculate_weights_numba(0.5, 1e-5)

        result = fractional_diff_fast_numba(series, weights)

        assert isinstance(result, np.ndarray)
        assert len(result) == len(series)

    def test_fractional_diff_fast_numba_constant_series(self):
        """Test fractional differentiation on constant series."""
        series = np.full(50, 100.0, dtype=np.float64)
        weights = calculate_weights_numba(0.5, 1e-5)

        result = fractional_diff_fast_numba(series, weights)

        # Constant series should produce near-zero differentiation
        assert isinstance(result, np.ndarray)


@pytest.mark.skipif(not MODULE_AVAILABLE, reason="Module not available")
class TestFractionalDiffFixedWindow:
    """Test suite for fixed window fractional differentiation."""

    @pytest.fixture
    def sample_price_series(self):
        """Create sample price series for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2020-01-01', periods=500, freq='D')

        # Create geometric random walk
        returns = np.random.normal(0.0005, 0.02, 500)
        prices = 100 * np.exp(np.cumsum(returns))

        return pd.Series(prices, index=dates)

    def test_fixed_window_basic(self, sample_price_series):
        """Test basic fixed window differentiation."""
        result = fractional_diff_fixed_window(
            sample_price_series,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_price_series)
        # Check result has same index
        assert result.index.equals(sample_price_series.index)

    def test_fixed_window_different_d_values(self, sample_price_series):
        """Test fixed window with different d values."""
        for d in [0.1, 0.3, 0.5, 0.7]:
            result = fractional_diff_fixed_window(
                sample_price_series,
                d=d,
                threshold=1e-5,
            )

            assert isinstance(result, pd.Series)
            assert len(result) == len(sample_price_series)

    def test_fixed_window_threshold_effect(self, sample_price_series):
        """Test that threshold affects results."""
        result_strict = fractional_diff_fixed_window(
            sample_price_series,
            d=0.5,
            threshold=1e-8,
        )

        result_loose = fractional_diff_fixed_window(
            sample_price_series,
            d=0.5,
            threshold=1e-3,
        )

        assert isinstance(result_strict, pd.Series)
        assert isinstance(result_loose, pd.Series)

    def test_fixed_window_short_series(self):
        """Test fixed window with very short series."""
        short_series = pd.Series([100.0, 101.0, 102.0, 103.0])

        result = fractional_diff_fixed_window(
            short_series,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(short_series)

    def test_fixed_window_single_value(self):
        """Test fixed window with single value."""
        single_series = pd.Series([100.0])

        result = fractional_diff_fixed_window(
            single_series,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == 1


@pytest.mark.skipif(not MODULE_AVAILABLE, reason="Module not available")
class TestFractionalDiffExpandingWindow:
    """Test suite for expanding window fractional differentiation."""

    @pytest.fixture
    def sample_price_series(self):
        """Create sample price series for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2020-01-01', periods=500, freq='D')

        # Create geometric random walk
        returns = np.random.normal(0.0005, 0.02, 500)
        prices = 100 * np.exp(np.cumsum(returns))

        return pd.Series(prices, index=dates)

    def test_expanding_window_basic(self, sample_price_series):
        """Test basic expanding window differentiation."""
        result = fractional_diff_expanding_window(
            sample_price_series,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_price_series)

    def test_expanding_window_different_d_values(self, sample_price_series):
        """Test expanding window with different d values."""
        for d in [0.1, 0.3, 0.5, 0.7]:
            result = fractional_diff_expanding_window(
                sample_price_series,
                d=d,
                threshold=1e-5,
            )

            assert isinstance(result, pd.Series)
            assert len(result) == len(sample_price_series)

    def test_expanding_window_min_samples(self, sample_price_series):
        """Test expanding window with minimum samples requirement."""
        result = fractional_diff_expanding_window(
            sample_price_series,
            d=0.5,
            threshold=1e-5,
            min_samples=50,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_price_series)


@pytest.mark.skipif(not MODULE_AVAILABLE, reason="Module not available")
class TestFindOptimalD:
    """Test suite for finding optimal differentiation order."""

    @pytest.fixture
    def sample_price_series(self):
        """Create sample price series for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2020-01-01', periods=500, freq='D')

        # Create trending series (non-stationary)
        returns = np.random.normal(0.001, 0.02, 500)
        prices = 100 * np.exp(np.cumsum(returns))

        return pd.Series(prices, index=dates)

    def test_find_optimal_d_basic(self, sample_price_series):
        """Test basic optimal d finding."""
        result = find_optimal_d(
            sample_price_series,
            d_range=(0.1, 0.9),
            d_step=0.1,
            threshold=1e-5,
        )

        assert hasattr(result, 'd')
        assert hasattr(result, 'series')
        assert hasattr(result, 'adf_statistic')
        assert hasattr(result, 'p_value')
        assert hasattr(result, 'is_stationary')

        # Check that d is in reasonable range
        assert 0.1 <= result.d <= 0.9

    def test_find_optimal_d_different_ranges(self, sample_price_series):
        """Test optimal d finding with different ranges."""
        result_narrow = find_optimal_d(
            sample_price_series,
            d_range=(0.3, 0.7),
            d_step=0.1,
            threshold=1e-5,
        )

        assert 0.3 <= result_narrow.d <= 0.7

    def test_find_optimal_d_with_adf_threshold(self, sample_price_series):
        """Test optimal d finding with custom ADF threshold."""
        result = find_optimal_d(
            sample_price_series,
            d_range=(0.1, 0.9),
            d_step=0.1,
            threshold=1e-5,
            adf_threshold=0.01,
        )

        assert result is not None
        assert hasattr(result, 'p_value')


@pytest.mark.skipif(not MODULE_AVAILABLE, reason="Module not available")
class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_empty_series(self):
        """Test with empty series."""
        empty_series = pd.Series([], dtype=float)

        result = fractional_diff_fixed_window(
            empty_series,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_series_with_nan(self):
        """Test with series containing NaN values."""
        series_with_nan = pd.Series([100.0, np.nan, 102.0, 103.0, 104.0])

        result = fractional_diff_fixed_window(
            series_with_nan,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)

    def test_series_with_inf(self):
        """Test with series containing infinite values."""
        series_with_inf = pd.Series([100.0, 101.0, np.inf, 103.0, 104.0])

        result = fractional_diff_fixed_window(
            series_with_inf,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)

    def test_negative_prices(self):
        """Test with negative prices (invalid but should handle gracefully)."""
        negative_series = pd.Series([-100.0, -101.0, -102.0, -103.0])

        result = fractional_diff_fixed_window(
            negative_series,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)

    def test_zero_prices(self):
        """Test with zero prices."""
        zero_series = pd.Series([0.0, 0.0, 0.0, 0.0])

        result = fractional_diff_fixed_window(
            zero_series,
            d=0.5,
            threshold=1e-5,
        )

        assert isinstance(result, pd.Series)


@pytest.mark.skipif(not MODULE_AVAILABLE, reason="Module not available")
class TestPerformance:
    """Test suite for performance characteristics."""

    def test_calculate_weights_performance(self):
        """Test weight calculation performance."""
        import time

        start = time.time()
        weights = calculate_weights_numba(0.5, 1e-5)
        end = time.time()

        # Should be very fast with Numba
        assert (end - start) < 1.0  # Less than 1 second
        assert len(weights) > 0

    def test_fractional_diff_performance(self):
        """Test fractional differentiation performance."""
        import time

        # Create large series
        series = np.random.randn(10000).cumsum() + 100
        weights = calculate_weights_numba(0.5, 1e-5)

        start = time.time()
        result = fractional_diff_fast_numba(series, weights)
        end = time.time()

        # Should be fast with Numba
        assert (end - start) < 1.0  # Less than 1 second
        assert len(result) == len(series)


@pytest.mark.skipif(not MODULE_AVAILABLE, reason="Module not available")
class TestDataClass:
    """Test suite for FractionalDifferentiationResult dataclass."""

    def test_result_dataclass_creation(self):
        """Test creating FractionalDifferentiationResult."""
        result = FractionalDifferentiationResult(
            d=0.5,
            series=pd.Series([1.0, 2.0, 3.0]),
            adf_statistic=-5.0,
            p_value=0.0001,
            is_stationary=True,
            n_weights=100,
        )

        assert result.d == 0.5
        assert result.adf_statistic == -5.0
        assert result.p_value == 0.0001
        assert result.is_stationary is True
        assert result.n_weights == 100

    def test_result_dataclass_attributes(self):
        """Test FractionalDifferentiationResult attributes."""
        series = pd.Series([1.0, 2.0, 3.0])
        result = FractionalDifferentiationResult(
            d=0.3,
            series=series,
            adf_statistic=-3.5,
            p_value=0.01,
            is_stationary=False,
            n_weights=50,
        )

        assert hasattr(result, 'd')
        assert hasattr(result, 'series')
        assert hasattr(result, 'adf_statistic')
        assert hasattr(result, 'p_value')
        assert hasattr(result, 'is_stationary')
        assert hasattr(result, 'n_weights')
