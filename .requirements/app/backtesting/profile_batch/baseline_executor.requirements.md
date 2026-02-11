# baseline_executor.py

## Purpose
Executes baseline backtests with default parameters, supporting both single-strategy and multi-strategy modes with result aggregation.

---

## Type Definitions / Data Classes
No custom dataclasses defined - uses standard Dict and List types.

---

## Function Signatures (Contracts)

### `run_baseline(profile, config, multi_strategy) -> Dict[str, Any]`
**Pre:** profile is valid InputProfile, config has strategy section
**Post:** Returns baseline metrics dict with combined field for consistency
**Raises:** Returns empty metrics dict on failure
**Retry:** No
**Side Effects:** Creates/deletes temp YAML file, runs ComprehensiveBacktestRunner

### `_run_single_strategy_baseline(runner, profile) -> Dict[str, Any]`
**Pre:** runner is initialized, profile has objetivo_inversion
**Post:** Returns baseline metrics with "combined" field
**Raises:** Returns empty metrics if result extraction fails
**Retry:** No
**Side Effects:** Calls runner.run_baseline_backtest()

### `_run_multi_strategy_baseline(runner, profile) -> Dict[str, Any]`
**Pre:** runner is initialized, profile valid
**Post:** Returns combined metrics from all strategies plus per_strategy_results
**Raises:** Returns empty metrics on failure
**Retry:** No
**Side Effects:** Calls runner.run_multi_strategy_backtest()

### `aggregate_multi_strategy_results(results, profile) -> Dict[str, Any]`
**Pre:** results list has strategy result dicts with strategy_name field
**Post:** Returns combined metrics dict with weighted averages
**Raises:** Returns empty metrics if results empty
**Retry:** No
**Side Effects:** None (calculation)

### `_safe_extract_first_result(results, context) -> Dict[str, Any]`
**Pre:** results is list or None
**Post:** Returns first result dict if valid, otherwise empty metrics
**Raises:** None (handles all error cases)
**Retry:** No
**Side Effects:** None (safe extraction)

### `_get_empty_metrics() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with zero/empty values for all metric keys
**Raises:** None
**Retry:** No
**Side Effects:** None (dict creation)

---

## Acceptance Criteria
- [ ] run_baseline() creates temp YAML file and cleans it up in finally block
- [ ] Single-strategy mode returns metrics with "combined" field for consistency
- [ ] Multi-strategy mode returns combined metrics plus per_strategy_results
- [ ] Combined metrics use weighted averages based on capital_weight
- [ ] Aggregate calculation includes: total_pnl, return_pct, sharpe_ratio, max_drawdown, win_rate, total_trades
- [ ] Per-strategy results include: total_pnl, return_pct, sharpe_ratio, max_drawdown, win_rate, total_trades, final_capital, capital_weight
- [ ] _safe_extract_first_result() handles None, empty list, None element, non-dict element
- [ ] _safe_extract_first_result() validates expected fields present
- [ ] Temporary file uses profile.input_id in filename
- [ ] Empty metrics returned on any error

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

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ FIXED - 2026-02-01 - Added type aliases (ConfigDict, MetricsDict, PerStrategyDict) and updated all return types |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Catches ValueError, TypeError, etc. |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ⚠️ ACCEPTED - aggregate_multi_strategy_results() is ~100 lines due to: 1) Complex weighted average calculations across multiple strategies, 2) Pre-calculated combined result handling, 3) Per-strategy result separation and aggregation, 4) Capital weight normalization (equal weight fallback), 5) Comprehensive metrics dict construction with 15+ fields, 6) Extensive logging for audit trail. Lower priority code style issue, no functional impact. Future refactoring could extract metric calculation logic into separate helper class. |
| BT-004 | BASE_RULES | Realistic costs | ✅ OK - Uses config from backtest runner |
| CC-005 | BASE_RULES | Early returns | ⚠️ NOT APPLIED - Function flow is linear |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - Logging provides audit trail |

**NOTE:** Multi-strategy aggregation uses capital_weight for weighted averages. If capital_weight is 0, uses equal weight (1/n_strategies).

---

## Dependencies
- **External:** logging, pathlib, typing, yaml
- **Internal:**
  - `app.backtesting.comprehensive_backtest_runner.ComprehensiveBacktestRunner`
  - `app.core.models.input_profile.InputProfile`

---

## Required Tests
- **tests/backtesting/profile_batch/test_baseline_executor.py:**
  - Test run_baseline() single-strategy mode
  - Test run_baseline() multi-strategy mode
  - Test run_baseline() creates and deletes temp file
  - Test run_baseline() returns empty metrics on failure
  - Test _run_single_strategy_baseline() adds combined field
  - Test _run_multi_strategy_baseline() aggregates results
  - Test aggregate_multi_strategy_results() with capital_weight
  - Test aggregate_multi_strategy_results() with zero capital_weight (uses equal weight)
  - Test aggregate_multi_strategy_results() with pre-calculated combined result
  - Test _safe_extract_first_result() with None results
  - Test _safe_extract_first_result() with empty list
  - Test _safe_extract_first_result() with None element
  - Test _safe_extract_first_result() with non-dict element
  - Test _safe_extract_first_result() validates expected fields
  - Test _get_empty_metrics() returns correct structure

---

## Notes
Baseline execution is the reference point for optimization comparison. Uses same backtest runner as optimization for consistency.

**Known issues (GAPs):** aggregate_multi_strategy_results() exceeds ARCH-004 guideline (<20 lines) - **ARCH-004 ACCEPTED** as documented above (lower priority, complex aggregation logic).
