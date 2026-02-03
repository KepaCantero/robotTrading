# create_portfolio_use_case.py

## Purpose
Create Portfolio Use Case - Creates new portfolio entities with capital and risk parameters using factory pattern.

---

## Type Definitions / Data Classes

No custom data classes defined in this file (uses domain entities).

**Domain Dependencies:**
- `Portfolio` entity with `PortfolioStatus`
- `TradingEntityFactory` for entity creation
- `Capital` value object
- `RiskParameters` value object

---

## Function Signatures (Contracts)

### `CreatePortfolioUseCase.__init__(factory: Optional[TradingEntityFactory] = None) -> None`
**Pre:** None
**Post:** Use case initialized with factory
**Raises:** None
**Retry:** No
**Side Effects:** Creates default TradingEntityFactory if None

### `CreatePortfolioUseCase.execute(
    portfolio_id: str,
    initial_capital: Decimal,
    currency: str = "USD",
    max_position_size_pct: Decimal = Decimal("0.2"),
    max_portfolio_exposure_pct: Decimal = Decimal("0.8"),
) -> Portfolio`
**Pre:** portfolio_id is non-empty; initial_capital > 0; percentages in (0, 1]
**Post:** Returns created Portfolio entity
**Raises:** ValueError if factory validation fails
**Retry:** No
**Side Effects:** Delegates to factory.create_portfolio()

**Default Parameters:**
- currency: "USD"
- max_position_size_pct: 20% (0.2)
- max_portfolio_exposure_pct: 80% (0.8)

---

## Acceptance Criteria
- [ ] **AC-001:** execute() returns Portfolio entity
- [ ] **AC-002:** execute() delegates to factory.create_portfolio()
- [ ] **AC-003:** Default currency is USD
- [ ] **AC-004:** Default max position size is 20%
- [ ] **AC-005:** Default max portfolio exposure is 80%
- [ ] **AC-006:** All parameters passed to factory
- [ ] **AC-007:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Create Portfolio Use Case):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Use case pattern | Clean Architecture | Application orchestrator | ✅ OK - CreatePortfolioUseCase |
| Factory pattern | GoF | Factory for entity creation | ✅ OK - TradingEntityFactory |
| Delegation | Clean code | Factory creates entity | ✅ OK - execute() delegates |
| Optional dependency | BASE_RULES.md (ARCH-005) | Default factory provided | ✅ OK - __init__() |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and GoF Factory pattern.

---

## Dependencies
- **External:** `decimal` (std), `typing` (std)
- **Internal:**
  - `app.domain.entities.portfolio.Portfolio`
  - `app.domain.entities.portfolio.PortfolioStatus`
  - `app.domain.factories.TradingEntityFactory`
  - `app.domain.value_objects.capital.Capital`
  - `app.domain.value_objects.risk_parameters.RiskParameters`

---

## Required Tests
- **test_create_portfolio_use_case.py:**
  - `test_init_with_factory()` - Stores provided factory
  - `test_init_without_factory()` - Creates default factory
  - `test_execute_returns_portfolio()` - Portfolio created
  - `test_execute_passes_all_params()` - All params forwarded to factory
  - `test_execute_default_currency()` - USD
  - `test_execute_default_max_position_size()` - 20%
  - `test_execute_default_max_portfolio_exposure()` - 80%
  - `test_execute_custom_currency()` - Uses provided currency
  - `test_execute_custom_params()` - Uses provided percentages
  - `test_execute_delegates_to_factory()` - Factory called correctly

---

## Notes
- **Critical:** CreatePortfolioUseCase is a USE CASE (Clean Architecture application layer)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Application Service pattern
- **Use Case Pattern:** Simple orchestrator that delegates to factory
- **Factory Pattern:** TradingEntityFactory handles entity creation logic
- **Optional Dependency:** Factory can be injected (useful for testing)
- **Default Parameters:** Sensible defaults for risk parameters
  - max_position_size_pct: 20% (no single position exceeds 20%)
  - max_portfolio_exposure_pct: 80% (can use leverage or hold cash)
- **Currency:** USD default, but supports any currency code
- **Delegation:** All creation logic delegated to factory (Single Responsibility Principle)
- **Simple Use Case:** One of the simplest use cases - pure delegation
- **Testing:** Easy to test by mocking factory

---

**File Reference:** `app/application/use_cases/create_portfolio_use_case.py`
**Last Audited:** 2026-02-01
