"""
Unit tests for Corporate Actions Handler.

Tests cover:
- Stock split position adjustment
- Dividend baseline adjustment
- Merger position conversion
- Delisting position closure
- Spin-off position creation
- Symbol change handling
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.interfaces.broker_base import Order, OrderSide, OrderStatus, OrderType
from app.services.corporate_actions.handler import (
    CorporateAction,
    CorporateActionType,
    CorporateActionsHandler,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_broker():
    """Create a mock broker."""
    broker = MagicMock()
    broker.get_all_open_positions = AsyncMock(return_value=[])
    broker.execute_order_with_wal = AsyncMock()
    return broker


@pytest.fixture
def mock_position_monitor():
    """Create a mock position monitor."""
    monitor = MagicMock()
    monitor.adjust_baseline = AsyncMock()
    return monitor


@pytest.fixture
def sample_position():
    """Create a sample position for testing."""
    position = MagicMock()
    position.position_id = "pos_123"
    position.symbol = "AAPL"
    position.quantity = Decimal("100")
    position.avg_price = Decimal("150.00")
    position.recalculate_metrics = Mock()
    return position


@pytest.fixture
def sample_position_dict():
    """Create a sample position as dict for testing."""
    return {
        "position_id": "pos_456",
        "symbol": "AAPL",
        "quantity": Decimal("50"),
        "avg_price": Decimal("175.50"),
    }


@pytest.fixture
def handler(mock_broker, mock_position_monitor):
    """Create a CorporateActionsHandler instance."""
    return CorporateActionsHandler(broker=mock_broker, position_monitor=mock_position_monitor)


# =============================================================================
# TESTS: STOCK SPLITS
# =============================================================================


class TestStockSplits:
    """Tests for stock split handling."""

    @pytest.mark.asyncio
    async def test_stock_split_2_for_1(self, handler, mock_broker, sample_position):
        """Test 2-for-1 stock split."""
        # Setup
        mock_broker.get_all_open_positions.return_value = [sample_position]
        symbol = "AAPL"
        ratio = Decimal("2")
        ex_date = date(2024, 6, 1)

        # Execute
        result = await handler.on_stock_split(symbol, ratio, ex_date)

        # Verify
        assert result["symbol"] == symbol
        assert result["ratio"] == "2"
        assert result["positions_adjusted"] == 1

        # Check position adjustments
        adjustments = result["adjustments"]
        assert len(adjustments) == 1
        assert adjustments[0]["old_quantity"] == "100"
        assert adjustments[0]["new_quantity"] == "200"
        assert adjustments[0]["old_avg_price"] == "150.00"
        assert adjustments[0]["new_avg_price"] == "75.00"

        # Verify position was updated
        assert sample_position.quantity == Decimal("200")
        assert sample_position.avg_price == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_stock_split_3_for_2(self, handler, mock_broker, sample_position):
        """Test 3-for-2 stock split."""
        # Setup
        mock_broker.get_all_open_positions.return_value = [sample_position]
        symbol = "AAPL"
        ratio = Decimal("1.5")  # 3-for-2 = 1.5
        ex_date = date(2024, 6, 1)

        # Execute
        result = await handler.on_stock_split(symbol, ratio, ex_date)

        # Verify
        assert result["positions_adjusted"] == 1
        assert sample_position.quantity == Decimal("150")
        assert sample_position.avg_price == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_stock_split_multiple_positions(self, handler, mock_broker):
        """Test stock split with multiple positions."""
        # Setup
        pos1 = MagicMock()
        pos1.position_id = "pos_1"
        pos1.symbol = "AAPL"
        pos1.quantity = Decimal("100")
        pos1.avg_price = Decimal("150.00")
        pos1.recalculate_metrics = Mock()

        pos2 = MagicMock()
        pos2.position_id = "pos_2"
        pos2.symbol = "AAPL"
        pos2.quantity = Decimal("50")
        pos2.avg_price = Decimal("140.00")
        pos2.recalculate_metrics = Mock()

        mock_broker.get_all_open_positions.return_value = [pos1, pos2]

        # Execute
        result = await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))

        # Verify
        assert result["positions_adjusted"] == 2
        assert pos1.quantity == Decimal("200")
        assert pos2.quantity == Decimal("100")

    @pytest.mark.asyncio
    async def test_stock_split_invalid_ratio(self, handler):
        """Test stock split with invalid ratio."""
        with pytest.raises(ValueError, match="Invalid split ratio"):
            await handler.on_stock_split("AAPL", Decimal("0"), date(2024, 6, 1))

    @pytest.mark.asyncio
    async def test_stock_split_negative_ratio(self, handler):
        """Test stock split with negative ratio."""
        with pytest.raises(ValueError, match="Invalid split ratio"):
            await handler.on_stock_split("AAPL", Decimal("-2"), date(2024, 6, 1))

    @pytest.mark.asyncio
    async def test_stock_split_no_positions(self, handler, mock_broker):
        """Test stock split with no positions."""
        # Setup
        mock_broker.get_all_open_positions.return_value = []

        # Execute
        result = await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))

        # Verify
        assert result["positions_adjusted"] == 0
        assert result["adjustments"] == []


# =============================================================================
# TESTS: DIVIDENDS
# =============================================================================


class TestDividends:
    """Tests for dividend handling."""

    @pytest.mark.asyncio
    async def test_dividend_payment(self, handler, mock_broker, sample_position):
        """Test dividend payment recording."""
        # Setup
        mock_broker.get_all_open_positions.return_value = [sample_position]
        symbol = "AAPL"
        amount = Decimal("0.24")
        ex_date = date(2024, 2, 9)

        # Execute
        result = await handler.on_dividend(symbol, amount, ex_date)

        # Verify
        assert result["symbol"] == symbol
        assert result["amount"] == "0.24"
        assert result["shares_held"] == "100"
        assert result["total_payment"] == "24.00"  # 100 * 0.24

    @pytest.mark.asyncio
    async def test_dividend_with_payable_date(self, handler, mock_broker):
        """Test dividend with payable date."""
        # Setup
        mock_broker.get_all_open_positions.return_value = []

        # Execute
        result = await handler.on_dividend(
            symbol="AAPL",
            amount=Decimal("0.24"),
            ex_date=date(2024, 2, 9),
            payable_date=date(2024, 2, 16),
        )

        # Verify
        assert result["payable_date"] == "2024-02-16"

    @pytest.mark.asyncio
    async def test_dividend_invalid_amount(self, handler):
        """Test dividend with negative amount."""
        with pytest.raises(ValueError, match="Invalid dividend amount"):
            await handler.on_dividend("AAPL", Decimal("-0.24"), date(2024, 2, 9))

    @pytest.mark.asyncio
    async def test_dividend_no_positions(self, handler, mock_broker):
        """Test dividend with no positions."""
        # Setup
        mock_broker.get_all_open_positions.return_value = []

        # Execute
        result = await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))

        # Verify
        assert result["shares_held"] == "0"
        assert result["total_payment"] in ["0", "0.00"]  # Accept either format


# =============================================================================
# TESTS: MERGERS
# =============================================================================


class TestMergers:
    """Tests for merger handling."""

    @pytest.mark.asyncio
    async def test_merger_conversion(self, handler, mock_broker):
        """Test merger position conversion."""
        # Setup - create a position with TWTR symbol
        position = MagicMock()
        position.position_id = "pos_123"
        position.symbol = "TWTR"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()

        mock_broker.get_all_open_positions.return_value = [position]
        symbol = "TWTR"
        acquire_symbol = "ELON"
        ratio = Decimal("1.5")
        ex_date = date(2022, 10, 27)

        # Execute
        result = await handler.on_merger(symbol, acquire_symbol, ratio, ex_date)

        # Verify
        assert result["symbol"] == symbol
        assert result["acquire_symbol"] == acquire_symbol
        assert result["ratio"] == "1.5"
        assert result["positions_converted"] == 1

        # Check position conversion
        conversions = result["conversions"]
        assert len(conversions) == 1
        assert conversions[0]["old_symbol"] == symbol
        assert conversions[0]["new_symbol"] == acquire_symbol
        assert conversions[0]["old_quantity"] == "100"
        assert conversions[0]["new_quantity"] in ["150", "150.0"]  # Accept either format

        # Verify position was updated
        assert position.symbol == acquire_symbol
        assert position.quantity == Decimal("150")

    @pytest.mark.asyncio
    async def test_merger_invalid_ratio(self, handler):
        """Test merger with invalid ratio."""
        with pytest.raises(ValueError, match="Invalid merger ratio"):
            await handler.on_merger("TWTR", "ELON", Decimal("0"), date(2022, 10, 27))

    @pytest.mark.asyncio
    async def test_merger_no_acquire_symbol(self, handler):
        """Test merger without acquiring symbol."""
        with pytest.raises(ValueError, match="Acquiring symbol is required"):
            await handler.on_merger("TWTR", "", Decimal("1.5"), date(2022, 10, 27))


# =============================================================================
# TESTS: DELISTINGS
# =============================================================================


class TestDelistings:
    """Tests for delisting handling."""

    @pytest.mark.asyncio
    async def test_delisting_with_force_close(self, handler, mock_broker):
        """Test delisting with forced position closure."""
        # Setup - create a position with BANKRUPT symbol
        position = MagicMock()
        position.position_id = "pos_123"
        position.symbol = "BANKRUPT"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()

        mock_broker.get_all_open_positions.return_value = [position]

        # Mock successful order execution
        order_result = MagicMock()
        order_result.order_id = "ORDER_123"
        mock_broker.execute_order_with_wal.return_value = order_result

        # Execute
        result = await handler.on_delisting(
            symbol="BANKRUPT", delist_date=date(2024, 3, 15), reason="Bankruptcy", force_close=True
        )

        # Verify
        assert result["symbol"] == "BANKRUPT"
        assert result["reason"] == "Bankruptcy"
        assert result["positions_closed"] == 1

        # Verify order was placed
        mock_broker.execute_order_with_wal.assert_called_once()

    @pytest.mark.asyncio
    async def test_delisting_without_force_close(self, handler, mock_broker):
        """Test delisting without forced position closure."""
        # Setup - create a position with BANKRUPT symbol
        position = MagicMock()
        position.position_id = "pos_123"
        position.symbol = "BANKRUPT"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()

        mock_broker.get_all_open_positions.return_value = [position]

        # Execute
        result = await handler.on_delisting(
            symbol="BANKRUPT", delist_date=date(2024, 3, 15), reason="Bankruptcy", force_close=False
        )

        # Verify
        assert result["positions_closed"] == 1
        assert result["closures"][0]["status"] == "marked_closed"

        # Verify no order was placed
        mock_broker.execute_order_with_wal.assert_not_called()

    @pytest.mark.asyncio
    async def test_delisting_no_broker(self):
        """Test delisting when no broker is configured."""
        # Setup - handler without broker and a mock position
        handler = CorporateActionsHandler(broker=None)
        position = MagicMock()
        position.position_id = "pos_123"
        position.symbol = "BANKRUPT"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()

        handler._get_open_positions = AsyncMock(return_value=[position])

        # Execute
        result = await handler.on_delisting(
            symbol="BANKRUPT", delist_date=date(2024, 3, 15), reason="Bankruptcy", force_close=True
        )

        # Verify
        assert result["positions_closed"] == 1


# =============================================================================
# TESTS: SPIN-OFFS
# =============================================================================


class TestSpinoffs:
    """Tests for spin-off handling."""

    @pytest.mark.asyncio
    async def test_spinoff_creation(self, handler, mock_broker):
        """Test spin-off position creation."""
        # Setup - create a position with FOO symbol
        position = MagicMock()
        position.position_id = "pos_123"
        position.symbol = "FOO"
        position.quantity = Decimal("100")
        position.avg_price = Decimal("50.00")
        position.recalculate_metrics = Mock()

        mock_broker.get_all_open_positions.return_value = [position]
        symbol = "FOO"
        spinoff_symbol = "BAR"
        ratio = Decimal("0.5")
        ex_date = date(2024, 1, 1)

        # Execute
        result = await handler.on_spinoff(symbol, spinoff_symbol, ratio, ex_date)

        # Verify
        assert result["symbol"] == symbol
        assert result["spinoff_symbol"] == spinoff_symbol
        assert result["ratio"] == "0.5"
        assert result["new_positions_created"] == 1

        # Check spin-off creation
        creations = result["creations"]
        assert len(creations) == 1
        assert creations[0]["spinoff_symbol"] == spinoff_symbol
        assert creations[0]["spinoff_quantity"] in ["50.0", "50.00"]  # Accept either format

    @pytest.mark.asyncio
    async def test_spinoff_invalid_ratio(self, handler):
        """Test spin-off with invalid ratio."""
        with pytest.raises(ValueError, match="Invalid spinoff ratio"):
            await handler.on_spinoff("FOO", "BAR", Decimal("0"), date(2024, 1, 1))

    @pytest.mark.asyncio
    async def test_spinoff_no_symbol(self, handler):
        """Test spin-off without spin-off symbol."""
        with pytest.raises(ValueError, match="Spin-off symbol is required"):
            await handler.on_spinoff("FOO", "", Decimal("0.5"), date(2024, 1, 1))


# =============================================================================
# TESTS: SYMBOL CHANGES
# =============================================================================


class TestSymbolChanges:
    """Tests for symbol change handling."""

    @pytest.mark.asyncio
    async def test_symbol_change(self, handler, mock_broker, sample_position):
        """Test symbol change (ticker rename)."""
        # Setup
        mock_broker.get_all_open_positions.return_value = [sample_position]
        old_symbol = "FB"
        new_symbol = "META"
        ex_date = date(2022, 6, 9)

        sample_position.symbol = old_symbol

        # Execute
        result = await handler.on_symbol_change(old_symbol, new_symbol, ex_date)

        # Verify
        assert result["old_symbol"] == old_symbol
        assert result["new_symbol"] == new_symbol
        assert result["positions_updated"] == 1

        # Check updates
        updates = result["updates"]
        assert len(updates) == 1
        assert updates[0]["old_symbol"] == old_symbol
        assert updates[0]["new_symbol"] == new_symbol

        # Verify position was updated
        assert sample_position.symbol == new_symbol

    @pytest.mark.asyncio
    async def test_symbol_change_no_new_symbol(self, handler):
        """Test symbol change without new symbol."""
        with pytest.raises(ValueError, match="New symbol is required"):
            await handler.on_symbol_change("FB", "", date(2022, 6, 9))


# =============================================================================
# TESTS: CORPORATE ACTION MODEL
# =============================================================================


class TestCorporateActionModel:
    """Tests for CorporateAction dataclass."""

    def test_stock_split_action(self):
        """Test creating stock split action."""
        action = CorporateAction(
            action_type=CorporateActionType.STOCK_SPLIT,
            symbol="AAPL",
            ex_date=date(2024, 6, 1),
            ratio=Decimal("2"),
        )

        assert action.action_type == CorporateActionType.STOCK_SPLIT
        assert action.symbol == "AAPL"
        assert action.ratio == Decimal("2")

    def test_dividend_action(self):
        """Test creating dividend action."""
        action = CorporateAction(
            action_type=CorporateActionType.DIVIDEND,
            symbol="AAPL",
            ex_date=date(2024, 2, 9),
            amount=Decimal("0.24"),
        )

        assert action.action_type == CorporateActionType.DIVIDEND
        assert action.amount == Decimal("0.24")

    def test_action_to_dict(self):
        """Test converting action to dictionary."""
        action = CorporateAction(
            action_type=CorporateActionType.STOCK_SPLIT,
            symbol="AAPL",
            ex_date=date(2024, 6, 1),
            ratio=Decimal("2"),
            description="2-for-1 stock split",
        )

        result = action.to_dict()

        assert result["action_type"] == "stock_split"
        assert result["symbol"] == "AAPL"
        assert result["ex_date"] == "2024-06-01"
        assert result["ratio"] == "2"
        assert result["description"] == "2-for-1 stock split"

    def test_merger_action_validation(self):
        """Test merger action requires new_symbol."""
        with pytest.raises(ValueError, match="new_symbol required"):
            CorporateAction(
                action_type=CorporateActionType.MERGER,
                symbol="TWTR",
                ex_date=date(2022, 10, 27),
                ratio=Decimal("1.5"),
            )

    def test_dividend_action_validation(self):
        """Test dividend action requires non-negative amount."""
        with pytest.raises(ValueError, match="Amount must be non-negative"):
            CorporateAction(
                action_type=CorporateActionType.DIVIDEND,
                symbol="AAPL",
                ex_date=date(2024, 2, 9),
                amount=Decimal("-0.24"),
            )


# =============================================================================
# TESTS: QUERY METHODS
# =============================================================================


class TestQueryMethods:
    """Tests for handler query methods."""

    @pytest.mark.asyncio
    async def test_get_processed_actions(self, handler, mock_broker):
        """Test getting all processed actions."""
        # Setup
        mock_broker.get_all_open_positions.return_value = []

        # Execute multiple actions
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))
        await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))

        # Verify
        actions = handler.get_processed_actions()
        assert len(actions) == 2

    @pytest.mark.asyncio
    async def test_get_action_for_symbol(self, handler, mock_broker):
        """Test getting actions for specific symbol."""
        # Setup
        mock_broker.get_all_open_positions.return_value = []

        # Execute actions for different symbols
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))
        await handler.on_dividend("MSFT", Decimal("0.68"), date(2024, 2, 9))

        # Verify
        aapl_actions = handler.get_action_for_symbol("AAPL")
        assert len(aapl_actions) == 1
        assert aapl_actions[0].symbol == "AAPL"

        msft_actions = handler.get_action_for_symbol("MSFT")
        assert len(msft_actions) == 1
        assert msft_actions[0].symbol == "MSFT"

    @pytest.mark.asyncio
    async def test_get_action_by_type(self, handler, mock_broker):
        """Test getting actions by type."""
        # Setup
        mock_broker.get_all_open_positions.return_value = []

        # Execute different action types
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))
        await handler.on_stock_split("MSFT", Decimal("3"), date(2024, 6, 1))
        await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))

        # Verify
        split_actions = handler.get_action_by_type(CorporateActionType.STOCK_SPLIT)
        assert len(split_actions) == 2

        dividend_actions = handler.get_action_by_type(CorporateActionType.DIVIDEND)
        assert len(dividend_actions) == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, handler, mock_broker):
        """Test getting handler statistics."""
        # Setup
        mock_broker.get_all_open_positions.return_value = []

        # Execute actions
        await handler.on_stock_split("AAPL", Decimal("2"), date(2024, 6, 1))
        await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))
        await handler.on_merger("TWTR", "ELON", Decimal("1.5"), date(2022, 10, 27))

        # Verify
        stats = handler.get_stats()
        assert stats["stock_splits_processed"] == 1
        assert stats["dividends_processed"] == 1
        assert stats["mergers_processed"] == 1
        assert stats["delistings_processed"] == 0

    def test_clear_history(self, handler):
        """Test clearing action history."""
        # Add a mock action directly
        action = CorporateAction(
            action_type=CorporateActionType.STOCK_SPLIT,
            symbol="AAPL",
            ex_date=date(2024, 6, 1),
            ratio=Decimal("2"),
        )
        handler._processed_actions["AAPL_2024-06-01"] = action

        # Clear history
        handler.clear_history()

        # Verify
        assert len(handler.get_processed_actions()) == 0


# =============================================================================
# TESTS: POSITION EXTRACTION HELPERS
# =============================================================================


class TestPositionExtraction:
    """Tests for position data extraction methods."""

    def test_extract_symbol_from_object(self):
        """Test extracting symbol from position object."""
        position = MagicMock()
        position.symbol = "AAPL"

        handler = CorporateActionsHandler()
        assert handler._get_position_symbol(position) == "AAPL"

    def test_extract_symbol_from_dict(self):
        """Test extracting symbol from position dict."""
        position = {"symbol": "AAPL"}

        handler = CorporateActionsHandler()
        assert handler._get_position_symbol(position) == "AAPL"

    def test_extract_quantity_from_decimal(self):
        """Test extracting quantity from Decimal."""
        position = MagicMock()
        position.quantity = Decimal("100")

        handler = CorporateActionsHandler()
        assert handler._get_position_quantity(position) == Decimal("100")

    def test_extract_quantity_from_int(self):
        """Test extracting quantity from int."""
        position = MagicMock()
        position.quantity = 100

        handler = CorporateActionsHandler()
        assert handler._get_position_quantity(position) == Decimal("100")

    def test_extract_avg_price_from_object(self):
        """Test extracting avg_price from position object."""
        position = MagicMock()
        position.avg_price = Decimal("150.00")

        handler = CorporateActionsHandler()
        assert handler._get_position_avg_price(position) == Decimal("150.00")

    def test_extract_avg_price_from_dict(self):
        """Test extracting avg_price from position dict."""
        position = {"avg_price": "150.00"}

        handler = CorporateActionsHandler()
        assert handler._get_position_avg_price(position) == Decimal("150.00")

    def test_extract_position_id_from_object(self):
        """Test extracting position_id from position object."""
        position = MagicMock()
        position.position_id = "pos_123"

        handler = CorporateActionsHandler()
        assert handler._get_position_id(position) == "pos_123"
