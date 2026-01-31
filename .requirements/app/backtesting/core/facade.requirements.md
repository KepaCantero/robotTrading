# facade.py

## Purpose
Simplified facade for backtesting operations that hides orchestration complexity and provides clean API for running backtests, parameter sweeps, and result management.

---

## Type Definitions / Data Classes

### BacktestRunnerFacade Class
```python
class BacktestRunnerFacade:
    config_loader: BacktestConfigLoader      # REQUIRED - Loads and validates YAML config
    backtest_config: BacktestConfig          # REQUIRED - Validated backtest configuration
    results: BoundedResults                  # REQUIRED - Thread-safe results storage (maxlen=1000)
    backtest_results_objects: List[tuple]    # REQUIRED - Stores (test_name, BacktestResult) pairs
    output_dir: Path                         # REQUIRED - Directory for reports (created if missing)
    quotes: List[Any]                        # REQUIRED - Market data quotes loaded via DataLoader
    data_loader: DataLoader | None           # OPTIONAL - Initialized in load_data()
```

**Validation Rules:**
- `config_path` must exist and be valid YAML (raises FileNotFoundError)
- `output_dir` is created with `mkdir(parents=True, exist_ok=True)`
- `results` has maxlen=1000 for automatic memory management
- `quotes` must be loaded before running backtests
- All dates must be valid ISO format strings (YYYY-MM-DD)

---

## Function Signatures (Contracts)

### `__init__(config_path: str) -> None`
**Pre:** config_path exists and points to valid YAML file
**Post:** Facade initialized with config, output directory created, BoundedResults initialized
**Raises:** FileNotFoundError if config_path doesn't exist
**Retry:** No
**Side Effects:** File I/O (reads YAML), directory creation (mkdir)

### `async load_data(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> None`
**Pre:** config_loader has input section with valid dates
**Post:** self.quotes populated with market data, self.data_loader initialized
**Raises:** ValueError if date parsing fails, DataLoader errors
**Retry:** No
**Side Effects:** Async data loading, PortfolioBuilder instantiation

### `run_baseline(strategy: Any, strategy_name: Optional[str] = None) -> Dict[str, Any]`
**Pre:** quotes loaded, strategy has generate_signals() method
**Post:** Returns dict with metrics (total_pnl, sharpe_ratio, etc.), result stored in self.results
**Raises:** RuntimeError if strategy fails, ValueError if invalid inputs
**Retry:** No
**Side Effects:** Executor execution, result storage

### `run_strategy_test(strategy: Any, test_name: str, test_type: str = 'custom', **metadata) -> Dict[str, Any]`
**Pre:** quotes loaded, test_name is non-empty string
**Post:** Returns result dict with metadata merged, result stored
**Raises:** ValueError if test_name empty, RuntimeError on execution failure
**Retry:** No
**Side Effects:** Executor execution, result storage with metadata

### `run_parameter_sweep(strategy_factory: Any, parameters: Dict[str, List[Any]], test_name_prefix: str = 'param_sweep') -> List[Dict[str, Any]]`
**Pre:** parameters dict has non-empty lists, strategy_factory callable with **params signature
**Post:** Returns list of result dicts (one per combination)
**Raises:** TypeError if strategy_factory not callable, ValueError on invalid parameters
**Retry:** No
**Side Effects:** Multiple executor executions, results storage

### `get_results() -> pd.DataFrame`
**Pre:** None
**Post:** Returns DataFrame with all results sorted by sharpe_ratio descending
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `save_results(output_formats: Optional[List[str]] = None) -> None`
**Pre:** output_formats contains 'csv' and/or 'json'
**Post:** Files written to self.output_dir with timestamp
**Raises:** IOError if file write fails
**Retry:** No
**Side Effects:** File I/O (writes CSV/JSON)

### `get_best_result(metric: str = 'sharpe_ratio') -> Optional[Dict[str, Any]]`
**Pre:** None
**Post:** Returns best result dict or None if no results
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `clear_results() -> None`
**Pre:** None
**Post:** All results and backtest_objects cleared
**Raises:** No
**Retry:** No
**Side Effects:** Memory cleanup

### `create_backtest_runner(config_path: str) -> BacktestRunnerFacade`
**Pre:** config_path valid
**Post:** Returns BacktestRunnerFacade instance
**Raises:** FileNotFoundError if config invalid
**Retry:** No
**Side Effects:** Object instantiation

---

