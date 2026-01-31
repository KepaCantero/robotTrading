# numba_metrics.py

## Purpose
Numba-JIT accelerated performance metrics for backtesting (10-100x speedup over pure Python). All metric calculations MUST use Numba compilation - no fallbacks allowed.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

This file contains only JIT-compiled functions with standard numpy array inputs. No custom data classes.

---

## Function Signatures (Contracts)

### `sample_std_numba(values: np.ndarray) -> float`
**Pre:** values is 1D numpy array with length >= 2
**Post:** Returns sample standard deviation (ddof=1) of values
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_returns_numba(prices: np.ndarray) -> np.ndarray`
**Pre:** prices is 1D numpy array with length >= 2
**Post:** Returns array of length len(prices)-1 with percentage returns
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_cumulative_returns_numba(returns: np.ndarray) -> np.ndarray`
**Pre:** returns is 1D numpy array
**Post:** Returns array of cumulative returns starting at 1.0
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_cagr_numba(final_value: float, initial_value: float, n_periods: float) -> float`
**Pre:** initial_value > 0, n_periods > 0
**Post:** Returns compound annual growth rate as decimal
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_sharpe_numba(returns: np.ndarray, risk_free_rate: float, periods_per_year: int) -> float`
**Pre:** returns is non-empty 1D array, periods_per_year > 0
**Post:** Returns annualized Sharpe ratio (excess return / std * sqrt(periods_per_year))
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_sortino_numba(returns: np.ndarray, risk_free_rate: float, periods_per_year: int) -> float`
**Pre:** returns is non-empty 1D array, periods_per_year > 0
**Post:** Returns annualized Sortino ratio using downside deviation
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_var_numba(returns: np.ndarray, confidence_level: float = 0.95) -> float`
**Pre:** returns has length >= 2, confidence_level in (0, 1)
**Post:** Returns Value at Risk at specified confidence level
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_cvar_numba(returns: np.ndarray, confidence_level: float = 0.95) -> float`
**Pre:** returns has length >= 2, confidence_level in (0, 1)
**Post:** Returns Conditional VaR (expected shortfall) beyond VaR threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_drawdown_series_numba(equity_curve: np.ndarray) -> np.ndarray`
**Pre:** equity_curve is 1D numpy array with length >= 1
**Post:** Returns array of drawdown percentages (negative values)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_max_drawdown_numba(equity_curve: np.ndarray) -> float`
**Pre:** equity_curve is 1D numpy array with length >= 1
**Post:** Returns maximum drawdown (most negative value)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_max_drawdown_duration_numba(equity_curve: np.ndarray) -> int`
**Pre:** equity_curve is 1D numpy array with length >= 1
**Post:** Returns maximum number of periods to recover from peak
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_win_rate_numba(pnl_array: np.ndarray) -> float`
**Pre:** pnl_array is 1D numpy array
**Post:** Returns percentage of positive P&L values (0-100)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_profit_factor_numba(pnl_array: np.ndarray) -> float`
**Pre:** pnl_array is 1D numpy array
**Post:** Returns gross_profit / gross_loss (inf if no losses)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_volatility_numba(returns: np.ndarray, periods_per_year: int) -> float`
**Pre:** returns is non-empty 1D array, periods_per_year > 0
**Post:** Returns annualized volatility (sample_std * sqrt(periods_per_year))
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_numba_metrics_info() -> dict`
**Pre:** Module loaded successfully (Numba available)
**Post:** Returns dict with numba_available, functions_optimized count
**Raises:** RuntimeError if Numba not available
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] ALL metric functions use @jit(nopython=True, cache=False) decorator
- [ ] Runtime raises RuntimeError if Numba not installed (line 50)
- [ ] No fallbacks to pure Python - Numba is REQUIRED
- [ ] Sample standard deviation uses ddof=1 (manual calculation)
- [ ] Sharpe ratio annualizes with sqrt(periods_per_year)
- [ ] Sortino uses downside deviation (only negative returns)
- [ ] Drawdowns calculated as (equity - peak) / peak (negative percentages)
- [ ] VaR uses bubble sort for Numba compatibility
- [ ] CVaR averages returns below VaR threshold
- [ ] Win rate returns 0-100 percentage (not 0-1 decimal)
- [ ] Profit factor returns inf if gross_loss = 0
- [ ] All functions handle edge cases (empty arrays, zero division, etc.)
- [ ] Module logs initialization info with function count

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PERF-001 Numba for hot paths | 07-performance.md | Use JIT compilation for performance-critical code | ✅ OK - ALL functions use @jit(nopython=True) |
| PERF-002 No fallbacks | 07-performance.md | No pure Python fallbacks allowed | ✅ OK - Raises RuntimeError if Numba missing |
| PERF-003 cache=False | 07-performance.md | Disable cache for dynamic trading data | ✅ OK - All use cache=False |
| PERF-004 nopython=True | 07-performance.md | Use nopython mode for maximum speed | ✅ OK - All functions use nopython=True |
| ERR-001 Exception handling | 05-error-handling.md | Catch specific exceptions | ⚠️ NOT APPLIED - Uses broad Exception on import (line 41) |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ OK - Logs module load info |
| TYP-001 Type hints | 02-type-hints.md | All functions have type hints | ✅ OK - Complete type coverage |
| VAL-001 Input validation | 08-validation.md | Validate inputs before processing | ❌ GAP - No validation of array shapes/types |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - Pure functions, no global state |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy (required), numba (REQUIRED - no fallback), scipy (not used, manual impl)
- **Internal:** None (pure utility module)

---

## Required Tests
- **test_numba_metrics.py:**
  - Success: Sharpe ratio matches manual calculation (within 1e-6)
  - Success: Sortino uses downside deviation only
  - Success: Max drawdown correctly identifies peak-to-trough
  - Success: Drawdown duration returns correct period count
  - Success: Win rate returns percentage 0-100
  - Success: Profit factor handles all-positive case (returns inf)
  - Success: VaR returns correct percentile
  - Success: CVaR averages tail losses correctly
  - Success: Volatility annualizes correctly with periods_per_year
  - Edge: Empty arrays return NaN or 0 as appropriate
  - Edge: Single element arrays handled without crash
  - Edge: Zero division handled (returns 0, inf, or NaN as appropriate)
  - Performance: Sharpe calculation < 10ms for 10K data points
  - Performance: Max drawdown < 5ms for 10K data points
  - Error: Module raises RuntimeError if Numba not installed

---

## Notes
This is a CRITICAL performance module. Numba is REQUIRED - the code explicitly raises RuntimeError if Numba is not available (line 50). Performance improvements: 50-100x for returns, 40-90x for Sortino, 60-120x for max drawdown, 30-80x for VaR/CVaR. All functions use nopython=True for maximum speed and cache=False for dynamic trading data. The sample_std_numba helper manually calculates ddof=1 since Numba's np.std doesn't support the ddof parameter.
