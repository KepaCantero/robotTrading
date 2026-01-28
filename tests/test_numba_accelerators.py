"""
Test suite for Numba JIT accelerators.

Validates that all optimized functions work correctly and provide
expected performance improvements.
"""

import time
import numpy as np
import pytest
from typing import List

# Test imports
try:
    from app.core.numba_accelerators import (
        calculate_rsi_numba,
        calculate_ema_numba,
        calculate_macd_numba,
        calculate_atr_numba,
        calculate_bollinger_bands_numba,
        calculate_stochastic_numba,
        calculate_skewness_numba,
        calculate_kurtosis_numba,
        calculate_var_numba,
        calculate_cvar_numba,
        rolling_mean_numba,
        rolling_std_numba,
        calculate_rsi,
        calculate_ema,
        calculate_macd,
        calculate_atr,
        get_numba_info,
        NUMBA_AVAILABLE,
    )

    NUMBA_ENABLED = NUMBA_AVAILABLE
except ImportError:
    pytest.skip("Numba accelerators not available", allow_module_level=True)
    NUMBA_ENABLED = False


class TestNumbaAccelerators:
    """Test suite for Numba JIT compilation functions."""

    @pytest.fixture
    def sample_prices(self) -> List[float]:
        """Generate sample price data for testing."""
        np.random.seed(42)
        base = 100.0
        prices = [base]
        for _ in range(99):
            change = np.random.randn() * 2  # Random walk
            prices.append(prices[-1] * (1 + change / 100))
        return prices

    @pytest.fixture
    def sample_ohlc(self) -> tuple:
        """Generate sample OHLC data for testing."""
        np.random.seed(42)
        closes = np.array([100 + i * 0.1 + np.random.randn() for i in range(100)])
        highs = closes * 1.02
        lows = closes * 0.98
        return highs, lows, closes

    @pytest.fixture
    def sample_returns(self) -> List[float]:
        """Generate sample return data for testing."""
        np.random.seed(42)
        returns = [np.random.randn() * 0.02 for _ in range(1000)]
        return returns

    def test_numba_availability(self):
        """Test that Numba is available."""
        assert NUMBA_ENABLED, "Numba should be available for these tests"

    def test_get_numba_info(self):
        """Test Numba info function."""
        info = get_numba_info()
        assert isinstance(info, dict)
        assert 'numba_available' in info
        assert 'functions_optimized' in info
        assert 'expected_speedups' in info
        assert info['functions_optimized'] > 0

    def test_calculate_rsi_numba(self, sample_prices):
        """Test RSI calculation with Numba."""
        prices_array = np.array(sample_prices)
        rsi = calculate_rsi_numba(prices_array, period=14)

        # Validate RSI is in valid range
        assert 0 <= rsi <= 100
        assert not np.isnan(rsi)
        assert not np.isinf(rsi)

    def test_calculate_rsi_wrapper(self, sample_prices):
        """Test RSI wrapper function."""
        rsi = calculate_rsi(sample_prices, period=14)

        # Validate result
        assert rsi is not None
        assert 0 <= rsi <= 100
        assert isinstance(rsi, float)

    def test_calculate_ema_numba(self, sample_prices):
        """Test EMA calculation with Numba."""
        prices_array = np.array(sample_prices)
        ema_array = calculate_ema_numba(prices_array, period=20)

        # Validate EMA array
        assert len(ema_array) == len(sample_prices)
        # First few values should be NaN
        assert np.isnan(ema_array[0])
        # Last value should be valid
        assert not np.isnan(ema_array[-1])

    def test_calculate_ema_wrapper(self, sample_prices):
        """Test EMA wrapper function."""
        ema = calculate_ema(sample_prices, period=20)

        # Validate result
        assert ema is not None
        assert not np.isnan(ema)
        assert isinstance(ema, float)

    def test_calculate_macd_numba(self, sample_prices):
        """Test MACD calculation with Numba."""
        prices_array = np.array(sample_prices)
        macd_line, signal_line, histogram = calculate_macd_numba(prices_array)

        # Validate MACD components
        assert len(macd_line) == len(sample_prices)
        assert len(signal_line) == len(sample_prices)
        assert len(histogram) == len(sample_prices)

    def test_calculate_macd_wrapper(self, sample_prices):
        """Test MACD wrapper function."""
        macd, signal, hist = calculate_macd(sample_prices)

        # Validate results
        # Note: May be None for short time series
        if macd is not None:
            assert isinstance(macd, float)
            assert isinstance(signal, float)
            assert isinstance(hist, float)

    def test_calculate_atr_numba(self, sample_ohlc):
        """Test ATR calculation with Numba."""
        highs, lows, closes = sample_ohlc
        atr_array = calculate_atr_numba(highs, lows, closes, period=14)

        # Validate ATR array
        assert len(atr_array) == len(closes)
        # ATR should be positive
        assert atr_array[-1] > 0

    def test_calculate_atr_wrapper(self, sample_ohlc):
        """Test ATR wrapper function."""
        highs, lows, closes = sample_ohlc
        atr = calculate_atr(highs.tolist(), lows.tolist(), closes.tolist())

        # Validate result
        assert atr is not None
        assert atr > 0
        assert isinstance(atr, float)

    def test_calculate_bollinger_bands_numba(self, sample_prices):
        """Test Bollinger Bands calculation with Numba."""
        prices_array = np.array(sample_prices)
        upper, middle, lower = calculate_bollinger_bands_numba(prices_array)

        # Validate bands
        assert len(upper) == len(sample_prices)
        assert len(middle) == len(sample_prices)
        assert len(lower) == len(sample_prices)

        # Upper should be > middle > lower (where valid)
        last_valid = -1
        if not np.isnan(upper[last_valid]):
            assert upper[last_valid] > middle[last_valid]
            assert middle[last_valid] > lower[last_valid]

    def test_calculate_stochastic_numba(self, sample_ohlc):
        """Test Stochastic calculation with Numba."""
        highs, lows, closes = sample_ohlc
        k_percent, d_percent = calculate_stochastic_numba(highs, lows, closes)

        # Validate Stochastic values
        assert len(k_percent) == len(closes)
        assert len(d_percent) == len(closes)

        # Stochastic should be in [0, 100] range
        if not np.isnan(k_percent[-1]):
            assert 0 <= k_percent[-1] <= 100

    def test_calculate_skewness_numba(self, sample_returns):
        """Test skewness calculation with Numba."""
        returns_array = np.array(sample_returns)
        skewness = calculate_skewness_numba(returns_array)

        # Validate skewness
        assert not np.isnan(skewness)
        assert not np.isinf(skewness)
        assert isinstance(skewness, float)

    def test_calculate_kurtosis_numba(self, sample_returns):
        """Test kurtosis calculation with Numba."""
        returns_array = np.array(sample_returns)
        kurtosis = calculate_kurtosis_numba(returns_array)

        # Validate kurtosis
        assert not np.isnan(kurtosis)
        assert not np.isinf(kurtosis)
        assert isinstance(kurtosis, float)

    def test_calculate_var_numba(self, sample_returns):
        """Test VaR calculation with Numba."""
        returns_array = np.array(sample_returns)
        var = calculate_var_numba(returns_array, confidence_level=0.95)

        # Validate VaR
        assert not np.isnan(var)
        assert isinstance(var, float)
        # VaR should be negative for typical returns
        assert var < 0

    def test_calculate_cvar_numba(self, sample_returns):
        """Test CVaR calculation with Numba."""
        returns_array = np.array(sample_returns)
        cvar = calculate_cvar_numba(returns_array, confidence_level=0.95)

        # Validate CVaR
        assert not np.isnan(cvar)
        assert isinstance(cvar, float)
        # CVaR should be negative for typical returns
        assert cvar < 0

    def test_rolling_mean_numba(self, sample_prices):
        """Test rolling mean calculation with Numba."""
        prices_array = np.array(sample_prices)
        rolling = rolling_mean_numba(prices_array, window=20)

        # Validate rolling mean
        assert len(rolling) == len(sample_prices)
        # Last value should be valid
        assert not np.isnan(rolling[-1])

    def test_rolling_std_numba(self, sample_prices):
        """Test rolling std calculation with Numba."""
        prices_array = np.array(sample_prices)
        rolling = rolling_std_numba(prices_array, window=20)

        # Validate rolling std
        assert len(rolling) == len(sample_prices)
        # Last value should be valid and positive
        assert not np.isnan(rolling[-1])
        assert rolling[-1] >= 0


