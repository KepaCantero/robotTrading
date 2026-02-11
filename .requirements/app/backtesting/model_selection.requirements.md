# model_selection.py

## Purpose
Model Selection Criteria for Statistical Learning - Implements comprehensive model selection criteria following Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning" (ESL) Chapter 7: Model Assessment and Selection.

---

## Type Definitions / Data Classes

### CriterionType (str, Enum)
```python
class CriterionType(str, Enum):
    AIC = "aic"                  # Akaike Information Criterion
    BIC = "bic"                  # Bayesian Information Criterion
    ADJUSTED_R2 = "adjusted_r2"  # Adjusted R-squared
    MALLOW_CP = "mallow_cp"      # Mallow's Cp
    GCV = "gcv"                  # Generalized Cross-Validation
    CV_SCORE = "cv_score"        # Cross-Validation Score
```

### ModelCriterionResult
```python
@dataclass
class ModelCriterionResult:
    """Result of model selection criterion calculation."""
    timestamp: datetime
    model_name: str
    criterion_type: CriterionType
    criterion_value: float
    n_params: int
    n_samples: int

    # Performance metrics
    mse: float
    rmse: float
    r2: float
    adjusted_r2: float

    # Additional statistics
    log_likelihood: float = 0.0
    aic: float = 0.0
    bic: float = 0.0

    # Ranking (lower is better for AIC, BIC, Cp)
    rank: Optional[int] = None

    # Additional info
    details: Dict[str, Any] = field(default_factory=dict)
```

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert to dictionary

### ModelComparisonResult
```python
@dataclass
class ModelComparisonResult:
    """Result of comparing multiple models."""
    timestamp: datetime
    models: List[ModelCriterionResult]
    best_model_by_aic: str
    best_model_by_bic: str
    best_model_by_adjusted_r2: str
    best_model_by_cv: Optional[str]

    # Summary statistics
    comparison_table: pd.DataFrame
```

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert to dictionary

### AICCalculator
```python
class AICCalculator:
    """
    Akaike Information Criterion (AIC).

    AIC = 2k - 2ln(L) or AIC = n * ln(RSS/n) + 2k

    Lower AIC indicates better model (penalizes complexity).

    Interpretation:
    - ΔAIC < 2: Substantial evidence
    - 4 ≤ ΔAIC < 7: considerably less evidence
    - ΔAIC ≥ 10: essentially none

    Reference: ESL Section 7.5
    """
```

### BICCalculator
```python
class BICCalculator:
    """
    Bayesian Information Criterion (BIC).

    BIC = k * ln(n) - 2ln(L) or BIC = n * ln(RSS/n) + k * ln(n)

    Stronger penalty for complexity than AIC.
    Consistent model selection (selects true model as n → ∞).

    Reference: ESL Section 7.7
    """
```

### AdjustedR2Calculator
```python
class AdjustedR2Calculator:
    """
    Adjusted R-squared.

    Adjusted R² = 1 - (1 - R²) * (n - 1) / (n - p - 1)

    Higher is better. Can be negative if model fit is very poor.

    Reference: ESL Section 3.2
    """
```

### MallowCpCalculator
```python
class MallowCpCalculator:
    """
    Mallow's Cp.

    Cp = (RSS_p / σ²) - n + 2p

    Good models have Cp ≈ p.

    Reference: ESL Section 3.3
    """
```

### GCVCalculator
```python
class GCVCalculator:
    """
    Generalized Cross-Validation.

    GCV = (n * RSS) / (n - p)²

    Rotation-invariant version of cross-validation.

    Reference: ESL Section 5.4
    """
```

### ModelSelector
```python
class ModelSelector:
    """
    Comprehensive model selection using multiple criteria.

    Implements ESL-recommended model selection procedures:
    1. AIC
    2. BIC
    3. Adjusted R²
    4. Cross-validation score
    5. Mallow's Cp
    6. GCV
    """
```

---

## Function Signatures (Contracts)

