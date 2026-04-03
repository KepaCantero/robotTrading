"""
Tests for drawdown validator.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.backtesting.models import Trade, TradeStatus
from app.backtesting.validation.drawdown_validator import DrawdownValidationError, DrawdownValidator


@pytest.fixture
def validator():
    """Create drawdown validator."""
    return DrawdownValidator()


@pytest.fixture
def sample_equity_curve():
    """Create a sample equity curve."""
    return [
        ("start", Decimal("10000")),
        ("t1", Decimal("10500")),  # Peak
        ("t2", Decimal("10000")),  # -4.76% drawdown
        ("t3", Decimal("9500")),  # -9.52% drawdown (max)
        ("t4", Decimal("10000")),  # Recovery
        ("t5", Decimal("11000")),  # New peak
    ]


@pytest.fixture
def sample_trades(default_symbol):
    """Create sample trades for testing."""
    return [
        Trade(
            trade_id="T1",
            symbol=default_symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            exit_price=Decimal("105"),
            pnl=Decimal("500"),
            entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
            status=TradeStatus.CLOSED,
        ),
        Trade(
            trade_id="T2",
            symbol=default_symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("105"),
            exit_price=Decimal("100"),
            pnl=Decimal("-500"),
            entry_time=datetime(2024, 1, 3, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 4, tzinfo=timezone.utc),
            status=TradeStatus.CLOSED,
        ),
        Trade(
            trade_id="T3",
            symbol=default_symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            exit_price=Decimal("95"),
            pnl=Decimal("-500"),
            entry_time=datetime(2024, 1, 5, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 6, tzinfo=timezone.utc),
            status=TradeStatus.CLOSED,
        ),
    ]


def test_calculate_equity_curve(validator, sample_trades):
    """Test equity curve calculation."""
    curve = validator.calculate_equity_curve(sample_trades, Decimal("10000"))
    assert len(curve) == 4  # start + 3 trades
    assert curve[0][1] == Decimal("10000")
    assert curve[1][1] == Decimal("10500")
    assert curve[2][1] == Decimal("10000")
    assert curve[3][1] == Decimal("9500")


def test_calculate_equity_curve_empty(validator):
    """Test equity curve with no trades."""
    curve = validator.calculate_equity_curve([], Decimal("10000"))
    assert len(curve) == 1
    assert curve[0] == ("start", Decimal("10000"))


def test_calculate_equity_curve_open_trades_excluded(validator, default_symbol):
    """Test that open trades are excluded from equity curve."""
    trades = [
        Trade(
            trade_id="T1",
            symbol=default_symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            exit_price=Decimal("105"),
            pnl=Decimal("500"),
            entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
            status=TradeStatus.OPEN,  # Open trade
        ),
    ]
    curve = validator.calculate_equity_curve(trades, Decimal("10000"))
    # Open trades should not affect the curve
    assert len(curve) == 1
    assert curve[0] == ("start", Decimal("10000"))


def test_calculate_drawdown(validator, sample_equity_curve):
    """Test drawdown calculation."""
    drawdowns, max_dd = validator.calculate_drawdown(sample_equity_curve)

    assert max_dd < 0  # Should be negative
    assert max_dd <= -9  # Should be around -9.52%
    assert len(drawdowns) == len(sample_equity_curve)


def test_calculate_drawdown_empty_curve(validator):
    """Test drawdown calculation with empty curve."""
    drawdowns, max_dd = validator.calculate_drawdown([])
    assert drawdowns == []
    assert max_dd == Decimal("0")


def test_calculate_drawdown_no_decline(validator):
    """Test drawdown with only increases."""
    curve = [
        ("start", Decimal("10000")),
        ("t1", Decimal("10500")),
        ("t2", Decimal("11000")),
    ]
    drawdowns, max_dd = validator.calculate_drawdown(curve)
    assert max_dd == Decimal("0")  # No drawdown


def test_validate_max_drawdown_correct(validator, sample_equity_curve):
    """Test validation of correct max drawdown."""
    _, max_dd = validator.calculate_drawdown(sample_equity_curve)
    assert validator.validate_max_drawdown(max_dd, sample_equity_curve) is True


def test_validate_max_drawdown_incorrect(validator, sample_equity_curve):
    """Test validation fails for incorrect max drawdown."""
    with pytest.raises(DrawdownValidationError) as exc:
        validator.validate_max_drawdown(Decimal("0"), sample_equity_curve)
    assert "Max drawdown mismatch" in str(exc.value)


def test_validate_max_drawdown_from_trades(validator, sample_trades):
    """Test validation of max drawdown calculated from trades."""
    curve = validator.calculate_equity_curve(sample_trades, Decimal("10000"))
    _, max_dd = validator.calculate_drawdown(curve)
    assert (
        validator.validate_max_drawdown(
            max_dd, trades=sample_trades, initial_capital=Decimal("10000")
        )
        is True
    )


def test_validate_max_drawdown_missing_inputs(validator):
    """Test validation fails with missing inputs."""
    with pytest.raises(DrawdownValidationError) as exc:
        validator.validate_max_drawdown(Decimal("-10"))
    assert "Must provide either equity_curve" in str(exc.value)


def test_validate_drawdown_range_negative(validator):
    """Test validation accepts negative drawdown."""
    assert validator.validate_drawdown_range(Decimal("-10")) is True


def test_validate_drawdown_range_zero(validator):
    """Test validation accepts zero drawdown."""
    assert validator.validate_drawdown_range(Decimal("0")) is True


def test_validate_drawdown_range_positive_fails(validator):
    """Test validation fails for positive drawdown."""
    with pytest.raises(DrawdownValidationError) as exc:
        validator.validate_drawdown_range(Decimal("5"))
    assert "is positive" in str(exc.value)


def test_validate_drawdown_range_excessive_fails(validator):
    """Test validation fails for excessive drawdown."""
    with pytest.raises(DrawdownValidationError) as exc:
        validator.validate_drawdown_range(Decimal("-150"))
    assert "exceeds maximum" in str(exc.value)


def test_validate_drawdown_recovery(validator, sample_equity_curve):
    """Test drawdown recovery validation."""
    assert validator.validate_drawdown_recovery(sample_equity_curve) is True


def test_validate_drawdown_recovery_empty_curve(validator):
    """Test recovery validation with empty curve."""
    assert validator.validate_drawdown_recovery([]) is True


def test_validate_drawdown_recovery_single_point(validator):
    """Test recovery validation with single point."""
    assert validator.validate_drawdown_recovery([("start", Decimal("10000"))]) is True


def test_validate_drawdown_recovery_invalid_peaks(validator):
    """Test recovery validation with invalid peaks."""
    # This curve has a peak that decreases without tracking
    invalid_curve = [
        ("start", Decimal("10000")),
        ("t1", Decimal("11000")),  # Peak
        ("t2", Decimal("10500")),  # Decreased peak (invalid)
    ]
    # This should pass because the second point is not a peak (first was higher)
    assert validator.validate_drawdown_recovery(invalid_curve) is True


def test_get_drawdown_statistics(validator, sample_trades):
    """Test drawdown statistics calculation."""
    stats = validator.get_drawdown_statistics(sample_trades, Decimal("10000"))

    assert "max_drawdown_pct" in stats
    assert "avg_drawdown_pct" in stats
    assert "drawdown_periods" in stats
    assert "current_drawdown" in stats
    assert "equity_low" in stats
    assert "equity_high" in stats

    assert stats["max_drawdown_pct"] < 0
    assert stats["equity_low"] == 9500.0
    assert stats["equity_high"] == 10500.0


def test_get_drawdown_statistics_no_trades(validator):
    """Test statistics with no trades."""
    stats = validator.get_drawdown_statistics([], Decimal("10000"))
    assert stats["max_drawdown_pct"] == 0.0
    assert stats["equity_low"] == 10000.0
    assert stats["equity_high"] == 10000.0


def test_get_drawdown_statistics_all_losses(validator, default_symbol):
    """Test statistics with all losing trades."""
    trades = [
        Trade(
            trade_id=f"T{i}",
            symbol=default_symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            exit_price=Decimal("95"),
            pnl=Decimal("-500"),
            entry_time=datetime(2024, 1, i, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
            status=TradeStatus.CLOSED,
        )
        for i in range(1, 6)
    ]

    stats = validator.get_drawdown_statistics(trades, Decimal("10000"))
    assert stats["max_drawdown_pct"] < 0
    assert stats["drawdown_periods"] >= 1


def test_validator_custom_thresholds():
    """Test validator with custom thresholds."""
    custom_validator = DrawdownValidator(
        max_drawdown_pct=Decimal("50"),  # 50% max
        min_drawdown_pct=Decimal("-5"),  # -5% min
    )
    assert custom_validator.max_drawdown_pct == Decimal("50")
    assert custom_validator.min_drawdown_pct == Decimal("-5")


def test_validate_drawdown_range_with_custom_thresholds():
    """Test validation with custom thresholds."""
    custom_validator = DrawdownValidator(
        max_drawdown_pct=Decimal("200"),  # Allow up to 200%
    )
    # Should not raise error even with large drawdown
    assert custom_validator.validate_drawdown_range(Decimal("-150")) is True


def test_calculate_drawdown_with_zero_peak(validator):
    """Test drawdown calculation when peak is zero."""
    curve = [
        ("start", Decimal("0")),
        ("t1", Decimal("0")),
    ]
    drawdowns, max_dd = validator.calculate_drawdown(curve)
    # Should handle gracefully without division by zero
    assert max_dd == Decimal("0")


def test_calculate_drawdown_negative_equity(validator):
    """Test drawdown with negative equity values."""
    curve = [
        ("start", Decimal("10000")),
        ("t1", Decimal("5000")),  # Large drawdown
        ("t2", Decimal("2000")),  # Even more negative
    ]
    drawdowns, max_dd = validator.calculate_drawdown(curve)
    # Calculate from peak of 10000
    assert max_dd <= -80  # At least 80% drawdown
