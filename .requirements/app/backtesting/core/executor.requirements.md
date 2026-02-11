# executor.py

## Purpose
Abstract base classes and concrete implementations for backtest execution following Template Method pattern with support for simple, parallel, and process pool execution strategies.

---

## Type Definitions / Data Classes

### BacktestExecutor (ABC)
```python
class BacktestExecutor(ABC):
    config: BacktestConfig      # REQUIRED - Backtest configuration
    _execution_count: int       # PRIVATE - Number of executions
```

**Validation Rules:**
- Abstract base class - must be subclassed
- execute() is abstract method
- validate_inputs() called before each execution

### SimpleBacktestExecutor
```python
class SimpleBacktestExecutor(BacktestExecutor):
    # Inherits all from BacktestExecutor
    # Uses SimpleBacktester for execution
```

**Validation Rules:**
- Executes backtests synchronously in-process
- Generates signals if not provided
- Supports diagnostic_logger and enable_risk_envelope options

### ParallelBacktestExecutor
```python
class ParallelBacktestExecutor(BacktestExecutor):
    max_workers: Optional[int]   # OPTIONAL - Max thread workers (None for auto)
```

**Validation Rules:**
- Uses ThreadPoolExecutor for I/O-bound parallelism
- max_workers defaults to min(len(strategies), 4)
- execute() delegates to SimpleBacktestExecutor for single execution

### ProcessPoolBacktestExecutor
```python
class ProcessPoolBacktestExecutor(BacktestExecutor):
    max_processes: Optional[int] # OPTIONAL - Max processes (None for auto)
```

**Validation Rules:**
- Uses multiprocessing for CPU-bound isolation
- 5 minute timeout per process
- Avoids threading issues with ML libraries (torch, tensorflow)

### BacktestExecutorFactory
```python
class BacktestExecutorFactory:
    ExecutorType: Literal['simple', 'parallel', 'process']  # TYPE
    _executor_registry: Dict[ExecutorType, Type[BacktestExecutor]]  # CLASS VAR
```

**Validation Rules:**
- Registry maps executor_type to executor class
- create() validates executor_type
- register_executor() allows custom executor registration

---

## Function Signatures (Contracts)

### `BacktestExecutor.__init__(config: BacktestConfig) -> None`
**Pre:** config is valid BacktestConfig
**Post:** Executor initialized with config, execution_count = 0
**Raises:** No
**Retry:** No
**Side Effects:** State initialization

### `BacktestExecutor.execute(quotes: QuotesType, strategy: StrategyType, **kwargs) -> BacktestResult`
**Pre:** quotes non-empty, strategy valid
**Post:** Returns BacktestResult with performance metrics
**Raises:** ValueError if inputs invalid, RuntimeError if execution fails
**Retry:** No
**Side Effects:** Calls _pre_execute(), abstract execution, _post_execute()

### `BacktestExecutor.validate_inputs(quotes: QuotesType, strategy: StrategyType) -> None`
**Pre:** None
**Post:** Raises ValueError if validation fails
**Raises:** ValueError if quotes empty, strategy None, or initial_capital <= 0
**Retry:** No
**Side Effects:** None (validation only)

### `BacktestExecutor._pre_execute(quotes: QuotesType, strategy: StrategyType) -> None`
**Pre:** None
**Post:** Inputs validated, execution_count incremented
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** Calls validate_inputs(), increments counter

### `BacktestExecutor._post_execute(result: BacktestResult) -> None`
**Pre:** result is valid BacktestResult
**Post:** Execution logged
**Raises:** No
**Retry:** No
**Side Effects:** Logging (debug level)

### `SimpleBacktestExecutor.execute(quotes: QuotesType, strategy: StrategyType, **kwargs) -> BacktestResult`
**Pre:** quotes non-empty, strategy has generate_signals()
**Post:** Returns BacktestResult
**Raises:** ValueError on invalid inputs, RuntimeError on failure
**Retry:** No
**Side Effects:** Creates SimpleBacktester, generates signals, runs backtest

### `ParallelBacktestExecutor.execute_batch(quotes: QuotesType, strategies: List[StrategyType], **kwargs) -> List[BacktestResult]`
**Pre:** quotes non-empty, strategies non-empty
**Post:** Returns list of BacktestResult (one per strategy)
**Raises:** No (errors caught and logged)
**Retry:** No
**Side Effects:** ThreadPoolExecutor execution, concurrent runs

### `ProcessPoolBacktestExecutor.execute(quotes: QuotesType, strategy: StrategyType, **kwargs) -> BacktestResult`
**Pre:** quotes non-empty, strategy is pickleable
**Post:** Returns BacktestResult from subprocess
**Raises:** RuntimeError on timeout or execution failure
**Retry:** No
**Side Effects:** Spawns Process, joins with timeout

### `ProcessPoolBacktestExecutor._execute_in_process(...) -> BacktestResult`
**Pre:** strategy pickleable, quotes pickleable
**Post:** Returns result from queue or raises
**Raises:** RuntimeError on timeout/error
**Retry:** No
**Side Effects:** Process.spawn(), join(timeout=300), terminate if alive

