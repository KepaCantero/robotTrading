# Plan: Refactor app/api/portfolio.py - Implement Dependency Injection

## Overview
Refactor DP-004 violation in app/api/portfolio.py to use Dependency Injection pattern.
This addresses architectural violation found during GAP audit.

## Validation Commands
- `python -m py_compile app/api/portfolio.py`
- `python -m py_compile app/core/di_container.py`
- `mypy --strict app/api/portfolio.py`
- `ruff check app/api/portfolio.py`
- `pytest tests/api/test_portfolio.py -v`

## Context

**File:** `app/api/portfolio.py`
**Line:** 43
**Violation:** DP-004 (Direct Instantiation)
**Pattern:** DI Container with FastAPI Depends

### Current Code
```python
provider = PaperTradingPortfolioProvider()
_portfolio_service = PortfolioService(provider)
```

### Target Code
```python
from app.core.di_container import DIContainer

_di_container = DIContainer()

def get_portfolio_service() -> PortfolioService:
    """FastAPI dependency for portfolio service."""
    return _di_container.get_portfolio_service()

# All endpoints use:
# portfolio_service: PortfolioService = Depends(get_portfolio_service)
```

---

### Task 1: Create DI Container
- [ ] Create `app/core/di_container.py` with DI container class
- [ ] Implement singleton pattern with lazy initialization
- [ ] Add `get_portfolio_service()` method
- [ ] Verify syntax: `python -m py_compile app/core/di_container.py`

### Task 2: Refactor app/api/portfolio.py
- [ ] Add import: `from app.core.di_container import DIContainer`
- [ ] Create `_di_container` instance
- [ ] Create `get_portfolio_service()` dependency function
- [ ] Update all endpoints to use `Depends(get_portfolio_service)`
- [ ] Remove direct instantiation at line 43
- [ ] Verify syntax: `python -m py_compile app/api/portfolio.py`

### Task 3: Create/Update Tests
- [ ] Create/update `tests/api/test_portfolio.py`
- [ ] Add test: `test_get_portfolio_service_returns_singleton()`
- [ ] Add test: `test_get_portfolio_service_with_mock()`
- [ ] Run tests: `pytest tests/api/test_portfolio.py -v`
- [ ] Verify all tests pass

### Task 4: Run QA Checks
- [ ] Syntax check: `python -m py_compile app/api/portfolio.py`
- [ ] Type check: `mypy --strict app/api/portfolio.py`
- [ ] Lint check: `ruff check app/api/portfolio.py`
- [ ] All checks pass

### Task 5: Update Requirements Document
- [ ] Read: `.requirements/app/api/portfolio.py.requirements.md`
- [ ] Update DP-004 status from ❌ GAP to ✅ FIXED
- [ ] Add timestamp: `date -u +%Y-%m-%dT%H:%M:%SZ`
- [ ] Update Audit Status section

---

## Acceptance Criteria

- [ ] `app/core/di_container.py` created
- [ ] `app/api/portfolio.py` uses DI container
- [ ] All endpoints use `Depends(get_portfolio_service)`
- [ ] Tests pass
- [ ] QA checks pass (syntax, type, lint)
- [ ] Requirements updated: DP-004 → ✅ FIXED

---

## Related Files

- Task definition: `.claude/tasks/refactor_portfolio_di.md`
- Base template: `.claude/base/REFACTOR_BASE.md`
- Requirements: `.requirements/app/api/portfolio.py.requirements.md`
- BASE_RULES: `.requirements/BASE_RULES.md`

---

**Priority:** P1
**Estimated:** 2-3 hours
**Dependencies:** None (foundation for other DI tasks)
