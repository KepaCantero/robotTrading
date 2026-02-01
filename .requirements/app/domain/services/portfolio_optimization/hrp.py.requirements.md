# hrp.py

## Purpose
Implements Hierarchical Risk Parity (HRP) per López de Prado (2016) using hierarchical clustering and inverse variance allocation for robust portfolios without requiring invertible covariance matrices.

---

## Type Definitions / Data Classes

### HRPResult (dataclass)
```python
weights: np.ndarray                  # HRP weights (N,)
hierarchy: np.ndarray                # Linkage matrix from scipy
order: List[int]                     # Order of assets in hierarchy
clusters: Dict[str, List[int]]       # Cluster assignments
symbols: List[str]                   # Asset symbols
cophenetic_corr: float               # Quality of dendrogram preservation

@property
def weights_dict(self) -> Dict[str, float]:  # Get weights as dictionary
    return {symbol: float(weight) for symbol, weight in zip(self.symbols, self.weights)}
```

**Validation Rules:**
- weights must sum to 1.0
- All weights must be non-negative
- cophenetic_corr in [0, 1] (higher is better)

---

## Function Signatures (Contracts)

### `HierarchicalRiskParity.__init__(linkage_method, distance_metric)`
**Pre:** linkage_method in ['ward', 'single', 'complete', 'average'], distance_metric in ['euclidean', 'correlation']
**Post:** HRP optimizer initialized
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `optimize(cov_matrix, symbols) -> HRPResult`
**Pre:** cov_matrix is (N, N) PSD, symbols optional
**Post:** Returns HRPResult with optimal weights and hierarchy
**Raises:** ValueError if covariance validation fails
**Retry:** No
**Side Effects:** Logs cophenetic correlation warning if < 0.7

### `_cov_to_corr(cov_matrix) -> np.ndarray`
**Pre:** cov_matrix is (N, N)
**Post:** Returns correlation matrix with diagonal = 1.0
**Raises:** None
**Retry:** No
**Side Effects:** Warns if zero variance detected

### `_correlation_to_distance(corr_matrix) -> np.ndarray`
**Pre:** corr_matrix in [-1, 1]
**Post:** Returns distance matrix d = sqrt(0.5 * (1 - corr))
**Raises:** None
**Retry:** No
**Side Effects:** Clips correlation to [-1, 1]

### `get_dendrogram_data(cov_matrix) -> Tuple[np.ndarray, List[int]]`
**Pre:** cov_matrix is (N, N) PSD
**Post:** Returns (linkage_matrix, leaf_order) for plotting
**Raises:** ValueError if covariance invalid
**Retry:** No
**Side Effects:** None

### `inverse_variance_weights(cov_matrix) -> np.ndarray`
**Pre:** cov_matrix is (N, N)
**Post:** Returns inverse variance weights w_i ∝ 1/σ_i²
**Raises:** ValueError if all assets have zero variance
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Covariance matrix validated as PSD before clustering
- [ ] Correlation converted to distance: d = sqrt(0.5 * (1 - corr))
- [ ] Hierarchical clustering using scipy.linkage
- [ ] Linkage method validated (ward, single, complete, average)
- [ ] Bisectional allocation within clusters using inverse variance
- [ ] Weights sum to 1.0 (Rule 69)
- [ ] All weights non-negative (long-only, Rule 68)
- [ ] Cophenetic correlation calculated and logged if < 0.7
- [ ] Zero variance assets handled with MIN_VARIANCE_THRESHOLD
- [ ] Exception handling with structured logging
- [ ] Dendrogram data extractable for visualization

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance PSD validation | ✅ OK - validate_covariance_matrix() called |
| TRD-003 | BASE_RULES | Position limits enforced | ⚠️ NOT APPLIED - HRP naturally diversifies |
| TRD-007 | BASE_RULES | TRADING_DAYS=252 | ⚠️ NOT APPLIED - HRP works on any timescale |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - Only numpy/scipy imports |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All key steps logged |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ OK - log_optimization_failure() used |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - Full type hints |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Separate methods for clustering, allocation |

**Note:** HRP from López de Prado is designed to be robust without explicit position limits - the hierarchical structure naturally prevents extreme concentrations.

---

## Dependencies
- **External:** numpy, scipy (linkage, leaves_list, cophenet), logging
- **Internal:** app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_hrp.py:**
  - Covariance to correlation conversion
  - Correlation to distance conversion
  - Hierarchical clustering with ward linkage
  - Hierarchical clustering with single/complete/average linkage
  - Bisectional weight allocation
  - HRP weights calculation
  - Cophenetic correlation calculation
  - Low cophenetic correlation warning
  - Zero variance asset handling
  - Inverse variance weights function
  - Dendrogram data extraction
  - Complete HRP optimization pipeline
  - Cluster allocation extraction
  - HRPResult property methods

---

## Notes
HRP is robust to multicollinearity and doesn't require covariance invertibility. Uses bisectional allocation: split cluster, allocate by inverse variance, recurse. Cophenetic correlation > 0.7 indicates good dendrogram quality.
