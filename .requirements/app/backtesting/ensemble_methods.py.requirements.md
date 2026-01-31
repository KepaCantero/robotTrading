# ensemble_methods.py

## Purpose
Implements comprehensive ensemble techniques following "The Elements of Statistical Learning" (ESL). Provides bagging, boosting, stacking, random forests, and ensemble analysis tools for machine learning on trading data.

---

## Type Definitions / Data Classes

### EnsembleMethod Enum
```python
class EnsembleMethod(Enum):
    BAGGING = "bagging"
    BOOSTING = "boosting"
    STACKING = "stacking"
    VOTING = "voting"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
```

**Validation Rules:**
- Enum values are lowercase strings
- Used for type safety in result tracking

### EnsembleResult DataClass
```python
@dataclass
class EnsembleResult:
    timestamp: datetime                      # REQUIRED - When ensemble was run
    method: EnsembleMethod                   # REQUIRED - Which ensemble method
    n_estimators: int                        # REQUIRED - Number of base estimators
    train_score: float                       # REQUIRED - Training set score
    test_score: float                        # REQUIRED - Test set score
    estimator_scores: List[float]            # REQUIRED - Individual estimator scores
    ensemble_improvement: float              # REQUIRED - Improvement over best single
    diversity: float                         # REQUIRED - Diversity among estimators
    model_name: str                          # REQUIRED - Name of base model
    details: Dict[str, Any]                  # OPTIONAL - Additional metadata
```

**Validation Rules:**
- All numeric fields must be finite (not NaN or Inf)
- estimator_scores length must equal n_estimators
- diversity must be between 0 and 1

### BaggingConfig DataClass
```python
@dataclass
class BaggingConfig:
    n_estimators: int = 100
    max_samples: float = 1.0
    max_features: float = 1.0
    bootstrap: bool = True
    bootstrap_features: bool = False
    n_jobs: int = -1
    random_state: int = 42
```

**Validation Rules:**
- n_estimators must be positive
- max_samples must be between 0 and 1
- max_features must be between 0 and 1
- n_jobs=-1 uses all CPU cores

### BoostingConfig DataClass
```python
@dataclass
class BoostingConfig:
    n_estimators: int = 100
    learning_rate: float = 0.1
    max_depth: int = 3
    subsample: float = 1.0
    loss: str = "log_loss"
    random_state: int = 42
```

**Validation Rules:**
- learning_rate must be positive (typically 0.01 to 0.3)
- max_depth must be positive (typically 1-10)
- subsample must be between 0 and 1

### StackingConfig DataClass
```python
@dataclass
class StackingConfig:
    base_estimators: List[Tuple[str, BaseEstimator]]
    meta_estimator: BaseEstimator
    cv: int = 5
    n_jobs: int = -1
```

**Validation Rules:**
- base_estimators must have at least 2 estimators
- meta_estimator must be scikit-learn compatible
- cv must be at least 2

---

## Function Signatures (Contracts)

### `BaggingEnsemble.fit(X, y) -> BaggingEnsemble`
**Pre:** X and y must have same length, X must be 2D array-like, y must be 1D array-like
**Post:** Returns self with fitted bagger_ attribute
**Raises:** ValueError for invalid shapes, sklearn exceptions
**Retry:** ❌ No
**Side Effects:** Fits sklearn BaggingClassifier/BaggingRegressor

### `BaggingEnsemble.predict(X) -> np.ndarray`
**Pre:** X must have same number of features as training data, model must be fitted
**Post:** Returns predictions array
**Raises:** sklearn.exceptions.NotFittedError if not fitted
**Retry:** ❌ No
**Side Effects:** None (prediction only)

### `BaggingEnsemble.score(X, y) -> float`
**Pre:** Model must be fitted, X must match training features
**Post:** Returns R² score (regression) or accuracy (classification)
**Raises:** sklearn.exceptions.NotFittedError
**Retry:** ❌ No
**Side Effects:** None

### `BoostingEnsemble.fit(X, y) -> BoostingEnsemble`
**Pre:** X and y must have compatible shapes
**Post:** Returns self with fitted booster_ attribute
**Raises:** ValueError for invalid inputs
**Retry:** ❌ No
**Side Effects:** Fits GradientBoostingClassifier/Regressor

### `StackingEnsemble.fit(X, y) -> StackingEnsemble`
**Pre:** base_estimators must be list of (name, estimator) tuples
**Post:** Returns self with fitted stacker_ attribute
**Raises:** ValueError for invalid estimators
**Retry:** ❌ No
**Side Effects:** Fits stacking model with cross-validation

### `RandomForestEnsemble.fit(X, y) -> RandomForestEnsemble`
**Pre:** X and y must have compatible shapes
**Post:** Returns self with fitted rf_ attribute
**Raises:** ValueError for invalid inputs
**Retry:** ❌ No
**Side Effects:** Fits RandomForestClassifier/Regressor

