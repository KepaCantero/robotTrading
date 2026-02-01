# di_container.py

## Purpose
Lightweight Dependency Injection container supporting singleton, transient, and factory lifecycles for loose coupling and testability.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses standard types only (no Pydantic models or dataclasses).

### DIContainer Internal State
```python
class DIContainer:
    _singletons: Dict[Type, Any]           # REQUIRED - Cached singleton instances
    _transients: Dict[Type, Type]          # REQUIRED - Transient type mappings
    _factories: Dict[str, Callable]        # REQUIRED - Factory functions
    _lock: threading.RLock                 # REQUIRED - Thread-safe access
```

---

## Function Signatures (Contracts)

### `register_singleton(interface: Type[T], instance: T) -> None`
**Pre:** interface is a type, instance is non-null
**Post:** instance cached and returned for all get() calls
**Raises:** ValueError if interface already registered
**Retry:** No
**Side Effects:** Stores instance in _singletons dict

### `register_transient(interface: Type[T], implementation: Type[T]) -> None`
**Pre:** interface and implementation are types
**Post:** Each get() call creates new implementation instance
**Raises:** ValueError if interface already registered
**Retry:** No
**Side Effects:** Stores mapping in _transients dict

### `register_factory(name: str, factory: Callable[[DIContainer], T]) -> None`
**Pre:** name is non-empty string, factory is callable
**Post:** factory called each time get(name) invoked
**Raises:** ValueError if name already registered
**Retry:** No
**Side Effects:** Stores factory in _factories dict

### `get(interface: Type[T]) -> T`
**Pre:** interface registered with container
**Post:** Returns singleton instance or new transient instance
**Raises:** KeyError if interface not registered
**Retry:** No
**Side Effects:** May create new instance for transients

### `clear() -> None`
**Pre:** None
**Post:** All registrations cleared
**Raises:** None
**Retry:** No
**Side Effects:** Resets all internal dictionaries

---

## Acceptance Criteria
- [ ] SOL-005: All dependencies injected via constructor (no direct instantiation)
- [ ] Thread-safe operations with RLock
- [ ] Singleton instances cached and reused
- [ ] Transient types create new instance per get()
- [ ] Factory functions receive container reference
- [ ] KeyError raised for unregistered dependencies
- [ ] ValueError raised for duplicate registrations
- [ ] clear() resets all state
- [ ] Type hints present on all methods
- [ ] No circular dependencies supported

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| DP-004 | BASE_RULES.md | Dependency injection required | ✅ OK - DI container implemented |
| SOL-005 | BASE_RULES.md | Dependency Inversion Principle | ✅ OK - Depend on abstractions |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods typed |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Only manages DI |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - KeyError, ValueError |

---

## Dependencies
- **External:** typing, threading
- **Internal:** None

---

## Required Tests
- **tests/core/test_di_container.py:**
  - Test singleton registration and reuse
  - Test transient creates new instances
  - Test factory receives container and callable
  - Test duplicate registration raises ValueError
  - Test unregistered get raises KeyError
  - Test thread-safe concurrent access
  - Test clear() resets state
  - Test type hints with mypy

---

## Notes
Lightweight implementation without framework dependencies. Does not support circular dependency resolution. Thread-safe via RLock for singleton cache.
