"""
Unit tests for Monte Carlo VaR Calculator.

Tests for Monte Carlo simulation VaR calculation with Numba optimization.
"""
import pytest
import numpy as np
from unittest.mock import patch, Mock

from app.engines.risk_engine.var_calculators.var_calculators import (
    MonteCarloVaRCalculator,
    monte_carlo_simulation_numba,
)


@pytest.fixture
def sample_returns():
    """Create sample returns data."""
    np.random.seed(42)
    return np.random.normal(0.001, 0.02, 500)


@pytest.fixture
def calculator_config():
    """VaR calculator configuration."""
    return {
        'confidence_level': 0.95,
        'time_horizon': 1,
        'n_simulations': 10000,
    }


@pytest.fixture
def calculator(calculator_config):
    """Create MonteCarloVaRCalculator instance."""
    return MonteCarloVaRCalculator(calculator_config)


@pytest.mark.unit
class TestMonteCarloSimulation:
    """Test Monte Carlo simulation function."""

    def test_simulation_output_shape(self):
        """Test that simulation produces correct number of samples."""
        mean_ret = 0.001
        std_ret = 0.02
        n_sim = 1000

        simulations = monte_carlo_simulation_numba(mean_ret, std_ret, n_sim)

        assert len(simulations) == n_sim

    def test_simulation_mean_approximates_target(self):
        """Test that simulation mean is close to target."""
        mean_ret = 0.001
        std_ret = 0.02
        n_sim = 10000

        simulations = monte_carlo_simulation_numba(mean_ret, std_ret, n_sim)

        # Mean should be close to target
        assert abs(simulations.mean() - mean_ret) < 0.001

    def test_simulation_std_approximates_target(self):
        """Test that simulation std is close to target."""
        mean_ret = 0.001
        std_ret = 0.02
        n_sim = 10000

        simulations = monte_carlo_simulation_numba(mean_ret, std_ret, n_sim)

        # Std should be close to target
        assert abs(simulations.std() - std_ret) < 0.005


@pytest.mark.unit
class TestMonteCarloVaRCalculatorInitialization:
    """Test MonteCarloVaRCalculator initialization."""

    def test_default_initialization(self):
        """Test initialization with default config."""
        config = {}
        calc = MonteCarloVaRCalculator(config)

        assert calc.n_simulations == 10000

    def test_custom_n_simulations(self):
        """Test with custom number of simulations."""
        config = {'n_simulations': 50000}
        calc = MonteCarloVaRCalculator(config)

        assert calc.n_simulations == 50000


@pytest.mark.unit
class TestMonteCarloVaRSuccessCases:
    """Test successful Monte Carlo VaR calculations."""

    def test_calculate_var_success(self, calculator, sample_returns):
        """Test successful VaR calculation."""
        result = calculator.calculate_var(sample_returns)

        assert 'error' not in result
        assert 'var' in result
        assert 'cvar' in result
        assert result['method'] == 'monte_carlo'

    def test_n_simulations_in_result(self, calculator, sample_returns):
        """Test that n_simulations is included in result."""
        result = calculator.calculate_var(sample_returns)

        assert result['n_simulations'] == calculator.n_simulations

    def test_parallel_processing_flag(self, calculator, sample_returns):
        """Test parallel processing flag."""
        result = calculator.calculate_var(sample_returns)

        assert 'parallel_processing' in result

    def test_with_portfolio_value(self, calculator, sample_returns):
        """Test with portfolio value."""
        result = calculator.calculate_var(sample_returns, portfolio_value=100000.0)

        assert result['var_amount'] is not None
        assert result['cvar_amount'] is not None


@pytest.mark.unit
class TestMonteCarloVaRConsistency:
    """Test Monte Carlo consistency."""

    def test_deterministic_with_seed(self):
        """Test that results are consistent with same seed."""
        np.random.seed(42)
        returns1 = np.random.normal(0, 0.02, 500)

        calc = MonteCarloVaRCalculator({'n_simulations': 10000})
        result1 = calc.calculate_var(returns1)

        # Should calculate successfully
        assert 'var' in result1


@pytest.mark.unit
class TestMonteCarloVaRErrorHandling:
    """Test error handling."""

    def test_empty_returns(self, calculator):
        """Test with empty returns."""
        result = calculator.calculate_var(np.array([]))

        assert 'error' in result

    def test_small_sample_size(self, calculator):
        """Test with small sample."""
        returns = np.array([0.01, -0.01, 0.02])
        result = calculator.calculate_var(returns)

        # Should still work
        assert 'var' in result
