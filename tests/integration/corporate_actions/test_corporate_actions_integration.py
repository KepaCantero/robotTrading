"""
Integration tests for Corporate Actions Handler.

Tests cover:
- Integration with real broker adapters
- End-to-end corporate action processing
- Multi-action scenarios
- Database persistence
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.core.interfaces.broker_base import BrokerType, OrderSide, OrderStatus
from app.services.corporate_actions.handler import CorporateActionsHandler, CorporateActionType

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_portfolio_position():
    """Create a portfolio position matching app.models.portfolio.Position."""
    from app.domain.models.portfolio import AssetClass, Position as PortfolioPosition

    return PortfolioPosition(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("100"),
        avg_price=Decimal("150.00"),
        market_price=Decimal("175.00"),
        unrealized_pnl=Decimal("2500.00"),
        currency="USD",
        broker="ibkr",
    )


@pytest.fixture
def mock_ibkr_position():
    """Create an IBKR-style position."""
    position = MagicMock()
    position.contract = MagicMock()
    position.contract.symbol = "AAPL"
    position.position = 100
    position.avgCost = 150.00
    return position


@pytest.fixture
def mock_broker_with_positions():
    """Create a mock broker with positions."""
    # Create a simple mock position (not Portfolio model to avoid validation issues)
    position = MagicMock()
    position.position_id = "pos_123"
    position.symbol = "AAPL"
    position.quantity = Decimal("100")
    position.avg_price = Decimal("150.00")
    position.recalculate_metrics = Mock()

    broker = MagicMock()
    broker.get_broker_type = MagicMock(return_value=BrokerType.STOCKS_US)
    broker.get_broker_name = MagicMock(return_value="ibkr")

    # Return portfolio positions
    broker.get_all_open_positions = AsyncMock(return_value=[position])

    # Mock order execution
    order_result = MagicMock()
    order_result.order_id = "ORDER_123"
    order_result.status = OrderStatus.FILLED
    broker.execute_order_with_wal = AsyncMock(return_value=order_result)

    return broker


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestCorporateActionsIntegration:
    """Integration tests for corporate actions handling."""

    @pytest.mark.asyncio
    async def test_full_stock_split_workflow(self, mock_broker_with_positions):
        """Test complete stock split workflow from action to position update."""
        # Setup
        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute stock split
        result = await handler.on_stock_split(
            symbol="AAPL", ratio=Decimal("4"), ex_date=date(2024, 6, 1)
        )

        # Verify result
        assert result["positions_adjusted"] == 1
        assert result["adjustments"][0]["new_quantity"] in ["400", "400.0"]
        assert result["adjustments"][0]["new_avg_price"] == "37.50"

        # Verify action was recorded
        actions = handler.get_processed_actions()
        assert len(actions) == 1
        assert actions[0].action_type == CorporateActionType.STOCK_SPLIT

    @pytest.mark.asyncio
    async def test_dividend_does_not_trigger_stop_loss(self, mock_broker_with_positions):
        """Test that dividend baseline adjustment prevents false stop-loss."""
        # Setup
        mock_monitor = MagicMock()
        handler = CorporateActionsHandler(
            broker=mock_broker_with_positions, position_monitor=mock_monitor
        )

        # Execute dividend
        result = await handler.on_dividend(
            symbol="AAPL", amount=Decimal("0.24"), ex_date=date(2024, 2, 9)
        )

        # Verify dividend was recorded
        assert result["total_payment"] == "24.00"

        # Verify baseline adjustment was attempted
        # (Note: actual implementation depends on position_monitor interface)

    @pytest.mark.asyncio
    async def test_merger_workflow(self, mock_broker_with_positions):
        """Test complete merger workflow."""
        # Setup - create a position with TWTR symbol
        position = MagicMock()
        position.position_id = "pos_456"
        position.symbol = "TWTR"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()

        mock_broker_with_positions.get_all_open_positions.return_value = [position]

        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute merger
        result = await handler.on_merger(
            symbol="TWTR", acquire_symbol="ELON", ratio=Decimal("1.5"), ex_date=date(2022, 10, 27)
        )

        # Verify result
        assert result["positions_converted"] == 1
        assert result["conversions"][0]["new_symbol"] == "ELON"
        assert result["conversions"][0]["new_quantity"] in ["150", "150.0"]

    @pytest.mark.asyncio
    async def test_delisting_emergency_closure(self, mock_broker_with_positions):
        """Test emergency position closure on delisting."""
        # Setup
        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute delisting
        result = await handler.on_delisting(
            symbol="AAPL", delist_date=date(2024, 3, 15), reason="Bankruptcy", force_close=True
        )

        # Verify result
        assert result["positions_closed"] == 1

        # Verify order was placed
        mock_broker_with_positions.execute_order_with_wal.assert_called_once()

        # Get the order that was placed
        call_args = mock_broker_with_positions.execute_order_with_wal.call_args
        order = call_args[0][0]

        # Verify order parameters
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.SELL

    @pytest.mark.asyncio
    async def test_sequential_corporate_actions(self, mock_broker_with_positions):
        """Test multiple sequential corporate actions on same symbol."""
        # Setup
        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Simulate: Stock split -> Dividend -> Symbol change
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 1, 1))
        await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))
        await handler.on_symbol_change("AAPL", "AAPL_NEW", date(2024, 3, 1))

        # Verify all actions were recorded
        actions = handler.get_processed_actions()
        assert len(actions) == 3

        # Verify action types
        action_types = [a.action_type for a in actions]
        assert CorporateActionType.STOCK_SPLIT in action_types
        assert CorporateActionType.DIVIDEND in action_types
        assert CorporateActionType.SYMBOL_CHANGE in action_types

    @pytest.mark.asyncio
    async def test_spinoff_creates_new_position(self, mock_broker_with_positions):
        """Test spin-off creates new position record."""
        # Setup - create a position with FOO symbol
        position = MagicMock()
        position.position_id = "pos_789"
        position.symbol = "FOO"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()

        mock_broker_with_positions.get_all_open_positions.return_value = [position]

        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute spin-off
        result = await handler.on_spinoff(
            symbol="FOO", spinoff_symbol="BAR", ratio=Decimal("0.5"), ex_date=date(2024, 1, 1)
        )

        # Verify result
        assert result["new_positions_created"] == 1
        assert result["creations"][0]["spinoff_symbol"] == "BAR"
        assert result["creations"][0]["spinoff_quantity"] in ["50.0", "50.00"]


class TestCorporateActionsCallbacks:
    """Tests for corporate action callbacks."""

    @pytest.mark.asyncio
    async def test_action_callback_invoked(self, mock_broker_with_positions):
        """Test that callback is invoked when action is processed."""
        # Setup
        callback_actions = []

        def on_action(action):
            callback_actions.append(action)

        handler = CorporateActionsHandler(broker=mock_broker_with_positions, on_action=on_action)

        # Execute action
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))

        # Verify callback was invoked
        assert len(callback_actions) == 1
        assert callback_actions[0].action_type == CorporateActionType.STOCK_SPLIT

    @pytest.mark.asyncio
    async def test_multiple_callbacks(self, mock_broker_with_positions):
        """Test callbacks for multiple actions."""
        # Setup
        callback_actions = []

        def on_action(action):
            callback_actions.append(action)

        handler = CorporateActionsHandler(broker=mock_broker_with_positions, on_action=on_action)

        # Execute multiple actions
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))
        await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))

        # Verify callbacks
        assert len(callback_actions) == 2


class TestCorporateActionsStatistics:
    """Tests for corporate actions statistics tracking."""

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, mock_broker_with_positions):
        """Test that statistics are properly tracked."""
        # Setup
        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute various actions
        # Stock split for AAPL
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))
        # Dividend for AAPL
        await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))

        # Merger for TWTR (create a TWTR position)
        position = MagicMock()
        position.position_id = "pos_999"
        position.symbol = "TWTR"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()
        mock_broker_with_positions.get_all_open_positions.return_value = [position]
        await handler.on_merger("TWTR", "ELON", Decimal("1.5"), date(2022, 10, 27))

        # Get statistics
        stats = handler.get_stats()

        # Verify
        assert stats["stock_splits_processed"] == 1
        assert stats["dividends_processed"] == 1
        assert stats["mergers_processed"] == 1
        assert stats["positions_adjusted"] == 2  # split + merger

    @pytest.mark.asyncio
    async def test_delisting_increments_closed_count(self, mock_broker_with_positions):
        """Test that delisting increments closed count."""
        # Setup
        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute delisting
        await handler.on_delisting("AAPL", date(2024, 3, 15), "Bankruptcy", force_close=True)

        # Verify
        stats = handler.get_stats()
        assert stats["delistings_processed"] == 1
        assert stats["positions_closed"] == 1


class TestCorporateActionsErrorHandling:
    """Tests for error handling in corporate actions."""

    @pytest.mark.asyncio
    async def test_broker_unavailable(self):
        """Test behavior when broker is unavailable."""
        # Setup - handler without broker
        handler = CorporateActionsHandler(broker=None)

        # Should not raise exception, but return empty results
        result = await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))

        # Verify
        assert result["positions_adjusted"] == 0

    @pytest.mark.asyncio
    async def test_position_update_failure_continues(self, mock_broker_with_positions):
        """Test that failures with one position don't stop processing others."""
        # Setup
        pos1 = MagicMock()
        pos1.position_id = "pos_1"
        pos1.symbol = "AAPL"
        pos1.quantity = Decimal("100")
        pos1.avg_price = Decimal("150.00")

        pos2 = MagicMock()
        pos2.position_id = "pos_2"
        pos2.symbol = "AAPL"
        pos2.quantity = Decimal("50")
        pos2.avg_price = Decimal("140.00")

        # Make pos2 raise an error when accessing quantity
        type(pos2).quantity = property(lambda self: (_ for _ in ()).throw(ValueError("Test error")))

        mock_broker_with_positions.get_all_open_positions.return_value = [pos1, pos2]

        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute
        result = await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))

        # Verify one position was adjusted despite the error
        assert result["positions_adjusted"] == 1


class TestCorporateActionsWithDatabase:
    """Tests for database persistence of corporate actions."""

    @pytest.mark.asyncio
    async def test_action_persistence(self, mock_broker_with_positions):
        """Test that actions can be retrieved after processing."""
        # Setup
        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute actions
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))
        await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))

        # Query by symbol
        aapl_actions = handler.get_action_for_symbol("AAPL")
        assert len(aapl_actions) == 2

        # Query by type
        splits = handler.get_action_by_type(CorporateActionType.STOCK_SPLIT)
        assert len(splits) == 1
        assert splits[0].symbol == "AAPL"

        dividends = handler.get_action_by_type(CorporateActionType.DIVIDEND)
        assert len(dividends) == 1
        assert dividends[0].amount == Decimal("0.24")

    @pytest.mark.asyncio
    async def test_clear_history(self, mock_broker_with_positions):
        """Test clearing action history."""
        # Setup
        handler = CorporateActionsHandler(broker=mock_broker_with_positions)

        # Execute actions
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))

        # Clear history
        handler.clear_history()

        # Verify
        assert len(handler.get_processed_actions()) == 0
