# fama_french_factors.py

## Purpose
Implements Fama-French 3-factor and Carhart 4-factor models for analyzing asset returns and constructing factor portfolios using OLS regression.

---

## Type Definitions / Data Classes

### FactorReturns DataClass
```python
@dataclass
class FactorReturns:
    market_return: float    # REQUIRED - Rm - Rf (Market excess return)
    smb_return: float       # REQUIRED - Small Minus Big (size factor)
    hml_return: float       # REQUIRED - High Minus Low (value factor)
    umd_return: float = 0.0  # OPTIONAL - Up Minus Down (momentum factor)
    risk_free_rate: float = 0.0  # OPTIONAL - Risk-free rate
```

**Properties:**
- `three_factor`: Returns np.array([market_return, smb_return, hml_return])
- `four_factor`: Returns np.array([market_return, smb_return, hml_return, umd_return])

**Validation Rules:**
- All returns must be finite (can be negative)
- risk_free_rate must be finite (typically 0-0.05)

### FactorLoadings DataClass
```python
@dataclass
class FactorLoadings:
    market_beta: float    # REQUIRED - Market sensitivity
    smb_beta: float       # REQUIRED - Size factor sensitivity
    hml_beta: float       # REQUIRED - Value factor sensitivity
    umd_beta: float = 0.0  # OPTIONAL - Momentum factor sensitivity
    alpha: float = 0.0     # OPTIONAL - Excess return not explained by factors
```

**Methods:**
- `predict_return(factor_returns: FactorReturns) -> float`: Predicts return using factor loadings

**Validation Rules:**
- All betas must be finite
- alpha represents abnormal return (can be positive or negative)

### FactorModelResult DataClass
```python
@dataclass
class FactorModelResult:
    loadings: FactorLoadings              # REQUIRED - Estimated factor betas
    r_squared: float                      # REQUIRED - Model fit quality [0-1]
    p_values: Dict[str, float]            # REQUIRED - Statistical significance [0-1]
    t_stats: Dict[str, float]             # REQUIRED - T-statistics
    standard_errors: Dict[str, float]     # REQUIRED - Standard errors
    n_obs: int                            # REQUIRED - Number of observations
```

**Properties:**
- `is_market_beta_significant`: Returns True if market beta p-value < 0.05
- `has_positive_alpha`: Returns True if alpha > 0 and p-value < 0.1

**Validation Rules:**
- `r_squared` must be in range [0, 1]
- All p_values must be in range [0, 1]
- `n_obs` must be positive
- All dict keys must match factor names

### FactorTiming DataClass
```python
@dataclass
class FactorTiming:
    market_timing_score: float   # REQUIRED - Market timing [-1 to 1]
    size_timing_score: float     # REQUIRED - Size timing [-1 to 1]
    value_timing_score: float    # REQUIRED - Value timing [-1 to 1]
```

**Properties:**
- `recommend_momentum`: Returns True if market_timing_score > 0.3
- `recommend_value`: Returns True if value_timing_score > 0.3
- `recommend_small_cap`: Returns True if size_timing_score > 0.3

**Validation Rules:**
- All scores must be in range [-1, 1]

### FamaFrenchModel Class
```python
class FamaFrenchModel:
    model_type: str = "3factor"        # "3factor" or "4factor"
    risk_free_rate: float = 0.02       # Annual risk-free rate
```

**Validation Rules:**
- `model_type` must be one of: "3factor", "4factor"
- `risk_free_rate` must be non-negative

---

## Function Signatures (Contracts)

### `estimate_loadings(asset_returns: np.ndarray, factor_returns: FactorReturns) -> FactorModelResult`
**Pre:** asset_returns length >= 2, factor_returns contains finite values
**Post:** Returns FactorModelResult with estimated betas and statistics
**Raises:** No exceptions (returns default result on error)
**Retry:** No
**Side Effects:** Logs warnings for invalid data, handles singular matrices

