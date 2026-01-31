"""
Property-Based Tests for Position Sizing Calculations

This module uses Hypothesis to test mathematical properties and invariants
of position sizing calculations, ensuring correctness across wide ranges of inputs.

Properties tested:
- Kelly Criterion mathematical properties
- Position sizing bounds and constraints
- ATR-based stop loss calculations
- Risk management invariants
"""

from decimal import Decimal
from typing import Dict, Union

import numpy as np
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from hypothesis.extra import numpy as np_strategies

from app.services.position_sizing_engine import (
    PositionSizingEngine,
    MetaLabelingPositionSizer,
)


# ============================================================================
# Test Strategies
# ============================================================================


def valid_capital() -> st.SearchStrategy[Decimal]:
    """Generate valid capital values."""
    return st.floats(min_value=1_000, max_value=10_000_000).map(lambda x: Decimal(str(x)))


def valid_win_rate() -> st.SearchStrategy[float]:
    """Generate valid win rates (0 to 1)."""
    return st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def valid_avg_win() -> st.SearchStrategy[float]:
    """Generate valid average win values (positive)."""
    return st.floats(min_value=1.0, max_value=100_000, allow_nan=False, allow_infinity=False)


def valid_avg_loss() -> st.SearchStrategy[float]:
    """Generate valid average loss values (positive, represents magnitude)."""
    return st.floats(min_value=1.0, max_value=100_000, allow_nan=False, allow_infinity=False)


def valid_atr() -> st.SearchStrategy[float]:
    """Generate valid ATR values."""
    return st.floats(min_value=0.01, max_value=1000, allow_nan=False, allow_infinity=False)


def valid_entry_price() -> st.SearchStrategy[Decimal]:
    """Generate valid entry prices."""
    return st.floats(min_value=1.0, max_value=10_000, allow_nan=False, allow_infinity=False).map(
        lambda x: Decimal(str(x))
    )


