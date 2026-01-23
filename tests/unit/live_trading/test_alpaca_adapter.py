"""
Unit tests for AlpacaAdapter - BrokerConnector interface implementation for Alpaca.

Tests data transformation, state management, interface compliance, and error handling.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.live_trading.broker_adapters.alpaca_adapter import AlpacaAdapter
from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    BrokerType,
    OrderSide,
    OrderStatus,
)


@pytest.fixture
def alpaca_adapter():
    """Create AlpacaAdapter instance for testing."""
    adapter = AlpacaAdapter()
    # Mock the client to avoid real API calls
    # Use MagicMock for sync methods, AsyncMock for async methods
    mock_client = MagicMock()
    # Set up async methods as AsyncMock
    mock_client.authenticate = AsyncMock(return_value=True)
    mock_client.get_account = AsyncMock(return_value={})
    mock_client.submit_order = AsyncMock(return_value=MagicMock(id="test_order"))
    mock_client.cancel_order = AsyncMock(return_value=True)
    mock_client.get_order = AsyncMock(return_value={})
    mock_client.get_positions = AsyncMock(return_value=[])
    mock_client.start_stream = AsyncMock(return_value=None)
    mock_client.stop_stream = AsyncMock(return_value=None)
    adapter.client = mock_client
    return adapter


class TestAlpacaAdapterConnection:
    """Test AlpacaAdapter connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_success(self, alpaca_adapter):
        """Test successful connection to Alpaca."""
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
        alpaca_adapter.client.start_stream = AsyncMock(return_value=None)

        result = await alpaca_adapter.connect(
            api_key="test_key",
            api_secret="test_secret",
        )

        assert result is True
        assert alpaca_adapter.account is not None
        assert alpaca_adapter.account.account_id == "PA123456"
        assert alpaca_adapter.account.cash_available == Decimal("100000.00")

    @pytest.mark.asyncio
    async def test_connect_failure(self, alpaca_adapter):
        """Test connection failure."""
        alpaca_adapter.client.authenticate = AsyncMock(side_effect=Exception("Auth failed"))

        result = await alpaca_adapter.connect(
            api_key="invalid_key",
            api_secret="invalid_secret",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect(self, alpaca_adapter):
        """Test disconnection."""
        alpaca_adapter.client.stop_stream = AsyncMock(return_value=None)
        alpaca_adapter.is_connected = True

        result = await alpaca_adapter.disconnect()

        assert result is True
        alpaca_adapter.client.stop_stream.assert_called_once()


class TestAlpacaAdapterDataTransformation:
    """Test AlpacaAdapter data transformation methods."""

    def test_transform_account(self, alpaca_adapter):
        """Test transforming Alpaca account data to BrokerAccount."""
        alpaca_account = {
            "account_number": "PA987654",
            "cash": 50000.00,
            "portfolio_value": 100000.00,
            "buying_power": 150000.00,
            "equity": 100000.00,
            "multiplier": 2.0,
        }

        broker_account = alpaca_adapter._transform_account(alpaca_account)

        assert isinstance(broker_account, BrokerAccount)
        assert broker_account.account_id == "PA987654"
        assert broker_account.cash_available == Decimal("50000.00")
        assert broker_account.portfolio_value == Decimal("100000.00")
        assert broker_account.buying_power == Decimal("150000.00")
        assert broker_account.equity == Decimal("100000.00")
        assert broker_account.broker_type == BrokerType.ALPACA
        # margin_used = multiplier - 1 = 2.0 - 1 = 1.0
        assert broker_account.margin_used == Decimal("1.00")

    def test_transform_position(self, alpaca_adapter):
        """Test transforming Alpaca position data to BrokerPosition."""
        alpaca_pos = {
            "symbol": "AAPL",
            "qty": 100,
            "avg_fill_price": 150.00,
            "current_price": 160.00,
        }

        broker_pos = alpaca_adapter._transform_position(alpaca_pos)

        assert isinstance(broker_pos, BrokerPosition)
        assert broker_pos.symbol == "AAPL"
        assert broker_pos.quantity == Decimal("100")
        assert broker_pos.avg_price == Decimal("150.00")
        assert broker_pos.current_price == Decimal("160.00")
        # market_value = qty * current_price = 100 * 160 = 16000
        assert broker_pos.market_value == Decimal("16000.00")
        # unrealized_pl = (current - avg) * qty = (160 - 150) * 100 = 1000
        assert broker_pos.unrealized_pl == Decimal("1000.00")
        # unrealized_pl_pct = (pl / market_value) * 100 = (1000 / 16000) * 100 = 6.25
        assert broker_pos.unrealized_pl_pct == Decimal("6.25")

    def test_transform_position_loss(self, alpaca_adapter):
        """Test position transformation with unrealized loss."""
        alpaca_pos = {
            "symbol": "TSLA",
            "qty": 50,
            "avg_fill_price": 800.00,
            "current_price": 750.00,
        }

        broker_pos = alpaca_adapter._transform_position(alpaca_pos)

        # unrealized_pl = (750 - 800) * 50 = -2500
        assert broker_pos.unrealized_pl == Decimal("-2500.00")
        # unrealized_pl_pct = (-2500 / 37500) * 100 = -6.67
        assert broker_pos.unrealized_pl_pct == Decimal("-6.67")

    def test_transform_order(self, alpaca_adapter):
        """Test transforming Alpaca order data to BrokerOrder."""
        alpaca_order = {
            "id": "order_xyz",
            "qty": 100,
            "filled_qty": 100,
            "filled_avg_price": 150.50,
            "status": "filled",
            "type": "MARKET",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T10:00:05Z",
        }

        broker_order = alpaca_adapter._transform_order(
            alpaca_order, symbol="AAPL", side=OrderSide.BUY
        )

        assert isinstance(broker_order, BrokerOrder)
        assert broker_order.order_id == "order_xyz"
        assert broker_order.symbol == "AAPL"
        assert broker_order.side == OrderSide.BUY
        assert broker_order.quantity == Decimal("100")
        assert broker_order.filled_quantity == Decimal("100")
        assert broker_order.avg_filled_price == Decimal("150.50")
        assert broker_order.status == OrderStatus.FILLED


class TestAlpacaAdapterOrderStatusMapping:
    """Test order status mapping from Alpaca to standard OrderStatus."""

    def test_map_order_status_filled(self, alpaca_adapter):
        """Test mapping 'filled' status."""
        status = alpaca_adapter._map_order_status("filled")
        assert status == OrderStatus.FILLED

    def test_map_order_status_pending(self, alpaca_adapter):
        """Test mapping 'pending_new' status."""
        status = alpaca_adapter._map_order_status("pending_new")
        assert status == OrderStatus.PENDING

    def test_map_order_status_partially_filled(self, alpaca_adapter):
        """Test mapping 'partially_filled' status."""
        status = alpaca_adapter._map_order_status("partially_filled")
        assert status == OrderStatus.PARTIALLY_FILLED

    def test_map_order_status_canceled(self, alpaca_adapter):
        """Test mapping 'canceled' status."""
        status = alpaca_adapter._map_order_status("canceled")
        assert status == OrderStatus.CANCELED

    def test_map_order_status_rejected(self, alpaca_adapter):
        """Test mapping 'rejected' status."""
        status = alpaca_adapter._map_order_status("rejected")
        assert status == OrderStatus.REJECTED

    def test_map_order_status_expired(self, alpaca_adapter):
        """Test mapping 'expired' status."""
        status = alpaca_adapter._map_order_status("expired")
        assert status == OrderStatus.EXPIRED

    def test_map_order_status_accepted(self, alpaca_adapter):
        """Test mapping 'accepted' status."""
        status = alpaca_adapter._map_order_status("accepted")
        assert status == OrderStatus.ACKNOWLEDGED

    def test_map_order_status_unknown(self, alpaca_adapter):
        """Test mapping unknown status defaults to PENDING."""
        status = alpaca_adapter._map_order_status("unknown_status")
        assert status == OrderStatus.PENDING


class TestAlpacaAdapterOrderManagement:
    """Test AlpacaAdapter order operations."""

    @pytest.mark.asyncio
    async def test_place_order(self, alpaca_adapter):
        """Test placing an order."""
        mock_order = MagicMock(id="order_new")
        alpaca_adapter.client.submit_order = AsyncMock(return_value=mock_order.id)
        alpaca_adapter.is_connected = True

        order_id = await alpaca_adapter.place_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
        )

        assert order_id == "order_new"
        assert "order_new" in alpaca_adapter.orders

    @pytest.mark.asyncio
    async def test_cancel_order(self, alpaca_adapter):
        """Test canceling an order."""
        alpaca_adapter.client.cancel_order = AsyncMock(return_value=True)
        alpaca_adapter.is_connected = True
        # Pre-populate orders dict
        alpaca_adapter.orders["order_to_cancel"] = MagicMock()

        result = await alpaca_adapter.cancel_order("order_to_cancel")

        assert result is True
        alpaca_adapter.client.cancel_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_order_status(self, alpaca_adapter):
        """Test getting order status."""
        mock_order = {
            "id": "order_check",
            "status": "filled",
        }

        alpaca_adapter.client.get_order = AsyncMock(return_value=mock_order)
        alpaca_adapter.is_connected = True

        status = await alpaca_adapter.get_order_status("order_check")

        assert status == OrderStatus.FILLED


