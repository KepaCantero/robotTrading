# facade.py

## Purpose
Simplified facade interface for backtesting operations, hiding complexity of orchestration and execution while providing clean API for running backtests, parameter sweeps, and result management.

---

## Type Definitions / Data Classes

### BacktestRunnerFacade
```python
class BacktestRunnerFacade:
    config_loader: BacktestConfigLoader      # YAML config loader
    backtest_config: BacktestConfig          # Loaded configuration
    results: BoundedResults                  # Thread-safe results storage
    backtest_results_objects: List[tuple]    # (test_name, BacktestResult) tuples
    output_dir: Path                         # Reports output directory
    quotes: List[Any]                        # Market data quotes
    data_loader: Optional[DataLoader]        # Data loader instance
```
**Validation Rules:**
- config_path must exist and be valid YAML
- output_dir created with parents=True, exist_ok=True
- quotes loaded via async _load_portfolio_market_data

---

## Function Signatures (Contracts)

### `BacktestRunnerFacade.__init__(config_path: str) -> None`
**Pre:** config_path is valid path to YAML configuration file
**Post:** Facade initialized with loaded config, executor, results storage, and output directory created
**Raises:** FileNotFoundError if config_path doesn't exist, ValueError if YAML invalid
**Retry:** ❌ No
**Side Effects:** Creates output_dir, loads config, initializes BoundedResults, logs initialization

### `BacktestRunnerFacade.load_data(start_date=None, end_date=None) -> None` (async)
**Pre:** Config has input_config with start_date and end_date
**Post:** self.quotes populated with market data, self.data_loader initialized
**Raises:** ValueError if dates invalid or data loading fails
**Retry:** ❌ No
**Side Effects:** Creates DataLoader, calls PortfolioBuilder, loads market data asynchronously

### `BacktestRunnerFacade._load_portfolio_market_data(start_date, end_date) -> List[Any]` (async)
**Pre:** start_date and end_date are valid datetime objects
**Post:** Returns list of quotes for portfolio symbols
**Raises:** ValueError if data loading fails
**Retry:** ❌ No
**Side Effects:** Calls PortfolioBuilder.build_portfolio_quotes asynchronously

### `BacktestRunnerFacade.run_baseline(strategy, strategy_name=None) -> Dict[str, Any]`
**Pre:** self.quotes is non-empty, strategy has generate_signals method
**Post:** Returns dict with backtest metrics, result added to self.results and self.backtest_results_objects
**Raises:** ValueError if quotes empty or strategy invalid
**Retry:** ❌ No
**Side Effects:** Creates executor, executes backtest, logs audit trail (start/complete), stores results

### `BacktestRunnerFacade.run_strategy_test(strategy, test_name, test_type='custom', **metadata) -> Dict[str, Any]`
**Pre:** self.quotes non-empty, strategy valid, test_name non-empty
**Post:** Returns dict with backtest metrics plus metadata, result stored
**Raises:** ValueError if inputs invalid
**Retry:** ❌ No
**Side Effects:** Creates executor, executes backtest, logs audit trail, adds metadata to result_dict, stores results

### `BacktestRunnerFacade.run_parameter_sweep(strategy_factory, parameters, test_name_prefix='param_sweep') -> List[Dict[str, Any]]`
**Pre:** strategy_factory is callable creating strategy from kwargs, parameters is dict of param_name -> list of values
**Post:** Returns list of result dicts for all parameter combinations
**Raises:** ValueError if parameters empty or factory fails
**Retry:** ❌ No
**Side Effects:** Generates all combinations via itertools.product, executes each combination, logs audit trail (start/complete), stores all results

### `BacktestRunnerFacade.get_results() -> pd.DataFrame`
**Pre:** None
**Post:** Returns DataFrame with all results, sorted by sharpe_ratio descending if available
**Raises:** ❌ No (returns empty DataFrame if no results)
**Retry:** ❌ No
**Side Effects:** None (pure read)

### `BacktestRunnerFacade.save_results(output_formats=None) -> None`
**Pre:** None
**Post:** Results saved to output_dir in specified formats
**Raises:** OSError if file write fails
**Retry:** ❌ No
**Side Effects:** Creates CSV and/or JSON files with timestamp in filename

### `BacktestRunnerFacade._result_to_dict(result, test_type, test_name) -> Dict[str, Any]`
**Pre:** result is BacktestResult or dict, test_type and test_name are strings
**Post:** Returns dict with test_type, test_name, total_pnl, return_pct, final_capital, total_trades, win_rate, sharpe_ratio, sortino_ratio, max_drawdown, avg_trade_pnl
**Raises:** ❌ No (handles invalid result types gracefully)
**Retry:** ❌ No
**Side Effects:** None (conversion only)

### `BacktestRunnerFacade.get_best_result(metric='sharpe_ratio') -> Optional[Dict[str, Any]]`
**Pre:** metric is valid key in results
**Post:** Returns result dict with highest metric value or None if no results
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure read and max calculation)

### `BacktestRunnerFacade.clear_results() -> None`
**Pre:** None
**Post:** All results cleared from both storage containers
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Clears self.results and self.backtest_results_objects, logs info

