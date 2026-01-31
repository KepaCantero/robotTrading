# unit_of_work.py

## Purpose
Unit of Work pattern implementation - tracks changes during business transaction and commits as single atomic operation with rollback capability.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### `TrackedEntity` DataClass
```python
@dataclass
class TrackedEntity:
    entity: Any                        # REQUIRED - Domain entity being tracked
    state: str                         # REQUIRED - One of: 'new', 'clean', 'dirty', 'deleted'
    original_state: Optional[Dict[str, Any]]  # OPTIONAL - Snapshot for change detection (None for 'new')
```

**Validation Rules:**
- `state` must be one of: 'new', 'clean', 'dirty', 'deleted'
- `original_state` is required only for 'clean' state (change detection)
- `entity` must have identifiable key attribute

### Type Variables
```python
T = TypeVar("T")  # Domain entity type
K = TypeVar("K")  # Key type
```

---

## Function Signatures (Contracts)

### `AbstractUnitOfWork.__enter__() -> AbstractUnitOfWork`
**Pre:** Unit of Work is not already active
**Post:** Returns self, transaction begun
**Raises:** None
**Retry:** ❌ No
**Side Effects:** Begins transaction, initializes resources

### `AbstractUnitOfWork.__exit__(exc_type, exc_val, exc_tb)`
**Pre:** Unit of Work is active
**Post:** If no exception: commits changes; if exception: rollbacks changes
**Raises:** None (exceptions are logged, not propagated)
**Retry:** ❌ No
**Side Effects:** Database commit or rollback, cleanup

### `AbstractUnitOfWork.commit() -> None`
**Pre:** Unit of Work is active and not already committed
**Post:** All tracked changes are persisted atomically, tracked entities cleared
**Raises:** UnitOfWorkError if commit fails or already committed
**Retry:** ✅ Yes (implementation may retry on transient failures)
**Side Effects:** Database transaction commit

### `AbstractUnitOfWork.rollback() -> None`
**Pre:** Unit of Work is active
**Post:** All tracked changes discarded, tracked entities cleared
**Raises:** None (rollback should never fail)
**Retry:** ❌ No (rollback is final)
**Side Effects:** Database transaction rollback, memory cleanup

### `AbstractUnitOfWork.collect_new_events() -> List[Any]`
**Pre:** Unit of Work has tracked entities
**Post:** Returns list of domain events from tracked entities, clears events from entities
**Raises:** None
**Retry:** ❌ No
**Side Effects:** Clears events from entities after collection

### `GenericUnitOfWork.__init__()`
**Pre:** None
**Post:** Unit of Work initialized with empty tracking, commits flag set to False
**Raises:** None
**Retry:** N/A
**Side Effects:** Initializes empty collections

### `GenericUnitOfWork.register_repository(name: str, repository: AbstractRepository) -> None`
**Pre:** name is unique identifier, repository is valid instance
**Post:** Repository is accessible via uow.name attribute
**Raises:** None
**Retry:** N/A
**Side Effects:** Adds repository to internal registry and sets as attribute

### `GenericUnitOfWork.track_entity(entity: Any, state: str = 'new') -> None`
**Pre:** entity has identifiable key, state is valid
**Post:** Entity is tracked with given state, original_state snapshot if 'clean'
**Raises:** None
**Retry:** N/A
**Side Effects:** Adds entity to tracking dictionary

### `GenericUnitOfWork.mark_dirty(entity: Any) -> None`
**Pre:** entity is already being tracked
**Post:** Entity state is changed to 'dirty'
**Raises:** None (silently ignores if not tracked)
**Retry:** N/A
**Side Effects:** Updates tracked entity state

### `GenericUnitOfWork.mark_deleted(entity: Any) -> None`
**Pre:** entity is already being tracked
**Post:** Entity state is changed to 'deleted'
**Raises:** None (silently ignores if not tracked)
**Retry:** N/A
**Side Effects:** Updates tracked entity state

### `unit_of_work_context(uow_factory: Type[AbstractUnitOfWork])`
**Pre:** uow_factory is callable that returns AbstractUnitOfWork instance
**Post:** Yields active Unit of Work, commits on success or rollbacks on exception
**Raises:** Propagates exception from context block after rollback
**Retry:** ❌ No (context manager responsibility)
**Side Effects:** Database transaction managed by UoW lifecycle

---

