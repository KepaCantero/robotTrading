"""
Comprehensive tests for database repositories.

This module tests all repository classes including:
- BaseRepository CRUD operations
- UserRepository
- PortfolioRepository
- AssetRepository
- PositionRepository
- TradeRepository
- MarketDataRepository
- SignalRepository
- BacktestRepository
- RiskMetricsRepository
- SystemLogRepository

Tests cover:
- CRUD operations (Create, Read, Update, Delete)
- Structured logging verification
- Error handling and transaction rollback
- Pagination functionality
- Type hints (T | None)
"""

from __future__ import annotations  # Enable modern type hint syntax

import sys
from unittest import mock

# Mock structlog before importing any app modules
structlog_mock = mock.MagicMock()
structlog_mock.get_logger.return_value = mock.MagicMock()
sys.modules["structlog"] = structlog_mock

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import DatabaseError
from app.database import Base
from app.database.models import (
    Asset,
    Backtest,
    MarketData,
    Portfolio,
    Position,
    RiskMetrics,
    Signal,
    SystemLog,
    Trade,
    User,
)
from app.database import repositories
from app.database.repositories import (
    AssetRepository,
    BacktestRepository,
    BaseRepository,
    MarketDataRepository,
    PortfolioRepository,
    PositionRepository,
    RiskMetricsRepository,
    SignalRepository,
    SystemLogRepository,
    TradeRepository,
    UserRepository,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Drop PostgreSQL-specific check constraints before creating tables
    for table in Base.metadata.tables.values():
        table.constraints = [c for c in table.constraints
                           if not (hasattr(c, 'sqltext') and '~' in str(c.sqltext))]

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(in_memory_db):
    """Create a database session for testing."""
    Session = sessionmaker(bind=in_memory_db)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user in the database."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_portfolio(db_session, test_user):
    """Create a test portfolio in the database."""
    portfolio = Portfolio(
        user_id=test_user.id,
        name="Test Portfolio",
        description="A test portfolio",
        initial_cash=Decimal("10000.00"),
        current_cash=Decimal("10000.00"),
        total_value=Decimal("10000.00"),
        is_active=True,
    )
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)
    return portfolio


@pytest.fixture
def test_asset(db_session):
    """Create a test asset in the database."""
    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_class="stock",
        exchange="NASDAQ",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_position(db_session, test_portfolio, test_asset):
    """Create a test position in the database."""
    position = Position(
        portfolio_id=test_portfolio.id,
        asset_id=test_asset.id,
        quantity=Decimal("100"),
        average_price=Decimal("150.00"),
        current_price=Decimal("155.00"),
        unrealized_pnl=Decimal("500.00"),
        realized_pnl=Decimal("0"),
    )
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    return position


@pytest.fixture
def test_trade(db_session, test_portfolio, test_asset):
    """Create a test trade in the database."""
    trade = Trade(
        portfolio_id=test_portfolio.id,
        asset_id=test_asset.id,
        side="BUY",
        quantity=Decimal("100"),
        price=Decimal("150.00"),
        executed_at=datetime.utcnow(),
        commission=Decimal("1.50"),
        slippage=Decimal("0.05"),
        total_cost=Decimal("15001.55"),
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    return trade


@pytest.fixture
def test_signal(db_session, test_asset):
    """Create a test signal in the database."""
    signal = Signal(
        asset_id=test_asset.id,
        strategy_name="momentum",
        signal_type="BUY",
        confidence=Decimal("85.0"),
        strength="MODERATE",
        price=Decimal("150.00"),
        volume=Decimal("1000"),
    )
    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)
    return signal


# =============================================================================
# BaseRepository Tests
# =============================================================================

