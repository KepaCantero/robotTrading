"""
Unit tests for AlpacaClient - Low-level Alpaca REST API wrapper.

Tests authentication, order management, account info, positions, and error handling.
Uses mocked alpaca-trade-api responses.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.live_trading.broker_adapters.alpaca_client import (
    AlpacaClient,
    AlpacaClientError,
)


@pytest.fixture
def alpaca_client():
    """Create AlpacaClient instance for testing."""
    return AlpacaClient()


@pytest.fixture
def mock_rest_api():
    """Mock REST API instance."""
    return MagicMock()


class TestAlpacaClientAuthentication:
    """Test AlpacaClient authentication flow."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, alpaca_client, mock_rest_api):
        """Test successful authentication with Alpaca."""
        with patch(
            "app.services.live_trading.broker_adapters.alpaca_client.REST",
            return_value=mock_rest_api,
        ):
            # Mock successful get_account call to verify connection
            mock_rest_api.get_account.return_value = MagicMock(
                account_number="12345",
                cash=100000,
                portfolio_value=100000,
                buying_power=100000,
                equity=100000,
                multiplier=1,
            )

            result = await alpaca_client.authenticate(
                api_key="test_key",
                api_secret="test_secret",
                base_url="https://paper-api.alpaca.markets",
                paper_trading=True,
            )

            assert result is True
            assert alpaca_client.api is not None

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, alpaca_client):
        """Test authentication failure with invalid credentials."""
        with patch(
            "app.services.live_trading.broker_adapters.alpaca_client.REST",
            side_effect=Exception("Invalid credentials"),
        ):
            with pytest.raises(AlpacaClientError):
                await alpaca_client.authenticate(
                    api_key="invalid_key",
                    api_secret="invalid_secret",
                    base_url="https://paper-api.alpaca.markets",
                )

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self, alpaca_client):
        """Test authentication with missing credentials."""
        with pytest.raises(AlpacaClientError):
            await alpaca_client.authenticate(
                api_key=None,
                api_secret=None,
            )


class TestAlpacaClientOrderManagement:
    """Test AlpacaClient order management."""

    @pytest.mark.asyncio
    async def test_submit_market_order(self, alpaca_client, mock_rest_api):
        """Test submitting a market order."""
        alpaca_client.api = mock_rest_api

        # Mock order response
        mock_rest_api.submit_order.return_value = MagicMock(
            id="order_123",
            symbol="AAPL",
            qty=100,
            side="buy",
            order_type="market",
            status="new",
            created_at="2025-01-01T10:00:00Z",
        )

        order_id = await alpaca_client.submit_order(
            symbol="AAPL",
            qty=Decimal("100"),
            side="buy",
            order_type="market",
        )

        assert order_id == "order_123"
        mock_rest_api.submit_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_limit_order(self, alpaca_client, mock_rest_api):
        """Test submitting a limit order."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.submit_order.return_value = MagicMock(
            id="order_124",
            symbol="AAPL",
            qty=100,
            side="sell",
            order_type="limit",
            limit_price=150.50,
            status="new",
        )

        order_id = await alpaca_client.submit_order(
            symbol="AAPL",
            qty=Decimal("100"),
            side="sell",
            order_type="limit",
            limit_price=Decimal("150.50"),
        )

        assert order_id == "order_124"

    @pytest.mark.asyncio
    async def test_submit_stop_order(self, alpaca_client, mock_rest_api):
        """Test submitting a stop order."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.submit_order.return_value = MagicMock(
            id="order_125",
            symbol="AAPL",
            qty=100,
            side="sell",
            order_type="stop",
            stop_price=145.00,
            status="new",
        )

        order_id = await alpaca_client.submit_order(
            symbol="AAPL",
            qty=Decimal("100"),
            side="sell",
            order_type="stop",
            stop_price=Decimal("145.00"),
        )

        assert order_id == "order_125"

    @pytest.mark.asyncio
    async def test_submit_trailing_stop_order(self, alpaca_client, mock_rest_api):
        """Test submitting a trailing stop order."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.submit_order.return_value = MagicMock(
            id="order_126",
            symbol="AAPL",
            qty=100,
            side="sell",
            order_type="trailing_stop",
            trail_percent=5.0,
            status="new",
        )

        order_id = await alpaca_client.submit_order(
            symbol="AAPL",
            qty=Decimal("100"),
            side="sell",
            order_type="trailing_stop",
            trail_percent=5.0,
        )

        assert order_id == "order_126"

    @pytest.mark.asyncio
    async def test_cancel_order(self, alpaca_client, mock_rest_api):
        """Test canceling an order."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.cancel_order.return_value = None

        result = await alpaca_client.cancel_order("order_123")

        assert result is True
        mock_rest_api.cancel_order.assert_called_once_with("order_123")

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, alpaca_client, mock_rest_api):
        """Test canceling non-existent order."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.cancel_order.side_effect = Exception("Order not found")

        with pytest.raises(AlpacaClientError):
            await alpaca_client.cancel_order("nonexistent_order")

    @pytest.mark.asyncio
    async def test_get_order(self, alpaca_client, mock_rest_api):
        """Test getting single order status."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.get_order.return_value = MagicMock(
            id="order_123",
            symbol="AAPL",
            qty=100,
            side="buy",
            status="filled",
            filled_qty=100,
            filled_avg_price=150.00,
        )

        order_data = await alpaca_client.get_order("order_123")

        assert order_data["id"] == "order_123"
        assert order_data["status"] == "filled"


