"""
Unit tests for Greeks Calculator.

Tests for options Greeks calculations using Black-Scholes-Merton model.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import numpy as np
from scipy.stats import norm

from app.engines.risk_engine.greeks_calculator import GreeksCalculator


@pytest.fixture
def calculator():
    """Create GreeksCalculator instance with default config."""
    return GreeksCalculator()


@pytest.fixture
def custom_calculator():
    """Create GreeksCalculator with custom rates."""
    config = {
        'risk_free_rate': 0.03,
        'dividend_yield': 0.02
    }
    return GreeksCalculator(config)


@pytest.fixture
def valid_call_params():
    """Valid parameters for a call option."""
    return {
        'option_type': 'call',
        'spot_price': 100.0,
        'strike_price': 100.0,
        'time_to_expiry': 0.25,  # 3 months
        'volatility': 0.20,
    }


@pytest.fixture
def valid_put_params():
    """Valid parameters for a put option."""
    return {
        'option_type': 'put',
        'spot_price': 100.0,
        'strike_price': 95.0,
        'time_to_expiry': 0.5,  # 6 months
        'volatility': 0.25,
    }


@pytest.mark.unit
class TestGreeksCalculatorInitialization:
    """Test GreeksCalculator initialization and configuration."""

    def test_default_initialization(self, calculator):
        """Test calculator with default configuration."""
        assert calculator.risk_free_rate == 0.05
        assert calculator.dividend_yield == 0.0

    def test_custom_initialization(self, custom_calculator):
        """Test calculator with custom configuration."""
        assert custom_calculator.risk_free_rate == 0.03
        assert custom_calculator.dividend_yield == 0.02

    def test_empty_config_uses_defaults(self):
        """Test that empty config dict uses defaults."""
        calc = GreeksCalculator(config={})
        assert calc.risk_free_rate == 0.05
        assert calc.dividend_yield == 0.0


@pytest.mark.unit
class TestCalculateAllGreeks:
    """Test comprehensive Greeks calculation."""

    def test_calculate_call_greeks_success(self, calculator, valid_call_params):
        """Test successful Greeks calculation for call option."""
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' not in result
        assert result['option_type'] == 'call'
        assert 'primary_greeks' in result
        assert 'higher_order_greeks' in result
        assert 'risk_metrics' in result

        # Check primary Greeks exist
        greeks = result['primary_greeks']
        assert 'delta' in greeks
        assert 'gamma' in greeks
        assert 'theta' in greeks
        assert 'vega' in greeks
        assert 'rho' in greeks

        # Check higher-order Greeks
        higher = result['higher_order_greeks']
        assert 'vanna' in higher
        assert 'vomma' in higher
        assert 'charm' in higher
        assert 'veta' in higher

    def test_calculate_put_greeks_success(self, calculator, valid_put_params):
        """Test successful Greeks calculation for put option."""
        result = calculator.calculate_all_greeks(**valid_put_params)

        assert 'error' not in result
        assert result['option_type'] == 'put'

        # Put delta should be negative
        assert result['primary_greeks']['delta'] < 0

    def test_greeks_with_custom_rates(self, custom_calculator, valid_call_params):
        """Test Greeks calculation with custom rates."""
        result = custom_calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' not in result
        assert result['option_price'] > 0

    def test_invalid_time_to_expiry(self, calculator, valid_call_params):
        """Test error handling for invalid time to expiry."""
        valid_call_params['time_to_expiry'] = 0
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' in result
        assert 'positive time to expiry' in result['error']

    def test_negative_time_to_expiry(self, calculator, valid_call_params):
        """Test error handling for negative time to expiry."""
        valid_call_params['time_to_expiry'] = -0.1
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' in result

    def test_invalid_volatility(self, calculator, valid_call_params):
        """Test error handling for invalid volatility."""
        valid_call_params['volatility'] = 0
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' in result
        assert 'Volatility must be positive' in result['error']

    def test_negative_volatility(self, calculator, valid_call_params):
        """Test error handling for negative volatility."""
        valid_call_params['volatility'] = -0.1
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' in result

    def test_invalid_option_type(self, calculator, valid_call_params):
        """Test error handling for invalid option type."""
        valid_call_params['option_type'] = 'invalid'
        result = calculator.calculate_all_greeks(**valid_call_params)

        # Should raise error in delta calculation
        assert 'error' in result


@pytest.mark.unit
class TestDeltaCalculation:
    """Test Delta calculation specifically."""

    def test_call_delta_range(self, calculator):
        """Test that call delta is in [0, 1]."""
        params = {
            'option_type': 'call',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }
        result = calculator.calculate_all_greeks(**params)
        delta = result['primary_greeks']['delta']

        assert 0 <= delta <= 1

    def test_put_delta_range(self, calculator):
        """Test that put delta is in [-1, 0]."""
        params = {
            'option_type': 'put',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }
        result = calculator.calculate_all_greeks(**params)
        delta = result['primary_greeks']['delta']

        assert -1 <= delta <= 0

    def test_deep_itm_call_delta(self, calculator):
        """Test deep ITM call has delta close to 1."""
        params = {
            'option_type': 'call',
            'spot_price': 150.0,  # Well above strike
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }
        result = calculator.calculate_all_greeks(**params)
        delta = result['primary_greeks']['delta']

        assert delta > 0.9

    def test_deep_otm_call_delta(self, calculator):
        """Test deep OTM call has delta close to 0."""
        params = {
            'option_type': 'call',
            'spot_price': 50.0,  # Well below strike
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }
        result = calculator.calculate_all_greeks(**params)
        delta = result['primary_greeks']['delta']

        assert delta < 0.1

    def test_atm_delta_approximately_05(self, calculator):
        """Test ATM call has delta approximately 0.5."""
        params = {
            'option_type': 'call',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }
        result = calculator.calculate_all_greeks(**params)
        delta = result['primary_greeks']['delta']

        # ATM call delta should be close to 0.5
        assert 0.45 <= delta <= 0.55


@pytest.mark.unit
class TestGammaCalculation:
    """Test Gamma calculation."""

    def test_gamma_positive_for_call(self, calculator, valid_call_params):
        """Test that gamma is always positive for calls."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        gamma = result['primary_greeks']['gamma']

        assert gamma > 0

    def test_gamma_positive_for_put(self, calculator, valid_put_params):
        """Test that gamma is always positive for puts."""
        result = calculator.calculate_all_greeks(**valid_put_params)
        gamma = result['primary_greeks']['gamma']

        assert gamma > 0

    def test_gamma_highest_near_atm(self, calculator):
        """Test that gamma is highest near ATM."""
        # Test three scenarios: OTM, ATM, ITM
        scenarios = [
            {'spot': 90, 'strike': 100},  # OTM
            {'spot': 100, 'strike': 100},  # ATM
            {'spot': 110, 'strike': 100},  # ITM
        ]

        gammas = []
        for scenario in scenarios:
            params = {
                'option_type': 'call',
                'spot_price': scenario['spot'],
                'strike_price': scenario['strike'],
                'time_to_expiry': 0.25,
                'volatility': 0.20,
            }
            result = calculator.calculate_all_greeks(**params)
            gammas.append(result['primary_greeks']['gamma'])

        # ATM should have highest gamma
        assert gammas[1] > gammas[0]  # ATM > OTM
        assert gammas[1] > gammas[2]  # ATM > ITM

    def test_gamma_increases_as_expiry_approaches(self, calculator):
        """Test that gamma increases as expiration approaches."""
        short_term_params = {
            'option_type': 'call',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.01,  # Very short term
            'volatility': 0.20,
        }

        long_term_params = short_term_params.copy()
        long_term_params['time_to_expiry'] = 1.0  # One year

        short_result = calculator.calculate_all_greeks(**short_term_params)
        long_result = calculator.calculate_all_greeks(**long_term_params)

        assert short_result['primary_greeks']['gamma'] > long_result['primary_greeks']['gamma']


