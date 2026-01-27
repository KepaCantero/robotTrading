# Database Migrations Quick Reference

Fast reference for common database migration operations.

## Commands

### Create New Migration
```bash
python scripts/migrations/create_migration.py "description"
```

### Apply Migrations
```bash
# Upgrade to latest
python scripts/migrations/upgrade.py

# Upgrade to specific version
python scripts/migrations/upgrade.py --revision 0002

# Preview SQL only
python scripts/migrations/upgrade.py --sql
```

### Rollback Migrations
```bash
# Rollback one migration
python scripts/migrations/downgrade.py

# Rollback N migrations
python scripts/migrations/downgrade.py --steps 2

# Rollback to specific version
python scripts/migrations/downgrade.py --revision 0001
```

### Check Status
```bash
# Show current version and history
python scripts/migrations/status.py

# Verbose output
python scripts/migrations/status.py --verbose
```

### Mark Existing Database
```bash
# Mark database as current (without running migrations)
python scripts/migrations/stamp.py --revision head
```

### Test Migrations
```bash
# Test on fresh database
python scripts/migrations/test_migrations.py
```

## Environment Variables

```bash
# Override database URL for migrations
export ALEMBIC_DB_URL="postgresql://user:pass@host:port/dbname"

# Or use the main DATABASE_URL
export DATABASE_URL="sqlite:///./algotrading.db"
```

## Workflow

1. **Modify Models**: Edit files in `app/database/models.py`
2. **Create Migration**: `python scripts/migrations/create_migration.py "changes"`
3. **Review**: Check generated file in `app/database/migrations/versions/`
4. **Apply**: `python scripts/migrations/upgrade.py`
5. **Test**: Run your application
6. **Rollback** (if needed): `python scripts/migrations/downgrade.py`

## Current Migrations

| Revision | Description | Date |
|----------|-------------|------|
| 0001 | Initial schema (all core tables) | 2026-01-27 |
| 0002 | FIFO tax tracking (PostgreSQL only) | 2026-01-27 |

## Files

- **Configuration**: `alembic.ini`
- **Environment**: `app/database/migrations/env.py`
- **Migrations**: `app/database/migrations/versions/`
- **Scripts**: `scripts/migrations/`
- **Guide**: `docs/DATABASE_MIGRATIONS_GUIDE.md`

## Tips

- Always review auto-generated migrations
- Test migrations in development first
- Create backups before production changes
- Write reversible migrations (implement `downgrade()`)
- Use descriptive migration messages

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Migration fails | Check status, rollback, fix, re-apply |
| Auto-gen doesn't work | Ensure models are imported in `env.py` |
| Existing database | Use `stamp.py --revision head` |
| SQLite errors | Migration 0002 requires PostgreSQL (auto-skips) |

## More Information

See [Database Migrations Guide](DATABASE_MIGRATIONS_GUIDE.md) for complete documentation.
