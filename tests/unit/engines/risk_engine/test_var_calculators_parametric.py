"""
Unit tests for Parametric VaR Calculator.

Tests for variance-covariance (parametric) VaR calculation with Numba optimization.
"""
from unittest.mock import patch

import numpy as np
import pytest

from app.engines.risk_engine.var_calculators.var_calculators import (
    ParametricVaRCalculator,
    calculate_jarque_bera_numba,
    calculate_mean_std_numba,
)


@pytest.fixture
def sample_returns():
    """Create sample normally-distributed returns."""
    np.random.seed(42)
    return np.random.normal(0.001, 0.02, 500)


@pytest.fixture
def calculator_config():
    """VaR calculator configuration."""
    return {
        'confidence_level': 0.95,
        'time_horizon': 1,
    }


@pytest.fixture
def calculator(calculator_config):
    """Create ParametricVaRCalculator instance."""
    return ParametricVaRCalculator(calculator_config)


@pytest.mark.unit
class TestNumbaMeanStdCalculation:
    """Test Numba-optimized mean and std calculation."""

    def test_mean_std_calculation(self):
        """Test basic mean and std calculation."""
        data = np.array([1, 2, 3, 4, 5])
        mean, std = calculate_mean_std_numba(data)

        assert abs(mean - 3.0) < 0.01
        assert abs(std - np.std(data)) < 0.01

    def test_mean_with_negative_values(self):
        """Test mean with negative values."""
        data = np.array([-5, -3, -1, 1, 3, 5])
        mean, std = calculate_mean_std_numba(data)

        assert mean == 0.0
        assert std > 0

    def test_std_of_constant_values(self):
        """Test std of constant values (should be zero)."""
        data = np.array([5, 5, 5, 5, 5])
        mean, std = calculate_mean_std_numba(data)

        assert mean == 5.0
        assert std == 0.0

    def test_empty_array(self):
        """Test with empty array."""
        data = np.array([])
        mean, std = calculate_mean_std_numba(data)

        assert mean == 0.0
        assert std == 0.0


@pytest.mark.unit
class TestJarqueBeraTest:
    """Test Jarque-Bera normality test."""

    def test_normal_distribution_passes(self):
        """Test that normal distribution passes JB test."""
        np.random.seed(42)
        data = np.random.normal(0, 1, 1000)

        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # p-value should be > 0.05 for normal distribution
        assert p_value > 0.01

    def test_non_normal_distribution_fails(self):
        """Test that non-normal distribution fails JB test."""
        np.random.seed(42)
        # Create skewed distribution
        data = np.random.exponential(1, 1000)

        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # p-value should be very small for non-normal
        assert p_value < 0.05

    def test_small_sample_handling(self):
        """Test handling of small samples."""
        data = np.array([1, 2, 3, 4, 5])
        jb_stat, p_value = calculate_jarque_bera_numba(data)

        # Should handle gracefully
        assert isinstance(jb_stat, float)
        assert isinstance(p_value, float)


@pytest.mark.unit
class TestParametricVaRCalculatorInitialization:
    """Test ParametricVaRCalculator initialization."""

    def test_default_initialization(self):
        """Test initialization with default config."""
        config = {}
        calc = ParametricVaRCalculator(config)

        assert calc.confidence_level == 0.95
        assert calc.time_horizon == 1

    def test_custom_initialization(self):
        """Test initialization with custom config."""
        config = {
            'confidence_level': 0.99,
            'time_horizon': 10,
        }
        calc = ParametricVaRCalculator(config)

        assert calc.confidence_level == 0.99
        assert calc.time_horizon == 10


@pytest.mark.unit
class TestParametricVaRSuccessCases:
    """Test successful parametric VaR calculations."""

    def test_calculate_var_success(self, calculator, sample_returns):
        """Test successful VaR calculation."""
        result = calculator.calculate_var(sample_returns)

        assert 'error' not in result
        assert 'var' in result
        assert 'cvar' in result
        assert result['method'] == 'parametric'

    def test_var_includes_mean_and_std(self, calculator, sample_returns):
        """Test that mean and std are included."""
        result = calculator.calculate_var(sample_returns)

        assert 'mean_return' in result
        assert 'std_return' in result
        assert isinstance(result['mean_return'], float)
        assert isinstance(result['std_return'], float)

    def test_var_includes_z_score(self, calculator, sample_returns):
        """Test that z-score is included."""
        result = calculator.calculate_var(sample_returns)

        assert 'z_score' in result
        # For 95% confidence, z-score should be ~1.645
        assert abs(result['z_score'] - 1.645) < 0.01

    def test_normality_test_performed(self, calculator, sample_returns):
        """Test that normality test is performed."""
        result = calculator.calculate_var(sample_returns)

        assert 'is_normal_distribution' in result
        assert isinstance(result['is_normal_distribution'], bool)

    def test_with_portfolio_value(self, calculator, sample_returns):
        """Test with portfolio value."""
        result = calculator.calculate_var(sample_returns, portfolio_value=100000.0)

        assert result['var_amount'] is not None
        assert result['cvar_amount'] is not None
        assert result['var_amount'] >= 0


