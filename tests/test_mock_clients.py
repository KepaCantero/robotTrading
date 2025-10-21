"""
Integration tests for mock trading clients.

This module tests the complete flow from market data to order execution
using mock IBKR and Binance clients.
"""

import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime

from app.mocks import MockIBKRClient, MockBinanceClient, create_mock_ibkr_client, create_mock_binance_client
from app.models.order import Order, OrderType, OrderSide, OrderStatus
from app.models.portfolio import Position, AssetClass
from app.models.momentum import MarketData


class TestMockIBKRClient:
    """Tests for MockIBKRClient."""
    
    @pytest.fixture
    def ibkr_client(self):
        """Mock IBKR client fixture."""
        return create_mock_ibkr_client("DU123456")
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, ibkr_client):
        """Test connection and disconnection."""
        assert ibkr_client.connection_status.value == "disconnected"
        
        # Test connection
        result = await ibkr_client.connect()
        assert result is True
        assert ibkr_client.connection_status.value == "connected"
        
        # Test disconnection
        result = await ibkr_client.disconnect()
        assert result is True
        assert ibkr_client.connection_status.value == "disconnected"
    
    @pytest.mark.asyncio
    async def test_account_summary(self, ibkr_client):
        """Test account summary retrieval."""
        await ibkr_client.connect()
        
        summary = await ibkr_client.get_account_summary()
        
        assert summary["account_id"] == "DU123456"
        assert summary["total_cash"] == Decimal("100000.00")
        assert summary["buying_power"] == Decimal("200000.00")
        assert summary["currency"] == "USD"
        assert "timestamp" in summary
    
    @pytest.mark.asyncio
    async def test_market_data_subscription(self, ibkr_client):
        """Test market data subscription."""
        await ibkr_client.connect()
        
        # Subscribe to market data
        result = await ibkr_client.subscribe_market_data("AAPL")
        assert result is True
        
        # Get market data
        market_data = await ibkr_client.get_market_data("AAPL")
        assert market_data is not None
        assert market_data.symbol == "AAPL"
        assert market_data.close_price > 0
        assert market_data.bid < market_data.ask
        assert market_data.spread == market_data.ask - market_data.bid
    
    @pytest.mark.asyncio
    async def test_order_execution_flow(self, ibkr_client):
        """Test complete order execution flow."""
        await ibkr_client.connect()
        await ibkr_client.subscribe_market_data("AAPL")
        
        # Create buy order
        order = Order(
            id="test_order_1",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("150.00")
        )
        
        # Place order
        order_id = await ibkr_client.place_order(order)
        assert order_id.startswith("IBKR_")
        assert order.order_id == order_id
        assert order.status == OrderStatus.FILLED
        
        # Check position was created
        position = await ibkr_client.get_position("AAPL")
        assert position is not None
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.asset_class == AssetClass.EQUITY
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self, ibkr_client):
        """Test order cancellation."""
        await ibkr_client.connect()
        
        # Create limit order that won't execute immediately
        order = Order(
            id="test_order_2",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("94.99")  # Just below the 95% threshold, won't execute immediately
        )
        
        # Place order
        order_id = await ibkr_client.place_order(order)
        assert order.status == OrderStatus.PENDING  # Should be pending for cancellation
        
        # Test cancellation
        result = await ibkr_client.cancel_order(order_id)
        assert result is True
        assert order.status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_error_handling(self, ibkr_client):
        """Test error handling when not connected."""
        # Test operations without connection
        with pytest.raises(ConnectionError):
            await ibkr_client.get_account_summary()
        
        with pytest.raises(ConnectionError):
            await ibkr_client.get_positions()
        
        with pytest.raises(ConnectionError):
            await ibkr_client.place_order(Order(
                id="test_order_3",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                price=Decimal("150.00")
            ))


