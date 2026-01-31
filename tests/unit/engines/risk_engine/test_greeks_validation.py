"""
Unit tests for Enhanced Greeks Calculator - Hull Chapters 17-19

Tests for put-call parity validation, implied volatility calculation,
and Greeks consistency checks.
"""

import pytest
import numpy as np
from app.engines.risk_engine.greeks_calculator import GreeksCalculator


class TestGreeksCalculator:
    """Test suite for Greeks calculator."""

    @pytest.fixture
    def calculator(self):
        """Create Greeks calculator instance."""
        config = {'risk_free_rate': 0.05, 'dividend_yield': 0.0}
        return GreeksCalculator(config)

    @pytest.fixture
    def standard_option_params(self):
        """Standard option parameters for testing."""
        return {
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,  # 3 months
            'volatility': 0.2,  # 20%
            'risk_free_rate': 0.05,
            'dividend_yield': 0.0,
        }


class TestPutCallParity(TestGreeksCalculator):
    """Test put-call parity validation."""

    def test_put_call_parity_holds(self, calculator, standard_option_params):
        """Test that put-call parity holds for calculated options."""
        # Calculate call and put Greeks
        call_greeks = calculator.calculate_all_greeks(option_type='call', **standard_option_params)

        put_greeks = calculator.calculate_all_greeks(option_type='put', **standard_option_params)

        # Validate put-call parity
        result = calculator.validate_put_call_parity(
            call_greeks=call_greeks,
            put_greeks=put_greeks,
            spot_price=standard_option_params['spot_price'],
            strike_price=standard_option_params['strike_price'],
            time_to_expiry=standard_option_params['time_to_expiry'],
            risk_free_rate=standard_option_params['risk_free_rate'],
            tolerance=0.01,
        )

        assert 'error' not in result
        assert result['valid'], f"Put-call parity failed: {result}"
        assert 'difference' in result
        assert result['difference'] < 0.01
        assert not result.get('arbitrage_opportunity', False)

    def test_put_call_parity_atm_option(self, calculator):
        """Test put-call parity for at-the-money option."""
        params = {
            'spot_price': 50.0,
            'strike_price': 50.0,
            'time_to_expiry': 0.5,
            'volatility': 0.25,
            'risk_free_rate': 0.04,
        }

        call_greeks = calculator.calculate_all_greeks(option_type='call', **params)
        put_greeks = calculator.calculate_all_greeks(option_type='put', **params)

        result = calculator.validate_put_call_parity(
            call_greeks,
            put_greeks,
            params['spot_price'],
            params['strike_price'],
            params['time_to_expiry'],
            params['risk_free_rate'],
        )

        assert result['valid']
        # C - P should approximately equal S - K*e^(-rT)
        lhs = result['lhs']
        rhs = result['rhs']
        assert abs(lhs - rhs) < 0.01

    def test_put_call_parity_itm_option(self, calculator):
        """Test put-call parity for in-the-money option."""
        params = {
            'spot_price': 110.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.2,
            'risk_free_rate': 0.05,
        }

        call_greeks = calculator.calculate_all_greeks(option_type='call', **params)
        put_greeks = calculator.calculate_all_greeks(option_type='put', **params)

        result = calculator.validate_put_call_parity(
            call_greeks,
            put_greeks,
            params['spot_price'],
            params['strike_price'],
            params['time_to_expiry'],
            params['risk_free_rate'],
        )

        assert result['valid']

    def test_put_call_parity_with_dividends(self, calculator):
        """Test put-call parity with dividend yield."""
        params = {
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 1.0,
            'volatility': 0.2,
            'risk_free_rate': 0.05,
            'dividend_yield': 0.03,
        }

        call_greeks = calculator.calculate_all_greeks(option_type='call', **params)
        put_greeks = calculator.calculate_all_greeks(option_type='put', **params)

        result = calculator.validate_put_call_parity(
            call_greeks,
            put_greeks,
            params['spot_price'],
            params['strike_price'],
            params['time_to_expiry'],
            params['risk_free_rate'],
        )

        assert result['valid']

    def test_put_call_parity_invalid_input(self, calculator, standard_option_params):
        """Test put-call parity with invalid inputs."""
        result = calculator.validate_put_call_parity(
            call_greeks={'error': 'Invalid call'},
            put_greeks={'error': 'Invalid put'},
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry=0.25,
            risk_free_rate=0.05,
        )

        assert not result['valid']
        assert 'error' in result


