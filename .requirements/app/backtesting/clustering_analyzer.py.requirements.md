# clustering_analyzer.py

## Purpose
Advanced clustering and dimensionality reduction techniques for financial data analysis, including hierarchical clustering, DBSCAN, PCA, ICA, t-SNE, and silhouette analysis.

---

## Type Definitions / Data Classes

### AdvancedClusteringAnalyzer State
```python
random_state: int              # Random seed for reproducibility (default: 42)
n_jobs: int                    # Parallel jobs (-1 = all CPUs)
scaler: StandardScaler         # Feature standardization
```

**Validation Rules:**
- `random_state` must be positive integer (typically 42)
- `n_jobs = -1` uses all available CPU cores
- All methods require at least 2 data points

---

## Function Signatures (Contracts)

### `__init__(random_state: int = 42, n_jobs: int = -1)`
**Pre:** random_state >= 0
**Post:** ClusteringAnalyzer initialized with StandardScaler
**Raises:** No
**Retry:** No
**Side Effects:** Creates StandardScaler instance

### `hierarchical_clustering(data, n_clusters, linkage_method) -> Dict`
**Pre:** data is list of lists with len(data) >= 2, n_clusters >= 2
**Post:** Returns dict with labels, linkage_matrix, silhouette_score
**Raises:** No - returns None on error with logged message
**Retry:** No
**Side Effects:** Fits StandardScaler to data

### `dbscan_clustering(data, eps, min_samples) -> Dict`
**Pre:** data has len(data) >= 2, eps > 0, min_samples >= 1
**Post:** Returns dict with labels, n_clusters, n_noise_points
**Raises:** No - returns None on error with logged message
**Retry:** No
**Side Effects:** Fits StandardScaler to data

### `pca_analysis(data, n_components, variance_threshold) -> Dict`
**Pre:** data has len(data) >= 2, variance_threshold in (0, 1]
**Post:** Returns dict with explained_variance, components, transformed_data
**Raises:** No - returns None on error with logged message
**Retry:** No
**Side Effects:** Fits StandardScaler and PCA to data

### `ica_analysis(data, n_components, algorithm) -> Dict`
**Pre:** data has len(data) >= 2, algorithm in ['parallel', 'deflation']
**Post:** Returns dict with mixing_matrix, independent_components
**Raises:** No - returns None on error with logged message
**Retry:** No
**Side Effects:** Fits StandardScaler and FastICA to data

### `tsne_visualization(data, n_components, perplexity, n_iter) -> Optional[Dict]`
**Pre:** data has len(data) >= 2, n_components in [2, 3], perplexity > 0
**Post:** Returns dict with transformed_data, kl_divergence or None on error
**Raises:** No - logs error and returns None
**Retry:** No
**Side Effects:** Fits StandardScaler and TSNE to data

### `silhouette_analysis(data, labels) -> Dict`
**Pre:** data has len(data) >= 2, labels has same length as data, >= 2 unique labels
**Post:** Returns dict with overall_score, cluster_scores, interpretation
**Raises:** No - returns None on error with logged message
**Retry:** No
**Side Effects:** Fits StandardScaler to data

### `optimal_clusters(data, k_range, method) -> Dict`
**Pre:** data has len(data) >= 2, k_range is (min_k, max_k) with max_k <= len(data) - 1
**Post:** Returns dict with optimal_k, scores for each k
**Raises:** No - returns None on error with logged message
**Retry:** No
**Side Effects:** Fits multiple KMeans models

### `_get_cluster_sizes(labels) -> Dict[int, int]`
**Pre:** labels is non-empty list
**Post:** Returns dict mapping label -> count
**Raises:** No
**Retry:** No
**Side Effects:** No external state changes

### `_interpret_silhouette(score) -> str`
**Pre:** score is float
**Post:** Returns interpretation string
**Raises:** No
**Retry:** No
**Side Effects:** No external state changes

---

