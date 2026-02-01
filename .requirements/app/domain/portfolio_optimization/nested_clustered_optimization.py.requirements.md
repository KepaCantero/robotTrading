# nested_clustered_optimization.py

## Purpose
Implements Nested Clustered Optimization (NCO) per López de Prado (2019) to address MVO limitations by clustering assets and optimizing within clusters for robust portfolios.

---

## Type Definitions / Data Classes

### ClusteringMethod (Enum)
```python
KMEANS = "kmeans"  # K-means clustering with fixed n_clusters
DBSCAN = "dbscan"  # DBSCAN with automatic cluster detection
```

### NCOConfig (frozen dataclass)
```python
n_clusters: int = 5                        # Number of clusters for K-means
clustering_method: ClusteringMethod = KMEANS
dbscan_eps: float = 0.5                    # Max distance for DBSCAN
min_samples: int = 2                       # Min samples for DBSCAN neighborhood
min_cluster_size: int = 2                  # Min cluster size to be valid
max_weight_single_asset: float = 0.20      # Max weight per asset (Rule 70)
risk_free_rate: float = 0.02               # Risk-free rate
random_state: int = 42                     # Random seed for reproducibility
```

**Validation Rules:**
- n_clusters >= 2
- dbscan_eps > 0
- min_samples >= 1
- min_cluster_size >= 1
- max_weight_single_asset in (0, 1]

### NCOResult (dataclass)
```python
weights: NDArray[np.float64]                      # Final optimized weights (N,)
cluster_labels: NDArray[np.int32]                 # Cluster assignment (N,)
n_clusters: int                                   # Number of clusters
expected_return: float                            # Portfolio return
expected_risk: float                              # Portfolio risk
sharpe_ratio: float                               # Sharpe ratio
cluster_weights: NDArray[np.float64]              # Weight per cluster
within_cluster_weights: dict[int, NDArray]        # Cluster -> asset weights
converged: bool = True                            # Optimization converged
```

---

## Function Signatures (Contracts)

### `NestedClusteredOptimization.__init__(config)`
**Pre:** config valid or None for defaults
**Post:** NCO optimizer initialized
**Raises:** ValueError if config invalid
**Retry:** No
**Side Effects:** None

### `_correlation_to_distance(correlation_matrix) -> NDArray[np.float64]`
**Pre:** correlation_matrix is (N, N) in [-1, 1]
**Post:** Returns distance matrix d = sqrt(0.5 * (1 - corr))
**Raises:** None
**Retry:** No
**Side Effects:** Stores distance matrix in _last_distance_matrix

### `_cluster_assets(cov_matrix) -> NDArray[np.int32]`
**Pre:** cov_matrix is (N, N) PSD
**Post:** Returns cluster labels (N,) for each asset
**Raises:** ValueError if clustering method unknown
**Retry:** No
**Side Effects:** Logs clustering results

### `_optimize_within_cluster(expected_returns, cov_matrix, cluster_mask) -> NDArray[np.float64]`
**Pre:** expected_returns (N,), cov_matrix (N, N), cluster_mask (N,) boolean
**Post:** Returns optimal weights for assets in cluster (N,) with zeros elsewhere
**Raises:** None (falls back to equal weights on failure)
**Retry:** No
**Side Effects:** Logs optimization result

### `_allocate_clusters(expected_returns, cov_matrix, cluster_labels) -> NDArray[np.float64]`
**Pre:** expected_returns (N,), cov_matrix (N, N), cluster_labels (N,)
**Post:** Returns cluster weights (n_clusters,) via risk parity
**Raises:** None (returns equal weights on failure)
**Retry:** No
**Side Effects:** Logs allocation

### `get_weights(expected_returns, cov_matrix) -> NCOResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD, N >= 2
**Post:** Returns NCOResult with optimized weights
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** Logs complete NCO pipeline

---

## Acceptance Criteria
- [ ] Correlation converted to distance: d = sqrt(0.5 * (1 - corr))
- [ ] K-means clustering with n_clusters parameter
- [ ] DBSCAN clustering with eps and min_samples
- [ ] DBSCAN noise points assigned to separate clusters
- [ ] Within-cluster optimization uses mean-variance
- [ ] Cross-cluster allocation uses risk parity (inverse volatility)
- [ ] Final weights sum to 1.0 (Rule 69)
- [ ] All weights non-negative (long-only, Rule 68)
- [ ] Max 20% per asset constraint (Rule 70)
- [ ] Convergence check: weights >= 0 and sum ≈ 1.0
- [ ] Handles small clusters with equal weights
- [ ] Exception handling with detailed logging
- [ ] Structured logging (LOG-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance PSD validation | ✅ OK - Assumes PSD input |
| TRD-003 | BASE_RULES | Position limits (max 20%) | ✅ OK - max_weight_single_asset enforced |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All steps logged with context |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - Full type hints |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Separate methods for clustering, optimization, allocation |

---

## Dependencies
- **External:** numpy, scipy (minimize), sklearn (KMeans, DBSCAN), logging
- **Internal:** None (domain layer)

---

## Required Tests
- **test_nested_clustered_optimization.py:**
  - Correlation to distance conversion
  - Covariance to correlation conversion
  - K-means clustering
  - DBSCAN clustering
  - DBSCAN noise point handling
  - Within-cluster optimization
  - Small cluster equal weight fallback
  - Cross-cluster risk parity allocation
  - Complete NCO pipeline
  - Weight sum constraint validation
  - Convergence checking
  - NCOResult property methods (get_weight_dict, get_cluster_summary, is_diversified)
  - Configuration validation
  - Exception handling with logging
  - Convenience function compute_nco_weights

---

## Notes
NCO reduces dimensionality by clustering correlated assets, optimizing within clusters separately, then allocating across clusters using risk parity. This reduces estimation error impact compared to traditional MVO.
