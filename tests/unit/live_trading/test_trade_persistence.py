"""
T18.3: Live Trading Bridge - Trade Persistence Tests

Tests for the trade persistence layer with SQLAlchemy ORM models.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services.live_trading.trade_persistence import (
    Base,
    OrderRecord,
    PositionHistory,
    TradePersistenceManager,
    TradeRecord,
)


@pytest_asyncio.fixture
async def test_db():
    """Create in-memory test database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def persistence_manager(test_db):
    """Create persistence manager with test database."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    manager = TradePersistenceManager()

    # Create session factory for test database
    async_session_factory = async_sessionmaker(
        bind=test_db,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create a session factory that yields sessions
    def get_session_factory():
        async def factory():
            async with async_session_factory() as session:
                yield session

        return factory

    manager.session_factory = get_session_factory()
    yield manager
    # No shutdown needed for mock


class TestOrderRecordModel:
    """Test OrderRecord ORM model."""

    def test_order_record_creation(self):
        """Test creating an order record."""
        order = OrderRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="LIMIT",
            status="PENDING",
            broker_name="interactive_brokers",
        )

        assert order.symbol == "AAPL"
        assert order.side == "BUY"
        assert order.quantity == Decimal("100")
        assert order.order_type == "LIMIT"
        assert order.status == "PENDING"

    def test_order_record_to_dict(self):
        """Test converting order to dictionary."""
        order = OrderRecord(
            order_id="order_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="LIMIT",
            status="EXECUTED",
            broker_name="interactive_brokers",
        )

        order_dict = order.to_dict()

        assert order_dict["order_id"] == "order_123"
        assert order_dict["symbol"] == "AAPL"
        assert order_dict["side"] == "BUY"
        assert order_dict["status"] == "EXECUTED"


class TestTradeRecordModel:
    """Test TradeRecord ORM model."""

    def test_trade_record_creation(self):
        """Test creating a trade record."""
        trade = TradeRecord(
            order_id="order_123",
            symbol="AAPL",
            quantity=Decimal("100"),
            execution_price=Decimal("150.50"),
            execution_time=datetime.utcnow(),
            commission=Decimal("5.00"),
            slippage=Decimal("0.10"),
            side="BUY",
            fill_type="FULL",
        )

        assert trade.symbol == "AAPL"
        assert trade.quantity == Decimal("100")
        assert trade.execution_price == Decimal("150.50")
        assert trade.commission == Decimal("5.00")

    def test_trade_record_to_dict(self):
        """Test converting trade to dictionary."""
        now = datetime.utcnow()
        trade = TradeRecord(
            trade_id="trade_123",
            order_id="order_123",
            symbol="AAPL",
            quantity=Decimal("100"),
            execution_price=Decimal("150.50"),
            execution_time=now,
            commission=Decimal("5.00"),
            slippage=Decimal("0.10"),
            side="BUY",
            fill_type="FULL",
        )

        trade_dict = trade.to_dict()

        assert trade_dict["trade_id"] == "trade_123"
        assert trade_dict["symbol"] == "AAPL"
        assert float(trade_dict["commission"]) == 5.0


class TestPositionHistoryModel:
    """Test PositionHistory ORM model."""

    def test_position_history_creation(self):
        """Test creating a position history record."""
        position = PositionHistory(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            quantity=Decimal("100"),
            average_price=Decimal("150.00"),
            market_value=Decimal("15000.00"),
            unrealized_pnl=Decimal("500.00"),
            unrealized_pnl_pct=Decimal("3.45"),
            cost_basis=Decimal("15000.00"),
        )

        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.unrealized_pnl_pct == Decimal("3.45")

    def test_position_history_to_dict(self):
        """Test converting position to dictionary."""
        now = datetime.utcnow()
        position = PositionHistory(
            position_id="pos_123",
            symbol="AAPL",
            timestamp=now,
            quantity=Decimal("100"),
            average_price=Decimal("150.00"),
            market_value=Decimal("15000.00"),
            unrealized_pnl=Decimal("500.00"),
            unrealized_pnl_pct=Decimal("3.45"),
            cost_basis=Decimal("15000.00"),
        )

        pos_dict = position.to_dict()

        assert pos_dict["position_id"] == "pos_123"
        assert float(pos_dict["unrealized_pnl"]) == 500.0


class TestTradePersistenceManager:
    """Test TradePersistenceManager."""

    @pytest.mark.asyncio
    async def test_manager_initialization(self, persistence_manager):
        """Test manager initialization."""
        assert persistence_manager.session_factory is not None

    @pytest.mark.asyncio
    async def test_save_order(self, persistence_manager):
        """Test saving an order."""
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "PENDING",
            "broker_name": "interactive_brokers",
        }

        order_id = await persistence_manager.save_order(order_data)

        assert order_id is not None
        assert len(order_id) > 0

    @pytest.mark.asyncio
    async def test_get_order(self, persistence_manager):
        """Test retrieving an order."""
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "PENDING",
            "broker_name": "interactive_brokers",
        }

        order_id = await persistence_manager.save_order(order_data)
        retrieved = await persistence_manager.get_order(order_id)

        assert retrieved is not None
        assert retrieved["symbol"] == "AAPL"
        assert retrieved["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_save_trade(self, persistence_manager):
        """Test saving a trade."""
        # First create an order
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "EXECUTED",
            "broker_name": "interactive_brokers",
        }
        order_id = await persistence_manager.save_order(order_data)

        # Now save a trade
        trade_data = {
            "order_id": order_id,
            "symbol": "AAPL",
            "quantity": 100,
            "execution_price": 150.50,
            "execution_time": datetime.utcnow(),
            "commission": 5.00,
            "slippage": 0.10,
            "side": "BUY",
            "fill_type": "FULL",
        }

        trade_id = await persistence_manager.save_trade(trade_data)

        assert trade_id is not None
        assert len(trade_id) > 0

    @pytest.mark.asyncio
    async def test_get_trades_by_symbol(self, persistence_manager):
        """Test retrieving trades by symbol."""
        # Create an order
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "EXECUTED",
            "broker_name": "interactive_brokers",
        }
        order_id = await persistence_manager.save_order(order_data)

        # Create multiple trades
        for i in range(3):
            trade_data = {
                "order_id": order_id,
                "symbol": "AAPL",
                "quantity": 100 + i * 10,
                "execution_price": 150.50 + i * 0.1,
                "execution_time": datetime.utcnow(),
                "commission": 5.00,
                "slippage": 0.10,
                "side": "BUY",
                "fill_type": "PARTIAL" if i < 2 else "FULL",
            }
            await persistence_manager.save_trade(trade_data)

        # Retrieve trades
        trades = await persistence_manager.get_trades_by_symbol("AAPL")

        assert len(trades) == 3
        assert all(t["symbol"] == "AAPL" for t in trades)

    @pytest.mark.asyncio
    async def test_get_trades_by_date_range(self, persistence_manager):
        """Test retrieving trades by date range."""
        # Create an order
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "EXECUTED",
            "broker_name": "interactive_brokers",
        }
        order_id = await persistence_manager.save_order(order_data)

        now = datetime.utcnow()
        past = now - timedelta(days=1)
        future = now + timedelta(days=1)

        # Create trade
        trade_data = {
            "order_id": order_id,
            "symbol": "AAPL",
            "quantity": 100,
            "execution_price": 150.50,
            "execution_time": now,
            "commission": 5.00,
            "slippage": 0.10,
            "side": "BUY",
            "fill_type": "FULL",
        }
        await persistence_manager.save_trade(trade_data)

        # Retrieve trades within range
        trades = await persistence_manager.get_trades_by_date_range(past, future)

        assert len(trades) >= 1

    @pytest.mark.asyncio
    async def test_save_position_snapshot(self, persistence_manager):
        """Test saving a position snapshot."""
        position_data = {
            "symbol": "AAPL",
            "timestamp": datetime.utcnow(),
            "quantity": 100,
            "average_price": 150.00,
            "market_value": 15000.00,
            "unrealized_pnl": 500.00,
            "unrealized_pnl_pct": 3.45,
            "cost_basis": 15000.00,
        }

        position_id = await persistence_manager.save_position_snapshot(position_data)

        assert position_id is not None
        assert len(position_id) > 0

    @pytest.mark.asyncio
    async def test_get_position_history(self, persistence_manager):
        """Test retrieving position history."""
        # Create multiple position snapshots
        for i in range(5):
            position_data = {
                "symbol": "AAPL",
                "timestamp": datetime.utcnow() - timedelta(days=i),
                "quantity": 100 + i * 10,
                "average_price": 150.00 - i * 0.5,
                "market_value": 15000.00 + i * 500,
                "unrealized_pnl": 500.00 + i * 100,
                "unrealized_pnl_pct": 3.45 + i * 0.5,
                "cost_basis": 15000.00,
            }
            await persistence_manager.save_position_snapshot(position_data)

        # Retrieve history
        positions = await persistence_manager.get_position_history("AAPL", limit=3)

        assert len(positions) <= 3
        assert all(p["symbol"] == "AAPL" for p in positions)

    @pytest.mark.asyncio
    async def test_update_order_status(self, persistence_manager):
        """Test updating order status."""
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "PENDING",
            "broker_name": "interactive_brokers",
        }

        order_id = await persistence_manager.save_order(order_data)

        # Update status
        success = await persistence_manager.update_order_status(
            order_id, "EXECUTED", datetime.utcnow()
        )

        assert success is True

        # Verify update
        updated = await persistence_manager.get_order(order_id)
        assert updated["status"] == "EXECUTED"

    @pytest.mark.asyncio
    async def test_count_trades(self, persistence_manager):
        """Test counting trades."""
        # Create an order
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "EXECUTED",
            "broker_name": "interactive_brokers",
        }
        order_id = await persistence_manager.save_order(order_data)

        # Create multiple trades for different symbols
        symbols = ["AAPL", "GOOGL", "MSFT"]
        for symbol in symbols:
            trade_data = {
                "order_id": order_id,
                "symbol": symbol,
                "quantity": 100,
                "execution_price": 150.50,
                "execution_time": datetime.utcnow(),
                "commission": 5.00,
                "slippage": 0.10,
                "side": "BUY",
                "fill_type": "FULL",
            }
            await persistence_manager.save_trade(trade_data)

        # Count all trades
        total = await persistence_manager.count_trades()
        assert total >= 3

        # Count trades for specific symbol
        aapl_count = await persistence_manager.count_trades("AAPL")
        assert aapl_count >= 1

    @pytest.mark.asyncio
    async def test_order_with_relationship(self, persistence_manager):
        """Test order-trade relationship."""
        # Create an order
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.00,
            "order_type": "LIMIT",
            "status": "EXECUTED",
            "broker_name": "interactive_brokers",
        }
        order_id = await persistence_manager.save_order(order_data)

        # Create related trades
        for i in range(2):
            trade_data = {
                "order_id": order_id,
                "symbol": "AAPL",
                "quantity": 50,
                "execution_price": 150.50,
                "execution_time": datetime.utcnow(),
                "commission": 2.50,
                "slippage": 0.10,
                "side": "BUY",
                "fill_type": "PARTIAL" if i == 0 else "FULL",
            }
            await persistence_manager.save_trade(trade_data)

        # Verify trades were created
        trades = await persistence_manager.get_trades_by_symbol("AAPL")
        assert len(trades) >= 2

    @pytest.mark.asyncio
    async def test_error_handling_invalid_order(self, persistence_manager):
        """Test error handling for invalid operations."""
        # Try to get non-existent order
        result = await persistence_manager.get_order("non_existent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_symbols_tracking(self, persistence_manager):
        """Test tracking trades for multiple symbols."""
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]

        for symbol in symbols:
            order_data = {
                "symbol": symbol,
                "side": "BUY",
                "quantity": 100,
                "price": 150.00,
                "order_type": "LIMIT",
                "status": "EXECUTED",
                "broker_name": "interactive_brokers",
            }
            order_id = await persistence_manager.save_order(order_data)

            trade_data = {
                "order_id": order_id,
                "symbol": symbol,
                "quantity": 100,
                "execution_price": 150.50,
                "execution_time": datetime.utcnow(),
                "commission": 5.00,
                "slippage": 0.10,
                "side": "BUY",
                "fill_type": "FULL",
            }
            await persistence_manager.save_trade(trade_data)

        # Verify trades for each symbol
        for symbol in symbols:
            trades = await persistence_manager.get_trades_by_symbol(symbol)
            assert len(trades) >= 1
            assert trades[0]["symbol"] == symbol


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
