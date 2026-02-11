# portfolio_repository.py

## Purpose
Portfolio Repository Interface - Domain layer contract for portfolio data access. Defines the contract for portfolio CRUD operations. Implementations are provided by the infrastructure layer.

---

## Type Definitions / Data Classes

### PortfolioRepository(ABC)
```python
class PortfolioRepository(ABC):
    """
    Portfolio repository interface.

    This abstract class defines the contract for portfolio data access.
    Implementations must NOT contain business logic - only data access.
    """
```

**Pattern:** Repository Pattern (DDD)
**Purpose:** Abstract data access from domain logic
**Concurrency:** Async methods (async/await)
**Implementations:** In infrastructure layer

---

## Function Signatures (Contracts)

### `PortfolioRepository.save(portfolio: Portfolio) -> None`
**Pre:** portfolio is valid entity
**Post:** Portfolio persisted to storage
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** Stores portfolio (implementation-specific)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Must handle new portfolios (create)
- Must handle existing portfolios (update)
- Implementations choose storage mechanism

### `PortfolioRepository.find_by_id(portfolio_id: str) -> Optional[Portfolio]`
**Pre:** portfolio_id is string
**Post:** Returns Portfolio entity or None if not found
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Returns None if portfolio_id not found
- Implementations scan all storage locations

### `PortfolioRepository.find_all() -> List[Portfolio]`
**Pre:** None
**Post:** Returns list of all portfolios
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Return empty list if no portfolios
- No pagination (returns all)

### `PortfolioRepository.delete(portfolio_id: str) -> None`
**Pre:** portfolio_id is string
**Post:** Portfolio removed from storage
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** Removes portfolio from storage
**Async:** Yes (awaitable)

**Implementation Notes:**
- No-op if portfolio_id not found (or raises, implementation-defined)
- Should be idempotent (safe to call multiple times)

### `PortfolioRepository.exists(portfolio_id: str) -> bool`
**Pre:** portfolio_id is string
**Post:** Returns True if portfolio exists
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Returns True if portfolio_id exists in storage
- Returns False otherwise
- More efficient than `find_by_id()` if only checking existence

---

## Acceptance Criteria
- [ ] **AC-001:** PortfolioRepository is an abstract base class (ABC)
- [ ] **AC-002:** All methods have @abstractmethod decorator
- [ ] **AC-003:** All methods are async (def async)
- [ ] **AC-004:** save() accepts Portfolio entity
- [ ] **AC-005:** find_by_id() returns Optional[Portfolio]
- [ ] **AC-006:** find_all() returns List[Portfolio]
- [ ] **AC-007:** delete() accepts portfolio_id
- [ ] **AC-008:** exists() returns bool
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

### Reglas ESPECÍFICAS de este archivo (Portfolio Repository Interface):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Repository pattern | DDD | Abstract repository in domain | ✅ OK - PortfolioRepository(ABC) |
| Interface contract | DDD | All methods abstract | ✅ OK - @abstractmethod |
| Async operations | BASE_RULES.md (ASYNC-001) | async def methods | ✅ OK - All async |
| Dependency inversion | SOLID | Domain defines abstraction | ✅ OK - Domain layer |
| Infrastructure separation | Clean Architecture | Implementations in infrastructure | ✅ OK - Docstring |
| CRUD operations | Repository pattern | save, find, delete | ✅ OK - Complete CRUD |
| Exists check | Repository pattern | exists() method | ✅ OK - Efficient check |
| No business logic | Clean code | Only data access | ✅ OK - Docstring |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This is an INTERFACE - implementations in infrastructure layer must follow this contract.

---

## Dependencies
- **External:** None (std lib only: abc, typing)
- **Internal:**
  - `app.domain.entities.portfolio.Portfolio`

---

## Required Tests
- **test_portfolio_repository_interface.py:**
  - `test_portfolio_repository_is_abc()` - Cannot instantiate ABC
  - `test_save_is_abstract()` - Has @abstractmethod
  - `test_save_is_async()` - Method is async
  - `test_find_by_id_is_abstract()` - Has @abstractmethod
  - `test_find_by_id_is_async()` - Method is async
  - `test_find_all_is_abstract()` - Has @abstractmethod
  - `test_find_all_is_async()` - Method is async
  - `test_delete_is_abstract()` - Has @abstractmethod
  - `test_delete_is_async()` - Method is async
  - `test_exists_is_abstract()` - Has @abstractmethod
  - `test_exists_is_async()` - Method is async

**Implementation Tests (for concrete implementations):**
  - `test_save_persists_portfolio()` - Stores portfolio
  - `test_save_updates_existing()` - Updates if exists
  - `test_find_by_id_returns_portfolio()` - Returns entity when found
  - `test_find_by_id_returns_none()` - Returns None when not found
  - `test_find_all_returns_all()` - Returns all portfolios
  - `test_delete_removes_portfolio()` - Deletes portfolio
  - `test_delete_is_idempotent()` - Safe to call multiple times
  - `test_exists_returns_true()` - Returns True when found
  - `test_exists_returns_false()` - Returns False when not found

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
- **Interface Contract:**
  - Implementations MUST provide all 5 methods
  - Methods MUST be async
  - Methods MUST follow specified signatures
  - Return types MUST match interface
- **Clean Architecture:**
  - Domain knows nothing about storage implementation
  - Infrastructure imports domain (not vice versa)
  - Application depends on domain interface
- **Dependency Inversion Principle:**
  - High-level modules (application) depend on abstractions
  - Low-level modules (infrastructure) implement abstractions
  - Both depend on the interface, not concretions
- **Comparison with BacktestRepository:**
  - Simpler interface (5 methods vs 8)
  - No pagination (find_all returns all)
  - No filtering methods
  - No status/type filtering
  - Async by design (BacktestRepository is sync)
- **Production Rule:** Always depend on this interface, never concrete implementations

---

**File Reference:** `app/domain/repositories/portfolio_repository.py`
**Last Audited:** 2026-02-01
