# fractional_differentiation.py

## Purpose
Implements López de Prado's fractional differentiation for creating stationary features while preserving memory in financial time series, with 50-100x Numba JIT acceleration.

---

## Type Definitions / Data Classes

### FractionalDifferentiation Class
```python
class FractionalDifferentiation:
    threshold: float = 1e-3              # Weight cutoff threshold for expanding window
    adfuller_alpha: float = 0.05         # Significance level for ADF stationarity test
    max_lookback: int | None = None      # Maximum window size (None = use threshold)
    use_parallel: bool = False           # Use parallel processing for large datasets
    numba_enabled: bool = True           # Enable Numba JIT acceleration (50-100x speedup)
    _weights_cache: Dict[float, np.ndarray]  # Cache for calculated weights
```

**Validation Rules:**
- `threshold`: Must be > 0, typically 1e-3 to 1e-5
- `adfuller_alpha`: Must be between 0 and 1, typically 0.05
- `d` (differentiation order): Must satisfy 0 < d < 1
- Series input: Must have length >= 100 for reliable ADF tests
- Numba availability: Falls back to pure Python if unavailable (with warning)

### FractionalDiffTransformer Class
```python
class FractionalDiffTransformer:
    d: float = 0.5                       # Differentiation order
    threshold: float = 1e-5              # Weight cutoff threshold
    auto_find_d: bool = False            # Automatically find optimal d during fit
    adfuller_alpha: float = 0.05         # Significance level for ADF test
    use_parallel: bool = False           # Use parallel processing
    numba_enabled: bool = True           # Enable Numba JIT
    optimal_d_: float | None = None      # Fitted optimal d value
    feature_names_in_: List[str] = None  # Input feature names
```

**Validation Rules:**
- Scikit-learn transformer interface compliance
- `d` must be in [0, 1] range
- Requires at least 50 observations after differentiation for ADF test

---

## Function Signatures (Contracts)

### `get_weights(d: float, threshold: float = None) -> np.ndarray`
**Pre:** 0 < d < 1, threshold > 0
**Post:** Returns array of weights calculated via binomial expansion
**Raises:** No explicit exceptions, handles via warnings
**Retry:** No
**Side Effects:** Caches weights in `_weights_cache` dictionary

### `fractional_diff(series: pd.Series | np.ndarray, d: float, threshold: float = None) -> pd.Series`
**Pre:** Series length >= 100, 0 < d < 1, non-empty series
**Post:** Returns fractionally differentiated series with NaNs for initial values
**Raises:** TypeError if series not pd.Series/np.ndarray, ValueError if empty
**Retry:** No
**Side Effects:** None (pure transformation)

### `find_optimal_d(series: pd.Series | np.ndarray, min_d: float = 0.0, max_d: float = 1.0, step: float = 0.05, adfuller_alpha: float = None, method: str = 'binary') -> Tuple[float, float, Dict]`
**Pre:** Series length >= 100, 0 <= min_d < max_d <= 1
**Post:** Returns (optimal_d, p_value, metadata) achieving stationarity
**Raises:** Warns if series length < 100
**Retry:** No
**Side Effects:** Multiple ADF tests on differentiated series

### `_binary_search_d(series: pd.Series, min_d: float, max_d: float, alpha: float) -> Tuple[float, float, Dict]`
**Pre:** max_d achieves stationarity, series is clean (no NaNs)
**Post:** Returns minimum d with p-value < alpha
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Performs up to 50 ADF test iterations

### `_grid_search_d(series: pd.Series, min_d: float, max_d: float, step: float, alpha: float) -> Tuple[float, float, Dict]`
**Pre:** Series is clean, step > 0
**Post:** Returns best d from grid search
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Tests multiple d values from grid

### `calculate_memory_loss(original: pd.Series, frac_diff: pd.Series, lags: int = 20) -> Dict[str, float]`
**Pre:** Both series non-empty after NaN removal
**Post:** Returns dictionary with ACF-based memory metrics
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** None (pure calculation)

### `compare_d_values(series: pd.Series, d_values: List[float] = None) -> pd.DataFrame`
**Pre:** Series length >= 100
**Post:** Returns DataFrame with comparison metrics for each d
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Multiple fractional_diff and ADF tests

### Numba JIT Functions (Private)
### `calculate_weights_numba(d: float, threshold: float) -> np.ndarray`
**Pre:** 0 < d < 1, threshold > 0
**Post:** Returns weights array, stops when abs(w_k) < threshold
**Raises:** No exceptions in Numba
**Retry:** No
**Side Effects:** None (pure function)

### `fractional_diff_fast_numba(series: np.ndarray, weights: np.ndarray) -> np.ndarray`
**Pre:** series is 1D array, weights is 1D array
**Post:** Returns differentiated array with NaNs for initial values
**Raises:** No exceptions in Numba
**Retry:** No
**Side Effects:** None (pure function)

### `fractional_diff_parallel_numba(series: np.ndarray, weights: np.ndarray) -> np.ndarray`
**Pre:** series is 1D array, weights is 1D array
**Post:** Returns differentiated array using parallel processing
**Raises:** No exceptions in Numba
**Retry:** No
**Side Effects:** None (pure function)

### Transformer Interface Functions
### `fit(X: pd.DataFrame | np.ndarray, y = None) -> FractionalDiffTransformer`
**Pre:** X is 2D array or DataFrame
**Post:** Sets optimal_d_ and feature_names_in_, returns self
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** May call find_optimal_d if auto_find_d=True

