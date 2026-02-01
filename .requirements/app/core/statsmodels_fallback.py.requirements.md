# statsmodels_fallback.py

## Purpose
Graceful fallback mechanisms when statsmodels library is unavailable or specific functions are missing.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses conditional imports and fallback implementations.

### Fallback State
```python
STATSMODELS_AVAILABLE: bool = True/False    # REQUIRED - Indicates if statsmodels installed
```

---

## Function Signatures (Contracts)

### `get_statsmodels() -> Optional[ModuleType]`
**Pre:** None
**Post:** Returns statsmodels module or None
**Raises:** None
**Retry:** No
**Side Effects:** Attempts import

### `ols_fit(y: ArrayLike, x: ArrayLike) -> Optional[Dict]`
**Pre:** y and x are numeric arrays
**Post:** Returns OLS results or None if unavailable
**Raises:** None (graceful degradation)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Graceful degradation when statsmodels unavailable
- [ ] STATSMODELS_AVAILABLE flag indicates status
- [ ] Fallback implementations provided for key functions
- [ ] No crashes when library missing
- [ ] Warning logged when using fallback

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Graceful fallback |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - Warnings logged |

---

## Dependencies
- **External:** statsmodels (optional), numpy
- **Internal:** None

---

## Required Tests
- **tests/core/test_statsmodels_fallback.py:**
  - Test get_statsmodels() returns module when available
  - Test get_statsmodels() returns None when unavailable
  - Test STATSMODELS_AVAILABLE flag correct
  - Test ols_fit() works with statsmodels
  - Test ols_fit() returns None without statsmodels
  - Test warnings logged when using fallback

---

## Notes
Enables system to function without statsmodels. Performance may be reduced with NumPy-only fallbacks.