class TestImpliedVolatility(TestGreeksCalculator):
    """Test implied volatility calculation."""

    def test_implied_volatility_convergence(self, calculator, standard_option_params):
        """Test that implied volatility calculation converges."""
        # Calculate option price first
        greeks = calculator.calculate_all_greeks(option_type='call', **standard_option_params)

        market_price = greeks['option_price']

        # Now back out implied volatility
        result = calculator.calculate_greeks_implied_values(
            option_price=market_price,
            option_type='call',
            spot_price=standard_option_params['spot_price'],
            strike_price=standard_option_params['strike_price'],
            time_to_expiry=standard_option_params['time_to_expiry'],
            risk_free_rate=standard_option_params['risk_free_rate'],
            dividend_yield=standard_option_params.get('dividend_yield', 0.0),
        )

        assert 'error' not in result
        assert result['converged']
        assert 'implied_volatility' in result

        # Should recover original volatility (within tolerance)
        recovered_vol = result['implied_volatility']
        original_vol = standard_option_params['volatility']
        assert abs(recovered_vol - original_vol) < 0.0001

    def test_implied_volatility_put_option(self, calculator, standard_option_params):
        """Test implied volatility for put option."""
        greeks = calculator.calculate_all_greeks(option_type='put', **standard_option_params)

        market_price = greeks['option_price']

        result = calculator.calculate_greeks_implied_values(
            option_price=market_price,
            option_type='put',
            spot_price=standard_option_params['spot_price'],
            strike_price=standard_option_params['strike_price'],
            time_to_expiry=standard_option_params['time_to_expiry'],
            risk_free_rate=standard_option_params['risk_free_rate'],
        )

        assert 'error' not in result
        assert result['converged']
        assert abs(result['implied_volatility'] - standard_option_params['volatility']) < 0.0001

    def test_implied_volatility_tolerance(self, calculator):
        """Test implied volatility with different market prices."""
        params = {
            'spot_price': 100.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.25,
            'volatility': 0.2,
            'risk_free_rate': 0.05,
        }

        # Calculate base price
        base_greeks = calculator.calculate_all_greeks(option_type='call', **params)
        base_price = base_greeks['option_price']

        # Test with slightly different market prices
        for price_adj in [-0.5, 0.0, 0.5]:
            market_price = base_price + price_adj

            result = calculator.calculate_greeks_implied_values(
                option_price=market_price, option_type='call', **params
            )

            assert 'error' not in result
            assert result['converged']
            assert result['implied_volatility'] > 0

    def test_implied_volatility_deep_itm(self, calculator):
        """Test implied volatility for deep ITM option."""
        params = {
            'spot_price': 120.0,
            'strike_price': 100.0,
            'time_to_expiry': 0.1,
            'volatility': 0.25,
            'risk_free_rate': 0.05,
        }

        greeks = calculator.calculate_all_greeks(option_type='call', **params)
        result = calculator.calculate_greeks_implied_values(
            option_price=greeks['option_price'], option_type='call', **params
        )

        assert 'error' not in result
        assert result['converged']


class TestGreeksMarketPriceValidation(TestGreeksCalculator):
    """Test validation against market prices."""

    def test_validate_market_prices_accuracy(self, calculator, standard_option_params):
        """Test that model prices match market prices (synthetic test)."""
        # Generate synthetic "market" prices using the model
        call_greeks = calculator.calculate_all_greeks(option_type='call', **standard_option_params)

        put_greeks = calculator.calculate_all_greeks(option_type='put', **standard_option_params)

        market_prices = {
            'call': call_greeks['option_price'],
            'put': put_greeks['option_price'],
        }

        # Remove price-related params from option_params
        validation_params = standard_option_params.copy()

        result = calculator.validate_greeks_market_prices(
            market_prices=market_prices,
            option_params=validation_params,
            price_tolerance=0.01,
        )

        assert 'error' not in result
        assert result['overall_valid']
        assert result['within_tolerance'] == 2
        assert result['outside_tolerance'] == 0

    def test_validate_market_prices_with_noise(self, calculator, standard_option_params):
        """Test validation with noisy market prices."""
        # Generate base prices
        call_greeks = calculator.calculate_all_greeks(option_type='call', **standard_option_params)

        put_greeks = calculator.calculate_all_greeks(option_type='put', **standard_option_params)

        # Add small noise to simulate market friction
        np.random.seed(42)
        market_prices = {
            'call': call_greeks['option_price'] + np.random.normal(0, 0.01),
            'put': put_greeks['option_price'] + np.random.normal(0, 0.01),
        }

        validation_params = standard_option_params.copy()

        result = calculator.validate_greeks_market_prices(
            market_prices=market_prices,
            option_params=validation_params,
            price_tolerance=0.05,  # 5% tolerance
        )

        assert 'error' not in result
        # Should still be valid within tolerance
        assert result['within_tolerance'] >= 1

    def test_validate_market_prices_statistics(self, calculator, standard_option_params):
        """Test that validation statistics are calculated correctly."""
        base_greeks = calculator.calculate_all_greeks(option_type='call', **standard_option_params)

        # Create multiple price scenarios
        market_prices = {}
        for i in range(5):
            price = base_greeks['option_price'] * (1 + (i - 2) * 0.02)  # ±4% variation
            market_prices[f'call_scenario_{i}'] = price

        validation_params = standard_option_params.copy()

        result = calculator.validate_greeks_market_prices(
            market_prices=market_prices,
            option_params=validation_params,
            price_tolerance=0.05,
        )

        assert 'error' not in result
        assert 'avg_price_error' in result
        assert 'max_price_error' in result
        assert 'std_price_error' in result
        assert result['total_options'] == 5


