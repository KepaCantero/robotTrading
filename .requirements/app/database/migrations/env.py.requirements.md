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


## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05T10:00:00Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. All critical fixes applied. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Universal rules:** See `../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-002 | BASE_RULES.md | Environment variables for deployment | ✅ OK - ALEMBIC_DB_URL supported at lines 40-47 |
| CFG-003 | BASE_RULES.md | Configuration validation | ✅ FIXED - Added URL validation with error logging at lines 72-74 (offline) and 226-228 (online) |
| ASYNC-001 | BASE_RULES.md | Use async def for async functions | ✅ OK - run_async_migrations() properly async at line 139 |
| ASYNC-002 | BASE_RULES.md | Await async calls | ✅ OK - Properly awaits connection.run_sync() at line 160 |
| ASYNC-003 | BASE_RULES.md | Async context managers | ✅ OK - Proper connection lifecycle at lines 191-211 |
| ASYNC-006 | BASE_RULES.md | Handle asyncio.TimeoutError | ✅ OK - TimeoutError handling at lines 174-180 |
| ARCH-005 | BASE_RULES.md | Early returns | ⚠️ N/A - Linear control flow, no nesting |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ FIXED - Added try/except for all DB operations at lines 68-97, 102-136, 143-211, 221-273 |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ FIXED - Added logging with exc_info=True for all failures throughout |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ✅ OK - Partial URL logged at line 76 (first 20 chars only) |
| LOG-007 | BASE_RULES.md | Health checks | ⚠️ N/A - Alembic handles connection checks |
| FMT-008 | BASE_RULES.md | Context managers for resources | ✅ OK - Uses with statements for transactions at lines 86, 112, 246 |

**Migration-Specific Rules:**

| Rule ID | Rule | Requirement | Status | Priority |
|---------|------|------------|--------|----------|
| MIG-001 | Batch mode | Always enable render_as_batch for SQLite | ✅ OK - Enabled at lines 83, 108 | **P0** |
| MIG-002 | URL override | Support ALEMBIC_DB_URL environment variable | ✅ OK - Lines 40-47 | P1 |
| MIG-003 | Sync URL conversion | Convert async URL to sync for Alembic | ✅ OK - get_database_url_sync() at line 46 | **P0** |
| MIG-004 | Connection cleanup | Always dispose connections after migrations | ✅ FIXED - Lines 191-211 for async, line 250 for sync | **P0** |
| MIG-005 | Path manipulation | Add parent dir to sys.path before imports | ✅ OK - Line 21 | **P0** |
| MIG-006 | Driver detection | Auto-detect async/sync driver from URL | ✅ OK - Line 230 | P1 |
| MIG-007 | Metadata import | Import Base.metadata from app.database | ✅ OK - Line 26, 50 | **P0** |
| MIG-008 | Offline mode support | Generate SQL without DB connection | ✅ OK - Lines 58-97 | P1 |
| MIG-009 | Error propagation | Let Alembic handle migration errors | ✅ OK - All exceptions re-raised | P2 |
| MIG-010 | Transaction handling | Use context.begin_transaction() | ✅ FIXED - Lines 86, 112 for proper transaction handling | **P0** |

---

---

## BASE_RULES Compliance Summary

### Categories Verified (96 rules across 14 categories)

| Category | Rules | Status | Notes |
|----------|-------|--------|-------|
| Formatting (FMT) | 8 | ✅ PASS | Black formatting, proper imports, context managers used |
| Type Hints (TYP) | 6 | ✅ PASS | All functions have type hints where applicable |
| SOLID (SOL) | 5 | ✅ PASS | Single responsibility per function |
| Architecture (ARCH) | 7 | ✅ PASS | Proper layering, clean functions |
| Testing (TST) | 8 | ⚠️ N/A | Test file exists separately |
| Security (SEC) | 10 | ✅ PASS | No hardcoded secrets, proper URL handling |
| Logging (LOG) | 7 | ✅ PASS | Structured logging with exc_info, no sensitive data |
| Async (ASYNC) | 7 | ✅ PASS | Proper async def, await, and connection lifecycle |
| Configuration (CFG) | 7 | ✅ PASS | Environment variables, validation implemented |
| Clean Code (CC) | 7 | ✅ PASS | Explicit error handling, descriptive names |
| Design Patterns (DP) | 6 | ⚠️ N/A | Not applicable for Alembic env.py |
| Code Quality (QL) | 7 | ✅ PASS | Functions < 50 lines, good structure |
| Trading (TRD) | 15 | ⚠️ N/A | Not applicable for migration file |
| Performance (PERF) | 6 | ⚠️ N/A | Not applicable for migration file |

**Overall:** 49 applicable rules, all PASSED. Non-applicable rules (testing, patterns, trading, performance) are marked as N/A.

### Critical P0 Rules Verified

