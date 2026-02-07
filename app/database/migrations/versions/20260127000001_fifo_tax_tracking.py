"""Add FIFO tax tracking for Modelo 721 (Spain tax compliance)

This migration adds tables for tracking cryptocurrency and asset trades
for Spanish tax compliance (Modelo 721 - cryptocurrency reporting).

NOTE: This migration uses PostgreSQL-specific features (JSONB, timezone-aware datetimes).
For SQLite compatibility in development, this migration is optional and can be skipped.

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add FIFO tracking tables."""

    # Check if running on PostgreSQL
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    if not is_postgresql:
        # Skip this migration on SQLite
        logger.debug("WARNING: FIFO tax tracking migration requires PostgreSQL.")
        logger.debug("         Skipping migration on SQLite database.")
        return

    # ==========================================================================
    # ACCOUNTS (trading accounts/exchanges)
    # ==========================================================================

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_name", sa.String(100), nullable=False),
        sa.Column("exchange_type", sa.String(20), nullable=False),
        sa.Column("exchange_name", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("api_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("wallet_address", sa.String(255), nullable=True),
        sa.Column("balance_cached", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("balance_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
        sa.CheckConstraint(
            "exchange_type IN ('cex', 'dex', 'broker', 'wallet', 'otc')",
            name="ck_accounts_exchange_type",
        ),
    )
    op.create_index("idx_accounts_user_active", "accounts", ["user_id", "is_active"])
    op.create_index("idx_accounts_exchange_currency", "accounts", ["exchange_name", "currency"])

    # ==========================================================================
    # TRANSACTIONS (FIFO-enabled transactions)
    # ==========================================================================

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("exchange_tx_id", sa.String(255), nullable=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("tx_type", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=True),
        sa.Column("quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("quantity_symbol", sa.String(20), nullable=False),
        sa.Column("price", sa.Numeric(36, 18), nullable=True),
        sa.Column("total_value", sa.Numeric(36, 18), nullable=True),
        sa.Column("fee_amount", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("fee_currency", sa.String(10), nullable=False),
        sa.Column("fee_included", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settlement_date", sa.Date(), nullable=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_taxable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("from_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_address", sa.String(255), nullable=True),
        sa.Column("to_address", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_transactions_account_id"),
        sa.ForeignKeyConstraint(
            ["from_account_id"], ["accounts.id"], name="fk_transactions_from_account_id"
        ),
        sa.ForeignKeyConstraint(
            ["to_account_id"], ["accounts.id"], name="fk_transactions_to_account_id"
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], name="fk_transactions_lot_id"),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        sa.UniqueConstraint("external_id", "account_id", name="uq_tx_external_account"),
        sa.CheckConstraint(
            "asset_type IN ('crypto', 'stock_us', 'stock_eu', 'forex', 'etf')",
            name="ck_transactions_asset_type",
        ),
        sa.CheckConstraint(
            "tx_type IN ('buy', 'sell', 'transfer_in', 'transfer_out', 'staking_reward', 'mining_reward', 'airdrop', 'fork', 'fee', 'gas')",
            name="ck_transactions_tx_type",
        ),
    )
    op.create_index("idx_transactions_symbol_type", "transactions", ["symbol", "tx_type"])
    op.create_index("idx_transactions_occurred", "transactions", ["occurred_at"])
    op.create_index("idx_transactions_tax_year", "transactions", ["tax_year"])

    # ==========================================================================
    # LOTS (FIFO lots for cost basis tracking)
    # ==========================================================================

    op.create_table(
        "lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("opening_transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_opened", sa.Numeric(36, 18), nullable=False),
        sa.Column("cost_basis_open", sa.Numeric(36, 18), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(36, 18), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("realized_gain", sa.Numeric(36, 18), nullable=True),
        sa.Column("realized_loss", sa.Numeric(36, 18), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("holding_period_days", sa.Integer(), nullable=True),
        sa.Column("tax_year_closed", sa.Integer(), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_lots_account_id"),
        sa.ForeignKeyConstraint(
            ["opening_transaction_id"], ["transactions.id"], name="fk_lots_opening_transaction_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lots"),
        sa.CheckConstraint(
            "asset_type IN ('crypto', 'stock_us', 'stock_eu', 'forex', 'etf')",
            name="ck_lots_asset_type",
        ),
        sa.CheckConstraint("status IN ('open', 'closed', 'partial')", name="ck_lots_status"),
        sa.CheckConstraint("quantity_remaining >= 0", name="ck_lot_remaining_positive"),
        sa.CheckConstraint(
            "quantity_remaining <= quantity_opened", name="ck_lot_remaining_le_opened"
        ),
    )
    op.create_index("idx_lots_symbol_status", "lots", ["symbol", "status"])
    op.create_index("idx_lots_opened", "lots", ["opened_at"])

    # ==========================================================================
    # BALANCE SNAPSHOTS (for Modelo 721 - annual reporting)
    # ==========================================================================

    op.create_table(
        "balance_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_type", sa.String(20), nullable=False),
        sa.Column("balance", sa.Numeric(36, 18), nullable=False),
        sa.Column("balance_eur", sa.Numeric(36, 18), nullable=False),
        sa.Column("exchange_rate_eur", sa.Numeric(18, 8), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name="fk_balance_snapshots_account_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_balance_snapshots"),
    )
    op.create_index(
        "idx_balances_account_captured", "balance_snapshots", ["account_id", "captured_at"]
    )

    # ==========================================================================
    # TAX REPORTS (Modelo 721/720)
    # ==========================================================================

    op.create_table(
        "tax_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(20), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("report_data", postgresql.JSONB(), nullable=False),
        sa.Column("total_holdings_eur", sa.Numeric(36, 18), nullable=False),
        sa.Column("total_gain_eur", sa.Numeric(36, 18), nullable=False),
        sa.Column("total_loss_eur", sa.Numeric(36, 18), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_amended", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("amended_from_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_tax_reports"),
        sa.UniqueConstraint(
            "user_id",
            "report_type",
            "tax_year",
            "is_amended",
            name="uq_tax_report_user_type_year_amended",
        ),
        sa.CheckConstraint("status IN ('draft', 'final', 'filed')", name="ck_tax_reports_status"),
    )
    op.create_index("idx_tax_reports_user_year", "tax_reports", ["user_id", "tax_year"])


def downgrade() -> None:
    """Downgrade database schema - remove FIFO tracking tables."""

    # Check if running on PostgreSQL
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    if not is_postgresql:
        # Skip this migration on SQLite (tables don't exist)
        return

    # Drop tables in reverse order
    op.drop_table("tax_reports")
    op.drop_table("balance_snapshots")
    op.drop_table("lots")
    op.drop_table("transactions")
    op.drop_table("accounts")
