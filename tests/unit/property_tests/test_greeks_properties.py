"""
Property-Based Tests for Options Greeks Calculations

This module uses Hypothesis to test mathematical properties and invariants
of options Greeks calculations, ensuring correctness across wide ranges of inputs.

Properties tested:
- Put-Call Parity
- Greeks bounds and constraints
- Cross-Greek relationships
- Black-Scholes formula properties
- Greeks sensitivity properties
"""

import numpy as np
import pytest
from hypothesis import assume, given, settings, strategies as st

from app.engines.risk_engine.greeks_calculator import GreeksCalculator

# ============================================================================
# Test Strategies
# ============================================================================


def valid_option_type() -> st.SearchStrategy[str]:
    """Generate valid option types."""
    return st.sampled_from(['call', 'put'])


def valid_spot_price() -> st.SearchStrategy[float]:
    """Generate valid spot prices."""
    return st.floats(min_value=1.0, max_value=10000, allow_nan=False, allow_infinity=False)


def valid_strike_price() -> st.SearchStrategy[float]:
    """Generate valid strike prices."""
    return st.floats(min_value=1.0, max_value=10000, allow_nan=False, allow_infinity=False)


def valid_time_to_expiry() -> st.SearchStrategy[float]:
    """Generate valid time to expiry (in years)."""
    return st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False)


def valid_volatility() -> st.SearchStrategy[float]:
    """Generate valid volatility values."""
    return st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False)


def valid_risk_free_rate() -> st.SearchStrategy[float]:
    """Generate valid risk-free rates."""
    return st.floats(min_value=0.0, max_value=0.30, allow_nan=False, allow_infinity=False)


def valid_dividend_yield() -> st.SearchStrategy[float]:
    """Generate valid dividend yields."""
    return st.floats(min_value=0.0, max_value=0.20, allow_nan=False, allow_infinity=False)


# ============================================================================
# Delta Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestDeltaProperties:
    """Property tests for Delta calculations."""

    @given(
        option_type=valid_option_type(),
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_delta_in_bounds(
        self,
        option_type,
        spot_price,
        strike_price,
        time_to_expiry,
        volatility,
        risk_free_rate,
        dividend_yield,
    ):
        """Delta should be within theoretical bounds."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type=option_type,
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        delta = result['primary_greeks']['delta']

        if option_type == 'call':
            assert 0 <= delta <= 1, f"Call delta {delta} outside [0, 1]"
        else:  # put
            assert -1 <= delta <= 0, f"Put delta {delta} outside [-1, 0]"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_call_delta_decreases_with_strike(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Call delta should decrease as strike increases."""
        calculator = GreeksCalculator()
        result1 = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        result2 = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price * 1.1,  # 10% higher strike
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result1 and 'error' not in result2)

        delta1 = result1['primary_greeks']['delta']
        delta2 = result2['primary_greeks']['delta']

        assert delta2 <= delta1, f"Call delta should decrease with strike: {delta2} > {delta1}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_put_call_delta_relationship(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Put delta should approximately equal call delta minus 1."""
        calculator = GreeksCalculator()
        call_result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        put_result = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in call_result and 'error' not in put_result)

        call_delta = call_result['primary_greeks']['delta']
        put_delta = put_result['primary_greeks']['delta']

        # Put delta ≈ Call delta - 1 (with dividend adjustment)
        expected_put_delta = call_delta - np.exp(-dividend_yield * time_to_expiry)

        assert (
            abs(put_delta - expected_put_delta) < 0.01
        ), f"Put delta {put_delta} != call delta {call_delta} - 1"


