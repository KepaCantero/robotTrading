# mean_variance_optimizer.py.requirements.md

## Purpose
Implements Markowitz Mean-Variance Optimization (MPT) with constraints, regularization, and multiple optimization methods for robust portfolio construction.

---

## Type Definitions / Data Classes

### OptimizationMethod Enum
```python
class OptimizationMethod(str, Enum):
    MAX_SHARPE = "max_sharpe"      # Maximize Sharpe ratio (Rule 72)
    MIN_VARIANCE = "min_variance"  # Minimize portfolio variance
    EQUAL_WEIGHT = "equal_weight"  # Equal weight allocation
    RISK_PARITY = "risk_parity"    # Inverse volatility weighting (Rule 13)
```

### ShrinkageMethod Enum
```python
class ShrinkageMethod(str, Enum):
    LEDOIT_WOLF = "ledoit_wolf"          # Ledoit-Wolf shrinkage (Rule 74)
    ORACLE_APPROXIMATING = "oracle_approximating"  # OAS shrinkage
    SAMPLE = "sample"                    # Sample covariance (no shrinkage)
```

### OptimizationResult DataClass
```python
@dataclass(frozen=True)
class OptimizationResult:
    weights: NDArray[np.float64]    # REQUIRED - Optimal portfolio weights (N,)
    expected_return: float          # REQUIRED - Portfolio expected return (annualized)
    expected_risk: float            # REQUIRED - Portfolio expected risk (annualized)
    sharpe_ratio: float             # REQUIRED - Portfolio Sharpe ratio
    success: bool                   # REQUIRED - Whether optimization succeeded
    message: str                    # REQUIRED - Status message
    method: OptimizationMethod      # REQUIRED - Method used
```

**Validation Rules:**
- weights must sum to 1.0 (within tolerance)
- All weights >= 0 (long-only)
- All weights <= max_position (diversification constraint)
- expected_risk > 0 for valid Sharpe calculation

### EfficientFrontierPoint DataClass
```python
@dataclass(frozen=True)
class EfficientFrontierPoint:
    weights: NDArray[np.float64]    # REQUIRED - Portfolio weights (N,)
    portfolio_return: float         # REQUIRED - Expected return
    portfolio_risk: float           # REQUIRED - Expected risk (std dev)
    sharpe_ratio: float             # REQUIRED - Sharpe ratio
```

### EfficientFrontier DataClass
```python
@dataclass(frozen=True)
class EfficientFrontier:
    points: list[EfficientFrontierPoint]  # REQUIRED - Points on frontier (20+ per Rule 71)
    max_sharpe_index: int                 # REQUIRED - Index of max Sharpe portfolio
    min_variance_index: int               # REQUIRED - Index of min variance portfolio
```

**Property Methods:**
- `max_sharpe_portfolio: EfficientFrontierPoint` - Get tangency portfolio
- `min_variance_portfolio: EfficientFrontierPoint` - Get minimum variance portfolio
- `to_arrays() -> tuple[NDArray, NDArray, NDArray]` - Convert to plotting arrays

---

## Function Signatures (Contracts)

### `MeanVarianceOptimizer.__init__(lookback_days, max_position, risk_free_rate, regularization_gamma, sum_tolerance) -> None`
**Pre:** lookback_days >= 252, max_position in (0, 1], risk_free_rate in [0, 1], gamma >= 0, tolerance in (0, 1e-3)
**Post:** Optimizer initialized with validated parameters
**Raises:** ValueError if any parameter invalid
**Retry:** No
**Side Effects:** Logs initialization parameters

### `sanitize_inputs(returns: NDArray[np.float64]) -> NDArray[np.float64]`
**Pre:** returns is 2D array (T, N) with T >= lookback_days
**Post:** Returns cleaned returns with NaN and zero-vol assets removed
**Raises:** InputValidationError if insufficient data or assets
**Retry:** No
**Side Effects:** Logs warnings for dropped assets

