"""Add accounts.asset_type column with backfill

The Account model gained an `asset_type` field (AssetType enum) used by the
Modelo 721/720 fiscal queries, but the column never existed in the schema —
the queries would fail at runtime. This migration adds the column and
backfills it from the existing exchange_type/currency data:

- CEX/DEX/WALLET/OTC accounts  -> crypto
- BROKER accounts in EUR       -> stock_eu
- BROKER accounts in USD       -> stock_us
- anything else                -> forex

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17

"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str | None = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None

ASSET_TYPE_ENUM = sa.Enum(
    "crypto",
    "stock_us",
    "stock_eu",
    "forex",
    "etf",
    name="assettype",
)


def upgrade() -> None:
    # crear el tipo ENUM explícitamente (create_type implícito falla en PG real
    # cuando la tabla referenciara el tipo antes de su creación)
    sa.Enum("crypto", "stock_us", "stock_eu", "forex", "etf", name="assettype").create(
        op.get_bind(), checkfirst=True
    )
    op.add_column(
        "accounts",
        sa.Column(
            "asset_type",
            sa.Enum("crypto", "stock_us", "stock_eu", "forex", "etf", name="assettype"),
            nullable=True,
        ),
    )

    # Backfill derivado de exchange_type/currency
    op.execute(
        """
        UPDATE accounts SET asset_type = 'crypto'
        WHERE exchange_type IN ('cex', 'dex', 'wallet', 'otc')
        """
    )
    op.execute(
        """
        UPDATE accounts SET asset_type = 'stock_eu'
        WHERE asset_type IS NULL AND exchange_type = 'broker' AND currency = 'EUR'
        """
    )
    op.execute(
        """
        UPDATE accounts SET asset_type = 'stock_us'
        WHERE asset_type IS NULL AND exchange_type = 'broker' AND currency = 'USD'
        """
    )
    op.execute("UPDATE accounts SET asset_type = 'forex' WHERE asset_type IS NULL")

    op.alter_column(
        "accounts",
        "asset_type",
        nullable=False,
        server_default="crypto",
    )
    logger.info("accounts.asset_type añadida y backfill aplicado")


def downgrade() -> None:
    op.drop_column("accounts", "asset_type")