@pytest.mark.unit
class TestThetaCalculation:
    """Test Theta calculation."""

    def test_theta_negative_for_long_call(self, calculator, valid_call_params):
        """Test that theta is negative for long call (time decay)."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        theta = result['primary_greeks']['theta']

        assert theta < 0

    def test_theta_negative_for_long_put(self, calculator, valid_put_params):
        """Test that theta is negative for long put."""
        result = calculator.calculate_all_greeks(**valid_put_params)
        theta = result['primary_greeks']['theta']

        assert theta < 0

    def test_theta_annual_conversion(self, calculator, valid_call_params):
        """Test that theta_annual is approximately 365 * theta."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        theta_daily = result['primary_greeks']['theta']
        theta_annual = result['primary_greeks']['theta_annual']

        assert abs(theta_annual - theta_daily * 365) < 0.01

    def test_theta_acceleration_near_expiry(self, calculator):
        """Test that theta decay accelerates near expiry."""
        near_expiry_params = {
            'option_type': 'call',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.01,  # ~3.5 days
            'volatility': 0.20,
        }

        far_expiry_params = near_expiry_params.copy()
        far_expiry_params['time_to_expiry'] = 0.5

        near_result = calculator.calculate_all_greeks(**near_expiry_params)
        far_result = calculator.calculate_all_greeks(**far_expiry_params)

        # Near expiry should have more negative theta (faster decay)
        assert abs(near_result['primary_greeks']['theta']) > abs(far_result['primary_greeks']['theta'])


