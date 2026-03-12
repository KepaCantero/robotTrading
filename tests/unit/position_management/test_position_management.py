"""
Unit Tests for Position Management

Tests for TrailingStopManager, PartialTakeProfit, and PyramidingManager.
"""

import pytest
from decimal import Decimal

from app.services.position_management import (
    TrailingStopManager,
    PartialTakeProfit,
    PyramidingManager,
)


class TestTrailingStopManager:
    """Tests for TrailingStopManager (R11)."""

    def test_init(self):
        """Test initialization."""
        manager = TrailingStopManager(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )
        assert manager.entry_price == Decimal("100")
        assert manager.initial_stop == Decimal("95")
        assert manager.highest_price == Decimal("100")
        assert manager.current_stop == Decimal("95")

    def test_break_even_at_2r(self):
        """Test trailing stop moves to break-even at 2R."""
        manager = TrailingStopManager(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Subir a 110 (+10, que es 2R ya que el riesgo es 5 por share)
        # Para calcular R-multiple: unrealized_pnl / initial_risk_per_share
        # initial_risk = 100 - 95 = 5
        # Para 2R, necesitamos unrealized_pnl = 2 * 5 = 10
        result = manager.update(
            current_price=Decimal("110"),
            unrealized_pnl=Decimal("10"),  # P&L per share equivalent
        )

        assert result.new_stop == Decimal("100")  # Break-even
        assert result.action == "break_even"
        assert result.r_multiple >= 2.0

    def test_trailing_50pct_at_3r(self):
        """Test trailing stop at 50% of profit at 3R."""
        manager = TrailingStopManager(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Subir a 115 (+15, que es 3R)
        # Para 3R, necesitamos unrealized_pnl = 3 * 5 = 15
        result = manager.update(
            current_price=Decimal("115"),
            unrealized_pnl=Decimal("15"),  # P&L per share equivalent
        )

        # 50% del beneficio: 115 - (15 * 0.5) = 107.5
        assert result.new_stop == Decimal("107.5")
        assert result.action == "trailing_50pct"

    def test_trailing_1_5pct_at_1r(self):
        """Test trailing stop at 1.5% from high at 1R."""
        manager = TrailingStopManager(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Subir a 105 (+5, que es 1R)
        # Para 1R, necesitamos unrealized_pnl = 1 * 5 = 5
        result = manager.update(
            current_price=Decimal("105"),
            unrealized_pnl=Decimal("5"),  # P&L per share equivalent
        )

        # 1.5% desde el máximo: 105 * (1 - 0.015) = 103.425
        assert result.action == "trailing_1.5pct"
        assert result.new_stop == Decimal("103.425")

    def test_no_update_when_price_drops(self):
        """Test that trailing stop doesn't move down when price drops below break-even."""
        manager = TrailingStopManager(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Subir a 110 (break-even)
        result1 = manager.update(
            current_price=Decimal("110"),
            unrealized_pnl=Decimal("10"),
        )
        assert result1.new_stop == Decimal("100")

        # Bajar a 98 (por debajo del break-even)
        result2 = manager.update(
            current_price=Decimal("98"),
            unrealized_pnl=Decimal("-2"),  # Pequeña pérdida
        )
        # El stop NO debería bajar (se queda en 100)
        assert result2.new_stop is None
        assert manager.current_stop == Decimal("100")


class TestPartialTakeProfit:
    """Tests for PartialTakeProfit (R12)."""

    def test_init(self):
        """Test initialization."""
        manager = PartialTakeProfit(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )
        assert manager.entry_price == Decimal("100")
        assert manager.initial_stop == Decimal("95")
        assert len(manager.targets) == 3
        assert len(manager.executed_targets) == 0

    def test_first_target_2r(self):
        """Test first target at 2R (close 50%)."""
        manager = PartialTakeProfit(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Precio 110 = 2R
        action = manager.check_targets(
            current_price=Decimal("110"),
            position_size=Decimal("100"),
        )

        assert action is not None
        assert action.size_to_close == Decimal("50")  # 50% de 100
        assert action.action == "move_to_breakeven"
        assert action.r_multiple == 2.0

    def test_second_target_3r(self):
        """Test second target at 3R (close 25%)."""
        manager = PartialTakeProfit(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Ejecutar primer target
        manager.check_targets(Decimal("110"), Decimal("100"))

        # Precio 115 = 3R (pero ahora solo quedan 50 shares)
        action = manager.check_targets(
            current_price=Decimal("115"),
            position_size=Decimal("50"),  # Después de cerrar 50%
        )

        assert action is not None
        assert action.size_to_close == Decimal("12.5")  # 25% de 50
        assert action.action == "trailing_stop"
        assert action.r_multiple == 3.0

    def test_third_target_5r(self):
        """Test third target at 5R (close 25%)."""
        manager = PartialTakeProfit(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Ejecutar targets anteriores
        manager.check_targets(Decimal("110"), Decimal("100"))
        manager.check_targets(Decimal("115"), Decimal("50"))

        # Precio 125 = 5R (quedan 37.5 shares)
        action = manager.check_targets(
            current_price=Decimal("125"),
            position_size=Decimal("37.5"),
        )

        assert action is not None
        assert action.size_to_close == Decimal("9.375")  # 25% de 37.5
        assert action.action == "none"
        assert action.r_multiple == 5.0

    def test_targets_not_repeated(self):
        """Test that targets are not executed multiple times."""
        manager = PartialTakeProfit(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        # Ejecutar primer target
        action1 = manager.check_targets(Decimal("110"), Decimal("100"))
        assert action1 is not None

        # Intentar ejecutar de nuevo al mismo nivel
        action2 = manager.check_targets(Decimal("110"), Decimal("100"))
        assert action2 is None  # No debería ejecutar de nuevo

    def test_is_complete(self):
        """Test is_complete method."""
        manager = PartialTakeProfit(
            entry_price=Decimal("100"),
            initial_stop=Decimal("95"),
        )

        assert not manager.is_complete()

        # Ejecutar todos los targets
        manager.check_targets(Decimal("110"), Decimal("100"))
        assert not manager.is_complete()

        manager.check_targets(Decimal("115"), Decimal("50"))
        assert not manager.is_complete()

        manager.check_targets(Decimal("125"), Decimal("37.5"))
        assert manager.is_complete()


class TestPyramidingManager:
    """Tests for PyramidingManager (R13)."""

    def test_init(self):
        """Test initialization."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
        )
        assert manager.initial_size == Decimal("100")
        assert manager.max_additions == 2
        assert manager.current_additions == 0

    def test_cannot_add_when_loss(self):
        """Test that pyramiding is not allowed when position is in loss."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
        )

        result = manager.can_add_position(current_pnl=Decimal("-50"))

        assert not result.can_add
        assert "not profitable" in result.reason.lower()

    def test_cannot_add_when_zero_pnl(self):
        """Test that pyramiding is not allowed when P&L is zero."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
        )

        result = manager.can_add_position(current_pnl=Decimal("0"))

        assert not result.can_add
        assert "not profitable" in result.reason.lower()

    def test_can_add_when_profit(self):
        """Test that pyramiding is allowed when position is profitable."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
        )

        result = manager.can_add_position(current_pnl=Decimal("50"))

        assert result.can_add
        assert result.size_to_add == Decimal("50")  # 50% de 100
        assert result.additions_remaining == 1

    def test_first_addition_size(self):
        """Test that first addition is 50% of initial size."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
        )

        size = manager.get_addition_size()
        assert size == Decimal("50")  # 50%

    def test_second_addition_size(self):
        """Test that second addition is 25% of initial size."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
        )

        # Primera adición
        manager.add_position(Decimal("110"), Decimal("50"))

        # Segunda adición
        size = manager.get_addition_size()
        assert size == Decimal("25")  # 25%

    def test_max_additions_limit(self):
        """Test that pyramiding stops after max additions."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
            max_additions=2,
        )

        # Primera adición
        result1 = manager.add_position(Decimal("110"), Decimal("50"))
        assert result1.can_add

        # Segunda adición
        result2 = manager.add_position(Decimal("115"), Decimal("75"))
        assert result2.can_add

        # Tercera adición (no permitida)
        result3 = manager.can_add_position(current_pnl=Decimal("100"))
        assert not result3.can_add
        assert "maximum" in result3.reason.lower()

    def test_get_total_added(self):
        """Test get_total_added method."""
        manager = PyramidingManager(
            initial_size=Decimal("100"),
        )

        assert manager.get_total_added() == Decimal("0")

        manager.add_position(Decimal("110"), Decimal("50"))
        assert manager.get_total_added() == Decimal("50")

        manager.add_position(Decimal("115"), Decimal("75"))
        assert manager.get_total_added() == Decimal("75")  # 50 + 25


class TestIntegration:
    """Integration tests for position management components."""

    def test_position_workflow(self):
        """Test complete workflow of position management."""
        # Setup
        entry_price = Decimal("100")
        initial_stop = Decimal("95")
        position_size = Decimal("100")

        trailing_manager = TrailingStopManager(entry_price, initial_stop)
        partial_tp = PartialTakeProfit(entry_price, initial_stop)
        pyramiding = PyramidingManager(position_size)

        # Escenario 1: Precio sube a 110 (2R)
        current_price = Decimal("110")
        # El R-multiple se basa en el riesgo por share
        initial_risk_per_share = entry_price - initial_stop  # 5
        unrealized_pnl_per_share = current_price - entry_price  # 10

        # Trailing stop debería moverse a break-even
        ts_result = trailing_manager.update(current_price, unrealized_pnl_per_share)
        assert ts_result.new_stop == entry_price

        # Take profit parcial debería activarse
        tp_action = partial_tp.check_targets(current_price, position_size)
        assert tp_action is not None
        assert tp_action.size_to_close == Decimal("50")

        # Pyramiding debería estar disponible
        total_pnl = unrealized_pnl_per_share * position_size
        pyr_result = pyramiding.can_add_position(total_pnl)
        assert pyr_result.can_add

        # Escenario 2: Precio sube a 115 (3R)
        current_price = Decimal("115")
        unrealized_pnl_per_share = current_price - entry_price  # 15

        ts_result = trailing_manager.update(current_price, unrealized_pnl_per_share)
        assert ts_result.action == "trailing_50pct"

        # Escenario 3: Precio baja a 105 (debajo del trailing stop)
        current_price = Decimal("105")
        unrealized_pnl_per_share = current_price - entry_price  # 5
        ts_result = trailing_manager.update(current_price, unrealized_pnl_per_share)
        # El stop no debería bajar
        assert ts_result.new_stop is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
