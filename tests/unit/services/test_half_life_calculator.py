"""
Unit tests for Half-Life Calculator.

Tests Ornstein-Uhlenbeck half-life calculation as described in
Ernest Chan's "Quantitative Trading" (Chapter 2).
"""

import pytest
from decimal import Decimal

import numpy as np
import pandas as pd

from app.services.half_life_calculator import (
    HalfLifeCalculator,
    HalfLifeResult,
    OUProcessParams,
    calculate_half_life,
)


class TestHalfLifeCalculator:
    """Test suite for HalfLifeCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator instance."""
        return HalfLifeCalculator(min_samples=30)

    @pytest.fixture
    def mean_reverting_series(self):
        """Create a mean-reverting price series."""
        np.random.seed(42)
        n = 100

        # Create OU process: dx = theta * (mu - x) * dt + sigma * dW
        theta = 0.5  # Mean reversion rate
        mu = 100.0  # Long-term mean
        sigma = 2.0  # Volatility
        dt = 0.1  # Time step

        prices = [mu]
        for i in range(n - 1):
            dx = theta * (mu - prices[-1]) * dt + sigma * np.sqrt(dt) * np.random.randn()
            prices.append(prices[-1] + dx)

        return np.array(prices)

    @pytest.fixture
    def trending_series(self):
        """Create a trending (non-mean-reverting) price series."""
        np.random.seed(42)
        n = 100
        trend = 0.5
        noise = 2.0

        prices = [100]
        for i in range(n - 1):
            prices.append(prices[-1] + trend + noise * np.random.randn())

        return np.array(prices)

    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.min_samples == 30
        assert calculator.confidence_level == 0.95

    def test_calculate_half_life_mean_reverting(self, calculator, mean_reverting_series):
        """Test half-life calculation for mean-reverting series."""
        result = calculator.calculate_half_life(mean_reverting_series, data_frequency="D")

        # Check result structure
        assert isinstance(result, HalfLifeResult)
        assert result.is_mean_reverting
        assert result.half_life_days > 0
        assert result.mean_reversion_rate > 0
        assert result.half_life_days < float("inf")

    def test_calculate_half_life_trending(self, calculator, trending_series):
        """Test half-life calculation for trending series."""
        result = calculator.calculate_half_life(trending_series, data_frequency="D")

        # Should detect non-mean-reverting
        assert isinstance(result, HalfLifeResult)
        # Trending series should have very long or infinite half-life
        assert result.half_life_days > 50 or not result.is_mean_reverting

    def test_insufficient_data(self, calculator):
        """Test handling of insufficient data."""
        short_series = np.random.randn(10) * 10 + 100

        result = calculator.calculate_half_life(short_series)

        # Should return invalid result
        assert isinstance(result, HalfLifeResult)
        assert not result.is_mean_reverting
        assert result.half_life_days == float("inf")

    def test_constant_series(self, calculator):
        """Test handling of constant series."""
        constant_series = np.array([100.0] * 100)

        result = calculator.calculate_half_life(constant_series)

        # Should return invalid result
        assert isinstance(result, HalfLifeResult)
        assert not result.is_mean_reverting

    def test_fit_ou_process(self, calculator, mean_reverting_series):
        """Test OU process fitting."""
        params = calculator._fit_ou_process(mean_reverting_series)

        assert isinstance(params, OUProcessParams)
        assert params.theta > 0  # Should have positive mean reversion rate
        assert params.mu is not None
        assert params.sigma > 0
        assert params.half_life > 0

    def test_mean_reversion_speed_classification(self, calculator):
        """Test mean reversion speed classification."""
        # Fast mean reversion (half-life < 5 days)
        fast_prices = np.random.randn(100) * 2 + 100
        result = calculator.calculate_half_life(fast_prices, data_frequency="D")

        assert result.mean_reversion_speed in ["fast", "medium", "slow", "unknown"]

    def test_confidence_interval_calculation(self, calculator, mean_reverting_series):
        """Test confidence interval calculation."""
        params = calculator._fit_ou_process(mean_reverting_series)

        if params and params.theta > 0:
            ci, p_value = calculator._calculate_confidence_interval(
                mean_reverting_series, params.theta
            )

            # Should return valid confidence interval
            assert isinstance(ci, tuple)
            assert len(ci) == 2
            assert ci[0] < ci[1]  # Lower bound < upper bound
            assert 0.0 <= p_value <= 1.0

    def test_theta_significance(self, calculator, mean_reverting_series):
        """Test theta significance calculation."""
        p_value = calculator._calculate_theta_significance(mean_reverting_series)

        assert isinstance(p_value, float)
        assert 0.0 <= p_value <= 1.0

    def test_hurst_exponent_calculation(self, calculator, mean_reverting_series):
        """Test Hurst exponent calculation."""
        hurst = calculator._calculate_hurst_exponent(mean_reverting_series)

        # Mean-reverting series should have H < 0.5
        if hurst is not None:
            assert isinstance(hurst, float)
            assert 0.0 <= hurst <= 1.0

    def test_compare_half_lives(self, calculator):
        """Test comparing multiple half-life results."""
        np.random.seed(42)

        results = []
        for i in range(5):
            prices = np.random.randn(100) * 2 + 100
            result = calculator.calculate_half_life(prices)
            results.append(result)

        comparison = calculator.compare_half_lives(results)

        assert "count" in comparison
        assert "min_half_life" in comparison
        assert "max_half_life" in comparison
        assert "mean_half_life" in comparison


