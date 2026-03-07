"""
CRITICAL TESTS: Stop-Loss Functionality

These tests are CRITICAL for financial safety. Stop-loss failures
can lead to uncontrolled losses and account liquidation.

Audit Finding: ZERO tests for stop-loss logic - this is a CRITICAL gap.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, TradeStatus
from app.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


# Helper function to create timestamps in the past
def past_time(hours_ago=1):
    """Create a datetime in the past for testing."""
    return datetime.utcnow() - timedelta(hours=hours_ago)


class TestStopLossCritical:
    """CRITICAL: Stop-loss must always work correctly."""

    @pytest.fixture
    def backtester(self):
        """Create backtester with stop-loss enabled."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            stop_loss_percentage=Decimal("5"),  # 5% stop-loss
            take_profit_percentage=Decimal("10"),  # 10% take-profit
        )
        return SimpleBacktester(config)

    @pytest.fixture
    def buy_signal(self):
        """Create a standard buy signal."""
        return Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=2),
            metadata={"strategy": "test_strategy"},
        )

    @pytest.fixture
    def entry_quote(self):
        """Create a quote for entry."""
        return Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

    def test_stop_loss_triggers_on_decline(self, backtester, buy_signal, entry_quote):
        """Test that stop-loss triggers when price declines 5%."""
        # Execute buy at $100
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Verify position opened
        assert "AAPL" in backtester.positions
        assert backtester.positions["AAPL"] > 0
        backtester.capital

        # Simulate price dropping to $94 (6% decline - below 5% stop-loss)
        quote_decline = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("93.5"),
            ask=Decimal("94.5"),
            last=Decimal("94"),
            open=Decimal("95"),
            high=Decimal("95"),
            low=Decimal("94"),
            close=Decimal("94"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        # This should trigger stop-loss
        backtester._check_exit_conditions(quote_decline)

        # Verify position closed
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal(
            "0"
        ), "Position should be closed after stop-loss"

        # Verify trade was closed with loss
        closed_trades = [t for t in backtester.trades if t.status == TradeStatus.CLOSED]
        assert len(closed_trades) > 0, "Should have closed trades"

        # Verify P&L is negative (loss)
        final_trade = closed_trades[-1]
        assert final_trade.pnl < 0, f"Stop-loss trade should have loss, got PnL={final_trade.pnl}"

        # Verify loss is approximately 5% (not 50%)
        loss_percentage = abs(final_trade.pnl_percentage)
        assert (
            Decimal("4") <= loss_percentage <= Decimal("7")
        ), f"Loss should be ~5%, got {loss_percentage}% (PnL={final_trade.pnl})"

    def test_stop_loss_does_not_trigger_small_decline(self, backtester, buy_signal, entry_quote):
        """Test that stop-loss does NOT trigger on small 2% decline."""
        # Execute buy
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Simulate small decline to $98 (2% - above 5% stop-loss threshold)
        quote_small_decline = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("97.5"),
            ask=Decimal("98.5"),
            last=Decimal("98"),
            open=Decimal("99"),
            high=Decimal("99"),
            low=Decimal("98"),
            close=Decimal("98"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        # This should NOT trigger stop-loss
        backtester._check_exit_conditions(quote_small_decline)

        # Verify position still open
        assert (
            backtester.positions.get("AAPL", Decimal("0")) > 0
        ), "Position should remain open for small decline"

    def test_stop_loss_and_take_profit_same_bar(self, backtester, buy_signal, entry_quote):
        """
        Test pessimistic execution: SL before TP when both hit in same bar.

        Entry: $100
        Stop-loss: $95 (-5%)
        Take-profit: $110 (+10%)

        Bar: Low=$94 (hit SL), High=$111 (hit TP)
        Expected: SL executes (worst case - pessimistic execution)
        """
        # Execute buy
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Bar that hits BOTH SL and TP
        quote_both = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("94.5"),
            ask=Decimal("111.5"),
            last=Decimal("105"),
            open=Decimal("110"),
            high=Decimal("111"),  # Above TP ($110)
            low=Decimal("94"),  # Below SL ($95)
            close=Decimal("105"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_both)

        # Verify position closed
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal(
            "0"
        ), "Position should be closed when both SL and TP hit"

        # Verify exit was at stop-loss price (pessimistic)
        closed_trades = [t for t in backtester.trades if t.status == TradeStatus.CLOSED]
        assert len(closed_trades) > 0, "Should have closed trades"

        final_trade = closed_trades[-1]
        # Exit price should reflect stop-loss, not take-profit
        # The actual exit price depends on implementation, but PnL should be negative
        assert (
            final_trade.pnl < 0
        ), f"PnL should be negative (SL hit, not TP), got {final_trade.pnl}"

        # Verify loss is in the stop-loss range (~5-6%)
        loss_percentage = abs(final_trade.pnl_percentage)
        assert (
            Decimal("4") <= loss_percentage <= Decimal("8")
        ), f"Loss should be ~5-6% (SL range), got {loss_percentage}%"

    def test_stop_loss_prevents_catastrophic_loss(self, backtester, buy_signal, entry_quote):
        """
        Test that stop-loss prevents catastrophic 50% loss.

        Without SL: 50% loss = $50,000 loss
        With SL: 5% loss = $5,000 loss
        """
        # Store initial total capital before any trades
        initial_total_capital = backtester.capital

        # Execute buy
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Simulate catastrophic 50% drop to $50
        quote_crash = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("49.5"),
            ask=Decimal("50.5"),
            last=Decimal("50"),
            open=Decimal("60"),
            high=Decimal("60"),
            low=Decimal("50"),  # 50% crash!
            close=Decimal("50"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_crash)

        # Verify position closed at stop-loss, not at bottom
        final_capital = backtester.capital

        # Loss should be ~5% (stop-loss), not 50%
        # Calculate loss relative to initial total capital
        loss_amount = initial_total_capital - final_capital
        loss_pct = (loss_amount / initial_total_capital) * 100

        assert loss_pct < Decimal(
            "10"
        ), f"Loss {loss_pct:.2f}% exceeds 10% - stop-loss failed to prevent catastrophic loss!"

        assert loss_pct > 0, f"Should have a small loss ({loss_pct}%), not a gain"

        # Position should be closed
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal(
            "0"
        ), "Position should be closed after crash"

    def test_take_profit_triggers_on_rise(self, backtester, buy_signal, entry_quote):
        """Test that take-profit triggers when price rises 10%."""
        # Execute buy
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Simulate price rising to $111 (11% rise - above 10% TP)
        quote_rise = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("110.5"),
            ask=Decimal("111.5"),
            last=Decimal("111"),
            open=Decimal("110"),
            high=Decimal("111"),
            low=Decimal("110"),
            close=Decimal("111"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_rise)

        # Verify position closed
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal(
            "0"
        ), "Position should be closed after take-profit"

        # Verify P&L is positive (profit)
        closed_trades = [t for t in backtester.trades if t.status == TradeStatus.CLOSED]
        assert len(closed_trades) > 0, "Should have closed trades"

        final_trade = closed_trades[-1]
        assert (
            final_trade.pnl > 0
        ), f"Take-profit trade should have profit, got PnL={final_trade.pnl}"

        # Verify profit is approximately 10%
        profit_percentage = final_trade.pnl_percentage
        assert (
            Decimal("8") <= profit_percentage <= Decimal("12")
        ), f"Profit should be ~10%, got {profit_percentage}%"

    def test_stop_loss_exact_threshold(self, backtester, buy_signal, entry_quote):
        """Test stop-loss behavior at exact 5% threshold."""
        # Execute buy at $100
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Simulate price dropping exactly to $95 (5% - at stop-loss threshold)
        quote_exact_sl = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("94.5"),
            ask=Decimal("95.5"),
            last=Decimal("95"),
            open=Decimal("95"),
            high=Decimal("95"),
            low=Decimal("95"),
            close=Decimal("95"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_exact_sl)

        # Verify position closed (exact threshold should trigger)
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal(
            "0"
        ), "Position should be closed at exact stop-loss threshold"

    def test_take_profit_exact_threshold(self, backtester, buy_signal, entry_quote):
        """Test take-profit behavior at exact 10% threshold."""
        # Execute buy at $100
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Get the actual entry price (includes slippage)
        actual_entry_price = backtester.trades[-1].entry_price
        # Calculate expected take-profit price (10% above actual entry)
        expected_tp_price = actual_entry_price * (Decimal("1") + Decimal("10") / Decimal("100"))

        # Simulate price rising exactly to the take-profit threshold
        # Use the calculated threshold to account for slippage
        quote_exact_tp = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=expected_tp_price - Decimal("0.5"),
            ask=expected_tp_price + Decimal("0.5"),
            last=expected_tp_price,
            open=expected_tp_price,
            high=expected_tp_price,  # Exactly at TP threshold
            low=expected_tp_price,
            close=expected_tp_price,
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_exact_tp)

        # Verify position closed (exact threshold should trigger)
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal(
            "0"
        ), "Position should be closed at exact take-profit threshold"

    def test_no_stop_loss_config(self):
        """Test that trading without stop-loss configuration works (but is not recommended)."""
        # This test documents current behavior - stop_loss_percentage can be None
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            stop_loss_percentage=None,  # NO STOP-LOSS!
            take_profit_percentage=Decimal("10"),
        )

        backtester_no_sl = SimpleBacktester(config)

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        quote = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        # This should NOT raise an error (current implementation allows it)
        # But it documents a potential safety issue
        backtester_no_sl._execute_buy_signal(signal, quote)

        # Position should be opened
        assert backtester_no_sl.positions["AAPL"] > 0

        # Now simulate a crash - position should NOT be closed (no SL)
        quote_crash = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("49.5"),
            ask=Decimal("50.5"),
            last=Decimal("50"),
            open=Decimal("60"),
            high=Decimal("60"),
            low=Decimal("50"),
            close=Decimal("50"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester_no_sl._check_exit_conditions(quote_crash)

        # Position should STILL BE OPEN (dangerous!)
        assert (
            backtester_no_sl.positions.get("AAPL", Decimal("0")) > 0
        ), "WARNING: Position remains open without stop-loss - this is dangerous!"

    def test_multiple_positions_with_stop_loss(self, backtester):
        """Test stop-loss with multiple open positions."""
        # Open position in AAPL
        signal_aapl = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        quote_aapl = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._execute_buy_signal(signal_aapl, quote_aapl)

        # Open position in MSFT
        signal_msft = Signal(
            symbol="MSFT",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        quote_msft = Quote(
            symbol="MSFT",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("199"),
            ask=Decimal("201"),
            last=Decimal("200"),
            open=Decimal("200"),
            high=Decimal("201"),
            low=Decimal("199"),
            close=Decimal("200"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._execute_buy_signal(signal_msft, quote_msft)

        # Verify both positions open
        assert backtester.positions["AAPL"] > 0
        assert backtester.positions["MSFT"] > 0

        # Trigger stop-loss on AAPL only
        quote_aapl_decline = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("93.5"),
            ask=Decimal("94.5"),
            last=Decimal("94"),
            open=Decimal("95"),
            high=Decimal("95"),
            low=Decimal("94"),
            close=Decimal("94"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_aapl_decline)

        # Verify AAPL closed, MSFT still open
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal(
            "0"
        ), "AAPL should be closed by stop-loss"
        assert backtester.positions["MSFT"] > 0, "MSFT should remain open"

    def test_stop_loss_with_commission_and_slippage(self, backtester, buy_signal, entry_quote):
        """Test that stop-loss accounts for commission and slippage."""
        # Store initial total capital before any trades
        initial_total_capital = backtester.capital

        # Execute buy
        backtester._execute_buy_signal(buy_signal, entry_quote)

        # Trigger stop-loss
        quote_decline = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("93.5"),
            ask=Decimal("94.5"),
            last=Decimal("94"),
            open=Decimal("95"),
            high=Decimal("95"),
            low=Decimal("94"),
            close=Decimal("94"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_decline)

        final_capital = backtester.capital

        # Capital should decrease (loss + commission + slippage)
        assert (
            final_capital < initial_total_capital
        ), "Capital should decrease after stop-loss (loss + costs)"

        # Verify position closed
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal("0")

        # Verify closed trade includes commission and slippage
        closed_trades = [t for t in backtester.trades if t.status == TradeStatus.CLOSED]
        assert len(closed_trades) > 0

        final_trade = closed_trades[-1]
        assert final_trade.commission > 0, "Trade should have commission"
        assert final_trade.slippage > 0, "Trade should have slippage"


class TestStopLossEdgeCases:
    """Test edge cases and boundary conditions for stop-loss."""

    @pytest.fixture
    def backtester(self):
        """Create backtester with 3% stop-loss and 6% take-profit."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            stop_loss_percentage=Decimal("3"),
            take_profit_percentage=Decimal("6"),
        )
        return SimpleBacktester(config)

    def test_stop_loss_one_tick_below(self, backtester):
        """Test stop-loss triggering one tick below threshold."""
        # Entry at $100, SL at $97 (3%)
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        entry_quote = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._execute_buy_signal(signal, entry_quote)

        # Price drops to $96.99 (one tick below $97)
        quote_below = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("96.49"),
            ask=Decimal("97.49"),
            last=Decimal("96.99"),
            open=Decimal("97"),
            high=Decimal("97"),
            low=Decimal("96.99"),
            close=Decimal("96.99"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_below)

        # Should trigger stop-loss
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal("0")

    def test_stop_loss_one_tick_above(self, backtester):
        """Test stop-loss NOT triggering one tick above threshold."""
        # Entry at $100, SL at $97 (3%)
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        entry_quote = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._execute_buy_signal(signal, entry_quote)

        # Get actual entry price (includes slippage)
        actual_entry_price = backtester.trades[-1].entry_price
        # Calculate actual stop-loss price
        actual_sl_price = actual_entry_price * (Decimal("1") - Decimal("3") / Decimal("100"))

        # Price drops to one tick ABOVE the stop-loss threshold
        # Use the actual stop-loss price to account for slippage
        one_tick_above = actual_sl_price + Decimal("0.01")
        quote_above = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=one_tick_above - Decimal("0.5"),
            ask=one_tick_above + Decimal("0.5"),
            last=one_tick_above,
            open=one_tick_above + Decimal("0.5"),
            high=one_tick_above + Decimal("0.5"),
            low=one_tick_above,  # One tick above SL
            close=one_tick_above,
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_above)

        # Should NOT trigger stop-loss
        assert backtester.positions.get("AAPL", Decimal("0")) > 0

    def test_consecutive_bars_below_stop_loss(self, backtester):
        """Test that stop-loss only triggers once (not on consecutive bars)."""
        # Entry at $100, SL at $97
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        entry_quote = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._execute_buy_signal(signal, entry_quote)

        # First bar below SL
        quote_1 = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("95.5"),
            ask=Decimal("96.5"),
            last=Decimal("96"),
            open=Decimal("96"),
            high=Decimal("96"),
            low=Decimal("96"),
            close=Decimal("96"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_1)

        # Position should be closed
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal("0")

        # Second bar below SL (position already closed)
        quote_2 = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("94.5"),
            ask=Decimal("95.5"),
            last=Decimal("95"),
            open=Decimal("95"),
            high=Decimal("95"),
            low=Decimal("95"),
            close=Decimal("95"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_2)

        # Still closed (no double-triggering)
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal("0")

        # Should only have one closed trade (not two)
        closed_trades = [
            t for t in backtester.trades if t.status == TradeStatus.CLOSED and t.side == "sell"
        ]
        # We expect one summary sell trade for the position close
        assert len(closed_trades) == 1, f"Expected 1 closed sell trade, got {len(closed_trades)}"


class TestStopLossWithDifferentConfigs:
    """Test stop-loss with different configuration values."""

    def test_tight_stop_loss_1_percent(self):
        """Test very tight 1% stop-loss."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            stop_loss_percentage=Decimal("1"),  # Very tight SL
            take_profit_percentage=Decimal("3"),
        )

        backtester = SimpleBacktester(config)

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        entry_quote = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._execute_buy_signal(signal, entry_quote)

        # Price drops 1.5% to $98.50
        quote_decline = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("98"),
            ask=Decimal("99"),
            last=Decimal("98.50"),
            open=Decimal("99"),
            high=Decimal("99"),
            low=Decimal("98.50"),
            close=Decimal("98.50"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_decline)

        # Should trigger tight stop-loss
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal("0")

        closed_trades = [t for t in backtester.trades if t.status == TradeStatus.CLOSED]
        assert len(closed_trades) > 0

        # Loss should be ~1-2% (very tight)
        loss_pct = abs(closed_trades[-1].pnl_percentage)
        assert loss_pct <= Decimal("3"), f"Tight SL should limit loss to ~3%, got {loss_pct}%"

    def test_wide_stop_loss_15_percent(self):
        """Test wide 15% stop-loss."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            stop_loss_percentage=Decimal("15"),  # Wide SL
            take_profit_percentage=Decimal("25"),
        )

        backtester = SimpleBacktester(config)

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
        )

        entry_quote = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._execute_buy_signal(signal, entry_quote)

        # Price drops 10% to $90 (above 15% SL)
        quote_decline_10 = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("89.5"),
            ask=Decimal("90.5"),
            last=Decimal("90"),
            open=Decimal("91"),
            high=Decimal("91"),
            low=Decimal("90"),
            close=Decimal("90"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_decline_10)

        # Should NOT trigger (wide SL allows more drawdown)
        assert (
            backtester.positions.get("AAPL", Decimal("0")) > 0
        ), "Wide 15% SL should not trigger on 10% decline"

        # Price drops 20% to $80 (below 15% SL)
        quote_decline_20 = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("79.5"),
            ask=Decimal("80.5"),
            last=Decimal("80"),
            open=Decimal("81"),
            high=Decimal("81"),
            low=Decimal("80"),
            close=Decimal("80"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        backtester._check_exit_conditions(quote_decline_20)

        # Should trigger now
        assert backtester.positions.get("AAPL", Decimal("0")) == Decimal("0")

        closed_trades = [t for t in backtester.trades if t.status == TradeStatus.CLOSED]
        loss_pct = abs(closed_trades[-1].pnl_percentage)

        # Loss should be ~15-17% (wide SL)
        assert (
            Decimal("13") <= loss_pct <= Decimal("18")
        ), f"Wide SL should allow ~15% loss, got {loss_pct}%"
