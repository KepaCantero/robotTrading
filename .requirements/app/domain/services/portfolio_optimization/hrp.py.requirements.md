# hrp.py

## Purpose
Domain service file for Hierarchical Risk Parity portfolio optimization

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### HRPResult
**Purpose:** Result of Hierarchical Risk Parity optimization.
**Fields:**
- weights: np.ndarray - HRP weights
- hierarchy: np.ndarray - Linkage matrix (hierarchical clustering)
- order: List[int] - Order of assets in hierarchy
- clusters: Dict[str, List[int]] - Cluster assignments
- symbols: List[str] - Asset symbols
- cophenetic_corr: float - Quality of dendrogram preservation

### HierarchicalRiskParity
**Purpose:** Hierarchical Risk Parity portfolio optimizer.

HRP constructs portfolios by:
1. Hierarchical clustering of assets based on correlation
2. Bisectional allocation within clusters using inverse variance

Advantages over MVO:
- Does not require invertibility of covariance matrix
- More robust out-of-sample
- Naturally handles multicollinearity
- No need to estimate expected returns

---

## Function Signatures (Contracts)

### `HRPResult.weights_dict(self) -> Dict[str, float]`
**Pre:** None
**Post:** Returns weights as {symbol: weight} dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None

### `HRPResult.get_cluster_allocation(self, n_clusters: int) -> Dict[int, List[str]]`
**Pre:** 2 <= n_clusters <= number of assets
**Post:** Returns cluster_id -> [symbols] mapping
**Raises:** None
**Retry:** No
**Side Effects:** None

### `HierarchicalRiskParity.optimize(self, cov_matrix: np.ndarray, symbols: Optional[List[str]] = None) -> HRPResult`
**Pre:** cov_matrix is square, PSD
**Post:** HRPResult with optimal weights and hierarchy
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** Logs warning if cophenetic correlation < 0.7

### `HierarchicalRiskParity.get_dendrogram_data(self, cov_matrix: np.ndarray) -> Tuple[np.ndarray, List[int]]`
**Pre:** cov_matrix is square, PSD
**Post:** Returns (linkage_matrix, leaf_order)
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** None

### `inverse_variance_weights(cov_matrix: np.ndarray) -> np.ndarray`
**Pre:** cov_matrix is square with at least one positive variance asset
**Post:** Returns inverse variance weights summing to 1.0
**Raises:** ValueError if all assets have zero variance
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
**Notes:** File fully complies with BASE_RULES. Implements Lopez de Prado's HRP methodology. Validates covariance matrix via validate_covariance_matrix before optimization. Uses Ward linkage for hierarchical clustering. Logs cophenetic correlation warnings when dendrogram quality is low. Handles zero variance assets via sanitization. NumPy 2.0 compatible.

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
- **External:** numpy (numerical operations), scipy (hierarchical clustering, distance)
- **Internal:** app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_hrp.py:** Unit tests for:
  - HRP optimization with valid covariance matrix
  - Covariance matrix validation (PSD, symmetry)
  - Linkage method validation
  - Distance metric validation
  - Cophenetic correlation calculation and warnings
  - Dendrogram data generation
  - Inverse variance weights calculation
  - Zero variance asset handling

---

## Notes

**File Reference:** `app/domain/services/portfolio_optimization/hrp.py`
**Created:** 2026-02-05
**Status:** ✅ AUDIT PASSED
