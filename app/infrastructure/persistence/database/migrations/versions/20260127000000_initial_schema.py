"""Initial database schema for AlgoTrading Platform

This migration creates all core tables for the algorithmic trading system,
including user management, portfolios, trades, market data, backtesting,
and FIFO tax tracking.

Revision ID: 0001
Revises:
Create Date: 2026-01-27

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - create all initial tables."""

    # ==========================================================================
    # USERS & AUTHENTICATION
    # ==========================================================================

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_username", "users", ["username"], unique=True)
    op.create_index("idx_users_created_at", "users", ["created_at"])

    # ==========================================================================
    # API KEYS
    # ==========================================================================

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_api_keys_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_api_keys"),
    )
    op.create_index("idx_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_expires_at", "api_keys", ["expires_at"])

    # ==========================================================================
    # ASSETS
    # ==========================================================================

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("asset_class", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(50), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assets"),
    )
    op.create_index("idx_assets_symbol", "assets", ["symbol"], unique=True)
    op.create_index("idx_assets_asset_class", "assets", ["asset_class"])
    op.create_index("idx_assets_exchange", "assets", ["exchange"])
    op.create_index("idx_assets_currency", "assets", ["currency"])

    # ==========================================================================
    # PORTFOLIOS
    # ==========================================================================

    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("initial_cash", sa.Numeric(15, 2), nullable=False),
        sa.Column("current_cash", sa.Numeric(15, 2), nullable=False),
        sa.Column("total_value", sa.Numeric(15, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_portfolios_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_portfolios"),
        sa.UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
    )
    op.create_index("idx_portfolios_user_id", "portfolios", ["user_id"])
    op.create_index("idx_portfolios_name", "portfolios", ["name"])
    op.create_index("idx_portfolios_created_at", "portfolios", ["created_at"])

    # ==========================================================================
    # POSITIONS
    # ==========================================================================

    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(15, 8), nullable=False),
        sa.Column("average_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("current_price", sa.Numeric(15, 4), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(15, 2), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], name="fk_positions_portfolio_id"
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name="fk_positions_asset_id"),
        sa.PrimaryKeyConstraint("id", name="pk_positions"),
        sa.UniqueConstraint("portfolio_id", "asset_id", name="uq_positions_portfolio_asset"),
        sa.CheckConstraint("quantity != 0", name="ck_positions_quantity_nonzero"),
    )
    op.create_index("idx_positions_portfolio_id", "positions", ["portfolio_id"])
    op.create_index("idx_positions_asset_id", "positions", ["asset_id"])
    op.create_index("idx_positions_updated_at", "positions", ["updated_at"])

    # ==========================================================================
    # TRADES
    # ==========================================================================

    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", sa.String(100), nullable=True),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("quantity", sa.Numeric(15, 8), nullable=False),
        sa.Column("price", sa.Numeric(15, 4), nullable=False),
        sa.Column("commission", sa.Numeric(15, 4), nullable=False, server_default="0"),
        sa.Column("slippage", sa.Numeric(15, 4), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="FILLED"),
        sa.Column(
            "executed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], name="fk_trades_portfolio_id"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name="fk_trades_asset_id"),
        sa.PrimaryKeyConstraint("id", name="pk_trades"),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trades_side"),
        sa.CheckConstraint("quantity > 0", name="ck_trades_quantity_positive"),
        sa.CheckConstraint("price > 0", name="ck_trades_price_positive"),
    )
    op.create_index("idx_trades_portfolio_id", "trades", ["portfolio_id"])
    op.create_index("idx_trades_asset_id", "trades", ["asset_id"])
    op.create_index("idx_trades_order_id", "trades", ["order_id"])
    op.create_index("idx_trades_executed_at", "trades", ["executed_at"])
    op.create_index("idx_trades_side", "trades", ["side"])

    # ==========================================================================
    # MARKET DATA
    # ==========================================================================

    op.create_table(
        "market_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("open_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("high_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("low_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("close_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("volume", sa.Numeric(20, 0), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(15, 4), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name="fk_market_data_asset_id"),
        sa.PrimaryKeyConstraint("id", name="pk_market_data"),
        sa.UniqueConstraint("asset_id", "timestamp", name="uq_market_data_asset_timestamp"),
        sa.CheckConstraint("open_price > 0", name="ck_market_data_open_positive"),
        sa.CheckConstraint("high_price > 0", name="ck_market_data_high_positive"),
        sa.CheckConstraint("low_price > 0", name="ck_market_data_low_positive"),
        sa.CheckConstraint("close_price > 0", name="ck_market_data_close_positive"),
        sa.CheckConstraint("volume >= 0", name="ck_market_data_volume_nonnegative"),
        sa.CheckConstraint("high_price >= low_price", name="ck_market_data_high_ge_low"),
    )
    op.create_index("idx_market_data_asset_id", "market_data", ["asset_id"])
    op.create_index("idx_market_data_timestamp", "market_data", ["timestamp"])
    op.create_index("idx_market_data_asset_timestamp", "market_data", ["asset_id", "timestamp"])

    # ==========================================================================
    # SIGNALS
    # ==========================================================================

    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("signal_type", sa.String(10), nullable=False),
        sa.Column("strength", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False),
        sa.Column("price", sa.Numeric(15, 4), nullable=False),
        sa.Column("volume", sa.Numeric(15, 8), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name="fk_signals_asset_id"),
        sa.PrimaryKeyConstraint("id", name="pk_signals"),
        sa.CheckConstraint("signal_type IN ('BUY', 'SELL', 'HOLD')", name="ck_signals_signal_type"),
        sa.CheckConstraint(
            "strength IN ('WEAK', 'MODERATE', 'STRONG')", name="ck_signals_strength"
        ),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 100", name="ck_signals_confidence"),
        sa.CheckConstraint("price > 0", name="ck_signals_price_positive"),
    )
    op.create_index("idx_signals_asset_id", "signals", ["asset_id"])
    op.create_index("idx_signals_strategy_name", "signals", ["strategy_name"])
    op.create_index("idx_signals_signal_type", "signals", ["signal_type"])
    op.create_index("idx_signals_created_at", "signals", ["created_at"])

    # ==========================================================================
    # BACKTESTS
    # ==========================================================================

    op.create_table(
        "backtests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(15, 2), nullable=False),
        sa.Column("final_capital", sa.Numeric(15, 2), nullable=False),
        sa.Column("total_return", sa.Numeric(8, 4), nullable=False),
        sa.Column("sharpe_ratio", sa.Numeric(8, 4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(8, 4), nullable=True),
        sa.Column("win_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("results", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="COMPLETED"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], name="fk_backtests_portfolio_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtests"),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED')", name="ck_backtests_status"
        ),
        sa.CheckConstraint("start_date < end_date", name="ck_backtests_date_range"),
        sa.CheckConstraint("initial_capital > 0", name="ck_backtests_initial_capital"),
    )
    op.create_index("idx_backtests_portfolio_id", "backtests", ["portfolio_id"])
    op.create_index("idx_backtests_strategy_name", "backtests", ["strategy_name"])
    op.create_index("idx_backtests_start_date", "backtests", ["start_date"])
    op.create_index("idx_backtests_end_date", "backtests", ["end_date"])
    op.create_index("idx_backtests_status", "backtests", ["status"])

    # ==========================================================================
    # RISK METRICS
    # ==========================================================================

    op.create_table(
        "risk_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_date", sa.DateTime(), nullable=False),
        sa.Column("var_95", sa.Numeric(15, 2), nullable=True),
        sa.Column("var_99", sa.Numeric(15, 2), nullable=True),
        sa.Column("expected_shortfall", sa.Numeric(15, 2), nullable=True),
        sa.Column("volatility", sa.Numeric(8, 4), nullable=True),
        sa.Column("beta", sa.Numeric(8, 4), nullable=True),
        sa.Column("correlation_matrix", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], name="fk_risk_metrics_portfolio_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_risk_metrics"),
    )
    op.create_index("idx_risk_metrics_portfolio_id", "risk_metrics", ["portfolio_id"])
    op.create_index("idx_risk_metrics_calculation_date", "risk_metrics", ["calculation_date"])
    op.create_index(
        "idx_risk_metrics_portfolio_date", "risk_metrics", ["portfolio_id", "calculation_date"]
    )

    # ==========================================================================
    # SYSTEM LOGS
    # ==========================================================================

    op.create_table(
        "system_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_system_logs"),
        sa.CheckConstraint(
            "level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name="ck_system_logs_level",
        ),
    )
    op.create_index("idx_system_logs_level", "system_logs", ["level"])
    op.create_index("idx_system_logs_service", "system_logs", ["service"])
    op.create_index("idx_system_logs_timestamp", "system_logs", ["timestamp"])
    op.create_index("idx_system_logs_level_service", "system_logs", ["level", "service"])

    # ==========================================================================
    # POSITION STATES (for position monitoring persistence)
    # ==========================================================================

    op.create_table(
        "position_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("monitor_id", sa.String(255), nullable=False),
        sa.Column("positions_json", sa.Text(), nullable=False),
        sa.Column(
            "last_sync", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_position_states"),
    )
    op.create_index("idx_position_states_monitor_id", "position_states", ["monitor_id"])
    op.create_index("idx_position_states_last_sync", "position_states", ["last_sync"])
    op.create_index("idx_position_states_is_active", "position_states", ["is_active"])


def downgrade() -> None:
    """Downgrade database schema - drop all tables."""

    # Drop tables in reverse order of creation (to handle foreign key constraints)
    op.drop_table("position_states")
    op.drop_table("system_logs")
    op.drop_table("risk_metrics")
    op.drop_table("backtests")
    op.drop_table("signals")
    op.drop_table("market_data")
    op.drop_table("trades")
    op.drop_table("positions")
    op.drop_table("portfolios")
    op.drop_table("assets")
    op.drop_table("api_keys")
    op.drop_table("users")
