# fama_french_factors.py

## Purpose
Fama-French factor models domain service - implements 3-factor and 4-factor models for analyzing returns and constructing factor portfolios.

---

## Type Definitions / Data Classes

### FactorReturns
```python
@dataclass
class FactorReturns:
    market_return: float      # REQUIRED - Rm - Rf (Market excess return)
    smb_return: float         # REQUIRED - Small Minus Big (size factor)
    hml_return: float         # REQUIRED - High Minus Low (value factor)
    umd_return: float = 0.0   # OPTIONAL - Up Minus Down (momentum factor)
    risk_free_rate: float = 0.0 # OPTIONAL - Risk-free rate
```

**Properties:**
- `three_factor` - Returns np.array([Rm-Rf, SMB, HML])
- `four_factor` - Returns np.array([Rm-Rf, SMB, HML, UMD])

### FactorLoadings
```python
@dataclass
class FactorLoadings:
    market_beta: float       # REQUIRED - Market sensitivity (β_mkt)
    smb_beta: float          # REQUIRED - Size sensitivity (β_smb)
    hml_beta: float          # REQUIRED - Value sensitivity (β_hml)
    umd_beta: float = 0.0    # OPTIONAL - Momentum sensitivity (β_umd)
    alpha: float = 0.0        # OPTIONAL - Excess return not explained by factors
```

**Methods:**
- `predict_return(factor_returns)` - Returns predicted excess return using loadings

### FactorModelResult
```python
@dataclass
class FactorModelResult:
    loadings: FactorLoadings              # REQUIRED - Estimated factor betas
    r_squared: float                      # REQUIRED - Model fit quality (0-1)
    p_values: Dict[str, float]            # REQUIRED - Statistical significance
    t_stats: Dict[str, float]             # REQUIRED - T-statistics for coefficients
    standard_errors: Dict[str, float]     # REQUIRED - Standard errors
    n_obs: int                            # REQUIRED - Number of observations
```

**Properties:**
- `is_market_beta_significant` - True if p_value(market) < 0.05
- `has_positive_alpha` - True if alpha > 0 and p_value(alpha) < 0.1

### FactorTiming
```python
@dataclass
class FactorTiming:
    market_timing_score: float    # -1 to 1 (bearish to bullish on market)
    size_timing_score: float      # -1 to 1 (large cap to small cap)
    value_timing_score: float     # -1 to 1 (growth to value)
```

**Properties:**
- `recommend_momentum` - True if market_timing_score > 0.3
- `recommend_value` - True if value_timing_score > 0.3
- `recommend_small_cap` - True if size_timing_score > 0.3

---

## Function Signatures (Contracts)

### `FamaFrenchModel.__init__(model_type, risk_free_rate) -> None`
**Pre:** model_type in ["3factor", "4factor"]; risk_free_rate >= 0
**Post:** Model configured with parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `estimate_loadings(asset_returns, factor_returns) -> FactorModelResult`
**Pre:** asset_returns and factor_returns have same length T >= n_params
**Post:** Returns factor loadings via OLS regression
**Raises:** LinAlgError if X'X is singular (not handled)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `construct_factor_portfolio(factor_returns, target_factor, long_leg) -> Dict[str, float]`
**Pre:** factor_returns has required columns; target_factor in ["smb", "hml", "umd"]
**Post:** Returns portfolio targeting specified factor
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `calculate_expected_return(loadings, factor_returns) -> float`
**Pre:** loadings and factor_returns are compatible (same factors)
**Post:** Returns predicted excess return using factor model
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** OLS regression correctly estimates factor loadings
- [ ] **AC-002:** R-squared calculated as 1 - (SS_res / SS_tot)
- [ ] **AC-003:** 3-factor model uses [Market, SMB, HML] factors
- [ ] **AC-004:** 4-factor model adds UMD (momentum) factor
- [ ] **AC-005:** Standard errors from variance-covariance matrix
- [ ] **AC-006:** P-values calculated from t-distribution (two-tailed)
- [ ] **AC-007:** All public methods have complete type hints
- [ ] **AC-008:** NumPy/Pandas 2.0 compatibility

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Fama-French):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate returns array length | ❌ GAP - No validation |
| 3-factor model | Fama & French (1993) | R = α + β_mkt*MKT + β_smb*SMB + β_hml*HML | ✅ OK - Implemented |
| 4-factor model | Carhart (1997) | + β_umd*UMD | ✅ OK - Implemented |
| OLS regression | Econometrics | β = (X'X)^(-1)X'y | ✅ OK - np.linalg.lstsq |
| R-squared | Stats standard | 1 - SS_res/SS_tot | ✅ OK - Implemented |
| Standard errors | Econometrics | √diag(MSE * (X'X)^(-1)) | ✅ OK - Implemented |
| T-statistics | Stats standard | β / SE | ✅ OK - Implemented |
| P-values | Stats standard | 2 * (1 - t.cdf(\|t\|)) | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy/pandas/scipy |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Fama & French (1993), Carhart (1997) for factor model rules.

---

## Dependencies
- **External:** `numpy`, `pandas`, `scipy` (stats), `dataclasses` (std), `decimal` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_fama_french_factors.py:**
  - `test_3factor_loadings_estimation()` - OLS estimates 3 betas correctly
  - `test_4factor_loadings_estimation()` - OLS estimates 4 betas correctly
  - `test_r_squared_calculation()` - R² = 1 - SS_res/SS_tot
  - `test_predict_return()` - R = α + Σ β_i * F_i
  - `test_market_beta_significance()` - p < 0.05 means significant
  - `test_positive_alpha_detection()` - α > 0 and significant
  - `test_factor_portfolio_construction()` - Targets single factor
  - `test_insufficient_observations()` - Handles short arrays
  - `test_singular_matrix_handling()` - Handles collinear factors
  - `test_p_value_calculation()` - Two-tailed t-test
  - `test_standard_errors()` - From variance-covariance matrix

---

## Notes
- **Critical:** Factor models require excess returns (R - Rf), not raw returns
- **Fama & French (1993):** "Common risk factors in stock returns" - 3-factor model
- **Carhart (1997):** "On persistence in mutual fund performance" - 4-factor model
- **Market Factor (Rm-Rf):** Excess return of market portfolio
- **SMB (Small Minus Big):** Size factor (small caps outperform large caps)
- **HML (High Minus Low):** Value factor (value stocks outperform growth)
- **UMD (Up Minus Down):** Momentum factor (winners outperform losers)
- **Alpha:** Excess return not explained by factors (manager skill)
- **Beta (β):** Sensitivity to factor (systematic risk)
- **R-squared:** Proportion of variance explained by model
- **T-statistic:** Coefficient / Standard Error
- **P-value < 0.05:** Statistically significant at 95% confidence
- **Factor Portfolio:** Loads primarily on one factor (e.g., HML for value)

---

**File Reference:** `app/domain/strategies/fama_french_factors.py`
**Last Audited:** 2026-02-01