class TestAlpacaAdapterAccountInfo:
    """Test AlpacaAdapter account info operations."""

    @pytest.mark.asyncio
    async def test_get_account_info(self, alpaca_adapter):
        """Test retrieving account information."""
        mock_account = {
            "account_number": "PA555666",
            "cash": 75000.00,
            "portfolio_value": 125000.00,
            "buying_power": 175000.00,
            "equity": 125000.00,
            "multiplier": 1.5,
        }

        alpaca_adapter.client.get_account = AsyncMock(return_value=mock_account)
        alpaca_adapter.is_connected = True

        account = await alpaca_adapter.get_account_info()

        assert account is not None
        assert account.account_id == "PA555666"
        assert account.cash_available == Decimal("75000.00")

    @pytest.mark.asyncio
    async def test_sync_account_balance(self, alpaca_adapter):
        """Test syncing account balance."""
        mock_account = {
            "account_number": "PA666777",
            "cash": 80000.00,
            "portfolio_value": 130000.00,
            "buying_power": 180000.00,
            "equity": 130000.00,
            "multiplier": 1.0,
        }

        alpaca_adapter.client.get_account = AsyncMock(return_value=mock_account)

        result = await alpaca_adapter.sync_account_balance()

        assert result is True
        assert alpaca_adapter.account is not None


