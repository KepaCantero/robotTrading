# ensemble_methods.py

## Purpose
Comprehensive ensemble methods implementation following ESL (Hastie, Tibshirani, Friedman) including Bagging, Boosting, Stacking, Random Forests.

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

### EnsembleResult DataClass
```python
@dataclass
class EnsembleResult:
    timestamp: datetime
    method: EnsembleMethod
    n_estimators: int
    train_score: float
    test_score: float
    estimator_scores: List[float]
    ensemble_improvement: float
    diversity: float
    model_name: str
    details: Dict[str, Any]
```

### BaggingConfig, BoostingConfig, StackingConfig DataClasses
See file for complete definitions.

---

## Function Signatures (Contracts)

### `BaggingEnsemble.fit(X, y) -> BaggingEnsemble`
**Pre:** X and y have same length
**Post:** Returns fitted ensemble
**Raises:** ValueError from check_X_y
**Retry:** No
**Side Effects:** Fits sklearn BaggingClassifier/Regressor

### `BaggingEnsemble.predict(X) -> np.ndarray`
**Pre:** Model is fitted
**Post:** Returns predictions
**Raises:** NotFittedError
**Retry:** No
**Side Effects:** None

### `BaggingEnsemble.get_oob_score() -> Optional[float]`
**Pre:** Model fitted with bootstrap=True
**Post:** Returns out-of-bag score
**Raises:** NotFittedError
**Retry:** No
**Side Effects:** None

### `BoostingEnsemble.staged_predict(X) -> Generator`
**Pre:** Model fitted
**Post:** Yields predictions at each stage
**Raises:** NotFittedError
**Retry:** No
**Side Effects:** None

### `BoostingEnsemble.get_feature_importance() -> np.ndarray`
**Pre:** Model fitted
**Post:** Returns feature importance
**Raises:** NotFittedError
**Retry:** No
**Side Effects:** None

### `StackingEnsemble.fit(X, y) -> StackingEnsemble`
**Pre:** X and y valid
**Post:** Returns fitted stacking ensemble
**Raises:** ValueError
**Retry:** No
**Side Effects:** Fits StackingClassifier/Regressor

### `StackingEnsemble.get_base_model_scores(X, y) -> Dict[str, float]`
**Pre:** Model fitted
**Post:** Returns dict of base model scores
**Raises:** NotFittedError
**Retry:** No
**Side Effects:** None

### `RandomForestEnsemble.get_oob_score() -> Optional[float]`
**Pre:** Model fitted with oob_score=True
**Post:** Returns OOB score
**Raises:** NotFittedError
**Retry:** No
**Side Effects:** None

### `EnsembleAnalyzer._compute_diversity(ensemble, X) -> float`
**Pre:** ensemble fitted
**Post:** Returns diversity (1 - avg correlation)
**Raises:** NotFittedError
**Retry:** No
**Side Effects:** Computes pairwise correlations

### `EnsembleAnalyzer.compare_ensembles(X, y, ...) -> Dict[str, EnsembleResult]`
**Pre:** X and y valid
**Post:** Returns results from all ensemble methods
**Raises:** Exceptions logged
**Retry:** No
**Side Effects:** Runs all methods

---

## Acceptance Criteria
- [ ] All ensemble classes follow sklearn API
- [ ] Classification vs regression auto-detected (<=15 classes)
- [ ] All estimators use check_is_fitted
- [ ] All methods handle np.ndarray and pd.DataFrame
- [ ] Stacking defaults to LogisticRegression/Ridge
- [ ] Random Forest computes OOB by default
- [ ] Diversity = 1 - average correlation
- [ ] Error handling doesn't stop on single failure

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ⚠️ NOT APPLIED |
| DP-003 | 04-design-patterns.md | Strategy pattern | ✅ OK |
| LOG-004 | 09-logging-observability.md | Error logging | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK |
| TST-005 | 06-testing.md | Coverage > 80% | ❌ GAP - No test file found |
| ARCH-004 | 05-architecture.md | Functions < 20 lines | ❌ GAP - Many exceed |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, sklearn
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/test_ensemble_methods.py:**
  - Test BaggingEnsemble fit/predict/score
  - Test auto-detect classification vs regression
  - Test OOB score
  - Test BoostingEnsemble staged_predict
  - Test feature importance
  - Test StackingEnsemble
  - Test RandomForestEnsemble
  - Test diversity calculation
  - Test compare_ensembles

---

## Notes
- **ESL Reference:** Chapters 8, 10, 15, 16
- **Classification Threshold:** <=15 unique values
- **Diversity:** 1 - average pairwise correlation
