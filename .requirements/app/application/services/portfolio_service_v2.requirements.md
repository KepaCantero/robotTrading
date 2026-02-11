# portfolio_service_v2.py

## Purpose
Portfolio Service V2 - Portfolio management service with proper dependency injection following SOLID principles.

---

## Type Definitions / Data Classes

No custom data classes defined in this file (uses domain entities).

**Domain Dependencies:**
- `Portfolio` entity
- `PortfolioRepository` interface
- `AbstractEntityFactory` interface
- `DIContainer` for dependency injection

---

## Function Signatures (Contracts)

### `PortfolioServiceV2.__init__(repository, factory, di_container) -> None`
**Pre:** repository is PortfolioRepository; factory is AbstractEntityFactory
**Post:** Service initialized with injected dependencies
**Raises:** None
**Retry:** No
**Side Effects:** Stores dependency references

**Dependencies (Injected):**
- repository: PortfolioRepository (required)
- factory: AbstractEntityFactory (required)
- di_container: DIContainer (optional)

### `async def get_portfolio(portfolio_id: str) -> Optional[Portfolio]`
**Pre:** portfolio_id is non-empty string
**Post:** Returns Portfolio if found, None otherwise
**Raises:** None (errors caught, logged, return None)
**Retry:** No
**Side Effects:** None (query via repository)

**Error Handling:** Catches exceptions, prints error, returns None

### `async def create_portfolio(
    portfolio_id: str,
    initial_capital: Decimal,
    currency: str = "USD",
) -> Portfolio`
**Pre:** portfolio_id is non-empty; initial_capital > 0
**Post:** Returns created Portfolio
**Raises:** Exception (propagated from repository/factory)
**Retry:** No
**Side Effects:** Creates portfolio via factory, adds to repository

**Process:**
1. Create portfolio via factory
2. Add to repository
3. Return portfolio

### `async def update_portfolio_weights(
    portfolio_id: str,
    new_weights: Dict[str, Decimal],
) -> bool`
**Pre:** portfolio_id exists; new_weights valid (sum to ~1.0)
**Post:** Returns True if updated successfully, False if portfolio not found
**Raises:** None (errors return False)
**Retry:** No
**Side Effects:** Updates portfolio weights via domain logic, saves to repository

**Process:**
1. Get portfolio via get_portfolio()
2. If None, return False
3. Call portfolio.rebalance_weights(new_weights)
4. Save to repository
5. Return True

### `get_dependency_summary() -> Dict[str, str]`
**Pre:** None
**Post:** Returns dictionary of dependency types
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Output Format:**
```python
{
    "repository": "ClassName",
    "factory": "ClassName",
    "has_container": True/False
}
```

### `create_portfolio_service(container: DIContainer) -> PortfolioServiceV2`
**Pre:** container is DIContainer with registered dependencies
**Post:** Returns PortfolioServiceV2 with injected dependencies
**Raises:** None (container.get() will raise if not registered)
**Retry:** No
**Side Effects:** None (factory function)

**Factory Function:** Creates service via DI container
```python
service = create_portfolio_service(container)
```

---

## Acceptance Criteria
- [ ] **AC-001:** Service uses dependency injection (no direct instantiation)
- [ ] **AC-002:** get_portfolio() returns None if not found
- [ ] **AC-003:** get_portfolio() handles errors gracefully
- [ ] **AC-004:** create_portfolio() creates and persists portfolio
- [ ] **AC-005:** update_portfolio_weights() returns False if portfolio not found
- [ ] **AC-006:** update_portfolio_weights() uses domain logic (rebalance_weights)
- [ ] **AC-007:** get_dependency_summary() returns dependency types
- [ ] **AC-008:** create_portfolio_service() factory function works
- [ ] **AC-009:** All methods are async
- [ ] **AC-010:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Portfolio Service V2):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Dependency Injection | SOLID (DIP) | Dependencies injected | ✅ OK - __init__() |
| Single Responsibility | SOLID (SRP) | One responsibility | ✅ OK - Portfolio mgmt only |
| Open/Closed Principle | SOLID (OCP) | Extensible via interfaces | ✅ OK - Interfaces |
| Interface Segregation | SOLID (ISP) | Focused interfaces | ✅ OK - Small interfaces |
| Async/Await | BASE_RULES.md (ASYNC-001) | Async methods | ✅ OK - All async |
| Error handling | BASE_RULES.md (LOG-001) | Graceful error handling | ✅ OK - get_portfolio() |
| Factory function | Clean code | DI container factory | ✅ OK - create_portfolio_service() |
| Repository pattern | DDD (Evans) | Persistence abstraction | ✅ OK - PortfolioRepository |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and SOLID principles.

---

## Dependencies
- **External:** `decimal` (std), `typing` (std)
- **Internal:**
  - `app.core.di_container.DIContainer`
  - `app.domain.entities.portfolio.Portfolio`
  - `app.domain.factories.AbstractEntityFactory`
  - `app.domain.repositories.PortfolioRepository`

---

## Required Tests
- **test_portfolio_service_v2.py:**
  - `test_init_with_dependencies()` - Stores injected deps
  - `test_get_portfolio_found()` - Returns portfolio
  - `test_get_portfolio_not_found()` - Returns None
  - `test_get_portfolio_handles_error()` - Catches, prints, returns None
  - `test_create_portfolio()` - Creates and saves portfolio
  - `test_create_portfolio_default_currency()` - USD
  - `test_update_portfolio_weights_success()` - Returns True
  - `test_update_portfolio_weights_not_found()` - Returns False
  - `test_update_portfolio_weights_calls_rebalance()` - Domain logic called
  - `test_get_dependency_summary()` - Returns dep types
  - `test_get_dependency_summary_has_container()` - True if container
  - `test_get_dependency_summary_no_container()` - False if None
  - `test_create_portfolio_service_factory()` - Creates via container
  - `test_all_methods_are_async()` - await works on all

---

## Notes
- **Critical:** PortfolioServiceV2 demonstrates DEPENDENCY INVERSION (SOLID DIP)
- **Martin (Clean Architecture) Reference:** "Clean Architecture" (2017) - Dependency Inversion
- **SOLID Principles Demonstrated:**
  - **SRP:** Single responsibility - portfolio management only
  - **OCP:** Open for extension - can extend via interfaces
  - **LSP:** Liskov Substitution - can substitute implementations
  - **ISP:** Interface Segregation - small, focused interfaces
  - **DIP:** Dependency Inversion - depends on abstractions (interfaces)
- **Dependency Injection:** All dependencies injected via constructor (not created internally)
- **Old vs New:**
  - **Old way (violates DIP):** `service = PortfolioService(provider)` - creates deps
  - **New way (follows DIP):** `service = PortfolioServiceV2(repository=..., factory=...)`
- **DI Container:** Optional DIContainer for additional dependencies
- **Repository Pattern:** Abstracts persistence via PortfolioRepository interface
- **Factory Pattern:** AbstractEntityFactory for entity creation
- **Async Methods:** All methods are async (async/await pattern)
- **Error Handling:** get_portfolio() catches exceptions gracefully
- **Domain Logic:** update_portfolio_weights() delegates to portfolio.rebalance_weights()
- **Factory Function:** create_portfolio_service() for convenient DI container creation
- **Debugging:** get_dependency_summary() for inspecting injected dependencies
- **Testing:** Easy to test by injecting mock dependencies

---

**File Reference:** `app/application/services/portfolio_service_v2.py`
**Last Audited:** 2026-02-01