### `calculate_expected_returns(returns: NDArray[np.float64], annualize: bool) -> NDArray[np.float64]`
**Pre:** returns is 2D (T, N) with no NaN values
**Post:** Returns expected returns (N,) annualized if annualize=True
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_covariance_matrix(returns, use_shrinkage, shrinkage_method) -> NDArray[np.float64]`
**Pre:** returns is valid 2D array with T >= lookback_days (Rule 66)
**Post:** Returns covariance matrix (N, N) annualized with optional shrinkage (Rule 74)
**Raises:** InputValidationError, OptimizationError
**Retry:** No
**Side Effects:** Applies PSD correction if needed

### `validate_sum_constraint(weights: NDArray[np.float64]) -> bool`
**Pre:** weights is 1D array with length > 0
**Post:** Returns True if sum(weights) = 1.0 within tolerance (Rule 69)
**Raises:** None
**Retry:** No
**Side Effects:** Logs validation result

### `apply_long_only_constraint(weights: NDArray[np.float64]) -> NDArray[np.float64]`
**Pre:** weights is 1D array
**Post:** Returns weights clipped to [0, 1] and normalized to sum = 1 (Rule 68)
**Raises:** None
**Retry:** No
**Side Effects:** Logs number of clipped positions

### `apply_diversification_constraint(weights, max_weight: float | None) -> NDArray[np.float64]`
**Pre:** weights is 1D array, max_weight in (0, 1] or None
**Post:** Returns weights with no asset exceeding max_weight (Rule 70)
**Raises:** None
**Retry:** No
**Side Effects:** Iteratively redistributes excess weight

### `max_sharpe_portfolio(expected_returns, cov_matrix, risk_free_rate: float | None) -> OptimizationResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD
**Post:** Returns OptimizationResult with max Sharpe weights (Rule 72)
**Raises:** None
**Retry:** No
**Side Effects:** Uses scipy.optimize.minimize with SLSQP

### `min_variance_portfolio(expected_returns, cov_matrix) -> OptimizationResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD
**Post:** Returns OptimizationResult with minimum variance weights
**Raises:** None
**Retry:** No
**Side Effects:** None

### `regularized_mvo(expected_returns, cov_matrix, gamma: float | None) -> OptimizationResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD, gamma >= 0
**Post:** Returns OptimizationResult with L2-regularized weights (Rule 73)
**Raises:** None
**Retry:** No
**Side Effects:** Adds gamma * ||w||^2 penalty to objective

### `calculate_efficient_frontier(expected_returns, cov_matrix, n_points: int) -> EfficientFrontier`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD, n_points >= 10
**Post:** Returns EfficientFrontier with 20+ points (Rule 71)
**Raises:** OptimizationError if no frontier points calculable
**Retry:** No
**Side Effects:** Optimizes for each target return

### `check_false_diversification(cov_matrix: NDArray[np.float64], threshold: float) -> dict`
**Pre:** cov_matrix is valid (N, N), threshold in (0, 1)
**Post:** Returns dict with avg_correlation and warning if > threshold (Rule 14)
**Raises:** None
**Retry:** No
**Side Effects:** Logs error if false diversification detected

### `risk_parity_fallback(expected_returns, cov_matrix) -> OptimizationResult`
**Pre:** expected_returns (N,), cov_matrix (N, N) PSD
**Post:** Returns OptimizationResult with inverse-volatility weights (Rule 13)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `optimize(returns, method, use_shrinkage) -> OptimizationResult`
**Pre:** returns is 2D (T, N) with T >= lookback_days
**Post:** Returns OptimizationResult with optimal weights
**Raises:** None
**Retry:** No
**Side Effects:** Full pipeline: sanitize, covariance, optimize, check diversification

### `check_rebalance_trigger(current_weights, target_weights, threshold) -> dict`
**Pre:** current_weights and target_weights same shape (N,), threshold in (0, 1)
**Post:** Returns dict with rebalance flag and deviation details (Rule 9)
**Raises:** ValueError if shapes mismatch
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-MVO-001: lookback_days >= 252 (Rule 66)
- [ ] AC-MVO-002: Sum of weights = 1.0 (Rule 69) tolerance 1e-6
- [ ] AC-MVO-003: All weights >= 0 (Rule 68 - long-only)
- [ ] AC-MVO-004: All weights <= max_position (Rule 70 - diversification)
- [ ] AC-MVO-005: Efficient frontier has >= 20 points (Rule 71)
- [ ] AC-MVO-006: Default optimization is max_sharpe (Rule 72)
- [ ] AC-MVO-007: L2 regularization gamma >= 0 (Rule 73)
- [ ] AC-MVO-008: Covariance uses Ledoit-Wolf shrinkage (Rule 74)
- [ ] AC-MVO-009: False diversification warning if avg_corr > 0.85 (Rule 14)
- [ ] AC-MVO-010: Risk parity fallback on optimization failure (Rule 13)
- [ ] AC-MVO-011: Covariance matrix is positive semi-definite
- [ ] AC-MVO-012: Portfolio risk > 0 for non-zero variance
- [ ] AC-MVO-013: Sharpe ratio is finite (not NaN/inf)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance must be positive semi-definite | ✅ OK - _is_positive_semi_definite + correction |
| TRD-003 | BASE_RULES | Enforce max position size | ✅ OK - max_position constraint (Rule 70) |
| TRD-007 | BASE_RULES | Document TRADING_DAYS = 252 | ✅ OK - Lines 332, 369 |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ❌ GAP - Several functions exceed (optimize: 50+ lines) |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - Modern type hints throughout |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ❌ GAP - Generic error logging |
| TST-005 | BASE_RULES | Coverage > 80% | ⚠️ NOT APPLIED - Tests not yet written |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Separate methods for each concern |

