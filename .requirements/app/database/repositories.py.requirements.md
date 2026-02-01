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

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Repository Pattern | BASE_RULES.md | Generic base class | ✅ OK |
| Error Handling | BASE_RULES.md | Catch SQL exceptions | ✅ OK |
| Transaction Management | CRITICAL_RULES.md | Rollback on error | ✅ OK |
| Type Safety | BASE_RULES.md | Generic type hints | ✅ OK |
| Session Management | CRITICAL_RULES.md | Use session parameter | ✅ OK |
| Validation | BASE_RULES.md | Input validation | ✅ OK |
| Pagination | BASE_RULES.md | limit/offset support | ✅ OK |

---

## Dependencies
- **External:** uuid, datetime, decimal, typing, sqlalchemy
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
