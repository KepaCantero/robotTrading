# error_handling.py

## Purpose
Robust error handling with automatic retries for transient failures, especially mutex/locking issues in machine learning libraries, with subprocess fallback and comprehensive exception detection.

---

## Type Definitions / Data Classes

### Custom Exceptions
```python
class MutexError(Exception):
    """Mutex/locking issue detection (PyTorch, TensorFlow, OpenBLAS, MKL)."""

class TrainingError(Exception):
    """Training failure wrapper (insufficient data, convergence, resource exhaustion)."""

class SubprocessTimeoutError(TrainingError):
    """Subprocess training timeout."""
```
**Validation Rules:**
- MutexError indicates retry-worthy transient threading issues
- TrainingError indicates non-transient training failures
- SubprocessTimeoutError indicates subprocess exceeded timeout

---

## Function Signatures (Contracts)

### `is_mutex_error(exception: Exception) -> bool`
**Pre:** exception is Exception instance
**Post:** Returns True if exception message/type contains mutex-related keywords
**Raises:** ❌ No (returns False for non-exceptions)
**Retry:** ❌ No
**Side Effects:** None (pure detection)

**Mutex Keywords:** 'mutex', 'lock', 'blocking', 'thread', 'concurrent', 'omp', 'mkl', 'openblas', 'blas', 'torch'

### `train_with_retry(strategy, engine_type: str, use_subprocess: bool = False, timeout: int = 300) -> bool`
**Pre:** strategy has learning_engine attribute, engine_type is valid engine type
**Post:** Returns True if training succeeded, False if failed
**Raises:** MutexError if mutex errors persist after 3 retries, TrainingError if non-mutex failure
**Retry:** ✅ Yes - 3 attempts with exponential backoff (4-10 seconds) for MutexError only
**Side Effects:** Calls strategy.learning_engine.train() or spawns subprocess

**Tenacity Configuration:**
- stop: stop_after_attempt(3)
- wait: wait_exponential(multiplier=1, min=4, max=10)
- retry: retry_if_exception_type(MutexError)
- before_sleep: before_sleep_log(logger, WARNING)
- reraise: True

### `_train_in_subprocess(strategy, engine_type: str, timeout: int = 300) -> bool`
**Pre:** strategy is pickleable, has learning_engine attribute
**Post:** Returns True if training succeeded, False otherwise
**Raises:** SubprocessTimeoutError if timeout exceeded
**Retry:** ❌ No (wrapper is retried)
**Side Effects:** Spawns subprocess, terminates on timeout, joins process

**Process Configuration:**
- Context: multiprocessing.get_context('spawn')
- Queue: ctx.Queue() for result communication
- Timeout: Default 300 seconds (5 minutes)
- Termination: terminate() + 5s join + kill() if still alive

### `safe_execute(func: Callable, *args, default_return=None, log_errors=True, **kwargs) -> Any`
**Pre:** func is callable
**Post:** Returns func(*args, **kwargs) or default_return on exception
**Raises:** ❌ No (catches and logs all)
**Retry:** ❌ No
**Side Effects:** Logs errors if log_errors=True

**Caught Exceptions:** IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError (SQLAlchemy)

### `log_and_suppress(exception_types, message="Error suppressed", default_return=None) -> Callable`
**Pre:** exception_types is tuple of exception classes
**Post:** Returns decorator function
**Raises:** ❌ No (factory function)
**Retry:** ❌ No
**Side Effects:** None (returns decorator)

**Returned Decorator:**
- Catches specified exception_types
- Logs warning with message
- Returns default_return

---

