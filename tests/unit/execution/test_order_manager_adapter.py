"""
Unit tests for OrderManagerAdapter - Task 11 Order Manager Integration

Tests the adapter that bridges OrderManager to ITradeExecutor protocol.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.execution.order_manager_adapter import (
    OrderManagerAdapter,
    get_order_manager_adapter,
)
from app.services.live_trading.alert_to_trade_mapper import TradeSignal, TradeSignalType
from app.services.live_trading.broker_connector import (
    BrokerOrder,
    OrderSide,
    OrderStatus,
    OrderType,
)


@pytest.fixture
def mock_order_manager():
    """Create a mock OrderManager for testing."""
    manager = MagicMock()

    # Configure async methods
    manager.place_order = AsyncMock()
    manager.cancel_order = AsyncMock(return_value=True)
    manager.cancel_all_orders = AsyncMock(return_value=0)
    manager.get_order_status = AsyncMock(return_value=OrderStatus.FILLED)
    manager.get_pending_orders = AsyncMock(return_value=[])
    manager.get_executed_orders = AsyncMock(return_value=[])
    manager.get_order_history = AsyncMock(return_value=[])

    return manager


@pytest.fixture
def adapter(mock_order_manager):
    """Create OrderManagerAdapter with mock manager."""
    return OrderManagerAdapter(order_manager=mock_order_manager)


@pytest.fixture
def sample_signal():
    """Create a sample TradeSignal for testing."""
    return TradeSignal(
        signal_id="test_signal_001",
        alert_id="alert_001",
        alert_rule_id="rule_001",
        symbol="AAPL",
        signal_type=TradeSignalType.LONG,
        order_side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100"),
        price=Decimal("150.00"),
    )


@pytest.fixture
def sample_broker_order():
    """Create a sample BrokerOrder for testing."""
    return BrokerOrder(
        order_id="broker_order_001",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100"),
        status=OrderStatus.FILLED,
        filled_quantity=Decimal("100"),
        avg_filled_price=Decimal("150.05"),
    )


class TestOrderManagerAdapterProtocol:
    """Test ITradeExecutor protocol compliance."""

    def test_adapter_implements_protocol(self, adapter):
        """Verify adapter implements ITradeExecutor protocol methods."""
        # Check that all required methods are implemented
        required_methods = [
            "execute_order",
            "cancel_order",
            "modify_order",
            "get_order_status",
            "get_open_orders",
        ]
        for method in required_methods:
            assert hasattr(adapter, method)
            assert callable(getattr(adapter, method))

    def test_adapter_has_execute_order_method(self, adapter):
        """Verify execute_order method exists."""
        assert hasattr(adapter, "execute_order")
        assert callable(adapter.execute_order)

    def test_adapter_has_cancel_order_method(self, adapter):
        """Verify cancel_order method exists."""
        assert hasattr(adapter, "cancel_order")
        assert callable(adapter.cancel_order)

    def test_adapter_has_modify_order_method(self, adapter):
        """Verify modify_order method exists."""
        assert hasattr(adapter, "modify_order")
        assert callable(adapter.modify_order)

    def test_adapter_has_get_order_status_method(self, adapter):
        """Verify get_order_status method exists."""
        assert hasattr(adapter, "get_order_status")
        assert callable(adapter.get_order_status)

    def test_adapter_has_get_open_orders_method(self, adapter):
        """Verify get_open_orders method exists."""
        assert hasattr(adapter, "get_open_orders")
        assert callable(adapter.get_open_orders)


class TestExecuteOrder:
    """Test execute_order method."""

    @pytest.mark.asyncio
    async def test_execute_order_success(
        self, adapter, mock_order_manager, sample_signal, sample_broker_order
    ):
        """Test successful order execution."""
        # Configure mock to return filled order
        mock_order_manager.place_order.return_value = sample_broker_order

        result = await adapter.execute_order(sample_signal)

        assert result.success is True
        assert result.order_id == "broker_order_001"
        assert result.symbol == "AAPL"
        assert result.side == "buy"
        assert result.quantity == Decimal("100")
        assert result.execution_price == Decimal("150.05")
        assert result.status == "FILLED"

        # Verify place_order was called with correct parameters
        mock_order_manager.place_order.assert_called_once_with(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            price=Decimal("150.00"),
            stop_price=None,
            timeout_seconds=60,
        )

    @pytest.mark.asyncio
    async def test_execute_order_rejected_by_risk_gates(
        self, adapter, mock_order_manager, sample_signal
    ):
        """Test order rejected by risk gates."""
        # Configure mock to return None (rejected)
        mock_order_manager.place_order.return_value = None

        result = await adapter.execute_order(sample_signal)

        assert result.success is False
        assert result.order_id == ""
        assert result.status == "REJECTED"
        assert "rejected by risk gates" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_order_with_stop_loss(self, adapter, mock_order_manager):
        """Test order execution with stop loss."""
        signal = TradeSignal(
            signal_id="test_signal_002",
            alert_id="alert_002",
            alert_rule_id="rule_002",
            symbol="TSLA",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.STOP,
            quantity=Decimal("50"),
            price=Decimal("200.00"),
            stop_loss=Decimal("195.00"),
        )

        broker_order = BrokerOrder(
            order_id="broker_order_002",
            symbol="TSLA",
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            quantity=Decimal("50"),
            status=OrderStatus.FILLED,
            filled_quantity=Decimal("50"),
            avg_filled_price=Decimal("200.00"),
        )
        mock_order_manager.place_order.return_value = broker_order

        result = await adapter.execute_order(signal)

        assert result.success is True
        mock_order_manager.place_order.assert_called_once_with(
            symbol="TSLA",
            side=OrderSide.BUY,
            quantity=Decimal("50"),
            order_type=OrderType.STOP,
            price=Decimal("200.00"),
            stop_price=Decimal("195.00"),
            timeout_seconds=60,
        )

    @pytest.mark.asyncio
    async def test_execute_order_exception_handling(
        self, adapter, mock_order_manager, sample_signal
    ):
        """Test exception handling in execute_order."""
        # Configure mock to raise exception
        mock_order_manager.place_order.side_effect = Exception("Connection error")

        result = await adapter.execute_order(sample_signal)

        assert result.success is False
        assert result.status == "FAILED"
        assert "Connection error" in result.error

    @pytest.mark.asyncio
    async def test_execute_order_signal_to_order_mapping(
        self, adapter, mock_order_manager, sample_signal, sample_broker_order
    ):
        """Test signal to order ID mapping."""
        mock_order_manager.place_order.return_value = sample_broker_order

        await adapter.execute_order(sample_signal)

        # Verify mapping was created
        assert adapter.get_order_id_for_signal("test_signal_001") == "broker_order_001"


class TestCancelOrder:
    """Test cancel_order method."""

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter, mock_order_manager):
        """Test successful order cancellation."""
        result = await adapter.cancel_order("order_123")

        assert result is True
        mock_order_manager.cancel_order.assert_called_once_with("order_123")

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, adapter, mock_order_manager):
        """Test failed order cancellation."""
        mock_order_manager.cancel_order.return_value = False

        result = await adapter.cancel_order("order_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_order_clears_mapping(self, adapter, mock_order_manager):
        """Test that cancel clears signal-to-order mapping."""
        # Create a mapping
        adapter._signal_to_order_map["signal_001"] = "order_123"

        await adapter.cancel_order("order_123")

        # Verify mapping was cleared
        assert adapter.get_order_id_for_signal("signal_001") is None

    @pytest.mark.asyncio
    async def test_cancel_order_exception_handling(self, adapter, mock_order_manager):
        """Test exception handling in cancel_order."""
        mock_order_manager.cancel_order.side_effect = Exception("Network error")

        result = await adapter.cancel_order("order_123")

        assert result is False


class TestModifyOrder:
    """Test modify_order method."""

    @pytest.mark.asyncio
    async def test_modify_order_success(self, adapter, mock_order_manager):
        """Test successful order modification."""
        # Setup existing order
        existing_order = BrokerOrder(
            order_id="order_123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        # Setup replacement order
        new_order = BrokerOrder(
            order_id="order_456",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("151.00"),
        )

        mock_order_manager.get_pending_orders = AsyncMock(return_value=[existing_order])
        mock_order_manager.cancel_order = AsyncMock(return_value=True)
        mock_order_manager.place_order = AsyncMock(return_value=new_order)

        result = await adapter.modify_order("order_123", Decimal("151.00"))

        assert result is True
        mock_order_manager.cancel_order.assert_called_once_with("order_123")
        mock_order_manager.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_modify_order_not_found(self, adapter, mock_order_manager):
        """Test modify order when order not found."""
        mock_order_manager.get_pending_orders = AsyncMock(return_value=[])

        result = await adapter.modify_order("order_123", Decimal("151.00"))

        assert result is False

    @pytest.mark.asyncio
    async def test_modify_order_cancel_fails(self, adapter, mock_order_manager):
        """Test modify order when cancel fails."""
        existing_order = BrokerOrder(
            order_id="order_123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        mock_order_manager.get_pending_orders = AsyncMock(return_value=[existing_order])
        mock_order_manager.cancel_order = AsyncMock(return_value=False)

        result = await adapter.modify_order("order_123", Decimal("151.00"))

        assert result is False


class TestGetOrderStatus:
    """Test get_order_status method."""

    @pytest.mark.asyncio
    async def test_get_order_status_filled(self, adapter, mock_order_manager):
        """Test getting order status for filled order."""
        mock_order_manager.get_order_status = AsyncMock(return_value=OrderStatus.FILLED)

        status = await adapter.get_order_status("order_123")

        assert status == "FILLED"
        mock_order_manager.get_order_status.assert_called_once_with("order_123")

    @pytest.mark.asyncio
    async def test_get_order_status_pending(self, adapter, mock_order_manager):
        """Test getting order status for pending order."""
        mock_order_manager.get_order_status = AsyncMock(return_value=OrderStatus.PENDING)

        status = await adapter.get_order_status("order_123")

        assert status == "PENDING"

    @pytest.mark.asyncio
    async def test_get_order_status_unknown(self, adapter, mock_order_manager):
        """Test getting order status for unknown order."""
        mock_order_manager.get_order_status = AsyncMock(return_value=None)

        status = await adapter.get_order_status("order_123")

        assert status == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_get_order_status_cancelled(self, adapter, mock_order_manager):
        """Test getting order status for cancelled order."""
        mock_order_manager.get_order_status = AsyncMock(return_value=OrderStatus.CANCELED)

        status = await adapter.get_order_status("order_123")

        assert status == "CANCELED"


class TestGetOpenOrders:
    """Test get_open_orders method."""

    @pytest.mark.asyncio
    async def test_get_open_orders_empty(self, adapter, mock_order_manager):
        """Test getting open orders when none exist."""
        mock_order_manager.get_pending_orders = AsyncMock(return_value=[])

        orders = await adapter.get_open_orders()

        assert orders == []

    @pytest.mark.asyncio
    async def test_get_open_orders_with_orders(self, adapter, mock_order_manager):
        """Test getting open orders with pending orders."""
        pending_order = BrokerOrder(
            order_id="order_123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        mock_order_manager.get_pending_orders = AsyncMock(return_value=[pending_order])

        orders = await adapter.get_open_orders()

        assert len(orders) == 1
        assert orders[0].symbol == "AAPL"
        assert orders[0].quantity == Decimal("100")


class TestCancelAllOrders:
    """Test cancel_all_orders method."""

    @pytest.mark.asyncio
    async def test_cancel_all_orders(self, adapter, mock_order_manager):
        """Test cancelling all orders."""
        # Add some mappings
        adapter._signal_to_order_map["signal_1"] = "order_1"
        adapter._signal_to_order_map["signal_2"] = "order_2"

        mock_order_manager.cancel_all_orders = AsyncMock(return_value=2)

        count = await adapter.cancel_all_orders()

        assert count == 2
        assert len(adapter._signal_to_order_map) == 0  # Mappings cleared


class TestFactoryFunction:
    """Test factory function."""

    def test_get_order_manager_adapter_default(self):
        """Test factory function with defaults."""
        adapter = get_order_manager_adapter()

        assert isinstance(adapter, OrderManagerAdapter)
        assert adapter.enable_logging is False

    def test_get_order_manager_adapter_with_logging(self):
        """Test factory function with logging enabled."""
        adapter = get_order_manager_adapter(enable_logging=True)

        assert isinstance(adapter, OrderManagerAdapter)
        assert adapter.enable_logging is True


class TestHelperMethods:
    """Test helper methods."""

    def test_get_mapping_stats(self, adapter):
        """Test getting mapping statistics."""
        adapter._signal_to_order_map["signal_1"] = "order_1"
        adapter._signal_to_order_map["signal_2"] = "order_2"

        stats = adapter.get_mapping_stats()

        assert stats["total_mappings"] == 2
        assert stats["mappings"]["signal_1"] == "order_1"
        assert stats["mappings"]["signal_2"] == "order_2"

    def test_reset(self, adapter):
        """Test reset method."""
        adapter._signal_to_order_map["signal_1"] = "order_1"

        adapter.reset()

        assert len(adapter._signal_to_order_map) == 0
