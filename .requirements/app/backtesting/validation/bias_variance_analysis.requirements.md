# bias_variance_analysis.py

## Purpose
Implements bias-variance decomposition and analysis following Hastie/Tibshirani/Friedman's ESL methodology to diagnose model underfitting/overfitting and guide model complexity selection.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### BiasVarianceResult Class/DataClass
```python
@dataclass
class BiasVarianceResult:
    timestamp: datetime                  # REQUIRED - Analysis timestamp
    model_name: str                      # REQUIRED - Name of model analyzed
    bias_squared: float                  # REQUIRED, >= 0 - Squared bias component
    variance: float                      # REQUIRED, >= 0 - Variance component
    irreducible_error: float             # REQUIRED, >= 0 - Noise component (σ²)
    total_error: float                   # REQUIRED, >= 0 - Total MSE = bias² + variance + noise
    complexity_level: ModelComplexityLevel # REQUIRED - UNDERFIT/OPTIMAL/OVERFIT
    bias_contribution: float             # REQUIRED, [0, 100] - % of error from bias
    variance_contribution: float         # REQUIRED, [0, 100] - % of error from variance
    details: Dict[str, Any]              # OPTIONAL - Additional analysis details
```

**Validation Rules:**
- `bias_squared >= 0`, `variance >= 0`, `irreducible_error >= 0`
- `total_error = bias_squared + variance + irreducible_error`
- `bias_contribution + variance_contribution <= 100` (remainder is noise)
- `complexity_level` must be ModelComplexityLevel enum value

### LearningCurvePoint Class/DataClass
```python
@dataclass
class LearningCurvePoint:
    train_size: int                      # REQUIRED - Number of training samples
    train_score: float                   # REQUIRED - Training set score
    test_score: float                    # REQUIRED - Test set score
    fit_time: float                      # REQUIRED, >= 0 - Time to fit model
    train_std: float = 0.0               # OPTIONAL, >= 0 - Std dev of training scores
    test_std: float = 0.0                # OPTIONAL, >= 0 - Std dev of test scores
```

**Validation Rules:**
- `train_size >= 1`
- `fit_time >= 0`
- Scores in valid range for metric (e.g., [0, 1] for accuracy, R²)

### LearningCurveResult Class/DataClass
```python
@dataclass
class LearningCurveResult:
    timestamp: datetime                  # REQUIRED - Analysis timestamp
    model_name: str                      # REQUIRED - Name of model analyzed
    curve_points: List[LearningCurvePoint] # REQUIRED - Points on learning curve
    is_converged: bool                   # REQUIRED - Has training converged?
    convergence_gap: float               # REQUIRED - Gap between train/test at max size
    potential_improvement: float         # REQUIRED - Estimated improvement with more data
    suffers_high_bias: bool              # REQUIRED - Underfitting detected?
    suffers_high_variance: bool          # REQUIRED - Overfitting detected?
    recommended_action: str              # REQUIRED - Human-readable recommendation
    details: Dict[str, Any]              # OPTIONAL - Additional analysis details
```

**Validation Rules:**
- `curve_points` must have at least 1 point
- `convergence_gap = train_score - test_score` at final point
- `is_converged = convergence_gap < 0.1`
- `suffers_high_bias = train_score < 0.8`
- `suffers_high_variance = convergence_gap > 0.2`

### StabilityTestResult Class/DataClass
```python
@dataclass
class StabilityTestResult:
    timestamp: datetime                  # REQUIRED - Test timestamp
    model_name: str                      # REQUIRED - Name of model tested
    test_type: str                       # REQUIRED - 'temporal_stability' or 'bootstrap_stability'
    is_stable: bool                      # REQUIRED - Model stable across tests?
    stability_score: float               # REQUIRED, [0, 1] - Higher is more stable
    performance_variance: float          # REQUIRED, >= 0 - Variance of scores
    coefficient_of_variation: float      # REQUIRED, >= 0 - CV = std/mean
    details: Dict[str, Any]              # OPTIONAL - Additional test details
```

**Validation Rules:**
- `stability_score in [0, 1]`
- `performance_variance >= 0`
- `coefficient_of_variation >= 0`
- `is_stable = coefficient_of_variation < threshold` (0.2 for temporal, 0.15 for bootstrap)

---

## Function Signatures (Contracts)

### `BiasVarianceAnalyzer.decompose_bias_variance(model, X, y, n_bootstrap=None) -> BiasVarianceResult`
**Pre:** model must have fit() and predict() methods; X, y must have same length; n_bootstrap >= 1
**Post:** Returns BiasVarianceResult with bias² + variance + irreducible_error = total_error
**Raises:** Returns result with error details if bootstrap fails
**Retry:** ❌ No
**Side Effects:** Sets random seed; clones and fits model multiple times

