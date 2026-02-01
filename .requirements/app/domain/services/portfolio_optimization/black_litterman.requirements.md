# black_litterman.py

## Purpose
Black-Litterman portfolio optimization - combines market equilibrium returns with investor views using Bayes' rule for more stable and intuitive portfolios than MVO.

---

## Type Definitions / Data Classes

### View
```python
@dataclass
class View:
    symbols: List[str]       # REQUIRED - Assets involved in view
    pick: np.ndarray         # REQUIRED - View weights (sums to 0 for relative)
    confidence: float        # REQUIRED - View confidence (0-1)
    expected_return: float   # REQUIRED - Expected return of view
```

**Validation Rules:**
- `confidence` must be between 0 and 1
- For relative views, `pick` must sum to approximately 0
- `expected_return` typically annualized (converted to daily internally)

### BlackLittermanResult
```python
@dataclass
class BlackLittermanResult:
    equilibrium_returns: np.ndarray  # REQUIRED - Implied equilibrium returns
    blended_returns: np.ndarray      # REQUIRED - BL blended returns
    weights: np.ndarray              # REQUIRED - Optimal portfolio weights
    symbols: List[str]               # REQUIRED - Asset symbols
    view_adjustment: np.ndarray      # REQUIRED - Adjustment from views
    expected_return: float           # REQUIRED - Annualized portfolio return
    expected_risk: float             # REQUIRED - Annualized portfolio std dev
    sharpe_ratio: float              # REQUIRED - Sharpe ratio
    converged: bool                  # REQUIRED - Optimization convergence status
```

**Validation Rules:**
- `weights` must sum to 1.0 (within numerical tolerance)
- All weights must be non-negative (long-only)
- `blended_returns` = `equilibrium_returns` + `view_adjustment`

---

## Function Signatures (Contracts)

### `BlackLittermanOptimizer.__init__(risk_aversion, risk_free_rate, tau) -> None`
**Pre:** risk_aversion > 0, risk_free_rate >= 0, tau > 0
**Post:** Optimizer configured with BL parameters
**Raises:** ValueError if parameters are invalid
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `optimize(cov_matrix, market_cap_weights, views, symbols) -> BlackLittermanResult`
**Pre:** cov_matrix must be square, symmetric, and positive semidefinite; market_cap_weights sums to 1.0 (if provided)
**Post:** Returns BL portfolio with equilibrium + views blended
**Raises:** ValueError if covariance matrix validation fails or matrix inversions fail
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `create_relative_view(symbols, outperform, underperform, confidence, expected_alpha) -> View`
**Pre:** outperform and underperform must be in symbols; 0 <= confidence <= 1
**Post:** Returns View with pick vector [1, -1] for relative outperformance
**Raises:** ValueError if symbols not found or confidence invalid
**Retry:** ❌ No
**Side Effects:** None (pure construction)

