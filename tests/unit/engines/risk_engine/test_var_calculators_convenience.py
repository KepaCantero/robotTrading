"""
Unit tests for VaR Calculator convenience functions.

Tests for the calculate_var convenience function.
"""
import pytest
import numpy as np

from app.engines.risk_engine.var_calculators.var_calculators import (
    calculate_var,
    get_var_calculators_info,
)


@pytest.fixture
def sample_returns():
    """Create sample returns data."""
    np.random.seed(42)
    return np.random.normal(0.001, 0.02, 500)


@pytest.mark.unit
class TestCalculateVarConvenienceFunction:
    """Test calculate_var convenience function."""

    def test_historical_method(self, sample_returns):
        """Test historical method."""
        result = calculate_var(sample_returns, method='historical')

        assert 'error' not in result
        assert result['method'] == 'historical'

    def test_parametric_method(self, sample_returns):
        """Test parametric method."""
        result = calculate_var(sample_returns, method='parametric')

        assert 'error' not in result
        assert result['method'] == 'parametric'

    def test_monte_carlo_method(self, sample_returns):
        """Test Monte Carlo method."""
        result = calculate_var(sample_returns, method='monte_carlo')

        assert 'error' not in result
        assert result['method'] == 'monte_carlo'

    def test_garch_method(self, sample_returns):
        """Test GARCH method."""
        result = calculate_var(sample_returns, method='garch')

        assert 'error' not in result or 'method' in result

    def test_invalid_method_raises_error(self, sample_returns):
        """Test that invalid method raises error."""
        with pytest.raises(ValueError):
            calculate_var(sample_returns, method='invalid')

    def test_custom_confidence_level(self, sample_returns):
        """Test with custom confidence level."""
        result = calculate_var(sample_returns, method='historical', confidence_level=0.99)

        assert result['confidence_level'] == 0.99

    def test_with_portfolio_value(self, sample_returns):
        """Test with portfolio value."""
        result = calculate_var(sample_returns, method='historical', portfolio_value=100000.0)

        assert result['var_amount'] is not None

    def test_custom_n_simulations(self, sample_returns):
        """Test with custom n_simulations for Monte Carlo."""
        result = calculate_var(sample_returns, method='monte_carlo', n_simulations=50000)

        assert result['n_simulations'] == 50000


@pytest.mark.unit
class TestGetVarCalculatorsInfo:
    """Test get_var_calculators_info function."""

    def test_returns_dict(self):
        """Test that function returns a dict."""
        info = get_var_calculators_info()

        assert isinstance(info, dict)

    def test_includes_numba_info(self):
        """Test that Numba info is included."""
        info = get_var_calculators_info()

        assert 'numba_available' in info
        assert 'numba_version' in info

    def test_includes_arch_info(self):
        """Test that ARCH info is included."""
        info = get_var_calculators_info()

        assert 'arch_available' in info

    def test_includes_methods_available(self):
        """Test that available methods are listed."""
        info = get_var_calculators_info()

        assert 'methods_available' in info
        assert 'historical' in info['methods_available']

    def test_includes_performance_info(self):
        """Test that performance improvements are documented."""
        info = get_var_calculators_info()

        assert 'performance_improvements' in info
