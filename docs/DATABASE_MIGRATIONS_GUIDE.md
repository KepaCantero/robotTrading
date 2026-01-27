# Database Migrations Guide

Complete guide for managing database migrations in the AlgoTrading Platform using Alembic.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Creating Migrations](#creating-migrations)
5. [Running Migrations](#running-migrations)
6. [Rolling Back Migrations](#rolling-back-migrations)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Reference](#reference)

---

## Overview

### What are Database Migrations?

Database migrations are version-controlled scripts that modify your database schema over time. They allow you to:

- Evolve your database schema incrementally
- Roll back changes if needed
- Keep database schema in sync with code
- Collaborate with team members safely

### Why Use Alembic?

Alembic is a database migration tool for SQLAlchemy that provides:

- **Auto-generation**: Automatically create migrations from model changes
- **Version control**: Track all schema changes
- **Rollback support**: Safely undo changes
- **Database independence**: Works with PostgreSQL, SQLite, MySQL, etc.
- **Async support**: Compatible with async SQLAlchemy

### Project Structure

```
algoTrading/
├── alembic.ini                          # Alembic configuration
├── app/
│   ├── core/
│   │   ├── config.py                    # Database URL configuration
│   │   └── database.py                  # SQLAlchemy Base and engine
│   └── database/
│       ├── models.py                    # Database models
│       └── migrations/                  # Migration scripts
│           ├── env.py                   # Migration environment
│           ├── script.py.mako           # Migration template
│           └── versions/                # Migration files
│               ├── 20260127000000_initial_schema.py
│               └── 20260127000001_fifo_tax_tracking.py
└── scripts/
    └── migrations/                      # Utility scripts
        ├── create_migration.py
        ├── upgrade.py
        ├── downgrade.py
        ├── status.py
        └── stamp.py
```

---

## Installation

### Prerequisites

Alembic is already included in `requirements.txt`:

```
alembic>=1.12.0,<2.0.0
```

### Verify Installation

```bash
# Check Alembic is installed
alembic --version

# Should output: alembic 1.x.x
```

---

## Configuration

### Database URL

The database URL is loaded from `app/core/config.py`:

```python
# For migrations, Alembic uses the sync URL
settings = get_settings()
sync_url = settings.get_database_url_sync()
```

You can override this with an environment variable:

```bash
# Override database URL for migrations
export ALEMBIC_DB_URL="postgresql://user:pass@host:port/dbname"
```

### Environment-Specific Configurations

#### Development (SQLite)

```bash
# .env file
DATABASE_URL="sqlite:///./algotrading.db"
```

#### Production (PostgreSQL)

```bash
# .env file
DATABASE_URL="postgresql://algotrading:password@localhost:5432/algotrading"
```

---

## Creating Migrations

### Method 1: Using the Helper Script (Recommended)

```bash
# Create a new migration with auto-detection
python scripts/migrations/create_migration.py "add user preferences table"
```

This will:
1. Compare your models against the current database schema
2. Generate a migration file with the detected changes
3. Save it in `app/database/migrations/versions/`

### Method 2: Using Alembic Directly

```bash
# Create migration with auto-detection
alembic revision --autogenerate -m "add user preferences table"

# Create empty migration (manual writing)
alembic revision -m "add user preferences table"
```

### Reviewing Generated Migrations

Always review the generated migration before applying:

```python
# Example: app/database/migrations/versions/20260127120000_add_user_preferences.py

"""add user preferences table

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-27 12:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'

def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('theme', sa.String(20), nullable=False, server_default='light'),
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table('user_preferences')
```

### Manual Migration Writing

If auto-generation doesn't detect your changes, write the migration manually:

```python
def upgrade() -> None:
    # Add new column
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

    # Create index
    op.create_index('idx_users_phone', 'users', ['phone'])

    # Create new table
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    # Reverse all changes in opposite order
    op.drop_table('user_settings')
    op.drop_index('idx_users_phone', table_name='users')
    op.drop_column('users', 'phone')
```

---

## Running Migrations

### Method 1: Using Helper Scripts (Recommended)

```bash
# Upgrade to latest migration
python scripts/migrations/upgrade.py

# Upgrade to specific revision
python scripts/migrations/upgrade.py --revision 0002

# Show SQL without executing
python scripts/migrations/upgrade.py --sql
```

### Method 2: Using Alembic Directly

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade 0002

# Show SQL only
alembic upgrade head --sql
```

### Checking Migration Status

```bash
# Show current revision and history
python scripts/migrations/status.py

# Or with Alembic directly
alembic current
alembic history
alembic heads
```

---

## Rolling Back Migrations

### Method 1: Using Helper Script (Recommended)

```bash
# Rollback one migration
python scripts/migrations/downgrade.py

# Rollback N migrations
python scripts/migrations/downgrade.py --steps 2

# Rollback to specific revision
python scripts/migrations/downgrade.py --revision 0001

# Show SQL without executing
python scripts/migrations/downgrade.py --sql
```

### Method 2: Using Alembic Directly

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 0001

# Rollback to base (no migrations)
alembic downgrade base
```

### Emergency Rollback

If a migration causes issues, rollback immediately:

```bash
# 1. Check current version
python scripts/migrations/status.py

# 2. Rollback to previous version
python scripts/migrations/downgrade.py

# 3. Fix the migration file

# 4. Re-apply
python scripts/migrations/upgrade.py
```

---

## Best Practices

### 1. Always Review Auto-Generated Migrations

Auto-generation isn't perfect. Always review:

```bash
# Generate migration
python scripts/migrations/create_migration.py "add new feature"

# Review the generated file
# Edit if needed: app/database/migrations/versions/XXXXX_add_new_feature.py

# Then apply
python scripts/migrations/upgrade.py
```

### 2. Write Reversible Migrations

Always implement both `upgrade()` and `downgrade()`:

```python
def upgrade() -> None:
    op.create_table('new_table', ...)
    op.add_column('users', sa.Column('new_field', sa.String(100)))

def downgrade() -> None:
    # Must reverse operations in opposite order
    op.drop_column('users', 'new_field')
    op.drop_table('new_table')
```

### 3. Use Descriptive Messages

```bash
# Good
python scripts/migrations/create_migration.py "add user two-factor authentication support"

# Bad
python scripts/migrations/create_migration.py "update db"
```

### 4. Test Migrations in Development First

```bash
# In development
cp algotrading.db algotrading.db.backup
python scripts/migrations/upgrade.py

# Test the application
# If issues arise, restore and fix migration
```

### 5. Use Transactions

Migrations run in transactions by default. If something fails, it rolls back.

### 6. Handle Data Migrations Separately

For data changes (not schema), use data migrations:

```python
from sqlalchemy.orm import Session

def upgrade() -> None:
    # Schema change
    op.add_column('users', sa.Column('status', sa.String(20), server_default='active'))

    # Data migration
    connection = op.get_bind()
    session = Session(bind=connection)

    # Update existing users
    session.execute("UPDATE users SET status = 'active' WHERE status IS NULL")
    session.commit()

def downgrade() -> None:
    op.drop_column('users', 'status')
```

### 7. Create Backups Before Production Migrations

```bash
# PostgreSQL backup
pg_dump algotrading > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite backup
cp algotrading.db algotrading.db.backup_$(date +%Y%m%d_%H%M%S)

# Then run migration
python scripts/migrations/upgrade.py
```

### 8. Use Batch Mode for SQLite

SQLite has limited ALTER TABLE support. Use batch mode:

```python
# In alembic/env.py
context.configure(
    ...,
    render_as_batch=True,  # Required for SQLite
)
```

This is already configured in the project's `env.py`.

### 9. Add Indexes for Performance

```python
def upgrade() -> None:
    # Create index on frequently queried columns
    op.create_index('idx_trades_executed_at', 'trades', ['executed_at'])
    op.create_index('idx_trades_symbol_side', 'trades', ['symbol', 'side'])
```

### 10. Use Naming Conventions

The project uses SQLAlchemy naming conventions (defined in `app/core/database.py`):

```python
convention = {
    "ix": "ix_%(column_0_label)s",      # Index
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Unique constraint
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Check constraint
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Foreign key
    "pk": "pk_%(table_name)s",  # Primary key
}
```

---

## Troubleshooting

### Issue: Migration Fails with "Foreign Key Constraint"

**Problem**: You're trying to drop a table that's referenced by another table.

**Solution**: Drop the foreign key first:

```python
def upgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_trades_portfolio_id', 'trades', type_='foreignkey')
    # Then drop the referenced table
    op.drop_table('portfolios')
```

### Issue: Auto-Generation Doesn't Detect Changes

**Problem**: Alembic doesn't see your model changes.

**Solution**:
1. Make sure your models are imported in `app/database/models.py`
2. Check that `target_metadata = Base.metadata` in `env.py`
3. Try importing the models explicitly:

```python
# In app/database/migrations/env.py
from app.database.models import (
    User, Portfolio, Position, Trade, Asset,
    MarketData, Signal, Backtest, RiskMetrics,
    SystemLog, PositionState
)
```

### Issue: SQLite "Table Already Exists" Error

**Problem**: Running migration on existing database.

**Solution**: Use `if_not_exists` or stamp the database:

```python
def upgrade() -> None:
    # Use if_not_exists for new tables
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        # ... if_not_exists is handled by batch mode
    )
```

Or stamp the database if it already has the schema:

```bash
python scripts/migrations/stamp.py --revision head
```

### Issue: Migration is Slow

**Problem**: Migration takes too long on large tables.

**Solution**:
1. Add indexes before bulk data operations
2. Use batch operations for large data changes
3. Consider disabling foreign key checks temporarily (PostgreSQL):

```python
def upgrade() -> None:
    # Disable triggers (PostgreSQL)
    op.execute("SET session_replication_role = 'replica'")

    # Perform large operations
    # ...

    # Re-enable triggers
    op.execute("SET session_replication_role = 'origin'")
```

### Issue: Can't Rollback Migration

**Problem**: The `downgrade()` function is incomplete or missing.

**Solution**: Always write complete downgrade functions:

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('new_field', sa.String(100)))

def downgrade() -> None:
    # Must reverse upgrade
    op.drop_column('users', 'new_field')
```

---

## Reference

### Common Migration Operations

#### Create Table

```python
def upgrade() -> None:
    op.create_table(
        'new_table',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('new_table')
```

#### Add Column

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'phone')
```

#### Rename Column

```python
def upgrade() -> None:
    op.alter_column('users', 'old_name', new_column_name='new_name')

def downgrade() -> None:
    op.alter_column('users', 'new_name', new_column_name='old_name')
```

#### Create Index

```python
def upgrade() -> None:
    op.create_index('idx_users_email', 'users', ['email'], unique=True)

def downgrade() -> None:
    op.drop_index('idx_users_email', table_name='users')
```

#### Add Foreign Key

```python
def upgrade() -> None:
    op.create_foreign_key(
        'fk_trades_portfolio_id',
        'trades', 'portfolios',
        ['portfolio_id'], ['id']
    )

def downgrade() -> None:
    op.drop_constraint('fk_trades_portfolio_id', 'trades', type_='foreignkey')
```

#### Bulk Data Migration

```python
from sqlalchemy.orm import Session

def upgrade() -> None:
    connection = op.get_bind()
    session = Session(bind=connection)

    # Bulk update
    connection.execute(
        "UPDATE users SET status = 'active' WHERE status IS NULL"
    )

    session.commit()

def downgrade() -> None:
    # Reverse data changes if possible
    pass
```

### Migration File Template

```python
"""Description of migration

Revision ID: XXXX
Revises: XXXX
Create Date: YYYY-MM-DD HH:MM:SS

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'XXXX'
down_revision: Union[str, None] = 'XXXXX'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade database schema."""
    pass

def downgrade() -> None:
    """Downgrade database schema."""
    pass
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection URL | `postgresql://user:pass@localhost/db` |
| `ALEMBIC_DB_URL` | Override migration DB URL | `postgresql://user:pass@localhost/db` |

### Utility Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `create_migration.py` | Create new migration | `python scripts/migrations/create_migration.py "message"` |
| `upgrade.py` | Run migrations | `python scripts/migrations/upgrade.py` |
| `downgrade.py` | Rollback migrations | `python scripts/migrations/downgrade.py` |
| `status.py` | Show migration status | `python scripts/migrations/status.py` |
| `stamp.py` | Stamp database version | `python scripts/migrations/stamp.py --revision head` |

---

## Summary

1. **Create migrations** using helper scripts: `python scripts/migrations/create_migration.py "message"`
2. **Review** the generated migration file
3. **Apply** migrations: `python scripts/migrations/upgrade.py`
4. **Check status**: `python scripts/migrations/status.py`
5. **Rollback** if needed: `python scripts/migrations/downgrade.py`

**Remember**: Always test migrations in development before production!
