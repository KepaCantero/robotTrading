"""
Unit tests for EWMA VaR Calculator.

Tests for Exponentially Weighted Moving Average VaR calculation.
"""
import pytest
import numpy as np
from unittest.mock import patch, Mock

from app.engines.risk_engine.var_calculators.ewma_var import EWMAVaRCalculator


@pytest.fixture
def sample_returns():
    """Create sample returns data."""
    np.random.seed(42)
    return list(np.random.normal(0.001, 0.02, 100))


@pytest.fixture
def calculator():
    """Create EWMAVaRCalculator instance."""
    return EWMAVaRCalculator()


@pytest.fixture
def custom_calculator():
    """Create EWMAVaRCalculator with custom config."""
    config = {
        'confidence_level': 0.99,
        'decay_factor': 0.97,
        'min_observations': 50,
    }
    return EWMAVaRCalculator(config)


@pytest.mark.unit
class TestEWMAVaRCalculatorInitialization:
    """Test EWMAVaRCalculator initialization."""

    def test_default_initialization(self, calculator):
        """Test initialization with defaults."""
        assert calculator.confidence_level == 0.95
        assert calculator.decay_factor == 0.94
        assert calculator.min_observations == 30

    def test_custom_initialization(self, custom_calculator):
        """Test initialization with custom config."""
        assert custom_calculator.confidence_level == 0.99
        assert custom_calculator.decay_factor == 0.97
        assert custom_calculator.min_observations == 50


@pytest.mark.unit
class TestEWMAVaRCalculation:
    """Test EWMA VaR calculation."""

    def test_calculate_ewma_var_success(self, calculator, sample_returns):
        """Test successful EWMA VaR calculation."""
        result = calculator.calculate_ewma_var(sample_returns)

        assert 'error' not in result
        assert 'var' in result
        assert 'cvar' in result
        assert result['method'] == 'ewma'

    def test_ewma_volatility_calculated(self, calculator, sample_returns):
        """Test that EWMA volatility is calculated."""
        result = calculator.calculate_ewma_var(sample_returns)

        assert 'ewma_volatility' in result
        assert result['ewma_volatility'] > 0

    def test_ewma_variance_calculated(self, calculator, sample_returns):
        """Test that EWMA variance is calculated."""
        result = calculator.calculate_ewma_var(sample_returns)

        assert 'ewma_variance' in result
        assert result['ewma_variance'] > 0

    def test_with_portfolio_value(self, calculator, sample_returns):
        """Test with portfolio value."""
        result = calculator.calculate_ewma_var(sample_returns, portfolio_value=100000.0)

        assert result['var_amount'] is not None
        assert result['cvar_amount'] is not None

    def test_comparison_with_simple_std(self, calculator, sample_returns):
        """Test comparison with simple standard deviation."""
        result = calculator.calculate_ewma_var(sample_returns)

        assert 'comparison' in result
        assert 'ewma_volatility' in result['comparison']
        assert 'simple_std' in result['comparison']
        assert 'volatility_ratio' in result['comparison']

    def test_interpretation_provided(self, calculator, sample_returns):
        """Test that interpretation is provided."""
        result = calculator.calculate_ewma_var(sample_returns)

        assert 'interpretation' in result
        assert isinstance(result['interpretation'], str)


@pytest.mark.unit
class TestEWMAVarianceCalculation:
    """Test EWMA variance calculation."""

    def test_ewma_variance_formula(self, calculator):
        """Test EWMA variance calculation formula."""
        returns = [0.01, -0.01, 0.02, -0.02, 0.015, -0.015]
        variance = calculator._calculate_ewma_variance(np.array(returns))

        assert variance > 0

    def test_ewma_recursive_calculation(self, calculator):
        """Test that EWMA is calculated recursively."""
        returns = list(np.random.normal(0, 0.02, 100))
        variance = calculator._calculate_ewma_variance(np.array(returns))

        assert variance > 0


@pytest.mark.unit
class TestEWMAVaRErrorHandling:
    """Test error handling."""

    def test_insufficient_data(self, calculator):
        """Test with insufficient data."""
        short_returns = list(np.random.normal(0, 0.02, 10))
        result = calculator.calculate_ewma_var(short_returns)

        assert 'error' in result
        assert 'Insufficient data' in result['error']

    def test_empty_returns(self, calculator):
        """Test with empty returns."""
        result = calculator.calculate_ewma_var([])

        assert 'error' in result


@pytest.mark.unit
class TestEWMACorrelation:
    """Test EWMA correlation calculation."""

    def test_ewma_correlation_success(self, calculator):
        """Test EWMA correlation calculation."""
        returns1 = list(np.random.normal(0, 0.02, 100))
        returns2 = list(np.random.normal(0, 0.02, 100))

        result = calculator.calculate_ewma_correlation(returns1, returns2)

        assert 'error' not in result
        assert 'ewma_correlation' in result

    def test_ewma_correlation_range(self, calculator):
        """Test that correlation is in valid range."""
        # Create correlated returns
        returns1 = list(np.random.normal(0, 0.02, 100))
        returns2 = [r + 0.001 for r in returns1]

        result = calculator.calculate_ewma_correlation(returns1, returns2)

        assert -1 <= result['ewma_correlation'] <= 1

    def test_correlation_interpretation(self, calculator):
        """Test correlation change interpretation."""
        returns1 = list(np.random.normal(0, 0.02, 100))
        returns2 = list(np.random.normal(0, 0.02, 100))

        result = calculator.calculate_ewma_correlation(returns1, returns2)

        assert 'interpretation' in result


@pytest.mark.unit
class TestEWMAVolatilityForecasting:
    """Test EWMA volatility forecasting."""

    def test_forecast_volatility_success(self, calculator, sample_returns):
        """Test volatility forecasting."""
        result = calculator.forecast_volatility(sample_returns, horizon_days=10)

        assert 'error' not in result
        assert 'current_volatility' in result
        assert 'forecasts' in result
        assert len(result['forecasts']) == 10

    def test_forecast_includes_horizon(self, calculator, sample_returns):
        """Test that horizon is included."""
        result = calculator.forecast_volatility(sample_returns, horizon_days=5)

        assert result['horizon_days'] == 5

    def test_forecast_increases_with_horizon(self, calculator, sample_returns):
        """Test that forecasts increase with horizon (sqrt time rule)."""
        result = calculator.forecast_volatility(sample_returns, horizon_days=10)

        forecasts = result['forecasts']
        # Each subsequent forecast should be >= previous
        for i in range(len(forecasts) - 1):
            assert forecasts[i+1] >= forecasts[i]


@pytest.mark.unit
class TestEWMAInterpretationLogic:
    """Test interpretation logic."""

    def test_high_volatility_spike_interpretation(self, calculator):
        """Test interpretation when volatility spikes."""
        # Create scenario where EWMA >> simple
        returns = []
        for i in range(100):
            if i < 50:
                returns.append(np.random.normal(0, 0.01))
            else:
                returns.append(np.random.normal(0, 0.05))  # Vol spike

        result = calculator.calculate_ewma_var(returns)
        interpretation = result['interpretation']

        assert isinstance(interpretation, str)
        assert len(interpretation) > 0
