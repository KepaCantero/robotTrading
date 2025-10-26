"""
Tests for Database System
TASK-6: Configuración de base de datos
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import (Base, DatabaseManager, DatabaseSession,
                          async_database_transaction, check_database_health,
                          database_transaction, get_async_db, get_sync_db,
                          initialize_database)
from app.database.models import (APIKey, Asset, Backtest, MarketData,
                                 Portfolio, Position, RiskMetrics, Signal,
                                 SystemLog, Trade, User)
from app.database.repositories import (AssetRepository, BacktestRepository,
                                       BaseRepository, MarketDataRepository,
                                       PortfolioRepository, PositionRepository,
                                       RiskMetricsRepository, SignalRepository,
                                       SystemLogRepository, TradeRepository,
                                       UserRepository)
from app.exceptions import DatabaseError
from app.models.signal import SignalSource, SignalStrength, SignalType


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest.fixture
    def db_manager(self):
        """Create DatabaseManager instance."""
        with patch("app.database.get_config") as mock_config:
            mock_config.return_value.database.connection_string = "sqlite:///:memory:"
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
    """Tests for database models."""

    @pytest.fixture
    def db_session(self):
        """Create database session for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_user_model(self, db_session):
        """Test User model."""
        user = User(
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
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = Portfolio(
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
        asset = Asset(
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
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = Portfolio(
            user_id=user.id,
            name="Test Portfolio",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        db_session.add(portfolio)
        db_session.commit()

        asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        position = Position(
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
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = Portfolio(
            user_id=user.id,
            name="Test Portfolio",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        db_session.add(portfolio)
        db_session.commit()

        asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        trade = Trade(
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
        asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        market_data = MarketData(
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
        asset = Asset(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        db_session.add(asset)
        db_session.commit()

        signal = Signal(
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
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        portfolio = Portfolio(
            user_id=user.id,
            name="Test Portfolio",
            initial_cash=Decimal("10000.00"),
            current_cash=Decimal("10000.00"),
            total_value=Decimal("10000.00"),
        )
        db_session.add(portfolio)
        db_session.commit()

        backtest = Backtest(
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
        """Create database session for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_base_repository_create(self, db_session):
        """Test BaseRepository create method."""
        repo = BaseRepository(User, db_session)

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
        repo = BaseRepository(User, db_session)

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
        repo = BaseRepository(User, db_session)

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
        repo = BaseRepository(User, db_session)

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
        repo = UserRepository(User, db_session)

        user = repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        retrieved_user = repo.get_by_username("testuser")
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"

    def test_user_repository_get_by_email(self, db_session):
        """Test UserRepository get_by_email method."""
        repo = UserRepository(User, db_session)

        user = repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        retrieved_user = repo.get_by_email("test@example.com")
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"

    def test_asset_repository_get_by_symbol(self, db_session):
        """Test AssetRepository get_by_symbol method."""
        repo = AssetRepository(Asset, db_session)

        asset = repo.create(symbol="AAPL", name="Apple Inc.", asset_class="stock")
        retrieved_asset = repo.get_by_symbol("AAPL")
        assert retrieved_asset is not None
        assert retrieved_asset.symbol == "AAPL"

    def test_portfolio_repository_get_by_user(self, db_session):
        """Test PortfolioRepository get_by_user method."""
        user_repo = UserRepository(User, db_session)
        portfolio_repo = PortfolioRepository(Portfolio, db_session)

        user = user_repo.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        portfolio = portfolio_repo.create(
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

    def test_database_session_context_manager(self):
        """Test DatabaseSession context manager."""
        with patch("app.database.db_manager") as mock_manager:
            mock_session = MagicMock()
            mock_manager.get_sync_session.return_value = mock_session

            with DatabaseSession() as session:
                assert session == mock_session

            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_database_session_context_manager_with_exception(self):
        """Test DatabaseSession context manager with exception."""
        with patch("app.database.db_manager") as mock_manager:
            mock_session = MagicMock()
            mock_manager.get_sync_session.return_value = mock_session

            try:
                with DatabaseSession() as session:
                    raise ValueError("Test exception")
            except ValueError:
                pass

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    def test_database_transaction_decorator(self):
        """Test database_transaction decorator."""
        with patch("app.database.db_manager") as mock_manager:
            mock_session = MagicMock()
            mock_manager.get_sync_session.return_value = mock_session

            @database_transaction
            def test_function(session, value):
                return value * 2

            result = test_function(5)
            assert result == 10
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_check_database_health(self):
        """Test database health check."""
        with patch("app.database.db_manager") as mock_manager:
            mock_session = MagicMock()
            mock_manager.get_sync_session.return_value = mock_session

            result = check_database_health()
            assert result is True
            mock_session.execute.assert_called_once_with("SELECT 1")
            mock_session.close.assert_called_once()

    def test_check_database_health_failure(self):
        """Test database health check failure."""
        with patch("app.database.db_manager") as mock_manager:
            mock_session = MagicMock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_manager.get_sync_session.return_value = mock_session

            result = check_database_health()
            assert result is False
            mock_session.close.assert_called_once()


class TestDatabaseIntegration:
    """Tests for database integration."""

    def test_initialize_database(self):
        """Test database initialization."""
        with patch("app.database.db_manager") as mock_manager:
            initialize_database()

            mock_manager.initialize_sync_engine.assert_called_once()
            mock_manager.initialize_async_engine.assert_called_once()
            mock_manager.create_tables.assert_called_once()

    def test_get_sync_db_dependency(self):
        """Test get_sync_db dependency function."""
        with patch("app.database.db_manager") as mock_manager:
            mock_session = MagicMock()
            mock_manager.get_sync_session.return_value = mock_session

            db_gen = get_sync_db()
            session = next(db_gen)

            assert session == mock_session

            # Test cleanup
            try:
                next(db_gen)
            except StopIteration:
                pass

            mock_session.close.assert_called_once()
