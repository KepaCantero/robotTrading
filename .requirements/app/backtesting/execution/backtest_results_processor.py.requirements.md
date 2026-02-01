# backtest_results_processor.py

## Purpose
Processes and aggregates backtest results, calculating summary statistics, best/worst results, percentiles, and benchmark comparisons.

---

## Type Definitions / Data Classes

### BacktestResultsProcessor Class
```python
class BacktestResultsProcessor:
    results: List[BacktestResultValue]    # REQUIRED - List of accumulated backtest results
```

**Validation Rules:**
- `results` can be empty (initialized as empty list)
- All items in `results` must be BacktestResultValue instances
- Optional fields on BacktestResultValue are handled gracefully (sharpe_ratio, max_drawdown, win_rate, etc.)

---

## Function Signatures (Contracts)

### `__init__() -> None`
**Pre:** None
**Post:** Instance initialized with empty results list
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Initializes instance state

### `add_result(result: BacktestResultValue) -> None`
**Pre:** result is a valid BacktestResultValue instance
**Post:** result appended to results list
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Modifies results list, logs debug message

### `add_results(results: List[BacktestResultValue]) -> None`
**Pre:** results is a list of BacktestResultValue instances
**Post:** All results appended to results list
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Extends results list, logs info message

### `clear() -> None`
**Pre:** None
**Post:** results list is empty
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Clears results list

### `get_summary_statistics() -> Optional[Dict[str, Any]]`
**Pre:** None
**Post:** Returns summary statistics dict or None if no results
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs info message with summary

**Summary Statistics Structure:**
```python
{
    'total_runs': int,                              # Number of results
    'returns': {
        'mean': float,                               # Mean total return
        'std': float,                                # Std dev of returns
        'min': float,                                # Minimum return
        'max': float,                                # Maximum return
        'median': float,                             # Median return
    },
    'sharpe_ratios': { ... },                       # Optional, same structure
    'max_drawdowns': { ... },                       # Optional, same structure
    'win_rates': { ... },                           # Optional, same structure
}
```

### `get_best_result(metric: str = 'total_return_pct') -> Optional[BacktestResultValue]`
**Pre:** metric is a valid attribute name on BacktestResultValue
**Post:** Returns result with highest metric value or None if no results
**Raises:** ❌ No (getattr returns Decimal('0') as default)
**Retry:** ❌ No
**Side Effects:** None

### `get_worst_result(metric: str = 'total_return_pct') -> Optional[BacktestResultValue]`
**Pre:** metric is a valid attribute name on BacktestResultValue
**Post:** Returns result with lowest metric value or None if no results
**Raises:** ❌ No (getattr returns Decimal('0') as default)
**Retry:** ❌ No
**Side Effects:** None

### `get_percentile(percentile: float, metric: str = 'total_return_pct') -> Optional[Decimal]`
**Pre:** 0 <= percentile <= 100, metric is valid attribute name
**Post:** Returns percentile value as Decimal or None if no results
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `get_results_dataframe() -> Optional[pd.DataFrame]`
**Pre:** None
**Post:** Returns pandas DataFrame with results or None if no results
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

**DataFrame Columns:**
- run_id (int)
- total_return (float)
- total_return_pct (float)
- sharpe_ratio (float | None)
- sortino_ratio (float | None)
- max_drawdown (float | None)
- volatility (float | None)
- total_trades (int)
- winning_trades (int)
- losing_trades (int)
- win_rate (float | None)

### `compare_to_benchmark(benchmark_return: Decimal) -> Optional[Dict[str, Any]]`
**Pre:** benchmark_return is a valid Decimal
**Post:** Returns comparison dict or None if no results
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

