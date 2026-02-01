# cla.py

## Purpose
Implements the Critical Line Algorithm (CLA) for computing the efficient frontier and finding optimal corner portfolios in mean-variance optimization.

---

## Type Definitions / Data Classes

### CornerPortfolio (dataclass)
```python
weights: np.ndarray              # Portfolio weights (sum to 1.0)
expected_return: float           # Expected return (annualized)
variance: float                  # Portfolio variance
lambda_val: float                # Lagrange multiplier for return constraint
in_assets: List[int]             # Indices of assets with positive weights
out_assets: List[int]            # Indices of assets at bounds (zero weight)
symbols: List[str]               # Asset symbols
```

**Properties:**
- risk: float (sqrt(variance)) - Portfolio standard deviation

**Validation Rules:**
- weights sum to approximately 1.0
- variance >= 0
- len(weights) == len(symbols)
- expected_return matches weights @ returns

### EfficientFrontierCLA (dataclass)
```python
corner_portfolios: List[CornerPortfolio]  # Corner portfolios on frontier
n_portfolios: int                          # Number of corner portfolios
symbols: List[str]                         # Asset symbols
```

**Methods:**
- get_portfolio_for_return(target_return, cov_matrix) -> np.ndarray
- get_max_sharpe_portfolio(risk_free_rate) -> Optional[CornerPortfolio]

**Validation Rules:**
- corner_portfolios sorted by expected_return (ascending)
- n_portfolios == len(corner_portfolios)
- All corner portfolios have same symbols

### CriticalLineAlgorithm (class)
```python
_min_weight: float              # Minimum weight per asset (default: 0.0)
_max_weight: float              # Maximum weight per asset (default: 1.0)
```

**Constants:**
- DEFAULT_MIN_WEIGHT = 0.0
- DEFAULT_MAX_WEIGHT = 1.0
- DEFAULT_FRONTIER_POINTS = 10
- DEFAULT_LAMBDA_VAL = 0.0
- DEFAULT_WEIGHT_TOLERANCE = 1e-10
- DEFAULT_TURNOVER_COEFFICIENT = 0.5

---

## Function Signatures (Contracts)

### `CriticalLineAlgorithm.__init__(min_weight, max_weight, allow_short)`
**Pre:** min_weight >= (-1.0 if allow_short else 0.0), max_weight <= 1.0, min_weight <= max_weight
**Post:** CLA optimizer initialized with constraints
**Raises:** ValueError if weight bounds invalid
**Retry:** No
**Side Effects:** None

### `compute_efficient_frontier(expected_returns, cov_matrix, symbols) -> EfficientFrontierCLA`
**Pre:** expected_returns is 1D array, cov_matrix is NxN positive semidefinite
**Post:** Returns EfficientFrontierCLA with corner portfolios
**Raises:** ValueError if covariance matrix invalid or optimization fails
**Retry:** No
**Side Effects:** Logs optimization failures

**Algorithm:**
1. Validate covariance matrix (PSD, symmetry)
2. Compute minimum variance portfolio
3. Compute max return portfolio (single asset)
4. Generate intermediate portfolios at different return levels
5. Return frontier with all corner portfolios

### `_solve_min_variance(cov_matrix, symbols) -> CornerPortfolio`
**Pre:** cov_matrix is positive semidefinite
**Post:** Returns minimum variance portfolio
**Raises:** ValueError if matrix inversion fails
**Retry:** No
**Side Effects:** None

