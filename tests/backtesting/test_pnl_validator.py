"""
Tests for P&L validator.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from app.backtesting.validation.pnl_validator import PnLValidator, PnLValidationError
from app.backtesting.models import Trade, TradeStatus


@pytest.fixture
def sample_long_trade(default_symbol):
    """Create a sample long trade."""
    return Trade(
        trade_id="TEST001",
        symbol=default_symbol,
        side="buy",
        quantity=Decimal("100"),
        entry_price=Decimal("150.00"),
        exit_price=Decimal("155.00"),
        entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        exit_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        status=TradeStatus.CLOSED,
        pnl=Decimal("499.50"),  # (155-150) * 100 - 0.50 commission = 499.50
        commission=Decimal("0.50"),
    )


@pytest.fixture
def sample_short_trade(default_symbol):
    """Create a sample short trade."""
    return Trade(
        trade_id="TEST002",
        symbol=default_symbol,
        side="sell",
        quantity=Decimal("100"),
        entry_price=Decimal("150.00"),
        exit_price=Decimal("145.00"),
        entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        exit_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        status=TradeStatus.CLOSED,
        pnl=Decimal("499.50"),  # (150-145) * 100 - 0.50 commission = 499.50
        commission=Decimal("0.50"),
    )


@pytest.fixture
def validator():
    """Create P&L validator."""
    return PnLValidator()


def test_validate_trade_pnl_correct_long(validator, sample_long_trade):
    """Test validation of correct P&L for long trade."""
    assert validator.validate_trade_pnl(sample_long_trade) is True


def test_validate_trade_pnl_correct_short(validator, sample_short_trade):
    """Test validation of correct P&L for short trade."""
    assert validator.validate_trade_pnl(sample_short_trade) is True


def test_validate_trade_pnl_incorrect(validator, sample_long_trade):
    """Test validation fails for incorrect P&L."""
    sample_long_trade.pnl = Decimal("600.00")  # Wrong P&L
    with pytest.raises(PnLValidationError) as exc:
        validator.validate_trade_pnl(sample_long_trade)
    assert "P&L mismatch" in str(exc.value)


def test_validate_trade_pnl_missing(validator, sample_long_trade):
    """Test validation fails for missing P&L."""
    sample_long_trade.pnl = None
    with pytest.raises(PnLValidationError) as exc:
        validator.validate_trade_pnl(sample_long_trade)
    assert "no P&L value" in str(exc.value)


def test_validate_trade_pnl_missing_prices(validator, sample_long_trade):
    """Test validation fails for missing entry/exit prices."""
    sample_long_trade.exit_price = None
    with pytest.raises(PnLValidationError) as exc:
        validator.validate_trade_pnl(sample_long_trade)
    assert "missing entry/exit price" in str(exc.value)


def test_validate_trade_pnl_open_trade_skipped(validator, default_symbol):
    """Test that open trades are skipped."""
    open_trade = Trade(
        trade_id="TEST003",
        symbol=default_symbol,
        side="buy",
        quantity=Decimal("100"),
        entry_price=Decimal("150.00"),
        exit_price=None,
        entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        exit_time=None,
        status=TradeStatus.OPEN,
        pnl=None,
    )
    assert validator.validate_trade_pnl(open_trade) is True


def test_validate_total_pnl_correct(validator, sample_long_trade, sample_short_trade):
    """Test validation of correct total P&L."""
    trades = [sample_long_trade, sample_short_trade]
    total = sum(t.pnl for t in trades)
    assert validator.validate_total_pnl(trades, total) is True


def test_validate_total_pnl_incorrect(validator, sample_long_trade):
    """Test validation fails for incorrect total P&L."""
    trades = [sample_long_trade]
    with pytest.raises(PnLValidationError) as exc:
        validator.validate_total_pnl(trades, Decimal("1000.00"))
    assert "Total P&L mismatch" in str(exc.value)


def test_validate_trades_pnl_all_valid(validator, sample_long_trade, sample_short_trade):
    """Test validation of all valid trades."""
    trades = [sample_long_trade, sample_short_trade]
    all_valid, errors = validator.validate_trades_pnl(trades)
    assert all_valid is True
    assert len(errors) == 0


def test_validate_trades_pnl_mixed_validity(validator, sample_long_trade):
    """Test validation with mixed valid/invalid trades."""
    sample_long_trade.pnl = Decimal("1000.00")  # Wrong
    trades = [sample_long_trade]
    all_valid, errors = validator.validate_trades_pnl(trades)
    assert all_valid is False
    assert len(errors) > 0


def test_validate_commission_reasonable(validator):
    """Test validation of reasonable commission."""
    assert validator.validate_commission(Decimal("10000"), Decimal("1")) is True


def test_validate_commission_too_high(validator):
    """Test validation fails for excessive commission."""
    with pytest.raises(PnLValidationError) as exc:
        validator.validate_commission(Decimal("100"), Decimal("5"))  # 5%
    assert "too high" in str(exc.value)


def test_validate_commission_zero_trade_value(validator):
    """Test validation with zero trade value."""
    assert validator.validate_commission(Decimal("0"), Decimal("1")) is True


def test_validate_pnl_consistency_correct(validator, sample_long_trade):
    """Test P&L consistency with capital changes."""
    trades = [sample_long_trade]
    initial = Decimal("10000")
    final = initial + sample_long_trade.pnl
    assert validator.validate_pnl_consistency(trades, initial, final) is True


def test_validate_pnl_consistency_incorrect(validator, sample_long_trade):
    """Test validation fails for inconsistent capital."""
    trades = [sample_long_trade]
    with pytest.raises(PnLValidationError) as exc:
        validator.validate_pnl_consistency(trades, Decimal("10000"), Decimal("20000"))
    assert "Capital inconsistency" in str(exc.value)


def test_validate_pnl_consistency_no_closed_trades(validator, default_symbol):
    """Test P&L consistency with no closed trades."""
    open_trade = Trade(
        trade_id="TEST004",
        symbol=default_symbol,
        side="buy",
        quantity=Decimal("100"),
        entry_price=Decimal("150.00"),
        exit_price=None,
        entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        exit_time=None,
        status=TradeStatus.OPEN,
    )
    # Should be consistent with no P&L from open trades
    assert validator.validate_pnl_consistency([open_trade], Decimal("10000"), Decimal("10000")) is True


def test_validator_custom_thresholds():
    """Test validator with custom thresholds."""
    custom_validator = PnLValidator(
        max_difference_bps=Decimal("10"),  # 10 bps tolerance
        max_commission_pct=Decimal("0.05"),  # 5% max commission
    )
    assert custom_validator.max_difference_bps == Decimal("10")
    assert custom_validator.max_commission_pct == Decimal("0.05")


def test_validate_trade_pnl_with_commission(validator, default_symbol):
    """Test that commission is properly subtracted from P&L."""
    trade = Trade(
        trade_id="TEST005",
        symbol=default_symbol,
        side="buy",
        quantity=Decimal("100"),
        entry_price=Decimal("150.00"),
        exit_price=Decimal("155.00"),
        entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        exit_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        status=TradeStatus.CLOSED,
        pnl=Decimal("498.00"),  # 500 - 2 commission
        commission=Decimal("2.00"),
    )
    assert validator.validate_trade_pnl(trade) is True


def test_validate_trade_pnl_wrong_commission(validator, default_symbol):
    """Test that wrong commission is detected."""
    trade = Trade(
        trade_id="TEST006",
        symbol=default_symbol,
        side="buy",
        quantity=Decimal("100"),
        entry_price=Decimal("150.00"),
        exit_price=Decimal("155.00"),
        entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        exit_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        status=TradeStatus.CLOSED,
        pnl=Decimal("500.00"),  # Should be 498 with commission
        commission=Decimal("2.00"),
    )
    with pytest.raises(PnLValidationError):
        validator.validate_trade_pnl(trade)
