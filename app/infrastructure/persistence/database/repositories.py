"""
Repository Pattern Implementation for Database Access
TASK-6: Configuración de base de datos
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Generic, TypeVar

from sqlalchemy import and_, func
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.orm import Session
from structlog import get_logger

from app.infrastructure.persistence.models import (
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
from app.shared.exceptions.exceptions import raise_database_error

# pylint: disable=inconsistent-return-statements
# The raise_database_error function always raises an exception, so pylint
# incorrectly reports inconsistent return statements. This is intentional.


T = TypeVar("T")
logger = get_logger(__name__)


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""

    def __init__(self, model_class: type[T], session: Session):
        self.model_class = model_class
        self.session = session

    def create(self, **kwargs) -> T:
        """Create a new record."""
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            logger.info(
                "created_record",
                model=self.model_class.__name__,
                id=str(instance.id),
            )
            return instance
        except IntegrityError as e:
            self.session.rollback()
            logger.error(
                "create_failed",
                model=self.model_class.__name__,
                error=str(e),
            )
            raise_database_error(
                f"Failed to create {self.model_class.__name__}: {str(e)}",
                "create",
                self.model_class.__tablename__,
            )

    def get_by_id(self, id: uuid.UUID) -> T | None:  # pylint: disable=redefined-builtin
        """Get record by ID."""
        try:
            result = self.session.query(self.model_class).filter(self.model_class.id == id).first()
            logger.debug(
                "queried_by_id",
                model=self.model_class.__name__,
                id=str(id),
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_id_failed",
                model=self.model_class.__name__,
                id=str(id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get {self.model_class.__name__} by ID: {str(e)}",
                "get_by_id",
                self.model_class.__tablename__,
            )

    def get_all(self, limit: int | None = None, offset: int | None = None) -> list[T]:
        """Get all records with optional pagination."""
        try:
            query = self.session.query(self.model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_all",
                model=self.model_class.__name__,
                count=len(result),
                limit=limit,
                offset=offset,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_all_failed",
                model=self.model_class.__name__,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get all {self.model_class.__name__}: {str(e)}",
                "get_all",
                self.model_class.__tablename__,
            )

    def update(self, id: uuid.UUID, **kwargs) -> T | None:
        """Update record by ID."""
        try:
            instance = self.get_by_id(id)
            if not instance:
                logger.warning(
                    "update_not_found",
                    model=self.model_class.__name__,
                    id=str(id),
                )
                return None
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.session.commit()
            self.session.refresh(instance)
            logger.info(
                "updated_record",
                model=self.model_class.__name__,
                id=str(id),
                fields=list(kwargs.keys()),
            )
            return instance
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            self.session.rollback()
            logger.error(
                "update_failed",
                model=self.model_class.__name__,
                id=str(id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to update {self.model_class.__name__}: {str(e)}",
                "update",
                self.model_class.__tablename__,
            )

    def delete(self, id: uuid.UUID) -> bool:
        """Delete record by ID."""
        try:
            instance = self.get_by_id(id)
            if not instance:
                logger.warning(
                    "delete_not_found",
                    model=self.model_class.__name__,
                    id=str(id),
                )
                return False
            self.session.delete(instance)
            self.session.commit()
            logger.info(
                "deleted_record",
                model=self.model_class.__name__,
                id=str(id),
            )
            return True
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            self.session.rollback()
            logger.error(
                "delete_failed",
                model=self.model_class.__name__,
                id=str(id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to delete {self.model_class.__name__}: {str(e)}",
                "delete",
                self.model_class.__tablename__,
            )

    def count(self) -> int:
        """Count total records."""
        try:
            result = self.session.query(self.model_class).count()
            logger.debug(
                "counted_records",
                model=self.model_class.__name__,
                count=result,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "count_failed",
                model=self.model_class.__name__,
                error=str(e),
            )
            raise_database_error(
                f"Failed to count {self.model_class.__name__}: {str(e)}",
                "count",
                self.model_class.__tablename__,
            )


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        try:
            result = self.session.query(User).filter(User.username == username).first()
            logger.debug(
                "queried_user_by_username",
                username=username,
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_username_failed",
                username=username,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get user by username: {str(e)}", "get_by_username", "users"
            )

    def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        try:
            result = self.session.query(User).filter(User.email == email).first()
            logger.debug(
                "queried_user_by_email",
                email=email,
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_email_failed",
                email=email,
                error=str(e),
            )
            raise_database_error(f"Failed to get user by email: {str(e)}", "get_by_email", "users")

    def get_active_users(self) -> list[User]:
        """Get all active users."""
        try:
            result = self.session.query(User).filter(User.is_active).all()
            logger.debug(
                "queried_active_users",
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_active_users_failed",
                error=str(e),
            )
            raise_database_error(
                f"Failed to get active users: {str(e)}", "get_active_users", "users"
            )


class PortfolioRepository(BaseRepository[Portfolio]):
    """Repository for Portfolio model."""

    def get_by_user(self, user_id: uuid.UUID) -> list[Portfolio]:
        """Get portfolios by user ID."""
        try:
            result = self.session.query(Portfolio).filter(Portfolio.user_id == user_id).all()
            logger.debug(
                "queried_portfolios_by_user",
                user_id=str(user_id),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_user_failed",
                user_id=str(user_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get portfolios by user: {str(e)}",
                "get_by_user",
                "portfolios",
            )

    def get_active_by_user(self, user_id: uuid.UUID) -> list[Portfolio]:
        """Get active portfolios by user ID."""
        try:
            result = (
                self.session.query(Portfolio)
                .filter(and_(Portfolio.user_id == user_id, Portfolio.is_active))
                .all()
            )
            logger.debug(
                "queried_active_portfolios_by_user",
                user_id=str(user_id),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_active_by_user_failed",
                user_id=str(user_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get active portfolios by user: {str(e)}",
                "get_active_by_user",
                "portfolios",
            )

    def update_total_value(self, portfolio_id: uuid.UUID, total_value: Decimal) -> bool:
        """Update portfolio total value."""
        try:
            self.session.query(Portfolio).filter(Portfolio.id == portfolio_id).update(
                {"total_value": total_value}
            )
            self.session.commit()
            logger.info(
                "updated_portfolio_total_value",
                portfolio_id=str(portfolio_id),
                total_value=float(total_value),
            )
            return True
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            self.session.rollback()
            logger.error(
                "update_total_value_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to update portfolio total value: {str(e)}",
                "update_total_value",
                "portfolios",
            )


class AssetRepository(BaseRepository[Asset]):
    """Repository for Asset model."""

    def get_by_symbol(self, symbol: str) -> Asset | None:
        """Get asset by symbol."""
        try:
            result = self.session.query(Asset).filter(Asset.symbol == symbol).first()
            logger.debug(
                "queried_asset_by_symbol",
                symbol=symbol,
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_symbol_failed",
                symbol=symbol,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get asset by symbol: {str(e)}", "get_by_symbol", "assets"
            )

    def get_by_asset_class(self, asset_class: str) -> list[Asset]:
        """Get assets by asset class."""
        try:
            result = self.session.query(Asset).filter(Asset.asset_class == asset_class).all()
            logger.debug(
                "queried_assets_by_class",
                asset_class=asset_class,
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_asset_class_failed",
                asset_class=asset_class,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get assets by class: {str(e)}",
                "get_by_asset_class",
                "assets",
            )

    def get_active_assets(self) -> list[Asset]:
        """Get all active assets."""
        try:
            result = self.session.query(Asset).filter(Asset.is_active).all()
            logger.debug(
                "queried_active_assets",
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_active_assets_failed",
                error=str(e),
            )
            raise_database_error(
                f"Failed to get active assets: {str(e)}", "get_active_assets", "assets"
            )

    def search_by_name(self, name_pattern: str) -> list[Asset]:
        """Search assets by name pattern."""
        try:
            result = self.session.query(Asset).filter(Asset.name.ilike(f"%{name_pattern}%")).all()
            logger.debug(
                "searched_assets_by_name",
                pattern=name_pattern,
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "search_by_name_failed",
                pattern=name_pattern,
                error=str(e),
            )
            raise_database_error(
                f"Failed to search assets by name: {str(e)}", "search_by_name", "assets"
            )


class PositionRepository(BaseRepository[Position]):
    """Repository for Position model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID) -> list[Position]:
        """Get positions by portfolio ID."""
        try:
            result = (
                self.session.query(Position).filter(Position.portfolio_id == portfolio_id).all()
            )
            logger.debug(
                "queried_positions_by_portfolio",
                portfolio_id=str(portfolio_id),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_portfolio_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get positions by portfolio: {str(e)}",
                "get_by_portfolio",
                "positions",
            )

    def get_by_portfolio_and_asset(
        self, portfolio_id: uuid.UUID, asset_id: uuid.UUID
    ) -> Position | None:
        """Get position by portfolio and asset IDs."""
        try:
            result = (
                self.session.query(Position)
                .filter(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.asset_id == asset_id,
                    )
                )
                .first()
            )
            logger.debug(
                "queried_position_by_portfolio_and_asset",
                portfolio_id=str(portfolio_id),
                asset_id=str(asset_id),
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_portfolio_and_asset_failed",
                portfolio_id=str(portfolio_id),
                asset_id=str(asset_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get position by portfolio and asset: {str(e)}",
                "get_by_portfolio_and_asset",
                "positions",
            )

    def get_non_zero_positions(self, portfolio_id: uuid.UUID) -> list[Position]:
        """Get non-zero positions for a portfolio."""
        try:
            result = (
                self.session.query(Position)
                .filter(and_(Position.portfolio_id == portfolio_id, Position.quantity != 0))
                .all()
            )
            logger.debug(
                "queried_non_zero_positions",
                portfolio_id=str(portfolio_id),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_non_zero_positions_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get non-zero positions: {str(e)}",
                "get_non_zero_positions",
                "positions",
            )

    def update_position_price(self, position_id: uuid.UUID, current_price: Decimal) -> bool:
        """Update position current price and unrealized PnL."""
        try:
            position = self.get_by_id(position_id)
            if not position:
                logger.warning(
                    "update_position_price_not_found",
                    position_id=str(position_id),
                )
                return False
            position.current_price = current_price
            position.unrealized_pnl = (current_price - position.average_price) * position.quantity
            self.session.commit()
            logger.info(
                "updated_position_price",
                position_id=str(position_id),
                current_price=float(current_price),
                unrealized_pnl=float(position.unrealized_pnl),
            )
            return True
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            self.session.rollback()
            logger.error(
                "update_position_price_failed",
                position_id=str(position_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to update position price: {str(e)}",
                "update_position_price",
                "positions",
            )


class TradeRepository(BaseRepository[Trade]):
    """Repository for Trade model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID, limit: int | None = None) -> list[Trade]:
        """Get trades by portfolio ID."""
        try:
            query = (
                self.session.query(Trade)
                .filter(Trade.portfolio_id == portfolio_id)
                .order_by(Trade.executed_at.desc())
            )
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_trades_by_portfolio",
                portfolio_id=str(portfolio_id),
                count=len(result),
                limit=limit,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_portfolio_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get trades by portfolio: {str(e)}",
                "get_by_portfolio",
                "trades",
            )

    def get_by_asset(self, asset_id: uuid.UUID, limit: int | None = None) -> list[Trade]:
        """Get trades by asset ID."""
        try:
            query = (
                self.session.query(Trade)
                .filter(Trade.asset_id == asset_id)
                .order_by(Trade.executed_at.desc())
            )
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_trades_by_asset",
                asset_id=str(asset_id),
                count=len(result),
                limit=limit,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_asset_failed",
                asset_id=str(asset_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get trades by asset: {str(e)}", "get_by_asset", "trades"
            )

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> list[Trade]:
        """Get trades within date range."""
        try:
            result = (
                self.session.query(Trade)
                .filter(and_(Trade.executed_at >= start_date, Trade.executed_at <= end_date))
                .order_by(Trade.executed_at.desc())
                .all()
            )
            logger.debug(
                "queried_trades_by_date_range",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_date_range_failed",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get trades by date range: {str(e)}",
                "get_by_date_range",
                "trades",
            )

    def get_trade_summary(self, portfolio_id: uuid.UUID) -> dict[str, Any]:
        """Get trade summary statistics for a portfolio."""
        try:
            result = (
                self.session.query(
                    func.count(Trade.id).label("total_trades"),  # pylint: disable=not-callable
                    func.sum(Trade.commission).label("total_commission"),
                    func.sum(Trade.slippage).label("total_slippage"),
                    func.sum(Trade.total_cost).label("total_cost"),
                )
                .filter(Trade.portfolio_id == portfolio_id)
                .first()
            )
            summary = {
                "total_trades": result.total_trades or 0,
                "total_commission": result.total_commission or Decimal("0"),
                "total_slippage": result.total_slippage or Decimal("0"),
                "total_cost": result.total_cost or Decimal("0"),
            }
            logger.debug(
                "queried_trade_summary",
                portfolio_id=str(portfolio_id),
                total_trades=summary["total_trades"],
            )
            return summary
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_trade_summary_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get trade summary: {str(e)}", "get_trade_summary", "trades"
            )


class MarketDataRepository(BaseRepository[MarketData]):
    """Repository for MarketData model."""

    def get_by_asset_and_date_range(
        self, asset_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> list[MarketData]:
        """Get market data by asset and date range."""
        try:
            result = (
                self.session.query(MarketData)
                .filter(
                    and_(
                        MarketData.asset_id == asset_id,
                        MarketData.timestamp >= start_date,
                        MarketData.timestamp <= end_date,
                    )
                )
                .order_by(MarketData.timestamp.asc())
                .all()
            )
            logger.debug(
                "queried_market_data_by_asset_and_date_range",
                asset_id=str(asset_id),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_asset_and_date_range_failed",
                asset_id=str(asset_id),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get market data by asset and date range: {str(e)}",
                "get_by_asset_and_date_range",
                "market_data",
            )

    def get_latest_price(self, asset_id: uuid.UUID) -> MarketData | None:
        """Get latest market data for an asset."""
        try:
            result = (
                self.session.query(MarketData)
                .filter(MarketData.asset_id == asset_id)
                .order_by(MarketData.timestamp.desc())
                .first()
            )
            logger.debug(
                "queried_latest_price",
                asset_id=str(asset_id),
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_latest_price_failed",
                asset_id=str(asset_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get latest price: {str(e)}",
                "get_latest_price",
                "market_data",
            )

    def bulk_insert(self, market_data_list: list[dict[str, Any]]) -> bool:
        """Bulk insert market data."""
        try:
            self.session.bulk_insert_mappings(MarketData, market_data_list)
            self.session.commit()
            logger.info(
                "bulk_inserted_market_data",
                count=len(market_data_list),
            )
            return True
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            self.session.rollback()
            logger.error(
                "bulk_insert_failed",
                count=len(market_data_list),
                error=str(e),
            )
            raise_database_error(
                f"Failed to bulk insert market data: {str(e)}",
                "bulk_insert",
                "market_data",
            )


class SignalRepository(BaseRepository[Signal]):
    """Repository for Signal model."""

    def get_by_strategy(self, strategy_name: str, limit: int | None = None) -> list[Signal]:
        """Get signals by strategy name."""
        try:
            query = (
                self.session.query(Signal)
                .filter(Signal.strategy_name == strategy_name)
                .order_by(Signal.created_at.desc())
            )
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_signals_by_strategy",
                strategy_name=strategy_name,
                count=len(result),
                limit=limit,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_strategy_failed",
                strategy_name=strategy_name,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get signals by strategy: {str(e)}",
                "get_by_strategy",
                "signals",
            )

    def get_by_asset(self, asset_id: uuid.UUID, limit: int | None = None) -> list[Signal]:
        """Get signals by asset ID."""
        try:
            query = (
                self.session.query(Signal)
                .filter(Signal.asset_id == asset_id)
                .order_by(Signal.created_at.desc())
            )
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_signals_by_asset",
                asset_id=str(asset_id),
                count=len(result),
                limit=limit,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_asset_failed",
                asset_id=str(asset_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get signals by asset: {str(e)}", "get_by_asset", "signals"
            )

    def get_recent_signals(self, hours: int = 24) -> list[Signal]:
        """Get recent signals within specified hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            result = (
                self.session.query(Signal)
                .filter(Signal.created_at >= cutoff_time)
                .order_by(Signal.created_at.desc())
                .all()
            )
            logger.debug(
                "queried_recent_signals",
                hours=hours,
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_recent_signals_failed",
                hours=hours,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get recent signals: {str(e)}",
                "get_recent_signals",
                "signals",
            )


class BacktestRepository(BaseRepository[Backtest]):
    """Repository for Backtest model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID) -> list[Backtest]:
        """Get backtests by portfolio ID."""
        try:
            result = (
                self.session.query(Backtest)
                .filter(Backtest.portfolio_id == portfolio_id)
                .order_by(Backtest.created_at.desc())
                .all()
            )
            logger.debug(
                "queried_backtests_by_portfolio",
                portfolio_id=str(portfolio_id),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_portfolio_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get backtests by portfolio: {str(e)}",
                "get_by_portfolio",
                "backtests",
            )

    def get_by_strategy(self, strategy_name: str) -> list[Backtest]:
        """Get backtests by strategy name."""
        try:
            result = (
                self.session.query(Backtest)
                .filter(Backtest.strategy_name == strategy_name)
                .order_by(Backtest.created_at.desc())
                .all()
            )
            logger.debug(
                "queried_backtests_by_strategy",
                strategy_name=strategy_name,
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_strategy_failed",
                strategy_name=strategy_name,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get backtests by strategy: {str(e)}",
                "get_by_strategy",
                "backtests",
            )

    def get_completed_backtests(self) -> list[Backtest]:
        """Get all completed backtests."""
        try:
            result = (
                self.session.query(Backtest)
                .filter(Backtest.status == "COMPLETED")
                .order_by(Backtest.completed_at.desc())
                .all()
            )
            logger.debug(
                "queried_completed_backtests",
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_completed_backtests_failed",
                error=str(e),
            )
            raise_database_error(
                f"Failed to get completed backtests: {str(e)}",
                "get_completed_backtests",
                "backtests",
            )


class RiskMetricsRepository(BaseRepository[RiskMetrics]):
    """Repository for RiskMetrics model."""

    def get_latest_by_portfolio(self, portfolio_id: uuid.UUID) -> RiskMetrics | None:
        """Get latest risk metrics for a portfolio."""
        try:
            result = (
                self.session.query(RiskMetrics)
                .filter(RiskMetrics.portfolio_id == portfolio_id)
                .order_by(RiskMetrics.calculation_date.desc())
                .first()
            )
            logger.debug(
                "queried_latest_risk_metrics_by_portfolio",
                portfolio_id=str(portfolio_id),
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_latest_by_portfolio_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get latest risk metrics: {str(e)}",
                "get_latest_by_portfolio",
                "risk_metrics",
            )

    def get_by_date_range(
        self, portfolio_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> list[RiskMetrics]:
        """Get risk metrics by date range."""
        try:
            result = (
                self.session.query(RiskMetrics)
                .filter(
                    and_(
                        RiskMetrics.portfolio_id == portfolio_id,
                        RiskMetrics.calculation_date >= start_date,
                        RiskMetrics.calculation_date <= end_date,
                    )
                )
                .order_by(RiskMetrics.calculation_date.asc())
                .all()
            )
            logger.debug(
                "queried_risk_metrics_by_date_range",
                portfolio_id=str(portfolio_id),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                count=len(result),
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_date_range_failed",
                portfolio_id=str(portfolio_id),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get risk metrics by date range: {str(e)}",
                "get_by_date_range",
                "risk_metrics",
            )


class SystemLogRepository(BaseRepository[SystemLog]):
    """Repository for SystemLog model."""

    def get_by_level(self, level: str, limit: int | None = None) -> list[SystemLog]:
        """Get logs by level."""
        try:
            query = (
                self.session.query(SystemLog)
                .filter(SystemLog.level == level)
                .order_by(SystemLog.timestamp.desc())
            )
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_logs_by_level",
                level=level,
                count=len(result),
                limit=limit,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_level_failed",
                level=level,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get logs by level: {str(e)}", "get_by_level", "system_logs"
            )

    def get_by_service(self, service: str, limit: int | None = None) -> list[SystemLog]:
        """Get logs by service."""
        try:
            query = (
                self.session.query(SystemLog)
                .filter(SystemLog.service == service)
                .order_by(SystemLog.timestamp.desc())
            )
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_logs_by_service",
                service=service,
                count=len(result),
                limit=limit,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_service_failed",
                service=service,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get logs by service: {str(e)}",
                "get_by_service",
                "system_logs",
            )

    def get_recent_logs(self, hours: int = 24, limit: int | None = None) -> list[SystemLog]:
        """Get recent logs within specified hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            query = (
                self.session.query(SystemLog)
                .filter(SystemLog.timestamp >= cutoff_time)
                .order_by(SystemLog.timestamp.desc())
            )
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_recent_logs",
                hours=hours,
                count=len(result),
                limit=limit,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_recent_logs_failed",
                hours=hours,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get recent logs: {str(e)}", "get_recent_logs", "system_logs"
            )
