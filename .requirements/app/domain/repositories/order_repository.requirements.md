# order_repository.py

## Purpose
Order Repository Interface - Domain layer contract for order data access. Defines the contract for order CRUD operations. Implementations are provided by the infrastructure layer.

---

## Type Definitions / Data Classes

### OrderRepository(ABC)
```python
class OrderRepository(ABC):
    """
    Order repository interface.

    Defines the contract for order data access.
    """
```

**Pattern:** Repository Pattern (DDD)
**Purpose:** Abstract data access from domain logic
**Concurrency:** Async methods (async/await)
**Implementations:** In infrastructure layer

---

## Function Signatures (Contracts)

### `OrderRepository.save(order: Order) -> None`
**Pre:** order is valid entity
**Post:** Order persisted to storage
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** Stores order (implementation-specific)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Must handle new orders (create)
- Must handle existing orders (update)
- Implementations choose storage mechanism

### `OrderRepository.find_by_id(order_id: str) -> Optional[Order]`
**Pre:** order_id is string
**Post:** Returns Order entity or None if not found
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Returns None if order_id not found
- Implementations scan all storage locations

### `OrderRepository.find_by_portfolio(portfolio_id: str) -> List[Order]`
**Pre:** portfolio_id is string
**Post:** Returns list of all orders for that portfolio
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)
**Async:** Yes (awaitable)

**Implementation Notes:**
- Return empty list if no orders found
- No pagination (returns all)
- Should be sorted by creation date (typically newest first)

---

## Acceptance Criteria
- [ ] **AC-001:** OrderRepository is an abstract base class (ABC)
- [ ] **AC-002:** All methods have @abstractmethod decorator
- [ ] **AC-003:** All methods are async (def async)
- [ ] **AC-004:** save() accepts Order entity
- [ ] **AC-005:** find_by_id() returns Optional[Order]
- [ ] **AC-006:** find_by_portfolio() returns List[Order]
- [ ] **AC-007:** All methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Order Repository Interface):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Repository pattern | DDD | Abstract repository in domain | ✅ OK - OrderRepository(ABC) |
| Interface contract | DDD | All methods abstract | ✅ OK - @abstractmethod |
| Async operations | BASE_RULES.md (ASYNC-001) | async def methods | ✅ OK - All async |
| Dependency inversion | SOLID | Domain defines abstraction | ✅ OK - Domain layer |
| Infrastructure separation | Clean Architecture | Implementations in infrastructure | ✅ OK - Docstring |
| CRUD operations | Repository pattern | save, find | ✅ OK - Basic CRUD |
| Portfolio filtering | Domain | find_by_portfolio method | ✅ OK - Portfolio-specific |
| No business logic | Clean code | Only data access | ✅ OK - Docstring |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |

**NOTE:** This is an INTERFACE - implementations in infrastructure layer must follow this contract.

---

## Dependencies
- **External:** None (std lib only: abc, typing)
- **Internal:**
  - `app.domain.entities.order.Order`

---

## Required Tests
- **test_order_repository_interface.py:**
  - `test_order_repository_is_abc()` - Cannot instantiate ABC
  - `test_save_is_abstract()` - Has @abstractmethod
  - `test_save_is_async()` - Method is async
  - `test_find_by_id_is_abstract()` - Has @abstractmethod
  - `test_find_by_id_is_async()` - Method is async
  - `test_find_by_portfolio_is_abstract()` - Has @abstractmethod
  - `test_find_by_portfolio_is_async()` - Method is async

**Implementation Tests (for concrete implementations):**
  - `test_save_persists_order()` - Stores order
  - `test_save_updates_existing()` - Updates if exists
  - `test_find_by_id_returns_order()` - Returns entity when found
  - `test_find_by_id_returns_none()` - Returns None when not found
  - `test_find_by_portfolio_returns_all()` - Returns all orders for portfolio
  - `test_find_by_portfolio_returns_empty()` - Returns empty list if no orders

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
  - Implementations MUST provide all 3 methods
  - Methods MUST be async
  - Methods MUST follow specified signatures
  - Return types MUST match interface
- **Clean Architecture:**
  - Domain knows nothing about storage implementation
  - Infrastructure imports domain (not vice versa)
  - Application depends on domain interface
- **Minimal Interface:**
  - Only 3 methods (simplest of all repositories)
  - No delete method (orders may be immutable for audit)
  - No find_all() (only portfolio-scoped access)
  - No pagination (portfolio orders typically limited)
- **Order Lifecycle:**
  - Orders are created by strategies/execution
  - Once created, orders may be immutable (append-only)
  - This is why no delete() method exists
- **Comparison with Other Repositories:**
  - Simplest interface (3 methods vs 5 for Portfolio, 8 for Backtest)
  - Async by design (like PortfolioRepository)
  - Portfolio-scoped access (orders belong to portfolios)
  - No global find_all() method
- **Production Rule:** Always depend on this interface, never concrete implementations

---

**File Reference:** `app/domain/repositories/order_repository.py`
**Last Audited:** 2026-02-01
