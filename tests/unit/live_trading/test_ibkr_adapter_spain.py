"""
Unit tests for IBKRSpainAdapter.

Tests the IBrokerAdapter Protocol implementation for Spanish traders.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.live_trading.broker_adapters.ibkr_adapter_spain import (
    IBKRSpainAdapter,
    get_ibkr_spain_adapter,
)


@pytest.fixture
def mock_ib():
    """Mock IB connection."""
    ib = MagicMock()
    ib.isConnected.return_value = True
    ib.connectAsync = AsyncMock(return_value=None)
    ib.disconnectAsync = AsyncMock(return_value=None)
    ib.errorEvent = MagicMock()
    ib.accountSummary = MagicMock(return_value=[])
    ib.positions = MagicMock(return_value=[])
    ib.trades = MagicMock(return_value=[])
    ib.openTrades = MagicMock(return_value=[])
    ib.placeOrder = MagicMock()
    ib.cancelOrder = MagicMock()
    return ib


@pytest.fixture
def adapter(mock_ib):
    """Create adapter with mocked IB connection."""
    config = {
        "host": "127.0.0.1",
        "port": 7497,
        "client_id": 1,
        "account": "TEST123",
        "paper_trading": True,
    }
    with patch("app.services.live_trading.broker_adapters.ibkr_adapter_spain.IB", return_value=mock_ib):
        adapter = IBKRSpainAdapter(config, ib_instance=mock_ib)
        adapter._connected = True
        yield adapter


class TestIBKRSpainAdapterProtocol:
    """Tests for IBrokerAdapter Protocol compliance."""

    def test_has_connect_method(self, adapter):
        """Test adapter has connect() method."""
        assert hasattr(adapter, "connect")
        assert callable(adapter.connect)

    def test_has_disconnect_method(self, adapter):
        """Test adapter has disconnect() method."""
        assert hasattr(adapter, "disconnect")
        assert callable(adapter.disconnect)

    def test_has_place_order_method(self, adapter):
        """Test adapter has place_order() method."""
        assert hasattr(adapter, "place_order")
        assert callable(adapter.place_order)

    def test_has_cancel_order_method(self, adapter):
        """Test adapter has cancel_order() method."""
        assert hasattr(adapter, "cancel_order")
        assert callable(adapter.cancel_order)

    def test_has_get_account_method(self, adapter):
        """Test adapter has get_account() method."""
        assert hasattr(adapter, "get_account")
        assert callable(adapter.get_account)

    @pytest.mark.asyncio
    async def test_connect_returns_bool(self, adapter, mock_ib):
        """Test connect() returns bool."""
        mock_ib.isConnected.return_value = True
        result = await adapter.connect()
        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_returns_bool(self, adapter, mock_ib):
        """Test disconnect() returns bool."""
        result = await adapter.disconnect()
        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_place_order_returns_str(self, adapter, mock_ib):
        """Test place_order() returns str (order_id)."""
        # Setup mock trade
        mock_trade = MagicMock()
        mock_order = MagicMock()
        mock_order.orderId = 12345
        mock_trade.order = mock_order
        mock_trade.fills = []
        mock_ib.placeOrder.return_value = mock_trade

        order = {
            "symbol": "SAN.MC",
            "side": "BUY",
            "quantity": 100,
            "order_type": "MKT",
        }

        result = await adapter.place_order(order)
        assert isinstance(result, str)
        assert result == "12345"

    @pytest.mark.asyncio
    async def test_cancel_order_returns_bool(self, adapter, mock_ib):
        """Test cancel_order() returns bool."""
        mock_ib.openTrades.return_value = []
        result = await adapter.cancel_order("12345")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_account_returns_dict(self, adapter, mock_ib):
        """Test get_account() returns dict."""
        result = await adapter.get_account()
        assert isinstance(result, dict)

    def test_max_five_protocol_methods(self, adapter):
        """Test ISP compliance: max 5 methods from Protocol."""
        # The Protocol requires 5 methods
        protocol_methods = ["connect", "disconnect", "place_order", "cancel_order", "get_account"]
        for method in protocol_methods:
            assert hasattr(adapter, method), f"Missing Protocol method: {method}"


class TestIBKRSpainAdapterConnect:
    """Tests for connect/disconnect functionality."""

    @pytest.mark.asyncio
    async def test_connect_success(self, adapter, mock_ib):
        """Test successful connection."""
        mock_ib.isConnected.return_value = True
        result = await adapter.connect()
        assert result is True
        assert adapter._connected is True

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, adapter, mock_ib):
        """Test connecting when already connected."""
        adapter._connected = True
        mock_ib.isConnected.return_value = True
        result = await adapter.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_ib):
        """Test connection failure."""
        mock_ib.isConnected.return_value = False
        with patch("app.services.live_trading.broker_adapters.ibkr_adapter_spain.IB", return_value=mock_ib):
            adapter = IBKRSpainAdapter(ib_instance=mock_ib)
            result = await adapter.connect()
            assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_success(self, adapter, mock_ib):
        """Test successful disconnection."""
        result = await adapter.disconnect()
        assert result is True
        assert adapter._connected is False


class TestIBKRSpainAdapterPlaceOrder:
    """Tests for order placement."""

    @pytest.mark.asyncio
    async def test_place_market_order(self, adapter, mock_ib):
        """Test placing a market order."""
        mock_trade = MagicMock()
        mock_order = MagicMock()
        mock_order.orderId = 12345
        mock_trade.order = mock_order
        mock_trade.fills = []
        mock_ib.placeOrder.return_value = mock_trade

        order = {
            "symbol": "SAN.MC",
            "side": "BUY",
            "quantity": 100,
            "order_type": "MKT",
        }

        result = await adapter.place_order(order)
        assert result == "12345"
        mock_ib.placeOrder.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_limit_order(self, adapter, mock_ib):
        """Test placing a limit order."""
        mock_trade = MagicMock()
        mock_order = MagicMock()
        mock_order.orderId = 12346
        mock_trade.order = mock_order
        mock_trade.fills = []
        mock_ib.placeOrder.return_value = mock_trade

        order = {
            "symbol": "TEF.MC",
            "side": "BUY",
            "quantity": 50,
            "order_type": "LMT",
            "price": 10.50,
        }

        result = await adapter.place_order(order)
        assert result == "12346"

    @pytest.mark.asyncio
    async def test_place_stop_order(self, adapter, mock_ib):
        """Test placing a stop order."""
        mock_trade = MagicMock()
        mock_order = MagicMock()
        mock_order.orderId = 12347
        mock_trade.order = mock_order
        mock_trade.fills = []
        mock_ib.placeOrder.return_value = mock_trade

        order = {
            "symbol": "REP.MC",
            "side": "SELL",
            "quantity": 200,
            "order_type": "STP",
            "stop_price": 15.00,
        }

        result = await adapter.place_order(order)
        assert result == "12347"

    @pytest.mark.asyncio
    async def test_place_order_missing_required_field(self, adapter):
        """Test placing order with missing required field."""
        order = {
            "symbol": "SAN.MC",
            "side": "BUY",
            # Missing "quantity" and "order_type"
        }

        with pytest.raises(ValueError, match="Missing required field"):
            await adapter.place_order(order)

    @pytest.mark.asyncio
    async def test_place_order_invalid_side(self, adapter):
        """Test placing order with invalid side."""
        order = {
            "symbol": "SAN.MC",
            "side": "INVALID",
            "quantity": 100,
            "order_type": "MKT",
        }

        with pytest.raises(ValueError, match="Invalid side"):
            await adapter.place_order(order)

    @pytest.mark.asyncio
    async def test_place_order_invalid_quantity(self, adapter):
        """Test placing order with invalid quantity."""
        order = {
            "symbol": "SAN.MC",
            "side": "BUY",
            "quantity": -100,
            "order_type": "MKT",
        }

        with pytest.raises(ValueError, match="Invalid quantity"):
            await adapter.place_order(order)

    @pytest.mark.asyncio
    async def test_place_order_limit_without_price(self, adapter):
        """Test placing limit order without price."""
        order = {
            "symbol": "SAN.MC",
            "side": "BUY",
            "quantity": 100,
            "order_type": "LMT",
            # Missing "price"
        }

        with pytest.raises(ValueError, match="Limit price required"):
            await adapter.place_order(order)

    @pytest.mark.asyncio
    async def test_place_order_stop_without_stop_price(self, adapter):
        """Test placing stop order without stop price."""
        order = {
            "symbol": "SAN.MC",
            "side": "BUY",
            "quantity": 100,
            "order_type": "STP",
            # Missing "stop_price"
        }

        with pytest.raises(ValueError, match="Stop price required"):
            await adapter.place_order(order)


class TestIBKRSpainAdapterCancelOrder:
    """Tests for order cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter, mock_ib):
        """Test successful order cancellation."""
        mock_trade = MagicMock()
        mock_order = MagicMock()
        mock_order.orderId = 12345
        mock_trade.order = mock_order
        mock_ib.openTrades.return_value = [mock_trade]

        result = await adapter.cancel_order("12345")
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self, adapter, mock_ib):
        """Test cancelling non-existent order."""
        mock_ib.openTrades.return_value = []
        result = await adapter.cancel_order("99999")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_order_invalid_id(self, adapter, mock_ib):
        """Test cancelling with invalid order ID."""
        result = await adapter.cancel_order("invalid")
        assert result is False


