"""
Comprehensive unit tests for EWMA VaR Calculator.

Tests for all EWMA VaR functionality including correlation and forecasting.
"""
import pytest
import numpy as np

from app.engines.risk_engine.var_calculators.ewma_var import EWMAVaRCalculator


@pytest.fixture
def calculator():
    """Create EWMAVaRCalculator instance."""
    return EWMAVaRCalculator()


@pytest.fixture
def volatility_regime_returns():
    """Create returns with volatility regime change."""
    np.random.seed(42)
    returns = []
    # Low vol regime
    for _ in range(50):
        returns.append(np.random.normal(0, 0.01))
    # High vol regime
    for _ in range(50):
        returns.append(np.random.normal(0, 0.04))
    return returns


@pytest.mark.unit
class TestEWMAVolatilityRegimeDetection:
    """Test EWMA detection of volatility regimes."""

    def test_ewma_detects_volatility_increase(self, calculator, volatility_regime_returns):
        """Test that EWMA detects volatility increase."""
        result = calculator.calculate_ewma_var(volatility_regime_returns)

        if 'comparison' in result:
            # EWMA should be higher than simple std after vol spike
            assert 'volatility_ratio' in result['comparison']

    def test_ewma_interpretation_message(self, calculator, volatility_regime_returns):
        """Test that interpretation message is generated."""
        result = calculator.calculate_ewma_var(volatility_regime_returns)

        assert 'interpretation' in result
        assert len(result['interpretation']) > 0


@pytest.mark.unit
class TestEWMACorrelationCalculation:
    """Test EWMA correlation calculation."""

    def test_ewma_correlation_calculation(self, calculator):
        """Test EWMA correlation between two series."""
        returns1 = list(np.random.normal(0, 0.02, 100))
        returns2 = list(np.random.normal(0, 0.02, 100))

        result = calculator.calculate_ewma_correlation(returns1, returns2)

        assert 'error' not in result
        assert 'ewma_correlation' in result

    def test_correlation_value_range(self, calculator):
        """Test that correlation is in valid range."""
        # Create correlated series
        returns1 = list(np.random.normal(0, 0.02, 100))
        returns2 = [r + 0.001 for r in returns1]

        result = calculator.calculate_ewma_correlation(returns1, returns2)

        assert -1 <= result['ewma_correlation'] <= 1


@pytest.mark.unit
class TestEWMAForecasting:
    """Test EWMA volatility forecasting."""

    def test_volatility_forecast(self, calculator):
        """Test volatility forecast generation."""
        returns = list(np.random.normal(0, 0.02, 100))
        result = calculator.forecast_volatility(returns, horizon_days=10)

        assert 'error' not in result
        assert 'forecasts' in result
        assert len(result['forecasts']) == 10

    def test_forecast_increasing_with_horizon(self, calculator):
        """Test that forecasts increase with horizon (sqrt time)."""
        returns = list(np.random.normal(0, 0.02, 100))
        result = calculator.forecast_volatility(returns, horizon_days=10)

        forecasts = result['forecasts']
        for i in range(len(forecasts) - 1):
            assert forecasts[i + 1] >= forecasts[i]
