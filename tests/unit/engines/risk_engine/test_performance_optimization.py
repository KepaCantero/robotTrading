"""
Performance tests for Risk Engine components.

Tests that verify Numba acceleration and performance characteristics.
"""
import pytest
import numpy as np
import time

from app.engines.risk_engine.var_calculators.var_calculators import (
    HistoricalVaRCalculator,
    ParametricVaRCalculator,
    MonteCarloVaRCalculator,
    calculate_percentile_numba,
    calculate_mean_std_numba,
)


@pytest.mark.unit
class TestNumbaAcceleration:
    """Test Numba acceleration is working."""

    def test_percentile_performance(self):
        """Test that percentile calculation is fast."""
        data = np.random.normal(0, 0.02, 10000)

        start = time.time()
        for _ in range(100):
            result = calculate_percentile_numba(data, 5)
        elapsed = time.time() - start

        # Should complete 100 iterations in reasonable time
        assert elapsed < 5.0

    def test_mean_std_performance(self):
        """Test that mean/std calculation is fast."""
        data = np.random.normal(0, 0.02, 10000)

        start = time.time()
        for _ in range(100):
            mean, std = calculate_mean_std_numba(data)
        elapsed = time.time() - start

        # Should complete 100 iterations in reasonable time
        assert elapsed < 5.0


@pytest.mark.unit
class TestVaRCalculationPerformance:
    """Test VaR calculation performance."""

    def test_historical_var_performance(self):
        """Test historical VaR calculation speed."""
        returns = np.random.normal(0, 0.02, 10000)
        calc = HistoricalVaRCalculator({'confidence_level': 0.95})

        start = time.time()
        for _ in range(10):
            result = calc.calculate_var(returns)
        elapsed = time.time() - start

        # Should complete 10 calculations in reasonable time
        assert elapsed < 3.0

    def test_parametric_var_performance(self):
        """Test parametric VaR calculation speed."""
        returns = np.random.normal(0, 0.02, 10000)
        calc = ParametricVaRCalculator({'confidence_level': 0.95})

        start = time.time()
        for _ in range(10):
            result = calc.calculate_var(returns)
        elapsed = time.time() - start

        # Should complete 10 calculations in reasonable time
        assert elapsed < 3.0


@pytest.mark.unit
class TestMonteCarloPerformance:
    """Test Monte Carlo calculation performance."""

    def test_monte_carlo_with_parallel_processing(self):
        """Test Monte Carlo with parallel processing."""
        returns = np.random.normal(0, 0.02, 500)
        calc = MonteCarloVaRCalculator({
            'confidence_level': 0.95,
            'n_simulations': 10000,
        })

        start = time.time()
        result = calc.calculate_var(returns)
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 10.0
        assert 'error' not in result


@pytest.mark.unit
class TestNumbaFlags:
    """Test Numba acceleration flags."""

    def test_historical_var_numba_flag(self):
        """Test that historical VaR reports Numba acceleration."""
        returns = np.random.normal(0, 0.02, 1000)
        calc = HistoricalVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(returns)

        assert 'numba_accelerated' in result

    def test_parametric_var_numba_flag(self):
        """Test that parametric VaR reports Numba acceleration."""
        returns = np.random.normal(0, 0.02, 1000)
        calc = ParametricVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(returns)

        assert 'numba_accelerated' in result

    def test_monte_carlo_numba_flag(self):
        """Test that Monte Carlo VaR reports Numba acceleration."""
        returns = np.random.normal(0, 0.02, 1000)
        calc = MonteCarloVaRCalculator({
            'confidence_level': 0.95,
            'n_simulations': 10000,
        })
        result = calc.calculate_var(returns)

        assert 'numba_accelerated' in result
        assert 'parallel_processing' in result
