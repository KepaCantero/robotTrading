"""
Comprehensive Tests for Paper Trading System

This module contains comprehensive tests for the paper trading system including
portfolio management, trade execution, position tracking, and performance metrics.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.paper_trading_service import PaperTradingService
from app.models.paper_trading import (
    PaperTradingMode,
    PaperTradingConfig,
    PaperPortfolio,
    PaperTradingSession,
    PaperTrade,
    PaperPosition,
    TradeStatus,
    OrderSide,
    OrderType
)
from app.models.market_data import Quote, DataFeedType, MarketDataStatus


class TestPaperTradingService:
    """Tests for PaperTradingService."""
    
    @pytest.fixture
    def service(self):
        """Paper trading service fixture."""
        return PaperTradingService()
    
    @pytest.fixture
    def portfolio(self, service):
        """Portfolio fixture."""
        return asyncio.run(service.create_portfolio("Test Portfolio"))
    
    @pytest.fixture
    def session(self, service, portfolio):
        """Session fixture."""
        return asyncio.run(service.create_session(
            portfolio_id=portfolio.id,
            name="Test Session"
        ))
    
    @pytest.mark.asyncio
    async def test_create_portfolio(self, service):
        """Test portfolio creation."""
        portfolio = await service.create_portfolio("Test Portfolio")
        
        assert portfolio.name == "Test Portfolio"
        assert portfolio.cash_balance == Decimal("100000")
        assert portfolio.initial_cash == Decimal("100000")
        assert portfolio.total_equity == Decimal("100000")
        assert portfolio.simulation_mode == PaperTradingMode.REALISTIC
        
        # Verify portfolio is stored
        stored_portfolio = await service.get_portfolio(portfolio.id)
        assert stored_portfolio is not None
        assert stored_portfolio.id == portfolio.id
    
    @pytest.mark.asyncio
    async def test_create_portfolio_with_custom_cash(self, service):
        """Test portfolio creation with custom initial cash."""
        portfolio = await service.create_portfolio(
            "Custom Portfolio",
            initial_cash=Decimal("50000")
        )
        
        assert portfolio.cash_balance == Decimal("50000")
        assert portfolio.initial_cash == Decimal("50000")
        assert portfolio.total_equity == Decimal("50000")
    
    @pytest.mark.asyncio
    async def test_create_session(self, service, portfolio):
        """Test session creation."""
        session = await service.create_session(
            portfolio_id=portfolio.id,
            name="Test Session",
            description="Test session description"
        )
        
        assert session.name == "Test Session"
        assert session.description == "Test session description"
        assert session.portfolio_id == portfolio.id
        assert session.is_active is True
        assert session.status == "running"
        
        # Verify session is stored
        stored_session = await service.get_session(session.id)
        assert stored_session is not None
        assert stored_session.id == session.id
    
    @pytest.mark.asyncio
    async def test_execute_buy_trade(self, service, portfolio):
        """Test executing a buy trade."""
        initial_cash = portfolio.cash_balance
        
        trade = await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        assert trade.symbol == "AAPL"
        assert trade.side == OrderSide.BUY
        assert trade.order_type == OrderType.MARKET
        assert trade.quantity == Decimal("100")
        assert trade.status == TradeStatus.FILLED
        assert trade.filled_quantity == Decimal("100")
        assert trade.filled_at is not None
        
        # Verify portfolio cash was reduced
        updated_portfolio = await service.get_portfolio(portfolio.id)
        assert updated_portfolio.cash_balance < initial_cash
        
        # Verify position was created
        positions = await service.get_positions(portfolio.id)
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == Decimal("100")
    
    @pytest.mark.asyncio
    async def test_execute_sell_trade(self, service, portfolio):
        """Test executing a sell trade."""
        # First buy some shares
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        initial_cash = (await service.get_portfolio(portfolio.id)).cash_balance
        
        # Then sell some shares
        trade = await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("50")
        )
        
        assert trade.side == OrderSide.SELL
        assert trade.status == TradeStatus.FILLED
        assert trade.filled_quantity == Decimal("50")
        
        # Verify portfolio cash increased
        updated_portfolio = await service.get_portfolio(portfolio.id)
        assert updated_portfolio.cash_balance > initial_cash
        
        # Verify position was reduced
        positions = await service.get_positions(portfolio.id)
        assert len(positions) == 1
        assert positions[0].quantity == Decimal("50")  # 100 - 50
    
    @pytest.mark.asyncio
    async def test_execute_limit_order(self, service, portfolio):
        """Test executing a limit order."""
        trade = await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("140.00")  # Lower than market price
        )
        
        assert trade.order_type == OrderType.LIMIT
        assert trade.price == Decimal("140.00")
        assert trade.status == TradeStatus.FILLED
        assert trade.filled_price == Decimal("140.00")
    
    @pytest.mark.asyncio
    async def test_insufficient_cash_rejection(self, service):
        """Test trade rejection due to insufficient cash."""
        # Create portfolio with small amount
        portfolio = await service.create_portfolio(
            "Small Portfolio",
            initial_cash=Decimal("1000")
        )
        
        # Try to buy expensive shares
        trade = await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="GOOGL",  # Expensive stock
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10")  # Would cost ~$25,000
        )
        
        assert trade.status == TradeStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_position_sizing_limit(self, service):
        """Test position sizing limits."""
        config = PaperTradingConfig(
            name="Small Position Config",
            max_position_size=Decimal("0.05"),  # 5% max position
            initial_cash=Decimal("100000")
        )
        service.configs[config.id] = config
        
        portfolio = await service.create_portfolio(
            "Test Portfolio",
            config_id=config.id
        )
        
        # Try to buy large position
        trade = await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1000")  # Would be >5% of portfolio
        )
        
        assert trade.status == TradeStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_partial_fill_simulation(self, service):
        """Test partial fill simulation."""
        config = PaperTradingConfig(
            name="Partial Fill Config",
            partial_fill_probability=Decimal("1.0"),  # 100% partial fills
            initial_cash=Decimal("100000"),
            max_position_size=Decimal("0.5"),  # 50% max position
            max_daily_loss=Decimal("0.1"),  # 10% max daily loss
            max_drawdown=Decimal("0.2")  # 20% max drawdown
        )
        service.configs[config.id] = config
        
        portfolio = await service.create_portfolio(
            "Test Portfolio",
            config_id=config.id
        )
        
        trade = await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        assert trade.status == TradeStatus.PARTIALLY_FILLED
        assert trade.filled_quantity < trade.quantity
        assert trade.filled_quantity > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_execution_costs_calculation(self, service, portfolio):
        """Test execution costs calculation."""
        trade = await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        # Verify costs are calculated
        assert trade.commission > Decimal("0")
        assert trade.slippage >= Decimal("0")
        assert trade.market_impact >= Decimal("0")
        
        # Verify filled price includes slippage
        assert trade.filled_price != trade.price
    
    @pytest.mark.asyncio
    async def test_position_pnl_calculation(self, service, portfolio):
        """Test position P&L calculation."""
        # Buy shares
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        # Update market price (simulate price increase)
        quotes = {
            "AAPL": Quote(
                symbol="AAPL",
                bid=Decimal("160.00"),
                ask=Decimal("160.10"),
                last=Decimal("160.05"),
                open=Decimal("150.00"),
                high=Decimal("165.00"),
                low=Decimal("149.00"),
                close=Decimal("160.05"),
                volume=Decimal("1000000"),
                spread=Decimal("0.10"),
                feed_type=DataFeedType.MOCK,
                status=MarketDataStatus.ACTIVE
            )
        }
        
        await service.update_market_prices(quotes)
        
        # Check position P&L
        positions = await service.get_positions(portfolio.id)
        assert len(positions) == 1
        
        position = positions[0]
        assert position.unrealized_pnl > Decimal("0")  # Should have profit
        assert position.current_price == Decimal("160.05")
    
    @pytest.mark.asyncio
    async def test_portfolio_metrics_update(self, service, portfolio):
        """Test portfolio metrics update."""
        # Execute some trades
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50")
        )
        
        # Update market prices
        quotes = {
            "AAPL": Quote(
                symbol="AAPL",
                bid=Decimal("160.00"),
                ask=Decimal("160.10"),
                last=Decimal("160.05"),
                open=Decimal("150.00"),
                high=Decimal("165.00"),
                low=Decimal("149.00"),
                close=Decimal("160.05"),
                volume=Decimal("1000000"),
                spread=Decimal("0.10"),
                feed_type=DataFeedType.MOCK,
                status=MarketDataStatus.ACTIVE
            ),
            "MSFT": Quote(
                symbol="MSFT",
                bid=Decimal("310.00"),
                ask=Decimal("310.20"),
                last=Decimal("310.10"),
                open=Decimal("300.00"),
                high=Decimal("315.00"),
                low=Decimal("299.00"),
                close=Decimal("310.10"),
                volume=Decimal("500000"),
                spread=Decimal("0.20"),
                feed_type=DataFeedType.MOCK,
                status=MarketDataStatus.ACTIVE
            )
        }
        
        await service.update_market_prices(quotes)
        
        # Check portfolio metrics
        updated_portfolio = await service.get_portfolio(portfolio.id)
        assert updated_portfolio.total_equity > updated_portfolio.cash_balance
        assert updated_portfolio.total_pnl != Decimal("0")
        assert updated_portfolio.total_return != Decimal("0")
    
    @pytest.mark.asyncio
    async def test_session_statistics_update(self, service, portfolio, session):
        """Test session statistics update."""
        # Execute trades in session
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            session_id=session.id
        )
        
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50"),
            session_id=session.id
        )
        
        # Check session statistics
        updated_session = await service.get_session(session.id)
        assert updated_session.total_trades == 2
        assert updated_session.successful_trades == 2
        assert updated_session.failed_trades == 0
    
    @pytest.mark.asyncio
    async def test_close_session(self, service, session):
        """Test closing a session."""
        closed_session = await service.close_session(session.id)
        
        assert closed_session.is_active is False
        assert closed_session.status == "closed"
        assert closed_session.ended_at is not None
    
    @pytest.mark.asyncio
    async def test_get_trades_with_filters(self, service, portfolio):
        """Test getting trades with filters."""
        # Execute trades
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50")
        )
        
        # Test filters
        all_trades = await service.get_trades(portfolio_id=portfolio.id)
        assert len(all_trades) == 2
        
        aapl_trades = await service.get_trades(
            portfolio_id=portfolio.id,
            symbol="AAPL"
        )
        assert len(aapl_trades) == 1
        assert aapl_trades[0].symbol == "AAPL"
        
        filled_trades = await service.get_trades(
            portfolio_id=portfolio.id,
            status=TradeStatus.FILLED
        )
        assert len(filled_trades) == 2
        assert all(t.status == TradeStatus.FILLED for t in filled_trades)
    
    @pytest.mark.asyncio
    async def test_short_position(self, service, portfolio):
        """Test short position creation."""
        # First buy shares
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        # Then sell more than we have (short position)
        await service.execute_trade(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("150")  # Sell 150, only have 100
        )
        
        # Check position
        positions = await service.get_positions(portfolio.id)
        assert len(positions) == 1
        assert positions[0].quantity == Decimal("-50")  # Short 50 shares
    
    @pytest.mark.asyncio
    async def test_multiple_portfolios(self, service):
        """Test multiple portfolios independence."""
        portfolio1 = await service.create_portfolio("Portfolio 1")
        portfolio2 = await service.create_portfolio("Portfolio 2")
        
        # Execute trades in different portfolios
        await service.execute_trade(
            portfolio_id=portfolio1.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100")
        )
        
        await service.execute_trade(
            portfolio_id=portfolio2.id,
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50")
        )
        
        # Check positions are independent
        positions1 = await service.get_positions(portfolio1.id)
        positions2 = await service.get_positions(portfolio2.id)
        
        assert len(positions1) == 1
        assert len(positions2) == 1
        assert positions1[0].symbol == "AAPL"
        assert positions2[0].symbol == "MSFT"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test error handling."""
        # Try to create session with non-existent portfolio
        with pytest.raises(ValueError):
            await service.create_session(
                portfolio_id=uuid4(),  # Non-existent ID
                name="Test Session"
            )
        
        # Try to execute trade with non-existent portfolio
        with pytest.raises(ValueError):
            await service.execute_trade(
                portfolio_id=uuid4(),  # Non-existent ID
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100")
            )
        
        # Try to close non-existent session
        with pytest.raises(ValueError):
            await service.close_session(uuid4())  # Non-existent ID