### `BiasVarianceAnalyzer.analyze_learning_curve(model, X, y, train_sizes=None, cv=None, scoring=None) -> LearningCurveResult`
**Pre:** model must have fit() and score() methods; X, y must have same length
**Post:** Returns LearningCurveResult with points for each train_size
**Raises:** Returns result with error details if analysis fails
**Retry:** ❌ No
**Side Effects:** Clones and fits model multiple times across train sizes

### `BiasVarianceAnalyzer.test_temporal_stability(model, X, y, timestamps, n_windows=5) -> StabilityTestResult`
**Pre:** model must have fit() and score() methods; X, y, timestamps must have same length
**Post:** Returns StabilityTestResult with is_stable = (CV < 0.2)
**Raises:** Returns result with error details if test fails
**Retry:** ❌ No
**Side Effects:** Clones model and performs CV on each time window

### `BiasVarianceAnalyzer.test_bootstrap_stability(model, X, y, n_bootstrap=None) -> StabilityTestResult`
**Pre:** model must have fit() and score() methods; X, y must have same length
**Post:** Returns StabilityTestResult with is_stable = (CV < 0.15)
**Raises:** Returns result with error details if bootstrap fails
**Retry:** ❌ No
**Side Effects:** Sets random seed; clones and fits model on bootstrap samples

### `BiasVarianceAnalyzer.comprehensive_analysis(model, X, y, timestamps=None) -> Dict[str, Any]`
**Pre:** model must have fit(), predict(), score() methods; X, y must have same length
**Post:** Returns dict with bias_variance, learning_curve, temporal_stability (if timestamps), bootstrap_stability
**Raises:** No explicit exceptions (individual tests catch errors)
**Retry:** ❌ No
**Side Effects:** Calls all analysis methods; logs errors for failed analyses

### `analyze_bias_variance(model, X, y, config=None) -> Dict[str, Any]`
**Pre:** model must be sklearn-compatible; X, y must be numpy arrays
**Post:** Returns dict from comprehensive_analysis
**Raises:** Exceptions from BiasVarianceAnalyzer
**Retry:** ❌ No
**Side Effects:** Creates BiasVarianceAnalyzer instance

---

## Acceptance Criteria
- [ ] decompose_bias_variance() uses bootstrap to estimate bias² and variance
- [ ] Total error = bias² + variance + irreducible_error (within numerical tolerance)
- [ ] analyze_learning_curve() generates points for all train_sizes
- [ ] is_converged correctly identifies convergence (gap < 0.1)
- [ ] suffers_high_bias detects underfitting (train_score < 0.8)
- [ ] suffers_high_variance detects overfitting (gap > 0.2)
- [ ] test_temporal_stability() calculates CV correctly
- [ ] test_bootstrap_stability() is more stringent (CV < 0.15)
- [ ] comprehensive_analysis() runs all tests
- [ ] Complexity level matches bias/variance contributions
- [ ] Edge cases: small datasets, failed bootstrap, edge train sizes

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses logger.error for failed analyses |
| LOG-005 | BASE_RULES.md | Never log passwords/tokens | ✅ OK - No sensitive data logged |
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - Complete type coverage |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - Tests not in scope |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Pure domain logic, no framework deps |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Analyzer handles only bias-variance analysis |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses field(default_factory=dict) |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - info/warning/error used correctly |

**NOTE:** This analysis considers all 96+ rules from BASE_RULES.md. File demonstrates strong statistical analysis patterns with proper error handling and logging.

---

## Dependencies
- **External:** numpy, logging, typing, time, sklearn (clone, cross_val_score)
- **Internal:** None (standalone validation module)

---

## Required Tests
- **tests/backtesting/validation/test_bias_variance_analysis.py:**
  - Test BiasVarianceAnalyzer initialization with config
  - Test decompose_bias_variance() returns valid decomposition
  - Test decompose_bias_variance(): bias² + variance + noise = total
  - Test decompose_bias_variance() handles bootstrap failures
  - Test analyze_learning_curve() generates correct points
  - Test analyze_learning_curve() detects convergence
  - Test analyze_learning_curve() diagnoses high bias
  - Test analyze_learning_curve() diagnoses high variance
  - Test analyze_learning_curve() provides recommendations
  - Test test_temporal_stability() calculates CV correctly
  - Test test_bootstrap_stability() is more stringent than temporal
  - Test comprehensive_analysis() runs all tests
  - Test comprehensive_analysis() skips temporal if no timestamps
  - Test analyze_bias_variance() convenience function
  - Test ModelComplexityLevel determination logic
  - Test edge cases: n_samples < 10, failed bootstrap, single train size

---

## Notes
Implements ESL Chapter 7 methodology for model assessment. Critical for diagnosing model performance issues: high bias = underfit (need more complexity/features), high variance = overfit (need more data/regularization). Bootstrap resampling key for variance estimation.