# ============================================================================
# Kelly Criterion Property Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestKellyCriterionProperties:
    """Property tests for Kelly Criterion calculations."""

    @given(win_rate=valid_win_rate(), avg_win=valid_avg_win(), avg_loss=valid_avg_loss())
    @settings(max_examples=100)
    def test_kelly_fraction_bounded(self, win_rate, avg_win, avg_loss):
        """Kelly fraction should always be bounded between reasonable limits."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        # Half-Kelly should be bounded between 0 and 0.25
        half_kelly = float(result['half_kelly_fraction'])
        assert 0.0 <= half_kelly <= 0.25, f"Half-Kelly {half_kelly} outside bounds [0, 0.25]"

    @given(win_rate=valid_win_rate(), avg_win=valid_avg_win(), avg_loss=valid_avg_loss())
    @settings(max_examples=100)
    def test_kelly_half_equals_raw_divided_by_two(self, win_rate, avg_win, avg_loss):
        """Half-Kelly should equal raw Kelly divided by 2 (before capping)."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        raw_kelly = float(result['kelly_fraction'])
        half_kelly = float(result['half_kelly_fraction'])

        # Half-Kelly should be approximately half of raw Kelly (before capping)
        # Account for capping at 0.25
        if raw_kelly <= 0:
            assert half_kelly == 0.0, "Negative Kelly should result in zero position"
        elif raw_kelly * 0.5 <= 0.25:
            assert (
                abs(half_kelly - (raw_kelly * 0.5)) < 0.01
            ), f"Half-Kelly {half_kelly} != {raw_kelly * 0.5}"

    @given(
        win_rate=valid_win_rate(),
        avg_win=valid_avg_win(),
        avg_loss=valid_avg_loss(),
        capital=valid_capital(),
    )
    @settings(max_examples=100)
    def test_position_value_never_exceeds_capital(self, win_rate, avg_win, avg_loss, capital):
        """Position value should never exceed capital."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            capital=capital,
        )

        position_value = result.get('position_value', Decimal('0'))
        assert position_value >= Decimal('0'), "Position value should be non-negative"
        assert position_value <= capital, f"Position value {position_value} > capital {capital}"

    @given(
        win_rate=valid_win_rate(),
        avg_win=valid_avg_win(),
        avg_loss=valid_avg_loss(),
        capital=valid_capital(),
    )
    @settings(max_examples=100)
    def test_position_value_capped_at_25_percent(self, win_rate, avg_win, avg_loss, capital):
        """Position value should be capped at 25% of capital."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            capital=capital,
        )

        position_value = result.get('position_value', Decimal('0'))
        max_position = capital * Decimal('0.25')
        assert (
            position_value <= max_position
        ), f"Position value {position_value} exceeds 25% cap {max_position}"

    @given(
        win_rate=st.floats(min_value=0.51, max_value=0.90),
        avg_win=valid_avg_win(),
        avg_loss=valid_avg_loss(),
    )
    @settings(max_examples=50)
    def test_positive_expectancy_gives_positive_kelly(self, win_rate, avg_win, avg_loss):
        """Positive expectancy should result in positive Kelly fraction."""
        # Only test when expectancy is positive
        expected_value = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        assume(expected_value > 0)

        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        raw_kelly = float(result['kelly_fraction'])
        assert raw_kelly > 0, f"Positive expectancy should give positive Kelly, got {raw_kelly}"

    @given(win_rate=valid_win_rate(), avg_win=valid_avg_win(), avg_loss=valid_avg_loss())
    @settings(max_examples=50)
    def test_negative_expectancy_gives_negative_or_zero_kelly(self, win_rate, avg_win, avg_loss):
        """Negative expectancy should result in negative or zero Kelly fraction."""
        # Calculate expected value to ensure it's negative
        expected_value = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        assume(expected_value < 0)

        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        raw_kelly = float(result['kelly_fraction'])
        assert (
            raw_kelly <= 0
        ), f"Negative expectancy should give non-positive Kelly, got {raw_kelly}"

    @given(
        win_rate=valid_win_rate(),
        avg_win=valid_avg_win(),
        avg_loss=valid_avg_loss(),
        capital=valid_capital(),
    )
    @settings(max_examples=100)
    def test_position_percentage_equals_fraction_times_100(
        self, win_rate, avg_win, avg_loss, capital
    ):
        """Position percentage should equal fraction times 100."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            capital=capital,
        )

        position_pct = float(result['position_percentage'])
        half_kelly = float(result['half_kelly_fraction'])

        assert (
            abs(position_pct - (half_kelly * 100)) < 0.01
        ), f"Position percentage {position_pct} != {half_kelly * 100}"

    @given(
        win_rate=st.floats(min_value=0.45, max_value=0.55),
        avg_win=st.floats(min_value=10.0, max_value=100.0),
        avg_loss=st.floats(min_value=10.0, max_value=100.0),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_kelly_symmetry_with_win_loss_swap(self, win_rate, avg_win, avg_loss):
        """Test symmetry when swapping win and loss rates."""
        engine = PositionSizingEngine(atr_multiplier=2.0)

        # Only test when win and loss are close
        assume(abs(avg_win - avg_loss) < 5.0)

        result1 = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        result2 = engine.calculate_kelly_position_size(
            win_rate=1 - win_rate,
            avg_win=avg_loss,
            avg_loss=avg_win,
        )

        # Kelly should be approximately symmetric (with opposite signs)
        kelly1 = float(result1['kelly_fraction'])
        kelly2 = float(result2['kelly_fraction'])

        # The 25% cap can break symmetry when one value is capped
        # Skip the assertion if either value is at or near the cap
        if abs(kelly1) >= 0.24 or abs(kelly2) >= 0.24:
            return

        # When win/loss are similar and symmetric around 0.5, results should be opposite
        assert abs(kelly1 + kelly2) < 0.15, f"Symmetry violation: {kelly1} vs {kelly2}"

    @given(win_rate=valid_win_rate(), avg_win=valid_avg_win(), avg_loss=valid_avg_loss())
    @settings(max_examples=100)
    def test_recommendation_matches_kelly_sign(self, win_rate, avg_win, avg_loss):
        """Recommendation should match Kelly fraction sign."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        raw_kelly = float(result['kelly_fraction'])
        recommendation = result['recommendation']

        if raw_kelly <= 0:
            assert recommendation in [
                'AVOID',
                'REDUCE',
            ], f"Negative Kelly {raw_kelly} should give AVOID/REDUCE, got {recommendation}"
        elif raw_kelly < 0.02:
            assert recommendation in [
                'REDUCE',
                'BUY',
            ], f"Small Kelly {raw_kelly} should give REDUCE/BUY, got {recommendation}"
        else:
            assert (
                recommendation == 'BUY'
            ), f"Positive Kelly {raw_kelly} should give BUY, got {recommendation}"


