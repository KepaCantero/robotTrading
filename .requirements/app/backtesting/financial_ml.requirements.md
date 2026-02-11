# financial_ml.py

## Purpose
Comprehensive Financial ML pipeline integrating all López de Prado methods: fractional differentiation, triple barrier labeling, purged K-fold CV, meta-labeling, bet sizing, and feature importance.

---

## Type Definitions / Data Classes

### FinancialMLConfig
```python
@dataclass
class FinancialMLConfig:
    # Fractional Differentiation
    fracdiff_threshold: float = 1e-5          # REQUIRED - Convergence threshold
    fracdiff_adfuller_alpha: float = 0.05    # REQUIRED - Stationarity test p-value
    apply_fracdiff: bool = True              # OPTIONAL - Enable fractional diff

    # Triple Barrier
    upper_barrier_pct: float = 0.02          # REQUIRED - Upper barrier (2%)
    lower_barrier_pct: float = -0.01         # REQUIRED - Lower barrier (-1%)
    vertical_barrier_days: int = 5           # REQUIRED - Time barrier (days)
    vol_scaling: bool = True                 # OPTIONAL - Volatility scaling

    # Purged K-Fold CV
    use_purged_cv: bool = True               # OPTIONAL - Use purged CV
    n_folds: int = 5                         # REQUIRED - Number of CV folds
    purge_pct: float = 0.05                  # REQUIRED - Purge period (5%)
    embargo_pct: float = 0.02                # REQUIRED - Embargo period (2%)

    # Meta-labeling
    use_meta_labeling: bool = True           # OPTIONAL - Enable meta-labeling
    primary_model_type: str = "rf"           # REQUIRED - Primary model (rf/logistic)
    meta_model_type: str = "rf"              # REQUIRED - Meta model type

    # Bet Sizing
    bet_sizing_method: str = "kelly"         # REQUIRED - kelly/fixed
    kelly_fraction: float = 0.25             # REQUIRED - Kelly fraction (0-1)
    max_bet_size: float = 1.0                # REQUIRED - Maximum bet size

    # Feature Importance
    compute_importance: bool = True          # OPTIONAL - Compute feature importance
    importance_method: str = "combined"      # REQUIRED - mdi/mda/sfi/combined

    # General
    random_state: int = 42                   # REQUIRED - Random seed
    n_jobs: int = -1                         # REQUIRED - Parallel jobs (-1 = all)
```

**Validation Rules:**
- `fracdiff_threshold` must be > 0
- `fracdiff_adfuller_alpha` must be in (0, 1)
- `upper_barrier_pct` must be > 0
- `lower_barrier_pct` must be < 0
- `n_folds` must be >= 2
- `kelly_fraction` must be in (0, 1]
- `max_bet_size` must be in (0, 1]
- `importance_method` must be one of: "mdi", "mda", "sfi", "combined"

### FinancialMLResult
```python
@dataclass
class FinancialMLResult:
    # Features
    X_original: np.ndarray                    # REQUIRED - Original feature matrix
    X_transformed: np.ndarray                 # REQUIRED - Transformed features
    feature_names: List[str]                  # REQUIRED - Feature name list

    # Labels
    y_original: np.ndarray                    # REQUIRED - Original labels
    y_triple_barrier: np.ndarray              # REQUIRED - Triple barrier labels
    y_meta: Optional[np.ndarray] = None       # OPTIONAL - Meta-labels

    # Predictions
    primary_predictions: Optional[np.ndarray] = None    # OPTIONAL - Primary model predictions
    meta_predictions: Optional[np.ndarray] = None       # OPTIONAL - Meta model predictions
    bet_sizes: Optional[np.ndarray] = None              # OPTIONAL - Bet sizes from meta-labels

    # Feature Importance
    importance: Optional[ImportanceResult] = None       # OPTIONAL - Feature importance results

    # Cross-validation scores
    cv_scores: Dict[str, List[float]] = field(default_factory=dict)  # AUTO - CV scores per fold

    # Metrics
    primary_accuracy: float = 0.0            # AUTO - Primary model accuracy
    meta_accuracy: float = 0.0                # AUTO - Meta model accuracy
    combined_accuracy: float = 0.0            # AUTO - Combined accuracy

    # Metadata
    n_samples: int = 0                        # AUTO - Number of samples
    n_features: int = 0                       # AUTO - Number of features
    timestamp: datetime = field(default_factory=datetime.now)  # AUTO
```

