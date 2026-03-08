"""
Integration Tests for Pessimistic Execution Engine (Req #10 - CRITICAL)

Tests for realistic order execution including:
- Signal at close t, execution at open t+1 (prevents Look-Ahead Bias)
- Pessimistic Execution: SL before TP in same bar (worst-case)
- Slippage calculation and application
- Commission calculation on execution
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.execution_engine import (
    ExecutionType,
    PessimisticExecutionEngine,
    Position,
    create_position_with_stops,
)
from app.core.decimal_utils import round_price
from app.models.market_data import Quote

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def execution_engine():
    """Default pessimistic execution engine."""
    return PessimisticExecutionEngine(
        execution_type=ExecutionType.PESSIMISTIC,
        base_slippage_bps=Decimal("5"),
    )


@pytest.fixture
def sample_quotes():
    """Generate sample quotes for testing."""
    quotes = []
    base_price = 100.0
    start_date = datetime(2020, 1, 1)

    for i in range(10):
        price = base_price + i  # Slight uptrend

        quotes.append(
            Quote(
                symbol="TEST",
                timestamp=start_date + timedelta(days=i),
                bid=round_price(price * 0.999, "equity", "TEST"),
                ask=round_price(price * 1.001, "equity", "TEST"),
                last=round_price(price, "equity", "TEST"),
                volume=Decimal("1000000"),
                open=round_price(price - 0.5, "equity", "TEST"),
                high=round_price(price + 1.5, "equity", "TEST"),
                low=round_price(price - 1.5, "equity", "TEST"),
                close=round_price(price, "equity", "TEST"),
            )
        )

    return quotes


# ============================================================================
# Tests: Next Day Execution (Req #10 - t -> t+1)
# ============================================================================


class TestNextDayExecution:
    """Tests for next-day execution (Req #10)."""

    def test_execute_entry_order_uses_next_day_open(self, execution_engine):
        """Test that entry order uses next bar's open price (Req #10)."""
        signal_time = datetime(2020, 1, 1, 16, 0)  # Close of day 1
        signal_price = Decimal("100.00")
        next_open = Decimal("100.50")
        next_bar_time = datetime(2020, 1, 2, 9, 30)  # Open of day 2

        result = execution_engine.execute_entry_order(
            symbol="TEST",
            side="buy",
            quantity=Decimal("100"),
            signal_time=signal_time,
            signal_price=signal_price,
            next_open_price=next_open,
            next_bar_time=next_bar_time,
        )

        # Execution should be at next day's open (with slippage)
        assert result.execution_time == next_bar_time
        assert result.signal_time == signal_time
        # Price should be next_open + slippage
        assert result.execution_price > next_open

    def test_execution_prevents_look_ahead_bias(self, execution_engine):
        """Test that execution prevents Look-Ahead Bias (Req #10)."""
        # Signal based on close price
        signal_close = Decimal("100.00")

        # Next bar opens higher (would miss if using signal price)
        next_open = Decimal("102.00")

        result = execution_engine.execute_entry_order(
            symbol="TEST",
            side="buy",
            quantity=Decimal("100"),
            signal_time=datetime(2020, 1, 1),
            signal_price=signal_close,
            next_open_price=next_open,
            next_bar_time=datetime(2020, 1, 2),
        )

        # Should NOT execute at signal price (prevents look-ahead)
        assert result.execution_price != signal_close
        # Should execute at next open (with slippage)
        assert result.execution_price >= next_open

    def test_sell_order_slippage_direction(self, execution_engine):
        """Test that sell orders have downward slippage."""
        next_open = Decimal("100.00")

        result = execution_engine.execute_entry_order(
            symbol="TEST",
            side="sell",
            quantity=Decimal("100"),
            signal_time=datetime(2020, 1, 1),
            signal_price=Decimal("100.00"),
            next_open_price=next_open,
            next_bar_time=datetime(2020, 1, 2),
        )

        # Sell: receive less (slippage downward)
        assert result.execution_price < next_open


# ============================================================================
# Tests: Pessimistic Execution (Req #10 - SL before TP)
# ============================================================================


class TestPessimisticExecution:
    """Tests for pessimistic execution (Req #10 - SL before TP)."""

    def test_sl_before_tp_both_hit_long(self, execution_engine):
        """Test pessimistic execution: SL executes before TP for long (Req #10)."""
        # Long position entry at 100
        position = create_position_with_stops(
            symbol="TEST",
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),  # SL at 95
            take_profit_pct=Decimal("0.10"),  # TP at 110
        )

        # Bar that hits both: low 94 (below SL), high 112 (above TP)
        result, remaining = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("98"),
            bar_high=Decimal("112"),  # Above TP
            bar_low=Decimal("94"),  # Below SL
            bar_close=Decimal("105"),
            bar_time=datetime(2020, 1, 2),
        )

        assert result is not None
        assert result.stop_loss_hit is True
        assert result.take_profit_hit is True  # Both were hit
        # Pessimistic: SL executed (not TP)
        assert float(result.stop_execution_price) <= 95  # Around SL price

    def test_sl_before_tp_both_hit_short(self, execution_engine):
        """Test pessimistic execution: SL executes before TP for short (Req #10)."""
        # Short position entry at 100
        position = create_position_with_stops(
            symbol="TEST",
            side="short",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),  # SL at 105
            take_profit_pct=Decimal("0.10"),  # TP at 90
        )

        # Bar that hits both: high 106 (above SL), low 89 (below TP)
        result, remaining = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("102"),
            bar_high=Decimal("106"),  # Above SL
            bar_low=Decimal("89"),  # Below TP
            bar_close=Decimal("95"),
            bar_time=datetime(2020, 1, 2),
        )

        assert result is not None
        assert result.stop_loss_hit is True
        assert result.take_profit_hit is True  # Both were hit
        # Pessimistic: SL executed (not TP)
        assert float(result.stop_execution_price) >= 105  # Around SL price

    def test_only_sl_hit_long(self, execution_engine):
        """Test when only SL is hit (long position)."""
        position = create_position_with_stops(
            symbol="TEST",
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),  # SL at 95
            take_profit_pct=Decimal("0.10"),  # TP at 110
        )

        # Bar hits SL but not TP
        result, remaining = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("98"),
            bar_high=Decimal("105"),  # Below TP
            bar_low=Decimal("94"),  # Below SL
            bar_close=Decimal("96"),
            bar_time=datetime(2020, 1, 2),
        )

        assert result is not None
        assert result.stop_loss_hit is True
        assert result.take_profit_hit is False

    def test_only_tp_hit_long(self, execution_engine):
        """Test when only TP is hit (long position)."""
        position = create_position_with_stops(
            symbol="TEST",
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),  # SL at 95
            take_profit_pct=Decimal("0.10"),  # TP at 110
        )

        # Bar hits TP but not SL
        result, remaining = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("105"),
            bar_high=Decimal("112"),  # Above TP
            bar_low=Decimal("97"),  # Above SL
            bar_close=Decimal("110"),
            bar_time=datetime(2020, 1, 2),
        )

        assert result is not None
        assert result.stop_loss_hit is False
        assert result.take_profit_hit is True

    def test_no_stops_hit(self, execution_engine):
        """Test when no stops are hit."""
        position = create_position_with_stops(
            symbol="TEST",
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),  # SL at 95
            take_profit_pct=Decimal("0.10"),  # TP at 110
        )

        # Bar doesn't hit either stop
        result, remaining = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("102"),
            bar_high=Decimal("108"),
            bar_low=Decimal("98"),
            bar_close=Decimal("105"),
            bar_time=datetime(2020, 1, 2),
        )

        assert result is None  # No execution
        assert remaining is position  # Position unchanged


