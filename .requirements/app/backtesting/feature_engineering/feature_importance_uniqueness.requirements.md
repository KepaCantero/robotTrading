# feature_importance_uniqueness.py

## Purpose
Implements López de Prado's feature importance methods with sample uniqueness weighting to handle overlapping labels and correlated features in financial ML.

---

## Type Definitions / Data Classes

### UniquenessConfig DataClass
```python
@dataclass
class UniquenessConfig:
    # Uniqueness calculation
    uniqueness_method: str = "average"              # Method: average, concurrent, sequential
    overlap_threshold: float = 0.5                  # Minimum overlap to consider samples concurrent

    # MDI settings
    mdi_normalize: bool = True                      # Normalize importance scores
    mdi_min_weight: float = 0.01                    # Minimum sample weight

    # MDA settings
    mda_n_repeats: int = 10                         # Number of permutation repeats
    mda_uniqueness_correction: bool = True          # Apply uniqueness correction to MDA
    mda_scoring: str = "accuracy"                   # Scoring metric

    # SFI settings
    sfi_n_splits: int = 5                           # Number of CV splits
    sfi_purge_pct: float = 0.05                     # Purge percentage
    sfi_embargo_pct: float = 0.01                   # Embargo percentage

    # Feature clustering
    cluster_features: bool = True                   # Cluster correlated features
    correlation_threshold: float = 0.7              # Correlation threshold for clustering
    cluster_method: str = "hierarchical"            # Method: hierarchical, kmeans
```

**Validation Rules:**
- `uniqueness_method`: Must be one of ["average", "concurrent", "sequential"]
- `overlap_threshold`: Must be in [0, 1] range
- `correlation_threshold`: Must be in [0, 1] range
- Validation in `__post_init__` raises ValueError for invalid values

### UniquenessResult DataClass
```python
@dataclass
class UniquenessResult:
    feature_names: List[str]                        # All feature names

    # Importance scores
    mdi_importance: Dict[str, float] = {}           # MDI with uniqueness weighting
    mda_importance: Dict[str, float] = {}           # MDA with uniqueness correction
    sfi_importance: Dict[str, float] = {}           # SFI with uniqueness

    # Uniqueness information
    uniqueness_weights: np.ndarray = np.array([])   # Sample uniqueness weights
    avg_uniqueness: float = 0.0                     # Average uniqueness score

    # Feature clusters
    feature_clusters: Dict[str, List[str]] = {}     # Clustered features

    # Combined
    combined_importance: Dict[str, float] = {}      # Combined importance

    # Metadata
    n_samples: int = 0                              # Number of samples
    n_features: int = 0                             # Number of features
    methods_used: List[str] = []                    # Methods computed
    timestamp: datetime = field(default_factory=datetime.now)
```

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert result to dictionary

---

## Function Signatures (Contracts)

### UniquenessCalculator.calculate_average_uniqueness(events: pd.Series, labels: pd.DataFrame, price_series: pd.Series) -> np.ndarray
**Pre:** events and labels have same length, price_series contains event indices
**Post:** Returns array of uniqueness weights (normalized to sum to n_samples)
**Raises:** Catches KeyError/AttributeError, uses index fallback
**Retry:** No
**Side Effects:** None (pure calculation)

### UniquenessCalculator.calculate_concurrent_uniqueness(events: pd.Series, labels: pd.DataFrame) -> np.ndarray
**Pre:** events and labels have same length
**Post:** Returns array of uniqueness weights based on concurrent samples
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** None (pure calculation)

### MDIWithUniqueness.calculate(model: Any, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, events: pd.Series, labels: pd.DataFrame, feature_names: Optional[List[str]] = None) -> Dict[str, float]
**Pre:** Model has feature_importances_, events/labels have timing information
**Post:** Returns dictionary mapping features to uniqueness-weighted MDI importance
**Raises:** Returns empty dict if model incompatible
**Retry:** No
**Side Effects:** Calculates uniqueness weights, applies to importance

### MDAWithUniqueness.calculate(model: Any, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, events: pd.Series, labels: pd.DataFrame, feature_names: Optional[List[str]] = None) -> Dict[str, float]
**Pre:** Model has predict() method, X/y/events/labels compatible
**Post:** Returns dictionary mapping features to uniqueness-corrected MDA importance
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Creates multiple shuffled copies with weighting

