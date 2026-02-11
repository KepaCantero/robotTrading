# risk_parity.py

## Purpose
Risk Parity portfolio optimization - allocates weights such that each asset contributes equal risk to the portfolio, with related allocation methods.

---

## Type Definitions / Data Classes

### RiskParityResult
```python
@dataclass
class RiskParityResult:
    weights: np.ndarray              # REQUIRED - Risk parity weights
    risk_contributions: np.ndarray   # REQUIRED - Risk contribution of each asset
    risk_budget: np.ndarray          # REQUIRED - Target risk budget
    symbols: List[str]               # REQUIRED - Asset symbols
    converged: bool                  # REQUIRED - Optimization convergence status
```

**Properties:**
- `weights_dict` - Returns weights as {symbol: weight} dictionary
- `risk_parity_error` - Standard deviation of risk contributions (lower = better parity)

**Validation Rules:**
- `weights` must sum to 1.0 (within numerical tolerance)
- All weights must be non-negative (long-only)
- `risk_contributions` should be approximately equal for true risk parity
- `risk_budget` must sum to 1.0

---

## Function Signatures (Contracts)

### `RiskParityOptimizer.__init__(risk_free_rate, min_weight, max_weight) -> None`
**Pre:** risk_free_rate >= 0, min_weight >= 0, max_weight <= 1.0, min_weight <= max_weight
**Post:** Optimizer configured with bounds and parameters
**Raises:** ValueError if bounds invalid
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `optimize(cov_matrix, symbols, risk_budget) -> RiskParityResult`
**Pre:** cov_matrix must be square, symmetric, and positive semidefinite; risk_budget sums to 1.0 (if provided)
**Post:** Returns weights that equalize risk contributions per risk_budget
**Raises:** ValueError if covariance matrix invalid
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `inverse_volatility(cov_matrix, symbols) -> RiskParityResult`
**Pre:** cov_matrix must have positive diagonal elements
**Post:** Returns weights proportional to 1/σ_i (simple risk parity)
**Raises:** ValueError if all assets have zero variance
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `equal_weight(cov_matrix, symbols) -> RiskParityResult`
**Pre:** cov_matrix must be valid (n_assets >= 1)
**Post:** Returns equal 1/n weights
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `diversified_risk_parity(cov_matrix, symbols, kappa) -> RiskParityResult`
**Pre:** cov_matrix must be PSD; kappa > 0
**Post:** Returns DRP weights maximizing diversification while maintaining parity
**Raises:** ValueError if covariance matrix invalid
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `get_diversification_ratio(weights, cov_matrix) -> float`
**Pre:** weights sum to 1.0; cov_matrix is valid
**Post:** Returns DR = (Σ w_i σ_i) / σ_p (>1 indicates diversification benefit)
**Raises:** None (returns 1.0 if portfolio_vol == 0)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `cluster_based_risk_parity(cov_matrix, cluster_labels, symbols) -> np.ndarray` (module function)
**Pre:** cov_matrix valid; cluster_labels length matches n_assets
**Post:** Returns two-level risk parity weights (within clusters + across clusters)
**Raises:** None (handles single-asset clusters)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** Covariance matrix validated before optimization (PSD check, symmetry) ✅ FIXED
- [x] **AC-002:** Zero variance asset handling (no ZeroDivisionError) ✅ FIXED
- [x] **AC-003:** Optimization failures logged with context ✅ FIXED
- [x] **AC-004:** All public methods have complete type hints ✅ OK
- [x] **AC-005:** NumPy 2.0 compatibility ✅ OK
- [x] **AC-006:** All functions have docstrings following Google style ✅ OK
- [x] **AC-007:** Risk contribution calculation verified (RC_i = w_i * (Σw)_i / σ_p) ✅ OK
- [x] **AC-008:** Magic numbers documented as constants ✅ FIXED

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Risk Parity):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PSD validation | BASE_RULES.md (TRD-001) | Validate covariance matrix is positive semidefinite | ✅ FIXED - validate_covariance_matrix() |
| Input sanitization | BASE_RULES.md (TRD-015) | Remove NaN, zero variance assets | ✅ FIXED - sanitize_covariance_matrix() |
| Error logging | BASE_RULES.md (LOG-004) | Log optimization failures | ✅ FIXED - log_optimization_failure() |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy/scipy |
| Risk contribution formula | Qian & Maas (2010) | RC_i = w_i * (Σw)_i / σ_p | ✅ OK - Implemented |
| Inverse volatility | Risk Parity standard | w_i ∝ 1/σ_i | ✅ OK - Implemented |
| Diversification ratio | Qian & Maas (2010) | DR = (Σ w_i σ_i) / σ_p | ✅ OK - Implemented |
| Cluster-based RP | Advanced RP | Two-level risk parity | ✅ OK - Implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |
| Magic numbers | BASE_RULES.md (CC-001) | Document constants | ✅ FIXED - Constants defined |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Qian & Maas (2010) for Risk Parity rules.

---

## Dependencies
- **External:** `numpy`, `scipy` (optimize), `dataclasses` (std)
- **Internal:** `app.domain.services.portfolio_optimization._validation`

---

## Required Tests
- **test_risk_parity.py:**
  - `test_risk_parity_valid_input()` - Happy path with valid covariance
  - `test_risk_parity_equal_contributions()` - Verify RC_i ≈ RC_j for all i,j
  - `test_risk_parity_custom_budget()` - Custom risk budget (not equal)
  - `test_inverse_volatility()` - IVP baseline
  - `test_equal_weight()` - Benchmark comparison
  - `test_diversified_risk_parity()` - DRP vs RP comparison
  - `test_diversification_ratio()` - DR calculation
  - `test_cluster_based_risk_parity()` - CBRP two-level allocation
  - `test_risk_parity_zero_variance()` - Error path for σ=0
  - `test_risk_parity_singular_covariance()` - Edge case handling
  - `test_risk_parity_converged_false()` - Fallback behavior

---

## Notes
- **Critical:** Covariance matrix must be positive semidefinite for optimization
- **Risk Parity Formula:** Risk Contribution RC_i = w_i * (Σw)_i / σ_p
- **Equal Risk Contribution:** All RC_i should be approximately equal for true risk parity
- **Diversification Ratio:** DR > 1 indicates diversification benefit
- **Cluster-Based RP:** Two-level allocation (within clusters + across clusters)
- **Qian & Maas Reference:** "Risk Parity Portfolios" (2010) - Equal risk contribution principle
- **Trading Convention:** Assumes daily covariance (annualization if needed)
- **Constants:** DEFAULT_RISK_FREE_RATE, DEFAULT_MIN_WEIGHT, DEFAULT_MAX_WEIGHT, etc.

---

**File Reference:** `app/domain/services/portfolio_optimization/risk_parity.py`
**Last Audited:** 2026-02-04
**Last Fixed:** 2026-02-04 (GAP FIXED: Typo in constant name)

## Audit Summary (2026-02-04)
✅ **PASS** - All critical BASE_RULES compliant after fix
- TRD-001: PSD validation via validate_covariance_matrix() ✅
- LOG-001/LOG-004: Structured logging with stack traces ✅
- TYP-001: 100% type hint coverage ✅
- ARCH-001: Domain layer purity (no infrastructure imports) ✅
- All constants documented ✅
- GAP FIXED: DEFAULT_DIVERSE_RISK_PARRY_KAPPA → DEFAULT_DIVERSE_RISK_PARITY_KAPPA ✅
- Python compilation: ✅ PASS
- Validation: ✅ ALL GAPS FIXED