### `transform(X: pd.DataFrame | np.ndarray) -> pd.DataFrame`
**Pre:** X is 2D, fitted with optimal_d_ set
**Post:** Returns DataFrame with fractionally differentiated columns
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** Applies fractional_diff to each column

### Convenience Functions
### `apply_frac_diff_to_dataframe(df: pd.DataFrame, d: float = 0.5, columns: List[str] = None, threshold: float = 1e-5, use_parallel: bool = False) -> pd.DataFrame`
**Pre:** df is non-empty DataFrame
**Post:** Returns DataFrame with _fracdiff suffix columns
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** None (creates copy of DataFrame)

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] Numba JIT acceleration provides 50-100x speedup on weight calculations
- [ ] Fractional differentiation preserves memory while achieving stationarity
- [ ] ADF test correctly identifies stationary series (p-value < alpha)
- [ ] Binary search for optimal d converges within 50 iterations
- [ ] Grid search tests all specified d values
- [ ] Memory loss calculation returns valid metrics (0-100% range)
- [ ] Transformer interface is scikit-learn compatible
- [ ] Cache mechanism reduces redundant weight calculations
- [ ] Fallback to pure Python when Numba unavailable
- [ ] Series validation prevents empty or too-short inputs
- [ ] NaN handling in differentiated series preserves index
- [ ] Parallel processing enabled for datasets > 10K points

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ PARTIAL - Some parameters lack type hints in Numba functions |
| PERF-001 | BASE_RULES | Use Numba JIT for hot paths | ✅ OK - All core functions use @jit/@njit |
| PERF-005 | BASE_RULES | Profile before optimizing | ✅ OK - Comments document 50-100x speedup |
| ARCH-007 | BASE_RULES | Composition > inheritance | ✅ OK - FractionalDiffTransformer composes FractionalDifferentiation |
| LOG-004 | BASE_RULES | Error logging | ⚠️ PARTIAL - Uses warnings but no structured logging |
| CC-007 | BASE_RULES | Functions < 20 lines | ⚠️ PARTIAL - Some functions exceed 20 lines (binary_search_d: 62 lines) |
| TST-005 | BASE_RULES | Coverage > 80% | ❓ UNKNOWN - No test coverage data |
| TRD-007 | BASE_RULES | Annualization documented | ✅ OK - Not applicable (no trading days assumption) |
| FMT-001 | BASE_RULES | Line length <= 100 | ✅ OK - Black formatted |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - No mutable default arguments |

**Specific Financial ML Requirements:**
- López de Prado fixed-window fractional differentiation correctly implemented
- Binomial expansion weights: w_k = -w_{k-1} * ((d - k + 1) / k)
- ADF stationarity test with configurable significance level
- Memory preservation measured via autocorrelation function
- Scikit-learn transformer interface for pipeline integration

**Performance Requirements:**
- Numba JIT compilation enabled by default
- 50-100x speedup on weight calculations vs pure Python
- Parallel processing option for large datasets (>10K points)
- Weight caching to avoid redundant calculations
- Vectorized operations where possible

---

## Dependencies
- **External:**
  - numpy (array operations)
  - pandas (Series/DataFrame handling)
  - numba (JIT compilation - REQUIRED for performance)
  - statsmodels (adfuller test - optional, has fallback)

- **Internal:**
  - `app.core.statsmodels_fallback` (fallback adfuller if statsmodels unavailable)

- **Optional:**
  - numba: If unavailable, falls back to pure Python (with warning)
  - statsmodels: If unavailable, uses fallback implementation

---

## Required Tests
- **tests/backtesting/feature_engineering/test_fractional_differentiation.py:**
  - Success paths:
    - Calculate weights for various d values (0.1, 0.5, 0.9)
    - Apply fractional differentiation to random walk series
    - Find optimal d via binary search
    - Find optimal d via grid search
    - Calculate memory loss metrics
    - Compare multiple d values
    - Transformer fit/transform interface
    - Apply to DataFrame columns
  - Error paths:
    - Empty series raises ValueError
    - Non-Series/ndarray input raises TypeError
    - Series length < 100 produces warning
    - Invalid d values (d < 0 or d > 1) behavior
  - Edge cases:
    - Series with NaN values
    - Very short series (length < 50)
    - d = 0 (no differentiation)
    - d = 1 (integer differentiation)
    - Threshold at boundary conditions
    - Numba unavailable scenario
    - Cache hit for repeated weight calculations
    - Parallel vs single-threaded execution
  - Performance:
    - Verify 50-100x speedup with Numba enabled
    - Benchmark weight calculation time
    - Benchmark differentiation time for 10K points

- **tests/backtesting/feature_engineering/test_fractional_diff_numba.py:**
  - Numba-specific tests:
    - JIT compilation succeeds
    - Cached functions return same results
    - Parallel version matches serial version results
    - Fallback to pure Python when Numba unavailable

---

## Notes
- **Critical:** Numba JIT is REQUIRED for production performance (50-100x speedup)
- **Memory:** Weight caching uses (d, threshold) as key - may consume memory for many unique combos
- **Stationarity:** ADF test requires minimum 50 observations after differentiation
- **Scikit-learn:** Transformer interface enables pipeline integration for feature engineering
- **López de Prado Reference:** Chapter 3, Section 3.4 of "Advances in Financial Machine Learning"
- **Fallback:** Gracefully handles missing numba/statsmodels dependencies