### MDAWithUniqueness._score_model_weighted(model: Any, X: np.ndarray, y: np.ndarray, sample_weights: np.ndarray) -> float
**Pre:** Model has predict(), arrays compatible, weights sum > 0
**Post:** Returns weighted score based on configured metric
**Raises:** Falls back to weighted accuracy for unsupported metrics
**Retry:** No
**Side Effects:** Calls model.predict() and optionally predict_proba()

### FeatureClusterer.cluster_features(X: pd.DataFrame | np.ndarray, feature_names: Optional[List[str]] = None) -> Dict[str, List[str]]
**Pre:** X is 2D array/DataFrame with >= 1 feature
**Post:** Returns dictionary mapping cluster representatives to member features
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Computes correlation matrix

### FinancialMLFeatureImportanceWithUniqueness.calculate_importance(model: Any, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, events: pd.Series, labels: pd.DataFrame, feature_names: Optional[List[str]] = None) -> UniquenessResult
**Pre:** Model trained, X/y/events/labels compatible
**Post:** Returns UniquenessResult with uniqueness-weighted importance scores
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Calculates uniqueness, MDI, MDA, clusters, combines results

### FinancialMLFeatureImportanceWithUniqueness._combine_importances(mdi: Dict[str, float], mda: Dict[str, float]) -> Dict[str, float]
**Pre:** At least one importance dict is non-empty
**Post:** Returns combined importance (average of available methods, normalized)
**Raises:** No raises
**Retry:** No
**Side Effects:** None (pure function)

### calculate_feature_importance_with_uniqueness(model: Any, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, events: pd.Series, labels: pd.DataFrame, method: str = "combined", **kwargs) -> Dict[str, float]
**Pre:** Model trained, all inputs compatible
**Post:** Returns importance dictionary for requested method
**Raises:** ValueError if method invalid (via config validation)
**Retry:** No
**Side Effects:** Creates config and appropriate calculator

---

## Acceptance Criteria
- [ ] All dataclasses have complete type annotations (TYP-001)
- [ ] Uniqueness weights calculated based on sample overlap
- [ ] Average uniqueness normalized to sum to n_samples
- [ ] MDI importance weighted by sample uniqueness
- [ ] MDA importance corrected for overlap
- [ ] MDA uses weighted scoring with uniqueness weights
- [ ] Feature clustering groups correlated features
- [ ] Correlation threshold configurable (default: 0.7)
- [ ] Concurrent uniqueness calculates 1/(1+n_concurrent)
- [ ] Result includes uniqueness weights in output
- [ ] Result includes feature clusters
- [ ] Combined importance averages MDI and MDA
- [ ] Configuration validation checks uniqueness_method
- [ ] Configuration validation checks overlap_threshold in [0,1]
- [ ] Handles missing price_series index gracefully
- [ ] Falls back to index-based calculation for events
- [ ] Logging provides progress updates

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| TYP-003 | BASE_RULES | No Any without justification | ⚠️ PARTIAL - model: Any used appropriately |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Infrastructure layer (ML utilities) |
| ARCH-007 | BASE_RULES | Composition > inheritance | ✅ OK - Composes UniquenessCalculator, MDI, MDA, Clusterer |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Each class handles one aspect |
| DP-004 | BASE_RULES | Dependency injection | ✅ OK - Config injected via constructor |
| LOG-003 | BASE_RULES | Appropriate logging levels | ✅ OK - Uses logger.info for progress |
| CC-002 | BASE_RULES | DRY - No duplication | ✅ OK - Shared helper methods |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ PARTIAL - Some silent failures (MDI returns {}) |
| FMT-001 | BASE_RULES | Line length <= 100 | ✅ OK - Lines appear within limit |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - Uses default_factory for arrays/dicts |
| TST-005 | BASE_RULES | Coverage > 80% | ❓ UNKNOWN - No test coverage data |