@pytest.mark.unit
class TestVegaCalculation:
    """Test Vega calculation."""

    def test_vega_positive(self, calculator, valid_call_params):
        """Test that vega is positive (long options benefit from vol increase)."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        vega = result['primary_greeks']['vega']

        assert vega > 0

    def test_vega_same_for_call_and_put(self, calculator):
        """Test that vega is same for call and put with same params."""
        params = {
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }

        call_result = calculator.calculate_all_greeks(option_type='call', **params)
        put_result = calculator.calculate_all_greeks(option_type='put', **params)

        assert abs(call_result['primary_greeks']['vega'] - put_result['primary_greeks']['vega']) < 0.0001

    def test_vega_highest_for_atm(self, calculator):
        """Test that vega is highest for ATM options."""
        scenarios = [
            {'spot': 90, 'strike': 100},  # OTM
            {'spot': 100, 'strike': 100},  # ATM
            {'spot': 110, 'strike': 100},  # ITM
        ]

        vegas = []
        for scenario in scenarios:
            params = {
                'option_type': 'call',
                'spot_price': scenario['spot'],
                'strike_price': scenario['strike'],
                'time_to_expiry': 0.25,
                'volatility': 0.20,
            }
            result = calculator.calculate_all_greeks(**params)
            vegas.append(result['primary_greeks']['vega'])

        # ATM should have highest vega
        assert vegas[1] > vegas[0]
        assert vegas[1] > vegas[2]


@pytest.mark.unit
class TestHigherOrderGreeks:
    """Test higher-order Greeks calculations."""

    def test_vanna_calculation(self, calculator, valid_call_params):
        """Test vanna calculation."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        vanna = result['higher_order_greeks']['vanna']

        # Vanna can be positive or negative
        assert isinstance(vanna, float)

    def test_vomma_calculation(self, calculator, valid_call_params):
        """Test vomma calculation."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        vomma = result['higher_order_greeks']['vomma']

        # Vomma can be positive or negative
        assert isinstance(vomma, float)

    def test_charm_calculation(self, calculator, valid_call_params):
        """Test charm calculation."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        charm = result['higher_order_greeks']['charm']

        # Charm should exist
        assert isinstance(charm, float)

    def test_veta_calculation(self, calculator, valid_call_params):
        """Test veta calculation."""
        result = calculator.calculate_all_greeks(**valid_call_params)
        veta = result['higher_order_greeks']['veta']

        # Veta should exist
        assert isinstance(veta, float)


