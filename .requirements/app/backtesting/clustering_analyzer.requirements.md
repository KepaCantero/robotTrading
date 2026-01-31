# clustering_analyzer.py

## Purpose
Advanced clustering and dimensionality reduction - hierarchical clustering with dendrograms, DBSCAN density-based clustering, PCA, ICA, t-SNE visualization, silhouette analysis, and optimal cluster detection.

---

## Type Definitions / Data Classes

None - uses sklearn transformers and clusterers, no custom dataclasses.

---

## Function Signatures (Contracts)

### `AdvancedClusteringAnalyzer.__init__(random_state: int = 42, n_jobs: int = -1) -> None`
**Pre:** `random_state` is non-negative integer; `n_jobs` is integer
**Post:** Analyzer initialized with StandardScaler for feature normalization
**Raises:** None
**Retry:** No
**Side Effects:** None (initialization only)

### `AdvancedClusteringAnalyzer.hierarchical_clustering(data: List[List[float]], n_clusters: int = 3, linkage_method: str = 'ward') -> Dict`
**Pre:** `data` has >= 2 samples; `n_clusters` >= 2; `linkage_method` in ['ward', 'complete', 'average', 'single']
**Post:** Returns dict with labels, linkage_matrix, silhouette_score, cluster_sizes
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** Fits StandardScaler and AgglomerativeClustering

### `AdvancedClusteringAnalyzer.dbscan_clustering(data: List[List[float]], eps: float = 0.5, min_samples: int = 5) -> Dict`
**Pre:** `data` has >= 2 samples; `eps` > 0; `min_samples` >= 1
**Post:** Returns dict with labels, n_clusters, n_noise_points, silhouette_score
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** Fits StandardScaler and DBSCAN

### `AdvancedClusteringAnalyzer.pca_analysis(data: List[List[float]], n_components: Optional[int] = None, variance_threshold: float = 0.95) -> Dict`
**Pre:** `data` has >= 2 samples; `variance_threshold` in (0, 1]
**Post:** Returns dict with n_components, explained_variance, cumulative_variance, components, transformed_data
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** Fits StandardScaler and PCA

### `AdvancedClusteringAnalyzer.ica_analysis(data: List[List[float]], n_components: Optional[int] = None, algorithm: str = 'parallel') -> Dict`
**Pre:** `data` has >= 2 samples; `algorithm` in ['parallel', 'deflation']
**Post:** Returns dict with n_components, mixing_matrix, unmixing_matrix, transformed_data
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** Fits StandardScaler and FastICA

### `AdvancedClusteringAnalyzer.tsne_visualization(data: List[List[float]], n_components: int = 2, perplexity: int = 30, n_iter: int = 1000) -> Optional[Dict]`
**Pre:** `data` has >= 2 samples; `n_components` in [2, 3]; `perplexity` > 0
**Post:** Returns dict with transformed_data (2D or 3D), kl_divergence, or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** Fits StandardScaler and TSNE

### `AdvancedClusteringAnalyzer.silhouette_analysis(data: List[List[float]], labels: List[int]) -> Dict`
**Pre:** `data` has >= 2 samples; `labels` has same length as `data`; >= 2 unique labels
**Post:** Returns dict with overall_score, cluster_scores, sample_scores, interpretation
**Raises:** Returns None on insufficient data or < 2 clusters
**Retry:** No
**Side Effects:** None (analysis only)

### `AdvancedClusteringAnalyzer.optimal_clusters(data: List[List[float]], k_range: Tuple[int, int] = (2, 10), method: str = 'silhouette') -> Dict`
**Pre:** `data` has >= 2 samples; `k_range`[0] >= 2; `method` in ['silhouette', 'elbow']
**Post:** Returns dict with optimal_k, scores for each k in range
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** Fits KMeans for each k in range

### `AdvancedClusteringAnalyzer._get_cluster_sizes(labels: List[int]) -> Dict[int, int]` (static)
**Pre:** `labels` is non-empty list
**Post:** Returns dict mapping label to count
**Raises:** None
**Retry:** No
**Side Effects:** None

