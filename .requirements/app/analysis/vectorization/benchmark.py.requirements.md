# benchmark.py

## Purpose
Benchmark vectorized vs non-vectorized implementations to demonstrate performance benefits of vectorization in trading systems.

---

## Type Definitions / Data Classes

### BenchmarkResult Class/DataClass (imported from models.py)
```python
@dataclass
class BenchmarkResult:
    function_name: str                      # REQUIRED - Name of benchmarked function
    vectorized_time: float                  # REQUIRED - Vectorized execution time (seconds)
    non_vectorized_time: float              # REQUIRED - Non-vectorized execution time (seconds)
    speedup: float                          # REQUIRED - Speedup factor (non_vectorized / vectorized)
    n_elements: int                         # REQUIRED - Number of elements processed
    per_element_time_vectorized: float      # REQUIRED - Time per element for vectorized (ns)
    per_element_time_non_vectorized: float  # REQUIRED - Time per element for non-vectorized (ns)
    memory_usage_vectorized: int | None     # OPTIONAL - Memory usage for vectorized (bytes)
    memory_usage_non_vectorized: int | None # OPTIONAL - Memory usage for non-vectorized (bytes)
    timestamp: float                        # REQUIRED - Benchmark timestamp
```

**Validation Rules:**
- All times must be positive (> 0)
- n_elements must be positive (> 0)
- speedup is calculated as non_vectorized_time / vectorized_time

---

## Function Signatures (Contracts)

### `__init__(warmup_iterations: int = 3, benchmark_iterations: int = 10, verbose: bool = False) -> VectorizationBenchmark`
**Pre:** warmup_iterations >= 0; benchmark_iterations >= 1
**Post:** Benchmark initialized with timing parameters
**Raises:** None
**Retry:** No
**Side Effects:** Stores configuration

### `benchmark_sum(n_elements: int = 1_000_000) -> BenchmarkResult`
**Pre:** n_elements > 0
**Post:** Returns BenchmarkResult with sum operation timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benchmark_ewm_calculate(n_elements: int = 100_000, span: int = 20) -> BenchmarkResult`
**Pre:** n_elements > 0; span > 0
**Post:** Returns BenchmarkResult with EWM calculation timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benchmark_rolling_calculation(n_elements: int = 50_000, window: int = 20) -> BenchmarkResult`
**Pre:** n_elements > 0; window > 0; window <= n_elements
**Post:** Returns BenchmarkResult with rolling mean timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benchmark_correlation(n_elements: int = 10_000, n_assets: int = 100) -> BenchmarkResult`
**Pre:** n_elements > 0; n_assets > 0
**Post:** Returns BenchmarkResult with correlation matrix timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benchmark_elementwise_operation(n_elements: int = 1_000_000) -> BenchmarkResult`
**Pre:** n_elements > 0
**Post:** Returns BenchmarkResult with element-wise operation timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benchmark_filtering(n_elements: int = 1_000_000) -> BenchmarkResult`
**Pre:** n_elements > 0
**Post:** Returns BenchmarkResult with filtering operation timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benchmark_groupby(n_elements: int = 100_000, n_groups: int = 50) -> BenchmarkResult`
**Pre:** n_elements > 0; n_groups > 0
**Post:** Returns BenchmarkResult with groupby aggregation timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benchmark_percentage_change(n_elements: int = 100_000) -> BenchmarkResult`
**Pre:** n_elements > 0
**Post:** Returns BenchmarkResult with percentage change timings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `run_all_benchmarks(n_elements: int | None = None) -> list[BenchmarkResult]`
**Pre:** None
**Post:** Returns list of BenchmarkResult for all standard benchmarks
**Raises:** None
**Retry:** No
**Side Effects:** Prints progress if verbose=True

### `generate_report(results: list[BenchmarkResult]) -> str`
**Pre:** results is non-empty list
**Post:** Returns formatted benchmark report string
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_latex_table(results: list[BenchmarkResult]) -> str`
**Pre:** results is non-empty list
**Post:** Returns LaTeX formatted table string
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_time_function(func: Callable[[], Any], warmup: bool = True) -> float`
**Pre:** func is callable
**Post:** Returns average execution time in seconds
**Raises:** None
**Retry:** No
**Side Effects:** Calls func multiple times for timing

---

## Acceptance Criteria
- [ ] All benchmarks use consistent warmup and iteration counts
- [ ] Non-vectorized implementations are actually non-vectorized (loops)
- [ ] Vectorized implementations use NumPy/Pandas operations
- [ ] Speedup is calculated correctly (non_vectorized_time / vectorized_time)
- [ ] Per-element times are in nanoseconds (× 1e9)
- [ ] Random seed is set for reproducibility (np.random.seed(42))
- [ ] Verbose mode prints timing information
- [ ] All benchmarks complete without exceptions
- [ ] Report includes summary statistics (avg, max, min speedup)
- [ ] LaTeX table is properly formatted

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| PERF-004 | BASE_RULES | Profile before optimizing | ✅ OK - Provides benchmarking for profiling |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear function names |
| LOG-006 | BASE_RULES | Timing info in logs | ✅ OK - Reports include timing |
| PERF-001 | BASE_RULES | Use vectorized operations | ✅ OK - Benchmark uses vectorized implementations |

---

## Dependencies
- **External:** numpy, pandas, time, dataclasses, typing
- **Internal:** app.analysis.vectorization.models.BenchmarkResult

---

## Required Tests
- **tests/unit/analysis/test_vectorization_benchmark.py:**
  - Test benchmark_sum returns valid BenchmarkResult
  - Test benchmark_ewm_calculate returns valid BenchmarkResult
  - Test benchmark_rolling_calculation returns valid BenchmarkResult
  - Test benchmark_correlation returns valid BenchmarkResult
  - Test benchmark_elementwise_operation returns valid BenchmarkResult
  - Test benchmark_filtering returns valid BenchmarkResult
  - Test benchmark_groupby returns valid BenchmarkResult
  - Test benchmark_percentage_change returns valid BenchmarkResult
  - Test run_all_benchmarks returns expected number of results
  - Test generate_report produces valid formatted string
  - Test generate_latex_table produces valid LaTeX
  - Test _time_function with warmup=True
  - Test _time_function with warmup=False
  - Verify speedup > 1 for all benchmarks (vectorized faster)
  - Test verbose flag produces output

---

## Notes
- Benchmarks demonstrate 10x-1000x speedups for vectorized operations
- Uses time.perf_counter() for high-precision timing
- Default sizes chosen to be representative but not excessively long
- Random seed ensures reproducibility across runs
