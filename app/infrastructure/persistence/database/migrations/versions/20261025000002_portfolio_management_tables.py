"""Create the portfolio-management tables (robo-advisor mode)

Tables for app/services/portfolio_management/store.py (TargetPortfolioRecord,
PortfolioLotRecord, RebalanceEventRecord): versioned target allocations,
per-lot purchase records for Spain tax-aware FIFO selling, and the
plain-language rebalance history. Created in the same migration as the ORM
declares them (A20 lesson: a table that only exists in the ORM fails the
first time a database was built with `alembic upgrade head`).

Audit acceptance (A20 pattern): base vacía → alembic upgrade head → guardar
y leer target portfolio / lote / evento de rebalanceo.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str | None = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "target_portfolios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("source_run_id", sa.String(64), nullable=True),
        sa.Column("strategy_name", sa.String(50), nullable=True),
        sa.Column("decision_status", sa.String(20), nullable=True),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("holdings_json", sa.JSON(), nullable=False),
        sa.Column("drift_band_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("cooldown_days", sa.Integer(), nullable=False),
        sa.Column("reactive_only", sa.Boolean(), nullable=False),
        sa.Column("max_position_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("equity_max_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_target_portfolios_created_at", "target_portfolios", ["created_at"])
    op.create_index("idx_target_portfolios_active", "target_portfolios", ["is_active", "version"])

    op.create_table(
        "portfolio_lots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("remaining", sa.Numeric(18, 6), nullable=False),
        sa.Column("purchase_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_portfolio_lots_symbol", "portfolio_lots", ["symbol"])
    op.create_index("ix_portfolio_lots_purchased_at", "portfolio_lots", ["purchased_at"])
    op.create_index("idx_portfolio_lots_symbol_date", "portfolio_lots", ["symbol", "purchased_at"])

    op.create_table(
        "rebalance_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_rebalance_events_ts", "rebalance_events", ["ts"])


def downgrade() -> None:
    op.drop_index("ix_rebalance_events_ts", table_name="rebalance_events")
    op.drop_table("rebalance_events")
    op.drop_index("idx_portfolio_lots_symbol_date", table_name="portfolio_lots")
    op.drop_index("ix_portfolio_lots_purchased_at", table_name="portfolio_lots")
    op.drop_index("ix_portfolio_lots_symbol", table_name="portfolio_lots")
    op.drop_table("portfolio_lots")
    op.drop_index("idx_target_portfolios_active", table_name="target_portfolios")
    op.drop_index("ix_target_portfolios_created_at", table_name="target_portfolios")
    op.drop_table("target_portfolios")
