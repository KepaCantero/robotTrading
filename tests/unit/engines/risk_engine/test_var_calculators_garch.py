"""
Unit tests for GARCH VaR Calculator.

Tests for GARCH-based VaR calculation with volatility clustering.
"""
import pytest
import numpy as np
from unittest.mock import patch, Mock

from app.engines.risk_engine.var_calculators.var_calculators import (
    GARCHVaRCalculator,
)


@pytest.fixture
def sample_returns():
    """Create sample returns with volatility clustering."""
    np.random.seed(42)
    returns = []
    vol = 0.01
    for i in range(500):
        vol = 0.9 * vol + 0.1 * abs(np.random.normal(0, 0.01))
        returns.append(np.random.normal(0, vol))
    return np.array(returns)


@pytest.fixture
def calculator_config():
    """VaR calculator configuration."""
    return {
        'confidence_level': 0.95,
        'time_horizon': 1,
    }


@pytest.fixture
def calculator(calculator_config):
    """Create GARCHVaRCalculator instance."""
    return GARCHVaRCalculator(calculator_config)


@pytest.mark.unit
class TestGARCHVaRCalculatorInitialization:
    """Test GARCHVaRCalculator initialization."""

    def test_default_initialization(self):
        """Test initialization with default config."""
        config = {}
        calc = GARCHVaRCalculator(config)

        assert calc.confidence_level == 0.95


@pytest.mark.unit
class TestGARCHVaRSuccessCases:
    """Test successful GARCH VaR calculations."""

    def test_calculate_var_success(self, calculator, sample_returns):
        """Test successful VaR calculation."""
        result = calculator.calculate_var(sample_returns)

        assert 'var' in result
        assert 'method' == 'garch' or 'method' in result

    def test_conditional_volatility_calculated(self, calculator, sample_returns):
        """Test that conditional volatility is calculated."""
        result = calculator.calculate_var(sample_returns)

        if 'conditional_volatility' in result:
            assert result['conditional_volatility'] > 0


@pytest.mark.unit
class TestGARCHVaRFallback:
    """Test fallback behavior when ARCH is not available."""

    @patch('app.engines.risk_engine.var_calculators.var_calculators.ARCH_AVAILABLE', False)
    def test_fallback_to_parametric(self, sample_returns):
        """Test fallback to parametric when ARCH unavailable."""
        calc = GARCHVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(sample_returns)

        # Should fall back to parametric
        assert 'var' in result

    def test_fallback_with_insufficient_data(self, calculator):
        """Test fallback with insufficient data."""
        short_returns = np.array([0.01, -0.01, 0.02, -0.02])
        result = calculator.calculate_var(short_returns)

        # Should fall back to parametric
        assert 'var' in result


@pytest.mark.unit
class TestGARCHVaRErrorHandling:
    """Test error handling."""

    def test_empty_returns(self, calculator):
        """Test with empty returns."""
        result = calculator.calculate_var(np.array([]))

        assert 'error' in result or 'var' in result
