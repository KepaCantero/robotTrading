"""
Analytics Repository Implementations.

Split from repositories.py to improve maintainability index.
Contains MarketDataRepository, BacktestRepository, RiskMetricsRepository, SystemLogRepository.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, NoReturn

from sqlalchemy import and_
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

from app.infrastructure.persistence.database._base_repository import BaseRepository, logger
from app.infrastructure.persistence.database.models import (
    Backtest,
    MarketData,
    RiskMetrics,
    SystemLog,
)
from app.shared.exceptions.exceptions import raise_database_error as _raise_database_error

if TYPE_CHECKING:
    import uuid


def _handle_db_error(
    message: str,
    operation: str,
    table: str,
) -> NoReturn:
    """Type-safe wrapper that mypy can resolve without following imports."""
    _raise_database_error(message, operation, table)
    raise RuntimeError("unreachable")  # Safety net


class MarketDataRepository(BaseRepository[MarketData]):
    """Repository for MarketData model."""

    def get_by_asset_and_date_range(
        self, asset_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> list[MarketData]:
        """Get market data by asset and date range."""
        try:
            result: list[MarketData] = (
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_asset_and_date_range_failed",
                asset_id=str(asset_id),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            _handle_db_error(
                f"Failed to get market data by asset and date range: {e!s}",
                "get_by_asset_and_date_range",
                "market_data",
            )

    def get_latest_price(self, asset_id: uuid.UUID) -> MarketData | None:
        """Get latest market data for an asset."""
        try:
            result: MarketData | None = (
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_latest_price_failed",
                asset_id=str(asset_id),
                error=str(e),
            )
            _handle_db_error(
                f"Failed to get latest price: {e!s}",
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            self.session.rollback()
            logger.error(
                "bulk_insert_failed",
                count=len(market_data_list),
                error=str(e),
            )
            _handle_db_error(
                f"Failed to bulk insert market data: {e!s}",
                "bulk_insert",
                "market_data",
            )


class BacktestRepository(BaseRepository[Backtest]):
    """Repository for Backtest model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID) -> list[Backtest]:
        """Get backtests by portfolio ID."""
        try:
            result: list[Backtest] = (
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
            _handle_db_error(
                f"Failed to get backtests by portfolio: {e!s}",
                "get_by_portfolio",
                "backtests",
            )

    def get_by_strategy(self, strategy_name: str) -> list[Backtest]:
        """Get backtests by strategy name."""
        try:
            result: list[Backtest] = (
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
            _handle_db_error(
                f"Failed to get backtests by strategy: {e!s}",
                "get_by_strategy",
                "backtests",
            )

    def get_completed_backtests(self) -> list[Backtest]:
        """Get all completed backtests."""
        try:
            result: list[Backtest] = (
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_completed_backtests_failed",
                error=str(e),
            )
            _handle_db_error(
                f"Failed to get completed backtests: {e!s}",
                "get_completed_backtests",
                "backtests",
            )


class RiskMetricsRepository(BaseRepository[RiskMetrics]):
    """Repository for RiskMetrics model."""

    def get_latest_by_portfolio(self, portfolio_id: uuid.UUID) -> RiskMetrics | None:
        """Get latest risk metrics for a portfolio."""
        try:
            result: RiskMetrics | None = (
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_latest_by_portfolio_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            _handle_db_error(
                f"Failed to get latest risk metrics: {e!s}",
                "get_latest_by_portfolio",
                "risk_metrics",
            )

    def get_by_date_range(
        self, portfolio_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> list[RiskMetrics]:
        """Get risk metrics by date range."""
        try:
            result: list[RiskMetrics] = (
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
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_date_range_failed",
                portfolio_id=str(portfolio_id),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            _handle_db_error(
                f"Failed to get risk metrics by date range: {e!s}",
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
            result: list[SystemLog] = query.all()
            logger.debug(
                "queried_logs_by_level",
                level=level,
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
                "get_by_level_failed",
                level=level,
                error=str(e),
            )
            _handle_db_error(f"Failed to get logs by level: {e!s}", "get_by_level", "system_logs")

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
            result: list[SystemLog] = query.all()
            logger.debug(
                "queried_logs_by_service",
                service=service,
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
                "get_by_service_failed",
                service=service,
                error=str(e),
            )
            _handle_db_error(
                f"Failed to get logs by service: {e!s}",
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
            result: list[SystemLog] = query.all()
            logger.debug(
                "queried_recent_logs",
                hours=hours,
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
                "get_recent_logs_failed",
                hours=hours,
                error=str(e),
            )
            _handle_db_error(f"Failed to get recent logs: {e!s}", "get_recent_logs", "system_logs")