# ============================================================================
# ATR-Based Position Sizing Property Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestATRPositionSizingProperties:
    """Property tests for ATR-based position sizing."""

    @given(capital=valid_capital(), entry_price=valid_entry_price(), atr=valid_atr())
    @settings(max_examples=100)
    def test_position_size_non_negative(self, capital, entry_price, atr):
        """Position size should never be negative."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        position_size = engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        assert position_size is not None, "Position size should not be None"
        assert position_size >= 0, f"Position size {position_size} should be non-negative"

    @given(capital=valid_capital(), entry_price=valid_entry_price(), atr=valid_atr())
    @settings(max_examples=100)
    def test_position_value_never_exceeds_capital(self, capital, entry_price, atr):
        """Position value should never exceed available capital."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        position_size = engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        assume(position_size is not None)

        position_value = position_size * entry_price
        # Allow small tolerance for floating point arithmetic
        tolerance = capital * Decimal('0.0001')  # 0.01% tolerance
        assert (
            position_value <= capital + tolerance
        ), f"Position value {position_value} > capital {capital}"

    @given(
        capital=valid_capital(),
        entry_price=valid_entry_price(),
        atr=st.floats(min_value=0.01, max_value=100),
    )
    @settings(max_examples=100)
    def test_higher_atr_gives_smaller_position(self, capital, entry_price, atr):
        """Higher ATR (more volatility) should give smaller position size."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        atr_high = atr * 2

        size_low = engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        size_high = engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr_high,
        )

        assume(size_low is not None and size_high is not None)

        # Higher ATR should result in smaller or equal position size
        assert (
            size_high <= size_low
        ), f"Higher ATR {atr_high} should give smaller position {size_high} <= {size_low}"

    @given(capital=valid_capital(), entry_price=valid_entry_price(), atr=valid_atr())
    @settings(max_examples=100)
    def test_atr_multiplier_2_gives_reasonable_stop(self, capital, entry_price, atr):
        """ATR multiplier of 2 should give reasonable stop loss distance."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        stop_loss = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction='buy',
            atr=atr,
        )

        assume(stop_loss is not None)

        stop_distance = abs(entry_price - stop_loss)

        # Stop distance should be 2x ATR
        expected_distance = Decimal(str(atr)) * engine.atr_multiplier

        assert abs(stop_distance - expected_distance) < Decimal(
            '0.01'
        ), f"Stop distance {stop_distance} != 2*ATR {expected_distance}"

    @given(capital=valid_capital(), entry_price=valid_entry_price(), atr=valid_atr())
    @settings(max_examples=100)
    def test_buy_stop_below_entry(self, capital, entry_price, atr):
        """Buy stop loss should be below entry price."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        stop_loss = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction='buy',
            atr=atr,
        )

        assume(stop_loss is not None)

        assert stop_loss < entry_price, f"Buy stop {stop_loss} should be below entry {entry_price}"

    @given(capital=valid_capital(), entry_price=valid_entry_price(), atr=valid_atr())
    @settings(max_examples=100)
    def test_sell_stop_above_entry(self, capital, entry_price, atr):
        """Sell stop loss should be above entry price."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        stop_loss = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction='sell',
            atr=atr,
        )

        assume(stop_loss is not None)

        assert stop_loss > entry_price, f"Sell stop {stop_loss} should be above entry {entry_price}"


