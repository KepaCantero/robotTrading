# meta_labeling_cv.py

## Purpose
Implements purged and embargoed cross-validation specifically designed for meta-labeling in financial ML to prevent data leakage from overlapping labels.

---

## Type Definitions / Data Classes

### CVConfig
```python
@dataclass
class CVConfig:
    n_folds: int = 5                         # REQUIRED - Range [2, inf], number of CV folds
    shuffle: bool = False                    # REQUIRED - Must be False for time series (never shuffle!)
    purge_pct: float = 0.05                  # REQUIRED - Range [0, 1), percentage to purge from training
    embargo_pct: float = 0.01                # REQUIRED - Range [0, 1), percentage to embargo after test
    meta_labeling: bool = True               # REQUIRED - Enable meta-labeling specific logic
    primary_model_first: bool = True         # REQUIRED - Train primary model before meta-model
    is_timeseries: bool = True               # REQUIRED - Data is time series (affects split logic)
    timeseries_gap: int = 1                  # REQUIRED - Range [1, inf], minimum gap between train and test
```

**Validation Rules:**
- n_folds must be >= 2
- shuffle must be False for time series (critical!)
- purge_pct must be in [0, 1)
- embargo_pct must be in [0, 1)
- timeseries_gap must be >= 1

### CVResult
```python
@dataclass
class CVResult:
    fold_scores: List[float]                 # REQUIRED - Score for each fold
    mean_score: float                        # REQUIRED - Mean score across folds
    std_score: float                         # REQUIRED - Standard deviation of scores
    fold_predictions: List[np.ndarray]       # REQUIRED - Predictions for each fold
    fold_labels: List[np.ndarray]            # REQUIRED - True labels for each fold
    train_indices: List[np.ndarray]          # REQUIRED - Training indices for each fold
    test_indices: List[np.ndarray]           # REQUIRED - Test indices for each fold
    metadata: Dict[str, Any]                 # OPTIONAL - Additional metadata
    timestamp: datetime                      # AUTO - Result timestamp
```

**Validation Rules:**
- All lists must have length == n_folds
- mean_score must equal mean(fold_scores)
- std_score must equal std(fold_scores)
- All arrays in fold_predictions must have same length as corresponding fold_labels

---

## Function Signatures (Contracts)

### `PurgedKFold.__init__(n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01, timeseries_gap: int = 1) -> None`
**Pre:** n_folds >= 2, purge_pct and embargo_pct in [0, 1), timeseries_gap >= 1
**Post:** CV splitter initialized with purging parameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `PurgedKFold.split(X: Union[pd.DataFrame, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, y: Optional[Union[pd.Series, np.ndarray]] = None) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]`
**Pre:** X has n_samples, events/labels/y have compatible indices if provided
**Post:** Yields (train_indices, test_indices) for each fold with purging applied
**Raises:** None
**Retry:** No
**Side Effects:** None (generator)

### `PurgedKFold._apply_label_purge(train_mask: np.ndarray, test_start: int, test_end: int, events: pd.Series, labels: pd.DataFrame) -> np.ndarray`
**Pre:** train_mask is boolean array, labels has 'bars_to_barrier' column
**Post:** Returns train_mask with overlapping samples removed
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingCV.__init__(n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01, scoring: str = "accuracy") -> None`
**Pre:** n_folds >= 2, purge_pct and embargo_pct in [0, 1), scoring in ['accuracy', 'f1', 'roc_auc']
**Post:** Meta-labeling CV initialized
**Raises:** ValueError for invalid scoring method
**Retry:** No
**Side Effects:** Creates internal PurgedKFold instance

### `MetaLabelingCV.cross_validate(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, sample_weights: Optional[np.ndarray] = None) -> CVResult`
**Pre:** Models are scikit-learn compatible, X and y have same length
**Post:** Returns CVResult with fold scores and predictions
**Raises:** ValueError on input mismatch, RuntimeError on model training failure
**Retry:** No
**Side Effects:** Trains both models on each fold

### `MetaLabelingCV._calculate_score(y_true: np.ndarray, primary_pred: np.ndarray, meta_pred: np.ndarray) -> float`
**Pre:** Arrays have same length
**Post:** Returns score based on configured scoring metric
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SequentialBootstrap.__init__(n_splits: int = 5, test_size: float = 0.2, gap: int = 1) -> None`
**Pre:** n_splits >= 2, test_size in (0, 1), gap >= 1
**Post:** Sequential bootstrap initialized
**Raises:** ValueError for invalid parameters
**Retry:** No
**Side Effects:** None

