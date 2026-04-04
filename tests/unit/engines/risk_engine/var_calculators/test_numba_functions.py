"""
Unit tests for Numba-accelerated VaR helper functions.

Tests for low-level Numba JIT functions used in VaR calculations.
"""

import numpy as np
import pytest

from app.engines.risk_engine.var_calculators.var_calculators import (
    calculate_cvar_numba,
    calculate_jarque_bera_numba,
    calculate_mean_std_numba,
    calculate_percentile_numba,
)


@pytest.mark.unit
class TestCalculatePercentileNumba:
    """Test percentile calculation with Numba."""

    def test_percentile_50(self):
        """Test 50th percentile (median)."""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = calculate_percentile_numba(data, 50)
        assert result == 5.5

    def test_percentile_5(self):
        """Test 5th percentile."""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = calculate_percentile_numba(data, 5)
        assert 1.0 <= result <= 2.0

    def test_percentile_95(self):
        """Test 95th percentile."""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = calculate_percentile_numba(data, 95)
        assert 9.0 <= result <= 10.0

    def test_percentile_with_duplicates(self):
        """Test percentile with duplicate values."""
        data = np.array([5, 5, 5, 5, 5])
        result = calculate_percentile_numba(data, 50)
        assert result == 5.0

    def test_percentile_negative_values(self):
        """Test percentile with negative values."""
        data = np.array([-5, -3, -1, 0, 1, 3, 5])
        result = calculate_percentile_numba(data, 50)
        assert result == 0.0

    def test_percentile_empty_array(self):
        """Test percentile with empty array."""
        data = np.array([])
        result = calculate_percentile_numba(data, 50)
        assert np.isnan(result)

    def test_percentile_single_value(self):
        """Test percentile with single value."""
        data = np.array([42.0])
        result = calculate_percentile_numba(data, 50)
        assert result == 42.0


@pytest.mark.unit
class TestCalculateMeanStdNumba:
    """Test mean and std calculation with Numba."""

    def test_mean_std_basic(self):
        """Test basic mean and std calculation."""
        data = np.array([1, 2, 3, 4, 5])
        mean, std = calculate_mean_std_numba(data)
        assert abs(mean - 3.0) < 0.01
        assert abs(std - np.std(data)) < 0.01

    def test_mean_zero_centered(self):
        """Test mean of zero-centered data."""
        data = np.array([-2, -1, 0, 1, 2])
        mean, std = calculate_mean_std_numba(data)
        assert mean == 0.0
        assert std > 0

    def test_std_constant_values(self):
        """Test std of constant values."""
        data = np.array([5.0] * 10)
        mean, std = calculate_mean_std_numba(data)
        assert mean == 5.0
        assert std == 0.0

    def test_mean_std_large_values(self):
        """Test with large values."""
        data = np.array([1e6, 1e6 + 1, 1e6 - 1])
        mean, std = calculate_mean_std_numba(data)
        assert abs(mean - 1e6) < 1.0

    def test_empty_array(self):
        """Test with empty array."""
        data = np.array([])
        mean, std = calculate_mean_std_numba(data)
        assert mean == 0.0
        assert std == 0.0


@pytest.mark.unit
class TestCalculateCVaRNumba:
    """Test CVaR calculation with Numba."""

    def test_cvar_basic(self):
        """Test basic CVaR calculation."""
        data = np.array([-0.05, -0.04, -0.03, -0.02, -0.01])
        var = -0.03
        cvar = calculate_cvar_numba(data, var)

        # CVaR should be average of values <= var
        # (-0.05, -0.04, -0.03) / 3 = -0.04
        assert abs(cvar - (-0.04)) < 0.01

    def test_cvar_all_values_above_var(self):
        """Test CVaR when all values are above VaR."""
        data = np.array([0.01, 0.02, 0.03])
        var = -0.05
        cvar = calculate_cvar_numba(data, var)

        # Should return var when no values <= var
        assert cvar == var

    def test_cvar_empty_array(self):
        """Test CVaR with empty array."""
        data = np.array([])
        var = -0.03
        cvar = calculate_cvar_numba(data, var)

        # Should return var
        assert cvar == var

    def test_cvar_with_negative_var(self):
        """Test CVaR with negative VaR."""
        data = np.array([-0.08, -0.06, -0.04, -0.02, 0.01, 0.03])
        var = -0.05
        cvar = calculate_cvar_numba(data, var)

        # Should average values <= -0.05
        assert cvar <= var

    def test_cvar_more_negative_than_var(self):
        """Test that CVaR is more negative than VaR."""
        data = np.array([-0.10, -0.08, -0.06, -0.04, -0.02, 0.01])
        var = -0.05
        cvar = calculate_cvar_numba(data, var)

        # CVaR should be more negative
        assert cvar <= var


@pytest.mark.unit
class TestCalculateJarqueBeraNumba:
    """Test Jarque-Bera test with Numba."""

    def test_jb_normal_distribution(self):
        """Test JB statistic for normal distribution."""
        np.random.seed(42)
        data = np.random.normal(0, 1, 1000)

        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # p-value should be relatively high for normal data
        assert p_value > 0.01

    def test_jb_skewed_distribution(self):
        """Test JB statistic for skewed distribution."""
        np.random.seed(42)
        data = np.random.exponential(1, 1000)

        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # p-value should be very low for non-normal data
        assert p_value < 0.05

    def test_jb_small_sample(self):
        """Test JB with small sample."""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # Should still calculate
        assert isinstance(jb_stat, float)
        assert isinstance(p_value, float)

    def test_jb_constant_values(self):
        """Test JB with constant values (zero variance)."""
        data = np.array([5.0] * 100)

        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # Should handle gracefully
        assert p_value == 1.0

    def test_jb_very_small_sample(self):
        """Test JB with very small sample (< 20)."""
        data = np.array([1, 2, 3, 4, 5])

        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # Should return p_value = 1 for small samples
        assert p_value == 1.0