### `BacktestExecutorFactory.create(config: BacktestConfig, executor_type: ExecutorType = 'simple', max_workers: Optional[int] = None) -> BacktestExecutor`
**Pre:** executor_type in ['simple', 'parallel', 'process']
**Post:** Returns appropriate executor instance
**Raises:** ValueError if executor_type invalid
**Retry:** No
**Side Effects:** Object instantiation

### `BacktestExecutorFactory.register_executor(executor_type: ExecutorType, executor_class: Type[BacktestExecutor]) -> None`
**Pre:** executor_type not already registered, executor_class is BacktestExecutor subclass
**Post:** executor added to registry
**Raises:** No
**Retry:** No
**Side Effects:** Updates _executor_registry

### `_run_backtest_process(config, quotes, strategy, strategy_name, enable_risk_envelope, result_queue) -> None`
**Pre:** All arguments pickleable
**Post:** Result put in queue as ('success', result) or ('error', str)
**Raises:** No (catches and puts error in queue)
**Retry:** No
**Side Effects:** Runs backtest in subprocess, puts result in queue

---

## Acceptance Criteria
- [ ] AC-EXEC-001: BacktestExecutor.validate_inputs() raises ValueError on empty quotes
- [ ] AC-EXEC-002: BacktestExecutor.validate_inputs() raises ValueError if initial_capital <= 0
- [ ] AC-EXEC-003: SimpleBacktestExecutor.execute() returns BacktestResult
- [ ] AC-EXEC-004: ParallelBacktestExecutor.execute_batch() runs strategies concurrently
- [ ] AC-EXEC-005: ProcessPoolBacktestExecutor.execute() terminates after 300s timeout
- [ ] AC-EXEC-006: ProcessPoolBacktestExecutor.execute() raises RuntimeError on timeout
- [ ] AC-EXEC-007: BacktestExecutorFactory.create() raises ValueError on invalid executor_type
- [ ] AC-EXEC-008: BacktestExecutorFactory.register_executor() allows custom executor registration
- [ ] AC-EXEC-009: All executors increment _execution_count on execution
- [ ] AC-EXEC-010: ProcessPoolBacktestExecutor uses subprocess isolation for ML safety

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules with 23 P0)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| EXEC-001 | BASE_RULES.md (SOL-002) | Open/Closed - extensible executors | ✅ OK - Factory + ABC pattern |
| EXEC-002 | BASE_RULES.md (DP-002) | Factory pattern for creation | ✅ OK - BacktestExecutorFactory |
| EXEC-003 | BASE_RULES.md (DP-004) | Dependency injection | ✅ OK - Config injected via __init__ |
| EXEC-004 | BASE_RULES.md (TYP-001) | Type hints coverage | ✅ OK - Full type hints with aliases |
| EXEC-005 | BASE_RULES.md (ASYNC-001) | Timeout on external calls | ✅ OK - 300s timeout on process |
| EXEC-006 | BASE_RULES.md (CC-007) | Small functions | ✅ OK - Methods focused and concise |
| EXEC-007 | BASE_RULES.md (ARCH-007) | Composition over inheritance | ✅ OK - Uses composition for backtester |
| EXEC-008 | BASE_RULES.md (PERF-006) | Process isolation for CPU-bound | ✅ OK - ProcessPool for ML safety |
| EXEC-009 | BASE_RULES.md (LOG-004) | Error logging with stack traces | ✅ OK - logger.error with exc_info=True |

**GAP Analysis:**
- No critical gaps found. Design follows SOLID principles well.
- Optional: Add metrics tracking for execution time per executor type.

---

## Dependencies
- **External:** abc, concurrent.futures, multiprocessing, typing
- **Internal:**
  - `app.backtesting.models.BacktestConfig`
  - `app.backtesting.models.BacktestResult`
  - `app.backtesting.engine.SimpleBacktester`

---

## Required Tests
- **tests/backtesting/core/test_executor.py:**
  - Test BacktestExecutor.validate_inputs() with empty quotes
  - Test BacktestExecutor.validate_inputs() with invalid initial_capital
  - Test SimpleBacktestExecutor.execute() returns valid result
  - Test SimpleBacktestExecutor.execute() generates signals if not provided
  - Test ParallelBacktestExecutor.execute_batch() concurrent execution
  - Test ParallelBacktestExecutor.execute_batch() handles individual failures
  - Test ProcessPoolBacktestExecutor.execute() subprocess isolation
  - Test ProcessPoolBacktestExecutor.execute() timeout and termination
  - Test BacktestExecutorFactory.create() for all executor types
  - Test BacktestExecutorFactory.create() raises ValueError on invalid type
  - Test BacktestExecutorFactory.register_executor() custom registration
  - Test _pre_execute and _post_execute hooks called
  - Test execution_count increments correctly

---

## Notes
Template Method pattern with extensible executors. ProcessPool critical for ML library threading issues (torch, tensorflow). Factory pattern enables runtime executor selection.
