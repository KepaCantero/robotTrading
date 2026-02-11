# nested_clustered_optimization.py

## Purpose
Nested Clustered Optimization (NCO) per López de Prado (2019) - improves upon traditional mean-variance optimization.

---

## Type Definitions / Data Classes

### ClusteringMethod (Enum)
**Purpose:** Supported clustering methods (KMEANS, DBSCAN)

### NCOConfig (Dataclass)
**Purpose:** Configuration for NCO
- n_clusters: int = 5
- clustering_method: ClusteringMethod
- dbscan_eps: float = 0.5
- min_samples: int = 2
- min_cluster_size: int = 2
- max_weight_single_asset: float = 0.20
- risk_free_rate: float = 0.02
- random_state: int = 42

### NCOResult (Dataclass)
**Purpose:** Result from NCO
- weights: NDArray[np.float64]
- cluster_labels: NDArray[np.int32]
- n_clusters: int
- expected_return: float
- expected_risk: float
- sharpe_ratio: float
- cluster_weights: NDArray[np.float64]
- within_cluster_weights: dict[int, NDArray[np.float64]]
- converged: bool

---

## Function Signatures (Contracts)

### `NestedClusteredOptimization.get_weights(expected_returns, cov_matrix) -> NCOResult`
**Pre:** expected_returns.shape = (N,), cov_matrix.shape = (N, N)
**Post:** Returns NCO-optimized weights
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** All public methods have complete type hints
- [x] **AC-002:** NumPy 2.0 compatibility (uses np.float64, np.int32)
- [x] **AC-003:** All functions have docstrings following Google style
- [x] **AC-004:** Input validation on all public methods

---

## Audit Status

**Status:** PASSED
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** Excellent NCO implementation with full compliance to BASE_RULES.

---

## Critical Rules (MUST NOT BREAK)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type hints on public functions | ✅ PASSED - 7/7 typed |
| CC-001 | BASE_RULES.md | All functions documented | ✅ PASSED - Google style |
| CC-006 | BASE_RULES.md | Validate all inputs | ✅ PASSED - Comprehensive |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ PASSED - exc_info=True |
| TYP-002 | BASE_RULES.md | No deprecated np aliases | ✅ PASSED - Uses np.float64, np.int32 |
| ARCH-002 | BASE_RULES.md | Domain layer purity | ✅ PASSED - No infra imports |

---

## Dependencies
- **External:** numpy, scipy, sklearn
- **Internal:** None

---

## Required Tests
- **test_nested_clustered_optimization.py:** Tests for clustering, within-cluster optimization, allocation

---

## Notes
Excellent López de Prado NCO implementation with:
- Clear mathematical documentation with distance metric
- Well-structured three-step process (cluster, optimize within, allocate across)
- Good edge case handling (noise points, small clusters)
- Proper use of TYPE_CHECKING for imports
- Comprehensive validation and error logging

---

**File Reference:** `app/domain/portfolio_optimization/nested_clustered_optimization.py`
**Status:** ✅ PASSED AUDIT
