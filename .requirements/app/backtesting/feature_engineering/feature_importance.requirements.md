# feature_importance.py

## Purpose
Implements López de Prado's MDI, MDA, and SFI feature importance methods for financial ML model interpretability and feature selection.

---

## Type Definitions / Data Classes

### FeatureImportanceConfig DataClass
```python
@dataclass
class FeatureImportanceConfig:
    # Method selection
    compute_mdi: bool = True              # Compute Mean Decrease Impurity
    compute_mda: bool = True              # Compute Mean Decrease Accuracy
    compute_sfi: bool = False             # Compute Single Feature Importance (slow)

    # MDI settings
    mdi_normalize: bool = True            # Normalize importance scores to sum to 1
    mdi_min_samples: int = 10             # Minimum samples for importance calculation

    # MDA settings
    mda_n_repeats: int = 10               # Number of permutation repeats
    mda_scoring: str = "accuracy"         # Scoring metric: accuracy, f1, roc_auc, neg_mse, r2
    mda_n_jobs: int = -1                  # Parallel jobs (-1 = all CPUs)
    mda_random_state: int = 42            # Random seed for reproducibility

    # SFI settings
    sfi_n_splits: int = 5                 # Number of CV splits
    sfi_scoring: str = "accuracy"         # Scoring metric for SFI

    # General settings
    max_samples: int = 10000              # Subsample limit for large datasets
    feature_names: Optional[List[str]] = None  # Optional feature name list
```

**Validation Rules:**
- `mda_scoring`: Must be one of ["accuracy", "f1", "roc_auc", "neg_mse", "r2"]
- `mda_n_repeats`: Must be >= 1
- `max_samples`: Must be >= 1
- Validation in `__post_init__` raises ValueError for invalid scoring metric

### ImportanceResult DataClass
```python
@dataclass
class ImportanceResult:
    feature_names: List[str]                          # All feature names
    mdi_importance: Dict[str, float] = {}            # MDI scores by feature
    mda_importance: Dict[str, float] = {}            # MDA scores by feature
    sfi_importance: Dict[str, float] = {}            # SFI scores by feature

    # Rankings
    mdi_rank: Dict[str, int] = {}                    # MDI rank (1=highest)
    mda_rank: Dict[str, int] = {}                    # MDA rank
    sfi_rank: Dict[str, int] = {}                    # SFI rank

    # Combined
    combined_importance: Dict[str, float] = {}       # Average across methods
    combined_rank: Dict[str, int] = {}               # Combined ranking

    # Metadata
    n_features: int = 0                              # Number of features
    n_samples: int = 0                               # Number of samples
    methods_used: List[str] = []                     # Methods computed
    timestamp: datetime = field(default_factory=datetime.now)
```

**Methods:**
- `to_dict() -> Dict`: Convert result to dictionary
- `get_top_features(method: str = "combined", n: int = 10) -> List[str]`: Get top N features
- `get_low_importance_features(method: str = "combined", threshold: float = 0.01) -> List[str]`: Get features below threshold

---

## Function Signatures (Contracts)

### FeatureImportanceMDI.calculate(model: Any, feature_names: Optional[List[str]] = None) -> Dict[str, float]
**Pre:** Model has `feature_importances_` attribute (tree-based model)
**Post:** Returns dictionary mapping feature names to normalized MDI importance scores
**Raises:** No exception, returns empty dict if model incompatible
**Retry:** No
**Side Effects:** None (read-only access to model)

### FeatureImportanceMDA.calculate(model: Any, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, feature_names: Optional[List[str]] = None) -> Dict[str, float]
**Pre:** Model has `predict()` method, X and y have compatible dimensions
**Post:** Returns dictionary mapping feature names to MDA importance (normalized to sum to 1)
**Raises:** No explicit raises, handles prediction errors gracefully
**Retry:** No
**Side Effects:** Creates multiple shuffled copies of X for permutation testing

### FeatureImportanceMDA._score_model(model: Any, X: np.ndarray, y: np.ndarray) -> float
**Pre:** Model has `predict()` method, X and y are compatible
**Post:** Returns score based on configured metric (accuracy, f1, roc_auc, neg_mse, r2)
**Raises:** Falls back to accuracy for unsupported metrics
**Retry:** No
**Side Effects:** May call predict_proba for roc_auc

### FeatureImportanceSFI.calculate(X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, feature_names: Optional[List[str]] = None, model_type: Any = None) -> Dict[str, float]
**Pre:** X is 2D array/DataFrame, y is 1D array/Series
**Post:** Returns dictionary mapping feature names to SFI importance (normalized)
**Raises:** Catches exceptions, returns 0.0 importance for failed features
**Retry:** No
**Side Effects:** Trains separate model for each feature

### FinancialMLFeatureImportance.calculate_importance(model: Any, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, feature_names: Optional[List[str]] = None) -> ImportanceResult
**Pre:** Model trained on compatible X, y data
**Post:** Returns ImportanceResult with all requested importance methods
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Calls multiple importance calculators, logs progress

### FinancialMLFeatureImportance._create_ranking(importance: Dict[str, float]) -> Dict[str, int]
**Pre:** Importance dictionary is non-empty
**Post:** Returns ranking dict (1=highest importance)
**Raises:** No raises, returns empty dict if input empty
**Retry:** No
**Side Effects:** None (pure function)

### FinancialMLFeatureImportance._combine_importances(mdi: Dict[str, float], mda: Dict[str, float], sfi: Dict[str, float]) -> Dict[str, float]
**Pre:** At least one importance dict is non-empty
**Post:** Returns combined importance (average of available methods, normalized)
**Raises:** No raises
**Retry:** No
**Side Effects:** None (pure function)