**Validation Rules:**
- `X_original.shape[1] == X_transformed.shape[1]` (same number of features)
- `len(y_triple_barrier) == X_transformed.shape[0]` (aligned samples)
- `bet_sizes` must be in [0, 1] if provided
- All accuracies must be in [0, 1]
- `n_samples >= n_features` (more samples than features)

---

## Function Signatures (Contracts)

### `FinancialMLPipeline.__init__(config: Optional[FinancialMLConfig] = None) -> None`
**Pre:** None (config optional, defaults provided)
**Post:** Pipeline initialized with all sub-components (fracdiff, triple_barrier, meta_labeling, bet_sizing)
**Raises:** None
**Retry:** No
**Side Effects:** None (initialization only)

### `FinancialMLPipeline.fit(X: Union[pd.DataFrame, np.ndarray], prices: Union[pd.Series, np.ndarray], y: Optional[Union[pd.Series, np.ndarray]] = None) -> FinancialMLPipeline`
**Pre:** `X` and `prices` have same length; if `y` provided, same length as `X`
**Post:** Pipeline fitted; `X_transformed_`, `y_triple_barrier_`, `feature_names_` attributes set; `_is_fitted = True`
**Raises:** `ValueError` if insufficient data or invalid inputs
**Retry:** No
**Side Effects:** Fits internal models (meta_labeling, feature_importance); stores state

### `FinancialMLPipeline.predict(X: Union[pd.DataFrame, np.ndarray], prices: Optional[Union[pd.Series, np.ndarray]] = None) -> FinancialMLResult`
**Pre:** Pipeline must be fitted (`_is_fitted == True`); `X` has same number of features as training data
**Post:** Returns `FinancialMLResult` with predictions and bet_sizes (if meta_labeling enabled)
**Raises:** `ValueError` if pipeline not fitted
**Retry:** No
**Side Effects:** None (prediction only)

### `FinancialMLPipeline.fit_predict(X_train: Union[pd.DataFrame, np.ndarray], prices_train: Union[pd.Series, np.ndarray], X_test: Union[pd.DataFrame, np.ndarray], prices_test: Optional[Union[pd.Series, np.ndarray]] = None, y_test: Optional[Union[pd.Series, np.ndarray]] = None) -> FinancialMLResult`
**Pre:** Training and test data have compatible shapes; all arrays have same length within groups
**Post:** Returns fitted result with accuracies if `y_test` provided
**Raises:** `ValueError` on invalid shapes; falls back to predictions without evaluation
**Retry:** No
**Side Effects:** Fits pipeline on training data, predicts on test data

### `FinancialMLPipeline.cross_validate(X: Union[pd.DataFrame, np.ndarray], prices: Union[pd.Series, np.ndarray], y: Optional[Union[pd.Series, np.ndarray]] = None) -> Dict[str, List[float]]`
**Pre:** Sufficient data for `n_folds` splits
**Post:** Returns dict with `primary_accuracy`, `meta_accuracy`, `combined_accuracy` lists (one per fold)
**Raises:** Returns empty dict on error
**Retry:** No
**Side Effects:** None (validation only)

### `FinancialMLPipeline._apply_fracdiff_to_features(X: np.ndarray, prices: np.ndarray) -> np.ndarray`
**Pre:** `X` and `prices` have same length
**Post:** Returns fractionally differentiated features (NaN filled with 0)
**Raises:** Returns original `X` on error (fallback)
**Retry:** No
**Side Effects:** None (private transformation)

### `apply_financial_ml(X_train: Union[pd.DataFrame, np.ndarray], prices_train: Union[pd.Series, np.ndarray], X_test: Union[pd.DataFrame, np.ndarray], prices_test: Union[pd.Series, np.ndarray], y_test: Optional[Union[pd.Series, np.ndarray]] = None, config: Optional[FinancialMLConfig] = None) -> FinancialMLResult`
**Pre:** All inputs have compatible shapes
**Post:** Returns complete FinancialML result
**Raises:** Propagates exceptions from pipeline
**Retry:** No
**Side Effects:** Creates and fits pipeline (convenience function)

