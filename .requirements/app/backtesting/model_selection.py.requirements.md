# Requirements: app/backtesting/model_selection.py

## Purpose
Model Selection Criteria for Statistical Learning following Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning" (ESL) Chapter 7.

## Key Requirements

### 1. Information Criterion Calculators

#### AICCalculator
- **Formula**: `AIC = n * ln(RSS/n) + 2k`
- Where: n = sample size, RSS = residual sum of squares, k = number of parameters
- **Behavior**: Returns comparable values; can be negative when model fit is very good (RSS/n < 1)
- **Methods**:
  - `calculate(y_true, y_pred, n_params, estimate_sigma=True)`: Calculate from predictions
  - `calculate_with_likelihood(log_likelihood, n_params)`: Calculate from log-likelihood

#### BICCalculator
- **Formula**: `BIC = n * ln(RSS/n) + k * ln(n)`
- **Behavior**: Stronger complexity penalty than AIC; can be negative
- **Methods**:
  - `calculate(y_true, y_pred, n_params, estimate_sigma=True)`: Calculate from predictions
  - `calculate_with_likelihood(log_likelihood, n_params, n_samples)`: Calculate from log-likelihood

#### AdjustedR2Calculator
- **Formula**: `Adjusted R² = 1 - (1 - R²) * (n - 1) / (n - p - 1)`
- Range: (-∞, 1], higher is better
- Can be negative for poor model fits

#### MallowCpCalculator
- **Formula**: `Cp = (RSS_p / σ²) - n + 2p`
- Good models have Cp ≈ p

#### GCVCalculator
- **Formula**: `GCV = (n * RSS) / (n - p)²`
- For linear models approximation

### 2. ModelSelector Class

#### Initialization
- `cv_folds`: Number of cross-validation folds (default: 5)
- `random_state`: Random seed (default: 42)

#### Methods
- `evaluate_model(model, X, y, model_name)`: Evaluate single model using all criteria
- `compare_models(models, X, y)`: Compare multiple models
- `select_best_model(models, X, y, criterion)`: Select best model by criterion
- `compute_information_criteria(y_true, y_pred, n_params)`: Compute all criteria

### 3. Data Classes

#### ModelCriterionResult
- Contains: timestamp, model_name, criterion_type, criterion_value, n_params, n_samples
- Performance metrics: mse, rmse, r2, adjusted_r2
- Statistics: log_likelihood, aic, bic
- Ranking and details dictionary
- `to_dict()`: Serialization method

#### ModelComparisonResult
- Contains: timestamp, models list, best models by each criterion
- Comparison table as DataFrame
- `to_dict()`: Serialization method

### 4. Convenience Functions
- `select_model_by_aic(models, X, y)`: Select best model by AIC
- `select_model_by_bic(models, X, y)`: Select best model by BIC
- `compute_criteria(y_true, y_pred, n_params)`: Compute all criteria

## Important Notes

### AIC/BIC Sign Interpretation
- AIC and BIC are **comparative metrics**, not absolute measures
- They **can be negative** when model fit is very good (RSS/n < 1)
- The **relative difference** (ΔAIC, ΔBIC) is what matters for model selection
- Lower values indicate better models

### Test Requirements
- Tests should verify type checking (float), not positivity
- Tests should verify comparative behavior (more params → higher penalty)
- Perfect predictions result in log(RSS/n) → -∞, causing -∞ AIC/BIC

## Mathematical Reference
- ESL Chapter 7: Model Assessment and Selection
- ESL Chapter 9: Generalized Linear Models and Regression Splines

## Audit Results (2025-02-02)

### Issues Found
1. **Test assertions incorrectly expected AIC/BIC to be positive** - The tests asserted `aic > 0` and `bic > 0`, but these metrics can be negative when the model fit is very good (when RSS/n < 1, ln(RSS/n) is negative). This is mathematically correct behavior since these are comparative metrics.

### Fixes Applied
1. **Fixed `test_aic_calculation`** - Changed assertion from `aic > 0` to `np.isfinite(aic)` with explanation
2. **Fixed `test_bic_calculation`** - Changed assertion from `bic > 0` to `np.isfinite(bic)` with explanation
3. **Fixed `test_evaluate_single_model`** - Changed AIC/BIC positivity checks to finiteness checks

### Validation
- Syntax check: `python -m py_compile app/backtesting/model_selection.py` - PASSED
- Unit tests: `pytest tests/unit/backtesting/test_model_selection.py -v` - **26 PASSED**

### Modified Files
- `/Users/kepa.cantero/Projects/algoTrading/tests/unit/backtesting/test_model_selection.py` - Fixed test assertions
- `/Users/kepa.cantero/Projects/algoTrading/app/backtesting/model_selection.py` - No changes needed (implementation correct)

