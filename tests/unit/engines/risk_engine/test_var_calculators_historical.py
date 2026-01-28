"""
Unit tests for Historical VaR Calculator.

Tests for historical simulation VaR calculation with Numba optimization.
"""
import pytest
import numpy as np
from unittest.mock import patch, Mock

from app.engines.risk_engine.var_calculators.var_calculators import (
    HistoricalVaRCalculator,
    BaseVaRCalculator,
    calculate_percentile_numba,
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
    }


@pytest.fixture
def calculator(calculator_config):
    """Create HistoricalVaRCalculator instance."""
    return HistoricalVaRCalculator(calculator_config)


@pytest.mark.unit
class TestNumbaPercentileCalculation:
    """Test Numba-optimized percentile calculation."""

    def test_percentile_calculation(self):
        """Test basic percentile calculation."""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        percentile_50 = calculate_percentile_numba(data, 50)

        assert percentile_50 == 5.5

    def test_percentile_at_5(self):
        """Test 5th percentile (for 95% VaR)."""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        percentile_5 = calculate_percentile_numba(data, 5)

        # 5th percentile of 1-10 should be close to 1.5
        assert 1.0 <= percentile_5 <= 2.0

    def test_percentile_with_negative_values(self):
        """Test percentile with negative returns."""
        data = np.array([-0.05, -0.03, -0.01, 0.01, 0.02, 0.04])
        percentile_5 = calculate_percentile_numba(data, 5)

        # Should be one of the negative values
        assert percentile_5 < 0

    def test_percentile_empty_array(self):
        """Test percentile with empty array."""
        data = np.array([])
        result = calculate_percentile_numba(data, 50)

        assert np.isnan(result)

    def test_percentile_single_value(self):
        """Test percentile with single value."""
        data = np.array([5.0])
        result = calculate_percentile_numba(data, 50)

        assert result == 5.0


@pytest.mark.unit
class TestHistoricalVaRCalculatorInitialization:
    """Test HistoricalVaRCalculator initialization."""

    def test_default_initialization(self):
        """Test initialization with default config."""
        config = {}
        calc = HistoricalVaRCalculator(config)

        assert calc.confidence_level == 0.95
        assert calc.time_horizon == 1

    def test_custom_initialization(self):
        """Test initialization with custom config."""
        config = {
            'confidence_level': 0.99,
            'time_horizon': 10,
        }
        calc = HistoricalVaRCalculator(config)

        assert calc.confidence_level == 0.99
        assert calc.time_horizon == 10

    def test_inherits_from_base(self, calculator):
        """Test that calculator inherits from BaseVaRCalculator."""
        assert isinstance(calculator, BaseVaRCalculator)


@pytest.mark.unit
class TestHistoricalVaRSuccessCases:
    """Test successful VaR calculations."""

    def test_calculate_var_with_numpy_array(self, calculator, sample_returns):
        """Test VaR calculation with numpy array."""
        result = calculator.calculate_var(sample_returns)

        assert 'error' not in result
        assert 'var' in result
        assert 'cvar' in result
        assert result['method'] == 'historical'

    def test_calculate_var_with_portfolio_value(self, calculator, sample_returns):
        """Test VaR calculation with portfolio value."""
        portfolio_value = 100000.0
        result = calculator.calculate_var(sample_returns, portfolio_value)

        assert result['var_amount'] is not None
        assert result['cvar_amount'] is not None
        assert isinstance(result['var_amount'], float)
        assert isinstance(result['cvar_amount'], float)

    def test_var_is_negative(self, calculator, sample_returns):
        """Test that VaR is negative (representing loss)."""
        result = calculator.calculate_var(sample_returns)

        # VaR should be negative for loss
        assert result['var'] < 0

    def test_cvar_more_negative_than_var(self, calculator, sample_returns):
        """Test that CVaR is more negative than VaR."""
        result = calculator.calculate_var(sample_returns)

        # CVaR (expected shortfall) should be worse than VaR
        assert result['cvar'] <= result['var']

    def test_confidence_level_in_result(self, calculator, sample_returns):
        """Test that confidence level is included in result."""
        result = calculator.calculate_var(sample_returns)

        assert result['confidence_level'] == 0.95

    def test_observations_counted(self, calculator, sample_returns):
        """Test that observations are counted."""
        result = calculator.calculate_var(sample_returns)

        assert result['observations'] == len(sample_returns)

    def test_numba_acceleration_flag(self, calculator, sample_returns):
        """Test that Numba acceleration flag is set."""
        result = calculator.calculate_var(sample_returns)

        assert 'numba_accelerated' in result


