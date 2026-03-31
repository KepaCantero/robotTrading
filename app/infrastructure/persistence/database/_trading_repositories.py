"""
Trading Repository Implementations.

Split from repositories.py to improve maintainability index.
Contains TradeRepository and SignalRepository.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.sql.functions import count as sa_count, sum as sa_sum

from app.infrastructure.persistence.database._base_repository import BaseRepository, logger
from app.infrastructure.persistence.database.models import Signal, Trade
from app.shared.exceptions.exceptions import raise_database_error

if TYPE_CHECKING:
    import uuid


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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_portfolio_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get trades by portfolio: {e!s}",
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_asset_failed",
                asset_id=str(asset_id),
                error=str(e),
            )
            raise_database_error(f"Failed to get trades by asset: {e!s}", "get_by_asset", "trades")

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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_date_range_failed",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get trades by date range: {e!s}",
                "get_by_date_range",
                "trades",
            )

    def get_trade_summary(self, portfolio_id: uuid.UUID) -> dict[str, Any]:
        """Get trade summary statistics for a portfolio."""
        try:
            result = (
                self.session.query(
                    sa_count(Trade.id).label("total_trades"),
                    sa_sum(Trade.commission).label("total_commission"),
                    sa_sum(Trade.slippage).label("total_slippage"),
                    sa_sum(Trade.total_cost).label("total_cost"),
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_trade_summary_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get trade summary: {e!s}", "get_trade_summary", "trades"
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_strategy_failed",
                strategy_name=strategy_name,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get signals by strategy: {e!s}",
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_asset_failed",
                asset_id=str(asset_id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get signals by asset: {e!s}", "get_by_asset", "signals"
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_recent_signals_failed",
                hours=hours,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get recent signals: {e!s}",
                "get_recent_signals",
                "signals",
            )