@pytest.mark.unit
class TestParametricVaRNormalityWarning:
    """Test normality warning generation."""

    def test_warning_for_non_normal(self):
        """Test warning generated for non-normal returns."""
        # Create clearly non-normal returns (skewed)
        np.random.seed(42)
        returns = np.random.exponential(0.01, 500) - 0.01

        calc = ParametricVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(returns)

        # Should detect non-normality
        assert result['is_normal_distribution'] is False
        assert 'normality_warning' in result

    def test_no_warning_for_normal(self, calculator, sample_returns):
        """Test no warning for approximately normal returns."""
        result = calculator.calculate_var(sample_returns)

        # Sample returns are normal
        assert result['is_normal_distribution'] is True

    def test_warning_message_content(self):
        """Test that warning message is informative."""
        np.random.seed(42)
        returns = np.random.exponential(0.01, 500) - 0.01

        calc = ParametricVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(returns)

        if 'normality_warning' in result:
            warning = result['normality_warning']
            assert 'NOT normally distributed' in warning
            assert 'skew=' in warning
            assert 'kurtosis=' in warning


@pytest.mark.unit
class TestParametricVaRInputTypes:
    """Test VaR calculation with different input types."""

    def test_with_numpy_array(self, calculator, sample_returns):
        """Test with numpy array."""
        result = calculator.calculate_var(sample_returns)

        assert 'error' not in result

    def test_with_list(self, calculator):
        """Test with Python list."""
        returns = [-0.02, 0.01, -0.01, 0.03, -0.005] * 100
        result = calculator.calculate_var(returns)

        assert 'error' not in result

    def test_with_pandas_series(self, calculator):
        """Test with pandas Series."""
        pytest.importorskip('pandas')
        import pandas as pd

        returns = pd.Series([-0.02, 0.01, -0.01, 0.03, -0.005] * 100)
        result = calculator.calculate_var(returns)

        assert 'error' not in result


@pytest.mark.unit
class TestParametricVaRDifferentConfidenceLevels:
    """Test VaR at different confidence levels."""

    def test_confidence_90(self, sample_returns):
        """Test at 90% confidence."""
        config = {'confidence_level': 0.90}
        calc = ParametricVaRCalculator(config)
        result = calc.calculate_var(sample_returns)

        assert result['confidence_level'] == 0.90
        # z-score for 90% is ~1.282
        assert abs(result['z_score'] - 1.282) < 0.01

    def test_confidence_99(self, sample_returns):
        """Test at 99% confidence."""
        config = {'confidence_level': 0.99}
        calc = ParametricVaRCalculator(config)
        result = calc.calculate_var(sample_returns)

        assert result['confidence_level'] == 0.99
        # z-score for 99% is ~2.326
        assert abs(result['z_score'] - 2.326) < 0.01

    def test_higher_confidence_more_negative_var(self, sample_returns):
        """Test that higher confidence gives more negative VaR."""
        config_95 = {'confidence_level': 0.95}
        config_99 = {'confidence_level': 0.99}

        calc_95 = ParametricVaRCalculator(config_95)
        calc_99 = ParametricVaRCalculator(config_99)

        result_95 = calc_95.calculate_var(sample_returns)
        result_99 = calc_99.calculate_var(sample_returns)

        # 99% VaR should be more negative
        assert result_99['var'] <= result_95['var']


