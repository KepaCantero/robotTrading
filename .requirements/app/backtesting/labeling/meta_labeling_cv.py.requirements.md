# meta_labeling_cv.py

## Purpose
Implements purged and embargoed cross-validation for meta-labeling in financial ML, preventing data leakage from overlapping labels and ensuring realistic out-of-sample performance estimates.

---

## Type Definitions / Data Classes

### CVConfig Class/DataClass
```python
@dataclass
class CVConfig:
    n_folds: int = 5                      # REQUIRED - Number of CV folds > 1
    shuffle: bool = False                 # REQUIRED - Never shuffle time series!
    purge_pct: float = 0.05               # REQUIRED - Purge percentage [0,1)
    embargo_pct: float = 0.01             # REQUIRED - Embargo percentage [0,1)
    meta_labeling: bool = True            # OPTIONAL - Meta-labeling mode
    primary_model_first: bool = True      # OPTIONAL - Train primary before meta
    is_timeseries: bool = True            # OPTIONAL - Time-series data
    timeseries_gap: int = 1               # OPTIONAL - Minimum gap between train/test
```

**Validation Rules:**
- n_folds must be > 1
- purge_pct must be in [0, 1)
- embargo_pct must be in [0, 1)
- shuffle must be False for time series
- timeseries_gap must be >= 0

### CVResult Class/DataClass
```python
@dataclass
class CVResult:
    fold_scores: List[float]              # REQUIRED - Score for each fold
    mean_score: float                     # REQUIRED - Mean score across folds
    std_score: float                      # REQUIRED - Standard deviation of scores
    fold_predictions: List[np.ndarray]    # REQUIRED - Predictions for each fold
    fold_labels: List[np.ndarray]         # REQUIRED - True labels for each fold
    train_indices: List[np.ndarray]       # REQUIRED - Training indices per fold
    test_indices: List[np.ndarray]        # REQUIRED - Test indices per fold
    metadata: Dict[str, Any]              # OPTIONAL - Additional metadata
    timestamp: datetime = field(default_factory=datetime.now)
```

**Validation Rules:**
- All lists must have same length (n_folds)
- All scores must be in valid range for metric (e.g., [0,1] for accuracy)
- std_score must be non-negative
- fold_predictions[i] and fold_labels[i] must have same length

---

## Function Signatures (Contracts)

### `PurgedKFold.__init__(n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01, timeseries_gap: int = 1) -> None`
**Pre:** n_folds > 1, percentages in [0,1), gap >= 0
**Post:** Instance initialized with CV parameters
**Raises:** None (validation deferred to split)
**Retry:** No
**Side Effects:** None

### `PurgedKFold.split(X: Union[pd.DataFrame, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, y: Optional[Union[pd.Series, np.ndarray]] = None) -> Tuple[np.ndarray, np.ndarray]`
**Pre:** X has length > 0, events and labels (if provided) have compatible lengths
**Post:** Yields (train_indices, test_indices) tuples with no overlap
**Raises:** None (skips folds with no training samples after purging)
**Retry:** No
**Side Effects:** None (pure generator)

### `PurgedKFold._apply_label_purge(train_mask: np.ndarray, test_start: int, test_end: int, events: pd.Series, labels: pd.DataFrame) -> np.ndarray`
**Pre:** train_mask is boolean array, labels has 'bars_to_barrier' column
**Post:** Returns updated train_mask with overlapping samples removed
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingCV.__init__(n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01, scoring: str = "accuracy") -> None`
**Pre:** n_folds > 1, percentages in [0,1), scoring is valid metric
**Post:** Instance initialized with PurgedKFold
**Raises:** None
**Retry:** No
**Side Effects:** Creates PurgedKFold instance

### `MetaLabelingCV.cross_validate(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, sample_weights: Optional[np.ndarray] = None) -> CVResult`
**Pre:** primary_model and meta_model implement fit() and predict(), X and y have same length > 0
**Post:** Returns CVResult with scores, predictions, and indices for all folds
**Raises:** None (errors within folds are logged)
**Retry:** No
**Side Effects:** Fits models on each fold

### `MetaLabelingCV._calculate_score(y_true: np.ndarray, primary_pred: np.ndarray, meta_pred: np.ndarray) -> float`
**Pre:** Arrays have same length
**Post:** Returns score based on self.scoring metric
**Raises:** None (handles ValueError for single-class ROC AUC)
**Retry:** No
**Side Effects:** None

### `SequentialBootstrap.__init__(n_splits: int = 5, test_size: float = 0.2, gap: int = 1) -> None`
**Pre:** n_splits > 0, test_size in (0,1), gap >= 0
**Post:** Instance initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SequentialBootstrap.split(X: Union[pd.DataFrame, np.ndarray], y: Optional[Union[pd.Series, np.ndarray]] = None) -> Tuple[np.ndarray, np.ndarray]`
**Pre:** X has length > 0
**Post:** Yields sequential train/test splits respecting time order
**Raises:** None (skips invalid splits)
**Retry:** No
**Side Effects:** None