### `_calculate_implied_returns(cov_matrix, market_weights) -> np.ndarray` (private)
**Pre:** cov_matrix must be PSD; market_weights sums to 1.0
**Post:** Returns implied equilibrium returns (π = δ * Σ * w)
**Raises:** LinAlgError if covariance matrix is singular (logged with stack trace)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_combine_with_views(cov_matrix, implied_returns, views, symbols) -> Tuple[np.ndarray, np.ndarray]` (private)
**Pre:** cov_matrix valid; views have valid symbols; confidence in [0,1]
**Post:** Returns (blended_returns, view_adjustment) using BL formula
**Raises:** LinAlgError if matrix inversions fail (logged with stack trace); ValueError if view symbols not found
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_optimize_with_returns(cov_matrix, expected_returns, symbols) -> OptimizationResult` (private)
**Pre:** cov_matrix must be PSD
**Post:** Returns optimized portfolio maximizing Sharpe ratio
**Raises:** Logs optimization failures with stack trace
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** Covariance matrix validated before optimization (PSD check, symmetry) ✅ FIXED
- [x] **AC-002:** Matrix inversion errors logged with context ✅ FIXED
- [x] **AC-003:** Edge case handling: empty views, single asset, singular covariance ✅ FIXED
- [x] **AC-004:** All public methods have complete type hints ✅ OK
- [x] **AC-005:** Magic numbers documented as constants (252, tau=0.05, risk_aversion=3.0) ✅ FIXED
- [x] **AC-006:** NumPy 2.0 compatibility ✅ OK
- [x] **AC-007:** All functions have docstrings following Google style ✅ OK
- [x] **AC-008:** View validation (confidence bounds, symbol existence) ✅ OK

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Black-Litterman):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PSD validation | BASE_RULES.md (TRD-001) | Validate covariance matrix is positive semidefinite | ✅ FIXED - validate_covariance_matrix() |
| Matrix inversion error handling | BASE_RULES.md (LOG-004) | Log LinAlgError from np.linalg.inv | ✅ FIXED - log_optimization_failure() |
| Input sanitization | BASE_RULES.md (TRD-015) | Remove NaN, zero variance assets | ✅ FIXED - sanitize_covariance_matrix() |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only domain dependencies |
| Equilibrium returns | Black-Litterman (1992) | π = δ * Σ * w_market | ✅ OK - Implemented |
| Bayes' rule combination | Black-Litterman (1992) | μ_BL = [(τΣ)^(-1) + P'Ω(-1)P]^(-1) * [...] | ✅ OK - Implemented |
| View uncertainty matrix | Black-Litterman (1992) | Ω = (1-c)/c for each view | ✅ OK - Implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |
| Magic numbers | BASE_RULES.md (CC-001) | Document TRADING_DAYS, default tau, delta | ✅ FIXED - Constants in _validation.py |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Black-Litterman (1992) paper rules.

---

## Dependencies
- **External:** `numpy`, `scipy` (optimize), `dataclasses` (std)
- **Internal:**
  - `app.domain.services.portfolio_optimization.mean_variance_optimizer.MeanVarianceOptimizer`
  - `app.domain.services.portfolio_optimization._validation` (PSD validation, logging, sanitization)
  - `app.domain.services.portfolio_optimization.covariance_calculator.CovarianceResult`

---

## Required Tests
- **test_black_litterman.py:**
  - `test_bl_no_views()` - Happy path with equilibrium returns only
  - `test_bl_with_relative_view()` - Relative outperformance view
  - `test_bl_with_absolute_view()` - Absolute return view
  - `test_bl_multiple_views()` - Multiple views combined
  - `test_bl_view_confidence_scaling()` - Verify confidence affects weights
  - `test_bl_singular_covariance()` - Error path with singular matrix
  - `test_bl_market_cap_weights()` - Custom market weights
  - `test_bl_create_relative_view()` - View creation helper
  - `test_bl_invalid_view_symbols()` - Error path for invalid symbols
  - `test_bl_zero_confidence_view()` - Edge case with confidence=0
  - `test_bl_weights_sum_to_one()` - Validate weight constraint
  - `test_bl_view_adjustment_calculation()` - Verify adjustment = BL - equilibrium
  - `test_bl_psd_validation()` - PSD enforcement on covariance matrix
  - `test_bl_nan_sanitization()` - NaN handling in returns/covariance

---

## Notes
- **Critical:** Covariance matrix must be positive semidefinite for matrix inversions
- **Black-Litterman Reference:** Addresses two MVO issues: (1) Estimation error in expected returns, (2) Concentration of weights
- **Key Formula:** Implied returns π = δ * Σ * w_market (where δ = risk aversion)
- **View Uncertainty:** Ω[i,i] = (1 - confidence) / confidence (higher confidence → lower uncertainty)
- **Trading Convention:** Assumes 252 trading days/year for annualization (TRADING_DAYS constant)
- **Risk Aversion Default:** δ = 3.0 (DEFAULT_RISK_AVERSION constant)
- **Tau Default:** τ = 0.05 (DEFAULT_TAU constant)
- **Fallback Behavior:** View combination failures fall back to equilibrium returns with warning

---

**File Reference:** `app/domain/services/portfolio_optimization/black_litterman.py`
**Last Audited:** 2026-02-01
**Last Fixed:** 2026-02-01 (GAPs: PSD validation, error logging, magic numbers)
