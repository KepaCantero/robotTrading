"""
Tests for Database System
TASK-6: Configuracion de base de datos
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock, patch
import uuid

import pytest
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    Unicode,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.infrastructure.persistence.database import (
    DatabaseManager,
    DatabaseSession,
    check_database_health,
    database_transaction,
    get_sync_db,
    initialize_database,
)
from app.infrastructure.persistence.database._base_repository import BaseRepository
from app.infrastructure.persistence.database.models import (
    Position,
    Signal,
    Trade,
    User,
)
from app.infrastructure.persistence.database.repositories import (
    AssetRepository,
    PortfolioRepository,
    UserRepository,
)


# ---------------------------------------------------------------------------
# SQLite-compatible test models
# ---------------------------------------------------------------------------
# The production models use PostgreSQL-specific features (native UUID column
# type, regex-based CHECK constraints) that SQLite cannot handle.  Rather than
# requiring a live Postgres instance we define lightweight, SQLite-compatible
# table definitions that mirror the *structure* of the real models so that
# basic CRUD behaviour can be verified in-memory.
# ---------------------------------------------------------------------------

# SQLite does not have a native UUID type.  We use a simple String(36) stand-in
# that stores UUIDs in their hyphenated textual form.
class _SQLiteUUID(TypeDecorator):
    """Platform-independent UUID type that stores values as String(36)."""

    impl = String(36)
    cache_ok = True


class _TestBase(DeclarativeBase):
    metadata = MetaData()


class _TestUser(_TestBase):
    __tablename__ = "users"

    id = Column(_SQLiteUUID, primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class _TestPortfolio(_TestBase):
    __tablename__ = "portfolios"

    id = Column(_SQLiteUUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(_SQLiteUUID, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    initial_cash = Column(Numeric(15, 2), nullable=False)
    current_cash = Column(Numeric(15, 2), nullable=False)
    total_value = Column(Numeric(15, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class _TestAsset(_TestBase):
    __tablename__ = "assets"

    id = Column(_SQLiteUUID, primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    asset_class = Column(String(50), nullable=False)
    exchange = Column(String(50), nullable=True)
    currency = Column(String(3), nullable=False, default="USD")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class _TestPosition(_TestBase):
    __tablename__ = "positions"

    id = Column(_SQLiteUUID, primary_key=True)
    portfolio_id = Column(_SQLiteUUID, nullable=False)
    asset_id = Column(_SQLiteUUID, nullable=False)
    quantity = Column(Numeric(15, 8), nullable=False)
    average_price = Column(Numeric(15, 4), nullable=False)
    current_price = Column(Numeric(15, 4), nullable=True)


class _TestTrade(_TestBase):
    __tablename__ = "trades"

    id = Column(_SQLiteUUID, primary_key=True)
    portfolio_id = Column(_SQLiteUUID, nullable=False)
    asset_id = Column(_SQLiteUUID, nullable=False)
    side = Column(String(4), nullable=False)
    quantity = Column(Numeric(15, 8), nullable=False)
    price = Column(Numeric(15, 4), nullable=False)
    commission = Column(Numeric(15, 4), nullable=False)
    total_cost = Column(Numeric(15, 2), nullable=False)
    status = Column(String(20), nullable=False, default="FILLED")


class _TestMarketData(_TestBase):
    __tablename__ = "market_data"

    id = Column(_SQLiteUUID, primary_key=True)
    asset_id = Column(_SQLiteUUID, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open_price = Column(Numeric(15, 4), nullable=False)
    high_price = Column(Numeric(15, 4), nullable=False)
    low_price = Column(Numeric(15, 4), nullable=False)
    close_price = Column(Numeric(15, 4), nullable=False)
    volume = Column(Numeric(20, 0), nullable=False)


class _TestSignal(_TestBase):
    __tablename__ = "signals"

    id = Column(_SQLiteUUID, primary_key=True)
    asset_id = Column(_SQLiteUUID, nullable=False)
    strategy_name = Column(String(100), nullable=False)
    signal_type = Column(String(10), nullable=False)
    strength = Column(String(20), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False)
    price = Column(Numeric(15, 4), nullable=False)
    volume = Column(Numeric(15, 8), nullable=True)
    meta_data = Column(JSON, nullable=False, default=dict)


class _TestBacktest(_TestBase):
    __tablename__ = "backtests"

    id = Column(_SQLiteUUID, primary_key=True)
    portfolio_id = Column(_SQLiteUUID, nullable=False)
    strategy_name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)
    final_capital = Column(Numeric(15, 2), nullable=False)
    total_return = Column(Numeric(8, 4), nullable=False)
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)
    max_drawdown = Column(Numeric(8, 4), nullable=True)
    total_trades = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="COMPLETED")


# ===========================================================================
# Test classes
# ===========================================================================


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest.fixture(autouse=True)
    def _reset_global_db_manager(self):
        """Ensure the module-level _db_manager is reset after each test."""
        import app.infrastructure.persistence.database as db_mod

        original = db_mod._db_manager
        db_mod._db_manager = None
        yield
        db_mod._db_manager = original

    @pytest.fixture
    def db_manager(self):
        """Create DatabaseManager instance."""
        with patch(
            "app.shared.config.base.environment_config.get_config"
        ) as mock_config:
            mock_config.return_value.database.connection_string = (
                "sqlite:///:memory:"
            )
            mock_config.return_value.debug = False
            mock_config.return_value.database.db_pool_size = 5
            mock_config.return_value.database.db_max_overflow = 10
            mock_config.return_value.database.db_pool_timeout = 30

            manager = DatabaseManager()
            return manager

    def test_database_manager_initialization(self, db_manager):
        """Test DatabaseManager initialization."""
        assert db_manager.config is not None
        assert db_manager.sync_engine is None
        assert db_manager.async_engine is None

    def test_initialize_sync_engine(self, db_manager):
        """Test sync engine initialization."""
        db_manager.initialize_sync_engine()

        assert db_manager.sync_engine is not None
        assert db_manager.session_factory is not None

    def test_create_tables(self, db_manager):
        """Test table creation."""
        db_manager.initialize_sync_engine()
        db_manager.create_tables()

        # Tables should be created without error
        assert True

    def test_get_sync_session(self, db_manager):
        """Test getting sync session."""
        db_manager.initialize_sync_engine()
        session = db_manager.get_sync_session()

        assert session is not None
        session.close()

    def test_close_connections(self, db_manager):
        """Test closing connections."""
        db_manager.initialize_sync_engine()
        db_manager.close_connections()

        # Should not raise exception
        assert True


class TestDatabaseModels:
    """Tests for database models using SQLite-compatible schema."""

    @pytest.fixture
    def db_session(self):
        """Create database session for testing with SQLite-compatible tables."""
        engine = create_engine("sqlite:///:memory:")
        _TestBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_user_model(self, db_session):
        """Test User model."""
        user = _TestUser(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None

    def test_portfolio_model(self, db_session):
        """Test Portfolio model."""
        user = _TestUser(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = _TestPortfolio(
            user_id=user.id,
            name="Test Portfolio",
            description="Test portfolio description",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        db_session.add(portfolio)
        db_session.commit()

        assert portfolio.id is not None
        assert portfolio.user_id == user.id
        assert portfolio.name == "Test Portfolio"
        assert portfolio.initial_cash == Decimal("10000.00")
        assert portfolio.is_active is True

    def test_asset_model(self, db_session):
        """Test Asset model."""
        asset = _TestAsset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class="stock",
            exchange="NASDAQ",
            currency="USD",
        )
        db_session.add(asset)
        db_session.commit()

        assert asset.id is not None
        assert asset.symbol == "AAPL"
        assert asset.name == "Apple Inc."
        assert asset.asset_class == "stock"
        assert asset.exchange == "NASDAQ"
        assert asset.currency == "USD"
        assert asset.is_active is True

    def test_position_model(self, db_session):
        """Test Position model."""
        user = _TestUser(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = _TestPortfolio(
            user_id=user.id,
            name="Test Portfolio",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        db_session.add(portfolio)
        db_session.commit()

        asset = _TestAsset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        position = _TestPosition(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            quantity=Decimal("100.0"),
            average_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
        )
        db_session.add(position)
        db_session.commit()

        assert position.id is not None
        assert position.portfolio_id == portfolio.id
        assert position.asset_id == asset.id
        assert position.quantity == Decimal("100.0")
        assert position.average_price == Decimal("150.00")

    def test_trade_model(self, db_session):
        """Test Trade model."""
        user = _TestUser(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = _TestPortfolio(
            user_id=user.id,
            name="Test Portfolio",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        db_session.add(portfolio)
        db_session.commit()

        asset = _TestAsset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        trade = _TestTrade(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            side="BUY",
            quantity=Decimal("100.0"),
            price=Decimal("150.00"),
            commission=Decimal("1.50"),
            total_cost=Decimal("15001.50"),
        )
        db_session.add(trade)
        db_session.commit()

        assert trade.id is not None
        assert trade.portfolio_id == portfolio.id
        assert trade.asset_id == asset.id
        assert trade.side == "BUY"
        assert trade.quantity == Decimal("100.0")
        assert trade.price == Decimal("150.00")
        assert trade.status == "FILLED"

    def test_market_data_model(self, db_session):
        """Test MarketData model."""
        asset = _TestAsset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        market_data = _TestMarketData(
            asset_id=asset.id,
            timestamp=datetime.utcnow(),
            open_price=Decimal("150.00"),
            high_price=Decimal("155.00"),
            low_price=Decimal("148.00"),
            close_price=Decimal("152.00"),
            volume=Decimal("1000000"),
        )
        db_session.add(market_data)
        db_session.commit()

        assert market_data.id is not None
        assert market_data.asset_id == asset.id
        assert market_data.open_price == Decimal("150.00")
        assert market_data.high_price == Decimal("155.00")
        assert market_data.low_price == Decimal("148.00")
        assert market_data.close_price == Decimal("152.00")
        assert market_data.volume == Decimal("1000000")

    def test_signal_model(self, db_session):
        """Test Signal model."""
        asset = _TestAsset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        signal = _TestSignal(
            asset_id=asset.id,
            strategy_name="momentum",
            signal_type="BUY",
            strength="STRONG",
            confidence=Decimal("85.0"),
            price=Decimal("150.00"),
            volume=Decimal("100.0"),
            meta_data={"test": "data"},
        )
        db_session.add(signal)
        db_session.commit()

        assert signal.id is not None
        assert signal.asset_id == asset.id
        assert signal.strategy_name == "momentum"
        assert signal.signal_type == "BUY"
        assert signal.strength == "STRONG"
        assert signal.confidence == Decimal("85.0")

    def test_backtest_model(self, db_session):
        """Test Backtest model."""
        user = _TestUser(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = _TestPortfolio(
            user_id=user.id,
            name="Test Portfolio",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        db_session.add(portfolio)
        db_session.commit()

        backtest = _TestBacktest(
            portfolio_id=portfolio.id,
            strategy_name="momentum",
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            initial_capital=Decimal("10000.00"),
            final_capital=Decimal("10500.00"),
            total_return=Decimal("5.0"),
            sharpe_ratio=Decimal("1.2"),
            max_drawdown=Decimal("2.0"),
            total_trades=50,
        )
        db_session.add(backtest)
        db_session.commit()

        assert backtest.id is not None
        assert backtest.portfolio_id == portfolio.id
        assert backtest.strategy_name == "momentum"
        assert backtest.initial_capital == Decimal("10000.00")
        assert backtest.final_capital == Decimal("10500.00")
        assert backtest.total_return == Decimal("5.0")
        assert backtest.status == "COMPLETED"


class TestRepositories:
    """Tests for repository classes."""

    @pytest.fixture
    def db_session(self):
        """Create database session for testing with SQLite-compatible tables."""
        engine = create_engine("sqlite:///:memory:")
        _TestBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_base_repository_create(self, db_session):
        """Test BaseRepository create method."""
        repo = BaseRepository(_TestUser, db_session)

        user = repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_base_repository_get_by_id(self, db_session):
        """Test BaseRepository get_by_id method."""
        repo = BaseRepository(_TestUser, db_session)

        user = repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        retrieved_user = repo.get_by_id(user.id)
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"

    def test_base_repository_update(self, db_session):
        """Test BaseRepository update method."""
        repo = BaseRepository(_TestUser, db_session)

        user = repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        updated_user = repo.update(user.id, username="updateduser")
        assert updated_user is not None
        assert updated_user.username == "updateduser"

    def test_base_repository_delete(self, db_session):
        """Test BaseRepository delete method."""
        repo = BaseRepository(_TestUser, db_session)

        user = repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        result = repo.delete(user.id)
        assert result is True

        deleted_user = repo.get_by_id(user.id)
        assert deleted_user is None

    def test_user_repository_get_by_username(self, db_session):
        """Test UserRepository get_by_username method."""
        repo = UserRepository(_TestUser, db_session)

        repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        retrieved_user = repo.get_by_username("testuser")
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"

    def test_user_repository_get_by_email(self, db_session):
        """Test UserRepository get_by_email method."""
        repo = UserRepository(_TestUser, db_session)

        repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        retrieved_user = repo.get_by_email("test@example.com")
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"

    def test_asset_repository_get_by_symbol(self, db_session):
        """Test AssetRepository get_by_symbol method."""
        repo = AssetRepository(_TestAsset, db_session)

        repo.create(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        retrieved_asset = repo.get_by_symbol("AAPL")
        assert retrieved_asset is not None
        assert retrieved_asset.symbol == "AAPL"

    def test_portfolio_repository_get_by_user(self, db_session):
        """Test PortfolioRepository get_by_user method."""
        user_repo = UserRepository(_TestUser, db_session)
        portfolio_repo = PortfolioRepository(_TestPortfolio, db_session)

        user = user_repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        portfolio_repo.create(
            user_id=user.id,
            name="Test Portfolio",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        portfolios = portfolio_repo.get_by_user(user.id)
        assert len(portfolios) == 1
        assert portfolios[0].name == "Test Portfolio"


class TestDatabaseUtilities:
    """Tests for database utility functions."""

    @pytest.fixture(autouse=True)
    def _reset_global_db_manager(self):
        """Ensure the module-level _db_manager is reset around each test."""
        import app.infrastructure.persistence.database as db_mod

        original = db_mod._db_manager
        db_mod._db_manager = None
        yield
        db_mod._db_manager = original

    def test_database_session_context_manager(self):
        """Test DatabaseSession context manager."""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_sync_session.return_value = mock_session

        with patch(
            "app.infrastructure.persistence.database._get_db_manager",
            return_value=mock_manager,
        ):
            with DatabaseSession() as session:
                assert session == mock_session

            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_database_session_context_manager_with_exception(self):
        """Test DatabaseSession context manager with exception."""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_sync_session.return_value = mock_session

        with patch(
            "app.infrastructure.persistence.database._get_db_manager",
            return_value=mock_manager,
        ):
            try:
                with DatabaseSession():
                    raise ValueError("Test exception")
            except ValueError:
                pass

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    def test_database_transaction_decorator(self):
        """Test database_transaction decorator."""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_sync_session.return_value = mock_session

        with patch(
            "app.infrastructure.persistence.database._get_db_manager",
            return_value=mock_manager,
        ):

            @database_transaction
            def test_function(session, value):
                return value * 2

            result = test_function(5)
            assert result == 10
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_check_database_health(self):
        """Test database health check."""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_sync_session.return_value = mock_session

        with patch(
            "app.infrastructure.persistence.database._get_db_manager",
            return_value=mock_manager,
        ):
            result = check_database_health()
            assert result is True
            # Verify execute was called with a text clause containing SELECT 1
            mock_session.execute.assert_called_once()
            call_arg = mock_session.execute.call_args[0][0]
            assert str(call_arg) == "SELECT 1"
            mock_session.close.assert_called_once()

    def test_check_database_health_failure(self):
        """Test database health check failure."""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Database error")
        mock_manager.get_sync_session.return_value = mock_session

        with patch(
            "app.infrastructure.persistence.database._get_db_manager",
            return_value=mock_manager,
        ):
            result = check_database_health()
            assert result is False
            mock_session.close.assert_called_once()


class TestDatabaseIntegration:
    """Tests for database integration."""

    @pytest.fixture(autouse=True)
    def _reset_global_db_manager(self):
        """Ensure the module-level _db_manager is reset around each test."""
        import app.infrastructure.persistence.database as db_mod

        original = db_mod._db_manager
        db_mod._db_manager = None
        yield
        db_mod._db_manager = original

    def test_initialize_database(self):
        """Test database initialization."""
        mock_manager = MagicMock()

        with patch(
            "app.infrastructure.persistence.database._get_db_manager",
            return_value=mock_manager,
        ):
            initialize_database()

            mock_manager.initialize_sync_engine.assert_called_once()
            mock_manager.initialize_async_engine.assert_called_once()
            mock_manager.create_tables.assert_called_once()

    def test_get_sync_db_dependency(self):
        """Test get_sync_db dependency function."""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_sync_session.return_value = mock_session

        with patch(
            "app.infrastructure.persistence.database._get_db_manager",
            return_value=mock_manager,
        ):
            # get_sync_db is a @contextlib.contextmanager, use with-statement
            with get_sync_db() as session:
                assert session == mock_session

            mock_session.close.assert_called_once()