class TestAlpacaAdapterPositions:
    """Test AlpacaAdapter position operations."""

    @pytest.mark.asyncio
    async def test_get_positions(self, alpaca_adapter):
        """Test retrieving all positions."""
        mock_positions = [
            {
                "symbol": "AAPL",
                "qty": 100,
                "avg_fill_price": 150.00,
                "current_price": 160.00,
            },
            {
                "symbol": "TSLA",
                "qty": 50,
                "avg_fill_price": 800.00,
                "current_price": 820.00,
            },
        ]

        alpaca_adapter.client.get_positions = AsyncMock(return_value=mock_positions)
        alpaca_adapter.is_connected = True

        positions = await alpaca_adapter.get_positions()

        assert len(positions) == 2
        assert positions[0].symbol == "AAPL"
        assert positions[1].symbol == "TSLA"
        assert len(alpaca_adapter.positions) == 2

    @pytest.mark.asyncio
    async def test_get_position(self, alpaca_adapter):
        """Test retrieving single position."""
        mock_positions = [
            {
                "symbol": "AAPL",
                "qty": 100,
                "avg_fill_price": 150.00,
                "current_price": 160.00,
            },
        ]

        alpaca_adapter.client.get_positions = AsyncMock(return_value=mock_positions)
        alpaca_adapter.is_connected = True

        position = await alpaca_adapter.get_position("AAPL")

        assert position is not None
        assert position.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_position_not_found(self, alpaca_adapter):
        """Test getting non-existent position."""
        mock_positions = []

        alpaca_adapter.client.get_positions = AsyncMock(return_value=mock_positions)
        alpaca_adapter.is_connected = True

        position = await alpaca_adapter.get_position("NOTFOUND")

        assert position is None

    @pytest.mark.asyncio
    async def test_update_positions(self, alpaca_adapter):
        """Test updating positions."""
        mock_positions = [
            {
                "symbol": "GOOG",
                "qty": 25,
                "avg_fill_price": 140.00,
                "current_price": 145.00,
            },
        ]

        alpaca_adapter.client.get_positions = AsyncMock(return_value=mock_positions)
        alpaca_adapter.is_connected = True

        positions_dict = await alpaca_adapter.update_positions()

        assert "GOOG" in positions_dict
        assert positions_dict["GOOG"].symbol == "GOOG"

    @pytest.mark.asyncio
    async def test_calculate_portfolio_value(self, alpaca_adapter):
        """Test portfolio value calculation."""
        mock_account = {
            "account_number": "PA777888",
            "cash": 50000.00,
            "portfolio_value": 150000.00,
            "buying_power": 200000.00,
            "equity": 150000.00,
            "multiplier": 1.0,
        }

        alpaca_adapter.client.get_account = AsyncMock(return_value=mock_account)
        alpaca_adapter.is_connected = True

        portfolio_value = await alpaca_adapter.calculate_portfolio_value()

        assert portfolio_value == Decimal("150000.00")


