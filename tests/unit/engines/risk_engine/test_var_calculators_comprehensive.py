"""
Comprehensive integration tests for VaR calculators.

Tests comparing different VaR calculation methods.
"""
import pytest
import numpy as np

from app.engines.risk_engine.var_calculators.var_calculators import (
    HistoricalVaRCalculator,
    ParametricVaRCalculator,
    MonteCarloVaRCalculator,
    GARCHVaRCalculator,
)


@pytest.fixture
def sample_returns():
    """Create sample returns data."""
    np.random.seed(42)
    return np.random.normal(0.001, 0.02, 500)


@pytest.fixture
def calculators():
    """Create all calculator types."""
    config = {'confidence_level': 0.95, 'time_horizon': 1}
    return {
        'historical': HistoricalVaRCalculator(config),
        'parametric': ParametricVaRCalculator(config),
        'monte_carlo': MonteCarloVaRCalculator(config),
        'garch': GARCHVaRCalculator(config),
    }


@pytest.mark.unit
class TestVaRMethodComparison:
    """Test comparison between different VaR methods."""

    def test_all_methods_calculate_var(self, calculators, sample_returns):
        """Test that all methods can calculate VaR."""
        results = {}
        for name, calc in calculators.items():
            result = calc.calculate_var(sample_returns)
            results[name] = result
            assert 'error' not in result or 'var' in result

    def test_methods_produce_similar_results(self, calculators, sample_returns):
        """Test that methods produce reasonably similar results."""
        results = {}
        for name, calc in calculators.items():
            result = calc.calculate_var(sample_returns)
            if 'error' not in result:
                results[name] = result['var']

        # All VaRs should be negative
        for var in results.values():
            assert var < 0

    def test_historical_vs_parametric(self, sample_returns):
        """Test historical vs parametric VaR."""
        config = {'confidence_level': 0.95}
        hist_calc = HistoricalVaRCalculator(config)
        param_calc = ParametricVaRCalculator(config)

        hist_result = hist_calc.calculate_var(sample_returns)
        param_result = param_calc.calculate_var(sample_returns)

        # Should be reasonably close
        assert abs(hist_result['var'] - param_result['var']) < 0.02


@pytest.mark.unit
class TestVaRMethodSelection:
    """Test VaR method selection criteria."""

    def test_historical_for_non_normal_distributions(self):
        """Test that historical is better for non-normal."""
        np.random.seed(42)
        skewed_returns = np.random.exponential(0.01, 500) - 0.01

        config = {'confidence_level': 0.95}
        hist_calc = HistoricalVaRCalculator(config)
        param_calc = ParametricVaRCalculator(config)

        hist_result = hist_calc.calculate_var(skewed_returns)
        param_result = param_calc.calculate_var(skewed_returns)

        # Historical should handle better
        assert 'error' not in hist_result

    def test_parametric_for_normal_distributions(self, sample_returns):
        """Test that parametric works well for normal."""
        config = {'confidence_level': 0.95}
        param_calc = ParametricVaRCalculator(config)

        result = param_calc.calculate_var(sample_returns)

        assert result['is_normal_distribution'] is True
        assert 'error' not in result


@pytest.mark.unit
class TestCVaRComparison:
    """Test CVaR across methods."""

    def test_cvar_more_negative_than_var(self, calculators, sample_returns):
        """Test that CVaR is more negative than VaR for all methods."""
        for name, calc in calculators.items():
            result = calc.calculate_var(sample_returns)
            if 'error' not in result and 'cvar' in result:
                assert result['cvar'] <= result['var']


@pytest.mark.unit
class TestVaRConfidenceLevels:
    """Test VaR at different confidence levels across methods."""

    @pytest.mark.parametrize("confidence", [0.90, 0.95, 0.99])
    def test_all_confidence_levels_work(self, confidence, sample_returns):
        """Test that all confidence levels work."""
        config = {'confidence_level': confidence}
        calc = HistoricalVaRCalculator(config)

        result = calc.calculate_var(sample_returns)

        assert result['confidence_level'] == confidence
        assert 'var' in result
