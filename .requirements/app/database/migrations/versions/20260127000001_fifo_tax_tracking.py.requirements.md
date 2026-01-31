# 20260127000001_fifo_tax_tracking.py

## Purpose
Alembic migration that adds FIFO (First-In-First-Out) tax tracking tables for Spanish tax compliance (Modelo 721), including accounts, transactions, lots, balance snapshots, and tax reports for cryptocurrency and asset trading.

---

## Type Definitions / Data Classes

### Migration Metadata
```python
revision: str                       # REQUIRED - "0002" - unique migration identifier
down_revision: str | None           # REQUIRED - "0001" - depends on initial schema
branch_labels: str | Sequence[str] | None  # OPTIONAL - None
depends_on: str | Sequence[str] | None     # OPTIONAL - None
```

### Account Type Enum
```python
exchange_type: str                 # REQUIRED, one of: cex, dex, broker, wallet, otc
```

### Transaction Type Enum
```python
asset_type: str                    # REQUIRED, one of: crypto, stock_us, stock_eu, forex, etf
tx_type: str                       # REQUIRED, one of: buy, sell, transfer_in, transfer_out,
                                  #          staking_reward, mining_reward, airdrop, fork, fee, gas
```

### Lot Status Enum
```python
status: str                        # REQUIRED, one of: open, closed, partial
```

### Tax Report Type Enum
```python
report_type: str                   # REQUIRED - e.g., "721", "720"
```

### Tax Report Status Enum
```python
status: str                        # REQUIRED, one of: draft, final, filed
```

---

## Function Signatures (Contracts)

### `upgrade() -> None`
**Pre:** Database exists, initial schema migration (0001) is applied
**Post:** FIFO tracking tables are created if PostgreSQL; skipped if SQLite
**Raises:** sqlalchemy.exc.* on database errors (PostgreSQL only)
**Retry:** No
**Side Effects:** Creates 5 tables on PostgreSQL: accounts, transactions, lots, balance_snapshots, tax_reports

### `downgrade() -> None`
**Pre:** FIFO tracking tables exist (PostgreSQL only)
**Post:** FIFO tracking tables are dropped
**Raises:** sqlalchemy.exc.* on database errors (PostgreSQL only)
**Retry:** No
**Side Effects:** Drops 5 tables on PostgreSQL; no-op on SQLite

---

## Acceptance Criteria
- [ ] Migration skips gracefully on SQLite (prints warning message)
- [ ] All 5 tables are created on PostgreSQL
- [ ] All foreign key constraints point to correct tables
- [ ] All check constraints enforce proper enum values
- [ ] All indexes are created for query performance
- [ ] All unique constraints prevent duplicates
- [ ] All DateTime fields use timezone=True for PostgreSQL
- [ ] All JSONB fields have server_default="{}"
- [ ] Encrypted API credential fields are Text type
- [ ] Balance snapshots support both regular and EUR-denominated balances
- [ ] Tax reports support amendments via is_amended flag
- [ ] Downgrade only runs on PostgreSQL (skips SQLite)
- [ ] Lot tracking enforces quantity_remaining <= quantity_opened
- [ ] Transactions support both internal and external account references

---

## Critical Rules (MUST NOT BREAK)

