# black_litterman_optimizer.py

## Purpose
Implementation of Black-Litterman portfolio optimization model combining market equilibrium returns with investor views.

---

## Type Definitions / Data Classes

### ViewType (Enum)
**Purpose:** Type of investor view (ABSOLUTE or RELATIVE)

### InvestorView (Dataclass)
**Purpose:** Represents a single investor view on expected returns
- view_type: ViewType
- assets: list[int]
- pick_vector: NDArray[np.float64]
- expected_return: float
- confidence: float (0 < confidence < 1)
- id: str | None

### BlackLittermanConfig (Dataclass)
**Purpose:** Configuration for Black-Litterman optimization
- tau: float = 0.05 (uncertainty parameter)
- risk_aversion: float = 3.0
- use_shrinkage: bool = True
- lookback_days: int = 252
- risk_free_rate: float = 0.02
- max_position: float = 0.20
- omega_method: str = "idzorek"

### BlackLittermanResult (Dataclass)
**Purpose:** Result of Black-Litterman portfolio optimization
- weights: NDArray[np.float64]
- equilibrium_returns: NDArray[np.float64]
- bl_returns: NDArray[np.float64]
- views: list[InvestorView]
- posterior_covariance: NDArray[np.float64]
- expected_return: float
- expected_risk: float
- sharpe_ratio: float
- view_impact: NDArray[np.float64] | None
- success: bool
- message: str

---

## Function Signatures (Contracts)

### `BlackLittermanOptimizer.optimize(returns, market_caps, market_weights, views) -> BlackLittermanResult`
**Pre:** returns.shape = (T, N), T >= 252
**Post:** Returns optimal portfolio weights
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** All public methods have complete type hints
- [x] **AC-002:** NumPy 2.0 compatibility (uses np.float64)
- [x] **AC-003:** All functions have docstrings following Google style
- [x] **AC-004:** Input validation on all public methods

---

## Audit Status

**Status:** PASSED
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** Excellent implementation with full type hints, comprehensive docstrings, proper validation, and error logging.

---

## Critical Rules (MUST NOT BREAK)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type hints on public functions | ✅ PASSED - 13/13 typed |
| CC-001 | BASE_RULES.md | All functions documented | ✅ PASSED - Google style |
| CC-006 | BASE_RULES.md | Validate all inputs | ✅ PASSED - Comprehensive |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ PASSED - exc_info=True |
| TYP-002 | BASE_RULES.md | No deprecated np aliases | ✅ PASSED - Uses np.float64 |
| ARCH-002 | BASE_RULES.md | Domain layer purity | ✅ PASSED - No infra imports |

---

## Dependencies
- **External:** numpy, scipy, sklearn (optional, for LedoitWolf)
- **Internal:** None

---

## Required Tests
- **test_black_litterman_optimizer.py:** Tests for equilibrium returns, view matrix construction, optimization

---

## Notes
Excellent Black-Litterman implementation with:
- Clear mathematical documentation with formulas
- Comprehensive validation (confidence range, weight checks)
- Proper error handling with fallback to equal weights
- Well-structured class design (separate classes for concerns)

---

**File Reference:** `app/domain/portfolio_optimization/black_litterman_optimizer.py`
**Status:** ✅ PASSED AUDIT
