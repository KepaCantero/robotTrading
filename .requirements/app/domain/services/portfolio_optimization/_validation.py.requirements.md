# _validation.py

## Purpose
Shared validation utilities for portfolio optimization including covariance matrix validation, input sanitization, and logging across all optimization modules.

---

## Type Definitions / Data Classes
None (utility module with standalone functions)

---

## Function Signatures (Contracts)

### `is_square_matrix(matrix) -> bool`
**Pre:** matrix is numpy array
**Post:** Returns True if matrix.ndim == 2 and shape[0] == shape[1]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `is_symmetric(matrix, tolerance) -> bool`
**Pre:** matrix is numpy array
**Post:** Returns True if matrix == matrix.T within tolerance
**Raises:** None
**Retry:** No
**Side Effects:** None

### `is_positive_semidefinite(matrix, tolerance, check_symmetry) -> bool`
**Pre:** matrix is numpy array
**Post:** Returns True if all eigenvalues >= -tolerance
**Raises:** ValueError if matrix not square
**Retry:** No
**Side Effects:** None

### `validate_covariance_matrix(cov_matrix, check_psd, check_symmetry, enforce_psd) -> Tuple[bool, NDArray, Optional[str]]`
**Pre:** cov_matrix is numpy array
**Post:** Returns (is_valid, processed_matrix, error_message)
**Raises:** None (errors returned in tuple)
**Retry:** No
**Side Effects:** Logs validation results, symmetrizes if needed

### `enforce_positive_semidefinite(cov_matrix, tolerance) -> NDArray[np.float64]`
**Pre:** cov_matrix is square
**Post:** Returns PSD matrix via eigenvalue clipping
**Raises:** None
**Retry:** No
**Side Effects:** None

### `sanitize_input_returns(returns, min_variance_threshold) -> Tuple[NDArray, list[str], list[int]]`
**Pre:** returns is dict or array
**Post:** Returns (cleaned_returns, valid_symbols, valid_indices)
**Raises:** ValueError if no valid assets found
**Retry:** No
**Side Effects:** Logs dropped assets (NaN, zero variance)

### `validate_weights_sum_to_one(weights, tolerance) -> Tuple[bool, float]`
**Pre:** weights is numpy array
**Post:** Returns (is_valid, actual_sum)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `log_optimization_failure(method_name, exception, context)`
**Pre:** method_name is string, exception is Exception instance
**Post:** Logs error with stack trace and context
**Raises:** None
**Retry:** No
**Side Effects:** Writes to log

### `sanitize_covariance_matrix(cov_matrix, min_variance_threshold, enforce_psd) -> Tuple[NDArray, list[int]]`
**Pre:** cov_matrix is (N, N)
**Post:** Returns (cleaned_cov, valid_indices)
**Raises:** ValueError if no assets with positive variance
**Retry:** No
**Side Effects:** Logs removed assets

### `get_condition_number(matrix) -> float`
**Pre:** matrix is numpy array
**Post:** Returns condition number (max singular / min singular)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Square matrix check: ndim == 2 and shape[0] == shape[1]
- [ ] Symmetry check within tolerance (default 1e-10)
- [ ] PSD check via eigenvalue decomposition
- [ ] Eigenvalue clipping enforces PSD: max(eig, tolerance)
- [ ] Input sanitization removes NaN assets
- [ ] Input sanitization removes zero-variance assets
- [ ] Returns validation raises error if no valid assets
- [ ] Covariance sanitization removes zero-variance diagonal assets
- [ ] Weight sum validation within 1e-6 tolerance
- [ ] Condition number calculation for matrix stability
- [ ] Structured logging for all validation failures (LOG-001)
- [ ] Stack trace logging for optimization failures

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance PSD validation | ✅ OK - is_positive_semidefinite() |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All validation logged |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ OK - log_optimization_failure() |
| TYP-001 | BASE_RULES | Type hints | ✅ OK - Full type coverage |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear function names |
| ARCH-004 | BASE_RULES | Small functions | ✅ OK - All functions < 30 lines |

---

## Dependencies
- **External:** numpy, logging, traceback, typing
- **Internal:** None (utility module)

---

## Required Tests
- **test_validation.py:**
  - is_square_matrix with 2D square matrix
  - is_square_matrix with non-square matrix
  - is_square_matrix with 1D array
  - is_symmetric with symmetric matrix
  - is_symmetric with non-symmetric matrix
  - is_positive_semidefinite with PSD matrix
  - is_positive_semidefinite with non-PSD matrix
  - is_positive_semidefinite with non-square matrix (raises)
  - validate_covariance_matrix with valid matrix
  - validate_covariance_matrix with non-symmetric matrix (symmetrizes)
  - validate_covariance_matrix with non-PSD matrix (enforce_psd=True)
  - validate_covariance_matrix with non-PSD matrix (enforce_psd=False)
  - enforce_positive_semidefinite clips negative eigenvalues
  - sanitize_input_returns with dict input
  - sanitize_input_returns with array input
  - sanitize_input_returns removes NaN assets
  - sanitize_input_returns removes zero-variance assets
  - sanitize_input_returns raises error if no valid assets
  - validate_weights_sum_to_one with valid weights
  - validate_weights_sum_to_one with invalid sum
  - log_optimization_failure logs error and stack trace
  - sanitize_covariance_matrix removes zero-variance assets
  - sanitize_covariance_matrix enforces PSD
  - get_condition_number calculation

---

## Notes
This is a shared utility module used by all portfolio optimization algorithms. Centralized validation ensures consistency and reduces code duplication. All functions are pure (no side effects except logging).