## Acceptance Criteria
- [ ] **AC-ARCH-001:** Unit of Work follows context manager pattern (__enter__, __exit__)
- [ ] **AC-ARCH-002:** Commit on successful exit, rollback on exception
- [ ] **AC-TRANS-001:** All changes committed as single atomic operation
- [ ] **AC-TRANS-002:** Rollback discards all uncommitted changes
- [ ] **AC-STATE-001:** Entity tracking supports 4 states: new, clean, dirty, deleted
- [ ] **AC-STATE-002:** Commit order: deleted first, then dirty, then new (referential integrity)
- [ ] **AC-TRANS-003:** Cannot commit twice (raises AlreadyCommittedError)
- [ ] **AC-EVENT-001:** Domain events collected and cleared after collection
- [ ] **AC-REPO-001:** Repositories registered and accessible via attributes
- [ ] **AC-ASYNC-001:** Async context manager support for async operations
- [ ] **AC-LOG-001:** Commit and rollback operations logged at INFO level
- [ ] **AC-LOG-002:** Commit failures logged at ERROR level

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Unit of Work Pattern | 04-design-patterns.md (DP-001) | Track changes, commit atomically | ✅ OK |
| Context Manager | 01-formatting-style.md (FMT-008) | Use __enter__/__exit__ for resource management | ✅ OK |
| Transaction Management | 05-architecture.md (ARCH-001) | Single atomic operation for all changes | ✅ OK |
| Domain Events | 10-advanced-patterns.md | Collect events from tracked entities | ✅ OK |
| Repository Management | 04-design-patterns.md (DP-001) | UoW manages repository lifecycle | ✅ OK |
| State Tracking | 03-solid-principles.md (SOL-001) | Single responsibility: track entity state | ✅ OK |
| Commit Order | 05-architecture.md (ARCH-001) | Delete → Update → Create (referential integrity) | ✅ OK |
| Error Handling | 00-checklist.md (CC-006) | Custom exceptions: UnitOfWorkError, AlreadyCommittedError, NotActiveError | ✅ OK |
| Async Support | 07-async-patterns.md (ASYNC-003) | Async context manager provided | ✅ OK |
| Domain Layer Purity | 05-architecture.md (ARCH-003) | No framework imports in domain layer | ✅ OK |
| Logging | 09-logging-observability.md (LOG-003) | Appropriate log levels (info/error) | ✅ OK |
| Cleanup | 05-architecture.md (CC-007) | Resources cleaned up after commit/rollback | ✅ OK |

**NOTE:** This analysis applies all 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `logging` - Standard library logging
  - `abc` - Abstract base classes
  - `contextlib` - Async context manager decorator
  - `dataclasses` - TrackedEntity dataclass
  - `typing` - Type hints (TypeVar, Dict, List, Optional, Type)
- **Internal:**
  - `app.domain.repositories.base_repository` - AbstractRepository base class

---

## Required Tests
- **tests/domain/repositories/test_unit_of_work.py:**
  - Test context manager enters and exits correctly
  - Test commit on successful exit (no exception)
  - Test rollback on exception during context
  - Test commit raises error if already committed
  - Test rollback clears tracked entities
  - Test track_entity with 'new' state
  - Test track_entity with 'clean' state (snapshot created)
  - Test track_entity with 'dirty' state
  - Test track_entity with 'deleted' state
  - Test mark_dirty changes entity state
  - Test mark_deleted changes entity state
  - Test commit processes entities in correct order (deleted → dirty → new)
  - Test collect_new_events returns events from tracked entities
  - Test collect_new_events clears events from entities
  - Test register_repository makes repository accessible via attribute
  - Test unit_of_work_context commits on success
  - Test unit_of_work_context rollbacks on exception
  - Test UnitOfWorkError raised on commit failure
  - Test AlreadyCommittedError raised on double commit
  - Test NotActiveError raised when used outside context
  - Test cleanup called after commit
  - Test cleanup called after rollback
  - Test TradingUnitOfWork example with orders and portfolios
  - Test multiple repositories managed by single UoW

---

## Notes
- This module implements the Unit of Work pattern from "Architecture Patterns with Python" (Cosmic Python) Chapter 7
- Client code doesn't need to track what changed - UoW tracks automatically
- All changes committed as single atomic operation (all or nothing)
- Rollback does NOT revert entity object state, only discards tracking
- Domain Events pattern: entities generate events, UoW collects them for handlers
- Commit order ensures referential integrity: deleted first, then updated, then new
- GenericUnitOfWork provides base implementation, concrete UoW adds specific repositories
- TradingUnitOfWork example shows multi-repository coordination (orders, portfolios, positions)