class TestNumbaPerformance:
    """Performance tests for Numba accelerators."""

    @pytest.fixture
    def large_dataset(self) -> np.ndarray:
        """Generate large dataset for performance testing."""
        np.random.seed(42)
        return np.array([100 + i * 0.1 + np.random.randn() for i in range(10000)])

    def test_rsi_performance(self, large_dataset):
        """Test RSI calculation performance."""
        # Warm up JIT compilation
        calculate_rsi_numba(large_dataset[:100], period=14)

        # Benchmark
        start = time.time()
        iterations = 100
        for _ in range(iterations):
            rsi = calculate_rsi_numba(large_dataset, period=14)
        elapsed = time.time() - start

        # Should be very fast with Numba (< 1 second for 100 iterations)
        assert elapsed < 1.0, f"RSI too slow: {elapsed:.3f}s for {iterations} iterations"

        print(f"✅ RSI Performance: {elapsed:.3f}s for {iterations} iterations")
        print(f"   Average: {elapsed/iterations*1000:.2f}ms per calculation")

    def test_ema_performance(self, large_dataset):
        """Test EMA calculation performance."""
        # Warm up JIT compilation
        calculate_ema_numba(large_dataset[:100], period=20)

        # Benchmark
        start = time.time()
        iterations = 100
        for _ in range(iterations):
            ema = calculate_ema_numba(large_dataset, period=20)
        elapsed = time.time() - start

        # Should be very fast with Numba
        assert elapsed < 1.0, f"EMA too slow: {elapsed:.3f}s for {iterations} iterations"

        print(f"✅ EMA Performance: {elapsed:.3f}s for {iterations} iterations")
        print(f"   Average: {elapsed/iterations*1000:.2f}ms per calculation")

    def test_macd_performance(self, large_dataset):
        """Test MACD calculation performance."""
        # Warm up JIT compilation
        calculate_macd_numba(large_dataset[:100])

        # Benchmark
        start = time.time()
        iterations = 50
        for _ in range(iterations):
            macd, signal, hist = calculate_macd_numba(large_dataset)
        elapsed = time.time() - start

        # Should be fast with Numba
        assert elapsed < 2.0, f"MACD too slow: {elapsed:.3f}s for {iterations} iterations"

        print(f"✅ MACD Performance: {elapsed:.3f}s for {iterations} iterations")
        print(f"   Average: {elapsed/iterations*1000:.2f}ms per calculation")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
