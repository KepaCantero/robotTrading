# numba_metrics.py

## Purpose
Numba-Accelerated Backtest Metrics Calculator - Provides 10-100x faster performance for all backtesting metrics using JIT compilation.

---

## Function Signatures (Contracts)

### `validate_numeric_array(arr: np.ndarray, min_length: int = 1, name: str = "array") -> None`
**Pre:** None
**Post:** Validates array or raises exception
**Raises:** TypeError if not numpy array, ValueError for shape/content issues
**Retry:** No
**Side Effects:** None

**Validation Checks:**
- isinstance(arr, np.ndarray)
- arr.ndim == 1 (1-dimensional)
- len(arr) >= min_length
- np.issubdtype(arr.dtype, np.number)
- No NaN values
- No Inf values

### `calculate_returns_numba(prices: np.ndarray) -> np.ndarray`
**Pre:** prices is 1D array with length >= 2 (validated externally)
**Post:** Returns array of returns (length = len(prices) - 1)
**Raises:** None (returns empty array if len < 2)
**Retry:** No
**Side Effects:** None

### `calculate_cumulative_returns_numba(returns: np.ndarray) -> np.ndarray`
**Pre:** returns is 1D numeric array
**Post:** Returns cumulative returns array
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_sharpe_numba(returns: np.ndarray, risk_free_rate: float, periods_per_year: int) -> float`
**Pre:** returns is 1D array, risk_free_rate is finite, periods_per_year > 0
**Post:** Returns annualized Sharpe ratio
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [x] All metrics functions use @jit(nopython=True, cache=False)
- [x] Performance improvements: 10-100x speedup
- [x] Input validation via validate_numeric_array()
- [x] Clear documentation of validation requirements

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PERF-001 Numba JIT | 07-performance.md | Use JIT for hot paths | ✅ OK - All functions use @jit |
| VAL-001 Input validation | 08-validation.md | Validate array shapes/types | ✅ FIXED - 2026-02-01 - validate_numeric_array() added |
| TYP-001 Type hints | 02-type-hints.md | All functions typed | ✅ OK |
| LOG-001 Logging | 06-logging.md | Log module load | ✅ OK |

---

## Dependencies
- **External:** numba, numpy, logging, typing
- **Internal:** None

---

## Required Tests
- **test_numba_metrics.py:**
  - Test validate_numeric_array() with invalid inputs
  - Test calculate_returns_numba() with various array sizes
  - Test calculate_sharpe_numba() with edge cases
  - Test all metrics with NaN/Inf handling

---

## Notes
This module provides numba-optimized metrics calculations for backtesting. All functions use @jit(nopython=True, cache=False) for maximum performance. Expected speedups: 10-100x compared to pure Python implementations.

## GAP Fixes (2026-02-01)

### VAL-001 - Array Validation
✅ FIXED - Added comprehensive input validation:
1. Created `validate_numeric_array()` function for pre-computation validation
2. Added validation documentation to all key functions:
   - calculate_returns_numba()
   - calculate_cumulative_returns_numba()
   - calculate_sharpe_numba()
   - (and other core metrics functions)

### Validation Implementation Details
The validation function checks:
- Array is a numpy array (TypeError if not)
- Array is 1-dimensional (ValueError if not)
- Array has minimum required length (ValueError if not)
- Array is numeric type (TypeError if not)
- Array contains no NaN values (ValueError if found)
- Array contains no Inf values (ValueError if found)

Usage example:
```python
from app.backtesting.numba_metrics import validate_numeric_array, calculate_returns_numba

# Validate before calling numba function
validate_numeric_array(prices, min_length=2, name="prices")

# Now safe to call JIT-compiled function
returns = calculate_returns_numba(prices)
```

---

## Additional Fixes (2026-02-02)

### BUG-001 - Cumulative Returns Calculation
✅ FIXED - `calculate_cumulative_returns_numba()` was returning cumulative wealth values instead of cumulative returns.
**Issue:** Function returned values like [1.01, 1.0302, ...] instead of [0.01, 0.0302, ...]
**Fix:** Modified to subtract 1.0 from cumulative wealth at each step to return actual cumulative returns.

### BUG-002 - Information Ratio Calculation
✅ FIXED - `calculate_information_ratio_numba()` was using `np.std(ddof=1)` which is not supported in Numba nopython mode.
**Issue:** Numba JIT compilation failed with `np.std(excess_returns, ddof=1)`.
**Fix:** Replaced with manual mean calculation and `sample_std_numba()` helper function.

### BUG-003 - Zero Price Handling
✅ FIXED - `calculate_returns_numba()` was throwing ZeroDivisionError with zero prices.
**Issue:** Division by zero when price[i] == 0 caused runtime error.
**Fix:** Added explicit check for zero prices, returning inf/nan as appropriate:
```python
if prices[i] == 0.0:
    returns[i] = np.inf if prices[i + 1] > 0 else np.nan
else:
    returns[i] = (prices[i + 1] - prices[i]) / prices[i]
```