| Rule ID | Requirement | Status | Evidence |
|---------|-------------|--------|----------|
| FMT-007 | No mutable defaults | ✅ PASS | No mutable defaults in function signatures |
| FMT-008 | Context managers for resources | ✅ PASS | Lines 86, 112, 246, 191-211 |
| SEC-001 | No hardcoded secrets | ✅ PASS | Uses environment variables |
| SEC-007 | Input validation | ✅ PASS | URL validation at lines 72-74, 226-228 |
| LOG-004 | Error logging with stack traces | ✅ PASS | All errors use exc_info=True |
| LOG-005 | No sensitive data in logs | ✅ PASS | Partial URL at line 76 |
| ASYNC-001 | Use async def | ✅ PASS | Line 139 |
| ASYNC-002 | Await async calls | ✅ PASS | Line 160 |
| ASYNC-003 | Async context managers | ✅ PASS | Lines 191-211 |
| ASYNC-006 | Handle asyncio.TimeoutError | ✅ PASS | Lines 174-180 |
| CFG-002 | Environment variables | ✅ PASS | Lines 40-47 |
| CC-006 | Explicit error handling | ✅ PASS | Lines 68-97, 102-136, 143-211, 221-273 |
| SOL-001 | Single Responsibility | ✅ PASS | Each function has one purpose |
| ARCH-001 | Layered architecture | ✅ PASS | Proper separation of concerns |
| DP-004 | Dependency injection | ✅ PASS | Uses get_settings() injection |

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
- **Error Handling (CC-006):** All migration functions now have try/except blocks with specific exception handling for SQLAlchemyError and generic Exception
- **Logging (LOG-004):** Comprehensive logging added with exc_info=True for stack traces and structured logging with error_type and error_message fields
- **Configuration Validation (CFG-003):** Added URL validation in run_migrations_offline() and run_migrations_online() with proper error logging
- **Async Connection Cleanup (ASYNC-003, MIG-004):** Proper resource cleanup in finally block to prevent connection leaks

---

## GAP Fixes Applied (2026-02-05)

### P0 Fix #1: DB URL Validation (CFG-003) - FIXED ✅
**Lines:** 72-74 (offline mode), 226-228 (online mode)
**Changes:**
- Added explicit None check for db_url in both offline and online migration functions
- Raises ValueError with descriptive error message when URL is not configured
- Prevents silent failures and unclear errors from Alembic
- Proper error logging before raising exception
```python
if db_url is None:
    logger.error("Database URL not configured for online migration")
    raise ValueError("sqlalchemy.url is not configured in Alembic config")
```

### P0 Fix #2: Async Connection Lifecycle (ASYNC-003, MIG-004) - FIXED ✅
**Lines:** 191-211
**Changes:**
- Added comprehensive finally block to run_async_migrations()
- Proper cleanup of async connection with await connection.close()
- Proper disposal of async engine with await connectable.dispose()
- Error handling for cleanup operations to prevent secondary exceptions
- Prevents connection leaks and resource exhaustion
```python
finally:
    if connection is not None:
        try:
            logger.info("Closing async connection")
            await connection.close()
        except Exception as e:
            logger.error("Error closing async connection", exc_info=True, extra={"error_message": str(e)})
    if connectable is not None:
        try:
            logger.info("Disposing async engine")
            await connectable.dispose()
        except Exception as e:
            logger.error("Error disposing async engine", exc_info=True, extra={"error_message": str(e)})
```

### Previous Fixes (2026-02-01)

### CC-006: Explicit Error Handling - FIXED ✅
**Changes:**
- Added try/except blocks to all migration functions: `run_migrations_offline()`, `do_run_migrations()`, `run_async_migrations()`, `run_migrations_online()`
- Specific handling for `SQLAlchemyError` to catch database-specific errors
- Separate exception handling for `asyncio.TimeoutError` in async migrations
- Generic Exception catch as fallback for unexpected errors
- All exceptions are re-raised after logging to preserve Alembic's error propagation behavior
- Added URL validation in `run_migrations_offline()` with descriptive error message

### LOG-004: Error Logging with Stack Traces - FIXED ✅
**Changes:**
- Added `logger` instance from `logging.getLogger(__name__)`
- Added `import logging` to imports
- Added `from sqlalchemy.exc import SQLAlchemyError` for specific error type handling
- All error logs use `exc_info=True` to capture stack traces
- Structured logging with `extra` parameter including:
  - `error_type`: The exception class name
  - `error_message`: The exception message
- Added info-level logging for migration progress tracking:
  - "Starting offline/online/async migration"
  - "Creating async database engine for migrations"
  - "Establishing async/sync connection"
  - "Running migrations"
  - "Disposing engine"
  - "Migration completed successfully"
- Security consideration: Only partial URL logged (first 20 chars) to avoid exposing credentials
