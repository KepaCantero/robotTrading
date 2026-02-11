# _validation.py

## Purpose
Shared validation utilities module for portfolio optimization

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

No dataclasses - provides validation functions for portfolio optimization modules.

---

## Function Signatures (Contracts)

### `is_square_matrix(matrix: np.ndarray) -> bool`
**Pre:** None
**Post:** Returns True if matrix.ndim == 2 and shape[0] == shape[1]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `is_symmetric(matrix: np.ndarray, tolerance: float = SYMMETRY_TOLERANCE) -> bool`
**Pre:** None
**Post:** Returns True if matrix is square and allclose(M, M.T)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `is_positive_semidefinite(matrix: np.ndarray, tolerance: float = PSD_TOLERANCE, check_symmetry: bool = True) -> bool`
**Pre:** None
**Post:** Returns True if all eigenvalues >= -tolerance
**Raises:** ValueError if matrix not square
**Retry:** No
**Side Effects:** None

### `validate_covariance_matrix(cov_matrix: np.ndarray, check_psd: bool = True, check_symmetry: bool = True, enforce_psd: bool = False) -> Tuple[bool, np.ndarray, Optional[str]]`
**Pre:** None
**Post:** Returns (is_valid, processed_matrix, error_message)
**Raises:** None
**Side Effects:** Logs errors and warnings

### `enforce_positive_semidefinite(cov_matrix: np.ndarray, tolerance: float = PSD_TOLERANCE) -> np.ndarray`
**Pre:** cov_matrix is square
**Post:** Returns PSD matrix with eigenvalues clipped to >= tolerance
**Raises:** None
**Retry:** No
**Side Effects:** None

### `sanitize_input_returns(returns: dict[str, list[float]] | np.ndarray, min_variance_threshold: float = MIN_VARIANCE_THRESHOLD) -> Tuple[np.ndarray, list[str], list[int]]`
**Pre:** returns is dict or 2D array
**Post:** Returns (cleaned_returns, valid_symbols, valid_indices)
**Raises:** ValueError if no valid assets found
**Side Effects:** Logs warnings for NaN and zero variance assets

### `validate_weights_sum_to_one(weights: np.ndarray, tolerance: float = WEIGHT_SUM_TOLERANCE) -> Tuple[bool, float]`
**Pre:** None
**Post:** Returns (is_valid, actual_sum)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `log_optimization_failure(method_name: str, exception: Exception, context: Optional[dict] = None) -> None`
**Pre:** None
**Post:** Logs error with exception details and stack trace
**Raises:** None
**Retry:** No
**Side Effects:** Writes to logger

### `sanitize_covariance_matrix(cov_matrix: np.ndarray, min_variance_threshold: float = MIN_VARIANCE_THRESHOLD, enforce_psd: bool = True) -> Tuple[np.ndarray, list[int]]`
**Pre:** cov_matrix is square
**Post:** Returns (cleaned_cov_matrix, valid_indices)
**Raises:** ValueError if no positive variance assets
**Side Effects:** Logs warning for removed assets

### `get_condition_number(matrix: np.ndarray) -> float`
**Pre:** matrix is 2D
**Post:** Returns condition number (max singular value / min singular value)
**Raises:** None
**Retry:** No
**Side Effects:** None


---

## Acceptance Criteria
- [x] **AC-001:** All public methods have complete type hints ✅ PASSED
- [x] **AC-002:** NumPy 2.0 compatibility ✅ PASSED
- [x] **AC-003:** All functions have docstrings following Google style ✅ PASSED
- [x] **AC-004:** Input validation on all public methods ✅ PASSED

---

## Audit Status

**Status:** PASSED
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0
**Notes:** File fully complies with BASE_RULES. Provides shared validation utilities for all portfolio optimization modules. Uses modern type hints including `list[T]` and `dict[K, V]` union syntax. Implements eigenvalue-based PSD checking and enforcement. log_optimization_failure includes stack trace logging with traceback.format_exception. Sanitization handles NaN and zero variance assets. NumPy 2.0 compatible (uses np.linalg.eigvalsh for symmetric matrices).

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type hints on public functions | ✅ PASSED |
| CC-001 | BASE_RULES.md | All functions documented (Google style) | ✅ PASSED |
| CC-006 | BASE_RULES.md | Validate all inputs | ✅ PASSED |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ PASSED |
| TYP-002 | BASE_RULES.md | No deprecated np aliases | ✅ PASSED |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** numpy (numerical operations, linear algebra)
- **Internal:** None (this is a utility module)

---

## Required Tests
- **test__validation.py:** Unit tests for:
  - Matrix shape validation (square check)
  - Symmetry checking with tolerance
  - PSD checking and enforcement
  - Covariance matrix validation with all flag combinations
  - Input returns sanitization (NaN removal, zero variance detection)
  - Weight sum validation
  - Optimization failure logging (stack trace capture)
  - Condition number calculation

---

## Notes

**File Reference:** `app/domain/services/portfolio_optimization/_validation.py`
**Created:** 2026-02-05
**Status:** ✅ AUDIT PASSED
