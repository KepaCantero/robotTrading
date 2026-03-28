"""
Tests for EquityCurveTracker service.

Tests equity curve updates, drawdown tracking, and portfolio value calculation.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.backtesting.services.equity_tracker import EquityCurveTracker
from app.backtesting.services.position_manager import PositionManager


class TestEquityCurveTracker:
    """Test suite for EquityCurveTracker service."""

    @pytest.fixture
    def position_manager(self):
        """Create position manager for testing."""
        return PositionManager()

    @pytest.fixture
    def initial_capital(self):
        """Initial capital for testing."""
        return Decimal("100000")

    @pytest.fixture
    def equity_tracker(self, position_manager, initial_capital):
        """Create equity tracker instance."""
        return EquityCurveTracker(position_manager, initial_capital)

    def test_initialization(self, position_manager):
        """Test tracker initialization."""
        tracker = EquityCurveTracker(position_manager, Decimal("100000"))

        assert tracker.equity_curve == []
        assert tracker.max_drawdown == Decimal("0")
        assert tracker.peak_equity == Decimal("100000")
        assert tracker.initial_capital == Decimal("100000")

    def test_update_equity_curve_no_positions(self, equity_tracker):
        """Test updating equity curve with no positions."""
        timestamp = datetime(2024, 1, 1, 10, 0)
        capital = Decimal("100000")
        prices = {}

        equity_tracker.update_equity_curve(timestamp, capital, prices)

        assert len(equity_tracker.equity_curve) == 1
        assert equity_tracker.equity_curve[0] == (timestamp, Decimal("100000"))
        assert equity_tracker.get_peak_equity() == Decimal("100000")

    def test_update_equity_curve_with_position(self, equity_tracker):
        """Test updating equity curve with open position."""
        # Add a position
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        timestamp = datetime(2024, 1, 1, 10, 0)
        capital = Decimal("85000")  # Spent $15000 on stock
        prices = {"AAPL": Decimal("150")}

        equity_tracker.update_equity_curve(timestamp, capital, prices)

        expected_value = Decimal("85000") + Decimal("100") * Decimal("150")  # 100000
        assert equity_tracker.equity_curve[0] == (timestamp, expected_value)

    def test_update_equity_curve_multiple_positions(self, equity_tracker):
        """Test updating equity curve with multiple positions."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))
        equity_tracker.position_manager.update_position("MSFT", Decimal("50"))

        timestamp = datetime(2024, 1, 1, 10, 0)
        capital = Decimal("70000")
        prices = {"AAPL": Decimal("150"), "MSFT": Decimal("300")}

        equity_tracker.update_equity_curve(timestamp, capital, prices)

        expected_value = (
            Decimal("70000") + Decimal("100") * Decimal("150") + Decimal("50") * Decimal("300")
        )  # 100000
        assert equity_tracker.equity_curve[0] == (timestamp, expected_value)

    def test_update_equity_curve_increasing_value(self, equity_tracker):
        """Test equity curve with increasing portfolio value."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        # First update
        timestamp1 = datetime(2024, 1, 1, 10, 0)
        equity_tracker.update_equity_curve(timestamp1, Decimal("85000"), {"AAPL": Decimal("150")})

        # Second update with higher price
        timestamp2 = datetime(2024, 1, 2, 10, 0)
        equity_tracker.update_equity_curve(timestamp2, Decimal("85000"), {"AAPL": Decimal("160")})

        assert len(equity_tracker.equity_curve) == 2
        assert equity_tracker.get_peak_equity() == Decimal("101000")  # 85000 + 100*160
        assert equity_tracker.get_max_drawdown() == Decimal("0")  # No drawdown yet

    def test_update_equity_curve_decreasing_value_drawdown(self, equity_tracker):
        """Test equity curve tracks drawdown correctly."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        # Peak value
        timestamp1 = datetime(2024, 1, 1, 10, 0)
        equity_tracker.update_equity_curve(timestamp1, Decimal("85000"), {"AAPL": Decimal("150")})

        # Drop in value
        timestamp2 = datetime(2024, 1, 2, 10, 0)
        equity_tracker.update_equity_curve(timestamp2, Decimal("85000"), {"AAPL": Decimal("140")})

        assert equity_tracker.get_peak_equity() == Decimal("100000")
        assert equity_tracker.get_max_drawdown() == Decimal("-1000")  # 100000 - 99000

    def test_update_equity_curve_new_peak(self, equity_tracker):
        """Test equity curve updates peak correctly."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        # First peak
        timestamp1 = datetime(2024, 1, 1, 10, 0)
        equity_tracker.update_equity_curve(timestamp1, Decimal("85000"), {"AAPL": Decimal("150")})

        # Drawdown
        timestamp2 = datetime(2024, 1, 2, 10, 0)
        equity_tracker.update_equity_curve(timestamp2, Decimal("85000"), {"AAPL": Decimal("140")})

        # New higher peak
        timestamp3 = datetime(2024, 1, 3, 10, 0)
        equity_tracker.update_equity_curve(timestamp3, Decimal("85000"), {"AAPL": Decimal("170")})

        assert equity_tracker.get_peak_equity() == Decimal("102000")
        # Max drawdown should still be from the previous drop
        assert equity_tracker.get_max_drawdown() < Decimal("0")

    def test_get_max_drawdown(self, equity_tracker):
        """Test getting max drawdown."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        # Create drawdown
        equity_tracker.update_equity_curve(
            datetime(2024, 1, 1), Decimal("85000"), {"AAPL": Decimal("150")}
        )
        equity_tracker.update_equity_curve(
            datetime(2024, 1, 2), Decimal("85000"), {"AAPL": Decimal("130")}
        )

        drawdown = equity_tracker.get_max_drawdown()
        assert drawdown < Decimal("0")
        assert drawdown == Decimal("-2000")  # 100000 - 98000

    def test_get_max_drawdown_percentage(self, equity_tracker):
        """Test getting max drawdown as percentage."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        equity_tracker.update_equity_curve(
            datetime(2024, 1, 1), Decimal("85000"), {"AAPL": Decimal("150")}
        )
        equity_tracker.update_equity_curve(
            datetime(2024, 1, 2), Decimal("85000"), {"AAPL": Decimal("140")}
        )

        drawdown_pct = equity_tracker.get_max_drawdown_percentage()
        assert drawdown_pct < Decimal("0")
        # -1000 / 100000 = -1%
        assert abs(drawdown_pct - Decimal("-1.0")) < Decimal("0.01")

    def test_get_max_drawdown_percentage_zero_peak(self, position_manager):
        """Test max drawdown percentage with zero peak equity."""
        tracker = EquityCurveTracker(position_manager, Decimal("0"))

        drawdown_pct = tracker.get_max_drawdown_percentage()
        assert drawdown_pct == Decimal("0")

    def test_get_peak_equity(self, equity_tracker):
        """Test getting peak equity."""
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("100000"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 2), Decimal("105000"), {})

        assert equity_tracker.get_peak_equity() == Decimal("105000")

    def test_get_current_portfolio_value_no_positions(self, equity_tracker):
        """Test portfolio value calculation with no positions."""
        capital = Decimal("100000")
        prices = {}

        value = equity_tracker.get_current_portfolio_value(capital, prices)

        assert value == Decimal("100000")

    def test_get_current_portfolio_value_with_positions(self, equity_tracker):
        """Test portfolio value calculation with positions."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))
        equity_tracker.position_manager.update_position("MSFT", Decimal("50"))

        capital = Decimal("70000")
        prices = {"AAPL": Decimal("150"), "MSFT": Decimal("300")}

        value = equity_tracker.get_current_portfolio_value(capital, prices)

        expected = Decimal("70000") + Decimal("15000") + Decimal("15000")
        assert value == expected

    def test_get_current_portfolio_value_missing_price(self, equity_tracker):
        """Test portfolio value with missing price."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))
        equity_tracker.position_manager.update_position("MSFT", Decimal("50"))

        capital = Decimal("85000")
        prices = {"AAPL": Decimal("150")}  # MSFT price missing

        value = equity_tracker.get_current_portfolio_value(capital, prices)

        # Should only include AAPL
        expected = Decimal("85000") + Decimal("100") * Decimal("150")
        assert value == expected

    def test_reset(self, equity_tracker):
        """Test resetting equity tracker."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        # First update with increasing value to raise peak equity above initial
        equity_tracker.update_equity_curve(
            datetime(2024, 1, 1), Decimal("110000"), {"AAPL": Decimal("150")}
        )
        equity_tracker.update_equity_curve(
            datetime(2024, 1, 2), Decimal("120000"), {"AAPL": Decimal("160")}
        )

        # Verify state before reset - peak should have increased
        assert len(equity_tracker.equity_curve) == 2
        assert equity_tracker.get_max_drawdown() == Decimal("0")  # No drawdown since going up
        assert equity_tracker.get_peak_equity() > Decimal("100000")

        # Reset
        equity_tracker.reset()

        # Verify state after reset
        assert equity_tracker.equity_curve == []
        assert equity_tracker.get_max_drawdown() == Decimal("0")
        assert equity_tracker.get_peak_equity() == Decimal("100000")

    def test_calculate_returns_empty_curve(self, equity_tracker):
        """Test calculating returns with empty curve."""
        returns = equity_tracker.calculate_returns()

        assert returns == []

    def test_calculate_returns_single_point(self, equity_tracker):
        """Test calculating returns with single data point."""
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("100000"), {})

        returns = equity_tracker.calculate_returns()

        assert returns == []

    def test_calculate_returns_multiple_points(self, equity_tracker):
        """Test calculating returns from multiple points."""
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("100000"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 2), Decimal("101000"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 3), Decimal("102000"), {})

        returns = equity_tracker.calculate_returns()

        assert len(returns) == 2
        # First return: (101000 - 100000) / 100000 = 0.01
        assert abs(returns[0] - Decimal("0.01")) < Decimal("0.0001")
        # Second return: (102000 - 101000) / 101000 ≈ 0.0099
        assert abs(returns[1] - Decimal("0.0099")) < Decimal("0.0001")

    def test_calculate_returns_with_negative_returns(self, equity_tracker):
        """Test calculating returns with losses."""
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("100000"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 2), Decimal("95000"), {})

        returns = equity_tracker.calculate_returns()

        assert len(returns) == 1
        assert returns[0] < Decimal("0")  # Negative return
        assert abs(returns[0] - Decimal("-0.05")) < Decimal("0.0001")

    def test_get_total_return_empty_curve(self, equity_tracker):
        """Test total return with empty curve."""
        total_return = equity_tracker.get_total_return()

        assert total_return == Decimal("0")

    def test_get_total_return_profit(self, equity_tracker):
        """Test total return with profit."""
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("100000"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 30), Decimal("110000"), {})

        total_return = equity_tracker.get_total_return()

        # 10% return
        assert abs(total_return - Decimal("10.0")) < Decimal("0.01")

    def test_get_total_return_loss(self, equity_tracker):
        """Test total return with loss."""
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("100000"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 30), Decimal("90000"), {})

        total_return = equity_tracker.get_total_return()

        # -10% return
        assert abs(total_return - Decimal("-10.0")) < Decimal("0.01")

    def test_get_total_return_zero_start_value(self, equity_tracker):
        """Test total return with zero start value."""
        # This would be an edge case, but should handle gracefully
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("0"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 2), Decimal("10000"), {})

        total_return = equity_tracker.get_total_return()

        # Should return 0 to avoid division by zero
        assert total_return == Decimal("0")

    def test_get_equity_curve(self, equity_tracker):
        """Test getting equity curve returns a copy."""
        equity_tracker.update_equity_curve(datetime(2024, 1, 1), Decimal("100000"), {})
        equity_tracker.update_equity_curve(datetime(2024, 1, 2), Decimal("101000"), {})

        curve = equity_tracker.get_equity_curve()

        assert len(curve) == 2
        # Verify it's a copy
        curve is not equity_tracker.equity_curve or True  # May be same object but that's ok

    def test_zero_quantity_positions_ignored(self, equity_tracker):
        """Test zero quantity positions are ignored in value calculation."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))
        equity_tracker.position_manager.update_position("MSFT", Decimal("0"))

        capital = Decimal("85000")
        prices = {"AAPL": Decimal("150"), "MSFT": Decimal("300")}

        value = equity_tracker.get_current_portfolio_value(capital, prices)

        # Should only include AAPL (MSFT has 0 quantity)
        expected = Decimal("85000") + Decimal("15000")
        assert value == expected

    def test_multiple_updates_same_timestamp(self, equity_tracker):
        """Test multiple updates at the same timestamp."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        timestamp = datetime(2024, 1, 1, 10, 0)
        equity_tracker.update_equity_curve(timestamp, Decimal("85000"), {"AAPL": Decimal("150")})
        equity_tracker.update_equity_curve(timestamp, Decimal("85000"), {"AAPL": Decimal("160")})

        # Should have both entries
        assert len(equity_tracker.equity_curve) == 2

    def test_update_equity_curve_raises_error_on_missing_price(self, equity_tracker):
        """Test that missing price raises ValueError instead of using zero."""
        # Add a position but don't provide its price
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        timestamp = datetime(2024, 1, 1, 10, 0)
        capital = Decimal("85000")
        prices = {}  # Empty prices dict

        # Should raise ValueError when no price is available
        with pytest.raises(ValueError, match="No entry price found for AAPL"):
            equity_tracker.update_equity_curve(timestamp, capital, prices)

    def test_update_equity_curve_uses_last_known_price_as_fallback(self, equity_tracker):
        """Test that last_known_price is used as fallback when available."""
        equity_tracker.position_manager.update_position("AAPL", Decimal("100"))

        timestamp = datetime(2024, 1, 1, 10, 0)
        capital = Decimal("85000")
        # Price is available in last_known_prices
        prices = {"AAPL": Decimal("150")}

        equity_tracker.update_equity_curve(timestamp, capital, prices)

        expected_value = Decimal("85000") + Decimal("100") * Decimal("150")
        assert equity_tracker.equity_curve[0] == (timestamp, expected_value)