@pytest.mark.unit
class TestPortfolioGreeks:
    """Test portfolio-level Greeks calculations."""

    @pytest.fixture
    def sample_positions(self):
        """Create sample option positions."""
        return [
            {
                'symbol': 'AAPL',
                'option_type': 'call',
                'spot_price': 100.0,
                'strike_price': 100.0,
                'time_to_expiry': 0.25,
                'volatility': 0.20,
                'quantity': 10,
            },
            {
                'symbol': 'AAPL',
                'option_type': 'put',
                'spot_price': 100.0,
                'strike_price': 95.0,
                'time_to_expiry': 0.25,
                'volatility': 0.20,
                'quantity': 5,
            }
        ]

    def test_calculate_portfolio_greeks_success(self, calculator, sample_positions):
        """Test successful portfolio Greeks calculation."""
        result = calculator.calculate_portfolio_greeks(sample_positions)

        assert 'error' not in result
        assert 'total_delta' in result
        assert 'total_gamma' in result
        assert 'total_theta' in result
        assert 'total_vega' in result
        assert 'total_rho' in result
        assert 'positions' in result
        assert 'analysis' in result

    def test_portfolio_greeks_aggregation(self, calculator, sample_positions):
        """Test that portfolio Greeks are properly aggregated."""
        result = calculator.calculate_portfolio_greeks(sample_positions)

        # Should have 2 positions
        assert len(result['positions']) == 2

        # Totals should be non-zero
        assert result['total_delta'] != 0
        assert result['total_gamma'] > 0  # Gamma always positive

    def test_portfolio_analysis_risk_assessment(self, calculator, sample_positions):
        """Test portfolio risk analysis."""
        result = calculator.calculate_portfolio_greeks(sample_positions)
        analysis = result['analysis']

        assert 'delta_neutral' in analysis
        assert 'gamma_exposure' in analysis
        assert 'theta_profile' in analysis
        assert 'vega_exposure' in analysis
        assert 'risk_warnings' in analysis
        assert 'overall_risk' in analysis

    def test_empty_portfolio(self, calculator):
        """Test handling of empty portfolio."""
        result = calculator.calculate_portfolio_greeks([])

        assert 'error' not in result
        assert result['total_delta'] == 0
        assert result['total_gamma'] == 0

    def test_portfolio_with_invalid_position(self, calculator, sample_positions):
        """Test portfolio with one invalid position."""
        # Add invalid position
        sample_positions.append({
            'symbol': 'INVALID',
            'option_type': 'call',
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0,  # Invalid
            'volatility': 0.20,
        })

        result = calculator.calculate_portfolio_greeks(sample_positions)

        # Should skip invalid position
        assert 'error' not in result
        assert len(result['positions']) == 2  # Only valid positions


@pytest.mark.unit
class TestDeltaHedgeRatio:
    """Test delta hedge ratio calculation."""

    def test_calculate_hedge_ratio_success(self, calculator, valid_call_params):
        """Test successful hedge ratio calculation."""
        valid_call_params['quantity'] = 10
        result = calculator.calculate_delta_hedge_ratio(valid_call_params)

        assert 'error' not in result
        assert 'hedge_ratio' in result
        assert 'shares_to_trade' in result
        assert 'action' in result
        assert 'hedge_effectiveness' in result

    def test_hedge_ratio_for_call(self, calculator, valid_call_params):
        """Test hedge ratio for call option."""
        valid_call_params['quantity'] = 10
        result = calculator.calculate_delta_hedge_ratio(valid_call_params)

        # For long call, need to sell shares to hedge
        assert result['action'] in ['BUY', 'SELL_SHORT']

    def test_hedge_ratio_for_put(self, calculator, valid_put_params):
        """Test hedge ratio for put option."""
        valid_put_params['quantity'] = 10
        result = calculator.calculate_delta_hedge_ratio(valid_put_params)

        # For long put, need to buy shares to hedge
        assert result['action'] in ['BUY', 'SELL_SHORT']

    def test_hedge_ratio_quantity_scaling(self, calculator, valid_call_params):
        """Test that hedge ratio scales with quantity."""
        params_1 = valid_call_params.copy()
        params_1['quantity'] = 10
        result_1 = calculator.calculate_delta_hedge_ratio(params_1)

        params_2 = valid_call_params.copy()
        params_2['quantity'] = 20
        result_2 = calculator.calculate_delta_hedge_ratio(params_2)

        # Hedge ratio should double
        assert abs(result_2['hedge_ratio']) == abs(result_1['hedge_ratio']) * 2