# ============================================================================
# Tests: Slippage Calculation
# ============================================================================


class TestSlippageCalculation:
    """Tests for slippage calculation."""

    def test_base_slippage_applied(self, execution_engine):
        """Test that base slippage is applied."""
        result = execution_engine.execute_entry_order(
            symbol="TEST",
            side="buy",
            quantity=Decimal("100"),
            signal_time=datetime(2020, 1, 1),
            signal_price=Decimal("100"),
            next_open_price=Decimal("100"),
            next_bar_time=datetime(2020, 1, 2),
        )

        # 5 bps = 0.05% on buy (pay more)
        expected_slippage = Decimal("100") * Decimal("5") / Decimal("10000")
        assert result.slippage_bps == Decimal("5")
        assert abs(float(result.execution_price) - float(Decimal("100") + expected_slippage)) < 0.01

    def test_volatility_adjusted_slippage(self):
        """Test that volatility increases slippage."""
        engine = PessimisticExecutionEngine(base_slippage_bps=Decimal("5"))

        # Low volatility
        result_low = engine.execute_entry_order(
            symbol="TEST",
            side="buy",
            quantity=Decimal("100"),
            signal_time=datetime(2020, 1, 1),
            signal_price=Decimal("100"),
            next_open_price=Decimal("100"),
            next_bar_time=datetime(2020, 1, 2),
            volatility=Decimal("0.1"),  # 10% vol
        )

        # High volatility
        result_high = engine.execute_entry_order(
            symbol="TEST",
            side="buy",
            quantity=Decimal("100"),
            signal_time=datetime(2020, 1, 1),
            signal_price=Decimal("100"),
            next_open_price=Decimal("100"),
            next_bar_time=datetime(2020, 1, 2),
            volatility=Decimal("0.5"),  # 50% vol
        )

        # Higher volatility should have higher slippage
        assert result_high.slippage_bps > result_low.slippage_bps

    def test_double_slippage_on_stops(self, execution_engine):
        """Test that stops have double slippage (more expensive)."""
        position = create_position_with_stops(
            symbol="TEST",
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),
        )

        result, _ = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("98"),
            bar_high=Decimal("102"),
            bar_low=Decimal("94"),  # Hit SL
            bar_close=Decimal("95"),
            bar_time=datetime(2020, 1, 2),
        )

        # Stop execution should have higher slippage (double base)
        assert result.slippage_bps > execution_engine.base_slippage_bps


