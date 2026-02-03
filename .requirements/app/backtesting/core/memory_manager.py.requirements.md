# memory_manager.py

## Purpose
Aggressive memory management for backtesting operations with automatic cleanup, memory pressure monitoring, weak references, and thread-safe operations to prevent memory leaks during long-running operations.

---

## Type Definitions / Data Classes

### MemoryPressureError (Exception)
```python
class MemoryPressureError(Exception):
    """Raised when memory pressure exceeds threshold."""
```
**Validation Rules:**
- Raised when process memory exceeds memory_threshold_mb
- Indicates emergency cleanup was triggered

### AggressiveMemoryManager
```python
class AggressiveMemoryManager:
    max_results: int                           # Max lightweight result dicts
    max_backtest_objects: int                  # Max heavy BacktestResult objects
    memory_threshold_mb: int                   # Memory threshold in MB
    auto_monitor: bool                         # Enable automatic monitoring
    _results: deque[Dict[str, Any]]            # Bounded deque for results
    _backtest_refs: Dict[str, weakref.ref]     # Weak references to prevent cycles
    _backtest_objects: deque[Tuple[str, BacktestResult]]  # Heavy objects
    _lock: threading.RLock                     # Thread-safe lock
    _cleanup_count: int                        # Standard cleanup counter
    _emergency_cleanup_count: int              # Emergency cleanup counter
```
**Validation Rules:**
- max_results defaults to 500
- max_backtest_objects defaults to 100
- memory_threshold_mb defaults to 4096 (4GB)
- auto_monitor defaults to True
- Deque with maxlen provides automatic bounding
- Weak references prevent circular reference leaks
- All operations thread-safe via RLock

---

## Function Signatures (Contracts)

### `AggressiveMemoryManager.__init__(max_results=500, max_backtest_objects=100, memory_threshold_mb=4096, auto_monitor=True) -> None`
**Pre:** max_results > 0, max_backtest_objects > 0, memory_threshold_mb > 0
**Post:** Manager initialized with bounded deques, empty weak refs dict, and RLock
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Creates deque, dict, lock, initializes counters

### `AggressiveMemoryManager.add_result(result: Dict[str, Any]) -> None`
**Pre:** result is valid dict
**Post:** Result added to deque, cleanup triggered if needed, memory checked if auto_monitor enabled
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Thread-safe append, potential cleanup, potential memory check

### `AggressiveMemoryManager.add_backtest_object(key: str, obj: BacktestResult) -> None`
**Pre:** key is unique identifier, obj is BacktestResult
**Post:** Object added to deque, weak reference created, cleanup triggered, memory checked if auto_monitor
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Thread-safe append, creates weakref with cleanup_callback, potential cleanup, potential memory check

### `AggressiveMemoryManager.get_results() -> list[Dict[str, Any]]`
**Pre:** None
**Post:** Returns list of all result dicts (copy, not reference)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Thread-safe read

### `AggressiveMemoryManager.get_backtest_objects() -> list[Tuple[str, BacktestResult]]`
**Pre:** None
**Post:** Returns list of all (key, BacktestResult) tuples (copy)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Thread-safe read

### `AggressiveMemoryManager.clear_all() -> None`
**Pre:** None
**Post:** All results cleared, all objects deep cleaned, weak refs cleared, single GC pass
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Thread-safe clear, deep cleanup of objects, gc.collect()

### `AggressiveMemoryManager._cleanup_if_needed() -> None`
**Pre:** None
**Post:** Results reduced to 50% capacity if approaching 80%, single GC pass
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Removes oldest via popleft(), clears dict contents, increments cleanup_count, gc.collect()

### `AggressiveMemoryManager._cleanup_backtest_objects_if_needed() -> None`
**Pre:** None
**Post:** Backtest objects reduced to 50 max, deep cleanup of removed objects, weak refs cleaned up, GC if > 30 objects
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Popleft oldest, deep cleanup, remove weak refs, gc.collect() if needed

### `AggressiveMemoryManager._deep_cleanup_object(obj: Any) -> None`
**Pre:** obj is any object
**Post:** Object attributes cleared to break circular references
**Raises:** ❌ No (catches and logs exceptions)
**Retry:** ❌ No
**Side Effects:** Clears dict/list/set attributes, sets other attributes to None

### `AggressiveMemoryManager._perform_cleanup() -> None`
**Pre:** None
**Post:** Results reduced to 50% capacity, single GC pass
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Popleft results, clear dict contents, gc.collect()

### `AggressiveMemoryManager._emergency_cleanup() -> None`
**Pre:** None
**Post:** Only 10 results and 5 backtest objects remain, weak refs cleared, single GC pass, emergency_count incremented
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Aggressive cleanup, logs critical message, gc.collect()

### `AggressiveMemoryManager.check_memory_pressure() -> bool`
**Pre:** None
**Post:** Returns True if memory > threshold (triggers emergency cleanup), False otherwise
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** May trigger emergency cleanup, logs memory usage

### `AggressiveMemoryManager._auto_check_memory() -> bool`
**Pre:** None
**Post:** Returns True if memory > threshold (triggers emergency), False otherwise, logs memory at intervals
**Raises:** ❌ No (catches psutil errors)
**Retry:** ❌ No
**Side Effects:** Gets process memory, may trigger emergency cleanup, logs debug info

### `AggressiveMemoryManager.get_memory_usage_mb() -> float`
**Pre:** None
**Post:** Returns current memory usage in MB, or 0.0 on error
**Raises:** ❌ No (catches exceptions)
**Retry:** ❌ No
**Side Effects:** Reads process memory info