### `cv_score_meta_labeling(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01, scoring: str = "accuracy") -> Dict[str, float]`
**Pre:** Models are fitted-compatible, X and y have same length
**Post:** Returns dict with 'mean', 'std', 'scores' keys
**Raises:** ValueError on invalid parameters
**Retry:** No
**Side Effects:** Creates MetaLabelingCV and runs cross-validation

### `calculate_purge_embargo_sizes(n_samples: int, n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01) -> Dict[str, int]`
**Pre:** n_samples > 0, n_folds > 1, percentages in [0,1)
**Post:** Returns dict with 'fold_size', 'purge_size', 'embargo_size', 'train_size_per_fold'
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All public functions have complete type hints (TYP-001)
- [ ] CVConfig validates n_folds > 1 and percentages in [0,1)
- [ ] PurgedKFold never shuffles time series (shuffle=False)
- [ ] Train and test indices have no overlap after purging
- [ ] Embargo period applied after test set
- [ ] Label purge removes samples with overlapping holding periods
- [ ] MetaLabelingCV trains primary model before meta-model
- [ ] All scoring metrics handle edge cases (single class, empty predictions)
- [ ] SequentialBootstrap respects time ordering (no future in train)
- [ ] Gap applied between train and test in SequentialBootstrap
- [ ] CVResult contains correct number of folds
- [ ] Fold scores are within valid metric range
- [ ] train_indices and test_indices have correct lengths

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage for all functions | ⚠️ NOT APPLIED - Some private methods lack hints |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - Purging prevents leakage |
| BT-001 | BASE_RULES.md | Walk-forward validation | ✅ OK - Sequential implementation |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ PARTIAL - Logs warnings but no stack traces |
| ARCH-004 | BASE_RULES.md | Small functions | ❌ GAP - _apply_label_purge is 47 lines |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ PARTIAL - Handles ValueError but could be more specific |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Separate classes for different CV methods |
| TRD-004 | BASE_RULES.md | Audit trail | ⚠️ NOT APPLIED - CV results logged but not structured |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, sklearn (for metrics), logging, dataclasses
- **Internal:** None (standalone module)

---

## Required Tests
- **tests/unit/backtesting/labeling/test_meta_labeling_cv.py:**
  - Test CVConfig validation for all parameters
  - Test PurgedKFold.split generates non-overlapping splits
  - Test PurgedKFold applies embargo period correctly
  - Test PurgedKFold._apply_label_purge removes overlapping samples
  - Test MetaLabelingCV.cross_validate trains primary then meta
  - Test MetaLabelingCV scoring metrics (accuracy, f1, roc_auc)
  - Test MetaLabelingCV handles single-class edge case
  - Test SequentialBootstrap respects time ordering
  - Test SequentialBootstrap applies gap correctly
  - Test cv_score_meta_labeling returns correct dict structure
  - Test calculate_purge_embargo_sizes calculates correctly
  - Test CV with and without events/labels
  - Test empty edge case handling

---

## Notes
Implements López de Prado's purged CV for financial ML. Critical for preventing look-ahead bias from overlapping labels. The embargo period adds additional safety after test sets. Sequential bootstrap maintains time-series properties.
