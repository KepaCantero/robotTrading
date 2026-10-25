"""Create the live-trading tables (Fase 2, A20)

OrderManager/TradePersistenceManager models (order_records, trade_records,
position_history, trade_statistics in app/services/live_trading/
trade_persistence.py) were never part of any migration: a database created
with `alembic upgrade head` lacked them and persistence failed at first
use even though the API had started. This migration creates the four
tables exactly as the ORM declares them.

Audit acceptance (A20): base vacía → alembic upgrade head → guardar y leer
orden/fill/posición.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str | None = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "order_records",
        sa.Column("order_id", sa.String(36), primary_key=True),
        sa.Column("symbol", sa.String(10), nullable=False, index=True),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("price", sa.Numeric(18, 8), nullable=True),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("broker_name", sa.String(20), nullable=False),
        sa.Column("broker_order_id", sa.String(50), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("retry_count", sa.String(3), nullable=False, server_default="0"),
    )
    op.create_index("idx_symbol_created", "order_records", ["symbol", "created_at"])
    op.create_index("idx_status_created", "order_records", ["status", "created_at"])

    op.create_table(
        "trade_records",
        sa.Column("trade_id", sa.String(36), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(36),
            sa.ForeignKey("order_records.order_id"),
            nullable=False,
            index=True,
        ),
        sa.Column("symbol", sa.String(10), nullable=False, index=True),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("execution_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("execution_time", sa.DateTime(), nullable=False, index=True),
        sa.Column("commission", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("slippage", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("market_impact", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("fill_type", sa.String(20), nullable=False),
        sa.Column("broker_trade_id", sa.String(50), nullable=True, unique=True),
    )

    op.create_table(
        "position_history",
        sa.Column("position_id", sa.String(36), primary_key=True),
        sa.Column("symbol", sa.String(10), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("average_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("market_value", sa.Numeric(18, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(18, 8), nullable=False),
        sa.Column("unrealized_pnl_pct", sa.Numeric(10, 4), nullable=False),
        sa.Column("cost_basis", sa.Numeric(18, 8), nullable=False),
    )

    op.create_table(
        "trade_statistics",
        sa.Column("stat_id", sa.String(36), primary_key=True),
        sa.Column("date", sa.DateTime(), nullable=False, index=True, unique=True),
        sa.Column("total_trades", sa.String(5), nullable=False, server_default="0"),
        sa.Column("total_volume", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("total_commission", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("avg_slippage", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("winning_trades", sa.String(5), nullable=False, server_default="0"),
        sa.Column("losing_trades", sa.String(5), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("trade_statistics")
    op.drop_table("position_history")
    op.drop_table("trade_records")
    op.drop_index("idx_status_created", table_name="order_records")
    op.drop_index("idx_symbol_created", table_name="order_records")
    op.drop_table("order_records")
