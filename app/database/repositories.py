"""
Repository Pattern Implementation for Database Access
TASK-6: Configuración de base de datos
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Generic, List, Optional, TypeVar

from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import raise_database_error
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

T = TypeVar("T")


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
            return instance
        except IntegrityError as e:
            self.session.rollback()
            raise_database_error(
                f"Failed to create {self.model_class.__name__}: {str(e)}",
                "create",
                self.model_class.__tablename__,
            )

    def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        """Get record by ID."""
        try:
            return self.session.query(self.model_class).filter(self.model_class.id == id).first()
        except Exception as e:
            raise_database_error(
                f"Failed to get {self.model_class.__name__} by ID: {str(e)}",
                "get_by_id",
                self.model_class.__tablename__,
            )

    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """Get all records with optional pagination."""
        try:
            query = self.session.query(self.model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get all {self.model_class.__name__}: {str(e)}",
                "get_all",
                self.model_class.__tablename__,
            )

    def update(self, id: uuid.UUID, **kwargs) -> Optional[T]:
        """Update record by ID."""
        try:
            instance = self.get_by_id(id)
            if not instance:
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            self.session.commit()
            self.session.refresh(instance)
            return instance
        except Exception as e:
            self.session.rollback()
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
                return False

            self.session.delete(instance)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            raise_database_error(
                f"Failed to delete {self.model_class.__name__}: {str(e)}",
                "delete",
                self.model_class.__tablename__,
            )

    def count(self) -> int:
        """Count total records."""
        try:
            return self.session.query(self.model_class).count()
        except Exception as e:
            raise_database_error(
                f"Failed to count {self.model_class.__name__}: {str(e)}",
                "count",
                self.model_class.__tablename__,
            )


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            return self.session.query(User).filter(User.username == username).first()
        except Exception as e:
            raise_database_error(
                f"Failed to get user by username: {str(e)}", "get_by_username", "users"
            )

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            return self.session.query(User).filter(User.email == email).first()
        except Exception as e:
            raise_database_error(f"Failed to get user by email: {str(e)}", "get_by_email", "users")

    def get_active_users(self) -> List[User]:
        """Get all active users."""
        try:
            return self.session.query(User).filter(User.is_active).all()
        except Exception as e:
            raise_database_error(
                f"Failed to get active users: {str(e)}", "get_active_users", "users"
            )


class PortfolioRepository(BaseRepository[Portfolio]):
    """Repository for Portfolio model."""

    def get_by_user(self, user_id: uuid.UUID) -> List[Portfolio]:
        """Get portfolios by user ID."""
        try:
            return self.session.query(Portfolio).filter(Portfolio.user_id == user_id).all()
        except Exception as e:
            raise_database_error(
                f"Failed to get portfolios by user: {str(e)}",
                "get_by_user",
                "portfolios",
            )

    def get_active_by_user(self, user_id: uuid.UUID) -> List[Portfolio]:
        """Get active portfolios by user ID."""
        try:
            return (
                self.session.query(Portfolio)
                .filter(and_(Portfolio.user_id == user_id, Portfolio.is_active))
                .all()
            )
        except Exception as e:
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
            return True
        except Exception as e:
            self.session.rollback()
            raise_database_error(
                f"Failed to update portfolio total value: {str(e)}",
                "update_total_value",
                "portfolios",
            )


class AssetRepository(BaseRepository[Asset]):
    """Repository for Asset model."""

    def get_by_symbol(self, symbol: str) -> Optional[Asset]:
        """Get asset by symbol."""
        try:
            return self.session.query(Asset).filter(Asset.symbol == symbol).first()
        except Exception as e:
            raise_database_error(
                f"Failed to get asset by symbol: {str(e)}", "get_by_symbol", "assets"
            )

    def get_by_asset_class(self, asset_class: str) -> List[Asset]:
        """Get assets by asset class."""
        try:
            return self.session.query(Asset).filter(Asset.asset_class == asset_class).all()
        except Exception as e:
            raise_database_error(
                f"Failed to get assets by class: {str(e)}",
                "get_by_asset_class",
                "assets",
            )

    def get_active_assets(self) -> List[Asset]:
        """Get all active assets."""
        try:
            return self.session.query(Asset).filter(Asset.is_active).all()
        except Exception as e:
            raise_database_error(
                f"Failed to get active assets: {str(e)}", "get_active_assets", "assets"
            )

    def search_by_name(self, name_pattern: str) -> List[Asset]:
        """Search assets by name pattern."""
        try:
            return self.session.query(Asset).filter(Asset.name.ilike(f"%{name_pattern}%")).all()
        except Exception as e:
            raise_database_error(
                f"Failed to search assets by name: {str(e)}", "search_by_name", "assets"
            )


class PositionRepository(BaseRepository[Position]):
    """Repository for Position model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID) -> List[Position]:
        """Get positions by portfolio ID."""
        try:
            return self.session.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        except Exception as e:
            raise_database_error(
                f"Failed to get positions by portfolio: {str(e)}",
                "get_by_portfolio",
                "positions",
            )

    def get_by_portfolio_and_asset(
        self, portfolio_id: uuid.UUID, asset_id: uuid.UUID
    ) -> Optional[Position]:
        """Get position by portfolio and asset IDs."""
        try:
            return (
                self.session.query(Position)
                .filter(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.asset_id == asset_id,
                    )
                )
                .first()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get position by portfolio and asset: {str(e)}",
                "get_by_portfolio_and_asset",
                "positions",
            )

    def get_non_zero_positions(self, portfolio_id: uuid.UUID) -> List[Position]:
        """Get non-zero positions for a portfolio."""
        try:
            return (
                self.session.query(Position)
                .filter(and_(Position.portfolio_id == portfolio_id, Position.quantity != 0))
                .all()
            )
        except Exception as e:
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
                return False

            position.current_price = current_price
            position.unrealized_pnl = (current_price - position.average_price) * position.quantity

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            raise_database_error(
                f"Failed to update position price: {str(e)}",
                "update_position_price",
                "positions",
            )