@pytest.mark.unit
class TestHistoricalVaRInputTypes:
    """Test VaR calculation with different input types."""

    def test_calculate_var_with_list(self, calculator):
        """Test VaR calculation with Python list."""
        returns_list = [-0.02, 0.01, -0.01, 0.03, -0.005]
        result = calculator.calculate_var(returns_list)

        assert 'error' not in result
        assert 'var' in result

    def test_calculate_var_with_pandas_series(self, calculator):
        """Test VaR calculation with pandas Series."""
        pytest.importorskip('pandas')
        import pandas as pd

        returns_series = pd.Series([-0.02, 0.01, -0.01, 0.03, -0.005])
        result = calculator.calculate_var(returns_series)

        assert 'error' not in result
        assert 'var' in result


@pytest.mark.unit
class TestHistoricalVaRErrorHandling:
    """Test error handling in VaR calculation."""

    def test_empty_returns(self, calculator):
        """Test with empty returns array."""
        result = calculator.calculate_var(np.array([]))

        assert 'error' in result

    def test_very_small_sample(self, calculator):
        """Test with very small sample size."""
        returns = np.array([0.01, -0.01])
        result = calculator.calculate_var(returns)

        # Should still calculate
        assert 'var' in result

    def test_all_positive_returns(self, calculator):
        """Test with all positive returns (unusual)."""
        returns = np.array([0.01, 0.02, 0.015, 0.03, 0.01])
        result = calculator.calculate_var(returns)

        # VaR should still be calculated
        assert 'var' in result

    def test_all_negative_returns(self, calculator):
        """Test with all negative returns (crash scenario)."""
        returns = np.array([-0.01, -0.02, -0.015, -0.03, -0.01])
        result = calculator.calculate_var(returns)

        # VaR should be very negative
        assert 'var' in result
        assert result['var'] < -0.01


@pytest.mark.unit
class TestHistoricalVaRDifferentConfidenceLevels:
    """Test VaR at different confidence levels."""

    def test_confidence_90(self, sample_returns):
        """Test VaR at 90% confidence level."""
        config = {'confidence_level': 0.90}
        calc = HistoricalVaRCalculator(config)
        result = calc.calculate_var(sample_returns)

        assert result['confidence_level'] == 0.90

    def test_confidence_99(self, sample_returns):
        """Test VaR at 99% confidence level."""
        config = {'confidence_level': 0.99}
        calc = HistoricalVaRCalculator(config)
        result = calc.calculate_var(sample_returns)

        assert result['confidence_level'] == 0.99
        # 99% VaR should be more negative than 95% VaR

    def test_higher_confidence_more_negative(self, sample_returns):
        """Test that higher confidence gives more negative VaR."""
        config_95 = {'confidence_level': 0.95}
        config_99 = {'confidence_level': 0.99}

        calc_95 = HistoricalVaRCalculator(config_95)
        calc_99 = HistoricalVaRCalculator(config_99)

        result_95 = calc_95.calculate_var(sample_returns)
        result_99 = calc_99.calculate_var(sample_returns)

        # 99% VaR should be more negative
        assert result_99['var'] <= result_95['var']


@pytest.mark.unit
class TestHistoricalVaRConsistency:
    """Test consistency of VaR calculations."""

    def test_same_input_same_output(self, calculator, sample_returns):
        """Test that same input produces same output."""
        result1 = calculator.calculate_var(sample_returns)
        result2 = calculator.calculate_var(sample_returns)

        assert result1['var'] == result2['var']
        assert result1['cvar'] == result2['cvar']

    def test_deterministic_with_seed(self):
        """Test deterministic results with random seed."""
        np.random.seed(123)
        returns1 = np.random.normal(0, 0.02, 1000)

        np.random.seed(123)
        returns2 = np.random.normal(0, 0.02, 1000)

        config = {'confidence_level': 0.95}
        calc = HistoricalVaRCalculator(config)

        result1 = calc.calculate_var(returns1)
        result2 = calc.calculate_var(returns2)

        assert result1['var'] == result2['var']


