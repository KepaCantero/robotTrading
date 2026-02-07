# Requirements: backtesting/validation/bias_variance_analysis.py

## Source File Analysis
- **File Path**: `app/backtesting/validation/bias_variance_analysis.py`
- **Lines of Code**: 790
- **Module**: Backtesting - Validation

## Purpose
Bias-Variance Decomposition and Analysis for Financial ML Models.

Implements methodologies from Hastie, Tibshirani, and Friedman's
"The Elements of Statistical Learning" (ESL), Chapter 7.

Key analyses:
1. Bias-variance decomposition using bootstrap
2. Learning curve analysis for model diagnosis
3. Temporal stability tests across time periods
4. Cross-validation stability
5. Bootstrap stability for overfitting detection

## Dependencies

### External Dependencies
- `numpy` - Numerical computations
- `sklearn.base.clone` - Model cloning for bootstrap
- `sklearn.model_selection.cross_val_score` - Cross-validation
- `logging` - Structured logging
- `dataclasses` - Data models
- `enum` - Model complexity levels
- `datetime` - Timestamps

### Internal Dependencies
- None (self-contained validation module)

## Classes/Functions

### Enum
- `ModelComplexityLevel` - UNDERFIT, OPTIMAL, OVERFIT

### Data Models (dataclass)
- `BiasVarianceResult` - Bias², variance, irreducible error, complexity level
- `LearningCurvePoint` - Train size, scores, fit time, std
- `LearningCurveResult` - Curve analysis with convergence status
- `StabilityTestResult` - Stability score, CV, performance variance

### Main Class
- `BiasVarianceAnalyzer` - Bias-variance analyzer for ML models
  - `decompose_bias_variance()` - Bootstrap-based decomposition
  - `analyze_learning_curve()` - Learning curve analysis
  - `test_temporal_stability()` - Time-period stability test
  - `test_bootstrap_stability()` - Bootstrap stability test
  - `comprehensive_analysis()` - All analyses combined

### Convenience Functions
- `analyze_bias_variance()` - Quick analysis function

## Business Logic

### Bias-Variance Decomposition
Following ESL methodology:
- **Bias²**: (E[f(x)] - y)² - How far the average prediction is from truth
- **Variance**: E[(f(x) - E[f(x)])²] - How much predictions vary
- **Irreducible Error**: σ² - Noise in the data
- **Total Error** = Bias² + Variance + Irreducible Error

Bootstrap method:
1. Generate n bootstrap samples from training data
2. Train model on each sample
3. Predict on test set
4. Decompose error into components

### Learning Curve Analysis
Diagnoses bias/variance problems by analyzing performance vs training size:
- **High Bias**: Both train and test score are low (underfitting)
- **High Variance**: Large gap between train and test (overfitting)
- **Optimal**: Converged with small gap

Convergence criterion: gap < 0.1

### Stability Tests
**Temporal Stability** (critical for trading):
- Split data into n time windows
- Test model performance in each window
- Stable if coefficient of variation (CV) < 0.2

**Bootstrap Stability**:
- Test model sensitivity to training data variations
- Stable if CV < 0.15 (stricter than temporal)

### Complexity Assessment
- **Underfit**: Bias contributes >70% of error
- **Overfit**: Variance contributes >50% of error
- **Optimal**: Balanced bias and variance

## Data Models

### BiasVarianceResult (dataclass)
```python
timestamp: datetime
model_name: str
bias_squared: float
variance: float
irreducible_error: float
total_error: float
complexity_level: ModelComplexityLevel
bias_contribution: float  # % of total error
variance_contribution: float  # % of total error
details: Dict[str, Any]
```

### LearningCurveResult (dataclass)
```python
timestamp: datetime
model_name: str
curve_points: List[LearningCurvePoint]
is_converged: bool
convergence_gap: float
potential_improvement: float
suffers_high_bias: bool
suffers_high_variance: bool
recommended_action: str
details: Dict[str, Any]
```

## API Contracts

### Configuration
- `n_bootstrap_samples`: Default 100
- `train_sizes`: Default np.linspace(0.1, 1.0, 10)
- `cv_folds`: Default 5
- `random_state`: Default 42
- `bias_threshold`: Default 0.3
- `variance_threshold`: Default 0.2

### Model Requirements
- Must have `fit()` and `predict()` methods
- Compatible with sklearn's clone() function
- Works with both regression and classification

### Return Values
- All result objects have `to_dict()` method
- Graceful fallback on errors (returns result with error details)

## Error Handling
- Bootstrap iterations: continues on failure, logs warning
- Learning curve points: skips failed points, logs warning
- Returns valid result objects even on partial failure
- All exceptions logged with context
- Never raises for model training failures

## Performance Considerations
- Bootstrap is O(n × train_time) where n is n_bootstrap_samples
- Learning curve is O(n_sizes × cv_folds × train_time)
- Temporal stability is O(n_windows × cv × train_time)
- Consider using smaller n_bootstrap for large models

## Testing Strategy
- Test with synthetic data (known bias/variance)
- Validate decomposition: bias² + var + irreducible = total
- Test learning curve convergence detection
- Verify stability thresholds
- Test edge cases: empty data, single sample

## Critical Rules (BASE_RULES.md)

### Compliance Status: ✅ PASSED

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| R099 | Absolute imports | ✅ PASS | All imports are absolute |
| R104 | No bare except | ✅ PASS | Uses `except Exception as e:` |
| R105 | No print statements | ✅ PASS | Uses `logger` throughout |
| R108 | Exception handling | ✅ PASS | Comprehensive error handling |
| R110 | Docstrings | ✅ PASS | Google-style docstrings for all classes/functions |
| R111 | No circular imports | ✅ PASS | No internal dependencies |
| R100 | Modern type hints | ✅ PASS | Uses `from __future__ import annotations` |

### Notes
- Uses modern type hints with `from __future__ import annotations`
- Proper use of dataclasses for result models
- Enum for complexity levels (type-safe)
- Well-structured with clear separation of concerns

## Trading-Specific Rules Compliance

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| BT-005 | Multiple periods | ✅ PASS | Temporal stability across time windows |
| BT-002 | Out-of-sample testing | ✅ PASS | Bootstrap and CV use out-of-sample |

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T06:00:00Z |
| **Audit Status** | PASSED |
| **Auditor** | Ralph GAP Audit Automation |
| **Violations** | 0 critical violations |

---
*Generated on 2026-02-07T06:00:00Z*