## Acceptance Criteria
- [ ] AC-FACADE-001: Initialization validates YAML exists and creates output directory
- [ ] AC-FACADE-002: load_data() populates quotes with valid market data
- [ ] AC-FACADE-003: run_baseline() returns dict with all required metrics (total_pnl, sharpe_ratio, etc.)
- [ ] AC-FACADE-004: run_parameter_sweep() tests all combinations and returns N results where N = product(len(v) for v in parameters.values())
- [ ] AC-FACADE-005: get_results() returns DataFrame sorted by sharpe_ratio DESC
- [ ] AC-FACADE-006: save_results() creates files with timestamp in filename
- [ ] AC-FACADE-007: clear_results() empties both results and backtest_results_objects
- [ ] AC-FACADE-008: All results stored are within BoundedResults maxlen (1000)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules with 23 P0)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FAC-001 | BASE_RULES.md (DP-002) | Factory pattern for executor creation | ✅ OK - Uses BacktestExecutorFactory.create() |
| FAC-002 | BASE_RULES.md (ARCH-001) | Layered architecture - facade in application layer | ✅ OK - No domain/infrastructure mixing |
| FAC-003 | BASE_RULES.md (SOL-001) | Single Responsibility - facade only coordinates | ✅ OK - Delegates to executor/loader |
| FAC-004 | BASE_RULES.md (CC-002) | No code duplication | ⚠️ NOT APPLIED - _result_to_dict duplicated with orchestrator |
| FAC-005 | BASE_RULES.md (BT-004) | Realistic costs in backtesting | ✅ OK - Uses config.commission_per_trade |
| FAC-006 | BASE_RULES.md (LOG-001) | Structured logging | ✅ OK - Uses logger with context |
| FAC-007 | BASE_RULES.md (TYP-001) | Type hints coverage | ✅ OK - All methods have type hints |
| FAC-008 | BASE_RULES.md (TRD-004) | Audit trail for trading | ✅ FIXED - 2026-02-01: Added structured audit logging for all run_* methods with timestamp, parameters, config_summary, results_summary, execution_time |

**GAP Analysis:**
- **FAC-004:** _result_to_dict() is duplicated between facade.py and orchestrator.py. Should extract to shared utility.
- **FAC-008:** ✅ FIXED - Added structured audit logging with timestamp, parameters, config_summary, results_summary, execution_time for all run_* methods

---

## Dependencies
- **External:** pandas, yaml (PyYAML), pathlib
- **Internal:**
  - `app.backtesting.core.config_loader.BacktestConfigLoader`
  - `app.backtesting.core.executor.BacktestExecutorFactory`
  - `app.backtesting.core.orchestrator.BoundedResults`
  - `app.backtesting.models.BacktestResult`
  - `app.backtesting.data_loader.DataLoader`
  - `app.services.portfolio_builder.PortfolioBuilder`

---

## Required Tests
- **tests/backtesting/core/test_facade.py:**
  - Test initialization with valid/invalid config paths
  - Test load_data() with date ranges
  - Test run_baseline() returns valid result dict
  - Test run_strategy_test() with metadata
  - Test run_parameter_sweep() generates all combinations
  - Test get_results() sorts by sharpe_ratio
  - Test save_results() creates CSV/JSON files
  - Test get_best_result() by different metrics
  - Test clear_results() empties storage
  - Test BoundedResults maxlen enforcement
  - Test error handling when quotes not loaded

---

## Notes
Implements Facade pattern to hide complexity of BacktestExecutor, DataLoader, PortfolioBuilder, and BoundedResults. Critical for user-friendly backtesting API.

---

## Fixes Applied 2026-02-01

### ✅ GAP-FAC-008: Missing Audit Trail - FIXED
**Summary:** Added comprehensive structured audit trail logging for all backtest execution methods.

**Changes Made:**
1. **Imports updated:**
   - Added `time` import for execution time tracking
   - Added `timezone` to datetime import for UTC timestamps

2. **`run_baseline()` method enhanced:**
   - Start logging: timestamp, strategy_name, strategy_class, config_summary (initial_capital, commission)
   - Completion logging: results_summary (total_pnl, return_pct, sharpe_ratio, total_trades, win_rate, max_drawdown), execution_time_seconds

3. **`run_strategy_test()` method enhanced:**
   - Start logging: timestamp, test_name, test_type, strategy_class, metadata_keys, metadata_count
   - Completion logging: results_summary, execution_time_seconds

4. **`run_parameter_sweep()` method enhanced:**
   - Start logging: timestamp, parameter_combinations_count, parameter_names, parameter_values_count
   - Completion logging: total_results, execution_time_seconds, best_result_summary

**Validation Results:**
- ✅ Python syntax compilation: Passed
- ✅ Ruff linting: All checks passed
- ✅ Black formatting: Passed
- ✅ Isort import ordering: Passed
- ✅ Bandit security scan: No issues identified
