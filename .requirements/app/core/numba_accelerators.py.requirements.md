# numba_accelerators.py

## Purpose
Numba JIT-compiled functions for high-performance numerical calculations in backtesting and strategy execution.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses Numba JIT compilation for performance.

### Accelerated Functions
```python
@numba.jit(nopython=True, cache=True)
def calculate_returns(prices: np.ndarray, periods: int = 1) -> np.ndarray
    # Calculate returns with Numba acceleration

@numba.jit(nopython=True, cache=True)
def calculate_volatility(returns: np.ndarray, window: int) -> np.ndarray
    # Rolling volatility calculation

@numba.jit(nopython=True, cache=True)
def calculate_sharpe(returns: np.ndarray, risk_free_rate: float) -> float
    # Sharpe ratio calculation
```

---

## Function Signatures (Contracts)

### `calculate_returns(prices: np.ndarray, periods: int = 1) -> np.ndarray`
**Pre:** prices is 1D array, len(prices) > periods
**Post:** Returns array of returns
**Raises:** None (returns empty array on error)
**Retry:** No
**Side Effects:** None

### `calculate_volatility(returns: np.ndarray, window: int) -> np.ndarray`
**Pre:** returns is 1D array, window > 0, len(returns) >= window
**Post:** Returns rolling volatility
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_sharpe(returns: np.ndarray, risk_free_rate: float) -> float`
**Pre:** returns is 1D array
**Post:** Returns Sharpe ratio
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] PERF-005: All functions use @numba.jit(nopython=True, cache=True)
- [ ] nopython=True ensures no Python fallback
- [ ] cache=True speeds up subsequent calls
- [ ] Functions handle edge cases (empty arrays, NaN)
- [ ] Performance measured vs pure NumPy
- [ ] 10-100x speedup on hot paths

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PERF-005 | BASE_RULES.md | Numba JIT for hot paths | ✅ OK |
| PERF-004 | BASE_RULES.md | Profile before optimizing | ⚠️ GAP - Should benchmark |
| TYP-001 | BASE_RULES.md | Type coverage | ✅ OK |

---

## Dependencies
- **External:** numba >= 0.59.0, numpy
- **Internal:** None

---

## Required Tests
- **tests/core/test_numba_accelerators.py:**
  - Test calculate_returns() correct values
  - Test calculate_volatility() correct values
  - Test calculate_sharpe() correct values
  - Test edge cases (empty arrays, single element)
  - Test performance vs NumPy (benchmark)
  - Test Numba compilation succeeds
  - Test cache works on second call

---

## Notes
CRITICAL for backtesting performance. These functions are called millions of times. Numba provides 10-100x speedup vs pure NumPy.
