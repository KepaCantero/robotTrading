"""
Unit tests for TradingBridgeAdapter.

Tests the integration between TradingBridgeOrchestrator and ITradeExecutor protocol.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.execution.trading_bridge_adapter import (
    TradingBridgeAdapter,
    get_trading_bridge_adapter,
)
from app.services.live_trading.broker_connector import OrderSide, OrderStatus


@pytest.fixture
def mock_trading_bridge():
    """Create a mock TradingBridgeOrchestrator."""
    bridge = MagicMock()
    bridge.broker = MagicMock()

    # Mock process_alert
    execution = MagicMock()
    execution.order_id = "broker_order_123"
    execution.execution_id = "exec_abc123"
    execution.symbol = "AAPL"
    execution.side = OrderSide.BUY
    execution.quantity = Decimal("100")
    execution.execution_price = Decimal("150.25")
    execution.execution_status = OrderStatus.FILLED

    bridge.process_alert = AsyncMock(return_value=execution)

    # Mock broker methods
    bridge.broker.cancel_order = AsyncMock(return_value=True)
    bridge.broker.modify_order = AsyncMock(return_value=True)
    bridge.broker.get_order_status = AsyncMock(return_value=OrderStatus.FILLED)
    bridge.broker.get_open_orders = AsyncMock(return_value=[])

    # Mock other methods
    bridge.get_recent_executions = MagicMock(return_value=[])
    bridge.get_bridge_statistics = MagicMock(
        return_value={"status": "monitoring", "total_executions": 1}
    )

    return bridge


@pytest.fixture
def adapter(mock_trading_bridge):
    """Create TradingBridgeAdapter with mock trading bridge."""
    return TradingBridgeAdapter(trading_bridge=mock_trading_bridge)


@pytest.fixture
def mock_signal():
    """Create a mock TradeSignal."""
    signal = MagicMock()
    signal.symbol = "AAPL"
    signal.order_side = OrderSide.BUY
    signal.quantity = Decimal("100")
    signal.price = Decimal("150")
    signal.signal_id = "signal_123"
    return signal


class TestTradingBridgeAdapter:
    """Test suite for TradingBridgeAdapter."""

    @pytest.mark.asyncio
    async def test_execute_order_success(self, adapter, mock_signal):
        """Test successful order execution."""
        result = await adapter.execute_order(mock_signal)

        assert result.success is True
        assert result.order_id == "broker_order_123"
        assert result.symbol == "AAPL"
        assert result.side == "buy"  # OrderSide.BUY.value returns lowercase
        assert result.quantity == Decimal("100")
        assert result.execution_price == Decimal("150.25")
        assert result.status == "filled"  # OrderStatus.FILLED.value returns lowercase

    @pytest.mark.asyncio
    async def test_execute_order_failure_no_execution(
        self, mock_trading_bridge, mock_signal
    ):
        """Test order execution when trading bridge returns None."""
        mock_trading_bridge.process_alert = AsyncMock(return_value=None)
        adapter = TradingBridgeAdapter(trading_bridge=mock_trading_bridge)

        result = await adapter.execute_order(mock_signal)

        assert result.success is False
        assert result.status == "FAILED"
        assert "did not return execution" in result.error

    @pytest.mark.asyncio
    async def test_execute_order_exception(self, mock_trading_bridge, mock_signal):
        """Test order execution when exception occurs."""
        mock_trading_bridge.process_alert = AsyncMock(side_effect=Exception("Bridge error"))
        adapter = TradingBridgeAdapter(trading_bridge=mock_trading_bridge)

        result = await adapter.execute_order(mock_signal)

        assert result.success is False
        assert result.status == "FAILED"
        assert "Bridge error" in result.error

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter):
        """Test successful order cancellation."""
        result = await adapter.cancel_order("order_123")

        assert result is True
        adapter.trading_bridge.broker.cancel_order.assert_called_once_with("order_123")

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, adapter):
        """Test order cancellation when it fails."""
        adapter.trading_bridge.broker.cancel_order = AsyncMock(return_value=False)

        result = await adapter.cancel_order("order_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_modify_order_success(self, adapter):
        """Test successful order modification."""
        result = await adapter.modify_order("order_123", Decimal("155"))

        assert result is True
        adapter.trading_bridge.broker.modify_order.assert_called_once_with(
            "order_123", Decimal("155")
        )

    @pytest.mark.asyncio
    async def test_get_order_status(self, adapter):
        """Test getting order status."""
        result = await adapter.get_order_status("order_123")

        assert result == "filled"  # OrderStatus.FILLED.value returns lowercase
        adapter.trading_bridge.broker.get_order_status.assert_called_once_with(
            "order_123"
        )

    @pytest.mark.asyncio
    async def test_get_open_orders(self, adapter):
        """Test getting open orders."""
        adapter.trading_bridge.broker.get_open_orders = AsyncMock(
            return_value=["order1", "order2"]
        )

        result = await adapter.get_open_orders()

        assert result == ["order1", "order2"]

    def test_get_execution_history(self, adapter):
        """Test getting execution history."""
        adapter.trading_bridge.get_recent_executions.return_value = [
            "exec1",
            "exec2",
        ]

        result = adapter.get_execution_history()

        assert result == ["exec1", "exec2"]
        adapter.trading_bridge.get_recent_executions.assert_called_once_with(
            limit=100
        )

    def test_get_bridge_statistics(self, adapter):
        """Test getting bridge statistics."""
        result = adapter.get_bridge_statistics()

        assert result["total_executions"] == 1
        adapter.trading_bridge.get_bridge_statistics.assert_called_once()

    def test_order_mapping(self, adapter):
        """Test that order IDs are mapped to execution IDs."""
        # The mapping is done internally during execute_order
        # This test verifies the mapping dictionary exists
        assert hasattr(adapter, "_order_mapping")
        assert isinstance(adapter._order_mapping, dict)

    @pytest.mark.asyncio
    async def test_order_mapping_populated_on_execution(self, adapter, mock_signal):
        """Test that order mapping is populated after execution."""
        await adapter.execute_order(mock_signal)

        assert "broker_order_123" in adapter._order_mapping
        assert adapter._order_mapping["broker_order_123"] == "exec_abc123"


class TestTradingBridgeAdapterFactory:
    """Test suite for TradingBridgeAdapter factory function."""

    def test_get_trading_bridge_adapter_default(self):
        """Test factory function with default parameters."""
        with patch(
            "app.services.execution.trading_bridge_adapter.get_trading_bridge_orchestrator"
        ) as mock_get:
            mock_bridge = MagicMock()
            mock_get.return_value = mock_bridge

            adapter = get_trading_bridge_adapter()

            assert isinstance(adapter, TradingBridgeAdapter)
            assert adapter.trading_bridge == mock_bridge
            assert adapter.enable_logging is False

    def test_get_trading_bridge_adapter_with_logging(self):
        """Test factory function with logging enabled."""
        with patch(
            "app.services.execution.trading_bridge_adapter.get_trading_bridge_orchestrator"
        ) as mock_get:
            mock_bridge = MagicMock()
            mock_get.return_value = mock_bridge

            adapter = get_trading_bridge_adapter(enable_logging=True)

            assert isinstance(adapter, TradingBridgeAdapter)
            assert adapter.enable_logging is True
