# cla.py

## Purpose
Critical Line Algorithm (CLA) - computes the efficient frontier and optimal corner portfolios for mean-variance optimization.

---

## Type Definitions / Data Classes

### CornerPortfolio
```python
@dataclass
class CornerPortfolio:
    weights: np.ndarray              # REQUIRED - Portfolio weights
    expected_return: float           # REQUIRED - Expected portfolio return
    variance: float                  # REQUIRED - Portfolio variance
    lambda_val: float                # REQUIRED - Lagrange multiplier
    in_assets: List[int]             # REQUIRED - Assets with positive weights
    out_assets: List[int]            # REQUIRED - Assets at bounds (zero weight)
    symbols: List[str]               # REQUIRED - Asset symbols
```

**Properties:**
- `risk` - Returns √variance (portfolio standard deviation)

**Validation Rules:**
- `weights` must sum to 1.0 (within numerical tolerance)
- `in_assets` ∪ `out_assets` = all asset indices
- `in_assets` ∩ `out_assets` = ∅

### EfficientFrontierCLA
```python
@dataclass
class EfficientFrontierCLA:
    corner_portfolios: List[CornerPortfolio]  # REQUIRED - Corner portfolios
    n_portfolios: int                         # REQUIRED - Number of corners
    symbols: List[str]                        # REQUIRED - Asset symbols
```

**Methods:**
- `get_portfolio_for_return(target_return, cov_matrix)` - Interpolates weights
- `get_max_sharpe_portfolio(risk_free_rate)` - Returns max Sharpe corner

---

## Function Signatures (Contracts)

### `CriticalLineAlgorithm.__init__(min_weight, max_weight, allow_short) -> None`
**Pre:** min_weight >= -1.0 (if allow_short), min_weight >= 0 otherwise; max_weight <= 1.0
**Post:** Optimizer configured with bounds
**Raises:** ValueError if bounds invalid
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `compute_efficient_frontier(expected_returns, cov_matrix, symbols) -> EfficientFrontierCLA`
**Pre:** cov_matrix must be square, symmetric, and positive semidefinite; expected_returns length = n_assets
**Post:** Returns efficient frontier with corner portfolios
**Raises:** ValueError if covariance matrix invalid or matrix inversion fails (logged)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_solve_min_variance(cov_matrix, symbols) -> CornerPortfolio` (private)
**Pre:** cov_matrix must be invertible
**Post:** Returns minimum variance portfolio (analytical solution)
**Raises:** ValueError if covariance matrix is singular (logged)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_solve_target_return(expected_returns, cov_matrix, target_return, symbols) -> CornerPortfolio` (private)
**Pre:** cov_matrix valid; target_return achievable within bounds
**Post:** Returns portfolio minimizing variance for target return
**Raises:** Logs error if optimization fails
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `EfficientFrontierCLA.get_portfolio_for_return(target_return, cov_matrix) -> np.ndarray`
**Pre:** target_return within frontier range (or extrapolates)
**Post:** Returns optimal weights via linear interpolation
**Raises:** None (returns corner portfolio if outside range)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `EfficientFrontierCLA.get_max_sharpe_portfolio(risk_free_rate) -> CornerPortfolio`
**Pre:** risk_free_rate >= 0
**Post:** Returns corner portfolio with maximum Sharpe ratio
**Raises:** None (returns None if no corner portfolios)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `compute_turnover(old_weights, new_weights) -> float` (module function)
**Pre:** old_weights and new_weights same length; both sum to 1.0
**Post:** Returns 0.5 × Σ|w_new - w_old|
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** Covariance matrix validated before inversion (PSD check, condition number) ✅ FIXED
- [x] **AC-002:** Matrix inversion errors logged with context ✅ FIXED
- [x] **AC-003:** Edge case handling: singular covariance, infeasible target return ✅ FIXED
- [x] **AC-004:** All public methods have complete type hints ✅ OK
- [x] **AC-005:** NumPy 2.0 compatibility ✅ OK
- [x] **AC-006:** All functions have docstrings following Google style ✅ OK
- [x] **AC-007:** Corner portfolio ordering verified (monotonic return increase) ✅ OK
- [x] **AC-008:** Magic numbers documented as constants ✅ FIXED

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (CLA - Markowitz):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PSD validation | BASE_RULES.md (TRD-001) | Validate covariance matrix is positive semidefinite | ✅ FIXED - validate_covariance_matrix() |
| Matrix inversion error handling | BASE_RULES.md (LOG-004) | Log LinAlgError from np.linalg.inv | ✅ FIXED - log_optimization_failure() |
| Input sanitization | BASE_RULES.md (TRD-015) | Remove NaN, zero variance assets | ⚠️ NOT APPLIED - Depends on validated input |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy/scipy |
| Corner portfolio identification | Markowitz (1956) | Identify turning points where assets enter/exit | ⚠️ PARTIAL - Simplified implementation |
| Efficient frontier computation | Markowitz (1956) | Compute all optimal portfolios simultaneously | ✅ OK - Implemented via interpolation |
| Min variance analytical solution | Markowitz | w = Σ^(-1) * 1 / (1' * Σ^(-1) * 1) | ✅ OK - Implemented |
| Turnover calculation | Trading standard | 0.5 × Σ|w_new - w_old| | ✅ OK - Implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |
| Magic numbers | BASE_RULES.md (CC-001) | Document constants | ✅ FIXED - Constants defined |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Markowitz (1956) for CLA rules.

---

## Dependencies
- **External:** `numpy`, `scipy` (optimize), `dataclasses` (std)
- **Internal:** `app.domain.services.portfolio_optimization._validation`

---

## Required Tests
- **test_cla.py:**
  - `test_efficient_frontier_valid_input()` - Happy path with valid inputs
  - `test_min_variance_analytical()` - Verify analytical solution
  - `test_corner_portfolio_ordering()` - Returns increase monotonically
  - `test_get_portfolio_for_return()` - Interpolation between corners
  - `test_get_max_sharpe_portfolio()` - Maximum Sharpe identification
  - `test_cla_singular_covariance()` - Error path with singular matrix
  - `test_cla_infeasible_target_return()` - Out-of-range target handling
  - `test_compute_turnover()` - Turnover calculation
  - `test_cla_short_selling_allowed()` - Negative weights when allow_short=True
  - `test_cla_bounds_enforcement()` - Min/max weight constraints

---

## Notes
- **Critical:** Covariance matrix must be positive semidefinite for inversion
- **Markowitz Reference:** "The Optimization of a Quadratic Function Subject to Linear Constraints" (1956)
- **Simplified Implementation:** Full CLA identifies all turning points; this version uses interpolation
- **Corner Portfolios:** Points where asset weights enter or exit the solution
- **Efficient Frontier:** All optimal portfolios for different return levels
- **Analytical Solution:** Minimum variance has closed-form: w = Σ^(-1) * 1 / (1' * Σ^(-1) * 1)
- **Linear Interpolation:** Used between corner portfolios for continuous frontier
- **Turnover:** Measures portfolio change; high turnover = high transaction costs
- **Constants:** DEFAULT_MIN_WEIGHT, DEFAULT_MAX_WEIGHT, DEFAULT_FRONTIER_POINTS, etc.

---

**File Reference:** `app/domain/services/portfolio_optimization/cla.py`
**Last Audited:** 2026-02-01
**Last Fixed:** 2026-02-01 (GAPs: PSD validation, error logging, magic numbers)
