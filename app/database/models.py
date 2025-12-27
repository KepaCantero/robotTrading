"""
Database Models for AlgoTrading
TASK-6: Configuración de base de datos
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base



class User(Base):
    """User model for authentication and authorization."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    portfolios: Mapped[List["Portfolio"]] = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
        Index("idx_users_created_at", "created_at"),
        {"extend_existing": True},
    )



class APIKey(Base):
    """API Key model for external API access."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_key_hash", "key_hash"),
        Index("idx_api_keys_user_id", "user_id"),
        Index("idx_api_keys_expires_at", "expires_at"),
    )



class Portfolio(Base):
    """Portfolio model for managing trading portfolios."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    current_cash: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    positions: Mapped[List["Position"]] = relationship(
        "Position", back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[List["Trade"]] = relationship(
        "Trade", back_populates="portfolio", cascade="all, delete-orphan"
    )
    backtests: Mapped[List["Backtest"]] = relationship(
        "Backtest", back_populates="portfolio", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_portfolios_user_id", "user_id"),
        Index("idx_portfolios_name", "name"),
        Index("idx_portfolios_created_at", "created_at"),
        UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
    )



class Asset(Base):
    """Asset model for storing financial instruments."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # stock, etf, crypto, etc.
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    positions: Mapped[List["Position"]] = relationship("Position", back_populates="asset")
    trades: Mapped[List["Trade"]] = relationship("Trade", back_populates="asset")
    market_data: Mapped[List["MarketData"]] = relationship("MarketData", back_populates="asset")

    __table_args__ = (
        Index("idx_assets_symbol", "symbol"),
        Index("idx_assets_asset_class", "asset_class"),
        Index("idx_assets_exchange", "exchange"),
        Index("idx_assets_currency", "currency"),
    )



class Position(Base):
    """Position model for tracking portfolio positions."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 8), nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    unrealized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("0"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="positions")

    __table_args__ = (
        Index("idx_positions_portfolio_id", "portfolio_id"),
        Index("idx_positions_asset_id", "asset_id"),
        Index("idx_positions_updated_at", "updated_at"),
        UniqueConstraint("portfolio_id", "asset_id", name="uq_positions_portfolio_asset"),
        CheckConstraint("quantity != 0", name="ck_positions_quantity_nonzero"),
    )



class Trade(Base):
    """Trade model for recording executed trades."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY, SELL
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    commission: Mapped[Decimal] = mapped_column(
        Numeric(15, 4), default=Decimal("0"), nullable=False
    )
    slippage: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="FILLED"
    )  # PENDING, FILLED, CANCELLED
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="trades")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="trades")

    __table_args__ = (
        Index("idx_trades_portfolio_id", "portfolio_id"),
        Index("idx_trades_asset_id", "asset_id"),
        Index("idx_trades_order_id", "order_id"),
        Index("idx_trades_executed_at", "executed_at"),
        Index("idx_trades_side", "side"),
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trades_side"),
        CheckConstraint("quantity > 0", name="ck_trades_quantity_positive"),
        CheckConstraint("price > 0", name="ck_trades_price_positive"),
    )



class MarketData(Base):
    """Market data model for storing price and volume data."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    open_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 0), nullable=False)
    adjusted_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="market_data")

    __table_args__ = (
        Index("idx_market_data_asset_id", "asset_id"),
        Index("idx_market_data_timestamp", "timestamp"),
        Index("idx_market_data_asset_timestamp", "asset_id", "timestamp"),
        UniqueConstraint("asset_id", "timestamp", name="uq_market_data_asset_timestamp"),
        CheckConstraint("open_price > 0", name="ck_market_data_open_positive"),
        CheckConstraint("high_price > 0", name="ck_market_data_high_positive"),
        CheckConstraint("low_price > 0", name="ck_market_data_low_positive"),
        CheckConstraint("close_price > 0", name="ck_market_data_close_positive"),
        CheckConstraint("volume >= 0", name="ck_market_data_volume_nonnegative"),
        CheckConstraint("high_price >= low_price", name="ck_market_data_high_ge_low"),
    )



class Signal(Base):
    """Signal model for storing trading signals."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY, SELL, HOLD
    strength: Mapped[str] = mapped_column(String(20), nullable=False)  # WEAK, MODERATE, STRONG
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # 0-100
    price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 8), nullable=True)
    meta_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset")

    __table_args__ = (
        Index("idx_signals_asset_id", "asset_id"),
        Index("idx_signals_strategy_name", "strategy_name"),
        Index("idx_signals_signal_type", "signal_type"),
        Index("idx_signals_created_at", "created_at"),
        CheckConstraint("signal_type IN ('BUY', 'SELL', 'HOLD')", name="ck_signals_signal_type"),
        CheckConstraint("strength IN ('WEAK', 'MODERATE', 'STRONG')", name="ck_signals_strength"),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="ck_signals_confidence"),
        CheckConstraint("price > 0", name="ck_signals_price_positive"),
    )



class Backtest(Base):
    """Backtest model for storing backtest results."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    final_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_return: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)  # Percentage
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)  # Percentage
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="COMPLETED"
    )  # RUNNING, COMPLETED, FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="backtests")

    __table_args__ = (
        Index("idx_backtests_portfolio_id", "portfolio_id"),
        Index("idx_backtests_strategy_name", "strategy_name"),
        Index("idx_backtests_start_date", "start_date"),
        Index("idx_backtests_end_date", "end_date"),
        Index("idx_backtests_status", "status"),
        CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED')", name="ck_backtests_status"),
        CheckConstraint("start_date < end_date", name="ck_backtests_date_range"),
        CheckConstraint("initial_capital > 0", name="ck_backtests_initial_capital"),
    )



class RiskMetrics(Base):
    """Risk metrics model for storing portfolio risk calculations."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    calculation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    var_95: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )  # Value at Risk 95%
    var_99: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )  # Value at Risk 99%
    expected_shortfall: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    volatility: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), nullable=True
    )  # Annualized volatility
    beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    correlation_matrix: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio")

    __table_args__ = (
        Index("idx_risk_metrics_portfolio_id", "portfolio_id"),
        Index("idx_risk_metrics_calculation_date", "calculation_date"),
        Index("idx_risk_metrics_portfolio_date", "portfolio_id", "calculation_date"),
    )



class SystemLog(Base):
    """System log model for storing application logs."""



    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_system_logs_level", "level"),
        Index("idx_system_logs_service", "service"),
        Index("idx_system_logs_timestamp", "timestamp"),
        Index("idx_system_logs_level_service", "level", "service"),
        CheckConstraint(
            "level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name="ck_system_logs_level",
        ),
    )
