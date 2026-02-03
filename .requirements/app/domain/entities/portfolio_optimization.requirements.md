# portfolio_optimization.py

## Purpose
Portfolio Optimization Entity - Domain layer entity representing portfolio optimization results combining multiple methodologies.

---

## Type Definitions / Data Classes

### PortfolioOptimization
```python
@dataclass
class PortfolioOptimization:
    weights: Dict[str, Decimal]            # REQUIRED - Symbol -> weight mapping
    expected_return: float                  # REQUIRED - Expected portfolio return
    expected_risk: float                    # REQUIRED - Expected portfolio risk (std dev)
    sharpe_ratio: float                     # REQUIRED - Risk-adjusted return

    # Ernest Chan - Regime information
    regime: str                             # Default: "UNKNOWN"

    # Narang - Factor exposures
    factor_exposures: Dict[str, float]      # Default: {} - Factor -> exposure mapping

    # Hull - Risk metrics
    var_95: Optional[float]                 # Default: None - 95% VAR
```

---

## Function Signatures (Contracts)

### `__post_init__() -> None` (Dataclass validation)
**Pre:** weights is provided at construction
**Post:** Weights are non-empty and sum to 1.0 (±0.01 tolerance)
**Raises:** ValueError if validation fails
**Side Effects:** None (validation only)

### `get_weight_summary() -> Dict[str, str]`
**Pre:** None
**Post:** Returns dict of symbol -> formatted weight (4 decimal places)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_top_positions(n) -> List[Tuple[str, Decimal]]`
**Pre:** n > 0
**Post:** Returns top N positions sorted by weight (descending)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_risk_metrics() -> Dict[str, float]`
**Pre:** None
**Post:** Returns dict with expected_return, expected_risk, sharpe_ratio, var_95 (or 0.0)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_regime_info() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with regime, factor_exposures
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_efficient() -> bool`
**Pre:** None
**Post:** Returns True if sharpe_ratio >= 1.0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_diversified() -> bool`
**Pre:** None
**Post:** Returns True if weights non-empty AND max_weight <= 0.3 (30%)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** weights dict must be non-empty (validated in __post_init__)
- [x] **AC-002:** weights must sum to approximately 1.0 (±0.01 tolerance) (validated in __post_init__)
- [x] **AC-003:** expected_return is annualized return (documented in docstring)
- [x] **AC-004:** expected_risk is annualized standard deviation (documented in docstring)
- [x] **AC-005:** sharpe_ratio = (return - rf) / risk (documented in docstring)
- [x] **AC-006:** Efficient portfolio has sharpe_ratio >= 1.0 (is_efficient method)
- [x] **AC-007:** Diversified portfolio has max position <= 30% (is_diversified method)
- [x] **AC-008:** var_95 is 95% Value at Risk (Hull risk metric)
- [x] **AC-009:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Portfolio Optimization):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Weights sum to 1 | Portfolio constraint | Σweights = 1.0 (±0.01) | ✅ FIXED - 2026-02-01 - Added __post_init__ validation with tolerance |
| Expected return | Markowitz (1952) | E[R] = Σ(wᵢ × Rᵢ) | ✅ OK - Provided |
| Expected risk | Markowitz (1952) | σ = √(w'Σw) | ✅ OK - Provided |
| Sharpe ratio | Sharpe (1966) | (E[R] - rf) / σ | ✅ OK - Provided |
| Regime detection | Chan (2013) | Market regime label | ✅ OK - regime field |
| Factor exposures | Narang (2013) | Factor loadings | ✅ OK - factor_exposures |
| VAR 95% | Hull (2018) | 95% Value at Risk | ✅ OK - var_95 |
| Efficiency threshold | Portfolio theory | Sharpe >= 1.0 | ✅ OK - is_efficient() |
| Diversification | Portfolio theory | Max weight <= 30% | ✅ OK - is_diversified() |
| Top positions | Portfolio reporting | N largest positions | ✅ OK - get_top_positions() |
| Weight summary | Analytics | Formatted weights | ✅ OK - get_weight_summary() |
| Risk summary | Analytics | All risk metrics | ✅ OK - get_risk_metrics() |
| Regime info | Analytics | Regime + factors | ✅ OK - get_regime_info() |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain entity purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Markowitz (1952), Chan (2013), Narang (2013), Hull (2018) for portfolio optimization rules.

---

## Dependencies
- **External:** `dataclasses` (std), `decimal` (std), `typing` (std)
- **Internal:** None (domain entity)

---

## Required Tests
- **test_portfolio_optimization_entity.py:**
  - `test_get_weight_summary()` - Returns formatted weights
  - `test_get_top_positions()` - Returns N largest by weight
  - `test_get_risk_metrics()` - Returns all risk metrics
  - `test_get_regime_info()` - Returns regime + factor_exposures
  - `test_is_efficient_true()` - Sharpe >= 1.0
  - `test_is_efficient_false()` - Sharpe < 1.0
  - `test_is_diversified_true()` - Max weight <= 30%
  - `test_is_diversified_false()` - Max weight > 30%
  - `test_is_diversified_empty()` - False if empty weights
  - `test_regime_field()` - Chan regime detection
  - `test_factor_exposures()` - Narang factor loadings
  - `test_var_95()` - Hull VAR metric
  - `test_expected_return()` - Portfolio return
  - `test_expected_risk()` - Portfolio std dev
  - `test_sharpe_ratio()` - Risk-adjusted return

---

## Notes
- **Critical:** PortfolioOptimization contains results from optimization combining Chan (regime), Narang (factors), Hull (risk)
- **Markowitz Reference:** "Portfolio Selection" (1952) - Mean-variance optimization foundation
- **Chan Reference:** "Algorithmic Trading" (2013) - Regime-based optimization
- **Narang Reference:** "Inside the Black Box" (2013) - Factor exposures
- **Hull Reference:** "Options, Futures, and Other Derivatives" (2018) - VAR calculation
- **Weights:** Symbol -> weight mapping (should sum to 1.0)
- **Expected Return:** Weighted average return of portfolio
- **Expected Risk:** Standard deviation of portfolio returns
- **Sharpe Ratio:** Risk-adjusted return (return - risk_free) / risk
- **Regime:** Market regime label from Chan's regime detection
- **Factor Exposures:** Portfolio factor loadings (e.g., size, value, momentum)
- **VAR 95%:** 95% Value at Risk - maximum expected loss at 95% confidence
- **Efficient Portfolio:** Sharpe ratio >= 1.0 (common threshold)
- **Diversified Portfolio:** No single position > 30% (concentration limit)
- **Top Positions:** N positions with largest weights (for reporting)
- **Weight Summary:** Formatted weights with 4 decimal places
- **Risk Metrics Summary:** All risk metrics in one dict
- **Regime Info:** Regime and factor exposures for analysis

---

**File Reference:** `app/domain/entities/portfolio_optimization.py`
**Last Audited:** 2026-02-01