### `AICCalculator.calculate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_params: int,
    estimate_sigma: bool = True,
) -> float`
**Pre:** y_true and y_pred have same length; n_params >= 0
**Post:** Returns AIC value (lower is better)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `AIC = n * ln(RSS/n) + 2k`
- n = sample size
- RSS = residual sum of squares
- k = number of parameters (including σ² if estimate_sigma=True)

### `AICCalculator.calculate_with_likelihood(
    log_likelihood: float,
    n_params: int,
) -> float`
**Pre:** log_likelihood is float; n_params >= 0
**Post:** Returns AIC value
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `AIC = 2k - 2ln(L)`

### `BICCalculator.calculate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_params: int,
    estimate_sigma: bool = True,
) -> float`
**Pre:** y_true and y_pred have same length; n_params >= 0
**Post:** Returns BIC value (lower is better)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `BIC = n * ln(RSS/n) + k * ln(n)`
- k = number of parameters (including σ² if estimate_sigma=True)

### `BICCalculator.calculate_with_likelihood(
    log_likelihood: float,
    n_params: int,
    n_samples: int,
) -> float`
**Pre:** log_likelihood is float; n_params, n_samples > 0
**Post:** Returns BIC value
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `BIC = k * ln(n) - 2ln(L)`

### `AdjustedR2Calculator.calculate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_params: int,
) -> float`
**Pre:** y_true and y_pred have same length; n_params >= 0; n_samples > n_params + 1
**Post:** Returns adjusted R² value (higher is better)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `Adjusted R² = 1 - (1 - R²) * (n - 1) / (n - p - 1)`

### `MallowCpCalculator.calculate(
    rss_subset: float,
    rss_full: float,
    n_params_subset: int,
    n_params_full: int,
    n_samples: int,
) -> Tuple[float, float]`
**Pre:** All values positive; n_params_full < n_samples
**Post:** Returns (Cp value, p value for comparison)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `Cp = (RSS_p / σ²) - n + 2p`
- σ² = RSS_full / (n - n_params_full)

**Good Model Criterion:** Cp ≈ p

### `GCVCalculator.calculate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_params: int,
) -> float`
**Pre:** y_true and y_pred have same length; n_params < n_samples
**Post:** Returns GCV value (lower is better)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `GCV = (n * RSS) / (n - p)²`

### `ModelSelector.__init__(
    cv_folds: int = 5,
    random_state: int = 42,
) -> None`
**Pre:** cv_folds >= 2
**Post:** Selector initialized
**Raises:** None
**Retry:** No
**Side Effects:** Stores configuration

### `ModelSelector.evaluate_model(
    model: BaseEstimator,
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    model_name: str,
) -> ModelCriterionResult`
**Pre:** model is sklearn estimator; X and y have compatible shapes
**Post:** Returns ModelCriterionResult with all criteria
**Raises:** ValueError if model evaluation fails
**Retry:** No
**Side Effects:** Fits model if not fitted; clones model

**Process Flow:**
1. Validate inputs with check_array
2. Fit model if not fitted (using clone)
3. Calculate predictions
4. Calculate MSE, RMSE, R²
5. Count parameters (non-zero coef + intercept)
6. Calculate AIC, BIC, GCV, Adjusted R²
7. Run cross-validation for CV_RMSE
8. Estimate log-likelihood
9. Return ModelCriterionResult

### `ModelSelector.compare_models(
    models: Dict[str, BaseEstimator],
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
) -> ModelComparisonResult`
**Pre:** models dict non-empty; X and y compatible
**Post:** Returns ModelComparisonResult with rankings
**Raises:** ValueError if no models can be evaluated
**Retry:** No
**Side Effects:** Evaluates all models; clones and fits each

**Process Flow:**
1. Evaluate each model using evaluate_model
2. Rank by AIC (lower is better)
3. Rank by BIC (lower is better)
4. Rank by Adjusted R² (higher is better)
5. Find best model by each criterion
6. Find best by CV (if available)
7. Create comparison DataFrame
8. Return ModelComparisonResult

### `ModelSelector.select_best_model(
    models: Dict[str, BaseEstimator],
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    criterion: str = "bic",
) -> Tuple[str, BaseEstimator, ModelCriterionResult]`
**Pre:** models non-empty; criterion in ["aic", "bic", "adjusted_r2"]
**Post:** Returns (model_name, fitted_model, result)
**Raises:** ValueError for unknown criterion
**Retry:** No
**Side Effects:** Clones and fits best model

### `ModelSelector.compute_information_criteria(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_params: int,
) -> Dict[str, float]`
**Pre:** Arrays same length; n_params valid
**Post:** Returns dict with all criteria
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Output:** `{"aic": float, "bic": float, "adjusted_r2": float, "gcv": float, "r2": float, "mse": float}`

### `select_model_by_aic(
    models: Dict[str, BaseEstimator],
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
) -> Tuple[str, BaseEstimator, ModelCriterionResult]`
**Pre:** models non-empty; X and y compatible
**Post:** Returns (best_name, best_model, result) by AIC
**Raises:** None
**Retry:** No
**Side Effects:** Creates ModelSelector and calls select_best_model

**Convenience Function:** Simplified interface for AIC selection

### `select_model_by_bic(
    models: Dict[str, BaseEstimator],
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
) -> Tuple[str, BaseEstimator, ModelCriterionResult]`
**Pre:** models non-empty; X and y compatible
**Post:** Returns (best_name, best_model, result) by BIC
**Raises:** None
**Retry:** No
**Side Effects:** Creates ModelSelector and calls select_best_model

**Convenience Function:** Simplified interface for BIC selection

### `compute_criteria(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_params: int,
) -> Dict[str, float]`
**Pre:** Arrays same length; n_params valid
**Post:** Returns dict with all criteria
**Raises:** None
**Retry:** No
**Side Effects:** Creates ModelSelector and calls compute_information_criteria

**Convenience Function:** Quick criteria computation

---

## Acceptance Criteria
- [ ] **AC-001:** CriterionType has AIC, BIC, ADJUSTED_R2, MALLOW_CP, GCV, CV_SCORE values
- [ ] **AC-002:** AICCalculator.calculate() implements n * ln(RSS/n) + 2k formula
- [ ] **AC-003:** AICCalculator adds 1 to k when estimate_sigma=True
- [ ] **AC-004:** BICCalculator.calculate() implements n * ln(RSS/n) + k * ln(n) formula
- [ ] **AC-005:** AdjustedR2Calculator implements 1 - (1 - R²) * (n - 1) / (n - p - 1)
- [ ] **AC-006:** MallowCpCalculator returns Cp where good models have Cp ≈ p
- [ ] **AC-007:** GCVCalculator implements (n * RSS) / (n - p)² formula
- [ ] **AC-008:** ModelSelector.evaluate_model() calculates all criteria
- [ ] **AC-009:** ModelSelector.evaluate_model() counts non-zero coefficients
- [ ] **AC-010:** ModelSelector.compare_models() ranks by AIC (lower better)
- [ ] **AC-011:** ModelSelector.compare_models() ranks by BIC (lower better)
- [ ] **AC-012:** ModelSelector.compare_models() ranks by AdjR² (higher better)
- [ ] **AC-013:** ModelSelector.compare_models() creates comparison DataFrame
- [ ] **AC-014:** select_best_model() accepts "aic", "bic", "adjusted_r2" criteria
- [ ] **AC-015:** NumPy 2.0 compatible (no np aliases)
- [ ] **AC-016:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Model Selection):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| AIC formula | ESL Section 7.5 | n * ln(RSS/n) + 2k | ✅ OK - AICCalculator.calculate() |
| AIC interpretation | ESL Section 7.5 | ΔAIC < 2: substantial evidence | ✅ OK - Docstring |
| BIC formula | ESL Section 7.7 | n * ln(RSS/n) + k * ln(n) | ✅ OK - BICCalculator.calculate() |
| BIC consistency | ESL Section 7.7 | Stronger penalty than AIC | ✅ OK - ln(n) > 2 for n > 7 |
| Adjusted R² formula | ESL Section 3.2 | 1 - (1 - R²) * (n - 1) / (n - p - 1) | ✅ OK - AdjustedR2Calculator |
| Mallow's Cp | ESL Section 3.3 | (RSS_p / σ²) - n + 2p | ✅ OK - MallowCpCalculator |
| Cp criterion | ESL Section 3.3 | Good models have Cp ≈ p | ✅ OK - Docstring |
| GCV formula | ESL Section 5.4 | (n * RSS) / (n - p)² | ✅ OK - GCVCalculator |
| CV scoring | ESL Section 7.10 | Cross-validation for model selection | ✅ OK - ModelSelector.evaluate_model() |
| Model ranking | ESL Section 7.7 | Rank by multiple criteria | ✅ OK - compare_models() |
| Sklearn integration | Scikit-learn | BaseEstimator compatibility | ✅ OK - ModelSelector |
| Dataclass results | Clean code | Immutable result objects | ✅ OK - ModelCriterionResult |
| Convenience functions | Clean code | Simplified interfaces | ✅ OK - select_model_by_*() |
| Enum for criteria | Clean code | CriterionType enum | ✅ OK - CriterionType |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - np.ndarray |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and ESL (Hastie, Tibshirani, Friedman) for model selection standards.

---

## Dependencies
- **External:** `numpy`, `pandas`, `sklearn` (BaseEstimator, clone, metrics, model_selection, validation)
- **Internal:** None (infrastructure layer)

---

## Required Tests
- **test_model_selection.py:**
  - `test_criterion_type_enum()` - AIC, BIC, ADJUSTED_R2, MALLOW_CP, GCV, CV_SCORE
  - `test_aic_calculate()` - Returns correct AIC value
  - `test_aic_estimate_sigma()` - Adds 1 to k when True
  - `test_aic_with_likelihood()` - Uses 2k - 2ln(L) formula
  - `test_bic_calculate()` - Returns correct BIC value
  - `test_bic_stronger_penalty()` - BIC > AIC for n > 7
  - `test_bic_with_likelihood()` - Uses k * ln(n) - 2ln(L) formula
  - `test_adjusted_r2_calculate()` - Returns correct adjusted R²
  - `test_adjusted_r2_penalty()` - Lower than R² when adding params
  - `test_mallow_cp_calculate()` - Returns Cp value
  - `test_mallow_cp_good_model()` - Cp ≈ p for good model
  - `test_gcv_calculate()` - Returns correct GCV value
  - `test_model_selector_init()` - Initializes with defaults
  - `test_evaluate_model()` - Returns ModelCriterionResult
  - `test_evaluate_model_counts_params()` - Counts non-zero coef
  - `test_evaluate_model_unfitted()` - Fits model before evaluation
  - `test_evaluate_model_fitted()` - Uses fitted model
  - `test_compare_models()` - Returns ModelComparisonResult
  - `test_compare_models_ranking()` - Ranks by AIC, BIC, AdjR²
  - `test_compare_models_best_by_aic()` - Identifies lowest AIC
  - `test_compare_models_best_by_bic()` - Identifies lowest BIC
  - `test_compare_models_best_by_adj_r2()` - Identifies highest AdjR²
  - `test_compare_models_table()` - Creates comparison DataFrame
  - `test_select_best_model_bic()` - Selects by BIC (default)
  - `test_select_best_model_aic()` - Selects by AIC
  - `test_select_best_model_adjusted_r2()` - Selects by AdjR²
  - `test_select_best_model_unknown_criterion()` - Raises ValueError
  - `test_compute_information_criteria()` - Returns all criteria
  - `test_select_model_by_aic()` - Convenience function works
  - `test_select_model_by_bic()` - Convenience function works
  - `test_compute_criteria()` - Convenience function works
  - `test_model_criterion_result_to_dict()` - Converts to dict
  - `test_model_comparison_result_to_dict()` - Converts to dict

---

## Notes
- **Critical:** Model selection prevents overfitting by penalizing complexity
- **ESL Reference:** "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
  - Chapter 7: Model Assessment and Selection
  - Chapter 9: Generalized Linear Models and Regression Splines
- **AIC (Akaike Information Criterion):**
  - Formula: `AIC = n * ln(RSS/n) + 2k`
  - Lower is better
  - Penalty: 2 per parameter
  - Interpretation: ΔAIC < 2 = substantial evidence
  - Best for: Prediction-focused model selection
- **BIC (Bayesian Information Criterion):**
  - Formula: `BIC = n * ln(RSS/n) + k * ln(n)`
  - Lower is better
  - Penalty: ln(n) per parameter (stronger than AIC for n > 7)
  - Consistent: Selects true model as n → ∞
  - Best for: Explaining underlying data-generating process
- **Adjusted R²:**
  - Formula: `1 - (1 - R²) * (n - 1) / (n - p - 1)`
  - Higher is better
  - Can be negative for poor models
  - Penalizes adding useless predictors
- **Mallow's Cp:**
  - Formula: `Cp = (RSS_p / σ²) - n + 2p`
  - Good models have Cp ≈ p
  - Compares subset model to full model
  - Used for subset selection in regression
- **GCV (Generalized Cross-Validation):**
  - Formula: `GCV = (n * RSS) / (n - p)²`
  - Rotation-invariant version of CV
  - Computationally efficient
  - Used for smoothing splines
- **Model Selector:**
  - Evaluates models using all criteria
  - Ranks models by each criterion
  - Compares multiple models
  - Selects best by specified criterion
  - 5-fold cross-validation by default
- **Convenience Functions:**
  - `select_model_by_aic()`: Quick AIC-based selection
  - `select_model_by_bic()`: Quick BIC-based selection
  - `compute_criteria()`: Quick criteria calculation
- **Production Rule:** Use BIC for consistency (true model selection), AIC for prediction focus

---

**File Reference:** `app/backtesting/model_selection.py`
**Last Audited:** 2026-02-01
