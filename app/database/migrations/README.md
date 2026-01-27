# Database Migrations

This directory contains Alembic database migrations for the AlgoTrading Platform.

## Quick Start

```bash
# Create a new migration
python scripts/migrations/create_migration.py "description of changes"

# Apply migrations
python scripts/migrations/upgrade.py

# Check status
python scripts/migrations/status.py

# Rollback
python scripts/migrations/downgrade.py
```

## Directory Structure

```
app/database/migrations/
├── env.py                  # Alembic environment configuration
├── script.py.mako          # Migration file template
└── versions/               # Migration files
    ├── 20260127000000_initial_schema.py
    └── 20260127000001_fifo_tax_tracking.py
```

## Existing Migrations

### 0001 - Initial Schema (2026-01-27)

Creates all core tables:
- Users & authentication (users, api_keys)
- Trading data (assets, portfolios, positions, trades)
- Market data (market_data)
- Backtesting (backtests, signals)
- Risk management (risk_metrics)
- System logging (system_logs)
- Position monitoring (position_states)

### 0002 - FIFO Tax Tracking (2026-01-27)

Adds tax compliance tables for Spain (Modelo 721):
- Accounts (exchanges, brokers, wallets)
- Transactions (FIFO-enabled trading records)
- Lots (FIFO cost basis tracking)
- Balance Snapshots (annual reporting)
- Tax Reports (Modelo 721/720)

## Configuration

Migrations use the database URL from `app/core/config.py`:

```python
# Settings are loaded automatically
settings = get_settings()
sync_url = settings.get_database_url_sync()
```

Override with environment variable:

```bash
export ALEMBIC_DB_URL="postgresql://user:pass@host:port/dbname"
```

## Development Workflow

1. Make changes to models in `app/database/models.py`
2. Create migration: `python scripts/migrations/create_migration.py "changes"`
3. Review generated migration in `versions/`
4. Apply: `python scripts/migrations/upgrade.py`
5. Test application
6. Commit both model changes and migration

## Best Practices

- Always review auto-generated migrations
- Write reversible migrations (implement `downgrade()`)
- Test migrations in development first
- Use descriptive migration messages
- Create backups before production migrations
- Keep migrations small and focused

## Documentation

See [Database Migrations Guide](../../docs/DATABASE_MIGRATIONS_GUIDE.md) for complete documentation.

## Utility Scripts

Located in `scripts/migrations/`:

- `create_migration.py` - Create new migration
- `upgrade.py` - Apply migrations
- `downgrade.py` - Rollback migrations
- `status.py` - Show migration status
- `stamp.py` - Mark database version

## Troubleshooting

### Migration fails

1. Check current status: `python scripts/migrations/status.py`
2. Review error message
3. Fix migration file
4. Rollback if needed: `python scripts/migrations/downgrade.py`
5. Re-apply: `python scripts/migrations/upgrade.py`

### Database already has schema

Stamp the database as current:

```bash
python scripts/migrations/stamp.py --revision head
```

### Auto-generation doesn't work

Ensure models are imported in `env.py`:

```python
from app.database.models import (
    User, Portfolio, Position, Trade, Asset,
    MarketData, Signal, Backtest, RiskMetrics,
    SystemLog, PositionState
)
```

## Support

For issues or questions:
1. Check the [Migration Guide](../../docs/DATABASE_MIGRATIONS_GUIDE.md)
2. Review Alembic documentation: https://alembic.sqlalchemy.org/
3. Contact the development team