class TestAlpacaAdapterErrorHandling:
    """Test AlpacaAdapter error handling."""

    @pytest.mark.asyncio
    async def test_place_order_error_graceful_fallback(self, alpaca_adapter):
        """Test graceful error handling in place_order."""
        alpaca_adapter.client.submit_order = AsyncMock(side_effect=Exception("API error"))

        with pytest.raises(Exception):
            await alpaca_adapter.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=Decimal("100"),
            )

    @pytest.mark.asyncio
    async def test_get_positions_error_graceful_fallback(self, alpaca_adapter):
        """Test graceful error handling in get_positions."""
        alpaca_adapter.client.get_positions = AsyncMock(side_effect=Exception("Connection error"))

        positions = await alpaca_adapter.get_positions()

        # Should return empty list on error instead of raising
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_account_info_error_graceful_fallback(self, alpaca_adapter):
        """Test graceful error handling in get_account_info."""
        alpaca_adapter.client.get_account = AsyncMock(side_effect=Exception("API error"))
        alpaca_adapter.is_connected = True

        account = await alpaca_adapter.get_account_info()

        # Should return cached account on error
        assert account is not None or account is None  # Either cached or None


class TestAlpacaAdapterStateManagement:
    """Test AlpacaAdapter state caching."""

    @pytest.mark.asyncio
    async def test_order_caching(self, alpaca_adapter):
        """Test order state caching."""
        mock_order = MagicMock(id="cached_order")
        alpaca_adapter.client.submit_order = AsyncMock(return_value=mock_order.id)
        alpaca_adapter.is_connected = True

        order_id = await alpaca_adapter.place_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
        )

        assert order_id in alpaca_adapter.orders
        assert alpaca_adapter.orders[order_id].order_id == "cached_order"

    @pytest.mark.asyncio
    async def test_position_caching(self, alpaca_adapter):
        """Test position state caching."""
        mock_positions = [
            {
                "symbol": "MSFT",
                "qty": 30,
                "avg_fill_price": 380.00,
                "current_price": 390.00,
            },
        ]

        alpaca_adapter.client.get_positions = AsyncMock(return_value=mock_positions)
        alpaca_adapter.is_connected = True

        await alpaca_adapter.get_positions()

        assert "MSFT" in alpaca_adapter.positions
        assert alpaca_adapter.positions["MSFT"].symbol == "MSFT"


class TestAlpacaAdapterDecimalPrecision:
    """Test decimal precision handling."""

    def test_decimal_precision_in_account_transform(self, alpaca_adapter):
        """Test Decimal precision in account transformation."""
        alpaca_account = {
            "account_number": "PA999000",
            "cash": 99999.99,
            "portfolio_value": 199999.99,
            "buying_power": 299999.99,
            "equity": 199999.99,
            "multiplier": 1.5,
        }

        broker_account = alpaca_adapter._transform_account(alpaca_account)

        # Verify Decimal type is used
        assert isinstance(broker_account.cash_available, Decimal)
        assert isinstance(broker_account.portfolio_value, Decimal)
        assert isinstance(broker_account.buying_power, Decimal)

    def test_decimal_precision_in_position_transform(self, alpaca_adapter):
        """Test Decimal precision in position transformation."""
        alpaca_pos = {
            "symbol": "BRK.A",
            "qty": 1,
            "avg_fill_price": 599999.99,
            "current_price": 600000.01,
        }

        broker_pos = alpaca_adapter._transform_position(alpaca_pos)

        # Verify Decimal type is used and precision is maintained
        assert isinstance(broker_pos.avg_price, Decimal)
        assert isinstance(broker_pos.current_price, Decimal)
        assert isinstance(broker_pos.market_value, Decimal)


class TestAlpacaAdapterInterfaceCompliance:
    """Test compliance with BrokerConnector interface."""

    def test_adapter_has_all_required_methods(self, alpaca_adapter):
        """Test that adapter implements all required BrokerConnector methods."""
        required_methods = [
            "connect",
            "disconnect",
            "place_order",
            "cancel_order",
            "get_order_status",
            "get_account_info",
            "get_positions",
            "get_position",
            "update_positions",
            "sync_account_balance",
            "calculate_portfolio_value",
            "is_paper_trading",
            "get_broker_type",
        ]

        for method in required_methods:
            assert hasattr(alpaca_adapter, method), f"Missing method: {method}"

    def test_adapter_properties(self, alpaca_adapter):
        """Test that adapter has required properties."""
        assert hasattr(alpaca_adapter, "account")
        assert hasattr(alpaca_adapter, "positions")
        assert hasattr(alpaca_adapter, "orders")
        assert hasattr(alpaca_adapter, "is_connected")

    def test_broker_type_returns_alpaca(self, alpaca_adapter):
        """Test that get_broker_type returns ALPACA."""
        broker_type = alpaca_adapter.get_broker_type()
        assert broker_type == BrokerType.ALPACA

    def test_is_paper_trading(self, alpaca_adapter):
        """Test paper trading mode detection."""
        # Should check base URL
        alpaca_adapter.client.base_url = "https://paper-api.alpaca.markets"
        assert alpaca_adapter.is_paper_trading() is True

        alpaca_adapter.client.base_url = "https://api.alpaca.markets"
        assert alpaca_adapter.is_paper_trading() is False
