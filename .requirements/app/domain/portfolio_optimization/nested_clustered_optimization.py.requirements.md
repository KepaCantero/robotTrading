# nested_clustered_optimization.py.requirements.md

## Purpose
Implements López de Prado's Nested Clustered Optimization (NCO) to improve portfolio optimization by clustering assets and optimizing within clusters for robust weight allocation.

---

## Type Definitions / Data Classes

### NCOConfig DataClass
```python
@dataclass(frozen=True)
class NCOConfig:
    n_clusters: int                           # REQUIRED - Number of clusters for K-means, default 5, min 2
    clustering_method: ClusteringMethod       # REQUIRED - 'kmeans' or 'dbscan', default KMEANS
    dbscan_eps: float                         # REQUIRED - Max distance for DBSCAN, default 0.5, must be > 0
    min_samples: int                          # REQUIRED - Min samples for DBSCAN neighborhood, default 2, min 1
    min_cluster_size: int                     # REQUIRED - Min assets for valid cluster, default 2, min 1
    max_weight_single_asset: float            # REQUIRED - Max weight per asset (0, 1], default 0.20
    risk_free_rate: float                     # REQUIRED - Risk-free rate for Sharpe, default 0.02
    random_state: int                         # REQUIRED - Random seed for reproducibility, default 42
```

**Validation Rules:**
- n_clusters >= 2 (need at least 2 clusters)
- dbscan_eps > 0 (distance must be positive)
- min_samples >= 1
- min_cluster_size >= 1
- max_weight_single_asset in (0, 1] (percentage)

### NCOResult DataClass
```python
@dataclass
class NCOResult:
    weights: NDArray[np.float64]                      # REQUIRED - Final optimized weights (N,)
    cluster_labels: NDArray[np.int32]                 # REQUIRED - Cluster assignment for each asset (N,)
    n_clusters: int                                   # REQUIRED - Number of clusters found
    expected_return: float                            # REQUIRED - Portfolio expected return (annualized)
    expected_risk: float                              # REQUIRED - Portfolio expected risk (annualized)
    sharpe_ratio: float                               # REQUIRED - Portfolio Sharpe ratio
    cluster_weights: NDArray[np.float64]              # REQUIRED - Weight per cluster (n_clusters,)
    within_cluster_weights: dict[int, NDArray]        # REQUIRED - cluster_id -> asset weights in cluster
    converged: bool                                   # REQUIRED - Whether optimization converged
```

**Validation Rules:**
- weights must sum to 1.0 (within tolerance)
- All weights >= 0 (long-only constraint)
- len(weights) == len(cluster_labels)
- n_clusters == len(cluster_weights)
- expected_risk > 0 for valid Sharpe calculation

---

## Function Signatures (Contracts)

### `NestedClusteredOptimization.__init__(config: NCOConfig | None) -> None`
**Pre:** config is None or valid NCOConfig
**Post:** NCO optimizer initialized with config or defaults
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `_correlation_to_distance(correlation_matrix: np.ndarray) -> np.ndarray`
**Pre:** correlation_matrix is symmetric (N, N) with values in [-1, 1]
**Post:** Returns distance matrix (N, N) with d = sqrt(0.5 * (1 - corr))
**Raises:** None
**Retry:** No
**Side Effects:** Sets self._last_distance_matrix

### `_covariance_to_correlation(cov_matrix: np.ndarray) -> np.ndarray`
**Pre:** cov_matrix is symmetric positive semi-definite (N, N)
**Post:** Returns correlation matrix with diagonal = 1.0
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_cluster_assets(cov_matrix: np.ndarray) -> NDArray[np.int32]`
**Pre:** cov_matrix is valid (N, N) with N >= n_clusters
**Post:** Returns cluster labels (N,) for each asset
**Raises:** ValueError if clustering method invalid
**Retry:** No
**Side Effects:** Logs warnings if < 2 clusters found

### `_cluster_kmeans(distance_matrix: np.ndarray, n_assets: int) -> NDArray[np.int32]`
**Pre:** distance_matrix is valid (N, N)
**Post:** Returns K-means cluster labels in range [0, n_clusters)
**Raises:** None
**Retry:** No
**Side Effects:** Uses sklearn KMeans with random_state

### `_cluster_dbscan(distance_matrix: np.ndarray) -> NDArray[np.int32]`
**Pre:** distance_matrix is valid precomputed distance matrix
**Post:** Returns DBSCAN labels where -1 = noise, >= 0 = cluster
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_optimize_within_cluster(expected_returns, cov_matrix, cluster_mask) -> np.ndarray`
**Pre:** expected_returns (N,), cov_matrix (N, N), cluster_mask (N,) boolean
**Post:** Returns optimal weights (N,) for cluster (zeros outside cluster)
**Raises:** None
**Retry:** No
**Side Effects:** Falls back to equal weights if optimization fails

