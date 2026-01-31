# memory_manager.py

## Purpose
Aggressive memory management for backtesting operations to prevent memory leaks and excessive usage during long-running parameter sweeps with automatic cleanup, weak references, and psutil monitoring.

---

## Type Definitions / Data Classes

### MemoryPressureError(Exception)
```python
class MemoryPressureError(Exception):
    """Raised when memory pressure exceeds threshold."""
    pass
```

**Validation Rules:**
- Raised when memory usage exceeds memory_threshold_mb
- Triggers emergency cleanup

### AggressiveMemoryManager
```python
class AggressiveMemoryManager:
    max_results: int                        # REQUIRED - Max lightweight results (default: 500)
    max_backtest_objects: int               # REQUIRED - Max BacktestResult objects (default: 100)
    memory_threshold_mb: int                # REQUIRED - Cleanup threshold MB (default: 4096)
    auto_monitor: bool                      # REQUIRED - Enable auto monitoring (default: True)
    _results: deque[Dict[str, Any]]         # PRIVATE - Lightweight results with maxlen
    _backtest_objects: deque[Tuple[str, BacktestResult]]  # PRIVATE - Heavy objects
    _backtest_refs: Dict[str, weakref.ref]  # PRIVATE - Weak references to prevent cycles
    _lock: threading.RLock                  # PRIVATE - Thread-safe cleanup
    _cleanup_count: int                     # PRIVATE - Statistics counter
    _emergency_cleanup_count: int           # PRIVATE - Emergency counter
```

**Validation Rules:**
- deque with maxlen enforces automatic bounded size
- weak references prevent circular reference chains
- Thread-safe operations with RLock
- auto_monitor triggers _auto_check_memory() on each add

---

## Function Signatures (Contracts)

### `AggressiveMemoryManager.__init__(max_results: int = 500, max_backtest_objects: int = 100, memory_threshold_mb: int = 4096, auto_monitor: bool = True) -> None`
**Pre:** max_results > 0, max_backtest_objects > 0, memory_threshold_mb > 0
**Post:** Manager initialized with bounded deques and weak ref tracking
**Raises:** No
**Retry:** No
**Side Effects:** Creates deque(maxlen), RLock, initializes counters

### `AggressiveMemoryManager.add_result(result: Dict[str, Any]) -> None`
**Pre:** result is dict
**Post:** result added, cleanup triggered if >80% capacity, memory checked if auto_monitor
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe append, cleanup, potential memory check

### `AggressiveMemoryManager.add_backtest_object(key: str, obj: BacktestResult) -> None`
**Pre:** key is unique string, obj is BacktestResult
**Post:** Object added with weak reference, cleanup triggered, memory checked if auto_monitor
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe append, weakref creation, cleanup

### `AggressiveMemoryManager.get_results() -> list[Dict[str, Any]]`
**Pre:** None
**Post:** Returns list of all results (copy)
**Raises:** No
**Retry:** No
**Side Effects:** None (thread-safe read)

### `AggressiveMemoryManager.get_backtest_objects() -> list[Tuple[str, BacktestResult]]`
**Pre:** None
**Post:** Returns list of all (key, BacktestResult) tuples
**Raises:** No
**Retry:** No
**Side Effects:** None (thread-safe read)

### `AggressiveMemoryManager.clear_all() -> None`
**Pre:** None
**Post:** All results and objects cleared with deep cleanup, single GC pass
**Raises:** No
**Retry:** No
**Side Effects:** Clears containers, deep cleanup, gc.collect()

### `AggressiveMemoryManager._cleanup_if_needed() -> None`
**Pre:** None (private method)
**Post:** If >80% capacity, reduces to 50%
**Raises:** No
**Retry:** No
**Side Effects:** Removes oldest results, gc.collect()

### `AggressiveMemoryManager._cleanup_backtest_objects_if_needed() -> None`
**Pre:** None (private method)
**Post:** Keeps only 50 most recent, GC if >30
**Raises:** No
**Retry:** No
**Side Effects:** Deep cleanup of removed objects, gc.collect()

### `AggressiveMemoryManager._deep_cleanup_object(obj: Any) -> None`
**Pre:** obj has __dict__ attribute
**Post:** Clears dict/list/set attributes, sets others to None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** Modifies object __dict__ to break references

### `AggressiveMemoryManager._perform_cleanup() -> None`
**Pre:** None (private method)
**Post:** Reduces results to 50% capacity
**Raises:** No
**Retry:** No
**Side Effects:** Popleft() oldest, gc.collect()

