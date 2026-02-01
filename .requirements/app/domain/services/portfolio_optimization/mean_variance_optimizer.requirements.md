# mean_variance_optimizer.py

## Purpose
Markowitz Mean-Variance Portfolio Optimization - Implements classical MVO for maximizing Sharpe ratio, minimizing variance, and computing efficient frontier.

---

## Type Definitions / Data Classes

### OptimizationResult
```python
@dataclass
class OptimizationResult:
    weights: np.ndarray              # REQUIRED - Optimal portfolio weights
    expected_return: float           # REQUIRED - Annualized portfolio return
    expected_risk: float             # REQUIRED - Annualized portfolio std dev
    sharpe_ratio: float              # REQUIRED - Sharpe ratio
    symbols: List[str]               # REQUIRED - Asset symbols
    converged: bool                  # REQUIRED - Optimization convergence status
    message: str                     # REQUIRED - Optimizer message
```

**Validation Rules:**
- `weights` must sum to 1.0 (within numerical tolerance)
- `expected_return` and `expected_risk` must be annualized (×252, ×√252)
- `converged=False` should be logged as warning

### EfficientFrontier
```python
@dataclass
class EfficientFrontier:
    returns: np.ndarray              # REQUIRED - Portfolio returns
    risks: np.ndarray                # REQUIRED - Portfolio std devs
    weights_list: List[np.ndarray]   # REQUIRED - Weight sets
    sharpe_ratios: np.ndarray        # REQUIRED - Sharpe ratios
```

**Validation Rules:**
- All arrays must have same length
- At least 2 points required for frontier

---

## Function Signatures (Contracts)

### `MeanVarianceOptimizer.__init__(risk_free_rate, min_weight, max_weight, allow_short) -> None`
**Pre:** risk_free_rate >= 0, min_weight >= -1.0 (if allow_short), max_weight <= 1.0
**Post:** Optimizer configured with constraints
**Raises:** ValueError if invalid bounds
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `maximize_sharpe(cov_result: CovarianceResult) -> OptimizationResult`
**Pre:** cov_result.covariance_matrix must be positive semidefinite, cov_result.means length == n_assets
**Post:** Returns portfolio with maximum Sharpe ratio (weights sum to 1.0)
**Raises:** ValueError if optimization fails to converge (logged)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `minimize_variance(cov_result: CovarianceResult) -> OptimizationResult`
**Pre:** cov_result.covariance_matrix must be positive semidefinite
**Post:** Returns minimum variance portfolio (weights sum to 1.0)
**Raises:** ValueError if optimization fails to converge (logged)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `target_return(cov_result: CovarianceResult, target_return: float) -> OptimizationResult`
**Pre:** cov_result valid, target_return achievable within bounds
**Post:** Returns portfolio with minimum variance for target return
**Raises:** ValueError if target_return is infeasible (logged)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `compute_efficient_frontier(cov_result: CovarianceResult, n_points: int) -> EfficientFrontier`
**Pre:** cov_result valid, n_points >= 2
**Post:** Returns efficient frontier with n_points (or fewer if some infeasible)
**Raises:** None (gracefully handles infeasible points)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `get_global_minimum_variance(cov_result: CovarianceResult) -> OptimizationResult`
**Pre:** cov_result.covariance_matrix must be invertible
**Post:** Returns analytical GMV portfolio
**Raises:** ValueError if covariance matrix is singular (logged)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** All public methods have complete type hints (parameters + return types) ✅ OK
- [x] **AC-002:** No hardcoded numeric constants (252, √252 should be documented as TRADING_DAYS) ✅ FIXED
- [x] **AC-003:** Optimization failures (converged=False) are logged with context ✅ FIXED
- [x] **AC-004:** Covariance matrix positive semidefinite validation before optimization ✅ FIXED
- [x] **AC-005:** Edge case handling: empty symbols, single asset, singular covariance matrix ✅ OK
- [x] **AC-006:** NumPy 2.0 compatibility (no deprecated np aliases) ✅ OK
- [x] **AC-007:** All functions have docstrings following Google style ✅ OK

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Type hints coverage | 02-type-hints.md | 100% type hints on public functions | ✅ OK - All methods typed |
| Docstring coverage | 00-checklist.md | All public functions documented | ✅ OK - Complete docstrings |
| NumPy 2.0 compat | 02-type-hints.md | No `np.int`, `np.float` aliases | ✅ OK - Uses `float`, `int` |
| Input validation | 05-architecture.md | Validate covariance matrix properties | ✅ FIXED - validate_covariance_matrix() |
| Error logging | 09-logging-observability.md | Log optimization failures | ✅ FIXED - log_optimization_failure() |
| No magic numbers | 05-architecture.md | Document TRADING_DAYS = 252 | ✅ FIXED - Constants in _validation.py |
| Testing coverage | 06-testing.md | >80% coverage with edge cases | ⚠️ NOT APPLIED - Tests needed |
| Domain layer purity | 05-architecture.md | No infrastructure imports | ✅ OK - Only numpy/scipy |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** `numpy`, `scipy` (optimize), `dataclasses` (std)
- **Internal:** `app.domain.services.portfolio_optimization.covariance_calculator`, `app.domain.services.portfolio_optimization._validation`

---

## Required Tests
- **test_mean_variance_optimizer.py:**
  - `test_maximize_sharpe_converges()` - Happy path with valid input
  - `test_maximize_sharpe_singular_covariance()` - Error path with singular matrix
  - `test_minimize_variance_bounds()` - Edge case with min/max weight constraints
  - `test_target_return_infeasible()` - Error path for unachievable return
  - `test_efficient_frontier_single_asset()` - Edge case with n=1
  - `test_global_minimum_variance_analytical()` - Compare analytical vs numerical
  - `test_sharpe_ratio_calculation()` - Validate annualization formula
  - `test_short_selling_allowed()` - Verify negative weights when allow_short=True

---

## Notes
- **Critical:** Covariance matrix must be positive semidefinite for optimization to succeed
- **Trading Convention:** TRADING_DAYS = 252 for annualization
- **Numerical Stability:** Uses SLSQP optimizer with DEFAULT_OPTIMIZATION_TOLERANCE
- **Markowitz Reference:** Based on "Portfolio Selection" (1952) - see rules/trading/papers/48-papers-markowitz-portfolio-selection.md

---

**File Reference:** `app/domain/services/portfolio_optimization/mean_variance_optimizer.py`
**Last Audited:** 2026-02-01
**Last Fixed:** 2026-02-01 (GAPs: PSD validation, error logging, magic numbers)
