"""
Unit tests for Component VaR Calculator.

Tests for component VaR and risk contribution calculations.
"""

import numpy as np
import pytest

from app.engines.risk_engine.var_calculators.component_var import ComponentVaRCalculator


@pytest.fixture
def sample_portfolio_returns():
    """Create sample portfolio returns."""
    np.random.seed(42)
    return {
        'AAPL': np.random.normal(0.001, 0.02, 500),
        'MSFT': np.random.normal(0.0008, 0.018, 500),
        'GOOGL': np.random.normal(0.0012, 0.022, 500),
    }


@pytest.fixture
def sample_weights():
    """Create sample portfolio weights."""
    return np.array([0.4, 0.35, 0.25])


@pytest.fixture
def calculator():
    """Create ComponentVaRCalculator instance."""
    return ComponentVaRCalculator({'confidence_level': 0.95})


@pytest.mark.unit
class TestComponentVaRCalculator:
    """Test component VaR calculation."""

    def test_calculate_component_var(self, calculator, sample_portfolio_returns, sample_weights):
        """Test component VaR calculation."""
        result = calculator.calculate_component_var(sample_portfolio_returns, sample_weights)

        assert 'error' not in result
        assert 'total_var' in result
        assert 'component_vars' in result

    def test_component_var_sum_to_total(self, calculator, sample_portfolio_returns, sample_weights):
        """Test that component VaRs sum to total VaR."""
        result = calculator.calculate_component_var(sample_portfolio_returns, sample_weights)

        if 'component_vars' in result:
            component_sum = sum(result['component_vars'].values())
            # Components should approximately sum to total
            assert abs(component_sum - abs(result['total_var'])) < 0.01

    def test_marginal_var_calculation(self, calculator, sample_portfolio_returns, sample_weights):
        """Test marginal VaR calculation."""
        result = calculator.calculate_component_var(sample_portfolio_returns, sample_weights)

        if 'marginal_vars' in result:
            assert len(result['marginal_vars']) == len(sample_weights)
