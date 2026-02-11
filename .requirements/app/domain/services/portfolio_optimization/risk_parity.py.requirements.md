# risk_parity.py

## Purpose
Domain service file for Risk Parity portfolio optimization

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### RiskParityResult
**Purpose:** Result of Risk Parity optimization.
**Fields:**
- weights: np.ndarray - Risk parity weights
- risk_contributions: np.ndarray - Risk contribution of each asset
- risk_budget: np.ndarray - Target risk budget (usually equal)
- symbols: List[str] - Asset symbols
- converged: bool - Whether optimization converged

### RiskParityOptimizer
**Purpose:** Risk Parity portfolio optimizer.

Risk Parity allocates weights such that each asset contributes
equal risk to the portfolio:

RC_i = w_i * (Σw)_i / σ_p = constant

Methods:
- Risk Parity (equal risk contribution)
- Inverse Volatility
- Equal Weight (benchmark)
- Diversified Risk Parity

---

## Function Signatures (Contracts)

### `RiskParityResult.weights_dict(self) -> Dict[str, float]`
**Pre:** None
**Post:** Returns weights as {symbol: weight} dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None

### `RiskParityResult.risk_parity_error(self) -> float`
**Pre:** None
**Post:** Returns std dev of risk contributions (lower is better)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `RiskParityOptimizer.optimize(self, cov_matrix: np.ndarray, symbols: Optional[List[str]] = None, risk_budget: Optional[np.ndarray] = None) -> RiskParityResult`
**Pre:** cov_matrix is square, PSD
**Post:** RiskParityResult with risk parity weights
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** None

### `RiskParityOptimizer.inverse_volatility(self, cov_matrix: np.ndarray, symbols: Optional[List[str]] = None) -> RiskParityResult`
**Pre:** cov_matrix is square with at least one positive variance asset
**Post:** RiskParityResult with inverse volatility weights
**Raises:** ValueError if all assets have zero variance
**Retry:** No
**Side Effects:** None

### `RiskParityOptimizer.equal_weight(self, cov_matrix: np.ndarray, symbols: Optional[List[str]] = None) -> RiskParityResult`
**Pre:** cov_matrix is non-empty square matrix
**Post:** RiskParityResult with equal weights
**Raises:** ValueError if matrix empty or not square
**Retry:** No
**Side Effects:** None

### `RiskParityOptimizer.diversified_risk_parity(self, cov_matrix: np.ndarray, symbols: Optional[List[str]] = None, kappa: float = DEFAULT_DIVERSE_RISK_PARITY_KAPPA) -> RiskParityResult`
**Pre:** cov_matrix is square, PSD
**Post:** RiskParityResult with DRP weights
**Raises:** ValueError if covariance matrix invalid
**Retry:** No
**Side Effects:** None

### `RiskParityOptimizer.get_diversification_ratio(self, weights: np.ndarray, cov_matrix: np.ndarray) -> float`
**Pre:** weights and cov_matrix have compatible dimensions
**Post:** Returns diversification ratio (> 1 indicates benefit)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `cluster_based_risk_parity(cov_matrix: np.ndarray, cluster_labels: np.ndarray, symbols: Optional[List[str]] = None) -> np.ndarray`
**Pre:** cov_matrix is square, len(cluster_labels) == n_assets
**Post:** Returns CBRP weights
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** Logs warnings for empty or zero-variance clusters


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
**Notes:** File fully complies with BASE_RULES. Implements Risk Parity with multiple allocation methods. Validates covariance matrix before optimization. Sanitizes zero variance assets. Supports custom risk budgets. Includes Cluster-Based Risk Parity (CBRP) for hierarchical allocation. Logs warnings for zero variance assets. NumPy 2.0 compatible.

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
- **Internal:** app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_risk_parity.py:** Unit tests for:
  - Risk parity optimization with equal risk budget
  - Custom risk budget optimization
  - Inverse volatility weights
  - Equal weight benchmark
  - Diversified risk parity with various kappa values
  - Diversification ratio calculation
  - Cluster-based risk parity
  - Zero variance asset handling

---

## Notes

**File Reference:** `app/domain/services/portfolio_optimization/risk_parity.py`
**Created:** 2026-02-05
**Status:** ✅ AUDIT PASSED
