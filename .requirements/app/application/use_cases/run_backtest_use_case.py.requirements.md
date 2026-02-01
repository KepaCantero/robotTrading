# run_backtest_use_case.py

## Purpose
Application layer use case for executing backtests. Orchestrates the flow of data to and from entities, directing them to use their enterprise-wide business rules following Clean Architecture principles.

---

## Type Definitions / Data Classes

### BacktestStatus (Enum, imported from domain)
```python
class BacktestStatus(str, Enum):
    PENDING = "pending"  # Backtest is queued
    RUNNING = "running"  # Backtest is executing
    COMPLETED = "completed"  # Backtest finished successfully
    FAILED = "failed"  # Backtest failed with error
```

### BacktestConfigValue (imported from domain value_objects)
```python
@dataclass
class BacktestConfigValue:
    # Configuration parameters for backtest execution
    # Specific fields depend on domain model
```

### BacktestResultValue (imported from domain value_objects)
```python
@dataclass
class BacktestResultValue:
    # Results from backtest execution
    # Includes performance metrics, trades, equity curve
```

### Backtest (imported from domain entities)
```python
class Backtest:
    backtest_id: str  # REQUIRED - Unique identifier
    config: BacktestConfigValue  # REQUIRED - Configuration
    status: BacktestStatus  # REQUIRED - Current status
    result: Optional[BacktestResultValue]  # Result when completed

    def start() -> None:  # Mark as running
    def complete(result: BacktestResultValue) -> None:  # Mark completed
    def fail(error: str) -> None:  # Mark failed with error message
```

---

## Function Signatures (Contracts)

### `__init__(backtest_repository: BacktestRepository)`
**Pre:** `backtest_repository` must be non-null instance
**Post:** Use case initialized with repository dependency
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** Stores repository as private attribute

### `execute(config: BacktestConfigValue) -> Backtest`
**Pre:** `config` must be valid BacktestConfigValue
**Post:** Returns Backtest entity with results after execution
**Raises:** Exception if backtest execution fails (propagated)
**Retry:** No
**Side Effects:** Creates backtest, saves to repository, updates status through lifecycle

### `execute_batch(configs: List[BacktestConfigValue]) -> List[Backtest]`
**Pre:** `configs` non-empty list
**Post:** Returns list of Backtest entities (including failed ones)
**Raises:** No exceptions (catches and logs per-backtest errors)
**Retry:** No
**Side Effects:** Saves all backtests to repository, continues on individual failures

### `get_backtest(backtest_id: str) -> Optional[Backtest]`
**Pre:** `backtest_id` non-empty string
**Post:** Returns Backtest if found, None otherwise
**Raises:** No exceptions
**Retry:** No
**Side Effects:** No state changes

### `get_backtests_by_status(status: BacktestStatus) -> List[Backtest]`
**Pre:** `status` valid BacktestStatus enum value
**Post:** Returns list of backtests with specified status
**Raises:** No exceptions
**Retry:** No
**Side Effects:** No state changes

### `get_recent_backtests(limit: int = 10) -> List[Backtest]`
**Pre:** `limit` positive integer
**Post:** Returns list of recently completed backtests
**Raises:** No exceptions
**Retry:** No
**Side Effects:** No state changes

### `_generate_backtest_id() -> str`
**Pre:** None (no parameters)
**Post:** Returns unique backtest identifier
**Raises:** No exceptions
**Retry:** No
**Side Effects:** No state changes

### `_execute_backtest(config: BacktestConfigValue) -> BacktestResultValue`
**Pre:** `config` valid
**Post:** Returns BacktestResultValue with execution results
**Raises:** NotImplementedError (placeholder for infrastructure layer)
**Retry:** No
**Side Effects:** No state changes (delegates to infrastructure)

---

## Acceptance Criteria
- [ ] execute() creates Backtest with PENDING status
- [ ] execute() saves backtest to repository before starting
- [ ] execute() marks backtest as RUNNING before execution
- [ ] execute() marks backtest as COMPLETED on success
- [ ] execute() marks backtest as FAILED on exception
- [ ] execute() raises exception after marking as FAILED
- [ ] execute_batch() continues on individual backtest failures
- [ ] execute_batch() returns only successfully completed backtests
- [ ] execute_batch() logs errors for failed backtests
- [ ] get_backtest() returns None for non-existent ID
- [ ] get_backtests_by_status() returns empty list if no matches
- [ ] get_recent_backtests() respects limit parameter
- [ ] _generate_backtest_id() creates unique IDs
- [ ] Backtest lifecycle transitions: PENDING -> RUNNING -> COMPLETED/FAILED
- [ ] All backtest state changes are persisted to repository

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility - Orchestration only | ✅ OK |
| SOL-005 | BASE_RULES.md | Dependency Inversion - Depends on repository abstraction | ✅ OK |
| ARCH-001 | BASE_RULES.md | Layered architecture - Application layer use case | ✅ OK |
| DP-004 | BASE_RULES.md | Dependency injection - Repository injected | ✅ OK |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES.md | Modern syntax | ⚠️ PARTIAL - Uses `List` instead of `list` |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ GAP - Generic Exception catch in execute_batch |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ OK - Uses logging module |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ OK - Logs exceptions |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** `logging`, `datetime`, `typing`
- **Internal:**
  - `app.domain.entities.backtest` (Backtest, BacktestStatus)
  - `app.domain.repositories.backtest_repository` (BacktestRepository)
  - `app.domain.value_objects.backtest_config` (BacktestConfigValue)
  - `app.domain.value_objects.backtest_result` (BacktestResultValue)

---

## Required Tests
- **test_run_backtest_use_case.py:**
  - Test execute() creates backtest with PENDING status
  - Test execute() transitions to RUNNING status
  - Test execute() transitions to COMPLETED on success
  - Test execute() transitions to FAILED on exception
  - Test execute() saves backtest at each lifecycle stage
  - Test execute() propagates exception after FAILED
  - Test execute_batch() executes multiple configs
  - Test execute_batch() continues on individual failures
  - Test execute_batch() returns only successful backtests
  - Test execute_batch() logs errors for failed backtests
  - Test get_backtest() returns backtest for valid ID
  - Test get_backtest() returns None for invalid ID
  - Test get_backtests_by_status() filters correctly
  - Test get_recent_backtests() respects limit
  - Test _generate_backtest_id() generates unique IDs
  - Test _execute_backtest() raises NotImplementedError

---

## Notes
**Architecture Pattern:** This is a Clean Architecture use case that orchestrates domain entities and infrastructure services. It follows the "Use Case" pattern from Robert C. Martin's Clean Architecture.

**Placeholder Implementation:** The `_execute_backtest()` method is a placeholder that raises NotImplementedError. The actual execution should be implemented in the infrastructure layer and injected as a dependency.

**Lifecycle Management:** The use case manages the complete backtest lifecycle: PENDING -> RUNNING -> COMPLETED/FAILED, with repository persistence at each stage.

**Error Handling Strategy:** Individual backtest failures in batch mode don't stop the batch execution. Each failure is logged and the batch continues with remaining configs.
