# portfolio_service_v2.py

## Purpose
Portfolio management service demonstrating proper dependency injection following SOLID principles. Manages portfolio CRUD operations using injected repository and factory dependencies rather than creating them internally.

---

## Type Definitions / Data Classes

### Portfolio (imported from app.domain.entities.portfolio)
```python
class Portfolio:
    portfolio_id: str  # REQUIRED - Unique portfolio identifier
    initial_capital: Decimal  # REQUIRED - Initial capital amount
    currency: str  # REQUIRED - Currency code (default: "USD")
    # Additional portfolio attributes managed by entity
```

**Validation Rules:**
- `portfolio_id` must be non-empty string
- `initial_capital` must be positive Decimal
- `currency` must be valid ISO 4217 code

---

## Function Signatures (Contracts)

### `__init__(repository: PortfolioRepository, factory: AbstractEntityFactory, di_container: Optional[DIContainer] = None) -> None`
**Pre:** `repository` and `factory` must be non-null instances
**Post:** Service initialized with injected dependencies
**Raises:** No explicit validation (dependency injection framework handles)
**Retry:** No
**Side Effects:** Stores injected dependencies as private attributes

### `get_portfolio(portfolio_id: str) -> Optional[Portfolio]`
**Pre:** `portfolio_id` must be non-empty string
**Post:** Returns Portfolio if found, None otherwise
**Raises:** No exceptions (catches and logs Exception)
**Retry:** No
**Side Effects:** Logs errors, no state changes

### `create_portfolio(portfolio_id: str, initial_capital: Decimal, currency: str = "USD") -> Portfolio`
**Pre:** `portfolio_id` non-empty, `initial_capital` positive
**Post:** Returns created Portfolio persisted to repository
**Raises:** No explicit validation (delegated to factory/repository)
**Retry:** No
**Side Effects:** Creates Portfolio via factory, persists to repository

### `update_portfolio_weights(portfolio_id: str, new_weights: Dict[str, Decimal]) -> bool`
**Pre:** `portfolio_id` non-empty, `new_weights` non-empty dict
**Post:** Returns True if updated successfully, False if portfolio not found
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** Updates portfolio weights via domain logic, persists to repository

### `get_dependency_summary() -> Dict[str, str]`
**Pre:** None (no parameters)
**Post:** Returns dictionary with dependency type names
**Raises:** No exceptions
**Retry:** No
**Side Effects:** No state changes (debugging utility)

---

## Acceptance Criteria
- [ ] All dependencies are injected via constructor (DIP compliance)
- [ ] No direct instantiation of dependencies in service
- [ ] Repository is used for all portfolio persistence operations
- [ ] Factory is used for portfolio creation
- [ ] Errors in get_portfolio are caught and logged without raising
- [ ] get_portfolio returns None for non-existent portfolios
- [ ] create_portfolio uses factory to create portfolio entity
- [ ] create_portfolio persists portfolio to repository
- [ ] update_portfolio_weights uses portfolio domain logic (rebalance_weights)
- [ ] update_portfolio_weights returns False for non-existent portfolio
- [ ] get_dependency_summary returns correct dependency type names
- [ ] Service follows SRP (only portfolio management)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility - Only portfolio management | ✅ OK |
| SOL-005 | BASE_RULES.md | Dependency Inversion - Depend on abstractions | ✅ OK - EXEMPLAR |
| DP-004 | BASE_RULES.md | Dependency injection - All services | ✅ OK - EXEMPLAR |
| ARCH-001 | BASE_RULES.md | Layered architecture - Application layer | ✅ OK |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES.md | Modern syntax | ⚠️ PARTIAL - Uses `Dict` instead of `dict` |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ GAP - Catches Exception too broadly |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ FIXED - 2026-02-02 - Replaced print() with structured logging using logger |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ FIXED - 2026-02-02 - Added exc_info=True for stack trace logging |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** `typing.Dict`, `typing.List`, `typing.Optional`, `decimal.Decimal`
- **Internal:**
  - `app.core.di_container` (DIContainer)
  - `app.domain.entities.portfolio` (Portfolio)
  - `app.domain.factories` (AbstractEntityFactory)
  - `app.domain.repositories` (PortfolioRepository)

---

## Required Tests
- **test_portfolio_service_v2.py:**
  - Test constructor accepts injected dependencies
  - Test get_portfolio returns portfolio for valid ID
  - Test get_portfolio returns None for non-existent ID
  - Test get_portfolio handles repository errors gracefully
  - Test create_portfolio uses factory to create portfolio
  - Test create_portfolio persists to repository
  - Test create_portfolio returns created portfolio
  - Test update_portfolio_weights updates existing portfolio
  - Test update_portfolio_weights returns False for non-existent portfolio
  - Test update_portfolio_weights calls portfolio.rebalance_weights
  - Test get_dependency_summary returns correct types
  - Test DI container is optional
  - Test all methods delegate to dependencies appropriately

---

## Notes
**Design Pattern Example:** This service is a reference implementation for Dependency Inversion Principle (DIP) in the codebase. It demonstrates how to inject dependencies rather than create them, following Rule 03-solid-principles.md and Rule 05-architecture.md.

**Known Issues:**
- Uses `print()` for error logging instead of proper logger (LOG-001, LOG-004)
- Catches `Exception` too broadly in get_portfolio (CC-006)
- Should use modern `dict` type hint instead of `Dict` (TYP-002)
