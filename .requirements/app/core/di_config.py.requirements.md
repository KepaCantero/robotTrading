# di_config.py

## Purpose
Configures the DI container with application dependencies (factories, repositories, services).

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses standard types only (no Pydantic models or dataclasses).

### Configuration Structure
```python
def configure_container() -> DIContainer
    # Returns configured container with:
    # - AbstractEntityFactory -> TradingEntityFactory
    # - TODO: Repositories
    # - TODO: Application services
```

---

## Function Signatures (Contracts)

### `configure_container() -> DIContainer`
**Pre:** None
**Post:** Container initialized with domain factories
**Raises:** None
**Retry:** No
**Side Effects:** Registers singleton factories

### `initialize_container() -> DIContainer`
**Pre:** None
**Post:** Global container initialized
**Raises:** None
**Retry:** No
**Side Effects:** Calls configure_container()

---

## Acceptance Criteria
- [ ] DP-004: Dependency injection used for all services
- [ ] Domain factories registered as singletons
- [ ] Container returned is configured and ready
- [ ] initialize_container() calls configure_container()
- [ ] TODO markers addressed for repositories and services

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| DP-004 | BASE_RULES.md | Dependency injection required | ✅ OK |
| SOL-005 | BASE_RULES.md | Dependency Inversion Principle | ✅ OK |
| ARCH-003 | BASE_RULES.md | No framework in domain | ⚠️ PARTIAL - TODOs incomplete |

---

## Dependencies
- **External:** None
- **Internal:** app.core.di_container, app.domain.factories

---

## Required Tests
- **tests/core/test_di_config.py:**
  - Test container configuration completes
  - Test domain factories registered
  - Test singleton lifecycle for factories

---

## Notes
Incomplete implementation with TODO markers. Need to add repositories and services when available.
