# nco.py

## Purpose
Nested Clustered Optimization (NCO) - combines hierarchical clustering with convex optimization for improved out-of-sample performance over both HRP and MVO.

---

## Type Definitions / Data Classes

### NCOResult
```python
@dataclass
class NCOResult:
    weights: np.ndarray                      # REQUIRED - Optimal NCO portfolio weights
    cluster_weights: Dict[int, np.ndarray]   # REQUIRED - Weights within each cluster
    cluster_allocation: Dict[int, float]     # REQUIRED - Allocation to each cluster
    n_clusters: int                          # REQUIRED - Number of clusters used
    symbols: List[str]                       # REQUIRED - Asset symbols
```

**Validation Rules:**
- `weights` must sum to 1.0 (within numerical tolerance)
- All weights must be non-negative (long-only)
- Sum of `cluster_allocation` must equal 1.0
- Each `cluster_weights` array must sum to 1.0

---

## Function Signatures (Contracts)

### `NestedClusteredOptimizer.__init__(min_cluster_size, optimization_method) -> None`
**Pre:** min_cluster_size >= 2, optimization_method in ["sharpe", "min_variance"]
**Post:** Optimizer configured with clustering parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `optimize(cov_matrix, expected_returns, symbols, n_clusters) -> NCOResult`
**Pre:** cov_matrix must be square, symmetric, and positive semidefinite; cov_matrix.shape[0] >= 2
**Post:** Returns NCO weights with nested cluster structure
**Raises:** ValueError if optimization fails (currently returns fallback weights - GAP)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `get_nco_with_multiple_n(cov_matrix, expected_returns, symbols, n_clusters_range) -> Dict[int, NCOResult]`
**Pre:** cov_matrix must be valid; n_clusters_range values between 2 and n_assets/2
**Post:** Returns dictionary mapping n_clusters to NCOResult (may skip failed optimizations)
**Raises:** None (exceptions caught and logged - but no logging implemented)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_maximize_sharpe(cov_matrix, expected_returns, risk_free_rate) -> np.ndarray` (private)
**Pre:** cov_matrix PSD, expected_returns same length as cov_matrix
**Post:** Returns weights maximizing Sharpe ratio (sum to 1.0, non-negative)
**Raises:** Returns equal weights if optimization fails
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_minimize_variance(cov_matrix) -> np.ndarray` (private)
**Pre:** cov_matrix must be PSD
**Post:** Returns minimum variance weights (sum to 1.0, non-negative)
**Raises:** Returns equal weights if optimization fails
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Covariance matrix validated before optimization (PSD check, symmetry)
- [ ] **AC-002:** Optimization failures logged with context (not silent fallback)
- [ ] **AC-003:** Edge case handling: empty clusters, single asset, singular covariance
- [ ] **AC-004:** All public methods have complete type hints
- [ ] **AC-005:** Magic numbers documented as constants (0.7, 0.5 correlation thresholds)
- [ ] **AC-006:** NumPy 2.0 compatibility
- [ ] **AC-007:** All functions have docstrings following Google style

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (López de Prado NCO):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PSD validation | BASE_RULES.md (TRD-001) | Validate covariance matrix is positive semidefinite | ❌ GAP - No validation |
| Input sanitization | BASE_RULES.md (TRD-015) | Remove NaN, zero variance assets | ❌ GAP - No sanitization |
| Error logging | BASE_RULES.md (LOG-004) | Log optimization failures | ❌ GAP - Silent fallback in get_nco_with_multiple_n |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only domain (HRP) dependency |
| Hierarchical clustering | López de Prado (46-machine-learning-asset-managers) | Use linkage for clustering | ✅ OK - Implemented |
| Nested optimization | López de Prado (46) | Optimize within + across clusters | ✅ OK - Two-level optimization |
| Inverse variance allocation | López de Prado (46) | Use 1/σ² for inter-cluster allocation | ✅ OK - Implemented |
| Convex optimization within cluster | López de Prado (46) | Use scipy.optimize for cluster weights | ✅ OK - SLSQP implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |
| Magic numbers | BASE_RULES.md (CC-001) | Document thresholds as constants | ❌ GAP - 0.7, 0.5 hardcoded |

**NOTE:** This analysis references BASE_RULES.md for universal rules and López de Prado rules for NCO-specific requirements.

---

## Dependencies
- **External:** `numpy`, `scipy` (cluster.hierarchy, optimize, spatial.distance), `dataclasses` (std)
- **Internal:** `app.domain.services.portfolio_optimization.hrp.HierarchicalRiskParity`

---

## Required Tests
- **test_nco.py:**
  - `test_nco_valid_input()` - Happy path with valid covariance and returns
  - `test_nco_without_returns()` - Minimize variance mode (no expected_returns)
  - `test_nco_singular_covariance()` - Error path with singular matrix
  - `test_nco_single_cluster()` - Edge case with n_clusters=1 equivalent
  - `test_nco_auto_determine_clusters()` - Auto cluster count based on correlation
  - `test_nco_high_correlation()` - Verify fewer clusters for high avg correlation
  - `test_nco_weights_sum_to_one()` - Validate weight constraint
  - `test_get_nco_with_multiple_n()` - Test multi-cluster evaluation
  - `test_nco_empty_cluster_handling()` - Verify min_cluster_size enforcement
  - `test_nco_nan_handling()` - Error path for NaN values

---

## Notes
- **Critical:** Covariance matrix must be positive semidefinite for optimization to succeed
- **López de Prado Reference:** NCO advantages: (1) Reduces dimensionality, (2) Handles multicollinearity, (3) Outperforms HRP and MVO out-of-sample
- **Two-Level Optimization:** Within clusters (convex optimization) + Across clusters (inverse variance)
- **Cluster Heuristic:** Average correlation determines n_clusters: >0.7 → n/10, >0.5 → n/5, else → n/3
- **Fallback Behavior:** Optimization failures return equal weights (could be improved with logging)
- **Trading Convention:** Assumes 252 trading days/year for annualization (if applicable)

---

**File Reference:** `app/domain/services/portfolio_optimization/nco.py`
**Last Audited:** 2026-02-01
