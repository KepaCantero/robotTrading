# backtest_results_processor.py

## Purpose
Processes and aggregates multiple backtest results, calculating summary statistics, finding best/worst results, computing percentiles, and generating DataFrames for analysis.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

This file contains a plain class - no Pydantic models or dataclasses.

### BacktestResultsProcessor Class
```python
class BacktestResultsProcessor:
    results: List[BacktestResultValue]    # REQUIRED - List of backtest results to process
```

**Validation Rules:**
- `results` is initialized to empty list
- All methods handle empty results gracefully (return None or 0)

---

## Function Signatures (Contracts)

### `BacktestResultsProcessor.__init__() -> None`
**Pre:** None
**Post:** Processor initialized with empty results list
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestResultsProcessor.add_result(result: BacktestResultValue) -> None`
**Pre:** result is valid BacktestResultValue
**Post:** result appended to results list
**Raises:** None
**Retry:** No
**Side Effects:** Mutates results list

### `BacktestResultsProcessor.add_results(results: List[BacktestResultValue]) -> None`
**Pre:** results is list of valid BacktestResultValue
**Post:** All results appended to results list
**Raises:** None
**Retry:** No
**Side Effects:** Mutates results list (extends)

### `BacktestResultsProcessor.clear() -> None`
**Pre:** None
**Post:** results list cleared to empty
**Raises:** None
**Retry:** No
**Side Effects:** Mutates results list

### `BacktestResultsProcessor.get_summary_statistics() -> Optional[Dict[str, Any]]`
**Pre:** None
**Post:** Returns dict with mean/std/min/max/median for returns, sharpe, drawdown, win_rate
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestResultsProcessor.get_best_result(metric: str = 'total_return_pct') -> Optional[BacktestResultValue]`
**Pre:** results is non-empty
**Post:** Returns result with maximum value for specified metric
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestResultsProcessor.get_worst_result(metric: str = 'total_return_pct') -> Optional[BacktestResultValue]`
**Pre:** results is non-empty
**Post:** Returns result with minimum value for specified metric
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestResultsProcessor.get_percentile(percentile: float, metric: str = 'total_return_pct') -> Optional[Decimal]`
**Pre:** percentile in range [0, 100]
**Post:** Returns percentile value for specified metric
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestResultsProcessor.get_results_dataframe() -> Optional[pd.DataFrame]`
**Pre:** None
**Post:** Returns DataFrame with columns: run_id, total_return, sharpe_ratio, max_drawdown, etc.
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestResultsProcessor.compare_to_benchmark(benchmark_return: Decimal) -> Optional[Dict[str, Any]]`
**Pre:** benchmark_return is valid Decimal
**Post:** Returns dict with beats_benchmark count, beat_percentage, avg_excess_return
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] add_result() appends single result to results list
- [ ] add_results() extends results list with multiple results
- [ ] clear() empties results list
- [ ] get_summary_statistics() returns None if no results
- [ ] get_summary_statistics() calculates mean/std/min/max/median for returns
- [ ] get_summary_statistics() includes sharpe_ratios if any results have sharpe_ratio
- [ ] get_summary_statistics() includes max_drawdowns if any results have max_drawdown
- [ ] get_summary_statistics() includes win_rates if any results have win_rate
- [ ] get_best_result() returns None if no results
- [ ] get_best_result() finds max by specified metric (default: total_return_pct)
- [ ] get_worst_result() returns None if no results
- [ ] get_worst_result() finds min by specified metric (default: total_return_pct)
- [ ] get_percentile() returns None if no results
- [ ] get_percentile() uses np.percentile for calculation
- [ ] get_results_dataframe() returns None if no results
- [ ] get_results_dataframe() includes run_id, total_return, sharpe_ratio, max_drawdown, volatility, total_trades, winning_trades, losing_trades, win_rate
- [ ] compare_to_benchmark() returns None if no results
- [ ] compare_to_benchmark() calculates beats_benchmark count
- [ ] compare_to_benchmark() calculates beat_percentage (0-100)
- [ ] compare_to_benchmark() calculates avg_excess_return
- [ ] All statistics use float() conversion for Decimal values
- [ ] None values in BacktestResultValue handled gracefully (skipped in aggregates)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Only processes/aggregates results |
| TYP-001 Type hints | 02-type-hints.md | All functions have type hints | ✅ OK - Complete type coverage |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ⚠️ NOT APPLIED - Returns plain Dict for summary (by design for JSON serialization) |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ✅ FIXED - 2026-02-01 - Added validation logging |
| ERR-001 Exception handling | 05-error-handling.md | Handle edge cases gracefully | ✅ OK - Returns None for empty results |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ FIXED - 2026-02-01 - Added structured logging for all operations |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - Pure aggregation functions |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, decimal, logging, typing
- **Internal:** `app.domain.value_objects.backtest_result.BacktestResultValue`

---

## Required Tests
- **test_backtest_results_processor.py:**
  - Success: add_result() appends to results list
  - Success: add_results() extends results list
  - Success: clear() empties results list
  - Success: get_summary_statistics() returns None for empty results
  - Success: get_summary_statistics() calculates correct mean/std/min/max/median
  - Success: get_summary_statistics() includes only metrics present in results
  - Success: get_best_result() finds max by total_return_pct
  - Success: get_best_result() finds max by custom metric (sharpe_ratio)
  - Success: get_best_result() returns None for empty results
  - Success: get_worst_result() finds min by total_return_pct
  - Success: get_worst_result() finds min by custom metric (max_drawdown)
  - Success: get_worst_result() returns None for empty results
  - Success: get_percentile() calculates correct percentile (50th = median)
  - Success: get_percentile() returns None for empty results
  - Success: get_results_dataframe() returns None for empty results
  - Success: get_results_dataframe() creates DataFrame with correct columns
  - Success: compare_to_benchmark() returns None for empty results
  - Success: compare_to_benchmark() calculates beats_benchmark count correctly
  - Success: compare_to_benchmark() calculates beat_percentage correctly
  - Success: compare_to_benchmark() calculates avg_excess_return correctly
  - Edge: Results with None metrics skipped in aggregates
  - Edge: Single result handled correctly (mean = value, std = 0)
  - Integration: DataFrame contains all expected columns with correct types

---

## Notes
This is a results aggregation utility for analyzing multiple backtest runs. Provides statistical summary (mean/std/min/max/median) across all runs for key metrics: returns, Sharpe, max drawdown, win rate. Handles optional metrics gracefully - only includes them if present in results. The get_best_result() and get_worst_result() methods support any metric via getattr() with default to Decimal('0'), enabling flexible analysis. get_percentile() uses np.percentile for accurate calculation. The DataFrame output is convenient for visualization and further analysis. Benchmark comparison calculates what percentage of runs beat the benchmark and average excess return. All Decimal values converted to float for numpy/pandas compatibility. The processor is stateful - results accumulate until clear() is called. This design enables incremental result addition during iterative backtesting (e.g., Monte Carlo, grid search).