**Formula:**
- w = Σ^(-1) * 1 / (1' * Σ^(-1) * 1)
- Apply bounds and renormalize

### `_solve_target_return(expected_returns, cov_matrix, target_return, symbols) -> CornerPortfolio`
**Pre:** target_return achievable within bounds
**Post:** Returns portfolio for target return
**Raises:** None (returns x0 if optimization fails)
**Retry:** No
**Side Effects:** Logs failure if optimization unsuccessful

**Optimization:**
- Minimize: w'Σw (variance)
- Constraints: sum(w) = 1, w'μ = target_return
- Bounds: min_weight <= w_i <= max_weight
- Method: SLSQP (scipy.optimize.minimize)

### `EfficientFrontierCLA.get_portfolio_for_return(target_return, cov_matrix) -> np.ndarray`
**Pre:** cov_matrix matches frontier dimensions
**Post:** Returns optimal weights for target return (interpolated if needed)
**Raises:** None
**Retry:** No
**Side Effects:** None

**Interpolation:**
- If target_return <= min return: return min variance portfolio
- If target_return >= max return: return max return portfolio
- Otherwise: linear interpolation between neighboring corner portfolios

### `EfficientFrontierCLA.get_max_sharpe_portfolio(risk_free_rate) -> Optional[CornerPortfolio]`
**Pre:** risk_free_rate is annual rate
**Post:** Returns portfolio with maximum Sharpe ratio
**Raises:** None
**Retry:** No
**Side Effects:** None

**Formula:**
- Sharpe = (expected_return - risk_free_rate) / risk
- Returns corner portfolio with maximum Sharpe

### `compute_turnover(old_weights, new_weights) -> float`
**Pre:** weights arrays have same length
**Post:** Returns turnover (0-1)
**Raises:** None
**Retry:** No
**Side Effects:** None

**Formula:**
- Turnover = 0.5 * Σ|w_new - w_old|

---

## Acceptance Criteria
- [ ] Covariance matrix validated for PSD and symmetry
- [ ] Minimum variance portfolio computed analytically
- [ ] Target return optimization uses quadratic programming
- [ ] Corner portfolios sorted by expected return
- [ ] Weights sum to 1.0 (within tolerance)
- [ ] All weights within [min_weight, max_weight]
- [ ] Interpolation for target returns between corner portfolios
- [ ] Maximum Sharpe portfolio identified correctly
- [ ] Turnover calculation accurate
- [ ] Optimization failures logged with context
- [ ] Matrix inversion failures raise ValueError
- [ ] Invalid weight bounds raise ValueError

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance matrix PSD validation | ✅ OK - validate_covariance_matrix called |
| TRD-007 | BASE_RULES | Document TRADING_DAYS = 252 | ✅ OK - Imported from _validation |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |
| TYP-001 | BASE_RULES | Type hints | ✅ OK - Full type coverage |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError for invalid inputs |
| LOG-004 | BASE_RULES | Log exceptions with context | ✅ OK - log_optimization_failure |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Only CLA logic |
| CC-007 | BASE_RULES | Small functions | ✅ OK - Most methods < 30 lines |

### Portfolio Optimization Specific Rules (Markowitz, López de Prado)

| Rule ID | Rule | Priority | Status |
|---------|------|----------|--------|
| OPT-001 | Covariance matrix must be positive semidefinite | **P0** | ✅ OK |
| OPT-002 | Weights must sum to 1.0 (fully invested) | **P0** | ✅ OK |
| OPT-003 | All weights within bounds | **P0** | ✅ OK |
| OPT-004 | Minimize variance for target return | **P0** | ✅ OK |
| OPT-005 | Corner portfolios identify asset entry/exit | **P0** | ✅ OK |
| OPT-006 | Efficient frontier computed in single run | **P1** | ✅ OK |
| OPT-007 | Use analytical solution for min variance | **P1** | ✅ OK |
| OPT-008 | Use QP for constrained optimization | **P1** | ✅ OK |

---

## Dependencies
- **External:**
  - numpy (np) - for matrix operations
  - scipy.optimize.minimize - for quadratic programming
  - logging - for optimization failure logging
  - dataclasses, typing - for type hints
- **Internal:**
  - app.domain.services.portfolio_optimization._validation
    - validate_covariance_matrix
    - log_optimization_failure
    - TRADING_DAYS

---

## Required Tests
- **test_cla.py:**
  - **Success paths:**
    - test_compute_efficient_frontier_valid_inputs: Returns frontier with corner portfolios
    - test_min_variance_portfolio: Weights minimize variance
    - test_target_return_portfolio: Achieves target return
    - test_corner_portfolios_sorted: Sorted by expected_return
    - test_weights_sum_to_one: Sum approximately 1.0
    - test_weights_within_bounds: All weights in [min, max]
    - test_get_portfolio_for_return_interpolation: Interpolates between corners
    - test_get_portfolio_for_return_below_min: Returns min variance portfolio
    - test_get_portfolio_for_return_above_max: Returns max return portfolio
    - test_get_max_sharpe_portfolio: Returns portfolio with max Sharpe
    - test_compute_turnover: Correct turnover calculation
    - test_allow_short_allows_negative_weights: Negative weights allowed
    - test_disallow_short_no_negative_weights: All weights >= 0
  - **Error paths:**
    - test_invalid_covariance_matrix_raises: ValueError for non-PSD matrix
    - test_invalid_weight_bounds_raises: ValueError for min > max
    - test_matrix_inversion_failure_raises: ValueError for singular matrix
    - test_optimization_failure_logs: Logs optimization failures
  - **Edge cases:**
    - test_single_asset_frontier: Works with one asset
    - test_two_asset_frontier: Correct corner portfolios
    - test_zero_correlation_assets: Uncorrelated assets handled
    - test_perfect_correlation_assets: Perfect correlation handled
    - test_min_weight_equals_max_weight: Single weight for all assets
    - test_target_return_unachievable: Returns closest portfolio

---

## Notes
**Critical Implementation Details:**
- CLA computes all optimal portfolios in one run (more efficient than solving for each target return)
- Corner portfolios identify where assets enter/exit the optimization
- Interpolation used for target returns between corner portfolios
- scipy.optimize.minimize with SLSQP method for constrained QP
- Analytical solution for minimum variance (unconstrained case)
- Covariance validation prevents numerical issues
- Logging of optimization failures aids debugging

**Mathematical Foundation:**
- Based on Markowitz (1956) "The Optimization of a Quadratic Function Subject to Linear Constraints"
- Solves mean-variance optimization: min(w'Σw) s.t. w'1 = 1, w'μ = target
- Critical lines identify turning points in efficient frontier
- Lagrange multipliers track shadow prices of constraints

**Limitations:**
- Assumes returns and covariance are known (estimation risk not addressed)
- Single-period optimization (no transaction costs, no multi-period)
- Requires PSD covariance matrix (uses enforcement if needed)
