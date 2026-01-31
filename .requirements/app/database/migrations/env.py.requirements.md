# env.py

## Purpose
Alembic migration environment configuration that provides database connection and metadata for database schema migrations in both synchronous and asynchronous modes.

---

## Type Definitions / Data Classes

### Configuration Objects
```python
config: object                      # Alembic Config object from alembic.config
target_metadata: MetaData           # SQLAlchemy MetaData from app.database.Base
```

---

## Function Signatures (Contracts)

### `run_migrations_offline() -> None`
**Pre:** Configuration has valid sqlalchemy.url
**Post:** Migration SQL is generated without database connection
**Raises:** ConfigurationError if URL missing
**Retry:** No
**Side Effects:** Outputs SQL migration script to stdout

### `do_run_migrations(connection) -> None`
**Pre:** Connection is valid and active
**Post:** Migrations are executed against the connection
**Raises:** sqlalchemy.exc.* exceptions on DB errors
**Retry:** No
**Side Effects:** Modifies database schema

### `run_async_migrations() -> coroutine`
**Pre:** Async database URL is configured
**Post:** Migrations are executed using async connection
**Raises:** asyncio.TimeoutError, sqlalchemy.exc.* exceptions
**Retry:** No
**Side Effects:** Creates async engine, executes migrations, disposes engine

### `run_migrations_online() -> None`
**Pre:** Database is accessible
**Post:** Migrations are executed against database
**Raises:** sqlalchemy.exc.* on DB connection or migration errors
**Retry:** No
**Side Effects:** Creates engine, runs migrations, closes connection

---

## Acceptance Criteria
- [ ] Migrations work correctly with both PostgreSQL and SQLite databases
- [ ] Async migrations are properly detected and executed for asyncpg/aiosqlite drivers
- [ ] ALEMBIC_DB_URL environment variable overrides settings database URL
- [ ] Batch migrations are enabled (`render_as_batch=True`) for SQLite compatibility
- [ ] Target metadata correctly imports all models from app.database
- [ ] Offline mode generates valid SQL without database connection
- [ ] Online mode properly disposes connections after migration
- [ ] Sync URL is correctly derived from async settings for Alembic
- [ ] Path manipulation correctly adds app to sys.path for imports
- [ ] Logging configuration is loaded from alembic.ini if present

---

## Critical Rules (MUST NOT BREAK)

**Universal rules:** See `../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-002 | BASE_RULES.md | Environment variables for deployment | ✅ OK - ALEMBIC_DB_URL supported |
| CFG-003 | BASE_RULES.md | Configuration validation | ⚠️ CHECK - Settings validation happens via get_settings() |
| ASYNC-001 | BASE_RULES.md | Use async def for async functions | ✅ OK - run_async_migrations() properly async |
| ASYNC-002 | BASE_RULES.md | Await async calls | ✅ OK - Properly awaits connection.run_sync() |
| ASYNC-003 | BASE_RULES.md | Async context managers | ✅ OK - Uses async with for connection |
| ARCH-005 | BASE_RULES.md | Early returns | ⚠️ N/A - Linear control flow, no nesting |
| CC-006 | BASE_RULES.md | Explicit error handling | ❌ GAP - No try/except for DB errors |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ❌ GAP - No logging on migration failures |
| LOG-007 | BASE_RULES.md | Health checks | ⚠️ N/A - Alembic handles connection checks |
| FMT-008 | BASE_RULES.md | Context managers for resources | ✅ OK - Uses with statements for connections |

**Migration-Specific Rules:**

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| MIG-001 | Batch mode | Always enable render_as_batch for SQLite | **P0** |
| MIG-002 | URL override | Support ALEMBIC_DB_URL environment variable | P1 |
| MIG-003 | Sync URL conversion | Convert async URL to sync for Alembic | **P0** |
| MIG-004 | Connection cleanup | Always dispose connections after migrations | **P0** |
| MIG-005 | Path manipulation | Add parent dir to sys.path before imports | **P0** |
| MIG-006 | Driver detection | Auto-detect async/sync driver from URL | P1 |
| MIG-007 | Metadata import | Import Base.metadata from app.database | **P0** |
| MIG-008 | Offline mode support | Generate SQL without DB connection | P1 |
| MIG-009 | Error propagation | Let Alembic handle migration errors | P2 |
| MIG-010 | Transaction handling | Use context.begin_transaction() | **P0** |

---

## Dependencies
- **External:**
  - `alembic` - Database migration framework
  - `sqlalchemy` - ORM and database toolkit
  - `sqlalchemy.ext.asyncio` - Async engine support
  - `asyncio` - Async runtime
  - `logging.config` - Logging configuration
  - `os`, `sys` - System operations

- **Internal:**
  - `app.core.config.get_settings` - Application settings
  - `app.database.Base` - Declarative base with metadata

---

## Required Tests
- **tests/database/migrations/test_env.py:**
  - Offline mode generates valid SQL
  - Online mode executes migrations successfully
  - Async mode detected and executed correctly for asyncpg URLs
  - ALEMBIC_DB_URL override works correctly
  - Sync URL properly derived from settings
  - Connection cleanup happens after migration
  - Batch mode is enabled for SQLite
  - Metadata includes all models
  - Path manipulation allows imports
  - Logging configuration loads from alembic.ini

---

## Notes
- This file is generated by Alembic (`alembic init migrations`) and modified for async support
- The async migration support is critical for production PostgreSQL with asyncpg driver
- Batch mode (`render_as_batch=True`) is required for SQLite but also works with PostgreSQL
- Connection pooling is disabled (`poolclass=pool.NullPool`) during migrations to avoid connection leaks