## Acceptance Criteria
- [ ] Hierarchical clustering returns valid labels and linkage matrix
- [ ] DBSCAN identifies noise points (-1 label)
- [ ] PCA explains at least variance_threshold of variance
- [ ] ICA returns mixing and unmixing matrices
- [ ] t-SNE handles both 2D and 3D visualization
- [ ] t-SNE adjusts perplexity if too large for dataset
- [ ] Silhouette score between -1 and 1
- [ ] Silhouette interpretation correct (>0.7 strong, >0.5 reasonable, >0.25 weak)
- [ ] Optimal clusters uses silhouette or elbow method
- [ ] All methods handle insufficient data gracefully (return None)
- [ ] All methods log errors instead of raising
- [ ] StandardScaler applied to all data before analysis
- [ ] Random state ensures reproducibility
- [ ] n_jobs=-1 enables parallel execution

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK - try/except with logging |
| LOG-004 | 09-logging-observability.md | All exceptions logged | ✅ OK - All errors logged |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK - Clear method names |
| ARCH-001 | 05-architecture.md | Layered architecture | ✅ OK - Analysis component |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Only clustering analysis |
| TST-005 | 06-testing.md | Coverage > 80% | ⚠️ NOT APPLIED - Not measured |
| SEC-001 | 28-security-and-secrets.md | No hardcoded secrets | ✅ OK - No secrets |
| PERF-006 | 20-sre-site-reliability-engineering.md | Async I/O | ⚠️ NOT APPLIED - CPU-bound work |

**GAP Analysis:**
- No critical gaps - well-structured analysis module
- Comprehensive error handling with logging
- Clear separation of concerns
- Defensive programming (returns None on errors)

---

## Dependencies
- **External:**
  - `numpy` - Numerical operations
  - `sklearn.cluster.AgglomerativeClustering, DBSCAN` - Clustering algorithms
  - `sklearn.cluster.KMeans` - For optimal_clusters
  - `sklearn.decomposition.PCA, FastICA` - Dimensionality reduction
  - `sklearn.manifold.TSNE` - Visualization
  - `sklearn.metrics.silhouette_score, silhouette_samples` - Cluster quality
  - `sklearn.preprocessing.StandardScaler` - Feature scaling
  - `scipy.cluster.hierarchy.linkage` - Hierarchical clustering linkage matrix
  - `logging` - Structured logging
  - `typing` - Type hints (Dict, List, Optional, Tuple)
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/test_clustering_analyzer.py:**
  - `test_hierarchical_clustering_valid` - Returns valid clustering results
  - `test_hierarchical_clustering_insufficient_data` - Returns None for < 2 samples
  - `test_hierarchical_clustering_linkage_matrix` - Returns scipy linkage matrix
  - `test_dbscan_clustering_identifies_noise` - Labels noise as -1
  - `test_dbscan_clustering_returns_cluster_count` - Returns n_clusters excluding noise
  - `test_pca_analysis_variance_threshold` - Explains at least threshold variance
  - `test_pca_analysis_explained_variance` - Returns cumulative variance
  - `test_ica_analysis_mixing_matrix` - Returns mixing and unmixing matrices
  - `test_ica_analysis_independent_components` - Returns ICA transformed data
  - `test_tsne_visualization_2d` - Returns 2D visualization
  - `test_tsne_visualization_3d` - Returns 3D visualization
  - `test_tsne_adjusts_perplexity` - Reduces perplexity if too large
  - `test_tsne_handles_sklearn_version` - Works with old and new sklearn API
  - `test_silhouette_analysis_score_range` - Score between -1 and 1
  - `test_silhouette_analysis_cluster_scores` - Returns per-cluster scores
  - `test_silhouette_interpretation` - Correct interpretation strings
  - `test_silhouette_requires_2_clusters` - Returns None for < 2 unique labels
  - `test_optimal_clusters_silhouette` - Uses silhouette method
  - `test_optimal_clusters_elbow` - Uses elbow method
  - `test_optimal_clusters_k_range` - Tests k in specified range
  - `test_get_cluster_sizes` - Returns correct counts
  - `test_interpret_silhouette` - Returns correct interpretation
  - `test_random_state_reproducibility` - Same input produces same output
  - `test_standardizer_applied` - Data is standardized before analysis
  - `test_error_handling_returns_none` - Errors return None with log

---

## Notes
- **PHASE 4 MODULE 7 PHASE 3:** Advanced clustering for market analysis
- **Reproducibility:** random_state=42 ensures consistent results
- **Parallel Execution:** n_jobs=-1 uses all CPU cores
- **Feature Scaling:** StandardScaler applied to all data before analysis
- **Error Handling:** All methods return None on error (defensive)
- **t-SNE Compatibility:** Handles both old (n_iter) and new (max_iter) sklearn API
- **Perplexity Adjustment:** Auto-adjusts if perplexity >= n_samples / 3
- **Silhouette Interpretation:**
  - > 0.7: Strong structure
  - > 0.5: Reasonable structure
  - > 0.25: Weak structure
  - <= 0.25: No substantial structure