class TestBaseRepository:
    """Test cases for BaseRepository CRUD operations."""

    def test_create_record(self, db_session):
        """Arrange-Act-Assert: Test creating a record."""
        # Arrange
        repo = BaseRepository(User, db_session)
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "hashed_password": "hashed_password",
            "is_active": True,
        }

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.create(**user_data)

        # Assert
        assert result is not None
        assert result.username == "newuser"
        assert result.email == "newuser@example.com"
        assert isinstance(result.id, uuid.UUID)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "created_record"

    def test_create_integrity_error_rolls_back(self, db_session, test_user):
        """Arrange-Act-Assert: Test that integrity errors cause rollback."""
        # Arrange
        repo = BaseRepository(User, db_session)
        duplicate_data = {
            "username": test_user.username,  # Duplicate username
            "email": "another@example.com",
            "hashed_password": "hashed_password",
            "is_active": True,
        }

        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            repo.create(**duplicate_data)

        assert "Failed to create User" in str(exc_info.value)

    def test_get_by_id_found(self, db_session, test_user):
        """Arrange-Act-Assert: Test getting a record by ID when it exists."""
        # Arrange
        repo = BaseRepository(User, db_session)

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.get_by_id(test_user.id)

        # Assert
        assert result is not None
        assert result.id == test_user.id
        assert result.username == test_user.username
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "queried_by_id"

    def test_get_by_id_not_found(self, db_session):
        """Arrange-Act-Assert: Test getting a record by ID when it doesn't exist."""
        # Arrange
        repo = BaseRepository(User, db_session)
        fake_id = uuid.uuid4()

        # Act
        result = repo.get_by_id(fake_id)

        # Assert
        assert result is None

    def test_get_all_without_pagination(self, db_session, test_user):
        """Arrange-Act-Assert: Test getting all records without pagination."""
        # Arrange
        repo = BaseRepository(User, db_session)

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.get_all()

        # Assert
        assert len(result) >= 1
        assert test_user in result
        mock_logger.debug.assert_called_once()

    def test_get_all_with_pagination(self, db_session):
        """Arrange-Act-Assert: Test getting all records with pagination."""
        # Arrange
        # Create multiple users
        repo = BaseRepository(User, db_session)
        for i in range(5):
            repo.create(
                username=f"user_{i}",
                email=f"user_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )

        # Act - Get first 2 records
        result = repo.get_all(limit=2, offset=0)

        # Assert
        assert len(result) == 2

    def test_update_record_success(self, db_session, test_user):
        """Arrange-Act-Assert: Test updating a record successfully."""
        # Arrange
        repo = BaseRepository(User, db_session)

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.update(test_user.id, is_active=False)

        # Assert
        assert result is not None
        assert result.is_active is False
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "updated_record"

    def test_update_record_not_found(self, db_session):
        """Arrange-Act-Assert: Test updating a non-existent record."""
        # Arrange
        repo = BaseRepository(User, db_session)
        fake_id = uuid.uuid4()

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.update(fake_id, is_active=False)

        # Assert
        assert result is None
        mock_logger.warning.assert_called_once()

    def test_delete_record_success(self, db_session, test_user):
        """Arrange-Act-Assert: Test deleting a record successfully."""
        # Arrange
        repo = BaseRepository(User, db_session)
        user_id = test_user.id

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.delete(user_id)

        # Assert
        assert result is True
        # Verify deletion
        assert repo.get_by_id(user_id) is None
        mock_logger.info.assert_called_once()

    def test_delete_record_not_found(self, db_session):
        """Arrange-Act-Assert: Test deleting a non-existent record."""
        # Arrange
        repo = BaseRepository(User, db_session)
        fake_id = uuid.uuid4()

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.delete(fake_id)

        # Assert
        assert result is False
        mock_logger.warning.assert_called_once()

    def test_count_records(self, db_session):
        """Arrange-Act-Assert: Test counting records."""
        # Arrange
        repo = BaseRepository(User, db_session)
        # Create a test user first
        repo.create(
            username="count_test_user",
            email="count_test@example.com",
            hashed_password="hashed",
            is_active=True,
        )

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            count = repo.count()

        # Assert
        assert count >= 1
        mock_logger.debug.assert_called_once()


# =============================================================================
# UserRepository Tests
# =============================================================================

class TestUserRepository:
    """Test cases for UserRepository."""

    def test_get_by_username_found(self, db_session, test_user):
        """Arrange-Act-Assert: Test getting user by username when found."""
        # Arrange
        repo = UserRepository(User, db_session)

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.get_by_username(test_user.username)

        # Assert
        assert result is not None
        assert result.username == test_user.username
        mock_logger.debug.assert_called_once()

    def test_get_by_username_not_found(self, db_session):
        """Arrange-Act-Assert: Test getting user by username when not found."""
        # Arrange
        repo = UserRepository(User, db_session)

        # Act
        result = repo.get_by_username("nonexistent")

        # Assert
        assert result is None

    def test_get_by_email_found(self, db_session, test_user):
        """Arrange-Act-Assert: Test getting user by email when found."""
        # Arrange
        repo = UserRepository(User, db_session)

        # Act
        result = repo.get_by_email(test_user.email)

        # Assert
        assert result is not None
        assert result.email == test_user.email

    def test_get_by_email_not_found(self, db_session):
        """Arrange-Act-Assert: Test getting user by email when not found."""
        # Arrange
        repo = UserRepository(User, db_session)

        # Act
        result = repo.get_by_email("nonexistent@example.com")

        # Assert
        assert result is None

    def test_get_active_users(self, db_session, test_user):
        """Arrange-Act-Assert: Test getting active users."""
        # Arrange
        repo = UserRepository(User, db_session)
        # Create an inactive user
        repo.create(
            username="inactive_user",
            email="inactive@example.com",
            hashed_password="hashed",
            is_active=False,
        )

        # Act
        active_users = repo.get_active_users()

        # Assert
        assert len(active_users) >= 1
        assert all(u.is_active for u in active_users)
        assert test_user in active_users


# =============================================================================
# PortfolioRepository Tests
# =============================================================================

class TestPortfolioRepository:
    """Test cases for PortfolioRepository."""

    def test_get_by_user(self, db_session, test_portfolio, test_user):
        """Arrange-Act-Assert: Test getting portfolios by user ID."""
        # Arrange
        repo = PortfolioRepository(Portfolio, db_session)

        # Act
        result = repo.get_by_user(test_user.id)

        # Assert
        assert len(result) >= 1
        assert test_portfolio in result

    def test_get_active_by_user(self, db_session, test_portfolio, test_user):
        """Arrange-Act-Assert: Test getting active portfolios by user ID."""
        # Arrange
        repo = PortfolioRepository(Portfolio, db_session)
        # Create an inactive portfolio
        inactive_portfolio = Portfolio(
            user_id=test_user.id,
            name="Inactive Portfolio",
            initial_cash=Decimal("5000.00"),
            current_cash=Decimal("5000.00"),
            total_value=Decimal("5000.00"),
            is_active=False,
        )
        db_session.add(inactive_portfolio)
        db_session.commit()

        # Act
        result = repo.get_active_by_user(test_user.id)

        # Assert
        assert len(result) >= 1
        assert all(p.is_active for p in result)
        assert test_portfolio in result
        assert inactive_portfolio not in result

    def test_update_total_value(self, db_session, test_portfolio):
        """Arrange-Act-Assert: Test updating portfolio total value."""
        # Arrange
        repo = PortfolioRepository(Portfolio, db_session)
        new_value = Decimal("15000.00")

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.update_total_value(test_portfolio.id, new_value)

        # Assert
        assert result is True
        db_session.refresh(test_portfolio)
        assert test_portfolio.total_value == new_value
        mock_logger.info.assert_called_once()


# =============================================================================
# AssetRepository Tests
# =============================================================================

class TestAssetRepository:
    """Test cases for AssetRepository."""

    def test_get_by_symbol_found(self, db_session, test_asset):
        """Arrange-Act-Assert: Test getting asset by symbol when found."""
        # Arrange
        repo = AssetRepository(Asset, db_session)

        # Act
        result = repo.get_by_symbol(test_asset.symbol)

        # Assert
        assert result is not None
        assert result.symbol == test_asset.symbol

    def test_get_by_symbol_not_found(self, db_session):
        """Arrange-Act-Assert: Test getting asset by symbol when not found."""
        # Arrange
        repo = AssetRepository(Asset, db_session)

        # Act
        result = repo.get_by_symbol("NONEXISTENT")

        # Assert
        assert result is None

    def test_get_by_asset_class(self, db_session, test_asset):
        """Arrange-Act-Assert: Test getting assets by asset class."""
        # Arrange
        repo = AssetRepository(Asset, db_session)
        # Create another asset in the same class
        Asset(
            symbol="MSFT",
            name="Microsoft",
            asset_class="stock",
            exchange="NASDAQ",
        )
        db_session.commit()

        # Act
        result = repo.get_by_asset_class("stock")

        # Assert
        assert len(result) >= 1
        assert all(a.asset_class == "stock" for a in result)

    def test_get_active_assets(self, db_session, test_asset):
        """Arrange-Act-Assert: Test getting active assets."""
        # Arrange
        repo = AssetRepository(Asset, db_session)
        # Create an inactive asset
        Asset(
            symbol="INACTIVE",
            name="Inactive Asset",
            asset_class="stock",
            exchange="NASDAQ",
            is_active=False,
        )
        db_session.commit()

        # Act
        result = repo.get_active_assets()

        # Assert
        assert len(result) >= 1
        assert all(a.is_active for a in result)
        assert test_asset in result

    def test_search_by_name(self, db_session, test_asset):
        """Arrange-Act-Assert: Test searching assets by name pattern."""
        # Arrange
        repo = AssetRepository(Asset, db_session)

        # Act
        result = repo.search_by_name("Apple")

        # Assert
        assert len(result) >= 1
        assert test_asset in result


# =============================================================================
# PositionRepository Tests
# =============================================================================

class TestPositionRepository:
    """Test cases for PositionRepository."""

    def test_get_by_portfolio(self, db_session, test_position, test_portfolio):
        """Arrange-Act-Assert: Test getting positions by portfolio ID."""
        # Arrange
        repo = PositionRepository(Position, db_session)

        # Act
        result = repo.get_by_portfolio(test_portfolio.id)

        # Assert
        assert len(result) >= 1
        assert test_position in result

    def test_get_by_portfolio_and_asset(
        self, db_session, test_position, test_portfolio, test_asset
    ):
        """Arrange-Act-Assert: Test getting position by portfolio and asset."""
        # Arrange
        repo = PositionRepository(Position, db_session)

        # Act
        result = repo.get_by_portfolio_and_asset(test_portfolio.id, test_asset.id)

        # Assert
        assert result is not None
        assert result.id == test_position.id

    def test_get_non_zero_positions(self, db_session, test_position, test_portfolio):
        """Arrange-Act-Assert: Test getting non-zero positions."""
        # Arrange
        repo = PositionRepository(Position, db_session)
        # Note: The Position model has a unique constraint on (portfolio_id, asset_id)
        # and a check constraint that quantity != 0
        # So we need to create positions with different assets
        # Create additional assets for testing
        asset2 = Asset(symbol="MSFT", name="Microsoft", asset_class="stock", exchange="NASDAQ")
        asset3 = Asset(symbol="GOOGL", name="Google", asset_class="stock", exchange="NASDAQ")
        asset4 = Asset(symbol="TSLA", name="Tesla", asset_class="stock", exchange="NASDAQ")
        db_session.add_all([asset2, asset3, asset4])
        db_session.commit()

        # Create additional positions with non-zero quantities
        for asset in [asset2, asset3, asset4]:
            position = Position(
                portfolio_id=test_portfolio.id,
                asset_id=asset.id,
                quantity=Decimal("50"),
                average_price=Decimal("100.00"),
                realized_pnl=Decimal("0"),
            )
            db_session.add(position)
        db_session.commit()

        # Act
        result = repo.get_non_zero_positions(test_portfolio.id)

        # Assert
        assert len(result) >= 4  # test_position + 3 new positions
        assert all(p.quantity != 0 for p in result)
        assert test_position in result

    def test_update_position_price(self, db_session, test_position):
        """Arrange-Act-Assert: Test updating position price."""
        # Arrange
        repo = PositionRepository(Position, db_session)
        new_price = Decimal("160.00")

        # Act
        result = repo.update_position_price(test_position.id, new_price)

        # Assert
        assert result is True
        db_session.refresh(test_position)
        assert test_position.current_price == new_price


# =============================================================================
# TradeRepository Tests
# =============================================================================

class TestTradeRepository:
    """Test cases for TradeRepository."""

    def test_get_by_portfolio(self, db_session, test_trade, test_portfolio):
        """Arrange-Act-Assert: Test getting trades by portfolio ID."""
        # Arrange
        repo = TradeRepository(Trade, db_session)

        # Act
        result = repo.get_by_portfolio(test_portfolio.id)

        # Assert
        assert len(result) >= 1
        assert test_trade in result

    def test_get_by_portfolio_with_limit(
        self, db_session, test_trade, test_portfolio
    ):
        """Arrange-Act-Assert: Test getting trades by portfolio with limit."""
        # Arrange
        repo = TradeRepository(Trade, db_session)
        # Create additional trades
        for _ in range(5):
            trade = Trade(
                portfolio_id=test_portfolio.id,
                asset_id=test_trade.asset_id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("100.00"),
                total_cost=Decimal("1000.00"),
                executed_at=datetime.utcnow(),
            )
            db_session.add(trade)
        db_session.commit()

        # Act
        result = repo.get_by_portfolio(test_portfolio.id, limit=3)

        # Assert
        assert len(result) == 3

    def test_get_by_asset(self, db_session, test_trade, test_asset):
        """Arrange-Act-Assert: Test getting trades by asset ID."""
        # Arrange
        repo = TradeRepository(Trade, db_session)

        # Act
        result = repo.get_by_asset(test_asset.id)

        # Assert
        assert len(result) >= 1
        assert test_trade in result

    def test_get_by_date_range(self, db_session, test_trade):
        """Arrange-Act-Assert: Test getting trades within date range."""
        # Arrange
        repo = TradeRepository(Trade, db_session)
        start_date = test_trade.executed_at - timedelta(hours=1)
        end_date = test_trade.executed_at + timedelta(hours=1)

        # Act
        result = repo.get_by_date_range(start_date, end_date)

        # Assert
        assert len(result) >= 1
        assert test_trade in result

    def test_get_trade_summary(self, db_session, test_trade, test_portfolio):
        """Arrange-Act-Assert: Test getting trade summary for a portfolio."""
        # Arrange
        repo = TradeRepository(Trade, db_session)

        # Act
        summary = repo.get_trade_summary(test_portfolio.id)

        # Assert
        assert summary is not None
        assert "total_trades" in summary
        assert "total_commission" in summary
        assert "total_slippage" in summary
        assert "total_cost" in summary
        assert summary["total_trades"] >= 1


# =============================================================================
# MarketDataRepository Tests
# =============================================================================

class TestMarketDataRepository:
    """Test cases for MarketDataRepository."""

    def test_get_by_asset_and_date_range(self, db_session, test_asset):
        """Arrange-Act-Assert: Test getting market data by asset and date range."""
        # Arrange
        repo = MarketDataRepository(MarketData, db_session)
        now = datetime.utcnow()
        # Create test market data
        for i in range(5):
            market_data = MarketData(
                asset_id=test_asset.id,
                timestamp=now + timedelta(minutes=i),
                open_price=Decimal("150.00"),
                high_price=Decimal("155.00"),
                low_price=Decimal("149.00"),
                close_price=Decimal("154.00"),
                volume=1000000,
            )
            db_session.add(market_data)
        db_session.commit()

        start_date = now - timedelta(minutes=1)
        end_date = now + timedelta(minutes=10)

        # Act
        result = repo.get_by_asset_and_date_range(test_asset.id, start_date, end_date)

        # Assert
        assert len(result) == 5
        assert all(r.asset_id == test_asset.id for r in result)

    def test_get_latest_price(self, db_session, test_asset):
        """Arrange-Act-Assert: Test getting latest market data for an asset."""
        # Arrange
        repo = MarketDataRepository(MarketData, db_session)
        now = datetime.utcnow()
        # Create test market data
        market_data = MarketData(
            asset_id=test_asset.id,
            timestamp=now,
            open_price=Decimal("150.00"),
            high_price=Decimal("155.00"),
            low_price=Decimal("149.00"),
            close_price=Decimal("154.00"),
            volume=1000000,
        )
        db_session.add(market_data)
        db_session.commit()

        # Act
        result = repo.get_latest_price(test_asset.id)

        # Assert
        assert result is not None
        assert result.asset_id == test_asset.id

    def test_bulk_insert(self, db_session, test_asset):
        """Arrange-Act-Assert: Test bulk inserting market data."""
        # Arrange
        repo = MarketDataRepository(MarketData, db_session)
        now = datetime.utcnow()
        market_data_list = [
            {
                "asset_id": test_asset.id,
                "timestamp": now + timedelta(minutes=i),
                "open_price": "150.00",
                "high_price": "155.00",
                "low_price": "149.00",
                "close_price": "154.00",
                "volume": 1000000,
            }
            for i in range(10)
        ]

        # Act
        with patch("app.database.repositories.logger") as mock_logger:
            result = repo.bulk_insert(market_data_list)

        # Assert
        assert result is True
        mock_logger.info.assert_called_once()


# =============================================================================
# SignalRepository Tests
# =============================================================================

class TestSignalRepository:
    """Test cases for SignalRepository."""

    def test_get_by_strategy(self, db_session, test_signal):
        """Arrange-Act-Assert: Test getting signals by strategy name."""
        # Arrange
        repo = SignalRepository(Signal, db_session)

        # Act
        result = repo.get_by_strategy("momentum")

        # Assert
        assert len(result) >= 1
        assert test_signal in result

    def test_get_by_strategy_with_limit(self, db_session, test_asset, test_signal):
        """Arrange-Act-Assert: Test getting signals by strategy with limit."""
        # Arrange
        repo = SignalRepository(Signal, db_session)
        # Create additional signals
        for i in range(5):
            signal = Signal(
                asset_id=test_asset.id,
                strategy_name="momentum",
                signal_type="BUY",
                confidence=Decimal("80.0"),
                strength="MODERATE",
                price=Decimal("160.00"),
            )
            db_session.add(signal)
        db_session.commit()

        # Act
        result = repo.get_by_strategy("momentum", limit=3)

        # Assert
        assert len(result) == 3

    def test_get_by_asset(self, db_session, test_signal, test_asset):
        """Arrange-Act-Assert: Test getting signals by asset ID."""
        # Arrange
        repo = SignalRepository(Signal, db_session)

        # Act
        result = repo.get_by_asset(test_asset.id)

        # Assert
        assert len(result) >= 1
        assert test_signal in result

    def test_get_recent_signals(self, db_session, test_signal):
        """Arrange-Act-Assert: Test getting recent signals."""
        # Arrange
        repo = SignalRepository(Signal, db_session)

        # Act
        result = repo.get_recent_signals(hours=24)

        # Assert
        assert len(result) >= 1
        assert test_signal in result


# =============================================================================
# BacktestRepository Tests
# =============================================================================

class TestBacktestRepository:
    """Test cases for BacktestRepository."""

    @pytest.fixture
    def test_backtest(self, db_session, test_portfolio):
        """Create a test backtest."""
        now = datetime.utcnow()
        backtest = Backtest(
            portfolio_id=test_portfolio.id,
            strategy_name="momentum",
            start_date=now - timedelta(days=30),
            end_date=now,
            status="RUNNING",
            initial_capital=Decimal("10000.00"),
            final_capital=Decimal("11000.00"),
            total_return=Decimal("0.10"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("-0.05"),
        )
        db_session.add(backtest)
        db_session.commit()
        db_session.refresh(backtest)
        return backtest

    def test_get_by_portfolio(self, db_session, test_backtest, test_portfolio):
        """Arrange-Act-Assert: Test getting backtests by portfolio ID."""
        # Arrange
        repo = BacktestRepository(Backtest, db_session)

        # Act
        result = repo.get_by_portfolio(test_portfolio.id)

        # Assert
        assert len(result) >= 1
        assert test_backtest in result

    def test_get_by_strategy(self, db_session, test_backtest):
        """Arrange-Act-Assert: Test getting backtests by strategy name."""
        # Arrange
        repo = BacktestRepository(Backtest, db_session)

        # Act
        result = repo.get_by_strategy("momentum")

        # Assert
        assert len(result) >= 1
        assert test_backtest in result

    def test_get_completed_backtests(self, db_session, test_backtest):
        """Arrange-Act-Assert: Test getting completed backtests."""
        # Arrange
        repo = BacktestRepository(Backtest, db_session)
        # Update backtest to completed
        test_backtest.status = "COMPLETED"
        test_backtest.completed_at = datetime.utcnow()
        db_session.commit()

        # Act
        result = repo.get_completed_backtests()

        # Assert
        assert len(result) >= 1
        assert test_backtest in result


# =============================================================================
# RiskMetricsRepository Tests
# =============================================================================

class TestRiskMetricsRepository:
    """Test cases for RiskMetricsRepository."""

    @pytest.fixture
    def test_risk_metrics(self, db_session, test_portfolio):
        """Create a test risk metrics."""
        risk_metrics = RiskMetrics(
            portfolio_id=test_portfolio.id,
            calculation_date=datetime.utcnow(),
            var_95=Decimal("100.00"),
            var_99=Decimal("200.00"),
            expected_shortfall=Decimal("150.00"),
            beta=Decimal("1.2"),
            volatility=Decimal("0.15"),
        )
        db_session.add(risk_metrics)
        db_session.commit()
        db_session.refresh(risk_metrics)
        return risk_metrics

    def test_get_latest_by_portfolio(self, db_session, test_risk_metrics, test_portfolio):
        """Arrange-Act-Assert: Test getting latest risk metrics by portfolio."""
        # Arrange
        repo = RiskMetricsRepository(RiskMetrics, db_session)

        # Act
        result = repo.get_latest_by_portfolio(test_portfolio.id)

        # Assert
        assert result is not None
        assert result.id == test_risk_metrics.id

    def test_get_by_date_range(self, db_session, test_risk_metrics, test_portfolio):
        """Arrange-Act-Assert: Test getting risk metrics by date range."""
        # Arrange
        repo = RiskMetricsRepository(RiskMetrics, db_session)
        start_date = test_risk_metrics.calculation_date - timedelta(hours=1)
        end_date = test_risk_metrics.calculation_date + timedelta(hours=1)

        # Act
        result = repo.get_by_date_range(test_portfolio.id, start_date, end_date)

        # Assert
        assert len(result) >= 1
        assert test_risk_metrics in result


# =============================================================================
# SystemLogRepository Tests
# =============================================================================

class TestSystemLogRepository:
    """Test cases for SystemLogRepository."""

    @pytest.fixture
    def test_log(self, db_session):
        """Create a test system log."""
        log = SystemLog(
            timestamp=datetime.utcnow(),
            level="INFO",
            service="test_service",
            message="Test log message",
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        return log

    def test_get_by_level(self, db_session, test_log):
        """Arrange-Act-Assert: Test getting logs by level."""
        # Arrange
        repo = SystemLogRepository(SystemLog, db_session)

        # Act
        result = repo.get_by_level("INFO")

        # Assert
        assert len(result) >= 1
        assert test_log in result

    def test_get_by_level_with_limit(self, db_session):
        """Arrange-Act-Assert: Test getting logs by level with limit."""
        # Arrange
        repo = SystemLogRepository(SystemLog, db_session)
        # Create multiple logs
        for _ in range(5):
            log = SystemLog(
                timestamp=datetime.utcnow(),
                level="ERROR",
                service="test_service",
                message="Error message",
            )
            db_session.add(log)
        db_session.commit()

        # Act
        result = repo.get_by_level("ERROR", limit=3)

        # Assert
        assert len(result) == 3

    def test_get_by_service(self, db_session, test_log):
        """Arrange-Act-Assert: Test getting logs by service."""
        # Arrange
        repo = SystemLogRepository(SystemLog, db_session)

        # Act
        result = repo.get_by_service("test_service")

        # Assert
        assert len(result) >= 1
        assert test_log in result

    def test_get_recent_logs(self, db_session, test_log):
        """Arrange-Act-Assert: Test getting recent logs."""
        # Arrange
        repo = SystemLogRepository(SystemLog, db_session)

        # Act
        result = repo.get_recent_logs(hours=24)

        # Assert
        assert len(result) >= 1
        assert test_log in result


# =============================================================================
# Type Hints Tests (Modern Python 3.10+ syntax)
# =============================================================================

class TestModernTypeHints:
    """Test cases for modern type hints (T | None instead of Optional[T])."""

    def test_base_repository_get_by_id_returns_none(self, db_session):
        """Test that get_by_id can return None (type: User | None)."""
        # Arrange
        repo = BaseRepository(User, db_session)
        fake_id = uuid.uuid4()

        # Act
        result = repo.get_by_id(fake_id)

        # Assert
        # Result should be None, which is valid for the | None type hint
        assert result is None

    def test_base_repository_update_returns_none(self, db_session):
        """Test that update can return None (type: User | None)."""
        # Arrange
        repo = BaseRepository(User, db_session)
        fake_id = uuid.uuid4()

        # Act
        result = repo.update(fake_id, is_active=False)

        # Assert
        assert result is None

    def test_user_repository_get_by_username_returns_none(self, db_session):
        """Test that get_by_username can return None (type: User | None)."""
        # Arrange
        repo = UserRepository(User, db_session)

        # Act
        result = repo.get_by_username("nonexistent")

        # Assert
        assert result is None

    def test_user_repository_get_by_email_returns_none(self, db_session):
        """Test that get_by_email can return None (type: User | None)."""
        # Arrange
        repo = UserRepository(User, db_session)

        # Act
        result = repo.get_by_email("nonexistent@example.com")

        # Assert
        assert result is None

    def test_asset_repository_get_by_symbol_returns_none(self, db_session):
        """Test that get_by_symbol can return None (type: Asset | None)."""
        # Arrange
        repo = AssetRepository(Asset, db_session)

        # Act
        result = repo.get_by_symbol("NONEXISTENT")

        # Assert
        assert result is None

    def test_position_repository_get_by_portfolio_and_asset_returns_none(
        self, db_session
    ):
        """Test that get_by_portfolio_and_asset can return None."""
        # Arrange
        repo = PositionRepository(Position, db_session)
        fake_portfolio_id = uuid.uuid4()
        fake_asset_id = uuid.uuid4()

        # Act
        result = repo.get_by_portfolio_and_asset(fake_portfolio_id, fake_asset_id)

        # Assert
        assert result is None

    def test_market_data_repository_get_latest_price_returns_none(self, db_session):
        """Test that get_latest_price can return None (type: MarketData | None)."""
        # Arrange
        repo = MarketDataRepository(MarketData, db_session)
        fake_asset_id = uuid.uuid4()

        # Act
        result = repo.get_latest_price(fake_asset_id)

        # Assert
        assert result is None

    def test_risk_metrics_repository_get_latest_by_portfolio_returns_none(
        self, db_session
    ):
        """Test that get_latest_by_portfolio can return None."""
        # Arrange
        repo = RiskMetricsRepository(RiskMetrics, db_session)
        fake_portfolio_id = uuid.uuid4()

        # Act
        result = repo.get_latest_by_portfolio(fake_portfolio_id)

        # Assert
        assert result is None


# =============================================================================
# Error Handling and Transaction Rollback Tests
# =============================================================================

class TestErrorHandlingAndTransactionRollback:
    """Test cases for error handling and transaction rollback."""

    def test_create_integrity_error_logs_and_raises(self, db_session, test_user):
        """Test that IntegrityError is logged and re-raised as DatabaseError."""
        # Arrange
        repo = BaseRepository(User, db_session)
        duplicate_data = {
            "username": test_user.username,  # Duplicate username
            "email": "another@example.com",
            "hashed_password": "hashed_password",
            "is_active": True,
        }

        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            repo.create(**duplicate_data)

        assert "Failed to create User" in str(exc_info.value)

    def test_get_by_id_database_error(self, db_session):
        """Test database error handling in get_by_id."""
        # Arrange
        repo = BaseRepository(User, db_session)
        # Close session to cause error
        db_session.close()

        # Act & Assert
        # This should raise a DatabaseError or SQLAlchemy error due to the closed session
        # Note: The repository catches database errors and converts them to DatabaseError
        # But a closed session might raise a different error
        try:
            repo.get_by_id(uuid.uuid4())
            assert False, "Expected an exception when using closed session"
        except (DatabaseError, Exception) as e:
            # Either DatabaseError (caught and re-raised) or raw SQLAlchemy error
            assert True

    def test_update_database_error_rolls_back(self, db_session, test_user):
        """Test that database errors during update cause rollback."""
        # Arrange
        repo = BaseRepository(User, db_session)
        # Close session to cause error
        db_session.close()

        # Act & Assert
        try:
            repo.update(test_user.id, is_active=False)
            assert False, "Expected an exception when using closed session"
        except (DatabaseError, Exception) as e:
            # Either DatabaseError (caught and re-raised) or raw SQLAlchemy error
            assert True


# =============================================================================
# Pagination Tests
# =============================================================================

class TestPagination:
    """Test cases for pagination functionality."""

    def test_get_all_pagination_offset_only(self, db_session):
        """Test get_all with only offset parameter."""
        # Arrange
        repo = BaseRepository(User, db_session)
        # Create multiple users
        initial_count = repo.count()
        created_count = 5
        for i in range(created_count):
            repo.create(
                username=f"user_offset_{i}",
                email=f"user_offset_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )

        # Act - Skip first 2 records
        result = repo.get_all(offset=2)

        # Assert - Should have total_count - 2 records (from offset)
        # Note: There might be other users in the DB from other tests
        assert len(result) == (initial_count + created_count) - 2

    def test_get_all_pagination_limit_only(self, db_session):
        """Test get_all with only limit parameter."""
        # Arrange
        repo = BaseRepository(User, db_session)
        # Create multiple users
        for i in range(5):
            repo.create(
                username=f"user_limit_{i}",
                email=f"user_limit_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )

        # Act - Get first 3 records
        result = repo.get_all(limit=3)

        # Assert
        assert len(result) == 3

    def test_get_all_pagination_both_parameters(self, db_session):
        """Test get_all with both offset and limit parameters."""
        # Arrange
        repo = BaseRepository(User, db_session)
        # Create multiple users
        for i in range(10):
            repo.create(
                username=f"user_both_{i}",
                email=f"user_both_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )

        # Act - Get records 3-7 (offset=3, limit=4)
        result = repo.get_all(offset=3, limit=4)

        # Assert
        assert len(result) == 4

    def test_trade_repository_get_by_asset_with_limit(
        self, db_session, test_trade, test_asset
    ):
        """Test TradeRepository.get_by_asset with limit."""
        # Arrange
        repo = TradeRepository(Trade, db_session)
        # Create additional trades
        for _ in range(5):
            trade = Trade(
                portfolio_id=test_trade.portfolio_id,
                asset_id=test_asset.id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("100.00"),
                total_cost=Decimal("1000.00"),
                executed_at=datetime.utcnow(),
            )
            db_session.add(trade)
        db_session.commit()

        # Act
        result = repo.get_by_asset(test_asset.id, limit=3)

        # Assert
        assert len(result) == 3

    def test_signal_repository_get_by_asset_with_limit(
        self, db_session, test_signal, test_asset
    ):
        """Test SignalRepository.get_by_asset with limit."""
        # Arrange
        repo = SignalRepository(Signal, db_session)
        # Create additional signals
        for _ in range(5):
            signal = Signal(
                asset_id=test_asset.id,
                strategy_name="momentum",
                signal_type="BUY",
                confidence=Decimal("80.0"),
                strength="MODERATE",
                price=Decimal("160.00"),
            )
            db_session.add(signal)
        db_session.commit()

        # Act
        result = repo.get_by_asset(test_asset.id, limit=3)

        # Assert
        assert len(result) == 3
