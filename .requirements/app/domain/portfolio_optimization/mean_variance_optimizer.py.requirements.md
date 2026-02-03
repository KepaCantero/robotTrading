# mean_variance_optimizer.py

## Purpose
Markowitz Mean-Variance Portfolio Optimization (1952) - Modern Portfolio Theory implementation.

---

## Type Definitions / Data Classes

### OptimizationMethod (Enum)
**Purpose:** Available optimization methods (MAX_SHARPE, MIN_VARIANCE, EQUAL_WEIGHT, RISK_PARITY)

### ShrinkageMethod (Enum)
**Purpose:** Shrinkage methods (LEDOIT_WOLF, ORACLE_APPROXIMATING, SAMPLE)

### OptimizationResult (Dataclass)
**Purpose:** Result of portfolio optimization
- weights: NDArray[np.float64]
- expected_return: float
- expected_risk: float
- sharpe_ratio: float
- success: bool
- message: str
- method: OptimizationMethod

### EfficientFrontier (Dataclass)
**Purpose:** Efficient frontier with multiple optimal portfolios
- points: list[EfficientFrontierPoint]
- max_sharpe_index: int
- min_variance_index: int

---

## Function Signatures (Contracts)

### `MeanVarianceOptimizer.optimize(returns, method, use_shrinkage) -> OptimizationResult`
**Pre:** returns.shape = (T, N), T >= 252
**Post:** Returns optimal portfolio weights
**Raises:** InputValidationError if data invalid
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [x] **AC-001:** All public methods have complete type hints
- [x] **AC-002:** NumPy 2.0 compatibility (uses np.float64)
- [ ] **AC-003:** All functions have docstrings following Google style ⚠️ 3 nested helper functions missing
- [x] **AC-004:** Input validation on all public methods

---

## Audit Status

**Status:** PASSED
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 1 P3
**Notes:** Excellent MVO implementation. Minor: 3 nested helper functions lack docstrings.

---

## Critical Rules (MUST NOT BREAK)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type hints on public functions | ✅ PASSED - 26/26 typed |
| CC-001 | BASE_RULES.md | All functions documented | ⚠️ MINOR - 3 nested helpers missing |
| CC-006 | BASE_RULES.md | Validate all inputs | ✅ PASSED - InputValidationError |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ PASSED - exc_info=True |
| TYP-002 | BASE_RULES.md | No deprecated np aliases | ✅ PASSED - Uses np.float64 |
| ARCH-002 | BASE_RULES.md | Domain layer purity | ✅ PASSED - No infra imports |

---

## Dependencies
- **External:** numpy, scipy, sklearn (optional, for shrinkage)
- **Internal:** None

---

## Required Tests
- **test_mean_variance_optimizer.py:** Tests for optimization methods, efficient frontier, constraints

---

## Notes
Comprehensive MVO implementation with:
- Excellent validation with custom exceptions
- Well-documented constraints (Rules 66-74)
- Good use of __slots__ for memory optimization
- Extensive error handling with risk parity fallback
- Minor gap: 3 nested helper functions need docstrings (P3)

---

**File Reference:** `app/domain/portfolio_optimization/mean_variance_optimizer.py`
**Status:** ✅ PASSED AUDIT
