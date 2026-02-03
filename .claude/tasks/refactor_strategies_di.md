# Task: Refactor app/api/strategies.py - Implement Dependency Injection

## Overview

Refactor **DP-004 violations** in `app/api/strategies.py` to use Dependency Injection pattern.

---

## Refactoring Details

**File:** `app/api/strategies.py`
**Lines:** 32, 41, 50, 62
**Violation:** DP-004 (Direct Instantiation - 4 locations)
**Pattern:** DI Container with FastAPI Depends

### Current Code
```python
def get_strategy_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    return registry

def get_strategy_config_loader() -> StrategyConfigLoader:
    loader = StrategyConfigLoader()
    return loader

def get_strategy_logger() -> StrategyLogger:
    logger = StrategyLogger()
    return logger

def get_execution_engine() -> ExecutionEngine:
    registry = get_strategy_registry()
    config_loader = get_strategy_config_loader()
    logger = get_strategy_logger()
    engine = ExecutionEngine(registry, config_loader, logger)
    return engine
```

### Target Code
```python
from app.core.di_container import DIContainer

_di_container = DIContainer()

def get_strategy_registry() -> StrategyRegistry:
    return _di_container.get_strategy_registry()

def get_strategy_config_loader() -> StrategyConfigLoader:
    return _di_container.get_strategy_config_loader()

def get_strategy_logger() -> StrategyLogger:
    return _di_container.get_strategy_logger()

def get_execution_engine() -> ExecutionEngine:
    return _di_container.get_execution_engine()
```

---

## Workflow Steps

### Step 1: Implementer
**Template:** `.tasks/templates/REFACTOR_IMPLEMENTER.md`

**Context Variables:**
- `{{PYTHON_FILE}}` = `app/api/strategies.py`
- `{{VIOLATION_TYPE}}` = `DP-004`
- `{{PATTERN}}` = `DI Container`

**Implementation:**
1. Extend `app/core/di_container.py` with 4 strategy services
2. Update all 4 getter functions to use DI container
3. Remove direct instantiation in all functions

---

### Step 2: Tester
**Template:** `.tasks/templates/REFACTOR_TESTER.md`

**Context Variables:**
- `{{PYTHON_FILE}}` = `app/api/strategies.py`
- `{{TEST_FILE}}` = `tests/api/test_strategies.py`

**Tests to Create:**
```python
def test_all_strategy_services_are_singletons():
    """Test all services return singleton instances."""
    assert get_strategy_registry() is get_strategy_registry()
    assert get_strategy_config_loader() is get_strategy_config_loader()
    assert get_strategy_logger() is get_strategy_logger()
    assert get_execution_engine() is get_execution_engine()

def test_execution_engine_dependency_chain():
    """Test execution engine has all dependencies."""
    engine = get_execution_engine()
    assert engine.registry is not None
    assert engine.config_loader is not None
    assert engine.logger is not None
```

---

### Step 3: Code Reviewer
**Template:** `.tasks/templates/REFACTOR_CODE_REVIEWER.md`

---

### Step 4: Auditor
**Template:** `.tasks/templates/REFACTOR_AUDITOR.md`

---

## Acceptance Criteria

- [ ] `app/core/di_container.py` extended with 4 services
- [ ] All 4 getter functions use DI container
- [ ] Service dependency chain managed by container
- [ ] Tests pass
- [ ] QA checks pass
- [ ] Requirements updated: DP-004 → ✅ FIXED

---

## Files

| File | Action |
|------|--------|
| `app/core/di_container.py` | EXTEND |
| `app/api/strategies.py` | MODIFY |
| `tests/api/test_strategies.py` | UPDATE |
| `.requirements/app/api/strategies.py.requirements.md` | UPDATE |

---

**Priority:** P1
**Estimated:** 3-4 hours
**Dependencies:** `refactor_portfolio_di.md` (requires DI container)