class TestAlpacaClientAccountInfo:
    """Test AlpacaClient account info retrieval."""

    @pytest.mark.asyncio
    async def test_get_account(self, alpaca_client, mock_rest_api):
        """Test retrieving account information."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.get_account.return_value = MagicMock(
            account_number="PA123456",
            cash=100000.00,
            portfolio_value=150000.00,
            buying_power=200000.00,
            equity=150000.00,
            multiplier=1.0,
        )

        account = await alpaca_client.get_account()

        assert account["account_number"] == "PA123456"
        assert account["cash"] == 100000.00
        assert account["portfolio_value"] == 150000.00

    @pytest.mark.asyncio
    async def test_get_account_failure(self, alpaca_client, mock_rest_api):
        """Test get account failure."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.get_account.side_effect = Exception("API Error")

        with pytest.raises(AlpacaClientError):
            await alpaca_client.get_account()


class TestAlpacaClientPositions:
    """Test AlpacaClient position retrieval."""

    @pytest.mark.asyncio
    async def test_get_positions(self, alpaca_client, mock_rest_api):
        """Test retrieving all positions."""
        alpaca_client.api = mock_rest_api

        mock_positions = [
            MagicMock(
                symbol="AAPL",
                qty=100,
                avg_fill_price=150.00,
                current_price=155.00,
                market_value=15500.00,
            ),
            MagicMock(
                symbol="TSLA",
                qty=50,
                avg_fill_price=800.00,
                current_price=850.00,
                market_value=42500.00,
            ),
        ]
        mock_rest_api.get_positions.return_value = mock_positions

        positions = await alpaca_client.get_positions()

        assert len(positions) == 2
        assert positions[0]["symbol"] == "AAPL"
        assert positions[1]["symbol"] == "TSLA"

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, alpaca_client, mock_rest_api):
        """Test retrieving positions when none exist."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.get_positions.return_value = []

        positions = await alpaca_client.get_positions()

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_get_positions_failure(self, alpaca_client, mock_rest_api):
        """Test get positions failure."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.get_positions.side_effect = Exception("API Error")

        with pytest.raises(AlpacaClientError):
            await alpaca_client.get_positions()