**Financial ML Specific Requirements:**
- López de Prado Chapter 8 methodology with sample uniqueness
- Sample uniqueness accounts for overlapping labels
- MDI weighted by uniqueness reduces bias from common patterns
- MDA corrected for overlap prevents overestimation
- Feature clustering handles multicollinearity
- Uniqueness weights prevent overfitting to overlapping samples
- Average uniqueness = mean uniqueness across all samples
- Overlap threshold determines concurrency

**Key Concepts:**
- Financial ML samples are NOT independent (overlapping labels)
- High overlap = low uniqueness = lower weight
- Standard feature importance assumes i.i.d. samples (invalid for finance)
- Uniqueness weighting prevents overfitting to common patterns
- Feature clustering groups correlated features for robust importance

---

## Dependencies
- **External:**
  - numpy (array operations, random number generation)
  - pandas (DataFrame/Series handling, index alignment)
  - dataclasses (dataclass, field)
  - datetime (timestamp tracking)
  - logging (progress logging)

- **Internal:** None (pure infrastructure/utility module)

---

## Required Tests
- **tests/backtesting/feature_engineering/test_feature_importance_uniqueness.py:**
  - Success paths:
    - Calculate average uniqueness for overlapping samples
    - Calculate concurrent uniqueness
    - MDI importance with uniqueness weighting
    - MDA importance with uniqueness correction
    - Feature clustering by correlation
    - Combined importance with uniqueness
    - Result conversion to dictionary
    - Convenience function with different methods
  - Error paths:
    - Invalid uniqueness_method raises ValueError
    - Invalid overlap_threshold raises ValueError
    - Missing bars_to_barrier column uses default
    - Event index not in price_series uses fallback
  - Edge cases:
    - No overlap between samples (all weights = 1.0)
    - Complete overlap (all weights equal)
    - Single sample
    - High correlation threshold (no clustering)
    - Low correlation threshold (all features clustered)
    - Different uniqueness methods (average, concurrent, sequential)
    - Empty feature list
  - Integration:
    - Full pipeline with MDI + MDA + clustering
    - Uniqueness weights affect MDI importance
    - Uniqueness correction affects MDA importance
    - Feature clusters produced when correlation_threshold met

- **tests/backtesting/feature_engineering/test_uniqueness_calculator.py:**
  - Uniqueness calculation tests:
    - Average uniqueness with varying overlap
    - Normalization sums to n_samples
    - Handles missing price_series index
    - Uses default holding period when bars_to_barrier missing
    - Concurrent uniqueness calculation
    - Uniqueness matrix symmetry

- **tests/backtesting/feature_engineering/test_mdi_with_uniqueness.py:**
  - MDI-specific tests:
    - Weights importance by average uniqueness
    - Normalization when enabled
    - Returns empty dict for unsupported models
    - Handles missing feature_names_in_

- **tests/backtesting/feature_engineering/test_mda_with_uniqueness.py:**
  - MDA-specific tests:
    - Weighted scoring with uniqueness weights
    - Permutation respects sample weights
    - Different scoring metrics with weights
    - roc_auc with sample_weight parameter

- **tests/backtesting/feature_engineering/test_feature_clusterer.py:**
  - Clustering tests:
    - Groups features above correlation threshold
    - Returns clusters as dict of rep -> members
    - Handles correlation at boundary threshold
    - Uncorrelated features form single-feature clusters
    - Handles numpy and pandas input

---

## Notes
- **Sample Uniqueness:** Critical for financial ML where observations are not independent
- **Overlapping Labels:** Financial ML uses overlapping time windows (not i.i.d.)
- **Uniqueness Weight:** High overlap = low uniqueness = lower weight in importance
- **MDI Bias Reduction:** Uniqueness weighting reduces bias toward common patterns
- **MDA Correction:** Permutation importance adjusted for sample overlap
- **Feature Clustering:** Groups correlated features to handle multicollinearity
- **Concurrent Samples:** Samples active at the same time have reduced uniqueness
- **Default Holding Period:** Uses 5 bars when bars_to_barrier unavailable
- **Index Fallback:** Uses sequential index when event timestamps not in price_series
- **López de Prado Reference:** Chapter 8 of "Advances in Financial Machine Learning"
- **Unique Samples:** Prevents overfitting to patterns present in many overlapping samples
- **Cluster Representatives:** First feature in cluster becomes representative
