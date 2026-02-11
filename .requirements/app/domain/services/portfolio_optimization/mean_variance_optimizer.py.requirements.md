# mean_variance_optimizer.py

## Purpose
Domain service file for Mean-Variance portfolio optimization (Markowitz)

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### OptimizationResult
**Purpose:** Result of portfolio optimization.
**Fields:**
- weights: np.ndarray - Optimal weights
- expected_return: float - Expected portfolio return (annualized)
- expected_risk: float - Expected portfolio risk (std dev, annualized)
- sharpe_ratio: float - Sharpe ratio
- symbols: List[str] - Asset symbols
- converged: bool - Whether optimization converged
- message: str - Optimizer message

### EfficientFrontier
**Purpose:** Efficient frontier points.
**Fields:**
- returns: np.ndarray - Portfolio returns (annualized)
- risks: np.ndarray - Portfolio risks (std dev, annualized)
- weights_list: List[np.ndarray] - Weight sets for each point
- sharpe_ratios: np.ndarray - Sharpe ratios

### MeanVarianceOptimizer
**Purpose:** Mean-variance portfolio optimizer (Markowitz).

Implements classic Markowitz optimization:
- Maximize Sharpe ratio
- Minimize variance
- Target return optimization
- Efficient frontier computation

---

## Function Signatures (Contracts)

### `OptimizationResult.weights_dict(self) -> Dict[str, float]`
**Pre:** None
**Post:** Returns weights as {symbol: weight} dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None

### `OptimizationResult.get_allocation(self, total_capital: Decimal) -> Dict[str, Decimal]`
**Pre:** total_capital > 0
**Post:** Returns {symbol: allocation} dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None

### `EfficientFrontier.get_max_sharpe_point(self) -> Tuple[int, float, float]`
**Pre:** Sharpe ratios not empty
**Post:** Returns (index, return, risk) of max Sharpe point
**Raises:** None
**Retry:** No
**Side Effects:** None

### `EfficientFrontier.get_min_variance_point(self) -> Tuple[int, float, float]`
**Pre:** Risks not empty
**Post:** Returns (index, return, risk) of min variance point
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MeanVarianceOptimizer.maximize_sharpe(self, cov_result: CovarianceResult) -> OptimizationResult`
**Pre:** cov_result.covariance_matrix is PSD
**Post:** OptimizationResult with maximum Sharpe ratio weights
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** Logs failure if optimization doesn't converge

### `MeanVarianceOptimizer.minimize_variance(self, cov_result: CovarianceResult) -> OptimizationResult`
**Pre:** cov_result.covariance_matrix is PSD
**Post:** OptimizationResult with minimum variance weights
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** Logs failure if optimization doesn't converge

### `MeanVarianceOptimizer.target_return(self, cov_result: CovarianceResult, target_return: float) -> OptimizationResult`
**Pre:** cov_result.covariance_matrix is PSD, target_return achievable
**Post:** OptimizationResult with weights for target return
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** Logs failure if optimization doesn't converge

### `MeanVarianceOptimizer.compute_efficient_frontier(self, cov_result: CovarianceResult, n_points: int = DEFAULT_EFFICIENT_FRONTIER_POINTS) -> EfficientFrontier`
**Pre:** n_points >= 2, cov_result valid
**Post:** EfficientFrontier with n_points (or fewer if some infeasible)
**Raises:** ValueError if n_points < 2
**Retry:** No
**Side Effects:** Skips infeasible targets with debug logging

### `MeanVarianceOptimizer.get_global_minimum_variance(self, cov_result: CovarianceResult) -> OptimizationResult`
**Pre:** cov_result.covariance_matrix is invertible
**Post:** OptimizationResult with GMV weights (analytical solution)
**Raises:** ValueError if matrix inversion fails
**Retry:** No
**Side Effects:** None


---

## Acceptance Criteria
- [x] **AC-001:** All public methods have complete type hints ✅ PASSED
- [x] **AC-002:** NumPy 2.0 compatibility ✅ PASSED
- [x] **AC-003:** All functions have docstrings following Google style ✅ PASSED
- [x] **AC-004:** Input validation on all public methods ✅ PASSED

---

## Audit Status

**Status:** PASSED
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0
**Notes:** File fully complies with BASE_RULES. Implements Markowitz Mean-Variance Optimization. Validates covariance matrix before optimization via validate_covariance_matrix. Uses SLSQP optimization with proper bounds and constraints. Annualizes returns using TRADING_DAYS = 252. Handles optimization failures with log_optimization_failure. Provides analytical solution for GMV portfolio. NumPy 2.0 compatible.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type hints on public functions | ✅ PASSED |
| CC-001 | BASE_RULES.md | All functions documented (Google style) | ✅ PASSED |
| CC-006 | BASE_RULES.md | Validate all inputs | ✅ PASSED |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ PASSED |
| TYP-002 | BASE_RULES.md | No deprecated np aliases | ✅ PASSED |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** numpy (numerical operations), scipy (optimization)
- **Internal:** 
  - app.domain.services.portfolio_optimization.covariance_calculator
  - app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_mean_variance_optimizer.py:** Unit tests for:
  - Sharpe maximization with valid inputs
  - Variance minimization
  - Target return optimization
  - Efficient frontier computation
  - Global minimum variance (analytical)
  - Constraint validation (weights sum to 1, bounds)
  - Covariance matrix validation
  - Optimization failure handling

---

## Notes

**File Reference:** `app/domain/services/portfolio_optimization/mean_variance_optimizer.py`
**Created:** 2026-02-05
**Status:** ✅ AUDIT PASSED