# ============================================================================
# Tests: Position Creation
# ============================================================================


class TestPositionCreation:
    """Tests for position creation with stops."""

    def test_create_long_position_with_stops(self, default_symbol):
        """Test creating long position with stops."""
        position = create_position_with_stops(
            symbol=default_symbol,
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),  # 5% SL
            take_profit_pct=Decimal("0.10"),  # 10% TP
        )

        assert position.side == "long"
        assert position.stop_loss_price == Decimal("95.00")  # 100 * (1 - 0.05)
        assert position.take_profit_price == Decimal("110.00")  # 100 * (1 + 0.10)

    def test_create_short_position_with_stops(self, default_symbol):
        """Test creating short position with stops."""
        position = create_position_with_stops(
            symbol=default_symbol,
            side="short",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),  # 5% SL
            take_profit_pct=Decimal("0.10"),  # 10% TP
        )

        assert position.side == "short"
        assert position.stop_loss_price == Decimal("105.00")  # 100 * (1 + 0.05)
        assert position.take_profit_price == Decimal("90.00")  # 100 * (1 - 0.10)

    def test_position_without_stops(self, default_symbol):
        """Test creating position without stops."""
        position = create_position_with_stops(
            symbol=default_symbol,
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
        )

        assert position.stop_loss_price is None
        assert position.take_profit_price is None


# ============================================================================
# Tests: Commission Calculation
# ============================================================================


class TestCommissionCalculation:
    """Tests for commission calculation on execution."""

    def test_commission_calculated_on_execution(self, execution_engine, default_symbol):
        """Test that commission is calculated on execution."""
        result = execution_engine.execute_entry_order(
            symbol=default_symbol,
            side="buy",
            quantity=Decimal("100"),
            signal_time=datetime(2020, 1, 1),
            signal_price=Decimal("100"),
            next_open_price=Decimal("100"),
            next_bar_time=datetime(2020, 1, 2),
        )

        # Commission should be calculated
        assert result.commission > 0

    def test_commission_on_stop_execution(self, execution_engine):
        """Test that commission is calculated on stop execution."""
        position = create_position_with_stops(
            symbol="TEST",
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
            stop_loss_pct=Decimal("0.05"),
        )

        result, _ = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("98"),
            bar_high=Decimal("102"),
            bar_low=Decimal("94"),
            bar_close=Decimal("95"),
            bar_time=datetime(2020, 1, 2),
        )

        # Commission should be calculated
        assert result.commission > 0


# ============================================================================
# Tests: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_quantity_order(self, execution_engine):
        """Test handling of zero quantity order."""
        result = execution_engine.execute_entry_order(
            symbol="TEST",
            side="buy",
            quantity=Decimal("0"),
            signal_time=datetime(2020, 1, 1),
            signal_price=Decimal("100"),
            next_open_price=Decimal("100"),
            next_bar_time=datetime(2020, 1, 2),
        )

        # Should still execute, commission will be minimal
        assert result.executed is True

    def test_position_without_stops_unchanged(self, execution_engine):
        """Test that position without stops remains unchanged."""
        position = Position(
            symbol="TEST",
            side="long",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            entry_time=datetime(2020, 1, 1),
        )

        result, remaining = execution_engine.process_intra_bar_execution(
            position=position,
            bar_open=Decimal("102"),
            bar_high=Decimal("105"),
            bar_low=Decimal("98"),
            bar_close=Decimal("103"),
            bar_time=datetime(2020, 1, 2),
        )

        assert result is None
        assert remaining is position


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