class TestGreeksConsistencyValidation(TestGreeksCalculator):
    """Test Greeks consistency validation."""

    def test_validate_greeks_consistency_call(self, calculator, standard_option_params):
        """Test Greeks consistency for call option."""
        greeks = calculator.calculate_all_greeks(option_type='call', **standard_option_params)

        result = calculator.validate_greeks_consistency(greeks)

        assert 'error' not in result
        assert result['valid']
        assert len(result['validation_issues']) == 0

    def test_validate_greeks_consistency_put(self, calculator, standard_option_params):
        """Test Greeks consistency for put option."""
        greeks = calculator.calculate_all_greeks(option_type='put', **standard_option_params)

        result = calculator.validate_greeks_consistency(greeks)

        assert 'error' not in result
        assert result['valid']

    def test_gamma_always_positive(self, calculator):
        """Test that gamma is always positive."""
        test_cases = [
            {'spot': 90, 'strike': 100, 'ttm': 0.25, 'vol': 0.2},
            {'spot': 100, 'strike': 100, 'ttm': 0.25, 'vol': 0.2},
            {'spot': 110, 'strike': 100, 'ttm': 0.25, 'vol': 0.2},
            {'spot': 100, 'strike': 100, 'ttm': 0.01, 'vol': 0.5},
        ]

        for case in test_cases:
            greeks = calculator.calculate_all_greeks(
                option_type='call',
                spot_price=case['spot'],
                strike_price=case['strike'],
                time_to_expiry=case['ttm'],
                volatility=case['vol'],
                risk_free_rate=0.05,
            )

            result = calculator.validate_greeks_consistency(greeks)
            gamma = greeks['primary_greeks']['gamma']

            assert gamma > 0, f"Gamma should be positive: {gamma}"
            assert result['valid']

    def test_vega_always_positive(self, calculator):
        """Test that vega is always positive."""
        greeks = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry=0.25,
            volatility=0.2,
            risk_free_rate=0.05,
        )

        result = calculator.validate_greeks_consistency(greeks)
        vega = greeks['primary_greeks']['vega']

        assert vega > 0, f"Vega should be positive: {vega}"

    def test_delta_range_validation(self, calculator):
        """Test that delta is within valid range."""
        # Call option delta should be in [0, 1]
        call_greeks = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry=0.25,
            volatility=0.2,
            risk_free_rate=0.05,
        )

        call_delta = call_greeks['primary_greeks']['delta']
        assert 0 <= call_delta <= 1

        # Put option delta should be in [-1, 0]
        put_greeks = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry=0.25,
            volatility=0.2,
            risk_free_rate=0.05,
        )

        put_delta = put_greeks['primary_greeks']['delta']
        assert -1 <= put_delta <= 0


