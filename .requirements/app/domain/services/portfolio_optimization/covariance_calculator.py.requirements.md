# covariance_calculator.py

## Purpose
Domain service file for covariance calculator

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### CovarianceResult
**Purpose:** Result of covariance calculation.
**Fields:**
- covariance_matrix: np.ndarray - Covariance matrix
- correlation_matrix: np.ndarray - Correlation matrix  
- std_devs: np.ndarray - Standard deviations
- means: np.ndarray - Mean returns
- symbols: List[str] - Asset symbols

### CovarianceCalculator
**Purpose:** Domain service for calculating covariance and correlation matrices.

Provides pure domain logic for:
- Sample covariance estimation
- Shrinkage estimators (Ledoit-Wolf)
- Exponential weighted covariance
- Correlation matrix calculation
- PSD enforcement

---

## Function Signatures (Contracts)

### `CovarianceResult.get_covariance(self, symbol1: str, symbol2: str) -> Decimal`
**Pre:** Both symbols exist in self.symbols
**Post:** Returns covariance as Decimal
**Raises:** ValueError if symbol not found
**Retry:** No
**Side Effects:** None

### `CovarianceResult.get_correlation(self, symbol1: str, symbol2: str) -> Decimal`
**Pre:** Both symbols exist in self.symbols
**Post:** Returns correlation as Decimal
**Raises:** ValueError if symbol not found
**Retry:** No
**Side Effects:** None

### `CovarianceResult.get_std_dev(self, symbol: str) -> Decimal`
**Pre:** Symbol exists in self.symbols
**Post:** Returns standard deviation as Decimal
**Raises:** ValueError if symbol not found
**Retry:** No
**Side Effects:** None

### `CovarianceCalculator.calculate_sample_covariance(self, returns: Dict[str, List[Decimal]]) -> CovarianceResult`
**Pre:** returns has at least 2 assets with 252+ observations
**Post:** CovarianceResult with PSD covariance matrix
**Raises:** ValueError if insufficient data or assets
**Retry:** No
**Side Effects:** None

### `CovarianceCalculator.calculate_shrinkage_covariance(self, returns: Dict[str, List[Decimal]], shrinkage: Optional[float] = None) -> CovarianceResult`
**Pre:** returns has at least 2 assets with 252+ observations
**Post:** CovarianceResult with shrunk covariance matrix
**Raises:** ValueError if insufficient data
**Retry:** No
**Side Effects:** None

### `CovarianceCalculator.calculate_exponential_covariance(self, returns: Dict[str, List[Decimal]], span: int = DEFAULT_EWMA_SPAN) -> CovarianceResult`
**Pre:** returns has at least 2 assets, span > 0
**Post:** CovarianceResult with EWMA covariance matrix
**Raises:** ValueError if invalid span or insufficient data
**Retry:** No
**Side Effects:** None

### `CovarianceCalculator.get_positive_semidefinite_covariance(self, cov_matrix: np.ndarray) -> np.ndarray`
**Pre:** cov_matrix is a square matrix
**Post:** Returns PSD covariance matrix
**Raises:** None
**Retry:** No
**Side Effects:** None

### `CovarianceCalculator.get_risk_contribution(self, weights: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray`
**Pre:** weights and cov_matrix have compatible dimensions
**Post:** Returns risk contribution array
**Raises:** None
**Retry:** No
**Side Effects:** None

### `CovarianceCalculator.get_effective_number_bets(self, weights: np.ndarray, cov_matrix: np.ndarray) -> float`
**Pre:** weights and cov_matrix have compatible dimensions
**Post:** Returns effective number of uncorrelated bets
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
**Notes:** File fully complies with BASE_RULES. Type hints use modern syntax (Optional[T], List[T]). Docstrings follow Google style with Args/Returns/Raises. Input validation includes range checks (min_observations >= 2, shrinkage in [0,1]), type validation, and data sanitization (NaN removal, zero variance detection). Error logging via shared _validation module. NumPy 2.0 compatible (uses np.ndarray directly).

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
- **External:** numpy (numerical operations), scipy (none - this is pure numpy)
- **Internal:** app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_covariance_calculator.py:** Unit tests for:
  - Sample covariance calculation with valid inputs
  - Shrinkage covariance with various shrinkage values
  - Exponential covariance calculation
  - PSD enforcement on non-PSD matrices
  - Input validation (insufficient data, invalid parameters)
  - NaN and zero variance handling

---

## Notes

**File Reference:** `app/domain/services/portfolio_optimization/covariance_calculator.py`
**Created:** 2026-02-05
**Status:** ✅ AUDIT PASSED