## Acceptance Criteria
- [ ] is_mutex_error detects mutex-related keywords in exception messages
- [ ] is_mutex_error detects mutex-related keywords in exception types
- [ ] is_mutex_error returns False for non-exceptions
- [ ] train_with_retry returns True on successful training
- [ ] train_with_retry retries 3 times for MutexError
- [ ] train_with_retry uses exponential backoff (4-10s)
- [ ] train_with_retry logs before each retry
- [ ] train_with_retry raises MutexError after 3 failed retries
- [ ] train_with_retry raises TrainingError for non-mutex errors
- [ ] train_with_retry uses subprocess when use_subprocess=True
- [ ] _train_in_subprocess spawns process with 'spawn' context
- [ ] _train_in_subprocess terminates process on timeout
- [ ] _train_in_subprocess kills process if terminate fails
- [ ] _train_in_subprocess raises SubprocessTimeoutError on timeout
- [ ] _train_in_subprocess returns True on success
- [ ] _train_in_subprocess returns False on training failure
- [ ] _train_in_subprocess reimports strategy module in subprocess
- [ ] safe_execute returns func result on success
- [ ] safe_execute returns default_return on exception
- [ ] safe_execute logs errors if log_errors=True
- [ ] safe_execute catches SQLAlchemy exceptions
- [ ] log_and_suppress returns callable decorator
- [ ] log_and_suppress decorator catches specified exceptions
- [ ] log_and_suppress decorator logs warning message
- [ ] log_and_suppress decorator returns default_return on exception

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
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Error handling only |
| ASYNC-005 | BASE_RULES.md | Timeouts for external calls | ✅ OK - 300s timeout for subprocess |
| ASYNC-006 | BASE_RULES.md | Handle asyncio.TimeoutError | ⚠️ NOT APPLIED - Uses multiprocessing, not asyncio |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ FIXED - All functions have explicit return type annotations |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses tuple[type[Exception], ...], Callable syntax, X | None syntax |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ FIXED - Uses LearningEngineProtocol and StrategyProtocol instead of Any |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ FIXED - Replaced emoji logging with structured logging using extra={} |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ FIXED - Added exc_info=True to all error logging (line 247, 329, 348, 376, 385, 400, 449) |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ✅ OK - No secrets logged |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exception types, custom exceptions (BacktestResultError added) |
| ARCH-004 | BASE_RULES.md | Small functions | ✅ OK - Most functions < 20 lines |

---

## Dependencies
- **External:** logging, multiprocessing, typing, tenacity
- **External (Optional):** sqlalchemy.exc (fallback to Exception if not available)

---

## Required Tests
- **tests/unit/backtesting/core/test_error_handling.py:**
  - Test is_mutex_error returns True for mutex keyword in message
  - Test is_mutex_error returns True for mutex keyword in type
  - Test is_mutex_error returns False for non-mutex errors
  - Test is_mutex_error returns False for non-exceptions
  - Test train_with_retry returns True on success
  - Test train_with_retry retries 3 times for MutexError
  - Test train_with_retry uses exponential backoff
  - Test train_with_retry logs before retry
  - Test train_with_retry raises MutexError after 3 failures
  - Test train_with_retry raises TrainingError for non-mutex errors
  - Test train_with_retry uses subprocess when use_subprocess=True
  - Test train_with_retry uses in-process when use_subprocess=False
  - Test _train_in_subprocess spawns process with spawn context
  - Test _train_in_subprocess returns True on success
  - Test _train_in_subprocess returns False on failure
  - Test _train_in_subprocess terminates on timeout
  - Test _train_in_subprocess kills if terminate fails
  - Test _train_in_subprocess raises SubprocessTimeoutError on timeout
  - Test _train_in_subprocess reimports module in subprocess
  - Test safe_execute returns result on success
  - Test safe_execute returns default_return on exception
  - Test safe_execute logs errors when log_errors=True
  - Test safe_execute doesn't log when log_errors=False
  - Test safe_execute catches SQLAlchemy exceptions
  - Test log_and_suppress returns decorator
  - Test log_and_suppress decorator catches specified exceptions
  - Test log_and_suppress decorator logs warning
  - Test log_and_suppress decorator returns default_return
  - Test log_and_suppress decorator doesn't catch other exceptions

---

## Notes
- Tenacity library provides declarative retry configuration with @retry decorator
- Subprocess fallback avoids threading issues with ML libraries (PyTorch, TensorFlow)
- 'spawn' context creates fresh Python process (no forked threading state)
- Timeout handling: terminate() → wait 5s → kill() if still alive
- SQLAlchemy exception types imported with try/except for graceful fallback
- train_with_retry designed for ML library mutex issues (OpenMP, MKL, OpenBLAS)
- Mutex detection keyword-based (covers common threading library error patterns)
- safe_execute generic wrapper for database operations
- log_and_suppress decorator factory for flexible exception suppression
- Emoji in logs (🔄, ✅, ❌) for visual emphasis - could be replaced with structured levels