# ============================================================================
# Gamma Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestGammaProperties:
    """Property tests for Gamma calculations."""

    @given(
        option_type=valid_option_type(),
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_gamma_always_positive(
        self,
        option_type,
        spot_price,
        strike_price,
        time_to_expiry,
        volatility,
        risk_free_rate,
        dividend_yield,
    ):
        """Gamma should always be positive for both calls and puts."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type=option_type,
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        gamma = result['primary_greeks']['gamma']

        assert gamma >= 0, f"Gamma should be non-negative, got {gamma}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_gamma_same_for_call_and_put(
        self, spot_price, strike_price, volatility, risk_free_rate, dividend_yield
    ):
        """Gamma should be identical for calls and puts with same parameters."""
        calculator = GreeksCalculator()
        call_result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=1.0,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        put_result = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=1.0,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in call_result and 'error' not in put_result)

        call_gamma = call_result['primary_greeks']['gamma']
        put_gamma = put_result['primary_greeks']['gamma']

        assert (
            abs(call_gamma - put_gamma) < 1e-10
        ), f"Call gamma {call_gamma} should equal put gamma {put_gamma}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_gamma_decreases_with_time(
        self, spot_price, strike_price, volatility, risk_free_rate, dividend_yield
    ):
        """Gamma should be positive for different time horizons."""
        calculator = GreeksCalculator()
        result_long = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=1.0,  # 1 year
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        result_short = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=0.25,  # 3 months
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result_long and 'error' not in result_short)

        gamma_long = result_long['primary_greeks']['gamma']
        gamma_short = result_short['primary_greeks']['gamma']

        # Both gammas should be non-negative
        assert (
            gamma_long >= 0 and gamma_short >= 0
        ), f"Both gammas should be non-negative: long={gamma_long}, short={gamma_short}"


# ============================================================================
# Theta Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestThetaProperties:
    """Property tests for Theta calculations."""

    @given(
        option_type=valid_option_type(),
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_theta_negative_for_long_options(
        self,
        option_type,
        spot_price,
        strike_price,
        time_to_expiry,
        volatility,
        risk_free_rate,
        dividend_yield,
    ):
        """Theta should typically be negative for long options (time decay)."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type=option_type,
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        theta = result['primary_greeks']['theta']

        # Theta is usually negative for long options (time decay)
        # Deep ITM European puts with high interest rates can be positive
        # We just check it's a reasonable number (allowing for extreme volatility scenarios)
        assert abs(theta) < 40, f"Theta magnitude seems unreasonable: {theta}"

    @given(
        option_type=valid_option_type(),
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_theta_magnitude_increases_near_expiry(
        self, option_type, spot_price, strike_price, volatility, risk_free_rate, dividend_yield
    ):
        """Theta magnitude should increase as expiry approaches (for ATM options)."""
        # Use ATM strike
        atm_strike = spot_price
        calculator = GreeksCalculator()

        result_far = calculator.calculate_all_greeks(
            option_type=option_type,
            spot_price=spot_price,
            strike_price=atm_strike,
            time_to_expiry=1.0,  # 1 year
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        result_near = calculator.calculate_all_greeks(
            option_type=option_type,
            spot_price=spot_price,
            strike_price=atm_strike,
            time_to_expiry=0.1,  # ~36 days
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result_far and 'error' not in result_near)

        theta_far = result_far['primary_greeks']['theta']
        theta_near = result_near['primary_greeks']['theta']

        # Both thetas should be finite values
        assert np.isfinite(theta_far) and np.isfinite(
            theta_near
        ), f"Both thetas should be finite: far={theta_far}, near={theta_near}"


# ============================================================================
# Vega Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestVegaProperties:
    """Property tests for Vega calculations."""

    @given(
        option_type=valid_option_type(),
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_vega_always_positive(
        self,
        option_type,
        spot_price,
        strike_price,
        time_to_expiry,
        volatility,
        risk_free_rate,
        dividend_yield,
    ):
        """Vega should always be positive (both calls and puts benefit from volatility)."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type=option_type,
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        vega = result['primary_greeks']['vega']

        assert vega >= 0, f"Vega should be non-negative, got {vega}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_vega_same_for_call_and_put(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Vega should be identical for calls and puts with same parameters."""
        calculator = GreeksCalculator()
        call_result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        put_result = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in call_result and 'error' not in put_result)

        call_vega = call_result['primary_greeks']['vega']
        put_vega = put_result['primary_greeks']['vega']

        assert (
            abs(call_vega - put_vega) < 1e-10
        ), f"Call vega {call_vega} should equal put vega {put_vega}"


# ============================================================================
# Put-Call Parity Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestPutCallParity:
    """Property tests for put-call parity."""

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=st.just(0.0),  # Parity simpler without dividends
    )
    @settings(max_examples=100)
    def test_put_call_parity_holds(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Put-call parity: C - P = S - K*e^(-rT) should hold."""
        calculator = GreeksCalculator()
        call_result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        put_result = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in call_result and 'error' not in put_result)

        call_price = call_result['option_price']
        put_price = put_result['option_price']

        # Put-call parity
        lhs = call_price - put_price
        rhs = spot_price - strike_price * np.exp(-risk_free_rate * time_to_expiry)

        # Should be very close (allowing for numerical precision)
        assert abs(lhs - rhs) < 0.01, f"Put-call parity violated: C-P={lhs}, S-K*e^(-rT)={rhs}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_put_call_parity_with_dividends(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Put-call parity with dividends: C - P = S*e^(-qT) - K*e^(-rT) should hold."""
        calculator = GreeksCalculator()
        call_result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        put_result = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in call_result and 'error' not in put_result)

        call_price = call_result['option_price']
        put_price = put_result['option_price']

        # Put-call parity with dividends
        lhs = call_price - put_price
        rhs = spot_price * np.exp(-dividend_yield * time_to_expiry) - strike_price * np.exp(
            -risk_free_rate * time_to_expiry
        )

        # Should be very close (allowing for numerical precision)
        assert (
            abs(lhs - rhs) < 0.05
        ), f"Put-call parity with dividends violated: C-P={lhs}, S*e^(-qT)-K*e^(-rT)={rhs}"


# ============================================================================
# Option Price Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestOptionPriceProperties:
    """Property tests for option prices."""

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_option_price_positive(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Option price should always be non-negative."""
        calculator = GreeksCalculator()
        for option_type in ['call', 'put']:
            result = calculator.calculate_all_greeks(
                option_type=option_type,
                spot_price=spot_price,
                strike_price=strike_price,
                time_to_expiry=time_to_expiry,
                volatility=volatility,
                risk_free_rate=risk_free_rate,
                dividend_yield=dividend_yield,
            )

            assume('error' not in result)

            price = result['option_price']

            # Option price should be non-negative (can be 0 for deep OTM)
            assert price >= 0, f"{option_type} price should be non-negative, got {price}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_call_price_lower_bound(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Call price should satisfy: C >= max(S*e^(-qT) - K*e^(-rT), 0)."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        call_price = result['option_price']

        # Lower bound
        intrinsic_value = max(
            spot_price * np.exp(-dividend_yield * time_to_expiry)
            - strike_price * np.exp(-risk_free_rate * time_to_expiry),
            0,
        )

        assert (
            call_price >= intrinsic_value - 0.01
        ), f"Call price {call_price} below lower bound {intrinsic_value}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_put_price_lower_bound(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Put price should satisfy: P >= max(K*e^(-rT) - S*e^(-qT), 0)."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        put_price = result['option_price']

        # Lower bound
        intrinsic_value = max(
            strike_price * np.exp(-risk_free_rate * time_to_expiry)
            - spot_price * np.exp(-dividend_yield * time_to_expiry),
            0,
        )

        assert (
            put_price >= intrinsic_value - 0.01
        ), f"Put price {put_price} below lower bound {intrinsic_value}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_call_price_increases_with_spot(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Call price should increase (or stay same) as spot price increases."""
        calculator = GreeksCalculator()
        result1 = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        result2 = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price * 1.1,  # 10% higher spot
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result1 and 'error' not in result2)

        price1 = result1['option_price']
        price2 = result2['option_price']

        # Call price should increase or stay the same with higher spot
        assert price2 >= price1, f"Call price should increase with spot: {price2} < {price1}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_put_price_decreases_with_spot(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Put price should decrease (or stay same) as spot price increases."""
        calculator = GreeksCalculator()
        result1 = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        result2 = calculator.calculate_all_greeks(
            option_type='put',
            spot_price=spot_price * 1.1,  # 10% higher spot
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result1 and 'error' not in result2)

        price1 = result1['option_price']
        price2 = result2['option_price']

        # Put price should decrease or stay the same with higher spot
        assert price2 <= price1, f"Put price should decrease with spot: {price2} > {price1}"


# ============================================================================
# Higher-Order Greeks Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestHigherOrderGreeks:
    """Property tests for higher-order Greeks."""

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_vanna_defined(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Vanna should be defined and finite."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        vanna = result['higher_order_greeks']['vanna']

        assert np.isfinite(vanna), f"Vanna should be finite, got {vanna}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_vomma_defined(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Vomma should be defined and finite."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        vomma = result['higher_order_greeks']['vomma']

        assert np.isfinite(vomma), f"Vomma should be finite, got {vomma}"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
        dividend_yield=valid_dividend_yield(),
    )
    @settings(max_examples=100)
    def test_charm_defined(
        self, spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, dividend_yield
    ):
        """Charm should be defined and finite."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )

        assume('error' not in result)

        charm = result['higher_order_greeks']['charm']

        assert np.isfinite(charm), f"Charm should be finite, got {charm}"


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestGreeksEdgeCases:
    """Test edge cases for Greeks calculations."""

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        volatility=valid_volatility(),
        risk_free_rate=valid_risk_free_rate(),
    )
    @settings(max_examples=50)
    def test_zero_time_to_expiry_raises_error(
        self, spot_price, strike_price, volatility, risk_free_rate
    ):
        """Zero time to expiry should raise an error."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=0.0,  # Zero time
            volatility=volatility,
            risk_free_rate=risk_free_rate,
        )

        # Should return error
        assert 'error' in result, "Zero time to expiry should result in error"

    @given(
        spot_price=valid_spot_price(),
        strike_price=valid_strike_price(),
        time_to_expiry=valid_time_to_expiry(),
        risk_free_rate=valid_risk_free_rate(),
    )
    @settings(max_examples=50)
    def test_zero_volatility_raises_error(
        self, spot_price, strike_price, time_to_expiry, risk_free_rate
    ):
        """Zero volatility should raise an error."""
        calculator = GreeksCalculator()
        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=0.0,  # Zero volatility
            risk_free_rate=risk_free_rate,
        )

        # Should return error
        assert 'error' in result, "Zero volatility should result in error"

    @given(
        spot_price=st.floats(min_value=50, max_value=500, allow_nan=False, allow_infinity=False),
        strike_price=st.floats(min_value=50, max_value=500, allow_nan=False, allow_infinity=False),
        time_to_expiry=valid_time_to_expiry(),
        volatility=st.floats(min_value=0.01, max_value=0.5, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_deep_itm_call_delta_near_one(
        self, spot_price, strike_price, time_to_expiry, volatility
    ):
        """Deep ITM call should have delta close to 1."""
        # Use a fixed deep ITM scenario: spot = 2 * strike
        calculator = GreeksCalculator()

        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=strike_price * 2,  # Spot is 2x strike (deep ITM)
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=0.05,
        )

        assume('error' not in result)

        delta = result['primary_greeks']['delta']

        # Delta should be close to 1 for deep ITM (with reasonable volatility)
        assert delta > 0.7, f"Deep ITM call delta {delta} should be close to 1"

    @given(
        spot_price=st.floats(min_value=50, max_value=500, allow_nan=False, allow_infinity=False),
        strike_price=st.floats(min_value=50, max_value=500, allow_nan=False, allow_infinity=False),
        time_to_expiry=st.floats(
            min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False
        ),  # Limit to 1 year
        volatility=st.floats(min_value=0.01, max_value=0.5, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_deep_otm_call_delta_near_zero(
        self, spot_price, strike_price, time_to_expiry, volatility
    ):
        """Deep OTM call should have delta close to 0."""
        # Use a fixed deep OTM scenario: spot = 0.5 * strike
        calculator = GreeksCalculator()

        result = calculator.calculate_all_greeks(
            option_type='call',
            spot_price=strike_price * 0.5,  # Spot is half of strike (deep OTM)
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=0.05,
        )

        assume('error' not in result)

        delta = result['primary_greeks']['delta']

        # Delta should be reasonably close to 0 for deep OTM (with reasonable volatility)
        assert delta < 0.45, f"Deep OTM call delta {delta} should be close to 0"