class TestHalfLifeResult:
    """Test HalfLifeResult dataclass."""

    def test_creation(self):
        """Test creating HalfLifeResult."""
        result = HalfLifeResult(
            half_life_days=10.5,
            half_life_hours=None,
            mean_reversion_rate=0.066,
            mean_level=100.0,
            mean_reversion_speed="fast",
            is_mean_reverting=True,
            p_value=0.001,
            confidence_interval=(8.0, 13.0),
            hurst_exponent=0.3,
            stationarity_test="stationary (p<0.01)",
        )

        assert result.half_life_days == 10.5
        assert result.mean_reversion_rate == 0.066
        assert result.is_mean_reverting
        assert result.mean_reversion_speed == "fast"


class TestOUProcessParams:
    """Test OUProcessParams dataclass."""

    def test_creation(self):
        """Test creating OUProcessParams."""
        params = OUProcessParams(
            theta=0.5,
            mu=100.0,
            sigma=2.0,
            half_life=1.386,  # ln(2) / 0.5
        )

        assert params.theta == 0.5
        assert params.mu == 100.0
        assert params.sigma == 2.0
        assert params.half_life == pytest.approx(1.386, rel=0.01)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_calculate_half_life_function(self):
        """Test calculate_half_life convenience function."""
        np.random.seed(42)
        prices = np.random.randn(100) * 2 + 100

        result = calculate_half_life(prices, data_frequency="D")

        assert isinstance(result, HalfLifeResult)

    def test_with_pandas_series(self):
        """Test with pandas Series input."""
        np.random.seed(42)
        prices = pd.Series(np.random.randn(100) * 2 + 100)

        result = calculate_half_life(prices, data_frequency="D")

        assert isinstance(result, HalfLifeResult)

    def test_with_list(self):
        """Test with list input."""
        np.random.seed(42)
        prices = list(np.random.randn(100) * 2 + 100)

        result = calculate_half_life(prices, data_frequency="D")

        assert isinstance(result, HalfLifeResult)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nan_values(self):
        """Test handling of NaN values."""
        calculator = HalfLifeCalculator()
        prices = np.array([100.0, np.nan, 102.0, np.nan, 101.0])

        result = calculator.calculate_half_life(prices)

        # Should handle NaNs gracefully
        assert isinstance(result, HalfLifeResult)

    def test_zero_variance(self):
        """Test handling of zero variance."""
        calculator = HalfLifeCalculator()
        prices = np.array([100.0] * 50)

        result = calculator.calculate_half_life(prices)

        # Should handle zero variance
        assert isinstance(result, HalfLifeResult)
        assert not result.is_mean_reverting

    def test_negative_prices(self):
        """Test handling of negative prices (invalid)."""
        calculator = HalfLifeCalculator()
        prices = np.array([100.0, 102.0, -50.0, 98.0, 101.0])

        result = calculator.calculate_half_life(prices)

        # Should still calculate (though results may be meaningless)
        assert isinstance(result, HalfLifeResult)
