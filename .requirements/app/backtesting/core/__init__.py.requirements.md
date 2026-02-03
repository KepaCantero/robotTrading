# __init__.py

## Purpose
Package initialization for backtesting core modules, providing clean imports and public API surface.

---

## Type Definitions / Data Classes

This file contains no type definitions - it only manages imports and exports.

---

## Function Signatures (Contracts)

No functions are defined in this file. It only provides import statements and `__all__` export list.

### Import Statements
```python
from app.backtesting.core.config_loader import BacktestConfigLoader
from app.backtesting.core.executor import BacktestExecutor
from app.backtesting.core.facade import BacktestRunnerFacade, create_backtest_runner
from app.backtesting.core.orchestrator import (
    BacktestDefaults,
    BacktestOrchestrator,
    BoundedResults,
    OrchestrationResult,
)
```

**Pre:** All imported modules exist and are valid
**Post:** All imports available in package namespace
**Raises:** ImportError if any imported module fails to load
**Retry:** No
**Side Effects:** Loads all core modules on package import

### `__all__` Export List
```python
__all__ = [
    "BacktestConfigLoader",
    "BacktestExecutor",
    "BacktestOrchestrator",
    "BacktestDefaults",
    "BoundedResults",
    "OrchestrationResult",
    "BacktestRunnerFacade",
    "create_backtest_runner",
]
```

**Purpose:** Defines public API of the package
**Usage:** Controls what is exported by `from app.backtesting.core import *`

---

## Acceptance Criteria
- [ ] All imports resolve successfully
- [ ] __all__ contains exactly 8 exports
- [ ] All exports in __all__ are imported
- [ ] No circular imports occur
- [ ] Package can be imported without side effects (except module loading)

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` for 96 universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | BASE_RULES.md | Explicit imports | ✅ OK - All imports are explicit |
| ARCH-002 | BASE_RULES.md | No circular imports | ✅ OK - No circular dependencies |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Using original class names |
| EXP-001 | BASE_RULES.md | Explicit __all__ | ✅ OK - __all__ defined |
| EXP-002 | BASE_RULES.md | __all__ matches imports | ✅ OK - All 8 imports in __all__ |
| MOD-001 | BASE_RULES.md | Package docstring | ✅ OK - Has module docstring |

---

## Dependencies
- **Internal:** All core backtesting modules (config_loader, executor, facade, orchestrator)

---

## Required Tests
- **tests/unit/backtesting/core/test_init.py:**
  - Test package imports successfully
  - Test all __all__ exports are accessible
  - Test from app.backtesting.core import * works correctly
  - Test BacktestConfigLoader is in __all__
  - Test BacktestExecutor is in __all__
  - Test BacktestOrchestrator is in __all__
  - Test BacktestDefaults is in __all__
  - Test BoundedResults is in __all__
  - Test OrchestrationResult is in __all__
  - Test BacktestRunnerFacade is in __all__
  - Test create_backtest_runner is in __all__
  - Test __all__ contains exactly 8 items

---

## Notes
- This is a pure initialization file with no logic
- It provides a clean public API for the backtesting.core package
- All core functionality is imported and made available at package level
- No circular import dependencies exist
- __all__ controls what gets exported with wildcard imports
