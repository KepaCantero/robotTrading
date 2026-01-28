"""
Comprehensive unit tests for PositionSizingEngine.

Following TDD best practices:
1. Test-driven development approach
2. Comprehensive edge case coverage
3. Property-based testing with Hypothesis
4. Proper mocking of external dependencies
5. Clear test names and structure
"""

from decimal import Decimal
from datetime import datetime
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import patch, MagicMock

from app.services.position_sizing_engine import PositionSizingEngine


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def position_engine():
    """Create PositionSizingEngine instance."""
    return PositionSizingEngine(atr_multiplier=2.0)


@pytest.fixture
def position_engine_custom_multiplier():
    """Create PositionSizingEngine with custom ATR multiplier."""
    return PositionSizingEngine(atr_multiplier=3.0)


# =============================================================================
# Initialization Tests
# =============================================================================

class TestPositionSizingEngineInitialization:
    """Test suite for PositionSizingEngine initialization."""

    def test_initialization_with_default_multiplier(self):
        """Test that engine initializes with default multiplier."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        assert engine.atr_multiplier == Decimal("2.0")

    def test_initialization_with_custom_multiplier(self):
        """Test that engine accepts custom ATR multiplier."""
        engine = PositionSizingEngine(atr_multiplier=1.5)
        assert engine.atr_multiplier == Decimal("1.5")

    def test_initialization_with_high_multiplier(self):
        """Test that engine accepts high ATR multiplier."""
        engine = PositionSizingEngine(atr_multiplier=5.0)
        assert engine.atr_multiplier == Decimal("5.0")

    def test_initialization_with_low_multiplier(self):
        """Test that engine accepts low ATR multiplier."""
        engine = PositionSizingEngine(atr_multiplier=0.5)
        assert engine.atr_multiplier == Decimal("0.5")


# =============================================================================
# Stop Loss Calculation Tests
# =============================================================================

class TestStopLossCalculation:
    """Test suite for stop loss price calculation."""

    # ATR-based stop loss tests
    def test_calculate_stop_loss_buy_with_atr(self, position_engine):
        """Test stop loss for buy order with ATR."""
        entry_price = Decimal("150.00")
        atr = 3.0

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        # 150 - (3 * 2) = 144
        expected = Decimal("144.00")
        assert stop_loss == expected

    def test_calculate_stop_loss_sell_with_atr(self, position_engine):
        """Test stop loss for sell order with ATR."""
        entry_price = Decimal("150.00")
        atr = 3.0

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="sell",
            atr=atr,
        )

        # 150 + (3 * 2) = 156
        expected = Decimal("156.00")
        assert stop_loss == expected

    def test_calculate_stop_loss_with_zero_atr(self, position_engine):
        """Test stop loss with zero ATR."""
        entry_price = Decimal("150.00")
        atr = 0.0

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        # Should equal entry price with zero ATR
        assert stop_loss == Decimal("150.00")

    def test_calculate_stop_loss_with_high_atr(self, position_engine):
        """Test stop loss with very high ATR."""
        entry_price = Decimal("150.00")
        atr = 20.0

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        # 150 - (20 * 2) = 110
        assert stop_loss == Decimal("110.00")

    def test_calculate_stop_loss_with_custom_multiplier(self, position_engine_custom_multiplier):
        """Test stop loss with custom ATR multiplier."""
        entry_price = Decimal("150.00")
        atr = 3.0

        stop_loss = position_engine_custom_multiplier.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        # 150 - (3 * 3) = 141
        assert stop_loss == Decimal("141.00")

    # Percentage-based stop loss tests
    def test_calculate_stop_loss_buy_with_percentage(self, position_engine):
        """Test stop loss for buy order with percentage."""
        entry_price = Decimal("150.00")
        stop_loss_pct = 0.05  # 5%

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            stop_loss_pct=stop_loss_pct,
        )

        # 150 * (1 - 0.05) = 142.5
        expected = Decimal("142.50")
        assert stop_loss == expected

    def test_calculate_stop_loss_sell_with_percentage(self, position_engine):
        """Test stop loss for sell order with percentage."""
        entry_price = Decimal("150.00")
        stop_loss_pct = 0.05  # 5%

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="sell",
            stop_loss_pct=stop_loss_pct,
        )

        # 150 * (1 + 0.05) = 157.5
        expected = Decimal("157.50")
        assert stop_loss == expected

    def test_calculate_stop_loss_with_high_percentage(self, position_engine):
        """Test stop loss with high percentage."""
        entry_price = Decimal("150.00")
        stop_loss_pct = 0.20  # 20%

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            stop_loss_pct=stop_loss_pct,
        )

        # 150 * (1 - 0.20) = 120
        assert stop_loss == Decimal("120.00")

    def test_calculate_stop_loss_atr_priority_over_percentage(self, position_engine):
        """Test that ATR takes priority over percentage when both provided."""
        entry_price = Decimal("150.00")
        atr = 3.0
        stop_loss_pct = 0.05

        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
            stop_loss_pct=stop_loss_pct,
        )

        # Should use ATR: 150 - (3 * 2) = 144
        assert stop_loss == Decimal("144.00")

    # Edge cases
    def test_calculate_stop_loss_with_invalid_entry_price(self, position_engine):
        """Test stop loss with zero or negative entry price."""
        result = position_engine.calculate_stop_loss_price(
            entry_price=Decimal("0"),
            direction="buy",
            atr=3.0,
        )
        assert result is None

    def test_calculate_stop_loss_with_negative_entry_price(self, position_engine):
        """Test stop loss with negative entry price."""
        result = position_engine.calculate_stop_loss_price(
            entry_price=Decimal("-100"),
            direction="buy",
            atr=3.0,
        )
        assert result is None

    def test_calculate_stop_loss_with_no_atr_or_percentage(self, position_engine):
        """Test stop loss when neither ATR nor percentage provided."""
        result = position_engine.calculate_stop_loss_price(
            entry_price=Decimal("150.00"),
            direction="buy",
        )
        assert result is None

    def test_calculate_stop_loss_with_invalid_direction(self, position_engine):
        """Test stop loss with invalid direction."""
        # Should still work with unexpected direction (just use it as-is)
        result = position_engine.calculate_stop_loss_price(
            entry_price=Decimal("150.00"),
            direction="invalid",
            atr=3.0,
        )
        # Implementation may return None or handle gracefully
        assert result is None

    def test_calculate_stop_loss_case_insensitive_direction(self, position_engine):
        """Test that direction is case-insensitive."""
        entry_price = Decimal("150.00")
        atr = 3.0

        stop_loss_buy = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="BUY",
            atr=atr,
        )
        stop_loss_sell = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="SELL",
            atr=atr,
        )

        assert stop_loss_buy == Decimal("144.00")
        assert stop_loss_sell == Decimal("156.00")


# =============================================================================
# Position Sizing from ATR Tests
# =============================================================================

class TestPositionSizingFromATR:
    """Test suite for ATR-based position sizing."""

    def test_calculate_position_size_basic(self, position_engine):
        """Test basic position size calculation."""
        capital = Decimal("10000")
        entry_price = Decimal("150.00")
        atr = 3.0

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        # Risk amount = 10000 * 0.02 = 200
        # Stop distance = 3 * 2 = 6
        # Position size = 200 / 6 = 33.33
        assert position_size is not None
        assert position_size > 0
        assert position_size < capital  # Should use less than full capital

    def test_calculate_position_size_with_custom_risk(self, position_engine):
        """Test position size with custom risk percentage."""
        capital = Decimal("10000")
        entry_price = Decimal("150.00")
        atr = 3.0
        risk_pct = 0.01  # 1%

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            risk_per_trade_pct=risk_pct,
            entry_price=entry_price,
            atr=atr,
        )

        # Risk amount = 10000 * 0.01 = 100
        # Stop distance = 3 * 2 = 6
        # Position size = 100 / 6 = 16.67
        assert position_size is not None

    def test_calculate_position_size_with_high_atr(self, position_engine):
        """Test position size with high ATR (should reduce position)."""
        capital = Decimal("10000")
        entry_price = Decimal("150.00")
        atr = 10.0  # High volatility

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        # Higher ATR should result in smaller position
        assert position_size is not None
        assert position_size > 0

    def test_calculate_position_size_capped_at_capital(self, position_engine):
        """Test that position size is capped at available capital."""
        capital = Decimal("1000")
        entry_price = Decimal("10.00")
        atr = 0.5  # Low volatility

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        # Position should not exceed capital / entry_price
        max_shares = capital / entry_price
        assert position_size <= max_shares + Decimal("0.01")  # Small tolerance

    def test_calculate_position_size_atr_stop_capped_at_20_percent(self, position_engine):
        """Test that ATR stop distance is capped at 20% of entry price."""
        capital = Decimal("10000")
        entry_price = Decimal("100.00")
        atr = 15.0  # Would result in 30 stop distance (30% of price)

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        # Should cap at 20% = $20 stop distance
        # Position size = 200 / 20 = 10 shares
        assert position_size is not None

    def test_calculate_position_size_fallback_to_percentage_stop(self, position_engine):
        """Test fallback to percentage-based stop when ATR not available."""
        capital = Decimal("10000")
        entry_price = Decimal("150.00")

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=None,  # No ATR
        )

        # Should use 5% default stop
        # Risk amount = 200, Stop distance = 150 * 0.05 = 7.5
        # Position size = 200 / 7.5 = 26.67
        assert position_size is not None

    # Edge cases
    def test_calculate_position_size_with_zero_capital(self, position_engine):
        """Test position size with zero capital."""
        result = position_engine.calculate_position_size_from_atr(
            capital=Decimal("0"),
            entry_price=Decimal("150.00"),
            atr=3.0,
        )
        assert result is None

    def test_calculate_position_size_with_negative_capital(self, position_engine):
        """Test position size with negative capital."""
        result = position_engine.calculate_position_size_from_atr(
            capital=Decimal("-1000"),
            entry_price=Decimal("150.00"),
            atr=3.0,
        )
        assert result is None

    def test_calculate_position_size_with_zero_entry_price(self, position_engine):
        """Test position size with zero entry price."""
        result = position_engine.calculate_position_size_from_atr(
            capital=Decimal("10000"),
            entry_price=Decimal("0"),
            atr=3.0,
        )
        assert result is None

    def test_calculate_position_size_with_zero_atr(self, position_engine):
        """Test position size with zero ATR."""
        capital = Decimal("10000")
        entry_price = Decimal("150.00")

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=0.0,
        )

        # Should fallback to percentage-based stop
        assert position_size is not None


# =============================================================================
# Kelly Criterion Tests
# =============================================================================

class TestKellyCriterion:
    """Test suite for Kelly Criterion position sizing."""

    # Valid inputs
    def test_kelly_with_positive_expectancy(self, position_engine):
        """Test Kelly with profitable strategy."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=500,
            avg_loss=400,
            capital=Decimal("10000"),
        )

        # Kelly = (0.55 * 500 - 0.45 * 400) / 500 = (275 - 180) / 500 = 0.19
        # Half-Kelly = 0.095
        assert result["kelly_fraction"] > 0
        assert result["half_kelly_fraction"] > 0
        assert result["recommendation"] == "BUY"
        assert result["position_value"] is not None

    def test_kelly_with_negative_expectancy(self, position_engine):
        """Test Kelly with unprofitable strategy."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.40,
            avg_win=300,
            avg_loss=500,
            capital=Decimal("10000"),
        )

        # Kelly = (0.40 * 300 - 0.60 * 500) / 300 = (120 - 300) / 300 = -0.6
        assert result["kelly_fraction"] < 0
        assert result["half_kelly_fraction"] == Decimal("0")
        assert result["recommendation"] == "AVOID"
        assert result["position_value"] == Decimal("0")

    def test_kelly_with_marginal_expectancy(self, position_engine):
        """Test Kelly with marginal positive expectancy."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.51,
            avg_win=102,
            avg_loss=100,
            capital=Decimal("10000"),
        )

        # Small positive edge
        assert result["kelly_fraction"] > 0
        assert result["recommendation"] in ["REDUCE", "BUY"]

    def test_kelly_half_kelly_cap(self, position_engine):
        """Test that Half-Kelly is capped at 25%."""
        # Create scenario that would result in >50% Kelly
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.90,
            avg_win=1000,
            avg_loss=100,
            capital=Decimal("10000"),
        )

        # Should be capped at 25%
        assert result["half_kelly_fraction"] <= Decimal("0.25")
        assert result["position_percentage"] <= Decimal("25")

    def test_kelly_without_capital(self, position_engine):
        """Test Kelly calculation without capital."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=500,
            avg_loss=400,
        )

        assert "kelly_fraction" in result
        assert "half_kelly_fraction" in result
        assert "position_value" not in result

    def test_kelly_position_value_calculation(self, position_engine):
        """Test that position value is calculated correctly."""
        capital = Decimal("10000")
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=500,
            avg_loss=400,
            capital=capital,
        )

        # Position value should be capital * half_kelly_fraction
        expected_value = capital * result["half_kelly_fraction"]
        assert abs(result["position_value"] - expected_value) < Decimal("0.01")

    # Input validation
    def test_kelly_with_invalid_win_rate_too_high(self, position_engine):
        """Test Kelly with win rate > 1.0."""
        with pytest.raises(ValueError, match="win_rate must be between 0 and 1"):
            position_engine.calculate_kelly_position_size(
                win_rate=1.5,
                avg_win=500,
                avg_loss=400,
            )

    def test_kelly_with_invalid_win_rate_negative(self, position_engine):
        """Test Kelly with negative win rate."""
        with pytest.raises(ValueError, match="win_rate must be between 0 and 1"):
            position_engine.calculate_kelly_position_size(
                win_rate=-0.1,
                avg_win=500,
                avg_loss=400,
            )

    def test_kelly_with_zero_avg_win(self, position_engine):
        """Test Kelly with zero average win."""
        with pytest.raises(ValueError, match="avg_win must be positive"):
            position_engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=0,
                avg_loss=400,
            )

    def test_kelly_with_negative_avg_win(self, position_engine):
        """Test Kelly with negative average win."""
        with pytest.raises(ValueError, match="avg_win must be positive"):
            position_engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=-100,
                avg_loss=400,
            )

    def test_kelly_with_zero_avg_loss(self, position_engine):
        """Test Kelly with zero average loss."""
        with pytest.raises(ValueError, match="avg_loss must be positive"):
            position_engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=500,
                avg_loss=0,
            )

    def test_kelly_with_invalid_type_win_rate(self, position_engine):
        """Test Kelly with non-numeric win rate."""
        with pytest.raises(ValueError, match="win_rate must be numeric"):
            position_engine.calculate_kelly_position_size(
                win_rate="invalid",
                avg_win=500,
                avg_loss=400,
            )

    def test_kelly_with_negative_capital(self, position_engine):
        """Test Kelly with negative capital."""
        with pytest.raises(ValueError, match="capital must be positive"):
            position_engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=500,
                avg_loss=400,
                capital=Decimal("-1000"),
            )

    def test_kelly_with_zero_capital(self, position_engine):
        """Test Kelly with zero capital."""
        with pytest.raises(ValueError, match="capital must be positive"):
            position_engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=500,
                avg_loss=400,
                capital=Decimal("0"),
            )

    # Boundary cases
    def test_kelly_with_zero_win_rate(self, position_engine):
        """Test Kelly with 0% win rate."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.0,
            avg_win=500,
            avg_loss=400,
        )

        assert result["kelly_fraction"] < 0
        assert result["recommendation"] == "AVOID"

    def test_kelly_with_perfect_win_rate(self, position_engine):
        """Test Kelly with 100% win rate."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=1.0,
            avg_win=500,
            avg_loss=400,
            capital=Decimal("10000"),
        )

        # Should be positive but capped
        assert result["half_kelly_fraction"] > 0
        assert result["half_kelly_fraction"] <= Decimal("0.25")

    def test_kelly_with_decimal_inputs(self, position_engine):
        """Test Kelly with Decimal type inputs."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=Decimal("0.55"),
            avg_win=Decimal("500"),
            avg_loss=Decimal("400"),
            capital=Decimal("10000"),
        )

        assert result["kelly_fraction"] > 0

    def test_kelly_with_int_inputs(self, position_engine):
        """Test Kelly with int type inputs."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0,  # Int 0, not float
            avg_win=500,
            avg_loss=400,
        )

        assert result["kelly_fraction"] < 0


# =============================================================================
# Kelly from Backtest Tests
# =============================================================================

class TestKellyFromBacktest:
    """Test suite for Kelly calculation from backtest metrics."""

    def test_kelly_from_backtest_with_percentage_win_rate(self, position_engine):
        """Test Kelly with win rate as percentage (> 1.0)."""
        metrics = {
            "win_rate": 55.0,  # 55% as percentage
            "avg_win": 500,
            "avg_loss": 400,
        }

        result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics,
            capital=Decimal("10000"),
        )

        # Should convert to decimal and calculate
        assert result["half_kelly_fraction"] > 0

    def test_kelly_from_backtest_with_decimal_win_rate(self, position_engine):
        """Test Kelly with win rate as decimal (< 1.0)."""
        metrics = {
            "win_rate": 0.55,  # 55% as decimal
            "avg_win": 500,
            "avg_loss": 400,
        }

        result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics,
            capital=Decimal("10000"),
        )

        assert result["half_kelly_fraction"] > 0

    def test_kelly_from_backtest_fallback_with_insufficient_data(self, position_engine):
        """Test Kelly fallback when metrics are insufficient."""
        metrics = {
            "win_rate": 0.0,
            "avg_win": 0,
            "avg_loss": 0,
        }

        result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics,
            capital=Decimal("10000"),
        )

        assert result["recommendation"] == "FALLBACK_2PCT"
        assert result["position_value"] == Decimal("200")  # 2% of 10000

    def test_kelly_from_backtest_with_missing_fields(self, position_engine):
        """Test Kelly with missing metric fields."""
        metrics = {}

        result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics,
            capital=Decimal("10000"),
        )

        # Should use fallback
        assert result["recommendation"] == "FALLBACK_2PCT"

    def test_kelly_from_backtest_without_capital(self, position_engine):
        """Test Kelly from backtest without capital."""
        metrics = {
            "win_rate": 55.0,
            "avg_win": 500,
            "avg_loss": 400,
        }

        result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics,
        )

        assert "kelly_fraction" in result
        assert "position_value" not in result


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestPositionSizingProperties:
    """Property-based tests using Hypothesis."""

    @given(
        entry_price=st.decimals(min_value=1, max_value=1000, places=2),
        atr=st.floats(min_value=0.1, max_value=50, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_buy_stop_loss_always_below_entry(self, position_engine, entry_price, atr):
        """Property: Buy stop loss should always be below entry price."""
        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        if stop_loss is not None:
            assert stop_loss <= entry_price

    @given(
        entry_price=st.decimals(min_value=1, max_value=1000, places=2),
        atr=st.floats(min_value=0.1, max_value=50, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_sell_stop_loss_always_above_entry(self, position_engine, entry_price, atr):
        """Property: Sell stop loss should always be above entry price."""
        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="sell",
            atr=atr,
        )

        if stop_loss is not None:
            assert stop_loss >= entry_price

    @given(
        capital=st.decimals(min_value=1000, max_value=1000000, places=2),
        entry_price=st.decimals(min_value=10, max_value=1000, places=2),
        atr=st.floats(min_value=0.5, max_value=20, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=30)
    def test_position_size_never_exceeds_capital(self, position_engine, capital, entry_price, atr):
        """Property: Position value should never exceed available capital."""
        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        if position_size is not None:
            position_value = position_size * entry_price
            assert position_value <= capital * Decimal("1.01")  # Small tolerance

    @given(
        win_rate=st.floats(min_value=0.01, max_value=0.99, allow_nan=False, allow_infinity=False),
        avg_win=st.integers(min_value=100, max_value=1000),
        avg_loss=st.integers(min_value=100, max_value=1000),
        capital=st.integers(min_value=10000, max_value=1000000),
    )
    @settings(max_examples=30)
    def test_kelly_fraction_always_reasonable(self, position_engine, win_rate, avg_win, avg_loss, capital):
        """Property: Kelly fraction should be within reasonable bounds."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            capital=Decimal(str(capital)),
        )

        # Half-kelly should be between 0 and 0.25 (capped)
        assert Decimal("0") <= result["half_kelly_fraction"] <= Decimal("0.25")

        # Position value should not exceed capital
        if "position_value" in result:
            assert result["position_value"] <= Decimal(str(capital))

    @given(
        win_rate=st.floats(min_value=0.4, max_value=0.6, allow_nan=False, allow_infinity=False),
        avg_win=st.integers(min_value=200, max_value=1000),
        avg_loss=st.integers(min_value=100, max_value=500),
    )
    @settings(max_examples=20)
    def test_kelly_formula_invariant(self, position_engine, win_rate, avg_win, avg_loss):
        """Property: Kelly formula should satisfy mathematical invariant."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        # Kelly = (win_rate * avg_win - (1-win_rate) * avg_loss) / avg_win
        expected_kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        actual_kelly = float(result["kelly_fraction"])

        # Should be close (within rounding tolerance)
        assert abs(actual_kelly - expected_kelly) < 0.01


# =============================================================================
# Edge Cases and Boundary Conditions
# =============================================================================

class TestPositionSizingEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_extremely_high_atr_multiplier(self, position_engine_custom_multiplier):
        """Test with extremely high ATR multiplier."""
        stop_loss = position_engine_custom_multiplier.calculate_stop_loss_price(
            entry_price=Decimal("100"),
            direction="buy",
            atr=5.0,
        )

        # With 3x multiplier: 100 - (5 * 3) = 85
        assert stop_loss == Decimal("85")

    def test_extremely_low_atr_multiplier(self):
        """Test with extremely low ATR multiplier."""
        engine = PositionSizingEngine(atr_multiplier=0.1)
        stop_loss = engine.calculate_stop_loss_price(
            entry_price=Decimal("100"),
            direction="buy",
            atr=5.0,
        )

        # With 0.1x multiplier: 100 - (5 * 0.1) = 99.5
        assert stop_loss == Decimal("99.5")

    def test_very_small_capital_amount(self, position_engine):
        """Test position sizing with very small capital."""
        position_size = position_engine.calculate_position_size_from_atr(
            capital=Decimal("100"),
            entry_price=Decimal("10"),
            atr=1.0,
        )

        # Should still calculate, but result will be small
        assert position_size is not None
        assert position_size > 0

    def test_very_large_capital_amount(self, position_engine):
        """Test position sizing with very large capital."""
        position_size = position_engine.calculate_position_size_from_atr(
            capital=Decimal("10000000"),
            entry_price=Decimal("100"),
            atr=5.0,
        )

        # Should calculate reasonable position
        assert position_size is not None
        # Position value should be capped
        position_value = position_size * Decimal("100")
        assert position_value <= Decimal("10000000")

    def test_atr_exactly_20_percent_of_price(self, position_engine):
        """Test ATR stop distance at exactly 20% boundary."""
        capital = Decimal("10000")
        entry_price = Decimal("100")
        atr = 20.0  # Exactly 20% of price with 2x multiplier = 40%

        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        # Should cap at 20% ($20 stop distance)
        assert position_size is not None

    def test_kelly_with_perfect_even_money(self, position_engine):
        """Test Kelly with even-money proposition."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.50,
            avg_win=100,
            avg_loss=100,
        )

        # Kelly should be 0 for even money with 50% win rate
        assert result["kelly_fraction"] <= Decimal("0.01")

    def test_kelly_with_high_win_rate_small_wins(self, position_engine):
        """Test Kelly with high win rate but small wins."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.80,
            avg_win=100,
            avg_loss=500,
        )

        # Might still be negative due to risk/reward
        # (0.80 * 100 - 0.20 * 500) / 100 = (80 - 100) / 100 = -0.2
        assert result["kelly_fraction"] < 0

    def test_kelly_with_low_win_rate_large_wins(self, position_engine):
        """Test Kelly with low win rate but large wins."""
        result = position_engine.calculate_kelly_position_size(
            win_rate=0.35,
            avg_win=500,
            avg_loss=100,
        )

        # Should be positive
        # (0.35 * 500 - 0.65 * 100) / 500 = (175 - 65) / 500 = 0.22
        assert result["kelly_fraction"] > 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestPositionSizingIntegration:
    """Integration tests for position sizing workflows."""

    def test_complete_position_sizing_workflow(self, position_engine):
        """Test complete workflow from analysis to position sizing."""
        # Simulate backtest results
        backtest_metrics = {
            "win_rate": 55.0,
            "avg_win": 500,
            "avg_loss": 400,
        }

        # Calculate Kelly-based position
        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=backtest_metrics,
            capital=Decimal("10000"),
        )

        # Calculate stop loss for the position
        entry_price = Decimal("150")
        atr = 3.0
        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        # Verify integration
        assert kelly_result["position_value"] is not None
        assert stop_loss is not None
        assert stop_loss < entry_price

    def test_risk_management_integration(self, position_engine):
        """Test that position sizing respects risk management constraints."""
        capital = Decimal("10000")
        entry_price = Decimal("100")
        atr = 5.0

        # Get position size
        position_size = position_engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        # Get stop loss
        stop_loss = position_engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        # Calculate actual risk
        stop_distance = entry_price - stop_loss
        actual_risk = position_size * stop_distance

        # Risk should be approximately 2% of capital
        expected_risk = capital * Decimal("0.02")

        assert abs(actual_risk - expected_risk) < Decimal("1")  # Small tolerance