class TestMockBinanceClient:
    """Tests for MockBinanceClient."""
    
    @pytest.fixture
    def binance_client(self):
        """Mock Binance client fixture."""
        return create_mock_binance_client("mock_key", "mock_secret")
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, binance_client):
        """Test connection and disconnection."""
        assert binance_client.connection_status.value == "disconnected"
        
        # Test connection
        result = await binance_client.connect()
        assert result is True
        assert binance_client.connection_status.value == "connected"
        
        # Test disconnection
        result = await binance_client.disconnect()
        assert result is True
        assert binance_client.connection_status.value == "disconnected"
    
    @pytest.mark.asyncio
    async def test_account_info(self, binance_client):
        """Test account info retrieval."""
        await binance_client.connect()
        
        account_info = await binance_client.get_account_info()
        
        assert account_info["account_type"] == "SPOT"
        assert account_info["can_trade"] is True
        assert len(account_info["balances"]) > 0
        assert "timestamp" in account_info
    
    @pytest.mark.asyncio
    async def test_balance_operations(self, binance_client):
        """Test balance operations."""
        await binance_client.connect()
        
        # Set initial balance
        binance_client.balances["USDT"] = Decimal("10000.00")
        binance_client.balances["BTC"] = Decimal("1.00")
        
        # Get balances
        usdt_balance = await binance_client.get_balance("USDT")
        btc_balance = await binance_client.get_balance("BTC")
        
        assert usdt_balance == Decimal("10000.00")
        assert btc_balance == Decimal("1.00")
    
    @pytest.mark.asyncio
    async def test_crypto_order_execution(self, binance_client):
        """Test crypto order execution."""
        await binance_client.connect()
        
        # Set initial balance
        binance_client.balances["USDT"] = Decimal("10000.00")
        
        # Create buy order
        order = Order(
            id="test_crypto_order_1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=Decimal("50000.00")
        )
        
        # Place order
        order_id = await binance_client.place_order(order)
        assert order_id.startswith("BINANCE_")
        assert order.order_id == order_id
        assert order.status == OrderStatus.FILLED
        
        # Check balances updated
        usdt_balance = await binance_client.get_balance("USDT")
        btc_balance = await binance_client.get_balance("BTC")
        
        assert usdt_balance < Decimal("10000.00")  # USDT reduced
        assert btc_balance > Decimal("0")  # BTC increased
    
    @pytest.mark.asyncio
    async def test_klines_data(self, binance_client):
        """Test klines data retrieval."""
        await binance_client.connect()
        
        klines = await binance_client.get_klines("BTCUSDT", "1d", 10)
        
        assert len(klines) == 10
        assert all("open" in kline for kline in klines)
        assert all("high" in kline for kline in klines)
        assert all("low" in kline for kline in klines)
        assert all("close" in kline for kline in klines)
        assert all("volume" in kline for kline in klines)
    
    @pytest.mark.asyncio
    async def test_insufficient_balance_rejection(self, binance_client):
        """Test order rejection due to insufficient balance."""
        await binance_client.connect()
        
        # Set low balance
        binance_client.balances["USDT"] = Decimal("100.00")
        
        # Create order requiring more balance
        order = Order(
            id="test_crypto_order_2",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),  # Requires ~50k USDT
            price=Decimal("50000.00")
        )
        
        # Place order
        order_id = await binance_client.place_order(order)
        assert order.status == OrderStatus.REJECTED
        assert order.rejected_reason == "Insufficient balance"


class TestMockClientIntegration:
    """Integration tests for mock clients."""
    
    @pytest.mark.asyncio
    async def test_multi_client_operations(self):
        """Test operations with multiple mock clients."""
        ibkr_client = create_mock_ibkr_client("DU123456")
        binance_client = create_mock_binance_client("mock_key", "mock_secret")
        
        # Connect both clients
        await ibkr_client.connect()
        await binance_client.connect()
        
        # Set up market data
        await ibkr_client.subscribe_market_data("AAPL")
        binance_client.balances["USDT"] = Decimal("10000.00")
        
        # Place orders on both platforms
        ibkr_order = Order(
            id="test_multi_order_1",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("150.00")
        )
        
        binance_order = Order(
            id="test_multi_order_2",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=Decimal("50000.00")
        )
        
        # Execute orders
        ibkr_order_id = await ibkr_client.place_order(ibkr_order)
        binance_order_id = await binance_client.place_order(binance_order)
        
        # Verify both orders executed
        assert ibkr_order.status == OrderStatus.FILLED
        assert binance_order.status == OrderStatus.FILLED
        
        # Verify positions/balances updated
        ibkr_position = await ibkr_client.get_position("AAPL")
        assert ibkr_position is not None
        
        btc_balance = await binance_client.get_balance("BTC")
        assert btc_balance > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent operations on mock clients."""
        ibkr_client = create_mock_ibkr_client("DU123456")
        await ibkr_client.connect()
        await ibkr_client.subscribe_market_data("AAPL")
        
        # Create multiple orders
        orders = [
            Order(
                id=f"test_concurrent_order_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("10"),
                price=Decimal("150.00")
            )
            for i in range(5)
        ]
        
        # Execute orders concurrently
        order_ids = await asyncio.gather(
            *[ibkr_client.place_order(order) for order in orders]
        )
        
        # Verify all orders executed
        assert len(order_ids) == 5
        assert all(order.status == OrderStatus.FILLED for order in orders)
        
        # Verify final position
        position = await ibkr_client.get_position("AAPL")
        assert position.quantity == Decimal("50")  # 5 orders * 10 shares each
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery scenarios."""
        ibkr_client = create_mock_ibkr_client("DU123456")
        
        # Test operations without connection
        with pytest.raises(ConnectionError):
            await ibkr_client.get_account_summary()
        
        # Connect and retry
        await ibkr_client.connect()
        summary = await ibkr_client.get_account_summary()
        assert summary is not None
        
        # Disconnect and test again
        await ibkr_client.disconnect()
        with pytest.raises(ConnectionError):
            await ibkr_client.get_account_summary()
        
        # Reconnect
        await ibkr_client.connect()
        summary = await ibkr_client.get_account_summary()
        assert summary is not None
