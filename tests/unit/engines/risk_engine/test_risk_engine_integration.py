"""
Integration tests for Risk Engine components.

Tests interaction between different risk engine modules.
"""
import pytest
import numpy as np
from unittest.mock import Mock

from app.engines.risk_engine.greeks_calculator import GreeksCalculator
from app.engines.risk_engine.alert_system import AlertSystem
from app.engines.risk_engine.risk_limits_enforcer import RiskLimitsEnforcer
from app.engines.risk_engine.var_calculators.var_calculators import calculate_var
from app.models.portfolio import Portfolio


@pytest.fixture
def sample_portfolio():
    """Create sample portfolio."""
    portfolio = Mock(spec=Portfolio)
    portfolio.total_equity = 100000.0
    return portfolio


@pytest.fixture
def risk_components():
    """Create all risk engine components."""
    return {
        'greeks': GreeksCalculator(),
        'alerts': AlertSystem({}),
        'limits': RiskLimitsEnforcer(),
    }


@pytest.mark.unit
class TestRiskEngineWorkflow:
    """Test complete risk engine workflow."""

    def test_var_to_alerts_workflow(self, sample_portfolio):
        """Test workflow from VaR calculation to alerts."""
        # Calculate VaR
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)
        var_result = calculate_var(returns, method='historical')

        # Create risk assessment
        risk_assessment = {
            'var': var_result,
            'drawdown': {
                'portfolio_drawdown': {
                    'current_drawdown': 0.10,
                }
            }
        }

        # Check alerts
        alert_system = AlertSystem({})
        alerts = alert_system.check_thresholds(risk_assessment, sample_portfolio)

        # Should return alerts (even if empty)
        assert isinstance(alerts, list)

    def test_var_to_limits_enforcement(self, sample_portfolio):
        """Test workflow from VaR to limits enforcement."""
        # Calculate VaR
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)
        var_result = calculate_var(returns, method='parametric')

        # Check limits
        enforcer = RiskLimitsEnforcer()
        result = enforcer.check_var_limits(sample_portfolio, var_result['var'])

        assert 'severity' in result
        assert 'action' in result

    def test_complete_risk_assessment(self, sample_portfolio, risk_components):
        """Test complete risk assessment workflow."""
        # 1. Calculate VaR
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)
        var_result = calculate_var(returns, method='historical')

        # 2. Check limits
        limits_result = risk_components['limits'].check_var_limits(
            sample_portfolio, var_result['var']
        )

        # 3. Create risk assessment
        risk_assessment = {
            'var': var_result,
            'drawdown': {
                'portfolio_drawdown': {
                    'current_drawdown': 0.10,
                }
            }
        }

        # 4. Generate alerts
        alerts = risk_components['alerts'].check_thresholds(
            risk_assessment, sample_portfolio
        )

        # All components should work
        assert 'severity' in limits_result
        assert isinstance(alerts, list)


@pytest.mark.unit
class TestGreeksWithLimits:
    """Test Greeks calculator with risk limits."""

    def test_greeks_risk_limit_validation(self):
        """Test Greeks validation against risk limits."""
        greeks_calc = GreeksCalculator()

        # Calculate Greeks
        greeks_result = greeks_calc.calculate_all_greeks(
            option_type='call',
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry=0.25,
            volatility=0.20,
        )

        # Validate consistency
        validation = greeks_calc.validate_greeks_consistency(greeks_result)

        assert 'valid' in validation

    def test_portfolio_greeks_risk_limits(self):
        """Test portfolio Greeks against risk limits."""
        greeks_calc = GreeksCalculator()

        positions = [
            {
                'option_type': 'call',
                'spot_price': 100.0,
                'strike_price': 100.0,
                'time_to_expiry': 0.25,
                'volatility': 0.20,
                'quantity': 10,
            }
        ]

        portfolio_greeks = greeks_calc.calculate_portfolio_greeks(positions)

        # Validate against limits
        validation = greeks_calc.validate_greeks_risk_limits(portfolio_greeks)

        assert 'within_limits' in validation
        assert 'violations' in validation