@pytest.mark.unit
class TestGreeksValidation:
    """Test Greeks validation functions."""

    @pytest.fixture
    def valid_greeks_result(self, calculator, valid_call_params):
        """Create valid Greeks result for testing."""
        return calculator.calculate_all_greeks(**valid_call_params)

    def test_validate_greeks_consistency_success(self, calculator, valid_greeks_result):
        """Test successful validation."""
        result = calculator.validate_greeks_consistency(valid_greeks_result)

        assert 'valid' in result
        assert 'validation_issues' in result
        assert 'warnings' in result
        assert 'greeks_checked' in result

    def test_validate_gamma_positive(self, calculator, valid_greeks_result):
        """Test that gamma validation catches negative gamma."""
        # Manually set negative gamma
        valid_greeks_result['primary_greeks']['gamma'] = -0.1
        result = calculator.validate_greeks_consistency(valid_greeks_result)

        assert result['valid'] is False
        assert any('Gamma must be positive' in issue for issue in result['validation_issues'])

    def test_validate_vega_positive(self, calculator, valid_greeks_result):
        """Test that vega validation catches negative vega."""
        valid_greeks_result['primary_greeks']['vega'] = -0.1
        result = calculator.validate_greeks_consistency(valid_greeks_result)

        assert result['valid'] is False
        assert any('Vega must be positive' in issue for issue in result['validation_issues'])

    def test_validate_call_delta_range(self, calculator, valid_greeks_result):
        """Test call delta range validation."""
        valid_greeks_result['primary_greeks']['delta'] = 1.5  # Out of range
        result = calculator.validate_greeks_consistency(valid_greeks_result)

        assert len(result['warnings']) > 0

    def test_validate_put_delta_range(self, calculator, valid_put_params):
        """Test put delta range validation."""
        result = calculator.calculate_all_greeks(**valid_put_params)
        result['primary_greeks']['delta'] = 0.5  # Out of range for put
        validation = calculator.validate_greeks_consistency(result)

        assert len(validation['warnings']) > 0


@pytest.mark.unit
class TestGreeksRiskLimits:
    """Test portfolio Greeks risk limit validation."""

    @pytest.fixture
    def sample_portfolio_greeks(self):
        """Create sample portfolio Greeks."""
        return {
            'total_delta': 50.0,
            'total_gamma': 2.0,
            'total_theta': -50.0,
            'total_vega': 100.0,
            'total_rho': 30.0,
        }

    def test_validate_within_default_limits(self, calculator, sample_portfolio_greeks):
        """Test portfolio within default limits."""
        result = calculator.validate_greeks_risk_limits(sample_portfolio_greeks)

        assert result['within_limits'] is True
        assert len(result['violations']) == 0

    def test_validate_delta_limit_violation(self, calculator, sample_portfolio_greeks):
        """Test delta limit violation."""
        sample_portfolio_greeks['total_delta'] = 150.0  # Exceeds default
        result = calculator.validate_greeks_risk_limits(sample_portfolio_greeks)

        assert result['within_limits'] is False
        assert any(v['greek'] == 'delta' for v in result['violations'])

    def test_validate_gamma_limit_violation(self, calculator, sample_portfolio_greeks):
        """Test gamma limit violation."""
        sample_portfolio_greeks['total_gamma'] = -10.0  # Exceeds default
        result = calculator.validate_greeks_risk_limits(sample_portfolio_greeks)

        assert result['within_limits'] is False
        assert any(v['greek'] == 'gamma' for v in result['violations'])

    def test_validate_custom_limits(self, calculator, sample_portfolio_greeks):
        """Test with custom risk limits."""
        custom_limits = {
            'max_delta': 10,
            'max_gamma': 1,
            'max_theta': -10,
            'max_vega': 50,
            'max_rho': 20,
        }

        sample_portfolio_greeks['total_delta'] = 50.0
        result = calculator.validate_greeks_risk_limits(sample_portfolio_greeks, limits=custom_limits)

        assert result['within_limits'] is False

    def test_risk_score_calculation(self, calculator, sample_portfolio_greeks):
        """Test risk score calculation."""
        # Create multiple violations
        sample_portfolio_greeks['total_delta'] = 200.0
        sample_portfolio_greeks['total_gamma'] = -10.0
        sample_portfolio_greeks['total_theta'] = -2000.0

        result = calculator.validate_greeks_risk_limits(sample_portfolio_greeks)

        assert 'risk_score' in result
        assert 'risk_level' in result
        assert result['risk_score'] > 0


