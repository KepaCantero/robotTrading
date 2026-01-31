# error_handling.py

## Purpose
Robust error handling with automatic retries for transient failures, especially mutex/locking issues in machine learning libraries, with subprocess fallback and timeout protection.

---

## Type Definitions / Data Classes

### MutexError(Exception)
```python
class MutexError(Exception):
    """
    Error raised when a mutex/locking issue is detected.
    This typically occurs with PyTorch/torchvision, TensorFlow,
    OpenBLAS/MKL threading conflicts.
    """
    pass
```

**Validation Rules:**
- Raised when threading/locking issues detected
- Triggers automatic retry with exponential backoff

### TrainingError(Exception)
```python
class TrainingError(Exception):
    """
    Error raised when training fails.
    Wrapper for insufficient data, convergence issues,
    resource exhaustion.
    """
    pass
```

**Validation Rules:**
- Wrapper for various training failures
- Does NOT trigger automatic retry

### SubprocessTimeoutError(TrainingError)
```python
class SubprocessTimeoutError(TrainingError):
    """Error raised when subprocess training times out."""
    pass
```

**Validation Rules:**
- Raised when subprocess exceeds timeout
- Does NOT trigger automatic retry

---

## Function Signatures (Contracts)

### `is_mutex_error(exception: Exception) -> bool`
**Pre:** exception is Exception instance
**Post:** Returns True if mutex-related (checks for keywords: mutex, lock, thread, omp, mkl, openblas, blas, torch)
**Raises:** No
**Retry:** No
**Side Effects:** None (detection only)

### `train_with_retry(strategy: Any, engine_type: str, use_subprocess: bool = False, timeout: int = 300) -> bool`
**Pre:** strategy has learning_engine attribute
**Post:** Returns True if training succeeded, False otherwise
**Raises:** MutexError if mutex errors persist after 3 retries, TrainingError for other failures
**Retry:** ✅ Yes - 3 attempts with exponential backoff (4-10s) for MutexError only
**Side Effects:** Calls strategy.learning_engine.train(), potentially spawns subprocess

### `_train_in_subprocess(strategy: Any, engine_type: str, timeout: int = 300) -> bool`
**Pre:** strategy pickleable
**Post:** Returns True if training succeeded, False otherwise
**Raises:** SubprocessTimeoutError if timeout exceeded
**Retry:** No
**Side Effects:** Spawns Process with 'spawn' context, joins with timeout, terminates if alive

### `safe_execute(func: Callable[..., Any], *args: Any, default_return: Any = None, log_errors: bool = True, **kwargs: Any) -> Any`
**Pre:** func is callable
**Post:** Returns func result or default_return on exception
**Raises:** No (catches and logs all exceptions)
**Retry:** ❌ No
**Side Effects:** Calls func, logs errors if log_errors=True

### `log_and_suppress(exception_types: tuple[type[Exception], ...] = (Exception,), message: str = "Error suppressed", default_return: Any = None) -> Callable[..., Any]`
**Pre:** exception_types is tuple of Exception classes
**Post:** Returns decorator function
**Raises:** No
**Retry:** No
**Side Effects:** Decorator logs and suppresses exceptions

---

## Acceptance Criteria
- [ ] AC-ERR-001: is_mutex_error() detects mutex keywords in error messages
- [ ] AC-ERR-002: is_mutex_error() detects 'torch' in error type
- [ ] AC-ERR-003: train_with_retry() retries 3 times for MutexError
- [ ] AC-ERR-004: train_with_retry() uses exponential backoff (4-10s)
- [ ] AC-ERR-005: train_with_retry() raises MutexError after retries exhausted
- [ ] AC-ERR-006: _train_in_subprocess() uses 'spawn' context
- [ ] AC-ERR-007: _train_in_subprocess() terminates process after timeout
- [ ] AC-ERR-008: _train_in_subprocess() kills process if terminate hangs
- [ ] AC-ERR-009: safe_execute() returns default_return on exception
- [ ] AC-ERR-010: safe_execute() logs errors when log_errors=True
- [ ] AC-ERR-011: log_and_suppress decorator suppresses specified exceptions

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules with 23 P0)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ERR-001 | BASE_RULES.md (CC-006) | Explicit error handling | ✅ OK - Specific exception types |
| ERR-002 | BASE_RULES.md (LOG-004) | Error logging with stack traces | ✅ OK - logger.error with exc_info=True |
| ERR-003 | BASE_RULES.md (ASYNC-005) | Timeouts on external calls | ✅ OK - 300s timeout on subprocess |
| ERR-004 | BASE_RULES.md (TYP-001) | Type hints coverage | ✅ OK - Full type hints |
| ERR-005 | BASE_RULES.md (ARCH-004) | Small functions | ✅ OK - Methods focused |
| ERR-006 | BASE_RULES.md (PERF-006) | Retry with exponential backoff | ✅ OK - tenacity retry with wait_exponential |
| ERR-007 | BASE_RULES.md (SEC-007) | Input validation | ⚠️ GAP - is_mutex_error doesn't validate exception is Exception |
| ERR-008 | BASE_RULES.md (LOG-005) | No sensitive data in logs | ✅ OK - No sensitive data logged |

**GAP Analysis:**
- **ERR-007:** is_mutex_error() checks `isinstance(exception, Exception)` but should handle edge cases where exception might be None or other types. Current implementation is safe but could be more defensive.

---

## Dependencies
- **External:** tenacity (retry decorators), multiprocessing
- **Internal:** None (standalone error handling utilities)

---

## Required Tests
- **tests/backtesting/core/test_error_handling.py:**
  - Test is_mutex_error() detects mutex keyword in message
  - Test is_mutex_error() detects 'torch' in error type
  - Test is_mutex_error() returns False for non-mutex errors
  - Test train_with_retry() succeeds on first attempt
  - Test train_with_retry() retries 3 times for MutexError
  - Test train_with_retry() uses exponential backoff
  - Test train_with_retry() raises MutexError after 3 failures
  - Test train_with_retry() doesn't retry non-mutex errors
  - Test _train_in_subprocess() succeeds with valid strategy
  - Test _train_in_subprocess() times out and terminates
  - Test _train_in_subprocess() kills if terminate hangs
  - Test safe_execute() returns result on success
  - Test safe_execute() returns default_return on exception
  - Test safe_execute() logs errors when log_errors=True
  - Test log_and_suppress decorator suppresses exceptions
  - Test log_and_suppress decorator logs message

---

## Notes
Critical for ML library threading issues (PyTorch, TensorFlow). Tenacity retry with exponential backoff handles transient failures. Subprocess fallback provides complete isolation. Timeout protection prevents hangs.