### `calculate_lopez_de_prado_features(prices: pd.Series, features: Optional[pd.DataFrame] = None, config: Optional[FinancialMLConfig] = None) -> Tuple[pd.DataFrame, pd.Series]`
**Pre:** `prices` is Series with DatetimeIndex; if `features` provided, index aligned with `prices`
**Post:** Returns (features DataFrame, labels Series) with aligned indices
**Raises:** Returns empty structures on error
**Retry:** No
**Side Effects:** Generates features if not provided (returns, volatility, momentum, RSI)

---

## Acceptance Criteria
- [ ] All dataclass fields have type hints and validation rules
- [ ] Fractional differentiation finds optimal `d` using ADF test
- [ ] Triple barrier labeling generates 3 classes (upper hit, lower hit, vertical barrier)
- [ ] Purged K-fold CV prevents look-ahead bias with purge/embargo periods
- [ ] Meta-labeling trains secondary model to predict primary model errors
- [ ] Bet sizing uses Kelly criterion or fixed sizing
- [ ] Feature importance supports MDI, MDA, SFI methods
- [ ] All methods handle DataFrame and numpy array inputs
- [ ] Pipeline validates fitted state before prediction
- [ ] Error handling with fallback to simple methods
- [ ] Cross-validation returns per-fold metrics
- [ ] Convenience functions for common workflows

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-003 | BASE_RULES.md | No look-ahead bias in CV | ✅ OK - Purged K-fold with embargo |
| BT-002 | BASE_RULES.md | Out-of-sample testing required | ✅ OK - fit_predict separates train/test |
| TRD-001 | BASE_RULES.md | Validate inputs (features, prices) | ⚠️ PARTIAL - Some validation missing |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - try/except with logging |
| LOG-004 | BASE_RULES.md | Log all exceptions | ✅ OK - logger.error in except blocks |
| TYP-001 | BASE_RULES.md | 100% type coverage | ⚠️ PARTIAL - Some parameters lack hints |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Pipeline orchestrates, delegates |
| ARCH-004 | BASE_RULES.md | Small functions | ⚠️ PARTIAL - Some methods > 20 lines |
| DP-004 | BASE_RULES.md | Dependency injection | ✅ OK - Config injected via constructor |

**NOTE:** All 96 BASE_RULES apply. Critical for ML pipeline:
- **BT-003:** Purged CV prevents leakage and overfitting
- **BT-002:** Strict train/test separation ensures validity
- **TRD-001:** Input validation prevents garbage in/garbage out
- **DP-004:** DI enables testing with mock components

---

## Dependencies
- **External:** `numpy`, `pandas`, `sklearn` (RandomForestClassifier), `dataclasses`, `datetime`, `logging`, `typing`
- **Internal:**
  - `.feature_engineering`: FractionalDifferentiation, FeatureImportanceConfig, FinancialMLFeatureImportance, ImportanceResult
  - `.labeling`: BetSizing, BetSizingConfig, MetaLabeling, MetaLabelingConfig, TripleBarrierConfig, TripleBarrierLabeler
  - `.validation`: purged_kfold_splits

---

## Required Tests
- **tests/backtesting/test_financial_ml.py:**
  - Test pipeline initialization with default and custom config
  - Test fractional differentiation application
  - Test triple barrier labeling generation
  - Test meta-labeling training and prediction
  - Test bet sizing calculation (Kelly, fixed)
  - Test purged K-fold cross-validation
  - Test feature importance calculation (MDI, MDA, SFI)
  - Test fit_predict workflow with evaluation
  - Test cross-validation returns per-fold metrics
  - Test error handling (insufficient data, invalid shapes)
  - Test convenience functions
  - Test DataFrame vs numpy array handling
  - Test fitted state validation (predict before fit raises)

---

## Notes
- Integrates 6 major López de Prado techniques from "Advances in Financial Machine Learning"
- Pipeline orchestrates complex ML workflow; delegates to specialized modules
- Graceful degradation: falls back to simpler methods on error
- Uses sklearn's RandomForestClassifier as default (configurable)
- Purged CV prevents leakage from test to train via embargo period
- Meta-labeling is two-stage: primary predicts direction, meta predicts correctness
- Bet sizes from meta-label probabilities enable position sizing