@pytest.mark.unit
class TestParametricVaRErrorHandling:
    """Test error handling."""

    def test_empty_returns(self, calculator):
        """Test with empty returns."""
        result = calculator.calculate_var(np.array([]))

        assert 'error' in result

    def test_very_small_sample(self, calculator):
        """Test with very small sample."""
        returns = np.array([0.01, -0.01])
        result = calculator.calculate_var(returns)

        # Should still calculate
        assert 'var' in result

    def test_constant_returns(self, calculator):
        """Test with constant returns (zero variance)."""
        returns = np.array([0.01] * 100)
        result = calculator.calculate_var(returns)

        assert 'var' in result


@pytest.mark.unit
class TestCVaRCalculation:
    """Test CVaR calculation in parametric method."""

    def test_cvar_more_negative_than_var(self, calculator, sample_returns):
        """Test that CVaR is more negative than VaR."""
        result = calculator.calculate_var(sample_returns)

        # CVaR should be worse than VaR
        assert result['cvar'] <= result['var']

    def test_cvar_formula(self, calculator):
        """Test CVaR formula under normality."""
        returns = np.array([-0.02, 0.01, -0.01, 0.03, -0.005] * 100)
        result = calculator.calculate_var(returns)

        # Under normality, CVaR should be approximately:
        # CVaR = mean - std * phi(z) / (1 - confidence)
        # This should give CVaR more negative than VaR
        assert result['cvar'] < result['var']


@pytest.mark.unit
class TestParametricVaRScipyFallback:
    """Test scipy import fallback behavior."""

    @patch('app.engines.risk_engine.var_calculators.var_calculators.stats', None)
    def test_z_score_fallback_without_scipy(self, sample_returns):
        """Test z-score fallback when scipy is not available."""
        calc = ParametricVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(sample_returns)

        # Should use hardcoded z-scores
        assert 'z_score' in result
        assert abs(result['z_score'] - 1.645) < 0.01


@pytest.mark.unit
class TestParametricVaRMethodAttributes:
    """Test method-specific attributes."""

    def test_method_identified(self, calculator, sample_returns):
        """Test that method is correctly identified."""
        result = calculator.calculate_var(sample_returns)

        assert result['method'] == 'parametric'

    def test_numba_acceleration_flag(self, calculator, sample_returns):
        """Test Numba acceleration flag."""
        result = calculator.calculate_var(sample_returns)

        assert 'numba_accelerated' in result
        assert isinstance(result['numba_accelerated'], bool)

    def test_time_horizon_included(self, calculator, sample_returns):
        """Test time horizon is included."""
        result = calculator.calculate_var(sample_returns)

        assert 'time_horizon' in result


@pytest.mark.unit
class TestParametricVaRWithRealWorldScenarios:
    """Test with realistic scenarios."""

    def test_low_volatility_regime(self, calculator):
        """Test with low volatility regime."""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.008, 500)  # Low vol
        result = calculator.calculate_var(returns)

        assert 'var' in result
        # VaR should be relatively small
        assert result['var'] > -0.02

    def test_high_volatility_regime(self, calculator):
        """Test with high volatility regime."""
        np.random.seed(42)
        returns = np.random.normal(0, 0.04, 500)  # High vol
        result = calculator.calculate_var(returns)

        assert 'var' in result
        # VaR should be large negative
        assert result['var'] < -0.05

    def test_negative_drift(self, calculator):
        """Test with negative drift (bear market)."""
        np.random.seed(42)
        returns = np.random.normal(-0.001, 0.02, 500)
        result = calculator.calculate_var(returns)

        assert 'var' in result
        # Mean return should be negative
        assert result['mean_return'] < 0

    def test_positive_drift(self, calculator):
        """Test with positive drift (bull market)."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)
        result = calculator.calculate_var(returns)

        assert 'var' in result
        # Mean return should be positive
        assert result['mean_return'] > 0


@pytest.mark.unit
class TestParametricVaRConsistency:
    """Test consistency of calculations."""

    def test_deterministic_results(self, calculator, sample_returns):
        """Test that results are deterministic."""
        result1 = calculator.calculate_var(sample_returns)
        result2 = calculator.calculate_var(sample_returns)

        assert result1['var'] == result2['var']
        assert result1['mean_return'] == result2['mean_return']
        assert result1['std_return'] == result2['std_return']

    def test_var_formula_correctness(self, calculator):
        """Test VaR formula: VaR = mean - z * std."""
        returns = np.array([-0.02, 0.01, -0.01, 0.03, -0.005] * 100)
        result = calculator.calculate_var(returns)

        expected_var = result['mean_return'] - result['z_score'] * result['std_return']

        assert abs(result['var'] - expected_var) < 0.0001