### `SequentialBootstrap.split(X: Union[pd.DataFrame, np.ndarray], y: Optional[Union[pd.Series, np.ndarray]] = None) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]`
**Pre:** X has n_samples
**Post:** Yields sequential (train_indices, test_indices) maintaining time order
**Raises:** None
**Retry:** No
**Side Effects:** None (generator)

### `cv_score_meta_labeling(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], events: Optional[pd.Series] = None, labels: Optional[pd.DataFrame] = None, n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01, scoring: str = "accuracy") -> Dict[str, float]`
**Pre:** Models fitted or compatible, X and y have same length
**Post:** Returns dict with 'mean', 'std', 'scores' keys
**Raises:** ValueError on invalid inputs
**Retry:** No
**Side Effects:** None (pure function)

### `calculate_purge_embargo_sizes(n_samples: int, n_folds: int = 5, purge_pct: float = 0.05, embargo_pct: float = 0.01) -> Dict[str, int]`
**Pre:** n_samples > 0, n_folds >= 2, percentages in [0, 1)
**Post:** Returns dict with 'fold_size', 'purge_size', 'embargo_size', 'train_size_per_fold'
**Raises:** ValueError for invalid parameters
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] PurgedKFold never shuffles data (shuffle=False for time series)
- [ ] PurgedKFold removes training samples overlapping with test set
- [ ] PurgedKFold applies embargo period after each test fold
- [ ] PurgedKFold handles label overlap via bars_to_barrier column
- [ ] MetaLabelingCV trains primary model first, then meta-model
- [ ] MetaLabelingCV generates meta-labels from training predictions
- [ ] MetaLabelingCV supports accuracy, f1, and roc_auc scoring
- [ ] Combined accuracy only counts samples where meta_pred == 1
- [ ] SequentialBootstrap maintains time ordering (no future data in training)
- [ ] SequentialBootstrap respects gap between train and test
- [ ] cv_score_meta_labeling returns mean, std, and individual scores
- [ ] calculate_purge_embargo_sizes returns correct integer sizes

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK |
| BT-001 | BASE_RULES | Walk-forward validation | ✅ OK - SequentialBootstrap implements |
| BT-002 | BASE_RULES | Out-of-sample testing | ✅ OK - PurgedKFold ensures OOS |
| BT-003 | BASE_RULES | No look-ahead bias | ✅ OK - Purging prevents leakage |
| ARCH-004 | BASE_RULES | Small functions | ⚠️ PARTIAL - Some methods > 20 lines (split, cross_validate) |
| TST-005 | BASE_RULES | Coverage > 80% | ❌ GAP - No test coverage documented |
| QL-007 | BASE_RULES | Max 7 parameters | ✅ OK - All methods within limit |

**Cross-Validation Specific Rules:**
- CV-001: NEVER shuffle time series data (shuffle must be False)
- CV-002: Purge period must remove samples with labels overlapping test set
- CV-003: Embargo period must add buffer after test set
- CV-004: Meta-labeling CV must train primary model before meta-model
- CV-005: Meta-labels must be generated from primary model predictions on training set
- CV-006: Sequential splits must maintain time order (no future in training)
- CV-007: Folds with no training samples after purging should be skipped with warning

---

## Dependencies
- **External:** numpy, pandas, scikit-learn
- **Internal:** None (standalone CV module)

---

## Required Tests
- **tests/backtesting/labeling/test_meta_labeling_cv.py:**
  - Test CVConfig validation (n_folds, shuffle, percentages)
  - Test PurgedKFold.split generates correct folds
  - Test PurgedKFold applies purge period correctly
  - Test PurgedKFold applies embargo period correctly
  - Test PurgedKFold._apply_label_purge removes overlapping samples
  - Test PurgedKFold skips folds with no training samples
  - Test MetaLabelingCV.cross_validate end-to-end
  - Test MetaLabelingCV trains primary then meta-model
  - Test MetaLabelingCV scoring (accuracy, f1, roc_auc)
  - Test MetaLabelingCV combined accuracy calculation
  - Test SequentialBootstrap.split maintains time order
  - Test SequentialBootstrap respects gap parameter
  - Test cv_score_meta_labeling returns correct dict structure
  - Test calculate_purge_embargo_sizes computes correct sizes
  - Test CVResult.to_dict serialization
  - Test generator pattern for split methods

---

## Notes
Based on Marcos López de Prado "Advances in Financial Machine Learning" Chapter 4. CRITICAL: Standard K-Fold CV is INVALID for financial time series due to label overlap (trades have different durations). Purged CV removes training samples whose labels overlap with test period. Embargo adds additional buffer to prevent leakage. Meta-labeling CV requires special handling: train primary model, generate meta-labels, then train meta-model.
