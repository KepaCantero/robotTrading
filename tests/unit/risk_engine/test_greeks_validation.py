"""
Tests for Greeks Calculator Validation Features.

Tests the new validation methods for Greeks calculations:
- validate_greeks_consistency
- validate_greeks_risk_limits
- calculate_greeks_sensitivity_analysis
"""

import pytest
import numpy as np

from app.engines.risk_engine.greeks_calculator import GreeksCalculator


class TestGreeksValidation:
    """Test Greeks validation features."""

    @pytest.fixture
    def greeks_calculator(self):
        """Create Greeks calculator instance."""
        return GreeksCalculator()

    @pytest.fixture
    def sample_call_params(self):
        """Sample call option parameters."""
        return {
            'option_type': 'call',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,  # 3 months
            'volatility': 0.20,
            'risk_free_rate': 0.05,
            'dividend_yield': 0.0,
        }

    @pytest.fixture
    def sample_put_params(self):
        """Sample put option parameters."""
        return {
            'option_type': 'put',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
            'risk_free_rate': 0.05,
            'dividend_yield': 0.0,
        }

    def test_validate_greeks_consistency_call(self, greeks_calculator, sample_call_params):
        """Test Greeks validation for call option."""
        # Calculate Greeks
        greeks = greeks_calculator.calculate_all_greeks(**sample_call_params)

        # Validate
        validation = greeks_calculator.validate_greeks_consistency(greeks)

        assert validation['valid'] is True
        assert len(validation['validation_issues']) == 0
        assert 'greeks_checked' in validation

    def test_validate_greeks_consistency_put(self, greeks_calculator, sample_put_params):
        """Test Greeks validation for put option."""
        greeks = greeks_calculator.calculate_all_greeks(**sample_put_params)
        validation = greeks_calculator.validate_greeks_consistency(greeks)

        assert validation['valid'] is True
        assert 'delta' in validation['greeks_checked']
        assert validation['greeks_checked']['delta'] < 0  # Put delta negative

    def test_validate_greeks_consistency_warnings(self, greeks_calculator):
        """Test that warnings are generated for unusual Greeks."""
        # Create option with unusual parameters that generate warnings
        params = {
            'option_type': 'call',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.01,  # Very short term
            'volatility': 0.50,  # High volatility
            'risk_free_rate': 0.05,
        }

        greeks = greeks_calculator.calculate_all_greeks(**params)
        validation = greeks_calculator.validate_greeks_consistency(greeks)

        # Should have warnings due to unusual parameters
        assert 'warnings' in validation

    def test_validate_greeks_risk_limits_within_limits(self, greeks_calculator):
        """Test risk limit validation when within limits."""
        portfolio_greeks = {
            'total_delta': 50.0,
            'total_gamma': 2.0,
            'total_theta': -500.0,
            'total_vega': 200.0,
            'total_rho': 100.0,
        }

        limits = {
            'max_delta': 100,
            'max_gamma': 5,
            'max_theta': -1000,
            'max_vega': 500,
            'max_rho': 200,
        }

        validation = greeks_calculator.validate_greeks_risk_limits(
            portfolio_greeks, limits
        )

        assert validation['within_limits'] is True
        assert validation['risk_level'] == 'LOW'
        assert len(validation['violations']) == 0

    def test_validate_greeks_risk_limits_violations(self, greeks_calculator):
        """Test risk limit validation when limits are exceeded."""
        portfolio_greeks = {
            'total_delta': 150.0,  # Exceeds limit
            'total_gamma': -7.0,  # Short gamma exceeds limit
            'total_theta': -1500.0,  # Exceeds limit
            'total_vega': 600.0,  # Exceeds limit
            'total_rho': 50.0,
        }

        limits = {
            'max_delta': 100,
            'max_gamma': 5,
            'max_theta': -1000,
            'max_vega': 500,
            'max_rho': 200,
        }

        validation = greeks_calculator.validate_greeks_risk_limits(
            portfolio_greeks, limits
        )

        assert validation['within_limits'] is False
        assert len(validation['violations']) > 0
        assert validation['risk_level'] in ['HIGH', 'CRITICAL']
        assert 'recommendation' in validation

    def test_validate_greeks_risk_limits_critical_gamma(self, greeks_calculator):
        """Test that short gamma violations are marked as critical."""
        portfolio_greeks = {
            'total_delta': 0.0,
            'total_gamma': -10.0,  # Severe short gamma
            'total_theta': 0.0,
            'total_vega': 0.0,
            'total_rho': 0.0,
        }

        limits = {'max_delta': 100, 'max_gamma': 5, 'max_theta': -1000,
                  'max_vega': 500, 'max_rho': 200}

        validation = greeks_calculator.validate_greeks_risk_limits(
            portfolio_greeks, limits
        )

        # Should have critical gamma violation
        gamma_violations = [v for v in validation['violations'] if v['greek'] == 'gamma']
        assert len(gamma_violations) > 0
        assert gamma_violations[0]['severity'] == 'CRITICAL'

    def test_sensitivity_analysis_spot(self, greeks_calculator, sample_call_params):
        """Test spot price sensitivity analysis."""
        sensitivity = greeks_calculator.calculate_greeks_sensitivity_analysis(
            sample_call_params
        )

        assert 'sensitivity_analysis' in sensitivity
        assert 'spot_sensitivity' in sensitivity['sensitivity_analysis']
        assert 'base_greeks' in sensitivity

        spot_sens = sensitivity['sensitivity_analysis']['spot_sensitivity']
        assert 'delta_change_up' in spot_sens
        assert 'delta_change_down' in spot_sens
        assert 'gamma_validation' in spot_sens

    def test_sensitivity_analysis_volatility(self, greeks_calculator, sample_call_params):
        """Test volatility sensitivity analysis."""
        sensitivity = greeks_calculator.calculate_greeks_sensitivity_analysis(
            sample_call_params
        )

        vol_sens = sensitivity['sensitivity_analysis']['volatility_sensitivity']
        assert 'vega_change_up' in vol_sens
        assert 'vega_change_down' in vol_sens
        assert 'vomma_validation' in vol_sens

    def test_sensitivity_analysis_time(self, greeks_calculator, sample_call_params):
        """Test time decay sensitivity analysis."""
        sensitivity = greeks_calculator.calculate_greeks_sensitivity_analysis(
            sample_call_params
        )

        time_sens = sensitivity['sensitivity_analysis']['time_decay_sensitivity']
        assert 'theta_acceleration' in time_sens
        assert 'theta_warning' in time_sens

    def test_sensitivity_analysis_overall_assessment(self, greeks_calculator,
                                                      sample_call_params):
        """Test overall sensitivity assessment."""
        sensitivity = greeks_calculator.calculate_greeks_sensitivity_analysis(
            sample_call_params
        )

        assessment = sensitivity['sensitivity_analysis']['assessment']
        assert 'stability_score' in assessment
        assert 'stability_level' in assessment
        assert 'recommendation' in assessment
        assert assessment['stability_level'] in ['HIGH', 'MODERATE', 'LOW']

    def test_sensitivity_analysis_custom_scenarios(self, greeks_calculator,
                                                    sample_call_params):
        """Test sensitivity analysis with custom shock scenarios."""
        custom_scenarios = {
            'spot_shock_pct': 0.10,  # 10% spot shock
            'vol_shock_pct': 0.20,  # 20% vol shock
        }

        sensitivity = greeks_calculator.calculate_greeks_sensitivity_analysis(
            sample_call_params,
            shock_scenarios=custom_scenarios
        )

        assert 'scenarios_applied' in sensitivity
        assert sensitivity['scenarios_applied']['spot_shock_pct'] == 0.10
        assert sensitivity['scenarios_applied']['vol_shock_pct'] == 0.20

    def test_validate_greeks_error_handling(self, greeks_calculator):
        """Test validation with error input."""
        validation = greeks_calculator.validate_greeks_consistency(
            {'error': 'Calculation failed'}
        )

        assert validation['valid'] is False
        assert 'error' in validation

    def test_sensitivity_analysis_error_handling(self, greeks_calculator):
        """Test sensitivity analysis with invalid parameters."""
        invalid_params = {
            'option_type': 'call',
            'spot_price': -100.0,  # Invalid negative price
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }

        result = greeks_calculator.calculate_greeks_sensitivity_analysis(
            invalid_params
        )

        # Should handle error gracefully
        assert 'error' in result or 'sensitivity_analysis' in result