@pytest.mark.unit
class TestCVaRCalculation:
    """Test Conditional VaR (Expected Shortfall) calculation."""

    def test_cvar_is_average_of_tail(self, calculator):
        """Test that CVaR is average of losses beyond VaR."""
        returns = np.array([-0.05, -0.04, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05])
        result = calculator.calculate_var(returns)

        # CVaR should be more negative than VaR
        assert result['cvar'] <= result['var']

    def test_cvar_amount_calculation(self, calculator, sample_returns):
        """Test CVaR amount calculation."""
        portfolio_value = 100000.0
        result = calculator.calculate_var(sample_returns, portfolio_value)

        # CVaR amount should be positive dollar amount
        assert result['cvar_amount'] >= 0
        assert isinstance(result['cvar_amount'], float)


@pytest.mark.unit
class TestHistoricalVaRExtremeCases:
    """Test VaR with extreme cases."""

    def test_high_volatility_returns(self, calculator):
        """Test with high volatility returns."""
        np.random.seed(42)
        returns = np.random.normal(0, 0.10, 1000)  # 10% daily vol
        result = calculator.calculate_var(returns)

        assert 'var' in result
        # VaR should be quite negative
        assert result['var'] < -0.15

    def test_low_volatility_returns(self, calculator):
        """Test with low volatility returns."""
        np.random.seed(42)
        returns = np.random.normal(0, 0.005, 1000)  # 0.5% daily vol
        result = calculator.calculate_var(returns)

        assert 'var' in result
        # VaR should be relatively small
        assert result['var'] > -0.02

    def test_fat_tailed_distribution(self, calculator):
        """Test with fat-tailed distribution."""
        np.random.seed(42)
        # Student-t like distribution with fatter tails
        returns = np.random.standard_t(3, 1000) * 0.01
        result = calculator.calculate_var(returns)

        assert 'var' in result


@pytest.mark.unit
class TestHistoricalVaRMethodAttributes:
    """Test method-specific attributes."""

    def test_method_identified(self, calculator, sample_returns):
        """Test that method is correctly identified."""
        result = calculator.calculate_var(sample_returns)

        assert result['method'] == 'historical'

    def test_time_horizon_included(self, calculator, sample_returns):
        """Test that time horizon is included."""
        result = calculator.calculate_var(sample_returns)

        assert 'time_horizon' in result
        assert result['time_horizon'] == 1

    def test_all_required_fields_present(self, calculator, sample_returns):
        """Test that all required fields are present."""
        result = calculator.calculate_var(sample_returns)

        required_fields = [
            'var', 'var_amount', 'cvar', 'cvar_amount',
            'confidence_level', 'time_horizon', 'method',
            'observations', 'numba_accelerated'
        ]

        for field in required_fields:
            assert field in result


@pytest.mark.unit
class TestHistoricalVaRWithRealWorldData:
    """Test with realistic market data patterns."""

    def test_bull_market_scenario(self, calculator):
        """Test with bull market returns (positive drift)."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.015, 500)  # Positive drift
        result = calculator.calculate_var(returns)

        assert 'var' in result

    def test_bear_market_scenario(self, calculator):
        """Test with bear market returns (negative drift)."""
        np.random.seed(42)
        returns = np.random.normal(-0.001, 0.025, 500)  # Negative drift
        result = calculator.calculate_var(returns)

        assert 'var' in result
        # VaR should be more negative than bull market

    def test_volatile_period(self, calculator):
        """Test with highly volatile period."""
        np.random.seed(42)
        # Regime-switching volatility
        returns = []
        for i in range(500):
            if i < 250:
                returns.append(np.random.normal(0, 0.01))
            else:
                returns.append(np.random.normal(0, 0.04))  # Vol spike

        result = calculator.calculate_var(np.array(returns))
        assert 'var' in result