### `AggressiveMemoryManager._emergency_cleanup() -> None`
**Pre:** None (private method, called when memory > threshold)
**Post:** Keeps only 10 results, 5 backtest objects, clears weak refs
**Raises:** No
**Retry:** No
**Side Effects:** Aggressive cleanup, gc.collect(), logs critical

### `AggressiveMemoryManager.check_memory_pressure() -> bool`
**Pre:** None
**Post:** Returns True if memory exceeds threshold
**Raises:** No
**Retry:** No
**Side Effects:** Calls _auto_check_memory()

### `AggressiveMemoryManager._auto_check_memory() -> bool`
**Pre:** None (private method)
**Post:** Returns True if memory > threshold, triggers emergency cleanup
**Raises:** No
**Retry:** No
**Side Effects:** psutil memory check, potential emergency cleanup

### `AggressiveMemoryManager.get_memory_usage_mb() -> float`
**Pre:** None
**Post:** Returns current RSS memory in MB or 0.0 on error
**Raises:** No
**Retry:** No
**Side Effects:** None (psutil read)

### `AggressiveMemoryManager.get_stats() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with counts, memory usage, thresholds
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

---

## Acceptance Criteria
- [ ] AC-MEM-001: add_result() enforces maxlen via deque
- [ ] AC-MEM-002: _cleanup_if_needed() keeps at 50% capacity
- [ ] AC-MEM-003: add_backtest_object() creates weak references
- [ ] AC-MEM-004: _cleanup_backtest_objects_if_needed() keeps max 50 objects
- [ ] AC-MEM-005: _deep_cleanup_object() clears container attributes
- [ ] AC-MEM-006: _emergency_cleanup() keeps only 10 results, 5 objects
- [ ] AC-MEM-007: check_memory_pressure() returns True when usage > threshold
- [ ] AC-MEM-008: _auto_check_memory() triggers emergency_cleanup() when threshold exceeded
- [ ] AC-MEM-009: clear_all() performs deep cleanup and single gc.collect()
- [ ] AC-MEM-010: Thread-safety via RLock for all operations
- [ ] AC-MEM-011: get_stats() includes weak_refs_count

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules with 23 P0)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| MEM-001 | BASE_RULES.md (PERF-002) | Memory management for large datasets | ✅ OK - Bounded deques + cleanup |
| MEM-002 | BASE_RULES.md (CC-007) | Small focused functions | ✅ OK - Methods are focused |
| MEM-003 | BASE_RULES.md (TYP-001) | Type hints coverage | ✅ OK - Full type hints |
| MEM-004 | BASE_RULES.md (LOG-001) | Structured logging | ✅ OK - Uses logger with context |
| MEM-005 | BASE_RULES.md (ARCH-004) | Thread-safety for concurrent access | ✅ OK - RLock for all operations |
| MEM-006 | BASE_RULES.md (TRD-002) | Risk validation - no memory leaks | ✅ OK - Weak refs prevent cycles |
| MEM-007 | BASE_RULES.md (LOG-005) | No sensitive data in logs | ✅ OK - No sensitive data logged |

**GAP Analysis:**
- No critical gaps found. Memory management is comprehensive with weak references, bounded deques, and aggressive cleanup.

---

## Dependencies
- **External:** gc, threading, weakref, collections.deque, psutil
- **Internal:**
  - `app.backtesting.models.BacktestResult`

---

## Required Tests
- **tests/backtesting/core/test_memory_manager.py:**
  - Test add_result() enforces maxlen
  - Test _cleanup_if_needed() reduces to 50% capacity
  - Test add_backtest_object() creates weak references
  - Test _cleanup_backtest_objects_if_needed() keeps max 50
  - Test _deep_cleanup_object() clears attributes
  - Test _emergency_cleanup() aggressive reduction
  - Test check_memory_pressure() with psutil mock
  - Test _auto_check_memory() triggers emergency cleanup
  - Test clear_all() performs deep cleanup
  - Test thread-safety with concurrent adds
  - Test weak reference callback removes from _backtest_refs
  - Test get_stats() returns all expected fields
  - Test memory_threshold_mb triggers cleanup

---

## Notes
Critical for long-running parameter sweeps. Weak references prevent circular reference chains. Bounded deques with automatic cleanup prevent unbounded memory growth. Emergency cleanup protects against OOM.