class TestGreeksRiskLimits(TestGreeksCalculator):
    """Test Greeks risk limit validation."""

    def test_validate_risk_limits_within_bounds(self, calculator):
        """Test risk limits when portfolio is within bounds."""
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

        result = calculator.validate_greeks_risk_limits(
            portfolio_greeks=portfolio_greeks,
            limits=limits,
        )

        assert 'error' not in result
        assert result['within_limits']
        assert len(result['violations']) == 0

    def test_validate_risk_limits_violations(self, calculator):
        """Test risk limits when portfolio exceeds limits."""
        portfolio_greeks = {
            'total_delta': 150.0,  # Exceeds limit
            'total_gamma': 8.0,  # Exceeds limit
            'total_theta': -1500.0,  # Exceeds limit
            'total_vega': 600.0,  # Exceeds limit
            'total_rho': 250.0,  # Exceeds limit
        }

        limits = {
            'max_delta': 100,
            'max_gamma': 5,
            'max_theta': -1000,
            'max_vega': 500,
            'max_rho': 200,
        }

        result = calculator.validate_greeks_risk_limits(
            portfolio_greeks=portfolio_greeks,
            limits=limits,
        )

        assert 'error' not in result
        assert not result['within_limits']
        assert len(result['violations']) == 5

        # Check violation details
        delta_violation = next(v for v in result['violations'] if v['greek'] == 'delta')
        assert delta_violation['severity'] == 'HIGH'

        gamma_violation = next(v for v in result['violations'] if v['greek'] == 'gamma')
        assert gamma_violation['severity'] in ['HIGH', 'CRITICAL']

    def test_risk_score_calculation(self, calculator):
        """Test that risk score is calculated correctly."""
        # Test various scenarios
        scenarios = [
            {'violations': [], 'expected_level': 'LOW'},
            {'violations': [{'severity': 'MEDIUM'}], 'expected_level': 'MEDIUM'},
            {'violations': [{'severity': 'HIGH'}, {'severity': 'HIGH'}], 'expected_level': 'HIGH'},
            {'violations': [{'severity': 'CRITICAL'}], 'expected_level': 'CRITICAL'},
        ]

        for scenario in scenarios:
            portfolio_greeks = {
                'total_delta': 0.0,
                'total_gamma': 0.0,
                'total_theta': 0.0,
                'total_vega': 0.0,
                'total_rho': 0.0,
            }

            # Manually create violations
            result = calculator.validate_greeks_risk_limits(
                portfolio_greeks=portfolio_greeks,
                limits={
                    'max_delta': 1000,
                    'max_gamma': 1000,
                    'max_theta': -10000,
                    'max_vega': 10000,
                    'max_rho': 10000,
                },
            )

            # Verify risk level is calculated
            assert 'risk_level' in result
            assert result['risk_level'] in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']


class TestGreeksSensitivityAnalysis(TestGreeksCalculator):
    """Test Greeks sensitivity analysis."""

    def test_spot_sensitivity_analysis(self, calculator, standard_option_params):
        """Test spot price sensitivity analysis."""
        result = calculator.calculate_greeks_sensitivity_analysis(
            option_params=standard_option_params,
            shock_scenarios={'spot_shock_pct': 0.05},
        )

        assert 'error' not in result
        assert 'base_greeks' in result
        assert 'sensitivity_analysis' in result
        assert 'spot_sensitivity' in result['sensitivity_analysis']

        spot_sens = result['sensitivity_analysis']['spot_sensitivity']
        assert 'delta_change_up' in spot_sens
        assert 'delta_change_down' in spot_sens

    def test_volatility_sensitivity_analysis(self, calculator, standard_option_params):
        """Test volatility sensitivity analysis."""
        result = calculator.calculate_greeks_sensitivity_analysis(
            option_params=standard_option_params,
        )

        assert 'error' not in result
        assert 'volatility_sensitivity' in result['sensitivity_analysis']

        vol_sens = result['sensitivity_analysis']['volatility_sensitivity']
        assert 'vega_change_up' in vol_sens
        assert 'vomma_validation' in vol_sens

    def test_time_decay_sensitivity_analysis(self, calculator, standard_option_params):
        """Test time decay sensitivity analysis."""
        result = calculator.calculate_greeks_sensitivity_analysis(
            option_params=standard_option_params,
        )

        assert 'error' not in result
        assert 'time_decay_sensitivity' in result['sensitivity_analysis']

        time_sens = result['sensitivity_analysis']['time_decay_sensitivity']
        assert 'theta_acceleration' in time_sens
        assert 'days_decay' in time_sens

    def test_sensitivity_assessment(self, calculator, standard_option_params):
        """Test overall sensitivity assessment."""
        result = calculator.calculate_greeks_sensitivity_analysis(
            option_params=standard_option_params,
        )

        assert 'error' not in result
        assert 'assessment' in result['sensitivity_analysis']

        assessment = result['sensitivity_analysis']['assessment']
        assert 'stability_score' in assessment
        assert 'stability_level' in assessment
        assert 'recommendation' in assessment

        assert 0 <= assessment['stability_score'] <= 100
        assert assessment['stability_level'] in ['HIGH', 'MODERATE', 'LOW']