### Markowitz MPT-Specific Rules (from papers):

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| MPT-66 | 252-day lookback for covariance (Rule 66) | ✅ OK - lookback_days=252 default |
| MPT-67 | Mean-variance optimization framework | ✅ OK - Core implementation |
| MPT-68 | Long-only constraint: 0 <= w <= 1 (Rule 68) | ✅ OK - apply_long_only_constraint |
| MPT-69 | Sum constraint: sum(w) = 1.0 (Rule 69) | ✅ OK - validate_sum_constraint |
| MPT-70 | Diversification: max 20% per asset (Rule 70) | ✅ OK - apply_diversification_constraint |
| MPT-71 | Efficient frontier: 20+ points (Rule 71) | ✅ OK - calculate_efficient_frontier |
| MPT-72 | Max Sharpe portfolio (Rule 72) | ✅ OK - max_sharpe_portfolio default |
| MPT-73 | L2 regularization gamma=0.01 (Rule 73) | ✅ OK - regularization_gamma default |
| MPT-74 | Ledoit-Wolf shrinkage (Rule 74) | ✅ OK - _shrink_covariance_matrix |

### Risk Management Rules:

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| RISK-09 | Check rebalancing trigger (Rule 9) | ✅ OK - check_rebalance_trigger |
| RISK-13 | Risk parity fallback (Rule 13) | ✅ OK - risk_parity_fallback |
| RISK-14 | False diversification detection (Rule 14) | ✅ OK - check_false_diversification |
| RISK-15 | Input sanitization (Rule 15) | ✅ OK - sanitize_inputs |

---

## Dependencies
- **External:** numpy, scipy (optimize), sklearn (covariance: LedoitWolf - optional)
- **Internal:** None (standalone domain module)

---

## Required Tests
- **tests/domain/portfolio_optimization/test_mean_variance_optimizer.py:**
  - Test initialization with valid parameters
  - Test initialization validation (invalid parameters raise ValueError)
  - Test sanitize_inputs removes NaN values
  - Test sanitize_inputs removes zero-volatility assets
  - Test sanitize_inputs raises error if insufficient assets remain
  - Test calculate_expected_returns with and without annualization
  - Test calculate_covariance_matrix with shrinkage
  - Test calculate_covariance_matrix without shrinkage
  - Test PSD correction for non-PSD covariance matrix
  - Test validate_sum_constraint with valid weights
  - Test validate_sum_constraint with invalid weights
  - Test apply_long_only_constraint clips negative weights
  - Test apply_diversification_constraint with violations
  - Test max_sharpe_portfolio optimization
  - Test min_variance_portfolio optimization
  - Test regularized_mvo with various gamma values
  - Test calculate_efficient_frontier returns 20+ points
  - Test check_false_diversification with low correlation
  - Test check_false_diversification with high correlation (> 0.85)
  - Test risk_parity_fallback returns inverse volatility weights
  - Test optimize with MAX_SHARPE method
  - Test optimize with MIN_VARIANCE method
  - Test optimize with RISK_PARITY method
  - Test optimization failure falls back to risk parity
  - Test check_rebalance_trigger with deviation
  - Test check_rebalance_trigger without deviation
  - Test all constraint enforcement (Rules 68, 69, 70)
  - Test edge cases: 2 assets only
  - Test edge cases: All assets have same return
  - Test edge cases: Perfect correlation (false diversification)

---

## Notes
- Markowitz MPT (1952) is the foundation of modern portfolio theory
- The implementation follows all key rules from the codebase (Rules 9, 13-15, 66-74)
- Long-only constraints prevent short selling (common for retail investors)
- Diversification constraint (max 20%) prevents concentration risk
- Ledoit-Wolf shrinkage is critical for robust covariance estimation with many assets
- L2 regularization prevents corner solutions and improves stability
- Risk parity fallback ensures the optimizer always returns valid weights
- Consider adding transaction cost constraints for practical implementation
- The 252-day lookback aligns with standard trading year convention
