# nco.py

## Purpose
Domain service file for Nested Clustered Optimization (NCO)

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### NCOResult
**Purpose:** Result of Nested Clustered Optimization.
**Fields:**
- weights: np.ndarray - NCO weights
- cluster_weights: Dict[int, np.ndarray] - Weights within each cluster
- cluster_allocation: Dict[int, float] - Allocation to each cluster
- n_clusters: int - Number of clusters used
- symbols: List[str] - Asset symbols

### NestedClusteredOptimizer
**Purpose:** Nested Clustered Optimization (NCO) portfolio optimizer.

NCO improves on HRP by:
1. Clustering assets hierarchically
2. Optimizing within each cluster (convex optimization)
3. Allocating across clusters (convex optimization)

This nested approach:
- Reduces dimensionality of optimization problem
- Handles multicollinearity naturally
- Outperforms both HRP and MVO out-of-sample

---

## Function Signatures (Contracts)

### `NCOResult.weights_dict(self) -> Dict[str, float]`
**Pre:** None
**Post:** Returns weights as {symbol: weight} dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None

### `NestedClusteredOptimizer.optimize(self, cov_matrix: np.ndarray, expected_returns: Optional[np.ndarray] = None, symbols: Optional[List[str]] = None, n_clusters: Optional[int] = None) -> NCOResult`
**Pre:** cov_matrix is square, PSD
**Post:** NCOResult with optimal weights
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** Logs cluster-level optimization failures

### `get_nco_with_multiple_n(cov_matrix: np.ndarray, expected_returns: Optional[np.ndarray] = None, symbols: Optional[List[str]] = None, n_clusters_range: Optional[List[int]] = None) -> Dict[int, NCOResult]`
**Pre:** cov_matrix is square, PSD
**Post:** Dictionary mapping n_clusters to NCOResult
**Raises:** None (logs errors and continues)
**Retry:** No
**Side Effects:** Logs failures for individual n values


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
**Notes:** File fully complies with BASE_RULES. Implements Lopez de Prado's Nested Clustered Optimization. Validates covariance matrix and sanitizes inputs (removes zero variance assets). Uses correlation-based heuristic for optimal cluster selection. Handles cluster-level optimization failures gracefully with fallback to equal weights. Supports both Sharpe maximization and variance minimization within clusters. NumPy 2.0 compatible.

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
- **External:** numpy (numerical operations), scipy (clustering, optimization, distance)
- **Internal:** 
  - app.domain.services.portfolio_optimization.hrp
  - app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_nco.py:** Unit tests for:
  - NCO optimization with valid covariance matrix
  - Cluster number validation (min_cluster_size)
  - Correlation-based optimal cluster selection
  - Intra-cluster Sharpe maximization
  - Intra-cluster variance minimization
  - Inter-cluster inverse variance allocation
  - Multiple n_clusters execution
  - Zero variance asset handling

---

## Notes

**File Reference:** `app/domain/services/portfolio_optimization/nco.py`
**Created:** 2026-02-05
**Status:** ✅ AUDIT PASSED
