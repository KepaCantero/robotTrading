# meta_labeling.py

## Purpose
Implements Marcos López de Prado's meta-labeling approach for financial ML, separating signal direction (primary model) from position sizing (meta-model) to improve risk-adjusted returns and reduce false positives.

---

## Type Definitions / Data Classes

### MetaLabelingConfig Class/DataClass
```python
@dataclass
class MetaLabelingConfig:
    primary_model_type: str              # REQUIRED - ML model type ('rf', 'xgb', 'lgb', 'logistic')
    primary_threshold: float = 0.5       # REQUIRED - Probability threshold [0,1]
    meta_model_type: str = "rf"          # REQUIRED - Meta-model type
    meta_threshold: float = 0.5          # REQUIRED - Meta-model threshold [0,1]
    bet_sizing_method: str = "kelly"     # REQUIRED - Method: 'kelly', 'probability', 'fixed'
    max_bet_size: float = 1.0            # REQUIRED - Maximum position [0,1]
    min_bet_size: float = 0.0            # REQUIRED - Minimum position [0, max_bet_size]
    use_purged_cv: bool = True           # OPTIONAL - Use purged cross-validation
    n_folds: int = 5                     # OPTIONAL - CV folds, must be > 0
    purge_pct: float = 0.05              # OPTIONAL - Purge percentage [0,1)
    embargo_pct: float = 0.02            # OPTIONAL - Embargo percentage [0,1)
    compute_importance: bool = True      # OPTIONAL - Calculate feature importance
    importance_method: str = "mdi"       # OPTIONAL - Method: 'mdi', 'mda', 'sfi'
```

**Validation Rules:**
- primary_threshold must be in [0, 1]
- meta_threshold must be in [0, 1]
- max_bet_size must be in [0, 1]
- min_bet_size must be in [0, max_bet_size]
- primary_model_type must be in ['rf', 'xgb', 'lgb', 'logistic']
- bet_sizing_method must be in ['kelly', 'probability', 'fixed']

### MetaLabelingResult Class/DataClass
```python
@dataclass
class MetaLabelingResult:
    primary_predictions: np.ndarray      # REQUIRED - Primary model predictions
    primary_proba: np.ndarray            # REQUIRED - Primary probabilities
    meta_predictions: np.ndarray         # REQUIRED - Meta-model predictions
    meta_proba: np.ndarray               # REQUIRED - Meta probabilities
    primary_accuracy: float              # REQUIRED - Primary model accuracy
    meta_accuracy: float                 # REQUIRED - Meta-model accuracy
    combined_accuracy: float             # REQUIRED - Combined accuracy
    bet_sizes: np.ndarray                # REQUIRED - Position sizes
    primary_importance: Dict[str, float] # OPTIONAL - Feature importance
    meta_importance: Dict[str, float]    # OPTIONAL - Meta importance
    n_samples: int = 0                   # OPTIONAL - Number of samples
    n_features: int = 0                  # OPTIONAL - Number of features
    timestamp: datetime = field(default_factory=datetime.now)
```

**Validation Rules:**
- All arrays must have same length (n_samples)
- Accuracy values must be in [0, 1]
- bet_sizes must be in [0, max_bet_size]

---

## Function Signatures (Contracts)

### `MetaLabeling.__init__(config: Optional[MetaLabelingConfig] = None) -> None`
**Pre:** config is None or valid MetaLabelingConfig
**Post:** Instance initialized with config, models set to None, _is_fitted=False
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `MetaLabeling.fit(X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], sample_weights: Optional[np.ndarray] = None) -> MetaLabeling`
**Pre:** X and y have same length > 0, X is 2D array
**Post:** Primary and meta models trained, _is_fitted=True, n_features_ set
**Raises:** ValueError if X and y length mismatch
**Retry:** No
**Side Effects:** Fits ML models, sets instance attributes

### `MetaLabeling.predict(X: Union[pd.DataFrame, np.ndarray]) -> MetaLabelingResult`
**Pre:** Model is fitted (_is_fitted=True), X is 2D array with n_features columns
**Post:** Returns MetaLabelingResult with predictions and bet_sizes
**Raises:** ValueError if model not fitted
**Retry:** No
**Side Effects:** None

