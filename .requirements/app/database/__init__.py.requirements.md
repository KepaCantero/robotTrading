# Requirements: app/database/__init__.py

## Source File Analysis
- **File Path**: `app/database/__init__.py`
- **Lines of Code**: 390
- **Status**: Analysis Complete

## Purpose
Database configuration and session management module. Provides:
- DatabaseManager class for engine lifecycle management
- Synchronous and asynchronous database session handling
- FastAPI dependency injection functions
- Database health check functions
- Context managers and decorators for transaction management

Supports both SQLite and PostgreSQL with appropriate pooling strategies.

## Dependencies
### Internal
- `app.core.environment_config.get_config` - Configuration retrieval
- `app.core.exceptions.raise_database_error` - Custom error raising

### External
- `contextlib` - Context manager utilities
- `logging` - Logging
- `sqlalchemy` - ORM and database connectivity
  - `MetaData`, `create_engine`, `event` - Core SQLAlchemy
  - `AsyncSession`, `async_sessionmaker`, `create_async_engine` - Async support
  - `declarative_base` - Model base class
  - `Session`, `sessionmaker` - Session management
  - `QueuePool` - Connection pooling
- `typing` - Type hints (`AsyncGenerator`, `Optional`)

## Classes/Functions

### class DatabaseManager
**Purpose**: Manages database connections and session factories
**Methods**:
- `__init__(self) -> None`: Initialize with config
- `initialize_sync_engine(self) -> None`: Setup synchronous engine with pooling
- `initialize_async_engine(self) -> None`: Setup asynchronous engine
- `_convert_to_async_url(self, sync_url: str) -> str`: Convert postgresql:// to postgresql+asyncpg://
- `_add_connection_listeners(self) -> None`: Setup event listeners for connections
- `create_tables(self) -> None`: Create all tables using Base metadata
- `drop_tables(self) -> None`: Drop all tables
- `get_sync_session(self) -> Session`: Return new sync session
- `get_async_session(self) -> AsyncSession`: Return new async session
- `close_connections(self) -> None`: Dispose all engines

### Functions
- `get_sync_db() -> Session`: FastAPI dependency for sync sessions (context manager)
- `get_async_db() -> AsyncGenerator[AsyncSession, None]`: FastAPI dependency for async sessions
- `initialize_database() -> None`: Initialize sync and async engines, create tables
- `initialize_database_async() -> None`: Initialize async engine only
- `check_database_health() -> bool`: Test sync database connection
- `check_database_health_async() -> bool`: Test async database connection
- `get_database_url() -> str`: Return connection string
- `get_database_config() -> dict`: Return config as dictionary

### class DatabaseSession
**Purpose**: Context manager for database sessions
**Methods**:
- `__init__(self, async_mode: bool = False) -> None`: Initialize with mode flag
- `__enter__(self) -> Session`: Sync context entry
- `__exit__(self, exc_type, exc_val, exc_tb) -> None`: Sync context exit with commit/rollback
- `__aenter__(self) -> AsyncSession`: Async context entry
- `__aexit__(self, exc_type, exc_val, exc_tb) -> None`: Async context exit

### Decorators
- `database_transaction(func)`: Wrapper for sync database transactions
- `async_database_transaction(func)`: Wrapper for async database transactions

## Business Logic

### Engine Initialization
- Detects SQLite vs PostgreSQL from connection string
- SQLite: No pooling, `check_same_thread=False`
- PostgreSQL: QueuePool with configurable size, timeout, pre_ping
- Sets timezone to UTC for PostgreSQL
- Configures statement_timeout and lock_timeout

### Session Management
- Sessions are NOT autocommit, NOT autoflush
- expire_on_commit=False to allow access to objects after transaction
- Context managers ensure proper cleanup

### Connection Pooling
- Pool size from config (`db_pool_size`)
- Max overflow from config (`db_max_overflow`)
- Pool timeout from config (`db_pool_timeout`)
- Pre-ping verifies connections before use