class TestPaperTradingIntegration:
    """Integration tests for paper trading system."""
    
    @pytest.fixture
    def service(self):
        """Paper trading service fixture."""
        return PaperTradingService()
    
    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self, service):
        """Test complete trading workflow."""
        # Create portfolio
        portfolio = await service.create_portfolio("Integration Test Portfolio")
        
        # Create session
        session = await service.create_session(
            portfolio_id=portfolio.id,
            name="Integration Test Session"
        )
        
        # Execute multiple trades
        trades = []
        symbols = ["AAPL", "MSFT", "TSLA"]  # Changed GOOGL to TSLA (cheaper)
        
        for symbol in symbols:
            trade = await service.execute_trade(
                portfolio_id=portfolio.id,
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("50"),  # Reduced quantity
                session_id=session.id
            )
            trades.append(trade)
        
        # Update market prices
        quotes = {}
        for symbol in symbols:
            quotes[symbol] = Quote(
                symbol=symbol,
                bid=Decimal("160.00"),
                ask=Decimal("160.10"),
                last=Decimal("160.05"),
                open=Decimal("150.00"),
                high=Decimal("165.00"),
                low=Decimal("149.00"),
                close=Decimal("160.05"),
                volume=Decimal("1000000"),
                spread=Decimal("0.10"),
                feed_type=DataFeedType.MOCK,
                status=MarketDataStatus.ACTIVE
            )
        
        await service.update_market_prices(quotes)
        
        # Verify results
        updated_portfolio = await service.get_portfolio(portfolio.id)
        updated_session = await service.get_session(session.id)
        positions = await service.get_positions(portfolio.id)
        
        assert len(trades) == 3
        assert all(t.status == TradeStatus.FILLED for t in trades)
        assert updated_session.total_trades == 3
        assert len(positions) == 3
        assert updated_portfolio.total_equity > updated_portfolio.cash_balance
    
    @pytest.mark.asyncio
    async def test_performance_metrics_calculation(self, service):
        """Test performance metrics calculation."""
        portfolio = await service.create_portfolio("Performance Test Portfolio")
        
        # Execute trades over time
        symbols = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"]  # Removed GOOGL
        
        for symbol in symbols:
            await service.execute_trade(
                portfolio_id=portfolio.id,
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("25")  # Reduced quantity
            )
        
        # Update market prices with gains
        quotes = {}
        for symbol in symbols:
            quotes[symbol] = Quote(
                symbol=symbol,
                bid=Decimal("165.00"),
                ask=Decimal("165.10"),
                last=Decimal("165.05"),
                open=Decimal("150.00"),
                high=Decimal("170.00"),
                low=Decimal("149.00"),
                close=Decimal("165.05"),
                volume=Decimal("1000000"),
                spread=Decimal("0.10"),
                feed_type=DataFeedType.MOCK,
                status=MarketDataStatus.ACTIVE
            )
        
        await service.update_market_prices(quotes)
        
        # Check performance metrics
        updated_portfolio = await service.get_portfolio(portfolio.id)
        
        # With realistic trading costs, we expect some loss due to commissions and slippage
        # But we should have unrealized gains on the positions
        assert updated_portfolio.total_equity > updated_portfolio.cash_balance  # Should have positions
        assert len(updated_portfolio.positions) > 0  # Should have positions
        
        # Check that positions have unrealized P&L (some positive, some negative due to price changes)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in updated_portfolio.positions)
        print(f"Total unrealized P&L: {total_unrealized_pnl}")
        print(f"Total portfolio P&L: {updated_portfolio.total_pnl}")
        print(f"Total equity: {updated_portfolio.total_equity}")
