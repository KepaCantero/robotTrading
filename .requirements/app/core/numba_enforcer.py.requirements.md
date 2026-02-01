# numba_enforcer.py

## Purpose
MANDATORY Numba enforcement module that ensures all performance-critical code uses JIT compilation.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses standard types only (no Pydantic models or dataclasses).

### Enforcement State
```python
_enforcement_checked: bool = False    # REQUIRED - Track if enforcement performed
```

---

## Function Signatures (Contracts)

### `enforce_numba_available() -> None`
**Pre:** None
**Post:** Numba >= 0.59.0 available or RuntimeError raised
**Raises:** RuntimeError if Numba unavailable or version insufficient
**Retry:** No
**Side Effects:** None (fail-fast)

### `get_numba_version() -> Optional[str]`
**Pre:** None
**Post:** Returns Numba version string or None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `verify_numba_function(func: Callable, *args, **kwargs) -> bool`
**Pre:** func is callable
**Post:** Returns True if function is Numba-compiled
**Raises:** RuntimeError if function not compiled or execution fails
**Retry:** No
**Side Effects:** Executes function for verification

### `detect_performance_critical_code(file_path: str) -> list`
**Pre:** file_path is valid Python file
**Post:** Returns list of performance-critical patterns found
**Raises:** None
**Retry:** No
**Side Effects:** Reads and analyzes file

### `require_numba(func: Callable) -> Callable`
**Pre:** func is callable
**Post:** Returns wrapper that enforces Numba compilation
**Raises:** RuntimeError if Numba unavailable or func not compiled
**Retry:** No
**Side Effects:** Executes enforcement before function call

---

## Acceptance Criteria
- [ ] PERF-005: Numba JIT required for performance-critical code
- [ ] enforce_numba_available() checks Numba version >= 0.59.0
- [ ] RuntimeError raised with clear message if Numba unavailable
- [ ] Auto-enforcement on module import (unless TESTING=1)
- [ ] verify_numba_function checks for Numba attributes
- [ ] detect_performance_critical_code finds patterns
- [ ] require_numba decorator enforces compilation

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PERF-005 | BASE_RULES.md | Numba JIT for hot paths | ✅ OK - Enforced |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - RuntimeError with messages |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ OK - Errors logged |

---

## Dependencies
- **External:** numba >= 0.59.0 (REQUIRED)
- **Internal:** None

---

## Required Tests
- **tests/core/test_numba_enforcer.py:**
  - Test enforce_numba_available() passes with Numba
  - Test enforce_numba_available() fails without Numba
  - Test enforce_numba_available() fails with old version
  - Test verify_numba_function() detects compiled functions
  - Test verify_numba_function() raises for non-compiled
  - Test detect_performance_critical_code() finds patterns
  - Test require_numba decorator enforces
  - Test auto-enforcement skipped when TESTING=1

---

## Notes
MANDATORY module for all performance-critical code. Fail-fast approach ensures Numba availability before execution. Testing mode (TESTING=1) skips enforcement for unit tests.
