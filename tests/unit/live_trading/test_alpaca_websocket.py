"""
Unit tests for Alpaca WebSocket streaming functionality.

Tests real-time quote updates, trade execution, order status updates,
and connection management.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.services.live_trading.broker_adapters.alpaca_client import (
    AlpacaClient,
    AlpacaClientError,
)
from app.services.live_trading.broker_adapters.alpaca_adapter import AlpacaAdapter
from app.services.live_trading.broker_connector import (
    BrokerPosition,
    OrderStatus,
)


@pytest.fixture
def alpaca_client():
    """Create AlpacaClient instance for testing."""
    client = AlpacaClient()
    client.is_authenticated = True
    client.api = MagicMock()
    return client


@pytest.fixture
def alpaca_adapter():
    """Create AlpacaAdapter instance for testing."""
    adapter = AlpacaAdapter()
    adapter.client = AsyncMock()
    adapter.client.is_authenticated = True
    return adapter


class TestAlpacaClientStreamingSetup:
    """Test WebSocket streaming setup and initialization."""

    @pytest.mark.asyncio
    async def test_start_stream_not_authenticated(self):
        """Test that stream start requires authentication."""
        client = AlpacaClient()
        client.is_authenticated = False

        with pytest.raises(AlpacaClientError):
            await client.start_stream()

    @pytest.mark.asyncio
    async def test_start_stream_already_running(self, alpaca_client):
        """Test that stream prevents double start."""
        alpaca_client.is_streaming = True

        await alpaca_client.start_stream()

        # Should return without error, just log warning

    @pytest.mark.asyncio
    async def test_start_stream_initializes_state(self, alpaca_client):
        """Test that start_stream initializes streaming state."""
        alpaca_client.stream_task = AsyncMock()

        with patch.object(asyncio, "create_task", return_value=AsyncMock()):
            await alpaca_client.start_stream(symbols=["AAPL", "TSLA"])

            assert alpaca_client.is_streaming is True
            assert alpaca_client.subscribed_symbols == ["AAPL", "TSLA"]

    @pytest.mark.asyncio
    async def test_start_stream_default_symbols(self, alpaca_client):
        """Test that start_stream defaults to all symbols."""
        with patch.object(asyncio, "create_task", return_value=AsyncMock()):
            await alpaca_client.start_stream()

            assert alpaca_client.subscribed_symbols == ["*"]


class TestAlpacaClientStreamingHandlers:
    """Test WebSocket message handlers."""

    def test_register_quote_handler(self, alpaca_client):
        """Test registering quote handler."""
        mock_handler = MagicMock()

        alpaca_client.register_quote_handler(mock_handler)

        assert alpaca_client.on_quote == mock_handler

    def test_register_trade_handler(self, alpaca_client):
        """Test registering trade handler."""
        mock_handler = MagicMock()

        alpaca_client.register_trade_handler(mock_handler)

        assert alpaca_client.on_trade == mock_handler

    def test_register_order_handler(self, alpaca_client):
        """Test registering order handler."""
        mock_handler = MagicMock()

        alpaca_client.register_order_handler(mock_handler)

        assert alpaca_client.on_order_update == mock_handler

    def test_register_error_handler(self, alpaca_client):
        """Test registering error handler."""
        mock_handler = MagicMock()

        alpaca_client.register_error_handler(mock_handler)

        assert alpaca_client.on_connection_error == mock_handler


class TestAlpacaClientStreamMessageProcessing:
    """Test processing of incoming WebSocket messages."""

    @pytest.mark.asyncio
    async def test_process_quote_message(self, alpaca_client):
        """Test processing quote message."""
        mock_handler = AsyncMock()
        alpaca_client.register_quote_handler(mock_handler)

        quote_data = {
            "T": "q",
            "S": "AAPL",
            "bp": "150.50",
            "ap": "150.60",
            "bs": 100,
            "as": 200,
        }
        message = '{"T": "q", "S": "AAPL", "bp": "150.50", "ap": "150.60"}'

        await alpaca_client._process_stream_message(message)

        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_trade_message(self, alpaca_client):
        """Test processing trade message."""
        mock_handler = AsyncMock()
        alpaca_client.register_trade_handler(mock_handler)

        message = '{"T": "t", "S": "TSLA", "p": "250.00", "s": 100}'

        await alpaca_client._process_stream_message(message)

        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_order_message(self, alpaca_client):
        """Test processing order message."""
        mock_handler = AsyncMock()
        alpaca_client.register_order_handler(mock_handler)

        message = '{"T": "o", "id": "order123", "status": "filled"}'

        await alpaca_client._process_stream_message(message)

        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_error_message(self, alpaca_client):
        """Test processing error message."""
        message = '{"T": "error", "msg": "Invalid symbol"}'

        # Should not raise, just log
        await alpaca_client._process_stream_message(message)

    @pytest.mark.asyncio
    async def test_process_invalid_json(self, alpaca_client):
        """Test handling of invalid JSON."""
        message = "invalid json"

        # Should not raise, just log warning
        await alpaca_client._process_stream_message(message)


class TestAlpacaClientStreamingURL:
    """Test WebSocket URL determination."""

    def test_paper_trading_url(self, alpaca_client):
        """Test WebSocket URL for paper trading."""
        alpaca_client.base_url = "https://paper-api.alpaca.markets"

        url = alpaca_client._get_stream_url()

        assert url == "wss://data.sandbox.alpaca.markets/stream"

    def test_live_trading_url(self, alpaca_client):
        """Test WebSocket URL for live trading."""
        alpaca_client.base_url = "https://api.alpaca.markets"

        url = alpaca_client._get_stream_url()

        assert url == "wss://data.alpaca.markets/stream"


class TestAlpacaClientStreamingStoppage:
    """Test WebSocket stream stopping."""

    @pytest.mark.asyncio
    async def test_stop_stream_not_running(self, alpaca_client):
        """Test stopping stream when not running."""
        alpaca_client.is_streaming = False

        result = await alpaca_client.stop_stream()

        # Should return without error

    @pytest.mark.asyncio
    async def test_stop_stream_closes_socket(self, alpaca_client):
        """Test that stop_stream closes socket."""
        mock_socket = AsyncMock()
        alpaca_client.stream_socket = mock_socket
        alpaca_client.is_streaming = True

        mock_task = AsyncMock()
        alpaca_client.stream_task = mock_task

        await alpaca_client.stop_stream()

        assert alpaca_client.is_streaming is False
        mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_stream_cancels_task(self, alpaca_client):
        """Test that stop_stream cancels task."""
        alpaca_client.is_streaming = True

        mock_task = AsyncMock()
        mock_task.cancel = MagicMock()
        alpaca_client.stream_task = mock_task

        await alpaca_client.stop_stream()

        mock_task.cancel.assert_called_once()


class TestAlpacaAdapterQuoteUpdates:
    """Test AlpacaAdapter handling of real-time quote updates."""

    def test_on_quote_update_updates_position_price(self, alpaca_adapter):
        """Test that quote update changes position price."""
        # Set up a position
        alpaca_adapter.positions["AAPL"] = BrokerPosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            current_price=Decimal("150.00"),
            market_value=Decimal("15000.00"),
            unrealized_pl=Decimal("0"),
            unrealized_pl_pct=Decimal("0"),
        )

        quote_data = {
            "S": "AAPL",
            "bp": "152.00",
            "ap": "152.10",
        }

        alpaca_adapter._on_quote_update(quote_data)

        # Price should be updated to midpoint
        assert alpaca_adapter.positions["AAPL"].current_price == Decimal("152.05")

    def test_on_quote_update_recalculates_pl(self, alpaca_adapter):
        """Test that quote update recalculates P&L."""
        alpaca_adapter.positions["TSLA"] = BrokerPosition(
            symbol="TSLA",
            quantity=Decimal("50"),
            avg_price=Decimal("800.00"),
            current_price=Decimal("800.00"),
            market_value=Decimal("40000.00"),
            unrealized_pl=Decimal("0"),
            unrealized_pl_pct=Decimal("0"),
        )

        quote_data = {
            "S": "TSLA",
            "bp": "850.00",
            "ap": "850.10",
        }

        alpaca_adapter._on_quote_update(quote_data)

        pos = alpaca_adapter.positions["TSLA"]
        # market_value = 50 * 850.05 = 42502.5
        assert pos.market_value == Decimal("42502.50")
        # unrealized_pl = (850.05 - 800) * 50 = 2502.5
        assert pos.unrealized_pl == Decimal("2502.50")

    def test_on_quote_update_ignores_unknown_symbol(self, alpaca_adapter):
        """Test that quote update ignores unknown symbols."""
        alpaca_adapter.positions = {}

        quote_data = {
            "S": "UNKNOWN",
            "bp": "100.00",
            "ap": "100.10",
        }

        # Should not raise
        alpaca_adapter._on_quote_update(quote_data)

        assert len(alpaca_adapter.positions) == 0


class TestAlpacaAdapterTradeUpdates:
    """Test AlpacaAdapter handling of trade execution updates."""

    def test_on_trade_update_logs_execution(self, alpaca_adapter):
        """Test that trade update logs execution."""
        trade_data = {
            "S": "AAPL",
            "p": "151.50",
            "s": "100",
        }

        # Should not raise
        alpaca_adapter._on_trade_update(trade_data)


class TestAlpacaAdapterOrderUpdates:
    """Test AlpacaAdapter handling of real-time order updates."""

    def test_on_order_update_updates_status(self, alpaca_adapter):
        """Test that order update changes order status."""
        from app.services.live_trading.broker_connector import BrokerOrder, OrderSide

        # Create a pending order
        order = BrokerOrder(
            order_id="order123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type="market",
            quantity=Decimal("100"),
            status=OrderStatus.SUBMITTED,
        )
        alpaca_adapter.orders["order123"] = order

        order_data = {
            "id": "order123",
            "status": "filled",
            "filled_qty": "100",
            "filled_avg_price": "151.50",
        }

        alpaca_adapter._on_order_update(order_data)

        assert alpaca_adapter.orders["order123"].status == OrderStatus.FILLED
        assert alpaca_adapter.orders["order123"].filled_quantity == Decimal("100")
        assert alpaca_adapter.orders["order123"].avg_filled_price == Decimal("151.50")

    def test_on_order_update_ignores_unknown_order(self, alpaca_adapter):
        """Test that order update ignores unknown orders."""
        alpaca_adapter.orders = {}

        order_data = {
            "id": "unknown",
            "status": "filled",
        }

        # Should not raise
        alpaca_adapter._on_order_update(order_data)


class TestAlpacaAdapterErrorHandling:
    """Test error handling in streaming."""

    def test_on_stream_error_logs_error(self, alpaca_adapter):
        """Test that stream error is logged."""
        error = Exception("Connection lost")

        # Should not raise
        alpaca_adapter._on_stream_error(error)


class TestAlpacaAdapterStreamingIntegration:
    """Test streaming integration in adapter."""

    @pytest.mark.asyncio
    async def test_connect_registers_handlers(self, alpaca_adapter):
        """Test that connect() registers streaming handlers."""
        mock_account = {
            "account_number": "PA123456",
            "cash": 100000.00,
            "portfolio_value": 150000.00,
            "buying_power": 200000.00,
            "equity": 150000.00,
            "multiplier": 1.0,
        }

        alpaca_adapter.client.authenticate = AsyncMock(return_value=True)
        alpaca_adapter.client.get_account = AsyncMock(return_value=mock_account)
        alpaca_adapter.client.get_positions = AsyncMock(return_value=[])
        alpaca_adapter.client.start_stream = AsyncMock(return_value=None)

        result = await alpaca_adapter.connect(
            api_key="test",
            api_secret="test",
        )

        assert result is True
        alpaca_adapter.client.start_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_stops_stream(self, alpaca_adapter):
        """Test that disconnect() stops stream."""
        alpaca_adapter.client.stop_stream = AsyncMock(return_value=None)
        alpaca_adapter.is_connected = True

        result = await alpaca_adapter.disconnect()

        assert result is True
        alpaca_adapter.client.stop_stream.assert_called_once()
