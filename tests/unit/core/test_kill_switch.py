"""
Unit tests for Kill Switch functionality (Hull Rule 13.1).

Tests the critical kill switch that triggers when daily loss exceeds 5%.
"""

from decimal import Decimal

import pytest

from app.core.compliance_engine import ComplianceEngine


@pytest.fixture(autouse=True)
def reset_kill_switch_state():
    """Reset kill switch state before each test."""
    # Get the singleton instance
    engine = ComplianceEngine(enable_logging=False)
    # Reset daily tracking
    engine.reset_daily_tracking()
    # Reset starting capital to default
    engine.set_starting_capital(100000.0)
    yield
    # Cleanup after test
    engine.reset_daily_tracking()


class TestKillSwitch:
    """Test suite for Hull Rule 13.1 - Kill Switch."""

    def test_kill_switch_initially_inactive(self):
        """Test that kill switch is initially inactive."""
        engine = ComplianceEngine(enable_logging=False)
        assert not engine.check_kill_switch()
        summary = engine.get_daily_pnl_summary()
        assert not summary["kill_switch_active"]

    def test_kill_switch_triggers_at_5_percent_loss(self):
        """Test that kill switch triggers at exactly 5% daily loss."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Track losses totaling exactly 5% (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=-5000.0,
        )

        # Kill switch should be triggered
        assert engine.check_kill_switch()
        summary = engine.get_daily_pnl_summary()
        assert summary["kill_switch_active"]
        assert summary["daily_return_pct"] == -0.05

    def test_kill_switch_triggers_above_5_percent_loss(self):
        """Test that kill switch triggers above 5% daily loss."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Track losses totaling 6% (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=-6000.0,
        )

        # Kill switch should be triggered
        assert engine.check_kill_switch()
        summary = engine.get_daily_pnl_summary()
        assert summary["kill_switch_active"]
        assert summary["daily_return_pct"] == -0.06

    def test_kill_switch_does_not_trigger_below_5_percent_loss(self):
        """Test that kill switch does NOT trigger below 5% daily loss."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Track losses totaling 4.9% (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=-4900.0,
        )

        # Kill switch should NOT be triggered
        assert not engine.check_kill_switch()
        summary = engine.get_daily_pnl_summary()
        assert not summary["kill_switch_active"]
        assert summary["daily_return_pct"] == -0.049

    def test_kill_switch_blocks_trades_when_active(self):
        """Test that kill switch blocks trades when active."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Trigger kill switch (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=-6000.0,
        )

        # Try to execute a trade - should be blocked
        analysis = engine.analyze_pre_trade(
            symbol="TSLA",
            side="BUY",
            quantity=Decimal("50"),
            price=Decimal("200"),
        )

        assert not analysis.can_execute
        assert analysis.confidence == 0.0
        assert any("KILL SWITCH" in reason for reason in analysis.reasons)

    def test_kill_switch_allows_trades_when_inactive(self):
        """Test that trades are allowed when kill switch is inactive."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Small profit - kill switch should not trigger (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=500.0,
        )

        # Try to execute a trade - should be allowed (assuming other checks pass)
        analysis = engine.analyze_pre_trade(
            symbol="TSLA",
            side="BUY",
            quantity=Decimal("50"),
            price=Decimal("200"),
        )

        # Kill switch should not block
        assert not any("KILL SWITCH" in reason for reason in analysis.reasons)

    def test_reset_daily_tracking(self):
        """Test that daily tracking can be reset."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Track some losses (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=-6000.0,
        )

        assert engine.check_kill_switch()

        # Reset daily tracking
        engine.reset_daily_tracking()

        # Kill switch should now be inactive
        assert not engine.check_kill_switch()
        summary = engine.get_daily_pnl_summary()
        assert not summary["kill_switch_active"]
        assert summary["total_trades"] == 0

    def test_reset_with_new_capital(self):
        """Test resetting with new starting capital."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Reset with new capital
        engine.reset_daily_tracking(new_starting_capital=150000.0)

        summary = engine.get_daily_pnl_summary()
        assert summary["starting_capital"] == 150000.0

    def test_set_starting_capital_validation(self):
        """Test that starting capital must be positive."""
        engine = ComplianceEngine(enable_logging=False)

        # Valid capital
        engine.set_starting_capital(50000.0)
        assert engine._starting_capital == 50000.0

        # Invalid capital
        with pytest.raises(ValueError, match="must be positive"):
            engine.set_starting_capital(-1000.0)

        with pytest.raises(ValueError, match="must be positive"):
            engine.set_starting_capital(0.0)

    def test_daily_pnl_summary(self):
        """Test daily P&L summary calculation."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Track multiple trades (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=500.0,
        )

        engine.track_daily_pnl(
            symbol="TSLA",
            side="SELL",
            quantity=Decimal("50"),
            entry_price=Decimal("200"),
            realized_pnl=250.0,
        )

        engine.track_daily_pnl(
            symbol="MSFT",
            side="BUY",
            quantity=Decimal("80"),
            entry_price=Decimal("300"),
            realized_pnl=-800.0,
        )

        summary = engine.get_daily_pnl_summary()
        assert summary["total_trades"] == 3
        assert summary["winning_trades"] == 2
        assert summary["losing_trades"] == 1
        assert summary["total_pnl"] == -50.0  # 500 + 250 - 800
        assert summary["daily_return_pct"] == -0.0005
        assert summary["win_rate"] == 2 / 3
        assert not summary["kill_switch_active"]

    def test_pnl_calculation_for_long_trades(self):
        """Test P&L calculation for long (BUY) trades."""
        engine = ComplianceEngine(enable_logging=False)

        # Long trade profit (using exit_price to calculate)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            exit_price=Decimal("160"),
        )

        summary = engine.get_daily_pnl_summary()
        assert summary["total_pnl"] == 1000.0  # (160 - 150) * 100

    def test_pnl_calculation_for_short_trades(self):
        """Test P&L calculation for short (SELL) trades."""
        engine = ComplianceEngine(enable_logging=False)

        # Short trade profit (using exit_price to calculate)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            entry_price=Decimal("160"),
            exit_price=Decimal("150"),
        )

        summary = engine.get_daily_pnl_summary()
        assert summary["total_pnl"] == 1000.0  # (160 - 150) * 100

    def test_multiple_losses_accumulate(self):
        """Test that multiple losses accumulate for kill switch."""
        engine = ComplianceEngine(enable_logging=False)
        engine.set_starting_capital(100000.0)

        # Multiple small losses that total > 5% (using only realized_pnl)
        engine.track_daily_pnl(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            realized_pnl=-2000.0,
        )

        engine.track_daily_pnl(
            symbol="TSLA",
            side="BUY",
            quantity=Decimal("50"),
            entry_price=Decimal("200"),
            realized_pnl=-2000.0,
        )

        engine.track_daily_pnl(
            symbol="MSFT",
            side="BUY",
            quantity=Decimal("80"),
            entry_price=Decimal("300"),
            realized_pnl=-800.0,
        )

        # Total loss: $4,800 (4.8%) - should not trigger yet
        assert not engine.check_kill_switch()

        # One more loss to push over 5%
        engine.track_daily_pnl(
            symbol="GOOGL",
            side="BUY",
            quantity=Decimal("30"),
            entry_price=Decimal("2500"),
            realized_pnl=-1000.0,
        )

        # Total loss: $5,800 (5.8%) - should trigger
        assert engine.check_kill_switch()

    def test_kill_switch_with_no_trades(self):
        """Test kill switch behavior when no trades tracked."""
        engine = ComplianceEngine(enable_logging=False)

        # No trades - should not trigger
        assert not engine.check_kill_switch()

        summary = engine.get_daily_pnl_summary()
        assert summary["total_trades"] == 0
        assert summary["total_pnl"] == 0.0
        assert not summary["kill_switch_active"]
