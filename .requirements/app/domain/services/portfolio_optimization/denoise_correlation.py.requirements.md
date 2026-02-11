# denoise_correlation.py

## Purpose
Domain service file for correlation matrix de-noising using Random Matrix Theory

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### DenoisedResult
**Purpose:** Result of correlation matrix de-noising.
**Fields:**
- original_corr: np.ndarray - Original correlation matrix (N, N)
- denoised_corr: np.ndarray - De-noised correlation matrix (N, N)
- denoised_cov: Optional[np.ndarray] - De-noised covariance matrix (N, N)
- eigenvalues: np.ndarray - Eigenvalues of original matrix (N,)
- denoised_eigenvalues: np.ndarray - Eigenvalues after de-noising (N,)
- symbols: List[str] - Asset symbols/tickers

### CorrelationDenoiser
**Purpose:** Correlation matrix de-noising using Random Matrix Theory.

Removes noise from correlation matrices by:
1. Computing eigenvalue decomposition
2. Identifying signal vs noise eigenvalues using RMT
3. Replacing noise eigenvalues with their average
4. Reconstructing de-noised matrix

---

## Function Signatures (Contracts)

### `DenoisedResult.noise_ratio(self) -> float`
**Pre:** None
**Post:** Returns ratio of noise eigenvalues to total eigenvalues
**Raises:** None
**Retry:** No
**Side Effects:** None

### `CorrelationDenoiser.denoise_correlation(self, corr_matrix: np.ndarray, n_observations: int, symbols: Optional[List[str]] = None) -> DenoisedResult`
**Pre:** corr_matrix is square (N, N), n_observations/n >= 2.0
**Post:** DenoisedResult with de-noised correlation matrix
**Raises:** ValueError if matrix not square or T/n ratio insufficient
**Retry:** No
**Side Effects:** None

### `CorrelationDenoiser.denoise_correlation_with_std(self, cov_matrix: np.ndarray, n_observations: int, symbols: Optional[List[str]] = None) -> DenoisedResult`
**Pre:** cov_matrix is square with positive variance assets, T/n >= 2.0
**Post:** DenoisedResult with de-noised covariance matrix
**Raises:** ValueError if matrix invalid or zero variance assets
**Retry:** No
**Side Effects:** None

### `CorrelationDenoiser.fit_kde(self, eigenvalues: np.ndarray) -> Tuple[np.ndarray, np.ndarray]`
**Pre:** eigenvalues has at least 2 elements
**Post:** Returns (eigenvalue_grid, pdf_values) for KDE
**Raises:** ValueError if < 2 eigenvalues, ImportError if scipy unavailable
**Retry:** No
**Side Effects:** None

### `CorrelationDenoiser.get_number_of_signal_factors(self, corr_matrix: np.ndarray, n_observations: int) -> int`
**Pre:** corr_matrix is square
**Post:** Returns estimated number of signal factors
**Raises:** ValueError if matrix not square
**Retry:** No
**Side Effects:** None

### `CorrelationDenoiser.shrink_to_constant_correlation(self, corr_matrix: np.ndarray, shrinkage: Optional[float] = None) -> np.ndarray`
**Pre:** corr_matrix is square, shrinkage in [0, 1] if provided
**Post:** Returns shrunk correlation matrix
**Raises:** ValueError if shrinkage out of range
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
**Notes:** File fully complies with BASE_RULES. Implements Lopez de Prado's RMT de-noising method. Validation includes matrix shape checking and RMT T/n ratio validation (min_observation_ratio >= 2.0). Logging uses log_optimization_failure for eigenvalue decomposition failures. Uses np.linalg.eigh for symmetric matrices. NumPy 2.0 compatible.

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
- **External:** numpy (numerical operations), scipy (optimization, spatial distance, stats)
- **Internal:** app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_denoise_correlation.py:** Unit tests for:
  - Spectral de-noising with valid correlation matrix
  - T/n ratio validation
  - Marchenko-Pastur eigenvalue threshold calculation
  - Covariance de-noising with std devs
  - KDE fitting for eigenvalue distribution
  - Signal factor counting
  - Constant correlation shrinkage

---

## Notes

**File Reference:** `app/domain/services/portfolio_optimization/denoise_correlation.py`
**Created:** 2026-02-05
**Status:** ✅ AUDIT PASSED
