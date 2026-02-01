# mean_variance_optimizer.py

## Purpose
Implements Markowitz Mean-Variance Optimization (MPT, 1952) with Ledoit-Wolf shrinkage, L2 regularization, and efficient frontier calculation for optimal portfolio construction.

---

## Type Definitions / Data Classes

### OptimizationMethod (Enum)
```python
MAX_SHARPE = "max_sharpe"      # Maximize Sharpe ratio (Rule 72)
MIN_VARIANCE = "min_variance"  # Minimize portfolio variance
EQUAL_WEIGHT = "equal_weight"  # Equal weight allocation
RISK_PARITY = "risk_parity"    # Inverse volatility weighting
```

### ShrinkageMethod (Enum)
```python
LEDOIT_WOLF = "ledoit_wolf"              # Ledoit-Wolf shrinkage (Rule 74)
ORACLE_APPROXIMATING = "oracle_approximating"  # OAS shrinkage
SAMPLE = "sample"                        # Sample covariance (no shrinkage)
```

### OptimizationResult (frozen dataclass)
```python
weights: NDArray[np.float64]      # Optimal portfolio weights (N,)
expected_return: float            # Portfolio expected return (annualized)
expected_risk: float              # Portfolio expected risk (annualized)
sharpe_ratio: float               # Portfolio Sharpe ratio
success: bool                     # Whether optimization succeeded
message: str                      # Status message
method: OptimizationMethod        # Method used
```

### EfficientFrontierPoint (frozen dataclass)
```python
weights: NDArray[np.float64]      # Portfolio weights (N,)
portfolio_return: float           # Expected return
portfolio_risk: float             # Expected risk (std dev)
sharpe_ratio: float               # Sharpe ratio
```

### EfficientFrontier (frozen dataclass)
```python
points: list[EfficientFrontierPoint]  # Frontier points
max_sharpe_index: int                 # Index of max Sharpe portfolio
min_variance_index: int               # Index of min variance portfolio
```

---

## Function Signatures (Contracts)

### `MeanVarianceOptimizer.__init__(lookback_days, max_position, risk_free_rate, regularization_gamma, sum_tolerance)`
**Pre:** lookback_days >= 252, max_position in (0,1], risk_free_rate in [0,1], gamma >= 0
**Post:** Optimizer initialized with validated parameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `sanitize_inputs(returns) -> NDArray[np.float64]`
**Pre:** returns is 2D array
**Post:** Returns cleaned returns with NaN and zero-volatility assets removed
**Raises:** InputValidationError if insufficient data
**Retry:** No
**Side Effects:** None (pure function)

### `calculate_covariance_matrix(returns, use_shrinkage, shrinkage_method) -> NDArray[np.float64]`
**Pre:** returns sanitized, T >= lookback_days
**Post:** Returns PSD covariance matrix (N, N) annualized
**Raises:** OptimizationError if calculation fails
**Retry:** No
**Side Effects:** Logs shrinkage application

### `max_sharpe_portfolio(expected_returns, cov_matrix, risk_free_rate) -> OptimizationResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD
**Post:** Returns OptimizationResult with max Sharpe weights
**Raises:** None (returns fallback result on failure)
**Retry:** No
**Side Effects:** Logs optimization result

### `min_variance_portfolio(expected_returns, cov_matrix) -> OptimizationResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD
**Post:** Returns OptimizationResult with minimum variance weights
**Raises:** None (returns fallback result on failure)
**Retry:** No
**Side Effects:** Logs optimization result

### `calculate_efficient_frontier(expected_returns, cov_matrix, n_points) -> EfficientFrontier`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD, n_points >= 2
**Post:** Returns EfficientFrontier with 20+ points (Rule 71)
**Raises:** OptimizationError if no points calculable
**Retry:** No
**Side Effects:** Logs frontier calculation

### `optimize(returns, method, use_shrinkage) -> OptimizationResult`
**Pre:** returns is (T, N) with T >= 252
**Post:** Returns OptimizationResult with optimal weights
**Raises:** None (catches exceptions, returns fallback)
**Retry:** No
**Side Effects:** Logs complete optimization pipeline

---

## Acceptance Criteria
- [ ] Covariance calculated with 252-day lookback (Rule 66)
- [ ] Ledoit-Wolf shrinkage applied by default (Rule 74)
- [ ] L2 regularization with gamma=0.01 (Rule 73)
- [ ] Long-only constraint enforced: 0 <= w[i] <= 1 (Rule 68)
- [ ] Sum constraint validated: sum(w) = 1.0 (Rule 69)
- [ ] Diversification enforced: max 20% per asset (Rule 70)
- [ ] Efficient frontier has 20+ points (Rule 71)
- [ ] Max Sharpe portfolio is default optimization (Rule 72)
- [ ] Covariance matrix is PSD (positive semi-definite)
- [ ] False diversification detected when avg correlation > 0.85 (Rule 14)
- [ ] Risk parity fallback when optimization fails (Rule 13)
- [ ] NaN and zero-volatility assets removed (Rule 15)
- [ ] Returns annualized by multiplying by 252
- [ ] Exception handling with equal weights fallback
- [ ] Structured logging throughout (LOG-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance PSD validation | ✅ OK - _is_positive_semi_definite() check |
| TRD-007 | BASE_RULES | TRADING_DAYS=252 for annualization | ✅ OK - Used throughout |
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ OK - @dataclass(frozen=True) |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All operations logged |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Separate methods for each concern |
| CC-002 | BASE_RULES | DRY principle | ✅ OK - Reusable validation methods |

---

## Dependencies
- **External:** numpy, scipy (minimize), sklearn (LedoitWolf), logging
- **Internal:** None (domain layer purity)

---

## Required Tests
- **test_mean_variance_optimizer.py:**
  - Input sanitization removes NaN assets
  - Input sanitization removes zero-volatility assets
  - Covariance calculation with Ledoit-Wolf shrinkage
  - Covariance calculation without shrinkage
  - PSD enforcement via eigenvalue clipping
  - Max Sharpe portfolio optimization
  - Min variance portfolio optimization
  - Regularized MVO with L2 penalty
  - Long-only constraint enforcement
  - Sum constraint validation
  - Diversification constraint (max 20%)
  - Efficient frontier calculation (20+ points)
  - False diversification detection
  - Risk parity fallback
  - Rebalance trigger detection
  - Complete optimization pipeline
  - Exception handling with fallback
  - Configuration validation

---

## Notes
Mean-Variance Optimization is foundational but sensitive to estimation errors. Shrinkage and regularization are critical for robustness. Code follows clean architecture with pure functions and no side effects.