# ============================================================================
# Stop Loss Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestStopLossProperties:
    """Property tests for stop loss calculations."""

    @given(
        entry_price=valid_entry_price(),
        atr=valid_atr(),
        stop_pct=st.floats(min_value=0.01, max_value=0.20),
    )
    @settings(max_examples=100)
    def test_atr_priority_over_percentage(self, entry_price, atr, stop_pct):
        """ATR-based stop should take priority over percentage-based stop."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        stop_with_atr = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction='buy',
            atr=atr,
            stop_loss_pct=stop_pct,
        )

        stop_without_atr = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction='buy',
            atr=None,
            stop_loss_pct=stop_pct,
        )

        assume(stop_with_atr is not None and stop_without_atr is not None)

        # ATR-based stop should differ from percentage-based stop
        assert stop_with_atr != stop_without_atr, "ATR stop should differ from percentage stop"

    @given(entry_price=valid_entry_price(), stop_pct=st.floats(min_value=0.01, max_value=0.50))
    @settings(max_examples=100)
    def test_percentage_stop_distance_proportional(self, entry_price, stop_pct):
        """Percentage-based stop distance should be proportional to entry price."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        stop_buy = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction='buy',
            atr=None,
            stop_loss_pct=stop_pct,
        )

        stop_sell = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction='sell',
            atr=None,
            stop_loss_pct=stop_pct,
        )

        assume(stop_buy is not None and stop_sell is not None)

        # Check buy stop
        buy_distance = abs(entry_price - stop_buy)
        expected_buy_distance = entry_price * Decimal(str(stop_pct))
        assert abs(buy_distance - expected_buy_distance) < Decimal(
            '0.01'
        ), f"Buy stop distance {buy_distance} != {expected_buy_distance}"

        # Check sell stop
        sell_distance = abs(stop_sell - entry_price)
        expected_sell_distance = entry_price * Decimal(str(stop_pct))
        assert abs(sell_distance - expected_sell_distance) < Decimal(
            '0.01'
        ), f"Sell stop distance {sell_distance} != {expected_sell_distance}"