**Universal rules:** See `../../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| DB-001 | Migration-specific | Numeric precision for money | ✅ OK - Uses Numeric(36,18) for high precision |
| DB-002 | Migration-specific | FK columns indexed | ✅ OK - All FKs have indexes |
| DB-003 | Migration-specific | Cascade behavior defined | ⚠️ CHECK - No explicit ON DELETE in FKs |
| DB-004 | Migration-specific | Check constraints at DB level | ✅ OK - Enum check constraints |
| DB-005 | Migration-specific | Unique constraints at DB level | ✅ OK - Multiple unique constraints |
| DB-006 | Migration-specific | Index naming convention | ✅ OK - idx_tablename_columns |
| DB-007 | Migration-specific | Constraint naming convention | ✅ OK - ck_tablename_rule |
| DB-011 | Migration-specific | Cross-database compatibility | ✅ OK - Detects dialect, skips on SQLite |
| SEC-010 | BASE_RULES.md | Encryption at rest | ⚠️ CHECK - api_key_encrypted must be encrypted |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ⚠️ CHECK - Verify encryption/decryption code |
| TRD-004 | BASE_RULES.md | Audit trail for trading | ✅ OK - Transactions have occurred_at, recorded_at |
| RSK-001 | BASE_RULES.md | VaR calculation supported | ⚠️ N/A - Tax compliance, not risk |
| ARCH-001 | BASE_RULES.md | Infrastructure layer | ✅ OK - In migrations (infrastructure) |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ N/A - Alembic handles errors |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - Prints WARNING on skip |

**FIFO Tracking Rules:**

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| FIFO-001 | Lot integrity | quantity_remaining <= quantity_opened | **P0** |
| FIFO-002 | Lot status | Status must be open/closed/partial | **P0** |
| FIFO-003 | Cost basis tracking | Track cost_basis_open accurately | **P0** |
| FIFO-004 | Holding period | Calculate holding_period_days | **P0** |
| FIFO-005 | Tax year assignment | Auto-calculate tax_year_closed | **P0** |
| FIFO-006 | Transaction types | Validate tx_type enum | **P0** |
| FIFO-007 | Asset types | Validate asset_type enum | **P0** |
| FIFO-008 | Account linking | Support from_account_id, to_account_id | **P0** |
| FIFO-009 | Balance snapshots | Capture EUR values for Modelo 721 | **P0** |
| FIFO-010 | Report amendments | Support is_amended, amended_from_id | **P0** |
| FIFO-011 | Timezone awareness | All DateTime fields use timezone=True | **P0** |
| FIFO-012 | Cross-database | Skip migration on SQLite gracefully | **P0** |
| FIFO-013 | Verification | Support is_verified flag for audit | P1 |
| FIFO-014 | Settlement dates | Track settled_at, settlement_date | P1 |

---

## Dependencies
- **External:**
  - `alembic.op` - Alembic operations API
  - `sqlalchemy` - SQLAlchemy schema types
  - `sqlalchemy.dialects.postgresql` - PostgreSQL-specific types (UUID, JSONB, timezone-aware DateTime)
  - `typing` - Type hints (Sequence, Union)

- **Internal:**
  - Migration 0001 (initial schema) - required for accounts foreign key to users

---

## Required Tests
- **tests/database/migrations/versions/test_20260127000001_fifo_tax_tracking.py:**
  - Test upgrade creates 5 tables on PostgreSQL
  - Test upgrade skips gracefully on SQLite with warning
  - Test downgrade removes all tables on PostgreSQL
  - Test downgrade is no-op on SQLite
  - Test check constraints enforce enum values
  - Test lot quantity constraints (remaining <= opened)
  - Test unique constraint on (external_id, account_id)
  - Test tax report unique constraint handles amendments
  - Test timezone-aware DateTime fields work correctly
  - Test JSONB fields accept dict data
  - Test encrypted credential fields accept large text
  - Test foreign key constraints prevent invalid references
  - Test balance snapshots store EUR values correctly
  - Test transaction-lot relationship works correctly
  - Test tax report status transitions work correctly

---

## Notes
- This migration is **PostgreSQL-only** - SQLite skips gracefully (for development)
- Uses PostgreSQL-specific features: JSONB (not JSON), timezone-aware DateTime
- High precision Numeric(36,18) for cryptocurrency quantities (satoshis, wei)
- Supports both centralized exchanges (CEX) and decentralized exchanges (DEX)
- Implements FIFO lot tracking for accurate capital gains calculation
- Designed for Spanish tax compliance: Modelo 721 (crypto) and Modelo 720 (foreign assets)
- Balance snapshots capture end-of-year balances for tax reporting
- Tax reports support amendments for corrected filings
- API credentials are stored encrypted (application layer must implement encryption)
- Transaction types cover all crypto operations: staking, mining, airdrops, forks
