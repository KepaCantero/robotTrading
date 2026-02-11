# position_repository.py

## Purpose
Position Repository Interface - Domain layer contract for position data access. Defines the contract for position CRUD operations. Implementations are provided by the infrastructure layer.

---

## Type Definitions / Data Classes

### PositionRepository(ABC)
```python
class PositionRepository(ABC):
    """
    Position repository interface.

    Defines the contract for position data access.
    """
```

**Pattern:** Repository Pattern (DDD)
**Purpose:** Abstract data access from domain logic
**Concurrency:** Async methods (async/await)
**Implementations:** In infrastructure layer
**Scope:** Portfolio-scoped (all methods require portfolio_id)

---

## Function Signatures (Contracts)

### `PositionRepository.save(portfolio_id: str, position: Position) -> None`
**Pre:** portfolio_id is string; position is valid entity
**Post:** Position persisted to storage
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** Stores position (implementation-specific)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Must handle new positions (create)
- Must handle existing positions (update)
- Positions belong to portfolios (portfolio_id required)
- Implementations choose storage mechanism

### `PositionRepository.find_by_symbol(portfolio_id: str, symbol: str) -> Optional[Position]`
**Pre:** portfolio_id is string; symbol is string
**Post:** Returns Position entity or None if not found
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Returns None if (portfolio_id, symbol) combination not found
- Positions are uniquely identified by (portfolio_id, symbol)
- Symbol is typically a ticker (e.g., "AAPL", "MSFT")

### `PositionRepository.find_by_portfolio(portfolio_id: str) -> List[Position]`
**Pre:** portfolio_id is string
**Post:** Returns list of all positions in that portfolio
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Return empty list if no positions found
- No pagination (returns all)
- Should include all active positions for the portfolio

### `PositionRepository.delete(portfolio_id: str, symbol: str) -> None`
**Pre:** portfolio_id is string; symbol is string
**Post:** Position removed from storage
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** Removes position from storage
**Async:** Yes (awaitable)

**Implementation Notes:**
- No-op if (portfolio_id, symbol) not found (or raises, implementation-defined)
- Should be idempotent (safe to call multiple times)
- Used when closing positions or rebalancing

---

## Acceptance Criteria
- [ ] **AC-001:** PositionRepository is an abstract base class (ABC)
- [ ] **AC-002:** All methods have @abstractmethod decorator
- [ ] **AC-003:** All methods are async (def async)
- [ ] **AC-004:** save() accepts portfolio_id and Position
- [ ] **AC-005:** find_by_symbol() accepts portfolio_id and symbol
- [ ] **AC-006:** find_by_symbol() returns Optional[Position]
- [ ] **AC-007:** find_by_portfolio() returns List[Position]
- [ ] **AC-008:** delete() accepts portfolio_id and symbol
- [ ] **AC-009:** All methods have complete type hints

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Position Repository Interface):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Repository pattern | DDD | Abstract repository in domain | ✅ OK - PositionRepository(ABC) |
| Interface contract | DDD | All methods abstract | ✅ OK - @abstractmethod |
| Async operations | BASE_RULES.md (ASYNC-001) | async def methods | ✅ OK - All async |
| Dependency inversion | SOLID | Domain defines abstraction | ✅ OK - Domain layer |
| Infrastructure separation | Clean Architecture | Implementations in infrastructure | ✅ OK - Docstring |
| CRUD operations | Repository pattern | save, find, delete | ✅ OK - Complete CRUD |
| Portfolio-scoped | Domain | All methods require portfolio_id | ✅ OK - Scoped access |
| Symbol uniqueness | Domain | (portfolio_id, symbol) unique | ✅ OK - Composite key |
| Delete operation | Repository pattern | delete() method | ✅ OK - Supports deletion |
| No business logic | Clean code | Only data access | ✅ OK - Docstring |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |

**NOTE:** This is an INTERFACE - implementations in infrastructure layer must follow this contract.

---

## Dependencies
- **External:** None (std lib only: abc, typing)
- **Internal:**
  - `app.domain.entities.portfolio.Position`

---

## Required Tests
- **test_position_repository_interface.py:**
  - `test_position_repository_is_abc()` - Cannot instantiate ABC
  - `test_save_is_abstract()` - Has @abstractmethod
  - `test_save_is_async()` - Method is async
  - `test_find_by_symbol_is_abstract()` - Has @abstractmethod
  - `test_find_by_symbol_is_async()` - Method is async
  - `test_find_by_portfolio_is_abstract()` - Has @abstractmethod
  - `test_find_by_portfolio_is_async()` - Method is async
  - `test_delete_is_abstract()` - Has @abstractmethod
  - `test_delete_is_async()` - Method is async

**Implementation Tests (for concrete implementations):**
  - `test_save_persists_position()` - Stores position
  - `test_save_updates_existing()` - Updates if (portfolio_id, symbol) exists
  - `test_find_by_symbol_returns_position()` - Returns entity when found
  - `test_find_by_symbol_returns_none()` - Returns None when not found
  - `test_find_by_portfolio_returns_all()` - Returns all positions for portfolio
  - `test_find_by_portfolio_returns_empty()` - Returns empty list if no positions
  - `test_delete_removes_position()` - Deletes position
  - `test_delete_is_idempotent()` - Safe to call multiple times
  - `test_portfolio_scoping()` - Positions from different portfolios are separate

---

## Notes
- **Critical:** This is an INTERFACE - domain defines contract
- **Repository Pattern (DDD):**
  - Domain layer defines repository interfaces
  - Infrastructure layer provides implementations
  - Application layer depends on abstraction (interface)
  - Enables testing with mock implementations
- **Async Design:**
  - All methods are async (async def)
  - Optimized for I/O-bound operations
  - Must be awaited when called
  - Implementations should use async I/O (aiofiles, asyncpg, etc.)
- **Portfolio-Scoped Design:**
  - All methods require portfolio_id parameter
  - Positions belong to portfolios (aggregate root pattern)
  - Positions are uniquely identified by (portfolio_id, symbol)
  - This ensures data isolation between portfolios
- **Interface Contract:**
  - Implementations MUST provide all 4 methods
  - Methods MUST be async
  - Methods MUST follow specified signatures
  - Return types MUST match interface
- **Clean Architecture:**
  - Domain knows nothing about storage implementation
  - Infrastructure imports domain (not vice versa)
  - Application depends on domain interface
- **Position Lifecycle:**
  - Positions are created when orders are filled
  - Positions are updated when more orders for same symbol are filled
  - Positions are deleted when closed (position goes to 0)
- **Aggregate Root Pattern:**
  - Portfolio is the aggregate root
  - Positions are children of Portfolio
  - Access to positions always goes through portfolio_id
  - This maintains consistency and encapsulation
- **Comparison with Other Repositories:**
  - 4 methods (vs 5 for Portfolio, 3 for Order, 8 for Backtest)
  - Async by design (like PortfolioRepository, OrderRepository)
  - Portfolio-scoped (like OrderRepository)
  - Has delete method (unlike OrderRepository)
  - Symbol-based lookup (unique among repositories)
- **Production Rule:** Always depend on this interface, never concrete implementations

---

**File Reference:** `app/domain/repositories/position_repository.py`
**Last Audited:** 2026-02-01
