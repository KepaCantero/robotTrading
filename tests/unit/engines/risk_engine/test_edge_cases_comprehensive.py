"""
Comprehensive edge case tests for Risk Engine.

Tests boundary conditions, unusual inputs, and stress scenarios.
"""

from unittest.mock import Mock

import numpy as np
import pytest

from app.engines.risk_engine.alert_system import AlertSystem
from app.engines.risk_engine.greeks_calculator import GreeksCalculator
from app.engines.risk_engine.risk_limits_enforcer import RiskLimitsEnforcer
from app.engines.risk_engine.var_calculators.ewma_var import EWMAVaRCalculator
from app.engines.risk_engine.var_calculators.var_calculators import calculate_var


@pytest.mark.unit
class TestVaREdgeCases:
    """Test VaR calculator edge cases."""

    def test_var_with_zero_variance(self):
        """Test VaR with zero variance returns."""
        returns = np.array([0.01] * 100)
        result = calculate_var(returns, method='parametric')

        # Should still calculate
        assert 'var' in result

    def test_var_with_extreme_outliers(self):
        """Test VaR with extreme outliers."""
        returns = list(np.random.normal(0, 0.02, 95)) + [0.50, -0.50]
        result = calculate_var(np.array(returns), method='historical')

        # Historical method should handle outliers
        assert 'var' in result

    def test_var_with_missing_values(self):
        """Test VaR handling of NaN values."""
        returns = np.array([0.01, -0.01, np.nan, 0.02, -0.02])
        result = calculate_var(returns, method='parametric')

        # Should handle or fail gracefully
        assert 'error' in result or 'var' in result

    def test_var_with_infinity(self):
        """Test VaR with infinite values."""
        returns = np.array([0.01, -0.01, np.inf, 0.02])
        result = calculate_var(returns, method='historical')

        # Should handle or fail gracefully
        assert 'error' in result or 'var' in result


@pytest.mark.unit
class TestGreeksEdgeCases:
    """Test Greeks calculator edge cases."""

    def test_greeks_zero_time_to_expiry(self):
        """Test Greeks at exact expiry."""
        calc = GreeksCalculator()
        result = calc.calculate_all_greeks(
            option_type='call',
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry=0.0001,  # Very close to zero
            volatility=0.20,
        )

        # Should handle near-zero time
        assert 'error' in result or 'primary_greeks' in result

    def test_greeks_zero_volatility(self):
        """Test Greeks with zero volatility."""
        calc = GreeksCalculator()
        result = calc.calculate_all_greeks(
            option_type='call',
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry=0.25,
            volatility=0.0001,  # Near zero
        )

        assert 'error' in result or 'primary_greeks' in result

    def test_greeks_extreme_moneyness(self):
        """Test Greeks with extreme moneyness."""
        calc = GreeksCalculator()

        # Deep ITM (spot >> strike)
        result1 = calc.calculate_all_greeks(
            option_type='call',
            spot_price=1000.0,
            strike_price=100.0,
            time_to_expiry=0.25,
            volatility=0.20,
        )

        # Deep OTM (spot << strike)
        result2 = calc.calculate_all_greeks(
            option_type='call',
            spot_price=10.0,
            strike_price=1000.0,
            time_to_expiry=0.25,
            volatility=0.20,
        )

        # Both should work
        assert 'error' not in result1 or 'primary_greeks' in result1
        assert 'error' not in result2 or 'primary_greeks' in result2


@pytest.mark.unit
class TestAlertSystemEdgeCases:
    """Test alert system edge cases."""

    def test_alerts_with_none_values(self):
        """Test alerts with None values in risk assessment."""
        system = AlertSystem({})
        portfolio = Mock()
        portfolio.total_equity = 100000.0

        risk_assessment = {
            'var': {
                'var_amount': None,
                'var': None,
            }
        }

        alerts = system.check_thresholds(risk_assessment, portfolio)

        # Should not crash
        assert isinstance(alerts, list)

    def test_alerts_with_very_large_portfolio(self):
        """Test alerts with very large portfolio value."""
        system = AlertSystem({})
        portfolio = Mock()
        portfolio.total_equity = 1e15  # Very large

        risk_assessment = {
            'var': {
                'var_amount': 1e13,
                'var': 0.10,
            }
        }

        alerts = system.check_thresholds(risk_assessment, portfolio)

        # Should handle large values
        assert isinstance(alerts, list)


@pytest.mark.unit
class TestRiskLimitsEdgeCases:
    """Test risk limits enforcer edge cases."""

    def test_limits_with_zero_portfolio(self):
        """Test limits with zero portfolio value."""
        enforcer = RiskLimitsEnforcer()
        portfolio = Mock()
        portfolio.total_equity = 0.0

        result = enforcer.enforce_position_limits(portfolio)

        # Should handle gracefully
        assert 'error' in result or 'violations' in result

    def test_limits_with_negative_var(self):
        """Test limits with negative VaR (unusual)."""
        enforcer = RiskLimitsEnforcer()
        portfolio = Mock()
        portfolio.total_equity = 100000.0

        result = enforcer.check_var_limits(portfolio, current_var=-0.05)

        # Should handle
        assert 'severity' in result


@pytest.mark.unit
class TestEWMAEdgeCases:
    """Test EWMA calculator edge cases."""

    def test_ewma_with_exactly_min_observations(self):
        """Test EWMA with exactly minimum observations."""
        calc = EWMAVaRCalculator({'min_observations': 30})
        returns = list(np.random.normal(0, 0.02, 30))

        result = calc.calculate_ewma_var(returns)

        # Should work with exactly minimum
        assert 'error' not in result

    def test_ewma_with_decay_factor_at_boundary(self):
        """Test EWMA with extreme decay factors."""
        # Very low decay (more weight to recent)
        calc1 = EWMAVaRCalculator({'decay_factor': 0.50})
        returns = list(np.random.normal(0, 0.02, 100))
        result1 = calc1.calculate_ewma_var(returns)

        # Very high decay (equal weighting)
        calc2 = EWMAVaRCalculator({'decay_factor': 0.999})
        result2 = calc2.calculate_ewma_var(returns)

        # Both should work
        assert 'error' not in result1 or 'var' in result1
        assert 'error' not in result2 or 'var' in result2