class TradeRepository(BaseRepository[Trade]):
    """Repository for Trade model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID, limit: Optional[int] = None) -> List[Trade]:
        """Get trades by portfolio ID."""
        try:
            query = (
                self.session.query(Trade)
                .filter(Trade.portfolio_id == portfolio_id)
                .order_by(Trade.executed_at.desc())
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get trades by portfolio: {str(e)}",
                "get_by_portfolio",
                "trades",
            )

    def get_by_asset(self, asset_id: uuid.UUID, limit: Optional[int] = None) -> List[Trade]:
        """Get trades by asset ID."""
        try:
            query = (
                self.session.query(Trade)
                .filter(Trade.asset_id == asset_id)
                .order_by(Trade.executed_at.desc())
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get trades by asset: {str(e)}", "get_by_asset", "trades"
            )

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Trade]:
        """Get trades within date range."""
        try:
            return (
                self.session.query(Trade)
                .filter(and_(Trade.executed_at >= start_date, Trade.executed_at <= end_date))
                .order_by(Trade.executed_at.desc())
                .all()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get trades by date range: {str(e)}",
                "get_by_date_range",
                "trades",
            )

    def get_trade_summary(self, portfolio_id: uuid.UUID) -> Dict[str, Any]:
        """Get trade summary statistics for a portfolio."""
        try:
            result = (
                self.session.query(
                    func.count(Trade.id).label("total_trades"),
                    func.sum(Trade.commission).label("total_commission"),
                    func.sum(Trade.slippage).label("total_slippage"),
                    func.sum(Trade.total_cost).label("total_cost"),
                )
                .filter(Trade.portfolio_id == portfolio_id)
                .first()
            )

            return {
                "total_trades": result.total_trades or 0,
                "total_commission": result.total_commission or Decimal("0"),
                "total_slippage": result.total_slippage or Decimal("0"),
                "total_cost": result.total_cost or Decimal("0"),
            }
        except Exception as e:
            raise_database_error(
                f"Failed to get trade summary: {str(e)}", "get_trade_summary", "trades"
            )


class MarketDataRepository(BaseRepository[MarketData]):
    """Repository for MarketData model."""

    def get_by_asset_and_date_range(
        self, asset_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> List[MarketData]:
        """Get market data by asset and date range."""
        try:
            return (
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
        except Exception as e:
            raise_database_error(
                f"Failed to get market data by asset and date range: {str(e)}",
                "get_by_asset_and_date_range",
                "market_data",
            )

    def get_latest_price(self, asset_id: uuid.UUID) -> Optional[MarketData]:
        """Get latest market data for an asset."""
        try:
            return (
                self.session.query(MarketData)
                .filter(MarketData.asset_id == asset_id)
                .order_by(MarketData.timestamp.desc())
                .first()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get latest price: {str(e)}",
                "get_latest_price",
                "market_data",
            )

    def bulk_insert(self, market_data_list: List[Dict[str, Any]]) -> bool:
        """Bulk insert market data."""
        try:
            self.session.bulk_insert_mappings(MarketData, market_data_list)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            raise_database_error(
                f"Failed to bulk insert market data: {str(e)}",
                "bulk_insert",
                "market_data",
            )


class SignalRepository(BaseRepository[Signal]):
    """Repository for Signal model."""

    def get_by_strategy(self, strategy_name: str, limit: Optional[int] = None) -> List[Signal]:
        """Get signals by strategy name."""
        try:
            query = (
                self.session.query(Signal)
                .filter(Signal.strategy_name == strategy_name)
                .order_by(Signal.created_at.desc())
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get signals by strategy: {str(e)}",
                "get_by_strategy",
                "signals",
            )

    def get_by_asset(self, asset_id: uuid.UUID, limit: Optional[int] = None) -> List[Signal]:
        """Get signals by asset ID."""
        try:
            query = (
                self.session.query(Signal)
                .filter(Signal.asset_id == asset_id)
                .order_by(Signal.created_at.desc())
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get signals by asset: {str(e)}", "get_by_asset", "signals"
            )

    def get_recent_signals(self, hours: int = 24) -> List[Signal]:
        """Get recent signals within specified hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return (
                self.session.query(Signal)
                .filter(Signal.created_at >= cutoff_time)
                .order_by(Signal.created_at.desc())
                .all()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get recent signals: {str(e)}",
                "get_recent_signals",
                "signals",
            )