### `construct_factor_portfolio(factor_returns: pd.DataFrame, target_factor: str = "hml", long_leg: bool = True) -> Dict[str, float]`
**Pre:** factor_returns has columns: Rm-Rf, SMB, HML, UMD
**Post:** Returns dictionary mapping asset -> weight for factor portfolio
**Raises:** No exceptions
**Retry:** No
**Side Effects:** None (currently simplified implementation)

### `calculate_expected_return(loadings: FactorLoadings, factor_returns: FactorReturns) -> float`
**Pre:** loadings and factor_returns are valid
**Post:** Returns predicted excess return
**Raises:** No exceptions
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Type hints coverage: 100% of functions have return type hints (AC-TYPE-001)
- [ ] All dataclass fields have validation rules documented
- [ ] Input validation handles empty arrays, NaN, inf values
- [ ] OLS regression handles singular matrices gracefully
- [ ] R-squared always in range [0, 1]
- [ ] P-values always in range [0, 1]
- [ ] Standard errors handle division by zero
- [ ] T-statistics handle zero standard errors
- [ ] No hardcoded model parameters (all configurable via constructor)
- [ ] Logs warnings for all error conditions (AC-LOG-001)
- [ ] Domain layer purity: no infrastructure imports (AC-ARCH-001)
- [ ] Black formatting compliance (AC-FMT-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| ARCH-003 | BASE_RULES.md | No framework imports in domain | ✅ OK |
| LOG-001 | BASE_RULES.md | Structured logging with context | ⚠️ NOT APPLIED - Uses standard logging |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Logs warnings on errors |
| TRD-001 | BASE_RULES.md | Covariance validation | ✅ OK - Handles singular matrices |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ NOT APPLIED - Returns default result instead of raising |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ OK |
| TRD-005 | BASE_RULES.md | Price validation | ✅ OK - Validates factor returns |

**GAP violations found:**
- ❌ GAP LOG-001: Uses standard logging instead of structured logging (priority P1)
  - Impact: Reduced observability in production
  - Recommendation: Use structlog for structured logging
- ⚠️ GAP TRD-001: construct_factor_portfolio is simplified implementation (priority P0)
  - Impact: Not production-ready for actual factor portfolio construction
  - Recommendation: Implement proper asset selection based on factor loadings

---

## Dependencies
- **External:** numpy, pandas, scipy.stats, logging, dataclasses, decimal, typing
- **Internal:** None (pure domain service)

---

## Required Tests
- **test_fama_french_factors.py:**
  - Success paths:
    - `test_estimate_3factor_loadings` - Correctly estimates market, size, value betas
    - `test_estimate_4factor_loadings` - Correctly estimates including momentum beta
    - `test_predict_return_from_loadings` - Predicts returns using factor model
    - `test_r_squared_bounds` - R-squared always in [0, 1]
    - `test_p_values_bounds` - P-values always in [0, 1]
    - `test_significance_checks` - Correctly identifies significant betas
  - Error paths:
    - `test_insufficient_observations` - Returns default result when n_obs < 2
    - `test_nan_asset_returns` - Filters NaN values from asset returns
    - `test_inf_asset_returns` - Filters inf values from asset returns
    - `test_nan_factor_returns` - Replaces NaN in factor returns with 0
    - `test_singular_matrix` - Handles singular matrix in variance calculation
  - Edge cases:
    - `test_zero_division_t_stats` - Handles zero standard errors in t-stat calculation
    - `test_zero_total_variance` - Handles ss_tot near zero in R-squared
    - `test_n_obs_equals_n_params` - Handles case where n_obs <= n_params
    - `test_factor_returns_three_factor` - Returns 3-factor array correctly
    - `test_factor_returns_four_factor` - Returns 4-factor array correctly
    - `test_factor_timing_recommendations` - Correctly recommends based on scores

---

## Notes
Reference: Fama & French (1993) - 3-factor model, Carhart (1997) - 4-factor model. Implements robust OLS with proper numerical stability handling for production use.
