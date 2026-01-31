# hrp.py

## Purpose
Hierarchical Risk Parity (HRP) portfolio optimization using hierarchical clustering and inverse variance allocation. More robust than MVO for out-of-sample performance.

---

## Type Definitions / Data Classes

### HRPResult
```python
@dataclass
class HRPResult:
    weights: np.ndarray              # REQUIRED - Optimal HRP portfolio weights
    hierarchy: np.ndarray            # REQUIRED - Linkage matrix from scipy
    order: List[int]                 # REQUIRED - Dendrogram leaf order
    clusters: Dict[str, List[int]]   # REQUIRED - Cluster assignments
    symbols: List[str]               # REQUIRED - Asset symbols
    cophenetic_corr: float           # REQUIRED - Quality of dendrogram preservation
```

**Validation Rules:**
- `weights` must sum to 1.0 (within numerical tolerance)
- All weights must be non-negative (long-only)
- `cophenetic_corr` should be > 0.7 for good clustering quality
- `hierarchy` must be valid scipy linkage matrix

---

## Function Signatures (Contracts)

### `HierarchicalRiskParity.__init__(linkage_method, distance_metric) -> None`
**Pre:** linkage_method in ["ward", "single", "complete", "average"], distance_metric in ["euclidean", "correlation"]
**Post:** Optimizer configured with specified clustering parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `optimize(cov_matrix: np.ndarray, symbols: Optional[List[str]]) -> HRPResult`
**Pre:** cov_matrix must be square, symmetric, and positive semidefinite; cov_matrix.shape[0] >= 2
**Post:** Returns HRP weights that sum to 1.0 with hierarchical structure
**Raises:** ValueError if cov_matrix is invalid (not currently implemented - GAP)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `get_dendrogram_data(cov_matrix: np.ndarray) -> Tuple[np.ndarray, List[int]]`
**Pre:** cov_matrix must be valid covariance matrix
**Post:** Returns (linkage_matrix, leaf_order) for visualization
**Raises:** None (errors propagate from scipy)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `inverse_variance_weights(cov_matrix: np.ndarray) -> np.ndarray` (module function)
**Pre:** cov_matrix must have positive diagonal elements
**Post:** Returns weights proportional to 1/σ² that sum to 1.0
**Raises:** ZeroDivisionError if any variance is zero
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `HRPResult.get_cluster_allocation(n_clusters: int) -> Dict[int, List[str]]`
**Pre:** 2 <= n_clusters <= number of assets
**Post:** Returns dictionary mapping cluster_id to list of symbols
**Raises:** ValueError if n_clusters is invalid
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Covariance matrix validated before optimization (PSD check, symmetry)
- [ ] **AC-002:** Edge case handling: single asset, singular covariance, NaN values
- [ ] **AC-003:** All public methods have complete type hints
- [ ] **AC-004:** NumPy 2.0 compatibility (no deprecated np aliases)
- [ ] **AC-005:** Error logging for optimization failures
- [ ] **AC-006:** All functions have docstrings following Google style
- [ ] **AC-007:** Cophenetic correlation quality warning if < 0.7

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (López de Prado HRP):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PSD validation | BASE_RULES.md (TRD-001) | Validate covariance matrix is positive semidefinite | ❌ GAP - No validation |
| Input sanitization | BASE_RULES.md (TRD-015) | Remove NaN, zero variance assets | ❌ GAP - No sanitization |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All public functions documented | ✅ OK - Complete |
| Error logging | BASE_RULES.md (LOG-004) | Log optimization failures | ❌ GAP - No logging |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy/scipy |
| Hierarchical clustering | López de Prado (03-advances-financial-ml.md) | Use linkage for clustering | ✅ OK - Implemented |
| Quasi-diagonalization | López de Prado | Reorder matrix by hierarchy | ✅ OK - leaves_list used |
| Recursive bisection | López de Prado | Allocate weights recursively | ⚠️ PARTIAL - Single bisection only |
| Inverse variance allocation | López de Prado | Use 1/σ² for risk parity | ✅ OK - Implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No `np.int`, `np.float` aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and López de Prado rules for HRP-specific requirements.

---

## Dependencies
- **External:** `numpy`, `scipy` (cluster.hierarchy, spatial.distance), `dataclasses` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_hrp.py:**
  - `test_hrp_valid_covariance()` - Happy path with valid input
  - `test_hrp_singular_covariance()` - Error path with singular matrix
  - `test_hrp_two_assets()` - Edge case with minimum assets
  - `test_hrp_single_asset_cluster()` - Verify single cluster handling
  - `test_hrp_cophenetic_quality()` - Validate quality metric
  - `test_inverse_variance_weights()` - Test IVP baseline
  - `test_get_cluster_allocation()` - Test cluster extraction
  - `test_hrp_nan_handling()` - Error path for NaN values
  - `test_hrp_zero_variance_asset()` - Error path for σ=0

---

## Notes
- **Critical:** Covariance matrix must be positive semidefinite for clustering to succeed
- **López de Prado Reference:** HRP advantages: (1) No matrix inversion needed, (2) More robust out-of-sample, (3) Handles multicollinearity naturally
- **Quality Metric:** Cophenetic correlation > 0.7 indicates good dendrogram preservation
- **Trading Convention:** Assumes 252 trading days/year for annualization (if annualized returns used)
- **Implementation Note:** Current bisection is simplified; full recursive bisection would traverse entire dendrogram

---

**File Reference:** `app/domain/services/portfolio_optimization/hrp.py`
**Last Audited:** 2026-02-01