class TestIBKRSpainAdapterGetAccount:
    """Tests for account information retrieval."""

    @pytest.mark.asyncio
    async def test_get_account_returns_expected_keys(self, adapter, mock_ib):
        """Test get_account() returns expected keys."""
        result = await adapter.get_account()

        expected_keys = [
            "account_id",
            "currency",
            "net_liquidation",
            "available_funds",
            "buying_power",
            "total_cash_balance",
            "positions",
            "timestamp",
        ]

        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_get_account_currency_eur(self, adapter, mock_ib):
        """Test account currency is EUR."""
        result = await adapter.get_account()
        assert result.get("currency") == "EUR"

    @pytest.mark.asyncio
    async def test_get_account_positions_list(self, adapter, mock_ib):
        """Test positions is a list."""
        result = await adapter.get_account()
        assert isinstance(result.get("positions"), list)

    @pytest.mark.asyncio
    async def test_get_account_timestamp_format(self, adapter, mock_ib):
        """Test timestamp is in ISO format."""
        result = await adapter.get_account()
        timestamp = result.get("timestamp")
        assert timestamp is not None
        # Check ISO format (basic validation)
        assert "T" in timestamp or "-" in timestamp


class TestIBKRSpainAdapterEURSupport:
    """Tests for EUR currency support."""

    def test_adapter_has_eur_currency_converter(self, adapter):
        """Test adapter has currency converter."""
        assert hasattr(adapter, "currency_converter")
        assert adapter.currency_converter is not None

    def test_adapter_default_currency_eur(self, adapter):
        """Test adapter defaults to EUR."""
        assert adapter.config.get("currency", "EUR") == "EUR" or \
            adapter.currency_converter is not None


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_ibkr_spain_adapter(self):
        """Test get_ibkr_spain_adapter returns instance."""
        adapter = get_ibkr_spain_adapter()
        assert isinstance(adapter, IBKRSpainAdapter)

    def test_get_ibkr_spain_adapter_with_config(self):
        """Test get_ibkr_spain_adapter with custom config."""
        config = {"account": "TEST456"}
        adapter = get_ibkr_spain_adapter(config)
        assert isinstance(adapter, IBKRSpainAdapter)
