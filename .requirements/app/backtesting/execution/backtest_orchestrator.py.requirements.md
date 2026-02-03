# backtest_orchestrator.py

## Purpose
Orchestrates the execution of multiple backtest types (baseline, walk-forward, Monte Carlo, etc.) while maintaining clean architecture separation from UI/infrastructure.

---

## Type Definitions / Data Classes

### BacktestOrchestrator Class
```python
class BacktestOrchestrator:
    config: Dict[str, Any]                      # REQUIRED - Orchestrator configuration
    backtest_config: Dict[str, Any]             # REQUIRED - Validated backtest configuration
    output_dir: str                             # REQUIRED - Directory for results output
    parallel_enabled: bool                      # REQUIRED - Whether parallel execution is enabled
    max_workers: int | None                     # REQUIRED - Max parallel workers or None
    STRATEGY_NAME_MAP: Dict[str, str]           # REQUIRED - Strategy name mappings
```

**Validation Rules:**
- `config` must contain `output_directory` key (defaults to 'results')
- `config` must contain `parallelization.enabled` (defaults to True)
- `config` must contain `parallelization.max_workers` (defaults to None)

---

## Function Signatures (Contracts)

### `__init__(config: Dict[str, Any]) -> None`
**Pre:** config is a dictionary with backtest configuration
**Post:** Instance initialized with validated config and parallel settings
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Initializes instance state, loads backtest config

### `run_baseline_backtest() -> BacktestResultValue`
**Pre:** backtest_config is properly initialized
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_learning_engine_backtests() -> List[BacktestResultValue]`
**Pre:** backtest_config is properly initialized
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_walk_forward_validation() -> BacktestResultValue`
**Pre:** backtest_config is properly initialized
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_monte_carlo_simulation(num_simulations: int = 1000) -> List[BacktestResultValue]`
**Pre:** num_simulations > 0
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_ablation_study() -> Dict[str, BacktestResultValue]`
**Pre:** backtest_config is properly initialized
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_grid_search(param_grid: Dict[str, List[Any]]) -> BacktestResultValue`
**Pre:** param_grid is non-empty dict with list values
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_out_of_sample_validation() -> BacktestResultValue`
**Pre:** backtest_config is properly initialized
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_multi_strategy_backtest() -> List[BacktestResultValue]`
**Pre:** backtest_config is properly initialized
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `run_regime_analysis() -> Dict[str, BacktestResultValue]`
**Pre:** backtest_config is properly initialized
**Post:** Raises NotImplementedError (not yet implemented)
**Raises:** NotImplementedError always
**Retry:** ❌ No
**Side Effects:** Logs info message

### `_load_backtest_config(config: Dict[str, Any]) -> Dict[str, Any]`
**Pre:** config is a valid configuration dictionary
**Post:** Returns validated configuration (currently identity function)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (currently just returns input)

### `_map_strategy_name(strategy_name: str) -> str`
**Pre:** strategy_name is a non-empty string
**Post:** Returns mapped strategy name from STRATEGY_NAME_MAP or original if not found
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] All backtest execution methods raise NotImplementedError (placeholder status)
- [ ] STRATEGY_NAME_MAP contains all expected strategy mappings
- [ ] _map_strategy_name returns correct mapped names
- [ ] _map_strategy_name returns original name if not in map
- [ ] __init__ properly extracts output_directory from config
- [ ] __init__ properly extracts parallelization settings from config
- [ ] All methods log appropriate info messages before execution
- [ ] No direct dependencies on UI or infrastructure frameworks
- [ ] Uses domain value objects (BacktestConfigValue, BacktestResultValue)

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

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-001 | 01-formatting-style.md | Line length ≤ 100 | ✅ OK |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Only orchestrates backtests |
| SOL-005 | 03-solid-principles.md | Dependency Inversion | ✅ OK - Uses value objects from domain |
| ARCH-001 | 05-architecture.md | Layered architecture | ✅ OK - In application layer |
| ARCH-002 | 05-architecture.md | Dependencies inward | ✅ OK - Depends on domain value objects |
| CC-006 | 05-architecture.md | Explicit error handling | ⚠️ NOT APPLIED - All methods raise NotImplementedError (intentional) |
| LOG-003 | 09-logging-observability.md | Appropriate logging levels | ✅ OK - Uses info for operations |
| BT-001 | BASE_RULES.md | Walk-forward validation | ✅ OK - Has dedicated method |
| BT-002 | BASE_RULES.md | Out-of-sample testing | ✅ OK - Has dedicated method |
| BT-005 | BASE_RULES.md | Multiple periods testing | ✅ OK - Has regime analysis method |

---

## Dependencies
- **External:** `logging`, `typing`
- **Internal:**
  - `app.domain.value_objects.backtest_config.BacktestConfigValue`
  - `app.domain.value_objects.backtest_result.BacktestResultValue`

---

## Required Tests
- **tests/unit/backtesting/execution/test_backtest_orchestrator.py:**
  - Test __init__ extracts output_directory correctly
  - Test __init__ extracts parallelization settings correctly
  - Test __init__ uses defaults for missing config keys
  - Test _map_strategy_name with known strategy names
  - Test _map_strategy_name with unknown strategy names
  - Test all backtest methods raise NotImplementedError (current state)
  - Test STRATEGY_NAME_MAP contains expected mappings
  - Test logging occurs in all backtest methods
  - Integration tests when methods are implemented (future)

---

## Notes
- This is an orchestrator in the application layer with clean architecture
- All backtest execution methods are currently stub implementations
- Consider implementing these methods for full functionality
- Strategy name mapping supports legacy YAML to factory name conversion
- No infrastructure dependencies (FastAPI, SQLAlchemy) - good separation
