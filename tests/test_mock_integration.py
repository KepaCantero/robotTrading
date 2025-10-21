"""
End-to-end integration tests using mock trading clients.

This module tests the complete trading workflow from signal generation
to order execution using mock IBKR and Binance clients.
"""

import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from app.mocks import MockIBKRClient, MockBinanceClient
from app.models.order import Order, OrderType, OrderSide, OrderStatus
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Position, AssetClass
from app.services.signal_scorer import SignalScorer
from app.services.portfolio_service import PortfolioService
from app.providers.paper_trading import PaperTradingPortfolioProvider


class TestTradingWorkflowIntegration:
    """End-to-end trading workflow tests."""
    
    @pytest.fixture
    def ibkr_client(self):
        """Mock IBKR client fixture."""
        client = MockIBKRClient("DU123456")
        return client
    
    @pytest.fixture
    def binance_client(self):
        """Mock Binance client fixture."""
        client = MockBinanceClient("mock_key", "mock_secret")
        return client
    
    @pytest.fixture
    def signal_scorer(self):
        """Signal scorer fixture."""
        return SignalScorer()
    
    @pytest.fixture
    def portfolio_provider(self):
        """Paper trading portfolio provider fixture."""
        return PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
    
    @pytest.fixture
    def portfolio_service(self, portfolio_provider):
        """Portfolio service fixture."""
        return PortfolioService(portfolio_provider)
    
    @pytest.mark.asyncio
    async def test_equity_trading_workflow(self, ibkr_client, signal_scorer, portfolio_service):
        """Test complete equity trading workflow."""
        # Setup
        await ibkr_client.connect()
        await ibkr_client.subscribe_market_data("AAPL")
        
        # Generate trading signal
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=90.0,
            priority_score=88.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow()
        )
        
        # Score signal
        scored_signal = signal_scorer.score_signal(signal)
        assert scored_signal.priority_score > 0
        
        # Create order from signal
        order = Order(
            id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=signal.price
        )
        
        # Execute order
        order_id = await ibkr_client.place_order(order)
        assert order_id is not None
        assert order.status == OrderStatus.FILLED
        
        # Verify position
        position = await ibkr_client.get_position("AAPL")
        assert position is not None
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        
        # Update portfolio
        await portfolio_service.add_position(position)
        portfolio = await portfolio_service.get_portfolio()
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_crypto_trading_workflow(self, binance_client, signal_scorer, portfolio_service):
        """Test complete crypto trading workflow."""
        # Setup
        await binance_client.connect()
        binance_client.balances["USDT"] = Decimal("10000.00")
        
        # Generate trading signal
        signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=95.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("50000.00"),
            volume=Decimal("1000"),
            timestamp=datetime.utcnow()
        )
        
        # Score signal
        scored_signal = signal_scorer.score_signal(signal)
        assert scored_signal.priority_score > 0
        
        # Create order from signal
        order = Order(
            id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=signal.price
        )
        
        # Execute order
        order_id = await binance_client.place_order(order)
        assert order_id is not None
        assert order.status == OrderStatus.FILLED
        
        # Verify balance updated
        btc_balance = await binance_client.get_balance("BTC")
        usdt_balance = await binance_client.get_balance("USDT")
        
        assert btc_balance > Decimal("0")
        assert usdt_balance < Decimal("10000.00")
    
    @pytest.mark.asyncio
    async def test_multi_asset_trading_workflow(self, ibkr_client, binance_client, signal_scorer):
        """Test trading workflow across multiple assets and exchanges."""
        # Setup both clients
        await ibkr_client.connect()
        await binance_client.connect()
        
        await ibkr_client.subscribe_market_data("AAPL")
        binance_client.balances["USDT"] = Decimal("20000.00")
        
        # Generate signals for different assets
        equity_signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=90.0,
            priority_score=88.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow()
        )
        
        crypto_signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=95.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("50000.00"),
            volume=Decimal("1000"),
            timestamp=datetime.utcnow()
        )
        
        # Score signals
        scored_equity = signal_scorer.score_signal(equity_signal)
        scored_crypto = signal_scorer.score_signal(crypto_signal)
        
        # Create orders
        equity_order = Order(
            id=str(uuid.uuid4()),
            symbol=equity_signal.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50"),
            price=equity_signal.price
        )
        
        crypto_order = Order(
            id=str(uuid.uuid4()),
            symbol=crypto_signal.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.2"),
            price=crypto_signal.price
        )
        
        # Execute orders concurrently
        equity_order_id, crypto_order_id = await asyncio.gather(
            ibkr_client.place_order(equity_order),
            binance_client.place_order(crypto_order)
        )
        
        # Verify both orders executed
        assert equity_order.status == OrderStatus.FILLED
        assert crypto_order.status == OrderStatus.FILLED
        
        # Verify positions/balances
        equity_position = await ibkr_client.get_position("AAPL")
        btc_balance = await binance_client.get_balance("BTC")
        
        assert equity_position is not None
        assert equity_position.quantity == Decimal("50")
        assert btc_balance > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_order_rejection_handling(self, ibkr_client, binance_client):
        """Test handling of order rejections."""
        # Setup
        await ibkr_client.connect()
        await binance_client.connect()
        
        await ibkr_client.subscribe_market_data("AAPL")
        binance_client.balances["USDT"] = Decimal("100.00")  # Low balance
        
        # Create orders that should be rejected
        equity_order = Order(
            id=str(uuid.uuid4()),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1000"),
            price=Decimal("50.00")  # Very low price, should be rejected
        )
        
        crypto_order = Order(
            id=str(uuid.uuid4()),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),  # Requires ~50k USDT, should be rejected
            price=Decimal("50000.00")
        )
        
        # Execute orders
        equity_order_id = await ibkr_client.place_order(equity_order)
        crypto_order_id = await binance_client.place_order(crypto_order)
        
        # Verify rejections
        assert equity_order.status == OrderStatus.REJECTED
        assert crypto_order.status == OrderStatus.REJECTED
        
        assert equity_order.rejected_reason == "Insufficient funds"
        assert crypto_order.rejected_reason == "Insufficient balance"
    
    @pytest.mark.asyncio
    async def test_order_cancellation_workflow(self, ibkr_client):
        """Test order cancellation workflow."""
        # Setup
        await ibkr_client.connect()
        await ibkr_client.subscribe_market_data("AAPL")
        
        # Create limit order that won't execute immediately
        order = Order(
            id=str(uuid.uuid4()),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("50.00")  # Low price, won't execute
        )
        
        # Place order
        order_id = await ibkr_client.place_order(order)
        
        # Order should be rejected due to low price
        assert order.status == OrderStatus.REJECTED
        
        # Test cancellation of rejected order
        result = await ibkr_client.cancel_order(order_id)
        assert result is True
        assert order.status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_portfolio_synchronization(self, ibkr_client, portfolio_service):
        """Test portfolio synchronization with mock client."""
        # Setup
        await ibkr_client.connect()
        await ibkr_client.subscribe_market_data("AAPL")
        
        # Create and execute order
        order = Order(
            id=str(uuid.uuid4()),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("150.00")
        )
        
        order_id = await ibkr_client.place_order(order)
        assert order.status == OrderStatus.FILLED
        
        # Get position from client
        position = await ibkr_client.get_position("AAPL")
        
        # Add to portfolio
        await portfolio_service.add_position(position)
        
        # Verify portfolio
        portfolio = await portfolio_service.get_portfolio()
        assert len(portfolio.positions) == 1
        
        portfolio_position = portfolio.positions[0]
        assert portfolio_position.symbol == "AAPL"
        assert portfolio_position.quantity == Decimal("100")
        assert portfolio_position.asset_class == AssetClass.EQUITY
        
        # Test position update
        position.quantity = Decimal("150")
        await portfolio_service.update_position(position)
        
        updated_portfolio = await portfolio_service.get_portfolio()
        assert updated_portfolio.positions[0].quantity == Decimal("150")
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, ibkr_client):
        """Test error recovery in trading workflow."""
        # Test operations without connection
        with pytest.raises(ConnectionError):
            await ibkr_client.get_account_summary()
        
        # Connect and retry
        await ibkr_client.connect()
        summary = await ibkr_client.get_account_summary()
        assert summary is not None
        
        # Test order execution
        await ibkr_client.subscribe_market_data("AAPL")
        
        order = Order(
            id=str(uuid.uuid4()),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("150.00")
        )
        
        order_id = await ibkr_client.place_order(order)
        assert order.status == OrderStatus.FILLED
        
        # Disconnect and test error handling
        await ibkr_client.disconnect()
        
        with pytest.raises(ConnectionError):
            await ibkr_client.place_order(order)
        
        # Reconnect and continue
        await ibkr_client.connect()
        await ibkr_client.subscribe_market_data("AAPL")
        
        new_order = Order(
            id=str(uuid.uuid4()),
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("50"),
            price=Decimal("150.00")
        )
        
        new_order_id = await ibkr_client.place_order(new_order)
        assert new_order.status == OrderStatus.FILLED
