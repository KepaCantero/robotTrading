# baseline_executor.py

## Purpose
Executes baseline backtests with default parameters. Handles both single-strategy and multi-strategy execution modes with result aggregation.

---

## Type Definitions / Data Classes

### BaselineBacktestExecutor Class
```python
class BaselineBacktestExecutor:
    output_dir: Path                    # REQUIRED - Directory for temporary config files
```

**Validation Rules:**
- `output_dir` must be valid directory path
- `output_dir` is created if it doesn't exist (parents=True, exist_ok=True)

### Type Aliases
```python
ConfigDict = Dict[str, Any]                              # Configuration dictionary
MetricsDict = Dict[str, Union[float, int, str, bool, None]]  # Metrics dictionary
PerStrategyDict = Dict[str, MetricsDict]                 # Per-strategy results
```

---

## Function Signatures (Contracts)

### `BaselineBacktestExecutor.__init__(output_dir: Path) -> None`
**Pre:** output_dir must be valid path
**Post:** BaselineBacktestExecutor initialized with output_dir created
**Raises:** OSError if directory creation fails
**Retry:** No
**Side Effects:** Creates output_dir with parents=True, exist_ok=True

### `BaselineBacktestExecutor.run_baseline(profile: InputProfile, config: ConfigDict, multi_strategy: bool = False) -> MetricsDict`
**Pre:** profile must be valid, config must contain required backtest parameters
**Post:** Returns baseline metrics (single or multi-strategy combined)
**Raises:** ValueError, TypeError, KeyError, AttributeError, IndexError
**Retry:** No
**Side Effects:** Creates temp config file, runs backtest, cleans up temp file in finally block

### `BaselineBacktestExecutor._run_single_strategy_baseline(runner: ComprehensiveBacktestRunner, profile: InputProfile) -> MetricsDict`
**Pre:** runner must be initialized, profile must be valid
**Post:** Returns baseline metrics with "combined" field added
**Raises:** No (returns empty metrics on failure)
**Retry:** No
**Side Effects:** Runs baseline backtest via runner

### `BaselineBacktestExecutor._run_multi_strategy_baseline(runner: ComprehensiveBacktestRunner, profile: InputProfile) -> MetricsDict`
**Pre:** runner must be initialized, profile must be valid
**Post:** Returns combined metrics with per_strategy_results
**Raises:** No (returns empty metrics on failure)
**Retry:** No
**Side Effects:** Runs multi-strategy backtest, aggregates results

### `BaselineBacktestExecutor.aggregate_multi_strategy_results(results: List[Dict[str, Any]], profile: InputProfile) -> MetricsDict`
**Pre:** results must be list of strategy result dicts
**Post:** Returns combined metrics dictionary
**Raises:** No (returns empty metrics if no results)
**Retry:** No
**Side Effects:** None (calculates combined metrics)

### `BaselineBacktestExecutor._safe_extract_first_result(results: List[Dict[str, Any]] | None, context: str) -> MetricsDict`
**Pre:** context must be descriptive string for logging
**Post:** Returns first result dict if valid, otherwise empty metrics
**Raises:** No (handles all error cases)
**Retry:** No
**Side Effects:** Logs warnings for missing/invalid results

### `BaselineBacktestExecutor._get_empty_metrics() -> MetricsDict`
**Pre:** None
**Post:** Returns empty metrics dict with default values
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] run_baseline() creates temporary config file
- [ ] run_baseline() cleans up temp file in finally block
- [ ] run_baseline() returns _get_empty_metrics() on exception
- [ ] run_baseline() with multi_strategy=False calls _run_single_strategy_baseline
- [ ] run_baseline() with multi_strategy=True calls _run_multi_strategy_baseline
- [ ] _run_single_strategy_baseline() adds "combined" field to results
- [ ] _run_multi_strategy_baseline() includes per_strategy_results
- [ ] _run_multi_strategy_baseline() includes per_strategy_raw
- [ ] aggregate_multi_strategy_results() calculates weighted average metrics
- [ ] aggregate_multi_strategy_results() handles pre-calculated combined result
- [ ] aggregate_multi_strategy_results() returns empty metrics if no results
- [ ] _safe_extract_first_result() handles None results
- [ ] _safe_extract_first_result() handles empty list
- [ ] _safe_extract_first_result() handles None first element
- [ ] _safe_extract_first_result() validates expected fields
- [ ] _get_empty_metrics() returns all required metric fields

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

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - No mutable defaults |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True in error handler |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All functions have type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure layer |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Baseline execution only |
| LOG-003 | BASE_RULES.md | Appropriate logging levels | ✅ OK - Uses info, warning, error |
| QL-001 | BASE_RULES.md | Complexity < 10 | ⚠️ PARTIAL - aggregate_multi_strategy_results is complex |
| CC-007 | BASE_RULES.md | Small functions | ⚠️ PARTIAL - aggregate_multi_strategy_results > 50 lines |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** yaml, logging, pathlib, typing
- **Internal:**
  - `app.backtesting.comprehensive_backtest_runner.ComprehensiveBacktestRunner`
  - `app.core.models.input_profile.InputProfile`

---

## Required Tests
- **tests/backtesting/profile_batch/test_baseline_executor.py:**
  - Test __init__() creates output directory
  - Test run_baseline() with multi_strategy=False returns combined metrics
  - Test run_baseline() with multi_strategy=True returns per-strategy results
  - Test run_baseline() creates and cleans up temp config file
  - Test run_baseline() returns empty metrics on exception
  - Test _run_single_strategy_baseline() adds combined field
  - Test _run_multi_strategy_baseline() includes per_strategy_results
  - Test _run_multi_strategy_baseline() includes per_strategy_raw
  - Test aggregate_multi_strategy_results() with pre-calculated combined result
  - Test aggregate_multi_strategy_results() calculates weighted averages
  - Test aggregate_multi_strategy_results() returns empty metrics for empty list
  - Test _safe_extract_first_result() with None input
  - Test _safe_extract_first_result() with empty list
  - Test _safe_extract_first_result() with None first element
  - Test _safe_extract_first_result() validates expected fields
  - Test _get_empty_metrics() returns all required fields

---

## Notes
- Temporary config files use pattern: temp_{profile.input_id}.yaml
- Temp files are cleaned up in finally block regardless of success/failure
- Multi-strategy mode aggregates results using capital_weight for weighting
- Combined metrics include: total_pnl, return_pct, sharpe_ratio, max_drawdown, win_rate, total_trades, avg_trade_pnl, final_capital
- Per-strategy results extract key metrics for reporting
- Empty metrics have zero values to avoid KeyError in downstream code
