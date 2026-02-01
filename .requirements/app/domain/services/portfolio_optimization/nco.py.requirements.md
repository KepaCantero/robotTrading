# nco.py

## Purpose
Implements Nested Clustered Optimization (NCO) combining hierarchical clustering with convex optimization for portfolio allocation per López de Prado's methodology.

---

## Type Definitions / Data Classes

### NCOResult Class/DataClass
```python
@dataclass
class NCOResult:
    weights: np.ndarray                    # REQUIRED - NCO optimal weights (N,)
    cluster_weights: Dict[int, np.ndarray] # REQUIRED - Intra-cluster weights mapping
    cluster_allocation: Dict[int, float]   # REQUIRED - Inter-cluster allocation weights
    n_clusters: int                        # REQUIRED - Number of clusters used
    symbols: List[str]                     # REQUIRED - Asset symbols/tickers
```

**Validation Rules:**
- `weights` must sum to approximately 1.0 (full investment)
- `len(weights) == len(symbols)`
- `cluster_weights` keys must be in range `[1, n_clusters]`
- `cluster_allocation` values must sum to 1.0

### NestedClusteredOptimizer Class
```python
class NestedClusteredOptimizer:
    min_cluster_size: int              # REQUIRED, min(2) - Minimum assets per cluster
    _optimization_method: str          # REQUIRED, enum["sharpe", "min_variance"] - Optimization method
```

**Validation Rules:**
- `min_cluster_size >= 2`
- `_optimization_method in ["sharpe", "min_variance"]`

---

## Function Signatures (Contracts)

### `NestedClusteredOptimizer.__init__(min_cluster_size: int, optimization_method: str) -> NestedClusteredOptimizer`
**Pre:** `min_cluster_size >= 2`, `optimization_method in ["sharpe", "min_variance"]`
**Post:** Valid optimizer instance initialized
**Raises:** `ValueError` if parameters invalid
**Retry:** No
**Side Effects:** None

### `NestedClusteredOptimizer.optimize(cov_matrix: np.ndarray, expected_returns: Optional[np.ndarray], symbols: Optional[List[str]], n_clusters: Optional[int]) -> NCOResult`
**Pre:** `cov_matrix` is square, symmetric, positive semidefinite; `n_assets >= 2 * min_cluster_size`
**Post:** Returns `NCOResult` with weights summing to 1.0, all weights non-negative
**Raises:** `ValueError` if covariance matrix validation fails
**Retry:** No
**Side Effects:** None (pure computation)

### `NestedClusteredOptimizer._maximize_sharpe(cov_matrix: np.ndarray, expected_returns: np.ndarray, risk_free_rate: float = 0.0) -> np.ndarray`
**Pre:** `cov_matrix` is PSD, `len(expected_returns) == cov_matrix.shape[0]`
**Post:** Returns weights summing to 1.0, all weights in [0, 1]
**Raises:** None (falls back to equal weights on optimization failure)
**Retry:** No
**Side Effects:** None

### `NestedClusteredOptimizer._minimize_variance(cov_matrix: np.ndarray) -> np.ndarray`
**Pre:** `cov_matrix` is PSD square matrix
**Post:** Returns weights summing to 1.0, all weights in [0, 1]
**Raises:** None (falls back to equal weights on optimization failure)
**Retry:** No
**Side Effects:** None

### `get_nco_with_multiple_n(cov_matrix: np.ndarray, expected_returns: Optional[np.ndarray], symbols: Optional[List[str]], n_clusters_range: Optional[List[int]]) -> Dict[int, NCOResult]`
**Pre:** `cov_matrix` is valid covariance matrix
**Post:** Returns dictionary mapping `n_clusters` to `NCOResult`
**Raises:** None (logs errors and continues)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All NCO weights sum to 1.0 (±0.01 tolerance)
- [ ] All weights are non-negative
- [ ] Covariance matrix validation is performed before optimization
- [ ] Invalid covariance matrices raise `ValueError` with descriptive message
- [ ] Optimization failures fallback to equal weights within cluster
- [ ] Number of clusters is bounded: `2 <= n_clusters <= n_assets // min_cluster_size`
- [ ] Inverse variance allocation across clusters sums to 1.0
- [ ] Zero-variance clusters handled without division by zero
- [ ] Symbols list matches filtered assets after sanitization
- [ ] Expected returns filtered to match valid asset indices

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES.md | Validate covariance matrix is PSD | ✅ OK - Uses `validate_covariance_matrix` with `check_psd=True` |
| TRD-007 | BASE_RULES.md | Document TRADING_DAYS = 252 | ⚠️ NOT APPLIED - No annualization in this file |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses `log_optimization_failure` for errors |
| ARCH-004 | BASE_RULES.md | Functions < 20 lines (ideally) | ❌ GAP - Several methods exceed 20 lines: `_maximize_sharpe` (32 lines), `optimize` (130 lines) |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific `ValueError` raised with context |
| TYP-001 | BASE_RULES.md | 100% type coverage | ⚠️ NOT APPLIED - Private methods lack return types in some cases |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, scipy (cluster.hierarchy, optimize, spatial.distance)
- **Internal:** `app.domain.services.portfolio_optimization.hrp.HierarchicalRiskParity`, `app.domain.services.portfolio_optimization._validation`

---

## Required Tests
- **tests/unit/domain/services/test_nco.py:**
  - Test successful NCO optimization with valid covariance matrix
  - Test covariance matrix validation (PSD, symmetry)
  - Test cluster size constraints (min_cluster_size enforcement)
  - Test optimization methods (sharpe, min_variance)
  - Test zero-variance cluster handling (fallback to equal weights)
  - Test inverse variance allocation across clusters
  - Test symbol and expected returns filtering after sanitization
  - Test `get_nco_with_multiple_n` with various cluster ranges
  - Test failure scenarios: non-PSD matrix, insufficient assets
  - Test edge cases: 2 clusters only, maximum clusters

---

## Notes
Critical for portfolio optimization - López de Prado's NCO method outperforms both HRP and MVO out-of-sample by reducing dimensionality and handling multicollinearity.