class TestGreeksRiskLimits:
    """Test Greeks risk limits enforcement."""

    @pytest.fixture
    def greeks_calculator(self):
        return GreeksCalculator()

    def test_risk_score_calculation(self, greeks_calculator):
        """Test risk score calculation for violations."""
        portfolio_greeks = {
            'total_delta': 200.0,  # HIGH
            'total_gamma': -10.0,  # CRITICAL
            'total_theta': -2000.0,  # MEDIUM
            'total_vega': 1000.0,  # HIGH
            'total_rho': 0.0,
        }

        limits = {'max_delta': 100, 'max_gamma': 5, 'max_theta': -1000,
                  'max_vega': 500, 'max_rho': 200}

        validation = greeks_calculator.validate_greeks_risk_limits(
            portfolio_greeks, limits
        )

        assert validation['risk_score'] > 0
        assert validation['risk_level'] == 'CRITICAL'

    def test_recommendation_generation(self, greeks_calculator):
        """Test recommendation generation based on violations."""
        portfolio_greeks = {
            'total_delta': 150.0,
            'total_gamma': 2.0,
            'total_theta': -500.0,
            'total_vega': 200.0,
            'total_rho': 0.0,
        }

        limits = {'max_delta': 100, 'max_gamma': 5, 'max_theta': -1000,
                  'max_vega': 500, 'max_rho': 200}

        validation = greeks_calculator.validate_greeks_risk_limits(
            portfolio_greeks, limits
        )

        assert 'recommendation' in validation
        assert isinstance(validation['recommendation'], str)
        assert len(validation['recommendation']) > 0