### `create_backtest_runner(config_path: str) -> BacktestRunnerFacade`
**Pre:** config_path is valid path to YAML config
**Post:** Returns initialized BacktestRunnerFacade instance
**Raises:** See BacktestRunnerFacade.__init__
**Retry:** ❌ No
**Side Effects:** Creates and returns BacktestRunnerFacade

---

## Acceptance Criteria
- [ ] Facade initializes successfully with valid config path
- [ ] Facade creates output directory if it doesn't exist
- [ ] load_data loads quotes asynchronously
- [ ] run_baseline executes backtest and returns result dict
- [ ] run_baseline logs structured audit trail (start/complete)
- [ ] run_strategy_test executes backtest with custom metadata
- [ ] run_parameter_sweep generates all parameter combinations
- [ ] run_parameter_sweep executes all combinations and returns results
- [ ] get_results returns DataFrame sorted by sharpe_ratio
- [ ] get_results returns empty DataFrame if no results
- [ ] save_results saves CSV if 'csv' in output_formats
- [ ] save_results saves JSON if 'json' in output_formats
- [ ] save_results uses config default formats if output_formats is None
- [ ] get_best_result returns result with highest metric
- [ ] get_best_result returns None if no results
- [ ] clear_results clears both results containers
- [ ] All execution methods log audit trails with structured context

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

**Reglas universales:** Ver `../../BASE_RULES.md` for 96 universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Facade provides simplified interface |
| DP-001 | BASE_RULES.md | Facade pattern | ✅ OK - Hides complexity of backtesting system |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ FIXED - All methods have explicit return type annotations |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ FIXED - Uses StrategyProtocol, StrategyFactory, BacktestResultDict TypedDict, Dict[str, float|int|str] |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ OK - Uses extra={} for structured context |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses specific BacktestResultError instead of generic error dict |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ✅ OK - No passwords/tokens logged |
| LOG-006 | BASE_RULES.md | Timing info in logs | ✅ OK - execution_time_seconds logged |
| TRD-004 | BASE_RULES.md | Audit trail for trade decisions | ✅ OK - Comprehensive audit logging with audit_type, timestamp, context |
| ARCH-004 | BASE_RULES.md | Small functions | ✅ FIXED - Extracted helper methods (_log_backtest_start, _log_backtest_complete, _get_config_summary, _get_results_summary, _store_result, _log_custom_backtest_start, _execute_parameter_combinations, _log_parameter_sweep_start, _log_parameter_sweep_complete, _get_best_result_summary, _calculate_return_pct, _get_total_trades, _get_win_rate, _get_sharpe_ratio, _get_sortino_ratio, _get_max_drawdown, _calculate_avg_trade_pnl) |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ FIXED - Uses BacktestResultError with context (test_type, test_name) instead of generic error dict |

---

## Dependencies
- **External:** logging, time, datetime, pathlib.Path, typing, pandas (as pd), itertools
- **Internal:** app.backtesting.core.config_loader.BacktestConfigLoader
- **Internal:** app.backtesting.core.executor.BacktestExecutorFactory
- **Internal:** app.backtesting.core.orchestrator.BoundedResults
- **Internal (Deferred):** app.backtesting.data_loader.DataLoader
- **Internal (Deferred):** app.services.portfolio_builder.PortfolioBuilder
- **Internal (Deferred):** app.services.portfolio_config_manager.get_portfolio_config_manager

---

## Required Tests
- **tests/unit/backtesting/core/test_facade.py:**
  - Test __init__ creates output directory
  - Test __init__ loads config successfully
  - Test load_data loads quotes asynchronously
  - Test load_data uses config dates if not provided
  - Test run_baseline executes backtest
  - Test run_baseline returns result dict with all metrics
  - Test run_baseline logs audit trail with structured context
  - Test run_baseline stores result in results and backtest_results_objects
  - Test run_strategy_test executes backtest with metadata
  - Test run_strategy_test adds metadata to result_dict
  - Test run_parameter_sweep generates all combinations
  - Test run_parameter_sweep executes all combinations
  - Test run_parameter_sweep logs audit trail with combination count
  - Test get_results returns DataFrame sorted by sharpe_ratio
  - Test get_results returns empty DataFrame when no results
  - Test save_results saves CSV when format specified
  - Test save_results saves JSON when format specified
  - Test save_results uses config default when formats not specified
  - Test save_results uses timestamp in filename
  - Test _result_to_dict converts BacktestResult correctly
  - Test _result_to_dict handles invalid result type
  - Test get_best_result returns max metric result
  - Test get_best_result returns None when empty
  - Test clear_results clears both containers
  - Test create_backtest_runner factory function

---

## Notes
- Facade pattern hides complexity of executor, orchestrator, data loading
- Comprehensive audit logging with structured context (audit_type, timestamp, execution_time, results_summary)
- Parameter sweep uses itertools.product for Cartesian product of all parameter combinations
- Results stored in two places: BoundedResults (lightweight dicts) and backtest_results_objects (full BacktestResult objects)
- Output files timestamped to avoid overwriting
- Async data loading for better performance with I/O-bound operations