### calculate_feature_importance(model: Any, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray, method: str = "combined", **kwargs) -> Dict[str, float]
**Pre:** Model trained, X and y compatible
**Post:** Returns importance dictionary for requested method
**Raises:** ValueError if method invalid (via config validation)
**Retry:** No
**Side Effects:** Creates config, calls calculator

---

## Acceptance Criteria
- [ ] All dataclasses have complete type annotations (TYP-001)
- [ ] MDI importance normalized to sum to 1.0
- [ ] MDA importance calculated via permutation (shuffling each feature)
- [ ] MDA repeats configured number of times (default: 10)
- [ ] SFI trains separate model for each feature
- [ ] Feature rankings computed correctly (1=highest importance)
- [ ] Combined importance averages available methods
- [ ] Low importance features filterable by threshold
- [ ] Top N features extractable by importance
- [ ] Result convertible to dictionary format
- [ ] Configuration validation catches invalid scoring metrics
- [ ] Models without feature_importances_ handled gracefully
- [ ] Subsampling applied for datasets > max_samples
- [ ] Multiple scoring metrics supported (accuracy, f1, roc_auc, neg_mse, r2)
- [ ] Random state ensures reproducible MDA results
- [ ] Logging provides progress updates for each method

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
| TYP-002 | BASE_RULES | Modern syntax (list[T], X \| None) | ✅ OK - Uses Union but consistent |
| TYP-003 | BASE_RULES | No Any without justification | ⚠️ PARTIAL - model: Any used appropriately |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Infrastructure layer (ML utilities) |
| ARCH-007 | BASE_RULES | Composition > inheritance | ✅ OK - FinancialMLFeatureImportance composes MDI/MDA/SFI |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Each class handles one importance method |
| DP-004 | BASE_RULES | Dependency injection | ✅ OK - Config injected via constructor |
| LOG-003 | BASE_RULES | Appropriate logging levels | ✅ OK - Uses logger.info for progress |
| CC-002 | BASE_RULES | DRY - No duplication | ✅ OK - Shared helper methods |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ PARTIAL - Some silent failures (MDI returns {}) |
| FMT-001 | BASE_RULES | Line length <= 100 | ✅ OK - Lines appear within limit |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - Uses default_factory for mutable defaults |
| TST-005 | BASE_RULES | Coverage > 80% | ❓ UNKNOWN - No test coverage data |

**Financial ML Specific Requirements:**
- López de Prado Chapter 8 methodology correctly implemented
- MDI: Mean Decrease Impurity from tree-based models
- MDA: Mean Decrease Accuracy via permutation importance
- SFI: Single Feature Importance via individual model training
- Multiple methods provide robust feature selection
- Importance scores normalized for comparison
- Rankings enable feature selection decisions

---

## Dependencies
- **External:**
  - numpy (array operations, random number generation)
  - pandas (DataFrame/Series handling)
  - sklearn (ensemble models, metrics: f1_score, roc_auc_score, r2_score)
  - dataclasses (dataclass, field)
  - datetime (timestamp tracking)
  - logging (progress logging)

- **Internal:** None (pure infrastructure/utility module)

---

## Required Tests
- **tests/backtesting/feature_engineering/test_feature_importance.py:**
  - Success paths:
    - Calculate MDI importance from RandomForest model
    - Calculate MDA importance with various scoring metrics
    - Calculate SFI importance for each feature
    - Combine multiple importance methods
    - Extract top N features
    - Filter low importance features by threshold
    - Convert result to dictionary
    - Convenience function with different methods
  - Error paths:
    - Model without feature_importances_ returns empty MDI
    - Invalid scoring metric raises ValueError in config
    - Empty X/y handling
    - Mismatched X and y dimensions
  - Edge cases:
    - Single feature dataset
    - Features with zero importance
    - All features have equal importance
    - max_samples triggers subsampling
    - Different model types (classifier vs regressor)
    - roc_auc without predict_proba falls back to accuracy
    - SFI model training failure (returns 0.0)
    - Random state reproducibility
  - Integration:
    - FinancialMLFeatureImportance with all methods enabled
    - Feature ranking consistency
    - Combined importance calculation

- **tests/backtesting/feature_engineering/test_feature_importance_mdi.py:**
  - MDI-specific tests:
    - Normalization sums to 1.0
    - Feature names from model.feature_names_in_
    - Feature names from parameter override model
    - Returns empty dict for unsupported models

- **tests/backtesting/feature_engineering/test_feature_importance_mda.py:**
  - MDA-specific tests:
    - Permutation decreases score for important features
    - Repeated shuffling produces stable results
    - Subsampling with max_samples
    - Different scoring metrics (accuracy, f1, roc_auc, neg_mse, r2)
    - Random state ensures reproducibility
    - Shuffling only affects target feature

- **tests/backtesting/feature_engineering/test_feature_importance_sfi.py:**
  - SFI-specific tests:
    - Trains separate model for each feature
    - Returns importance for each feature
    - Handles training failures gracefully
    - Normalization sums to 1.0

---

## Notes
- **MDI Bias:** MDI is biased toward high-cardinality features - use MDA for unbiased estimates
- **MDA Cost:** MDA is computationally expensive (n_repeats * n_features predictions)
- **SFI Cost:** SFI is very expensive (n_features model trainings) - disabled by default
- **Model Compatibility:** MDI requires tree-based models (RandomForest, GradientBoosting, etc.)
- **Permutation Importance:** MDA shuffles feature values to measure importance
- **Subsampling:** Datasets > max_samples are randomly subsampled for MDA performance
- **López de Prado Reference:** Chapter 8 of "Advances in Financial Machine Learning"
- **Feature Selection:** Use combined importance from multiple methods for robust selection
