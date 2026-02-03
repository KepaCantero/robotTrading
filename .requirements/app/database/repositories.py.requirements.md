# repositories.py

## Purpose
Repository Pattern Implementation for Database Access - provides generic CRUD operations with SQLAlchemy, transaction management, and error handling (TASK-6).

---

## Type Definitions / Data Classes

### BaseRepository(Generic[T])
```python
class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""

    model_class: type[T]                      # REQUIRED - SQLAlchemy model
    session: Session                          # REQUIRED - SQLAlchemy session
```

**Generic Type:** T = Model class (User, Portfolio, Backtest, etc.)

### Specific Repositories
```python
class UserRepository(BaseRepository[User])   # User-specific queries
class PortfolioRepository(BaseRepository[Portfolio])  # Portfolio queries
class BacktestRepository(BaseRepository[Backtest])    # Backtest queries
class PositionRepository(BaseRepository[Position])    # Position queries
# ... (one per model)
```

---

## Function Signatures (Contracts)

### BaseRepository Methods

### `__init__(self, model_class: type[T], session: Session) -> None`
**Pre:** model_class is valid SQLAlchemy model, session active
**Post:** Repository initialized
**Raises:** No
**Retry:** No
**Side Effects:** None

### `create(self, **kwargs) -> T`
**Pre:** kwargs match model fields
**Post:** Record created and committed
**Raises:** DatabaseError with context if creation fails
**Retry:** No (rolls back on error)
**Side Effects:** Adds to session, commits, refreshes

**Flow:**
1. Create instance from kwargs
2. session.add()
3. session.commit()
4. session.refresh()
5. Return instance

**Error Handling:** Rolls back on IntegrityError, raises DatabaseError

### `get_by_id(self, id: uuid.UUID) -> Optional[T]`
**Pre:** id is valid UUID
**Post:** Returns instance or None
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

**Query:** SELECT * FROM {table} WHERE id = {id} LIMIT 1

### `get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]`
**Pre:** None
**Post:** Returns list of instances
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

**Pagination:**
- offset: Skip N records
- limit: Return max N records

### `update(self, id: uuid.UUID, **kwargs) -> Optional[T]`
**Pre:** id exists, kwargs are valid fields
**Post:** Record updated and committed
**Raises:** DatabaseError with context if update fails
**Retry:** No (rolls back on error)
**Side Effects:** Updates instance, commits, refreshes

**Flow:**
1. Get instance by ID
2. Update fields from kwargs (if hasattr)
3. session.commit()
4. session.refresh()
5. Return instance or None

### `delete(self, id: uuid.UUID) -> bool`
**Pre:** id is valid UUID
**Post:** Record deleted if exists
**Raises:** DatabaseError with context if delete fails
**Retry:** No (rolls back on error)
**Side Effects:** Deletes instance, commits

**Returns:** True if deleted, False if not found

### `count(self) -> int`
**Pre:** None
**Post:** Returns total record count
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

### UserRepository Specific Methods

### `get_by_username(self, username: str) -> Optional[User]`
**Pre:** username is non-empty string
**Post:** Returns User or None
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

**Query:** SELECT * FROM users WHERE username = {username} LIMIT 1

### PortfolioRepository Specific Methods

### `get_by_user_id(self, user_id: uuid.UUID) -> List[Portfolio]`
**Pre:** user_id is valid UUID
**Post:** Returns list of user's portfolios
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

### `get_by_name(self, user_id: uuid.UUID, name: str) -> Optional[Portfolio]`
**Pre:** user_id valid, name non-empty
**Post:** Returns portfolio or None
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

### BacktestRepository Specific Methods

### `get_by_user_id(self, user_id: uuid.UUID, limit: int = 20) -> List[Backtest]`
**Pre:** user_id valid, limit > 0
**Post:** Returns user's backtests (paginated)
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

### `get_by_strategy(self, strategy_name: str, limit: int = 20) -> List[Backtest]`
**Pre:** strategy_name non-empty, limit > 0
**Post:** Returns backtests for strategy
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

### `get_recent(self, days: int = 30, limit: int = 20) -> List[Backtest]`
**Pre:** days > 0, limit > 0
**Post:** Returns recent backtests
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

**Query:** Filter by created_at >= now - timedelta(days=days)

### TradeRepository Specific Methods

### `get_by_portfolio_id(self, portfolio_id: uuid.UUID) -> List[Trade]`
**Pre:** portfolio_id valid
**Post:** Returns portfolio's trades
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

### `get_by_symbol(self, symbol: str, portfolio_id: Optional[uuid.UUID] = None) -> List[Trade]`
**Pre:** symbol non-empty
**Post:** Returns trades for symbol
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

### `get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Trade]`
**Pre:** start_date < end_date
**Post:** Returns trades in range
**Raises:** DatabaseError with context if query fails
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] BaseRepository is generic (supports any model)
- [ ] All CRUD operations have error handling
- [ ] Sessions rollback on errors
- [ ] DatabaseError raised with context (operation, table)
- [ ] create() returns refreshed instance
- [ ] update() only updates existing fields
- [ ] delete() returns False if not found
- [ ] Specific repositories have domain-specific queries
- [ ] Pagination supported (limit, offset)
- [ ] All methods handle SQLAlchemy exceptions

---


## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. All critical rules passed. Structured logging and modern type hints implemented. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Status | Lines |
|------|--------|-------------|--------|-------|
| Repository Pattern | BASE_RULES.md | Generic base class | ✅ PASS | 46-223 |
| Error Handling | BASE_RULES.md | Catch SQL exceptions | ✅ PASS | 66-77, 90-101, 120-130, 155-167 |
| Transaction Management | CRITICAL_RULES.md | Rollback on error | ✅ PASS | 67, 156, 189, 350, 554, 773 |
| Type Safety | BASE_RULES.md | Generic type hints | ✅ PASS | 42, 46, 79, 103, 132, etc. |
| Session Management | CRITICAL_RULES.md | Use session parameter | ✅ PASS | 49 (DI via constructor) |
| Validation | BASE_RULES.md | Input validation | ✅ PASS | 136-142 (exists check) |
| Pagination | BASE_RULES.md | limit/offset support | ✅ PASS | 103-130 (get_all) |

### BASE_RULES Compliance Details

| Rule ID | Category | Rule | Status | Evidence |
|---------|----------|------|--------|----------|
| TYP-001 | Type Hints | 100% type coverage | ✅ PASS | All methods have type hints |
| TYP-002 | Type Hints | Modern `T \| None` syntax | ✅ FIXED | Lines 79, 103, 132, etc. |
| TYP-003 | Type Hints | No Any without justification | ✅ PASS | Only `dict[str, Any]` on line 657 justified |
| LOG-001 | Logging | Structured logging (structlog) | ✅ FIXED | Line 43: `get_logger(__name__)` |
| LOG-002 | Logging | Context in logs | ✅ PASS | All logs include model, id, error context |
| LOG-003 | Logging | Appropriate levels | ✅ PASS | info/debug/error used correctly |
| LOG-004 | Logging | Error logging with details | ✅ PASS | All exceptions logged with context |
| CC-006 | Clean Code | Explicit error handling | ✅ PASS | All DB errors converted to DatabaseError |
| DP-001 | Patterns | Repository pattern | ✅ PASS | Generic BaseRepository implementation |
| DP-004 | Patterns | Dependency injection | ✅ PASS | Session injected via constructor |
| CC-002 | Clean Code | DRY | ✅ PASS | Generic base reduces duplication |
| SOL-001 | SOLID | Single Responsibility | ✅ PASS | Each repository handles one model |
| ARCH-001 | Architecture | Layered architecture | ✅ PASS | Infrastructure layer (DB access) |

---

## Fix Summary

### P1 Fixes Applied (February 2026)

| Fix ID | Description | Priority | Lines Affected |
|--------|-------------|----------|----------------|
| LOG-FIX-001 | Added structured logging with structlog | P1 | 43, 60-64, 68-72, 83-88, etc. (all methods) |
| TYP-FIX-001 | Modernized type hints to `T \| None` syntax | P1 | 79, 103, 132, 228, 248, 266, etc. (all return types) |

### Detailed Changes

#### 1. Structured Logging (P1 - LOG-001)
**Before:** No structured logging
**After:** Added `structlog` throughout all repository methods

```python
# Line 43: Logger initialization
logger = get_logger(__name__)

# Example: create() method - Lines 60-64
logger.info(
    "created_record",
    model=self.model_class.__name__,
    id=str(instance.id),
)

# Example: get_by_id() method - Lines 83-88
logger.debug(
    "queried_by_id",
    model=self.model_class.__name__,
    id=str(id),
    found=result is not None,
)

# Example: Error logging - Lines 68-72
logger.error(
    "create_failed",
    model=self.model_class.__name__,
    error=str(e),
)
```

**Benefits:**
- All database operations logged with structured context
- Easy debugging and monitoring
- Consistent log format across all repositories

#### 2. Modern Type Hints (P1 - TYP-002)
**Before:** `Optional[T]`, `List[T]`
**After:** `T \| None`, `list[T]`

```python
# Line 79: get_by_id return type
def get_by_id(self, id: uuid.UUID) -> T | None:

# Line 103: get_all return type
def get_all(self, limit: int | None = None, offset: int | None = None) -> list[T]:

# Line 132: update return type
def update(self, id: uuid.UUID, **kwargs) -> T | None:

# Applied to all repository methods
```

**Benefits:**
- Modern Python 3.10+ syntax
- More concise and readable
- Consistent with current Python best practices

---

## Dependencies
- **External:** uuid, datetime, decimal, typing, sqlalchemy, structlog
- **Internal:**
  - app.core.exceptions.raise_database_error
  - app.database.models (User, Portfolio, Backtest, Trade, Position, etc.)

---

## Required Tests
- **test_repositories.py:**
  - Test BaseRepository.create() with valid data
  - Test BaseRepository.create() rollback on IntegrityError
  - Test BaseRepository.get_by_id() returns instance
  - Test BaseRepository.get_by_id() returns None for missing
  - Test BaseRepository.get_all() with pagination
  - Test BaseRepository.update() updates fields
  - Test BaseRepository.update() returns None for missing
  - Test BaseRepository.delete() deletes and returns True
  - Test BaseRepository.delete() returns False for missing
  - Test BaseRepository.count() returns count
  - Test UserRepository.get_by_username()
  - Test PortfolioRepository.get_by_user_id()
  - Test PortfolioRepository.get_by_name()
  - Test BacktestRepository.get_by_strategy()
  - Test BacktestRepository.get_recent()
  - Test TradeRepository.get_by_portfolio_id()
  - Test TradeRepository.get_by_symbol()
  - Test TradeRepository.get_by_date_range()
  - Test all methods raise DatabaseError on SQL errors

---

## Notes
- CRITICAL: This is data access layer (Repository Pattern)
- Generic base class reduces code duplication
- All methods handle SQLAlchemy exceptions
- Transactions rollback on errors
- DatabaseError includes operation and table context
- Specific repositories have domain-specific queries
- Session injected (not created in repository)