@pytest.mark.unit
class TestSensitivityAnalysis:
    """Test Greeks sensitivity analysis."""

    def test_sensitivity_analysis_success(self, calculator, valid_call_params):
        """Test successful sensitivity analysis."""
        result = calculator.calculate_greeks_sensitivity_analysis(valid_call_params)

        assert 'error' not in result
        assert 'base_greeks' in result
        assert 'sensitivity_analysis' in result
        assert 'scenarios_applied' in result

    def test_spot_sensitivity_calculation(self, calculator, valid_call_params):
        """Test spot price sensitivity calculation."""
        result = calculator.calculate_greeks_sensitivity_analysis(valid_call_params)

        sensitivity = result['sensitivity_analysis']
        assert 'spot_sensitivity' in sensitivity
        assert 'delta_change_up' in sensitivity['spot_sensitivity']
        assert 'delta_change_down' in sensitivity['spot_sensitivity']

    def test_volatility_sensitivity_calculation(self, calculator, valid_call_params):
        """Test volatility sensitivity calculation."""
        result = calculator.calculate_greeks_sensitivity_analysis(valid_call_params)

        sensitivity = result['sensitivity_analysis']
        assert 'volatility_sensitivity' in sensitivity
        assert 'vega_change_up' in sensitivity['volatility_sensitivity']
        assert 'vega_change_down' in sensitivity['volatility_sensitivity']

    def test_custom_shock_scenarios(self, calculator, valid_call_params):
        """Test with custom shock scenarios."""
        custom_scenarios = {
            'spot_shock_pct': 0.10,  # 10% instead of 5%
            'vol_shock_pct': 0.20,  # 20% instead of 10%
        }

        result = calculator.calculate_greeks_sensitivity_analysis(
            valid_call_params,
            shock_scenarios=custom_scenarios
        )

        assert result['scenarios_applied']['spot_shock_pct'] == 0.10
        assert result['scenarios_applied']['vol_shock_pct'] == 0.20

    def test_sensitivity_assessment(self, calculator, valid_call_params):
        """Test overall sensitivity assessment."""
        result = calculator.calculate_greeks_sensitivity_analysis(valid_call_params)

        sensitivity = result['sensitivity_analysis']
        assert 'assessment' in sensitivity
        assert 'stability_score' in sensitivity['assessment']
        assert 'stability_level' in sensitivity['assessment']
        assert 'risk_factors' in sensitivity['assessment']