### `EnsembleAnalyzer.analyze_bagging(estimator, X, y, n_estimators) -> EnsembleResult`
**Pre:** estimator must be unfitted sklearn estimator, X and y valid
**Post:** Returns EnsembleResult with analysis metrics
**Raises:** sklearn exceptions
**Retry:** ❌ No
**Side Effects:** Splits data, fits bagging, calculates metrics

### `EnsembleAnalyzer.compare_ensembles(X, y, base_estimator, base_estimators, n_estimators) -> Dict[str, EnsembleResult]`
**Pre:** X and y must be valid, estimators must be sklearn-compatible
**Post:** Returns dict mapping method names to results
**Raises:** Logs exceptions, continues with partial results
**Retry:** ✅ Yes (individual ensemble failures don't stop comparison)
**Side Effects:** Fits multiple ensemble models

---

## Acceptance Criteria
- [ ] All ensemble classes follow sklearn API (fit, predict, score)
- [ ] Bagging reduces variance compared to single estimator
- [ ] Boosting improves accuracy over single estimator
- [ ] Stacking combines predictions from multiple base models
- [ ] Random Forest uses random feature selection at splits
- [ ] All ensembles auto-detect classification vs regression (<=15 unique classes)
- [ ] EnsembleResult contains all required metrics
- [ ] OOB (out-of-bag) scores available for bagging/RF
- [ ] Stacking uses cross-validation for meta-features
- [ ] Feature importance available for boosting/RF
- [ ] Diversity metric calculated for bagging/RF
- [ ] All ensembles support n_jobs=-1 for parallel execution
- [ ] Random state set for reproducibility (default: 42)
- [ ] Convenience functions (bagging_ensemble, stacking_ensemble) work end-to-end
- [ ] All classes use check_is_fitted for validation
- [ ] Type hints use Union[np.ndarray, pd.DataFrame] for flexibility

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True in error handlers |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - Comprehensive type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - ESL-compliant naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure component |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each class one method |
| DP-003 | BASE_RULES.md | Strategy pattern | ✅ OK - EnsembleMethod enum |
| TST-001 | BASE_RULES.md | AAA pattern | N/A - No tests yet |
| PERF-001 | BASE_RULES.md | List comprehensions | ✅ OK - Used throughout |
| QL-001 | BASE_RULES.md | Complexity < 10 | ✅ OK - Methods are focused |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** sklearn (ensemble, base, tree, utils, model_selection), numpy, pandas, dataclasses, enum, datetime, typing
- **Internal:** None

---

## Required Tests
- **tests/backtesting/test_ensemble_methods.py:**
  - Test BaggingEnsemble.fit() creates valid model
  - Test BaggingEnsemble.predict() returns predictions
  - Test BaggingEnsemble.score() returns valid score
  - Test BaggingEnsemble.get_oob_score() returns OOB score
  - Test BaggingEnsemble auto-detects classification vs regression
  - Test BoostingEnsemble.fit() creates valid model
  - Test BoostingEnsemble.staged_predict() yields predictions
  - Test BoostingEnsemble.get_feature_importance() returns importance array
  - Test StackingEnsemble.fit() creates valid stacked model
  - Test StackingEnsemble.get_base_model_scores() returns individual scores
  - Test RandomForestEnsemble.fit() creates valid RF model
  - Test RandomForestEnsemble.get_feature_importance() returns importance
  - Test RandomForestEnsemble.get_oob_score() returns OOB score
  - Test EnsembleAnalyzer.analyze_bagging() returns valid EnsembleResult
  - Test EnsembleAnalyzer.analyze_boosting() returns EnsembleResult
  - Test EnsembleAnalyzer.analyze_stacking() returns EnsembleResult
  - Test EnsembleAnalyzer.compare_ensembles() returns all methods
  - Test EnsembleAnalyzer._compute_diversity() returns diversity score
  - Test bagging_ensemble() convenience function
  - Test stacking_ensemble() convenience function
  - Test EnsembleResult.to_dict() converts correctly
  - Test all ensembles handle invalid inputs gracefully
  - Test n_jobs=-1 uses parallel execution
  - Test random_state ensures reproducibility

---

## Notes
- Follows ESL (Elements of Statistical Learning) reference implementation
- Classification threshold: <=15 unique values treated as classification
- All estimators use sklearn.utils.validation.check_is_fitted
- All ensembles support both np.ndarray and pd.DataFrame inputs
- Default random_state=42 for reproducibility
- n_jobs=-1 enables parallel execution by default
- Diversity calculated as 1 - average correlation between predictions
- Stacking defaults to Ridge (regression) or LogisticRegression (classification) as meta-learner
- Feature importance available via feature_importances_ attribute
- OOB (out-of-bag) scoring available when bootstrap=True
- Comprehensive docstrings with ESL chapter references
- Type hints use Union for flexibility with pandas/numpy