class BacktestRepository(BaseRepository[Backtest]):
    """Repository for Backtest model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID) -> List[Backtest]:
        """Get backtests by portfolio ID."""
        try:
            return (
                self.session.query(Backtest)
                .filter(Backtest.portfolio_id == portfolio_id)
                .order_by(Backtest.created_at.desc())
                .all()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get backtests by portfolio: {str(e)}",
                "get_by_portfolio",
                "backtests",
            )

    def get_by_strategy(self, strategy_name: str) -> List[Backtest]:
        """Get backtests by strategy name."""
        try:
            return (
                self.session.query(Backtest)
                .filter(Backtest.strategy_name == strategy_name)
                .order_by(Backtest.created_at.desc())
                .all()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get backtests by strategy: {str(e)}",
                "get_by_strategy",
                "backtests",
            )

    def get_completed_backtests(self) -> List[Backtest]:
        """Get all completed backtests."""
        try:
            return (
                self.session.query(Backtest)
                .filter(Backtest.status == "COMPLETED")
                .order_by(Backtest.completed_at.desc())
                .all()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get completed backtests: {str(e)}",
                "get_completed_backtests",
                "backtests",
            )


class RiskMetricsRepository(BaseRepository[RiskMetrics]):
    """Repository for RiskMetrics model."""

    def get_latest_by_portfolio(self, portfolio_id: uuid.UUID) -> Optional[RiskMetrics]:
        """Get latest risk metrics for a portfolio."""
        try:
            return (
                self.session.query(RiskMetrics)
                .filter(RiskMetrics.portfolio_id == portfolio_id)
                .order_by(RiskMetrics.calculation_date.desc())
                .first()
            )
        except Exception as e:
            raise_database_error(
                f"Failed to get latest risk metrics: {str(e)}",
                "get_latest_by_portfolio",
                "risk_metrics",
            )

    def get_by_date_range(
        self, portfolio_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> List[RiskMetrics]:
        """Get risk metrics by date range."""
        try:
            return (
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
        except Exception as e:
            raise_database_error(
                f"Failed to get risk metrics by date range: {str(e)}",
                "get_by_date_range",
                "risk_metrics",
            )


class SystemLogRepository(BaseRepository[SystemLog]):
    """Repository for SystemLog model."""

    def get_by_level(self, level: str, limit: Optional[int] = None) -> List[SystemLog]:
        """Get logs by level."""
        try:
            query = (
                self.session.query(SystemLog)
                .filter(SystemLog.level == level)
                .order_by(SystemLog.timestamp.desc())
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get logs by level: {str(e)}", "get_by_level", "system_logs"
            )

    def get_by_service(self, service: str, limit: Optional[int] = None) -> List[SystemLog]:
        """Get logs by service."""
        try:
            query = (
                self.session.query(SystemLog)
                .filter(SystemLog.service == service)
                .order_by(SystemLog.timestamp.desc())
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get logs by service: {str(e)}",
                "get_by_service",
                "system_logs",
            )

    def get_recent_logs(self, hours: int = 24, limit: Optional[int] = None) -> List[SystemLog]:
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

            return query.all()
        except Exception as e:
            raise_database_error(
                f"Failed to get recent logs: {str(e)}", "get_recent_logs", "system_logs"
            )
