"""
T18.3: Live Trading Bridge - Trade Persistence Layer

Provides database abstraction for orders, trades, and positions.
Implements SQLAlchemy ORM models and database operations for persistent storage.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    and_,
    desc,
    select,
)
from sqlalchemy.orm import relationship

from app.core.database import Base, get_session_factory

logger = logging.getLogger(__name__)


class OrderRecord(Base):
    """ORM Model for order records."""

    __tablename__ = 'order_records'

    order_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Numeric(18, 8), nullable=False)
    price = Column(Numeric(18, 8), nullable=True)
    order_type = Column(
        String(20), nullable=False
    )  # MARKET, LIMIT, STOP, STOP_LIMIT, TRAILING_STOP
    status = Column(
        String(20), nullable=False, index=True
    )  # PENDING, SUBMITTED, ACKNOWLEDGED, EXECUTED, etc.
    broker_name = Column(String(20), nullable=False)
    broker_order_id = Column(String(50), nullable=True, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    executed_at = Column(DateTime, nullable=True)
    raw_response = Column(JSON, nullable=True)
    error_message = Column(String(500), nullable=True)
    retry_count = Column(String(3), nullable=False, default="0")

    # Relationships
    trades = relationship("TradeRecord", back_populates="order")

    __table_args__ = (
        Index("idx_symbol_created", "symbol", "created_at"),
        Index("idx_status_created", "status", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": float(self.quantity),
            "price": float(self.price) if self.price else None,
            "order_type": self.order_type,
            "status": self.status,
            "broker_name": self.broker_name,
            "broker_order_id": self.broker_order_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "error_message": self.error_message,
            "retry_count": int(self.retry_count) if self.retry_count is not None else 0,
        }


class TradeRecord(Base):
    """ORM Model for executed trade records."""

    __tablename__ = "trade_records"

    trade_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String(36), ForeignKey("order_records.order_id"), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    quantity = Column(Numeric(18, 8), nullable=False)
    execution_price = Column(Numeric(18, 8), nullable=False)
    execution_time = Column(DateTime, nullable=False, index=True)
    commission = Column(Numeric(18, 8), nullable=False, default=0)
    slippage = Column(Numeric(18, 8), nullable=False, default=0)
    market_impact = Column(Numeric(18, 8), nullable=False, default=0)
    side = Column(String(10), nullable=False)  # BUY, SELL
    fill_type = Column(String(20), nullable=False)  # FULL, PARTIAL
    broker_trade_id = Column(String(50), nullable=True, unique=True)

    # Relationships
    order = relationship("OrderRecord", back_populates="trades")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "quantity": float(self.quantity),
            "execution_price": float(self.execution_price),
            "execution_time": self.execution_time.isoformat() if self.execution_time else None,
            "commission": float(self.commission) if self.commission is not None else 0.0,
            "slippage": float(self.slippage) if self.slippage is not None else 0.0,
            "market_impact": float(self.market_impact) if self.market_impact is not None else 0.0,
            "side": self.side,
            "fill_type": self.fill_type,
        }


class PositionHistory(Base):
    """ORM Model for position history snapshots."""

    __tablename__ = "position_history"

    position_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    quantity = Column(Numeric(18, 8), nullable=False)
    average_price = Column(Numeric(18, 8), nullable=False)
    market_value = Column(Numeric(18, 8), nullable=False)
    unrealized_pnl = Column(Numeric(18, 8), nullable=False)
    unrealized_pnl_pct = Column(Numeric(10, 4), nullable=False)
    cost_basis = Column(Numeric(18, 8), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "quantity": float(self.quantity),
            "average_price": float(self.average_price),
            "market_value": float(self.market_value),
            "unrealized_pnl": float(self.unrealized_pnl),
            "unrealized_pnl_pct": float(self.unrealized_pnl_pct),
            "cost_basis": float(self.cost_basis),
        }


class TradeStatistics(Base):
    """ORM Model for aggregated trade statistics."""

    __tablename__ = "trade_statistics"

    stat_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    date = Column(DateTime, nullable=False, index=True, unique=True)
    total_trades = Column(String(5), nullable=False, default="0")
    total_volume = Column(Numeric(18, 8), nullable=False, default=0)
    total_commission = Column(Numeric(18, 8), nullable=False, default=0)
    avg_slippage = Column(Numeric(10, 6), nullable=False, default=0)
    winning_trades = Column(String(5), nullable=False, default="0")
    losing_trades = Column(String(5), nullable=False, default="0")
    win_rate = Column(Numeric(10, 4), nullable=False, default=0)
    daily_pnl = Column(Numeric(18, 8), nullable=False, default=0)
    daily_pnl_pct = Column(Numeric(10, 4), nullable=False, default=0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date.isoformat(),
            "total_trades": int(self.total_trades),
            "total_volume": float(self.total_volume),
            "total_commission": float(self.total_commission),
            "avg_slippage": float(self.avg_slippage),
            "winning_trades": int(self.winning_trades),
            "losing_trades": int(self.losing_trades),
            "win_rate": float(self.win_rate),
            "daily_pnl": float(self.daily_pnl),
            "daily_pnl_pct": float(self.daily_pnl_pct),
        }


class TradePersistenceManager:
    """Manager for trade persistence operations.

    Uses the shared database configuration from app.core.database
    to avoid duplicate connections and ensure consistent database setup.
    """

    def __init__(self):
        """Initialize persistence manager using shared database configuration."""
        self.session_factory = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self) -> None:
        """Initialize database connection and get session factory.

        Tables are created by app.main.init_database() during app startup.
        """
        try:
            # Get the shared session factory
            self.session_factory = get_session_factory()
            self.logger.info("Trade persistence manager initialized")

        except Exception as e:
            self.logger.error(f"Error initializing persistence manager: {str(e)}")
            raise

    async def shutdown(self) -> None:
        """Shutdown persistence manager.

        Note: Database connections are managed globally by app.core.database
        """
        self.logger.info("Trade persistence manager shutdown")

    async def save_order(self, order_data: Dict[str, Any]) -> str:
        """Save an order record to database.

        Args:
            order_data: Dictionary with order information

        Returns:
            Order ID
        """
        try:
            async for session in self.session_factory():
                order = OrderRecord(
                    symbol=order_data["symbol"],
                    side=order_data["side"],
                    quantity=Decimal(str(order_data["quantity"])),
                    price=(
                        Decimal(str(order_data.get("price", 0)))
                        if order_data.get("price")
                        else None
                    ),
                    order_type=order_data["order_type"],
                    status=order_data["status"],
                    broker_name=order_data["broker_name"],
                    broker_order_id=order_data.get("broker_order_id"),
                    raw_response=order_data.get("raw_response"),
                )
                session.add(order)
                await session.commit()
                self.logger.info(f"Saved order {order.order_id}")
                return order.order_id

        except Exception as e:
            self.logger.error(f"Error saving order: {str(e)}")
            raise

    async def save_trade(self, trade_data: Dict[str, Any]) -> str:
        """Save a trade execution record.

        Args:
            trade_data: Dictionary with trade information

        Returns:
            Trade ID
        """
        try:
            async for session in self.session_factory():
                trade = TradeRecord(
                    order_id=trade_data["order_id"],
                    symbol=trade_data["symbol"],
                    quantity=Decimal(str(trade_data["quantity"])),
                    execution_price=Decimal(str(trade_data["execution_price"])),
                    execution_time=trade_data["execution_time"],
                    commission=Decimal(str(trade_data.get("commission", 0))),
                    slippage=Decimal(str(trade_data.get("slippage", 0))),
                    market_impact=Decimal(str(trade_data.get("market_impact", 0))),
                    side=trade_data["side"],
                    fill_type=trade_data["fill_type"],
                    broker_trade_id=trade_data.get("broker_trade_id"),
                )
                session.add(trade)
                await session.commit()
                self.logger.info(f"Saved trade {trade.trade_id}")
                return trade.trade_id

        except Exception as e:
            self.logger.error(f"Error saving trade: {str(e)}")
            raise

    async def save_position_snapshot(self, position_data: Dict[str, Any]) -> str:
        """Save a position history snapshot.

        Args:
            position_data: Dictionary with position information

        Returns:
            Position ID
        """
        try:
            async for session in self.session_factory():
                position = PositionHistory(
                    symbol=position_data["symbol"],
                    timestamp=position_data["timestamp"],
                    quantity=Decimal(str(position_data["quantity"])),
                    average_price=Decimal(str(position_data["average_price"])),
                    market_value=Decimal(str(position_data["market_value"])),
                    unrealized_pnl=Decimal(str(position_data["unrealized_pnl"])),
                    unrealized_pnl_pct=Decimal(str(position_data["unrealized_pnl_pct"])),
                    cost_basis=Decimal(str(position_data["cost_basis"])),
                )
                session.add(position)
                await session.commit()
                return position.position_id

        except Exception as e:
            self.logger.error(f"Error saving position: {str(e)}")
            raise

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order dictionary or None
        """
        try:
            async for session in self.session_factory():
                stmt = select(OrderRecord).where(OrderRecord.order_id == order_id)
                result = await session.execute(stmt)
                order = result.scalars().first()
                return order.to_dict() if order else None

        except Exception as e:
            self.logger.error(f"Error retrieving order: {str(e)}")
            return None

    async def get_trades_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all trades for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of trade dictionaries
        """
        try:
            async for session in self.session_factory():
                stmt = (
                    select(TradeRecord)
                    .where(TradeRecord.symbol == symbol)
                    .order_by(desc(TradeRecord.execution_time))
                )
                result = await session.execute(stmt)
                trades = result.scalars().all()
                return [trade.to_dict() for trade in trades]

        except Exception as e:
            self.logger.error(f"Error retrieving trades: {str(e)}")
            return []

    async def get_trades_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get trades within a date range.

        Args:
            start_date: Start datetime
            end_date: End datetime

        Returns:
            List of trade dictionaries
        """
        try:
            async for session in self.session_factory():
                stmt = (
                    select(TradeRecord)
                    .where(
                        and_(
                            TradeRecord.execution_time >= start_date,
                            TradeRecord.execution_time <= end_date,
                        )
                    )
                    .order_by(desc(TradeRecord.execution_time))
                )
                result = await session.execute(stmt)
                trades = result.scalars().all()
                return [trade.to_dict() for trade in trades]

        except Exception as e:
            self.logger.error(f"Error retrieving trades by date: {str(e)}")
            return []

    async def get_position_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get position history for a symbol.

        Args:
            symbol: Trading symbol
            limit: Maximum number of records

        Returns:
            List of position history dictionaries
        """
        try:
            async for session in self.session_factory():
                stmt = (
                    select(PositionHistory)
                    .where(PositionHistory.symbol == symbol)
                    .order_by(desc(PositionHistory.timestamp))
                    .limit(limit)
                )
                result = await session.execute(stmt)
                positions = result.scalars().all()
                return [pos.to_dict() for pos in positions]

        except Exception as e:
            self.logger.error(f"Error retrieving position history: {str(e)}")
            return []

    async def get_execution_statistics(self, date: datetime) -> Optional[Dict[str, Any]]:
        """Get execution statistics for a date.

        Args:
            date: Date for statistics

        Returns:
            Statistics dictionary or None
        """
        try:
            async for session in self.session_factory():
                stmt = select(TradeStatistics).where(TradeStatistics.date == date)
                result = await session.execute(stmt)
                stats = result.scalars().first()
                return stats.to_dict() if stats else None

        except Exception as e:
            self.logger.error(f"Error retrieving statistics: {str(e)}")
            return None

    async def update_order_status(
        self, order_id: str, status: str, executed_at: Optional[datetime] = None
    ) -> bool:
        """Update order status.

        Args:
            order_id: Order ID
            status: New status
            executed_at: Execution time if applicable

        Returns:
            True if successful
        """
        try:
            async for session in self.session_factory():
                stmt = select(OrderRecord).where(OrderRecord.order_id == order_id)
                result = await session.execute(stmt)
                order = result.scalars().first()

                if not order:
                    return False

                order.status = status
                if executed_at:
                    order.executed_at = executed_at

                await session.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error updating order status: {str(e)}")
            return False

    async def count_trades(self, symbol: Optional[str] = None) -> int:
        """Count total trades.

        Args:
            symbol: Optional symbol filter

        Returns:
            Total count
        """
        try:
            async for session in self.session_factory():
                if symbol:
                    stmt = select(TradeRecord).where(TradeRecord.symbol == symbol)
                else:
                    stmt = select(TradeRecord)
                result = await session.execute(stmt)
                return len(result.scalars().all())

        except Exception as e:
            self.logger.error(f"Error counting trades: {str(e)}")
            return 0


# Singleton instance
_persistence_manager_instance: Optional[TradePersistenceManager] = None


def get_trade_persistence_manager() -> TradePersistenceManager:
    """Get or create the trade persistence manager singleton.

    Returns:
        TradePersistenceManager: Shared persistence manager instance
    """
    global _persistence_manager_instance
    if _persistence_manager_instance is None:
        _persistence_manager_instance = TradePersistenceManager()
    return _persistence_manager_instance