### `AdvancedClusteringAnalyzer._interpret_silhouette(score: float) -> str` (static)
**Pre:** `score` in [-1, 1]
**Post:** Returns interpretation: ">0.7: Strong", ">0.5: Reasonable", ">0.25: Weak", else "No substantial"
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Hierarchical clustering uses AgglomerativeClustering with scipy linkage matrix
- [ ] DBSCAN handles noise points (label = -1) separately
- [ ] PCA automatically determines n_components from variance_threshold
- [ ] ICA returns mixing and unmixing matrices
- [ ] t-SNE supports 2D and 3D visualization with perplexity adjustment
- [ ] Silhouette analysis returns overall and per-cluster scores
- [ ] Optimal clusters supports silhouette and elbow methods
- [ ] All methods standardize features before clustering/transformation
- [ ] Silhouette score excludes noise points for DBSCAN
- [ ] t-SNE handles both old (n_iter) and new (max_iter) sklearn API
- [ ] Linkage methods: 'ward', 'complete', 'average', 'single'
- [ ] Elbow method finds maximum curvature point
- [ ] All methods return None on insufficient data
- [ ] Error handling with logging

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - try/except with logging |
| LOG-004 | BASE_RULES.md | Log all exceptions | ✅ OK - logger.error in except blocks |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods have hints |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each method does one analysis |
| ARCH-004 | BASE_RULES.md | Small functions | ✅ OK - Most methods < 20 lines |
| PERF-001 | BASE_RULES.md | Use efficient data structures | ✅ OK - List comprehensions used |
| DP-004 | BASE_RULES.md | Dependency injection | ⚠️ PARTIAL - random_state injected, n_jobs too |

**NOTE:** All 96 BASE_RULES apply. Critical for clustering:
- **CC-006:** Explicit error handling prevents sklearn crashes on invalid data
- **LOG-004:** Logging helps debug clustering failures (singular matrices, etc.)
- **PERF-001:** Efficient numpy operations enable scaling to large datasets
- **SOL-001:** Each method focuses on one clustering/reduction technique

---

## Dependencies
- **External:** `numpy`, `sklearn.cluster` (DBSCAN, AgglomerativeClustering), `sklearn.decomposition` (PCA, FastICA), `sklearn.manifold` (TSNE), `sklearn.metrics` (silhouette_samples, silhouette_score), `sklearn.preprocessing` (StandardScaler), `scipy.cluster.hierarchy` (linkage), `logging`, `typing` (Dict, List, Optional, Tuple)
- **Internal:** None (standalone analyzer)

---

## Required Tests
- **tests/backtesting/test_clustering_analyzer.py:**
  - Test hierarchical clustering with different linkage methods
  - Test hierarchical clustering linkage matrix generation
  - Test DBSCAN clustering with noise points
  - Test DBSCAN with varying eps and min_samples
  - Test PCA with variance_threshold auto-determination
  - Test PCA with explicit n_components
  - Test ICA returns mixing and unmixing matrices
  - Test t-SNE 2D visualization
  - Test t-SNE 3D visualization
  - Test t-SNE perplexity adjustment for small datasets
  - Test t-SNE handles both sklearn API versions (n_iter vs max_iter)
  - Test silhouette analysis overall and per-cluster scores
  - Test silhouette interpretation ranges
  - Test optimal clusters with silhouette method
  - Test optimal clusters with elbow method
  - Test _get_cluster_sizes static method
  - Test _interpret_silhouette static method
  - Test StandardScaler applied before all methods
  - Test insufficient data returns None
  - Test error handling and logging
  - Test DBSCAN noise points excluded from silhouette
  - Test elbow method finds maximum curvature

---

## Notes
- Module purpose: PHASE 4 MODULE 7 PHASE 3 of backtesting system
- Hierarchical clustering: agglomerative (bottom-up) with various linkage methods
  - Ward: minimizes variance within clusters
  - Complete: maximizes distance between clusters
  - Average: uses average distance between clusters
  - Single: uses minimum distance between clusters
- DBSCAN: density-based, finds arbitrary shapes, identifies noise (label -1)
- PCA: Principal Component Analysis, unsupervised dimensionality reduction
  - Finds orthogonal components that maximize variance
  - Auto-selects n_components to explain variance_threshold (default 95%)
- ICA: Independent Component Analysis, separates mixed signals
  - Returns mixing matrix (A) and unmixing matrix (W)
  - X = S @ A.T where S are independent components
- t-SNE: t-Distributed Stochastic Neighbor Embedding
  - Non-linear dimensionality reduction for visualization
  - Perplexity: balance between local and global structure (default 30)
  - KL divergence: measures information loss (lower is better)
- Silhouette score: measures cluster quality (-1 to 1, higher is better)
  - > 0.7: Strong structure
  - 0.5-0.7: Reasonable structure
  - 0.25-0.5: Weak structure
  - < 0.25: No substantial structure
- Optimal clusters: finds best k using silhouette or elbow method
  - Silhouette: maximize average silhouette score
  - Elbow: find point of maximum curvature in inertia plot
- All methods standardize features (zero mean, unit variance) first
- Static methods don't depend on fitted state
- Error handling: catch ValueError, TypeError, KeyError, AttributeError, return None, log error