## Data Models
No data models defined in this file. Uses SQLAlchemy ORM.

## API Contracts

### FastAPI Dependencies
```python
# In route handlers
@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_sync_db)):
    ...

# Async routes
@router.get("/portfolio")
async def get_portfolio(db: AsyncSession = Depends(get_async_db)):
    ...
```

## Error Handling

### Current Implementation
- Uses custom `raise_database_error()` for database failures
- Logs errors before re-raising
- Context managers handle rollback on exception

### **GAPS FOUND**

#### GAP-001: Missing SQLAlchemy Exception Imports (ERR-001, P0)
**Location:** Lines 178-179, 190-191, 219-220, 262-264, 277-279, 293-295, 308-310
**Issue:** SQLAlchemy exceptions are used but NOT imported:
```python
# These are used but NOT imported:
IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError
```
**Impact:** Code will crash with NameError when these exceptions are raised
**Fix Required:** Add imports at top of file:
```python
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    DatabaseError,
    DataError,
    ProgrammingError,
)
```

#### GAP-002: Raw SQL Without text() (SEC-007, P0)
**Location:** Lines 289, 304
**Issue:** Raw SQL strings passed to `session.execute()` without `text()` wrapper
```python
# Line 289 - WRONG:
session.execute("SELECT 1")

# Line 304 - WRONG:
await session.execute("SELECT 1")
```
**Impact:** SQLAlchemy 2.0+ requires `text()` for raw SQL. This will fail.
**Fix Required:**
```python
from sqlalchemy import text

# Line 289 - CORRECT:
session.execute(text("SELECT 1"))

# Line 304 - CORRECT:
await session.execute(text("SELECT 1"))
```

## Performance Considerations
- Connection pooling reduces connection overhead
- Pre-ping adds slight overhead but detects stale connections
- Async engine for I/O bound operations
- Context managers ensure proper resource cleanup

## Testing Strategy
Tests should verify:
1. Engine initialization for both SQLite and PostgreSQL
2. Session creation and cleanup
3. Transaction commit/rollback behavior
4. Health check queries
5. Context manager behavior
6. Async session handling

## Critical Rules (from BASE_RULES.md)

### Applicable Rules Status

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| **FMT-002** | Import organization | ✅ PASS | Imports properly organized |
| **TYP-001** | Type coverage | ⚠️ PARTIAL | Most functions typed, decorators missing some |
| **SOL-001** | Single Responsibility | ✅ PASS | DatabaseManager has single responsibility |
| **ERR-001** | Error handling | ❌ GAP | Missing exception imports (P0) |
| **SEC-007** | Input validation | ❌ GAP | Raw SQL without text() (P0) |
| **ARCH-004** | Small functions | ✅ PASS | Functions are focused and manageable |
| **LOG-004** | Error logging | ✅ PASS | All error paths log exceptions |
| **FMT-008** | Context managers | ✅ PASS | Proper context managers used |

### Gaps Fixed

#### ✅ FIXED: GAP-001 - Missing Exception Imports (P0)
**Fix Applied:** Added imports at line 11-17:
```python
from sqlalchemy.exc import (
    DataError,
    DatabaseError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
```

#### ✅ FIXED: GAP-002 - Raw SQL Without text() (P0)
**Fix Applied:**
1. Added `text` to sqlalchemy imports (line 10)
2. Wrapped raw SQL with `text()` on line 300: `session.execute(text("SELECT 1"))`
3. Wrapped raw SQL with `text()` on line 315: `await session.execute(text("SELECT 1"))`

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T12:15:00Z |
| **Audit Status** | **PASSED** |

### Audit Notes
- All critical gaps have been fixed
- Missing SQLAlchemy exception imports added
- Raw SQL queries properly wrapped with text()
- Syntax check passed
- File now complies with BASE_RULES.md

---
*Audited on 2026-02-07T12:10:00Z*
