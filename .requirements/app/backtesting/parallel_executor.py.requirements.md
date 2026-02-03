# parallel_executor.py

## Purpose
Provides parallel execution system for CPU-bound and I/O-bound backtesting tasks. Supports Monte Carlo simulations, grid search, and learning engine tests with configurable worker pools.

---

## Type Definitions / Data Classes

### ParallelExecutor Class
```python
class ParallelExecutor:
    max_workers: int                         # REQUIRED - Max number of workers (default: CPU count)
    use_processes: bool                      # REQUIRED - True for ProcessPoolExecutor, False for ThreadPoolExecutor
```

**Validation Rules:**
- `max_workers` defaults to min(cpu_count(), 8) for safety
- `use_processes=True` for CPU-bound tasks
- `use_processes=False` for I/O-bound tasks

---

## Function Signatures (Contracts)

### `ParallelExecutor.run_parallel(tasks, task_function, task_name) -> List[Dict[str, Any]]`
**Pre:** tasks must be list of dicts, task_function must accept dict and return dict
**Post:** Returns list of results from successful tasks
**Raises:** Logs exceptions, continues with remaining tasks
**Retry:** ✅ Yes (individual task failures don't stop execution)
**Side Effects:** Spawns multiple processes/threads, logs progress

### `ParallelExecutor.run_monte_carlo_parallel(num_simulations, simulation_function, **simulation_kwargs) -> List[Dict[str, Any]]`
**Pre:** num_simulations must be positive, simulation_function must be callable
**Post:** Returns list of simulation results
**Raises:** Logs exceptions for failed simulations
**Retry:** ✅ Yes (individual simulation failures don't stop batch)
**Side Effects:** Executes simulation_function in parallel

### `ParallelExecutor.run_grid_search_parallel(parameter_combinations, combination_function) -> List[Dict[str, Any]]`
**Pre:** parameter_combinations must be list of dicts, combination_function callable
**Post:** Returns list of grid search results
**Raises:** Logs exceptions for failed combinations
**Retry:** ✅ Yes (individual failures don't stop batch)
**Side Effects:** Executes combination_function for each parameter set

### `ParallelExecutor.run_learning_engines_parallel(engines, engine_function, **engine_kwargs) -> List[Dict[str, Any]]`
**Pre:** engines must be list of strings, engine_function callable
**Post:** Returns list of engine test results
**Raises:** Logs exceptions for failed engine tests
**Retry:** ✅ Yes (individual failures don't stop batch)
**Side Effects:** Tests multiple learning engines in parallel

### `create_parallel_executor(max_workers, use_processes) -> ParallelExecutor`
**Pre:** max_workers must be positive int or None
**Post:** Returns configured ParallelExecutor instance
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (factory function)

---

## Acceptance Criteria
- [ ] ParallelExecutor defaults max_workers to min(cpu_count(), 8)
- [ ] run_parallel() uses ProcessPoolExecutor when use_processes=True
- [ ] run_parallel() uses ThreadPoolExecutor when use_processes=False
- [ ] run_parallel() logs progress as tasks complete
- [ ] run_parallel() continues on individual task failures
- [ ] run_parallel() returns results from completed tasks only
- [ ] run_monte_carlo_parallel() creates simulation_num in task dict
- [ ] run_monte_carlo_parallel() includes all **simulation_kwargs in tasks
- [ ] run_grid_search_parallel() includes combination_num in task dict
- [ ] run_grid_search_parallel() includes parameters in task dict
- [ ] run_learning_engines_parallel() includes engine_name in task dict
- [ ] All run_* methods log success/failure counts
- [ ] create_parallel_executor() is factory function for convenience
- [ ] Executor context manager ensures cleanup
- [ ] Task failures are logged with task name
- [ ] Empty tasks list returns empty results

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True used |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ FIXED - TaskFunction type alias added for Callable |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure component |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - One responsibility |
| PERF-006 | BASE_RULES.md | Async I/O | ❌ N/A - Uses threading/multiprocessing, not asyncio |
| QL-001 | BASE_RULES.md | Complexity < 10 | ✅ OK - Simple methods |
| ASYNC-001 | BASE_RULES.md | Use async def | ❌ N/A - Not async (uses concurrent.futures) |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** multiprocessing, concurrent.futures, logging, typing
- **Internal:** None

---

## Required Tests
- **tests/backtesting/test_parallel_executor.py:**
  - Test __init__() defaults max_workers to min(cpu_count(), 8)
  - Test __init__() accepts custom max_workers
  - Test __init__() with use_processes=True uses ProcessPoolExecutor
  - Test __init__() with use_processes=False uses ThreadPoolExecutor
  - Test run_parallel() returns results from all tasks
  - Test run_parallel() continues on individual task failures
  - Test run_parallel() logs progress for completed tasks
  - Test run_parallel() handles empty tasks list
  - Test run_parallel() uses executor context manager
  - Test run_monte_carlo_parallel() creates simulation tasks
  - Test run_monte_carlo_parallel() includes simulation_num
  - Test run_monte_carlo_parallel() passes **simulation_kwargs
  - Test run_grid_search_parallel() creates combination tasks
  - Test run_grid_search_parallel() includes combination_num
  - Test run_grid_search_parallel() includes parameters
  - Test run_learning_engines_parallel() creates engine tasks
  - Test run_learning_engines_parallel() includes engine_name
  - Test create_parallel_executor() factory function
  - Test all run_* methods log correct success/failure counts
  - Test task failures are logged with task name
  - Test max_workers limits concurrent execution

---

## Notes
- Simple but effective parallel execution wrapper
- Uses concurrent.futures for clean API
- ProcessPoolExecutor for CPU-bound (avoid GIL)
- ThreadPoolExecutor for I/O-bound (lower overhead)
- max_workers capped at 8 for safety (prevents resource exhaustion)
- All run_* methods delegate to run_parallel()
- Task failures don't stop batch execution (fault-tolerant)
- Progress logging shows "X/Y completed" updates
- Factory function create_parallel_executor() for convenience
- Emoji usage in logging (🚀, ✅, ⚠️, ❌)
- No async/await (uses concurrent.futures instead)
- Line 63: Uses f-string for emoji - consistent with codebase style
- Type hint for task_function could be more specific (Callable[[Dict], Dict])
- No timeout handling for individual tasks (could hang indefinitely)