### `_allocate_clusters(expected_returns, cov_matrix, cluster_labels) -> np.ndarray`
**Pre:** expected_returns (N,), cov_matrix (N, N), cluster_labels (N,)
**Post:** Returns cluster allocation weights (n_clusters,) using risk parity
**Raises:** None
**Retry:** No
**Side Effects:** Logs cluster allocation details

### `get_weights(expected_returns: np.ndarray, cov_matrix: np.ndarray) -> NCOResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) symmetric PSD, N >= 2
**Post:** Returns NCOResult with optimized weights, metrics, and cluster info
**Raises:** ValueError if inputs invalid or incompatible
**Retry:** No
**Side Effects:** Performs 3-step NCO: cluster, optimize within, allocate across

### `compute_nco_weights(expected_returns, cov_matrix, n_clusters, clustering_method, max_weight) -> np.ndarray`
**Pre:** expected_returns (N,), cov_matrix (N, N) valid, n_clusters >= 2
**Post:** Returns optimal weights (N,)
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** Creates NCO instance and calls get_weights

---

## Acceptance Criteria
- [ ] AC-NCO-001: Final weights sum to 1.0 (tolerance 1e-6)
- [ ] AC-NCO-002: All weights are non-negative (long-only)
- [ ] AC-NCO-003: No single asset weight exceeds max_weight_single_asset
- [ ] AC-NCO-004: Number of clusters >= 1 (after handling noise)
- [ ] AC-NCO-005: Distance matrix diagonal is 0.0 (self-distance)
- [ ] AC-NCO-006: Correlation matrix diagonal is 1.0
- [ ] AC-NCO-007: DBSCAN noise points (label -1) are handled
- [ ] AC-NCO-008: Within-cluster weights sum to 1.0 (within cluster)
- [ ] AC-NCO-009: Cluster allocations sum to 1.0
- [ ] AC-NCO-010: Sharpe ratio is finite (not NaN or inf)
- [ ] AC-NCO-011: Portfolio risk > 0 for non-zero variance portfolios

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance matrix must be positive semi-definite | ✅ OK - Assumed input |
| TRD-003 | BASE_RULES | Enforce max position size | ✅ OK - max_weight_single_asset constraint |
| ARCH-004 | BASE_RULES | Functions < 20 lines (ideally) | ❌ GAP - Some functions exceed (get_weights: 100+ lines) |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - Modern type hints throughout |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ❌ GAP - Limited error logging |
| TST-005 | BASE_RULES | Coverage > 80% | ⚠️ NOT APPLIED - Tests not yet written |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear variable names |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Separate methods for each step |

### López de Prado NCO-Specific Rules:

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| NCO-001 | Use correlation distance: d = sqrt(0.5 * (1 - corr)) | ✅ OK - _correlation_to_distance |
| NCO-002 | Cluster assets based on correlation distance | ✅ OK - _cluster_assets |
| NCO-003 | Optimize within each cluster separately | ✅ OK - _optimize_within_cluster |
| NCO-004 | Allocate across clusters using risk parity | ✅ OK - _allocate_clusters (inverse vol) |
| NCO-005 | Handle DBSCAN noise points appropriately | ✅ OK - Lines 582-589 |
| NCO-006 | Ensure weights sum to 1.0 after combining | ✅ OK - Lines 632-637 |
| NCO-007 | Use long-only constraints within clusters | ✅ OK - bounds [(0.0, max_weight)] |

---

## Dependencies
- **External:** numpy, scipy (optimize), sklearn (cluster: KMeans, DBSCAN)
- **Internal:** None (standalone domain module)

---

## Required Tests
- **tests/domain/portfolio_optimization/test_nested_clustered_optimization.py:**
  - Test get_weights with valid inputs (K-means clustering)
  - Test get_weights with DBSCAN clustering method
  - Test correlation to distance transformation formula
  - Test covariance to correlation conversion
  - Test K-means clustering with various n_clusters
  - Test DBSCAN clustering with noise points
  - Test within-cluster optimization with valid cluster
  - Test within-cluster optimization with small cluster (< min_cluster_size)
  - Test cluster allocation using risk parity
  - Test that final weights sum to 1.0
  - Test that all weights are non-negative
  - Test that max weight constraint is enforced
  - Test edge case: 2 assets only
  - Test edge case: All assets in single cluster
  - Test edge case: Each asset in separate cluster
  - Test NCOResult properties (get_weight_dict, get_cluster_summary, is_diversified)
  - Test error handling: mismatched expected_returns and cov_matrix dimensions
  - Test error handling: non-symmetric covariance matrix
  - Test compute_nco_weights convenience function
  - Test reproducibility with same random_state

---

## Notes
- NCO is López de Prado's answer to instability in traditional mean-variance optimization
- Clustering reduces dimensionality: optimizing within smaller groups is more stable
- Risk parity allocation across clusters avoids concentration in high-volatility clusters
- The correlation distance metric ensures assets with similar return patterns are grouped
- DBSCAN is useful when the number of clusters is unknown
- Consider adding validation for covariance matrix positive semi-definiteness
- Could add warm-start optimization to improve convergence speed