### `MetaLabeling.fit_predict(X_train: Union[pd.DataFrame, np.ndarray], y_train: Union[pd.Series, np.ndarray], X_test: Union[pd.DataFrame, np.ndarray], y_test: Optional[Union[pd.Series, np.ndarray]] = None, sample_weights: Optional[np.ndarray] = None) -> MetaLabelingResult`
**Pre:** X_train and y_train have same length > 0, X_test has same features as X_train
**Post:** Returns MetaLabelingResult with accuracies calculated if y_test provided
**Raises:** ValueError on validation failures
**Retry:** No
**Side Effects:** Fits models, generates predictions

### `apply_meta_labeling(X_train: Union[pd.DataFrame, np.ndarray], y_train: Union[pd.Series, np.ndarray], X_test: Union[pd.DataFrame, np.ndarray], y_test: Optional[Union[pd.Series, np.ndarray]] = None, config: Optional[MetaLabelingConfig] = None) -> MetaLabelingResult`
**Pre:** X_train and y_train have same length, X_test has compatible shape
**Post:** Returns MetaLabelingResult with trained predictions
**Raises:** ValueError on input validation
**Retry:** No
**Side Effects:** Creates and fits MetaLabeling instance

### `calculate_meta_labels(primary_predictions: np.ndarray, actual_returns: np.ndarray, threshold: float = 0.0) -> np.ndarray`
**Pre:** primary_predictions and actual_returns have same length
**Post:** Returns binary meta-labels (1 if correct and profitable, 0 otherwise)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `snv_to_signal(side: np.ndarray, meta_labels: np.ndarray) -> np.ndarray`
**Pre:** side and meta_labels have same length
**Post:** Returns side * meta_labels (zeros out rejected trades)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All public functions have type hints (TYP-001)
- [ ] MetaLabelingConfig validates all parameters in __post_init__
- [ ] MetaLabeling.fit raises ValueError when X and y lengths differ
- [ ] MetaLabeling.predict raises ValueError when called before fit
- [ ] Bet sizes are clipped to [min_bet_size, max_bet_size]
- [ ] Meta-labels are binary (0 or 1)
- [ ] All models support predict() and predict_proba() methods
- [ ] Concurrent model training uses ProcessPoolExecutor for parallelism
- [ ] Feature importance extraction handles models without feature_importances_
- [ ] Kelly criterion produces positive bet sizes only when p > 0.5
- [ ] Fallback to RandomForest when XGBoost/LightGBM not available

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage for all functions | ⚠️ NOT APPLIED - Some functions lack return type hints |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ❌ GAP - Error logging in _create_model missing stack traces |
| ARCH-001 | BASE_RULES.md | Layered architecture respected | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ❌ GAP - Generic ValueError without context in some places |
| TRD-001 | BASE_RULES.md | Trading system validation | ❌ GAP - No validation that bet_sizes sum doesn't exceed capital |
| TRD-004 | BASE_RULES.md | Audit trail for trading decisions | ⚠️ NOT APPLIED - Logging present but not structured for audit |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - fit_predict separates train/test |
| PERF-002 | BASE_RULES.md | Use generators for large data | ⚠️ NOT APPLIED - Arrays fit in memory |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - MetaLabeling focuses on meta-labeling pipeline |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, sklearn, logging, dataclasses
- **Internal:** None (standalone module)

---

## Required Tests
- **tests/unit/backtesting/labeling/test_meta_labeling.py:**
  - Test MetaLabelingConfig validation (invalid thresholds, bet sizes)
  - Test MetaLabeling.fit with valid and invalid inputs
  - Test MetaLabeling.predict raises error when not fitted
  - Test meta-label generation accuracy
  - Test bet sizing methods (kelly, probability, fixed)
  - Test feature importance extraction
  - Test model fallback (XGBoost → RandomForest)
  - Test fit_predict with and without y_test
  - Test calculate_meta_labels with various thresholds
  - Test snv_to_signal multiplication
  - Test concurrent training edge cases

---

## Notes
Critical component for López de Prado's meta-labeling approach. Separates direction prediction from position sizing to reduce false positives and improve risk-adjusted returns.