class TestAlpacaClientOrderList:
    """Test AlpacaClient order listing with filters."""

    @pytest.mark.asyncio
    async def test_get_orders(self, alpaca_client, mock_rest_api):
        """Test retrieving order list."""
        alpaca_client.api = mock_rest_api

        mock_orders = [
            MagicMock(id="order_1", status="filled"),
            MagicMock(id="order_2", status="pending"),
            MagicMock(id="order_3", status="canceled"),
        ]
        mock_rest_api.get_orders.return_value = mock_orders

        orders = await alpaca_client.get_orders()

        assert len(orders) == 3

    @pytest.mark.asyncio
    async def test_get_orders_with_status_filter(self, alpaca_client, mock_rest_api):
        """Test retrieving orders filtered by status."""
        alpaca_client.api = mock_rest_api

        mock_orders = [
            MagicMock(id="order_1", status="filled"),
        ]
        mock_rest_api.get_orders.return_value = mock_orders

        orders = await alpaca_client.get_orders(status="filled")

        assert len(orders) == 1
        assert orders[0]["status"] == "filled"


class TestAlpacaClientErrorHandling:
    """Test AlpacaClient error handling."""

    @pytest.mark.asyncio
    async def test_api_error_mapping(self, alpaca_client):
        """Test that API errors are properly mapped."""
        alpaca_client.api = MagicMock()
        alpaca_client.api.get_account.side_effect = Exception("Connection timeout")

        with pytest.raises(AlpacaClientError):
            await alpaca_client.get_account()

    @pytest.mark.asyncio
    async def test_insufficient_funds_error(self, alpaca_client, mock_rest_api):
        """Test handling insufficient funds error."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.submit_order.side_effect = Exception("Insufficient buying power")

        with pytest.raises(AlpacaClientError):
            await alpaca_client.submit_order(
                symbol="AAPL",
                qty=Decimal("1000000"),
                side="buy",
                order_type="market",
            )

    @pytest.mark.asyncio
    async def test_invalid_symbol_error(self, alpaca_client, mock_rest_api):
        """Test handling invalid symbol error."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.submit_order.side_effect = Exception("Invalid symbol")

        with pytest.raises(AlpacaClientError):
            await alpaca_client.submit_order(
                symbol="INVALID",
                qty=Decimal("100"),
                side="buy",
                order_type="market",
            )


class TestAlpacaClientRateLimiting:
    """Test AlpacaClient rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limit_response(self, alpaca_client, mock_rest_api):
        """Test handling rate limit (429) response."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.get_account.side_effect = Exception("429 Too Many Requests")

        with pytest.raises(AlpacaClientError):
            await alpaca_client.get_account()


class TestAlpacaClientConnectionManagement:
    """Test AlpacaClient connection lifecycle."""

    @pytest.mark.asyncio
    async def test_start_stream(self, alpaca_client):
        """Test starting WebSocket stream."""
        # This is a placeholder for WebSocket implementation
        # For now, just verify the method exists and can be called
        await alpaca_client.start_stream(["AAPL", "TSLA"])
        # No assertion - method is not yet implemented, just verify no error

    @pytest.mark.asyncio
    async def test_stop_stream(self, alpaca_client):
        """Test stopping WebSocket stream."""
        await alpaca_client.stop_stream()
        # No assertion - method is not yet implemented, just verify no error


class TestAlpacaClientDecimalHandling:
    """Test AlpacaClient Decimal precision handling."""

    @pytest.mark.asyncio
    async def test_decimal_quantity_conversion(self, alpaca_client, mock_rest_api):
        """Test that Decimal quantities are properly converted."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.submit_order.return_value = MagicMock(
            id="order_decimal",
            qty=100,
        )

        # Submit order with Decimal quantity
        order_id = await alpaca_client.submit_order(
            symbol="AAPL",
            qty=Decimal("100.50"),
            side="buy",
            order_type="market",
        )

        assert order_id == "order_decimal"

    @pytest.mark.asyncio
    async def test_decimal_price_conversion(self, alpaca_client, mock_rest_api):
        """Test that Decimal prices are properly converted."""
        alpaca_client.api = mock_rest_api

        mock_rest_api.submit_order.return_value = MagicMock(
            id="order_price",
            limit_price=150.50,
        )

        order_id = await alpaca_client.submit_order(
            symbol="AAPL",
            qty=Decimal("100"),
            side="buy",
            order_type="limit",
            limit_price=Decimal("150.50"),
        )

        assert order_id == "order_price"