@pytest.mark.unit
class TestRiskMetrics:
    """Test risk metrics calculation."""

    def test_risk_metrics_calculation(self, calculator, valid_call_params):
        """Test risk metrics are calculated."""
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'risk_metrics' in result
        assert 'delta_exposure' in result['risk_metrics']
        assert 'gamma_profile' in result['risk_metrics']
        assert 'vega_profile' in result['risk_metrics']
        assert 'risk_interpretation' in result['risk_metrics']

    def test_gamma_profile_classification(self, calculator, valid_call_params):
        """Test gamma profile classification."""
        result = calculator.calculate_all_greeks(**valid_call_params)

        profile = result['risk_metrics']['gamma_profile']
        assert profile in ['long_gamma', 'short_gamma']

    def test_vega_profile_classification(self, calculator, valid_call_params):
        """Test vega profile classification."""
        result = calculator.calculate_all_greeks(**valid_call_params)

        profile = result['risk_metrics']['vega_profile']
        assert profile in ['long_vega', 'short_vega']

    def test_risk_interpretation_generation(self, calculator, valid_call_params):
        """Test risk interpretation is generated."""
        result = calculator.calculate_all_greeks(**valid_call_params)

        interpretation = result['risk_metrics']['risk_interpretation']
        assert isinstance(interpretation, str)
        assert len(interpretation) > 0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_low_volatility(self, calculator, valid_call_params):
        """Test with very low volatility."""
        valid_call_params['volatility'] = 0.01
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' not in result

    def test_very_high_volatility(self, calculator, valid_call_params):
        """Test with very high volatility."""
        valid_call_params['volatility'] = 2.0  # 200%
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' not in result

    def test_very_short_dated_option(self, calculator, valid_call_params):
        """Test with very short time to expiry."""
        valid_call_params['time_to_expiry'] = 0.001  # ~0.365 days
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' not in result

    def test_very_long_dated_option(self, calculator, valid_call_params):
        """Test with very long time to expiry."""
        valid_call_params['time_to_expiry'] = 5.0  # 5 years
        result = calculator.calculate_all_greeks(**valid_call_params)

        assert 'error' not in result

    def test_zero_spot_price(self, calculator, valid_call_params):
        """Test with zero spot price."""
        valid_call_params['spot_price'] = 0
        result = calculator.calculate_all_greeks(**valid_call_params)

        # Should handle gracefully or return error
        assert 'error' in result or result['option_price'] == 0

    def test_extreme_moneyness(self, calculator):
        """Test extreme moneyness scenarios."""
        # Deep ITM
        params = {
            'option_type': 'call',
            'spot_price': 1000.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }
        result = calculator.calculate_all_greeks(**params)
        assert 'error' not in result

        # Deep OTM
        params['spot_price'] = 10.0
        result = calculator.calculate_all_greeks(**params)
        assert 'error' not in result


@pytest.mark.unit
class TestNumericalStability:
    """Test numerical stability of calculations."""

    def test_put_call_parity_approximation(self, calculator):
        """Test put-call parity holds approximately."""
        params = {
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
            'risk_free_rate': 0.05,
            'dividend_yield': 0.0,
        }

        call_result = calculator.calculate_all_greeks(option_type='call', **params)
        put_result = calculator.calculate_all_greeks(option_type='put', **params)

        # Put-call parity: C - P = S - K*e^(-rT)
        call_price = call_result['option_price']
        put_price = put_result['option_price']
        S = params['spot_price']
        K = params['strike_price']
        r = params['risk_free_rate']
        T = params['time_to_expiry']

        lhs = call_price - put_price
        rhs = S - K * np.exp(-r * T)

        # Should be close
        assert abs(lhs - rhs) < 0.01

    def test_greeks_smoothness(self, calculator):
        """Test that Greeks change smoothly with spot price."""
        base_params = {
            'option_type': 'call',
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.20,
        }

        spot_prices = [95.0, 96.0, 97.0, 98.0, 99.0, 100.0]
        deltas = []

        for spot in spot_prices:
            base_params['spot_price'] = spot
            result = calculator.calculate_all_greeks(**base_params)
            deltas.append(result['primary_greeks']['delta'])

        # Deltas should be monotonically increasing for calls
        for i in range(len(deltas) - 1):
            assert deltas[i + 1] >= deltas[i]