### `AggressiveMemoryManager.get_stats() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with counts, memory usage, thresholds, cleanup counts
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (reads state)

### `AggressiveMemoryManager.__repr__() -> str`
**Pre:** None
**Post:** Returns string representation with counts and memory usage
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (string formatting)

---

## Acceptance Criteria
- [ ] AggressiveMemoryManager initializes with correct defaults
- [ ] add_result adds result and triggers cleanup at 80% capacity
- [ ] add_result triggers memory check if auto_monitor enabled
- [ ] add_backtest_object creates weak reference
- [ ] add_backtest_object triggers cleanup at 80% capacity
- [ ] add_backtest_object weak ref callback cleans up _backtest_refs
- [ ] get_results returns copy of results
- [ ] get_backtest_objects returns copy of objects
- [ ] clear_all performs deep cleanup of all objects
- [ ] clear_all calls gc.collect() once (not multiple times)
- [ ] _cleanup_if_needed reduces to 50% capacity
- [ ] _cleanup_backtest_objects_if_needed keeps max 50 objects
- [ ] _cleanup_backtest_objects_if_needed calls GC if > 30 objects
- [ ] _deep_cleanup_object clears dict/list/set attributes
- [ ] _deep_cleanup_object sets other attributes to None
- [ ] _emergency_cleanup keeps only 10 results and 5 objects
- [ ] _emergency_cleanup logs critical message
- [ ] check_memory_pressure triggers emergency cleanup over threshold
- [ ] check_memory_pressure returns True when over threshold
- [ ] _auto_check_memory logs memory at intervals (every 100 results, every 20 objects)
- [ ] get_memory_usage_mb returns process memory in MB
- [ ] get_memory_usage_mb returns 0.0 on error
- [ ] get_stats returns all statistics including weak_refs_count and auto_monitor_enabled
- [ ] __repr__ includes weak_refs count
- [ ] All operations are thread-safe via RLock

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
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Memory management only |
| ASYNC-003 | BASE_RULES.md | Thread-safe operations | ✅ OK - Uses RLock for all state changes |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ FIXED - All methods have explicit return type annotations including __init__ |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses list[BacktestResultDict], deque[tuple[str, BacktestResult]] syntax |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ FIXED - Uses BacktestResultDict TypedDict, removed Dict[str, Any] in favor of TypedDict |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ FIXED - Replaced emoji logging with structured logging using extra={} |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ FIXED - Added exc_info=True to all error logging (line 236, 354) |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Catches specific exceptions |
| PERF-002 | BASE_RULES.md | Generators for large data | ⚠️ NOT APPLIED - Uses bounded deques |
| PERF-003 | BASE_RULES.md | Sets for O(1) lookups | ⚠️ NOT APPLIED - No lookups needed |
| ARCH-006 | BASE_RULES.md | Value objects immutable | ⚠️ NOT APPLIED - Manager is mutable state |

---

## Dependencies
- **External:** gc, logging, threading, weakref, collections.deque, typing, psutil
- **Internal:** app.backtesting.models.BacktestResult

---

## Required Tests
- **tests/unit/backtesting/core/test_memory_manager.py:**
  - Test __init__ with default values
  - Test __init__ with custom values
  - Test add_result adds result to deque
  - Test add_result triggers cleanup at 80% capacity
  - Test add_result triggers memory check when auto_monitor=True
  - Test add_backtest_object adds object and weak ref
  - Test add_backtest_object weak ref callback cleans up _backtest_refs
  - Test add_backtest_object triggers cleanup
  - Test get_results returns copy of results
  - Test get_backtest_objects returns copy of objects
  - Test clear_all clears all containers
  - Test clear_all performs deep cleanup
  - Test clear_all calls gc.collect() once
  - Test _cleanup_if_needed reduces to 50% capacity
  - Test _cleanup_backtest_objects_if_needed keeps max 50 objects
  - Test _cleanup_backtest_objects_if_needed calls GC if > 30 objects
  - Test _deep_cleanup_object clears dict/list/set attributes
  - Test _deep_cleanup_object sets other attributes to None
  - Test _deep_cleanup_object handles exceptions gracefully
  - Test _emergency_cleanup keeps only 10 results and 5 objects
  - Test _emergency_cleanup increments emergency_cleanup_count
  - Test _emergency_cleanup logs critical message
  - Test check_memory_pressure returns True when over threshold
  - Test check_memory_pressure triggers emergency cleanup
  - Test _auto_check_memory logs memory at intervals
  - Test _auto_check_memory returns False when under threshold
  - Test get_memory_usage_mb returns process memory
  - Test get_memory_usage_mb returns 0.0 on psutil error
  - Test get_stats returns all statistics
  - Test get_stats includes weak_refs_count
  - Test get_stats includes auto_monitor_enabled
  - Test __repr__ includes weak_refs count
  - Test all operations are thread-safe with concurrent access
  - Test weakref callback removes from _backtest_refs when object deleted

---

## Notes
- **Phase 4 FIXES:** Proper deep cleanup, single GC pass (was 3), automatic monitoring actually works, weak references prevent circular refs
- Weak references critical for preventing memory leaks with BacktestResult objects
- Emergency cleanup is aggressive (10 results, 5 objects) to recover from memory pressure
- Memory monitoring uses psutil for accurate process memory measurement
- Thread safety via RLock for concurrent execution scenarios
- Deque with maxlen provides automatic bounding at hard limits
- Cleanup triggered at 80% to stay ahead of hard limits
- Single GC pass instead of multiple (was excessive in old code)
- Emoji in logs for visual emphasis (🚨, ⚠️, 🧹) - could be replaced with structured levels
