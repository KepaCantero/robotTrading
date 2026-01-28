"""
Property-based tests for Risk Engine using Hypothesis.

Tests invariants and properties across wide range of inputs.
"""
import pytest
import numpy as np
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import lists, floats, integers

from app.engines.risk_engine.var_calculators.var_calculators import (
    HistoricalVaRCalculator,
    ParametricVaRCalculator,
    calculate_percentile_numba,
)
from app.engines.risk_engine.var_calculators.ewma_var import EWMAVaRCalculator


@pytest.mark.unit
class TestPropertyBasedVaR:
    """Property-based tests for VaR calculations."""

    @given(lists(floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False), min_size=50, max_size=500))
    @settings(max_examples=50, deadline=500)
    def test_var_is_always_negative_or_zero(self, returns_list):
        """Test that VaR is always negative or zero (loss)."""
        # Skip test if all values are zero (edge case)
        if all(abs(x) < 1e-10 for x in returns_list):
            return

        calc = HistoricalVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(np.array(returns_list))

        if 'error' not in result:
            assert result['var'] <= 0

    @given(lists(floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False), min_size=100, max_size=1000))
    @settings(max_examples=30)
    def test_cvar_more_negative_than_var(self, returns_list):
        """Test that CVaR is always more negative than VaR."""
        calc = HistoricalVaRCalculator({'confidence_level': 0.95})
        result = calc.calculate_var(np.array(returns_list))

        if 'error' not in result and 'cvar' in result:
            assert result['cvar'] <= result['var']

    @given(lists(floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False), min_size=50, max_size=500))
    @settings(max_examples=30)
    def test_higher_confidence_more_negative_var(self, returns_list):
        """Test that higher confidence level gives more negative VaR."""
        calc_95 = HistoricalVaRCalculator({'confidence_level': 0.95})
        calc_99 = HistoricalVaRCalculator({'confidence_level': 0.99})

        result_95 = calc_95.calculate_var(np.array(returns_list))
        result_99 = calc_99.calculate_var(np.array(returns_list))

        if 'error' not in result_95 and 'error' not in result_99:
            assert result_99['var'] <= result_95['var']


@pytest.mark.unit
class TestPropertyBasedPercentile:
    """Property-based tests for percentile calculation."""

    @given(lists(floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), min_size=10, max_size=1000))
    @settings(max_examples=50)
    def test_percentile_in_range(self, data_list):
        """Test that percentile is within data range."""
        # Skip test if all values are the same (edge case)
        if len(data_list) > 0 and all(abs(x - data_list[0]) < 1e-10 for x in data_list):
            return

        data = np.array(data_list)
        percentile_50 = calculate_percentile_numba(data, 50)

        if len(data) > 0:
            assert np.min(data) <= percentile_50 <= np.max(data)

    @given(lists(floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), min_size=10, max_size=100))
    @settings(max_examples=30)
    def test_percentile_monotonic(self, data_list):
        """Test that higher percentiles give higher values."""
        data = np.array(data_list)
        p25 = calculate_percentile_numba(data, 25)
        p50 = calculate_percentile_numba(data, 50)
        p75 = calculate_percentile_numba(data, 75)

        assert p25 <= p50 <= p75


@pytest.mark.unit
class TestPropertyBasedEWMA:
    """Property-based tests for EWMA calculations."""

    @given(lists(floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False), min_size=50, max_size=500))
    @settings(max_examples=30)
    def test_ewma_variance_positive(self, returns_list):
        """Test that EWMA variance is always positive."""
        calc = EWMAVaRCalculator()
        variance = calc._calculate_ewma_variance(np.array(returns_list))

        assert variance >= 0

    @given(lists(floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False), min_size=50, max_size=500))
    @settings(max_examples=30)
    def test_ewma_volatility_positive(self, returns_list):
        """Test that EWMA volatility is always positive."""
        calc = EWMAVaRCalculator()
        variance = calc._calculate_ewma_variance(np.array(returns_list))
        volatility = np.sqrt(variance)

        assert volatility >= 0


@pytest.mark.unit
class TestPropertyBasedRiskMetrics:
    """Property-based tests for risk metrics."""

    @given(floats(min_value=0.01, max_value=1.0), floats(min_value=0.8, max_value=0.999))
    @settings(max_examples=20)
    def test_var_amount_positive(self, portfolio_value, confidence_level):
        """Test that VaR amount is always positive."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)

        calc = HistoricalVaRCalculator({'confidence_level': confidence_level})
        result = calc.calculate_var(returns, portfolio_value=portfolio_value)

        if 'error' not in result and result['var_amount'] is not None:
            assert result['var_amount'] >= 0

    @given(floats(min_value=0.80, max_value=0.999), floats(min_value=0.85, max_value=0.999))
    @settings(max_examples=20)
    def test_confidence_affects_var(self, conf1, conf2):
        """Test that different confidence levels give different VaRs."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)

        # Ensure conf1 < conf2
        if conf1 > conf2:
            conf1, conf2 = conf2, conf1

        calc1 = HistoricalVaRCalculator({'confidence_level': conf1})
        calc2 = HistoricalVaRCalculator({'confidence_level': conf2})

        result1 = calc1.calculate_var(returns)
        result2 = calc2.calculate_var(returns)

        if 'error' not in result1 and 'error' not in result2:
            # Higher confidence should give more negative VaR
            assert result2['var'] <= result1['var']
