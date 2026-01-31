# run_backtest_use_case.py

## Purpose
Run Backtest Use Case - Application layer orchestrator for executing backtests with state management and persistence.

---

## Type Definitions / Data Classes

No custom data classes defined in this file (uses domain entities).

**Domain Dependencies:**
- `Backtest` entity with `BacktestStatus` enum
- `BacktestConfigValue` value object
- `BacktestResultValue` value object
- `BacktestRepository` interface

---

## Function Signatures (Contracts)

### `RunBacktestUseCase.__init__(backtest_repository: BacktestRepository) -> None`
**Pre:** backtest_repository is valid BacktestRepository
**Post:** Use case initialized with repository
**Raises:** None
**Retry:** No
**Side Effects:** Stores repository reference

### `RunBacktestUseCase.execute(config: BacktestConfigValue) -> Backtest`
**Pre:** config is valid BacktestConfigValue
**Post:** Returns Backtest entity with results
**Raises:** Exception (backtest marked as failed, re-raised)
**Retry:** No
**Side Effects:** Creates, starts, executes, completes/fails backtest; saves to repository

**Process Flow:**
1. Create Backtest entity with PENDING status
2. Save initial state to repository
3. Mark backtest as STARTED, save
4. Execute backtest (_execute_backtest)
5. Mark backtest as COMPLETED, save
6. On exception: mark as FAILED, save, re-raise

### `RunBacktestUseCase.execute_batch(configs: List[BacktestConfigValue]) -> List[Backtest]`
**Pre:** configs is non-empty list
**Post:** Returns list of successfully executed backtests
**Raises:** None (errors logged, continues with next config)
**Retry:** No
**Side Effects:** Executes each config via execute(), logs failures

**Error Handling:** Individual backtest failures don't stop batch processing

### `RunBacktestUseCase.get_backtest(backtest_id: str) -> Optional[Backtest]`
**Pre:** backtest_id is non-empty string
**Post:** Returns Backtest if found, None otherwise
**Raises:** None
**Retry:** No
**Side Effects:** None (query via repository)

### `RunBacktestUseCase.get_backtests_by_status(status: BacktestStatus) -> List[Backtest]`
**Pre:** status is valid BacktestStatus
**Post:** Returns list of backtests with matching status
**Raises:** None
**Retry:** No
**Side Effects:** None (query via repository)

### `RunBacktestUseCase.get_recent_backtests(limit: int = 10) -> List[Backtest]`
**Pre:** limit > 0
**Post:** Returns list of recently completed backtests (max `limit`)
**Raises:** None
**Retry:** No
**Side Effects:** None (query via repository)

### `RunBacktestUseCase._generate_backtest_id() -> str`
**Pre:** None
**Post:** Returns unique backtest ID
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Format:** `bt_YYYYMMDD_HHMMSS` (UTC timestamp)

### `RunBacktestUseCase._execute_backtest(config: BacktestConfigValue) -> BacktestResultValue`
**Pre:** config is valid BacktestConfigValue
**Post:** Returns BacktestResultValue with results
**Raises:** `NotImplementedError` (placeholder)
**Retry:** No
**Side Effects:** None (delegated to infrastructure layer)

**Note:** This is a placeholder - actual implementation should be in infrastructure layer

---

## Acceptance Criteria
- [ ] **AC-001:** execute() creates Backtest entity with PENDING status
- [ ] **AC-002:** execute() transitions PENDING → STARTED → COMPLETED
- [ ] **AC-003:** execute() saves state after each transition
- [ ] **AC-004:** execute() marks backtest as FAILED on exception
- [ ] **AC-005:** execute() re-raises exception after marking failed
- [ ] **AC-006:** execute_batch() continues on individual failures
- [ ] **AC-007:** get_backtest() returns None if not found
- [ ] **AC-008:** get_backtests_by_status() queries by status
- [ ] **AC-009:** get_recent_backtests() limits results
- [ ] **AC-010:** _generate_backtest_id() creates unique IDs
- [ ] **AC-011:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Run Backtest Use Case):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Use case pattern | Clean Architecture | Application orchestrator | ✅ OK - RunBacktestUseCase |
| State machine | Pardo (2008) | PENDING → RUNNING → COMPLETED/FAILED | ✅ OK - Backtest entity |
| Repository pattern | DDD (Evans) | Persistence abstraction | ✅ OK - BacktestRepository |
| Error handling | BASE_RULES.md (LOG-001) | Log errors, mark failed | ✅ OK - try/except |
| Batch execution | Performance | Continue on individual failures | ✅ OK - execute_batch() |
| ID generation | Clean code | Unique, timestamp-based | ✅ OK - _generate_backtest_id() |
| Infrastructure delegation | Clean Architecture | Execution in infrastructure | ✅ OK - _execute_backtest() placeholder |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Async consideration | BASE_RULES.md (ASYNC-001) | Sync methods (repo may be async) | ⚠️ Review - execute() is sync |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Pardo (2008) for backtesting standards.

---

## Dependencies
- **External:** `logging` (std), `datetime` (std), `typing` (std)
- **Internal:**
  - `app.domain.entities.backtest.Backtest`
  - `app.domain.entities.backtest.BacktestStatus`
  - `app.domain.repositories.backtest_repository.BacktestRepository`
  - `app.domain.value_objects.backtest_config.BacktestConfigValue`
  - `app.domain.value_objects.backtest_result.BacktestResultValue`

---

## Required Tests
- **test_run_backtest_use_case.py:**
  - `test_init()` - Initializes with repository
  - `test_execute_creates_backtest()` - Backtest created
  - `test_execute_transitions_to_started()` - Status changes
  - `test_execute_completes_successfully()` - Returns completed backtest
  - `test_execute_marks_failed_on_exception()` - Status = FAILED on error
  - `test_execute_saves_after_each_transition()` - 3 saves (pending, started, completed)
  - `test_execute_re_raises_exception()` - Exception propagated
  - `test_execute_batch_all_success()` - Returns all backtests
  - `test_execute_batch_partial_failure()` - Continues on error
  - `test_get_backtest_found()` - Returns backtest
  - `test_get_backtest_not_found()` - Returns None
  - `test_get_backtests_by_status()` - Queries by status
  - `test_get_recent_backtests_default_limit()` - Returns 10
  - `test_get_recent_backtests_custom_limit()` - Returns N
  - `test_generate_backtest_id_unique()` - Different IDs over time
  - `test_generate_backtest_id_format()` - bt_YYYYMMDD_HHMMSS

---

## Notes
- **Critical:** RunBacktestUseCase is a USE CASE (Clean Architecture application layer)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Application Service pattern
- **Use Case Pattern:** Orchestrates domain entities and repositories without business logic
- **State Machine:** Backtest transitions through PENDING → STARTED → COMPLETED/FAILED
- **Repository Pattern:** Abstracts persistence via BacktestRepository interface
- **Error Handling:** Exceptions mark backtest as FAILED before re-raising
- **Batch Execution:** execute_batch() continues processing even if individual backtests fail
- **ID Generation:** Timestamp-based IDs (bt_YYYYMMDD_HHMMSS) using UTC
- **Infrastructure Delegation:** _execute_backtest() is placeholder - should be implemented in infrastructure layer
- **Query Methods:** get_backtest(), get_backtests_by_status(), get_recent_backtests() for retrieval
- **Logging:** Info level for success, error level for failures
- **Clean Architecture Separation:** Use case doesn't know HOW backtest runs, only orchestrates flow

---

**File Reference:** `app/application/use_cases/run_backtest_use_case.py`
**Last Audited:** 2026-02-01
