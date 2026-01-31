# backtest_orchestrator.py

## Purpose
Orchestrates backtest execution for multiple backtest types (baseline, learning engines, walk-forward, Monte Carlo, ablation, grid search, OOS, multi-strategy, regime analysis) while maintaining clean architecture separation.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

This file contains a plain class - no Pydantic models or dataclasses.

### BacktestOrchestrator Class
```python
class BacktestOrchestrator:
    config: Dict[str, Any]              # REQUIRED - Orchestrator configuration
    backtest_config: Dict[str, Any]     # REQUIRED - Backtest-specific config
    output_dir: str                     # REQUIRED - Output directory path
    parallel_enabled: bool              # REQUIRED - Whether parallelization is enabled
    max_workers: Optional[int]          # OPTIONAL - Max worker count for parallel exec
    STRATEGY_NAME_MAP: Dict[str, str]   # REQUIRED - YAML to factory name mapping (class attribute)
```

**Validation Rules:**
- `output_dir` defaults to 'results' if not in config
- `parallel_enabled` defaults to True if not in config
- `max_workers` defaults to None if not in config (use CPU count)
- `STRATEGY_NAME_MAP` maps YAML names to factory names for 7 strategies

---

## Function Signatures (Contracts)

### `BacktestOrchestrator.__init__(config: Dict[str, Any]) -> None`
**Pre:** config contains backtest configuration
**Post:** Orchestrator initialized with config, output_dir, parallel settings
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestOrchestrator.run_baseline_backtest() -> BacktestResultValue`
**Pre:** backtest_config is valid
**Post:** Returns BacktestResultValue with all modules active
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_learning_engine_backtests() -> List[BacktestResultValue]`
**Pre:** backtest_config is valid
**Post:** Returns list of BacktestResultValue for each learning engine
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_walk_forward_validation() -> BacktestResultValue`
**Pre:** backtest_config is valid
**Post:** Returns BacktestResultValue from walk-forward optimization
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_monte_carlo_simulation(num_simulations: int = 1000) -> List[BacktestResultValue]`
**Pre:** num_simulations > 0
**Post:** Returns list of BacktestResultValue for each simulation
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_ablation_study() -> Dict[str, BacktestResultValue]`
**Pre:** backtest_config is valid
**Post:** Returns dict mapping module names to BacktestResultValue
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_grid_search(param_grid: Dict[str, List[Any]]) -> BacktestResultValue`
**Pre:** param_grid is non-empty dict of parameter names to value lists
**Post:** Returns BacktestResultValue for best parameter combination
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_out_of_sample_validation() -> BacktestResultValue`
**Pre:** backtest_config is valid
**Post:** Returns BacktestResultValue from forward validation
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_multi_strategy_backtest() -> List[BacktestResultValue]`
**Pre:** backtest_config is valid
**Post:** Returns list of BacktestResultValue per strategy
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator.run_regime_analysis() -> Dict[str, BacktestResultValue]`
**Pre:** backtest_config is valid
**Post:** Returns dict mapping regime names to BacktestResultValue
**Raises:** NotImplementedError (currently not implemented)
**Retry:** No
**Side Effects:** Logs info message

### `BacktestOrchestrator._map_strategy_name(strategy_name: str) -> str`
**Pre:** strategy_name is a key in STRATEGY_NAME_MAP or not
**Post:** Returns mapped factory name or original name if not in map
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Orchestrator initialized with config from YAML
- [ ] Output directory defaults to 'results' if not specified
- [ ] Parallelization enabled by default
- [ ] Max workers defaults to None (CPU count) if not specified
- [ ] All backtest methods raise NotImplementedError (not yet implemented)
- [ ] run_baseline_backtest logs "Starting baseline backtest"
- [ ] run_learning_engine_backtests logs "Starting learning engine backtests"
- [ ] run_walk_forward_validation logs "Starting walk-forward validation"
- [ ] run_monte_carlo_simulation logs simulation count
- [ ] run_ablation_study logs "Starting ablation study"
- [ ] run_grid_search logs "Starting grid search optimization"
- [ ] run_out_of_sample_validation logs "Starting out-of-sample validation"
- [ ] run_multi_strategy_backtest logs "Starting multi-strategy backtest"
- [ ] run_regime_analysis logs "Starting regime analysis"
- [ ] STRATEGY_NAME_MAP maps 7 YAML names to factory names
- [ ] _map_strategy_name returns mapped name or original if not found

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Only orchestrates backtest execution |
| TYP-001 Type hints | 02-type-hints.md | All functions have type hints | ✅ OK - Complete type coverage |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ❌ GAP - Uses BacktestConfigValue but returns plain Dict |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ⚠️ NOT APPLIED - No validation of config structure |
| ERR-001 Exception handling | 05-error-handling.md | Handle errors appropriately | ⚠️ NOT APPLIED - All methods raise NotImplementedError |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ OK - Logs info messages for all operations |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - No side effects (not yet implemented) |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** logging, typing
- **Internal:**
  - `app.domain.value_objects.backtest_config.BacktestConfigValue`
  - `app.domain.value_objects.backtest_result.BacktestResultValue`

---

## Required Tests
- **test_backtest_orchestrator.py:**
  - Success: __init__ extracts output_dir from config
  - Success: __init__ extracts parallel_enabled from config (defaults True)
  - Success: __init__ extracts max_workers from config (defaults None)
  - Success: All backtest methods raise NotImplementedError with clear message
  - Success: All backtest methods log appropriate info message
  - Success: _map_strategy_name returns mapped name for known strategies
  - Success: _map_strategy_name returns original name for unknown strategies
  - Success: STRATEGY_NAME_MAP contains 7 strategy mappings
  - Edge: Empty config uses all defaults
  - Edge: Config with missing optional fields uses defaults
  - Integration: BacktestConfigValue.from_dict called with backtest_config

---

## Notes
This is the backtest orchestrator - a coordination layer for executing different types of backtests. Currently a stub with all methods raising NotImplementedError. The design follows clean architecture: orchestrator coordinates but doesn't execute business logic (delegates to engines/backtester). Supports 9 backtest types: baseline (all modules), learning engines (individual module testing), walk-forward (Tomasini validation), Monte Carlo (stress testing), ablation (module impact analysis), grid search (parameter optimization), OOS validation (forward testing), multi-strategy (parallel strategies), regime analysis (performance by market condition). STRATEGY_NAME_MAP maps YAML config names to factory names: momentum_modular -> modular_momentum, mean_reversion_modular -> mean_reversion, pairs_trading_modular -> pairs_trading, etc. This abstraction allows UI/infrastructure to orchestrate without knowing implementation details.