**Comparison Dictionary Structure:**
```python
{
    'benchmark_return': str,                    # Benchmark as string
    'total_runs': int,                           # Number of results
    'beats_benchmark': int,                      # Count beating benchmark
    'beat_percentage': float,                    # Percentage beating benchmark
    'avg_excess_return': str,                    # Average excess return
}
```

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] add_result() appends single result to list
- [ ] add_result() logs debug message with result count and return
- [ ] add_results() extends list with multiple results
- [ ] add_results() logs info message with counts
- [ ] clear() empties the results list
- [ ] get_summary_statistics() returns None when results empty
- [ ] get_summary_statistics() calculates correct mean/std/min/max/median
- [ ] get_summary_statistics() includes optional sections only when data exists
- [ ] get_best_result() returns None when results empty
- [ ] get_best_result() finds result with max metric value
- [ ] get_worst_result() returns None when results empty
- [ ] get_worst_result() finds result with min metric value
- [ ] get_percentile() returns None when results empty
- [ ] get_percentile() calculates correct np.percentile value
- [ ] get_results_dataframe() returns None when results empty
- [ ] get_results_dataframe() creates DataFrame with all expected columns
- [ ] compare_to_benchmark() returns None when results empty
- [ ] compare_to_benchmark() calculates beat count correctly
- [ ] compare_to_benchmark() calculates beat percentage correctly
- [ ] compare_to_benchmark() calculates average excess return correctly
- [ ] All numeric conversions preserve precision (Decimal -> float -> Decimal)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-001 | 01-formatting-style.md | Line length ≤ 100 | ✅ OK |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK |
| TYP-002 | 02-type-hints.md | Modern syntax (X \| None) | ✅ OK |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Only processes results |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK |
| LOG-002 | 09-logging-observability.md | Context in logs | ✅ OK - Uses extra dict for context |
| LOG-003 | 09-logging-observability.md | Appropriate levels | ✅ OK - debug for adds, info for summaries |
| PERF-002 | 19-high-performance-python.md | Generators for large data | ⚠️ NOT APPLIED - Results typically fit in memory |
| ARCH-001 | 05-architecture.md | Layered architecture | ✅ OK - Application layer |

---

## Dependencies
- **External:** `logging`, `decimal`, `typing`, `numpy`, `pandas`
- **Internal:**
  - `app.domain.value_objects.backtest_result.BacktestResultValue`

---

## Required Tests
- **tests/unit/backtesting/execution/test_backtest_results_processor.py:**
  - Test __init__ initializes empty results list
  - Test add_result() adds single result
  - Test add_result() logs debug message
  - Test add_results() adds multiple results
  - Test add_results() logs info message
  - Test clear() empties results list
  - Test get_summary_statistics() returns None when empty
  - Test get_summary_statistics() calculates correct statistics
  - Test get_summary_statistics() handles None values in optional fields
  - Test get_best_result() returns None when empty
  - Test get_best_result() finds maximum by default metric
  - Test get_best_result() finds maximum by custom metric
  - Test get_worst_result() returns None when empty
  - Test get_worst_result() finds minimum by default metric
  - Test get_worst_result() finds minimum by custom metric
  - Test get_percentile() returns None when empty
  - Test get_percentile() calculates correct percentile (50th = median)
  - Test get_percentile() handles edge cases (0th, 100th)
  - Test get_results_dataframe() returns None when empty
  - Test get_results_dataframe() creates correct DataFrame structure
  - Test get_results_dataframe() handles None values in optional fields
  - Test compare_to_benchmark() returns None when empty
  - Test compare_to_benchmark() calculates beat count correctly
  - Test compare_to_benchmark() calculates beat percentage correctly
  - Test compare_to_benchmark() calculates average excess return correctly
  - Test Decimal precision is preserved through float conversions

---

## Notes
- This is a pure processing/utility class in the application layer
- Handles optional fields gracefully (sharpe_ratio, max_drawdown, win_rate)
- Uses numpy for statistical calculations
- Converts Decimal to float for numpy, then back to Decimal for results
- All methods are synchronous (no async operations)
- Structured logging with extra dict for context