# ============================================================================
# Meta-Labeling Position Sizing Properties
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestMetaLabelingPositionSizingProperties:
    """Property tests for meta-labeling position sizing."""

    @given(data=st.data())
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
    def test_position_sizes_bounded(self, data):
        """Position sizes should be bounded between -1 and 1."""
        # Generate arrays of the same size
        size = data.draw(st.integers(min_value=1, max_value=50))
        signals = data.draw(
            np_strategies.arrays(
                dtype=np.int8, shape=st.just(size), elements=st.sampled_from([-1, 0, 1])
            )
        )
        meta_proba = data.draw(
            np_strategies.arrays(
                dtype=np.float64,
                shape=st.just(size),
                elements=st.floats(
                    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
                ),
            )
        )

        sizer = MetaLabelingPositionSizer()

        try:
            position_sizes = sizer.calculate_position_size(
                signals=signals,
                meta_proba=meta_proba,
            )

            assert all(
                -1 <= size <= 1 for size in position_sizes
            ), f"Position sizes should be in [-1, 1], got {position_sizes}"
        except ImportError:
            pytest.skip("ML modules not available")

    @given(data=st.data())
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
    def test_zero_signal_gives_zero_position(self, data):
        """Signal of 0 should result in position size of 0."""
        # Generate arrays of the same size with at least one zero signal
        size = data.draw(st.integers(min_value=1, max_value=50))
        signals = data.draw(
            np_strategies.arrays(
                dtype=np.int8, shape=st.just(size), elements=st.sampled_from([-1, 0, 1])
            )
        )
        meta_proba = data.draw(
            np_strategies.arrays(
                dtype=np.float64,
                shape=st.just(size),
                elements=st.floats(
                    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
                ),
            )
        )

        # Ensure we have at least one zero signal
        assume(np.any(signals == 0))

        sizer = MetaLabelingPositionSizer()

        try:
            position_sizes = sizer.calculate_position_size(
                signals=signals,
                meta_proba=meta_proba,
            )

            # Find indices where signal is 0
            zero_indices = np.where(signals == 0)[0]
            for idx in zero_indices:
                assert (
                    position_sizes[idx] == 0
                ), f"Signal 0 should give position 0, got {position_sizes[idx]}"
        except ImportError:
            pytest.skip("ML modules not available")

    @given(data=st.data())
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
    def test_position_sign_matches_signal_sign(self, data):
        """Position size sign should match signal sign."""
        # Generate arrays of the same size
        size = data.draw(st.integers(min_value=1, max_value=50))
        signals = data.draw(
            np_strategies.arrays(
                dtype=np.int8, shape=st.just(size), elements=st.sampled_from([-1, 0, 1])
            )
        )
        meta_proba = data.draw(
            np_strategies.arrays(
                dtype=np.float64,
                shape=st.just(size),
                elements=st.floats(
                    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
                ),
            )
        )

        sizer = MetaLabelingPositionSizer()

        try:
            position_sizes = sizer.calculate_position_size(
                signals=signals,
                meta_proba=meta_proba,
            )

            for i, (signal, size) in enumerate(zip(signals, position_sizes)):
                if signal != 0 and size != 0:
                    assert np.sign(size) == np.sign(
                        signal
                    ), f"Position sign {np.sign(size)} != signal sign {np.sign(signal)} at index {i}"
        except ImportError:
            pytest.skip("ML modules not available")


# ============================================================================
# Edge Cases and Validation
# ============================================================================


@pytest.mark.unit
@pytest.mark.property
class TestPositionSizingEdgeCases:
    """Test edge cases and validation."""

    @given(
        invalid_capital=st.one_of(
            st.floats(max_value=0), st.floats(min_value=-1_000_000, max_value=-1)
        )
    )
    @settings(max_examples=50)
    def test_negative_or_zero_capital_raises_error(self, invalid_capital):
        """Negative or zero capital should raise ValueError."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        with pytest.raises(ValueError):
            engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=100.0,
                avg_loss=75.0,
                capital=Decimal(str(invalid_capital)),
            )

    @given(
        invalid_win_rate=st.sampled_from(
            [
                -0.5,
                -0.1,
                -1.0,  # Negative values
                1.1,
                1.5,
                2.0,  # Values > 1.0
                float('nan'),  # NaN
                float('inf'),
                float('-inf'),  # Infinity
            ]
        )
    )
    @settings(max_examples=50)
    def test_invalid_win_rate_raises_error(self, invalid_win_rate):
        """Invalid win rate should raise ValueError."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        with pytest.raises((ValueError, TypeError)):
            engine.calculate_kelly_position_size(
                win_rate=invalid_win_rate,
                avg_win=100.0,
                avg_loss=75.0,
            )

    @given(
        invalid_avg_win=st.sampled_from(
            [
                -100.0,
                -10.0,
                -1.0,
                0.0,  # Negative or zero values
                float('nan'),  # NaN
                float('inf'),
                float('-inf'),  # Infinity
            ]
        )
    )
    @settings(max_examples=50)
    def test_invalid_avg_win_raises_error(self, invalid_avg_win):
        """Invalid average win should raise ValueError."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        with pytest.raises((ValueError, TypeError)):
            engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=invalid_avg_win,
                avg_loss=75.0,
            )
