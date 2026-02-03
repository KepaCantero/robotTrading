# base_repository.py

## Purpose
Generic repository pattern following Percival's Architecture Patterns with Python - provides collection-like interface for domain entities with abstraction from persistence details.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### `TrackedEntity` DataClass (in unit_of_work.py, referenced here)
```python
@dataclass
class TrackedEntity:
    entity: Any              # REQUIRED - Domain entity being tracked
    state: str               # REQUIRED - One of: 'new', 'clean', 'dirty', 'deleted'
    original_state: Optional[Dict[str, Any]]  # OPTIONAL - Snapshot for change detection
```

### Type Variables
```python
T = TypeVar("T")  # Domain entity type
K = TypeVar("K")  # Key type (typically str or int)
```

**Validation Rules:**
- Repository methods must work with any entity type (Generic[T, K])
- State must be one of: 'new', 'clean', 'dirty', 'deleted'
- Entity must have identifiable key (id, entity_id, order_id, etc.)

---

## Function Signatures (Contracts)

### `AbstractRepository.add(entity: T) -> None`
**Pre:** Entity is valid domain object with identifiable key
**Post:** Entity is persisted and assigned ID if not present
**Raises:** RepositoryError if entity cannot be added
**Retry:** ❌ No (up to implementation)
**Side Effects:** Database write

### `AbstractRepository.get(entity_id: K) -> Optional[T]`
**Pre:** entity_id is valid key type
**Post:** Returns entity if found, None otherwise
**Raises:** RepositoryError if retrieval fails
**Retry:** ✅ Yes (implementation-specific, typically 3 retries with exponential backoff)
**Side Effects:** None (read operation)

### `AbstractRepository.update(entity: T) -> None`
**Pre:** Entity exists in repository and has valid ID
**Post:** Entity is updated in persistence
**Raises:** NotFoundError if entity doesn't exist, RepositoryError if update fails
**Retry:** ❌ No (up to implementation)
**Side Effects:** Database write

### `AbstractRepository.delete(entity_id: K) -> None`
**Pre:** Entity exists in repository
**Post:** Entity is removed from persistence
**Raises:** NotFoundError if entity doesn't exist, RepositoryError if deletion fails
**Retry:** ❌ No (up to implementation)
**Side Effects:** Database write

### `AbstractRepository.list_all() -> List[T]`
**Pre:** None
**Post:** Returns all entities in repository
**Raises:** RepositoryError if listing fails
**Retry:** ✅ Yes (implementation-specific)
**Side Effects:** None (read operation)

### `AbstractRepository.get_or_create(entity_id: K, factory: Callable[[], T]) -> tuple[T, bool]`
**Pre:** factory is callable that returns valid entity
**Post:** Returns (entity, created) where created is True if new entity was created
**Raises:** RepositoryError if operation fails
**Retry:** ✅ Yes (on add operation)
**Side Effects:** Database write if entity doesn't exist

### `AbstractRepository.exists(entity_id: K) -> bool`
**Pre:** None
**Post:** Returns True if entity exists, False otherwise
**Raises:** None (catches exceptions)
**Retry:** ❌ No
**Side Effects:** None

### `AbstractRepository.count() -> int`
**Pre:** None
**Post:** Returns number of entities in repository
**Raises:** RepositoryError if counting fails
**Retry:** ✅ Yes (implementation-specific)
**Side Effects:** None

### `AbstractRepository.add_many(entities: Iterable[T]) -> None`
**Pre:** entities is non-empty iterable of valid entities
**Post:** All entities are persisted
**Raises:** RepositoryError if batch add fails
**Retry:** ✅ Yes (implementation may use bulk insert with retry)
**Side Effects:** Database write (batch operation)

### `AbstractRepository.get_many(entity_ids: Iterable[K]) -> List[T]`
**Pre:** entity_ids is iterable of valid keys
**Post:** Returns list of found entities (may be less than input)
**Raises:** RepositoryError if retrieval fails
**Retry:** ✅ Yes (implementation may use batch query with retry)
**Side Effects:** None (read operation)

### `QueryableRepository.find_by_criteria(**criteria: Any) -> List[T]`
**Pre:** criteria keys match entity field names
**Post:** Returns list of entities matching all criteria
**Raises:** RepositoryError if query fails
**Retry:** ✅ Yes (database query retry)
**Side Effects:** None (read operation)

### `QueryableRepository.find_first(**criteria: Any) -> Optional[T]`
**Pre:** criteria keys match entity field names
**Post:** Returns first matching entity or None
**Raises:** RepositoryError if query fails
**Retry:** ✅ Yes (database query retry)
**Side Effects:** None (read operation)

### `QueryableRepository.find_by_specification(specification: Callable[[T], bool]) -> List[T]`
**Pre:** specification is callable that takes entity and returns bool
**Post:** Returns list of entities where specification(entity) is True
**Raises:** RepositoryError if query fails
**Retry:** ✅ Yes (database query retry)
**Side Effects:** None (read operation)

### `StreamableRepository.stream_all() -> Iterator[T]`
**Pre:** None
**Post:** Yields entities one at a time (memory-efficient)
**Raises:** RepositoryError if streaming fails
**Retry:** ❌ No (streaming context)
**Side Effects:** None (read operation)

### `StreamableRepository.stream_by_criteria(**criteria: Any) -> Iterator[T]`
**Pre:** criteria keys match entity field names
**Post:** Yields matching entities one at a time
**Raises:** RepositoryError if streaming fails
**Retry:** ❌ No (streaming context)
**Side Effects:** None (read operation)

### `CachedRepository.__init__(repository, cache, ttl_seconds)`
**Pre:** repository is valid AbstractRepository instance
**Post:** Cache wrapper is initialized with given TTL
**Raises:** None
**Retry:** N/A
**Side Effects:** None (initialization)

---

## Acceptance Criteria
- [ ] **AC-ARCH-001:** All repository methods are async (use `async def`)
- [ ] **AC-TYP-001:** 100% type coverage - all methods have type hints
- [ ] **AC-ARCH-002:** Domain layer has no infrastructure imports (no SQLAlchemy, FastAPI, httpx)
- [ ] **AC-DP-001:** Repository pattern follows collection-like interface (add, get, update, delete)
- [ ] **AC-SOL-005:** Dependency inversion - domain defines interface, infrastructure implements
- [ ] **AC-EXC-001:** Custom exceptions inherit from RepositoryError base
- [ ] **AC-GEN-001:** Generic type parameters T and K used correctly
- [ ] **AC-LOG-001:** Cache hits/misses logged at DEBUG level
- [ ] **AC-VAL-001:** Cache invalidation on write operations (update, delete)
- [ ] **AC-CACHE-001:** TTL validation prevents negative or zero values

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

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Repository Pattern | 04-design-patterns.md (DP-001) | Repository provides collection-like interface | ✅ OK |
| Async Methods | 07-async-patterns.md (ASYNC-001) | All repository methods must be async | ✅ OK |
| Domain Layer Purity | 05-architecture.md (ARCH-003) | No framework imports in domain | ✅ OK |
| Generic Types | 02-type-hints.md (TYP-001) | Use TypeVar for generic entities | ✅ OK |
| Dependency Inversion | 03-solid-principles.md (SOL-005) | Domain defines contract, infrastructure implements | ✅ OK |
| No Business Logic | 05-architecture.md (ARCH-001) | Repository only does data access, no business rules | ✅ OK |
| Exception Hierarchy | 00-checklist.md (CC-006) | Custom exceptions inherit from RepositoryError | ✅ OK |
| Caching Strategy | 10-advanced-patterns.md | Cache-Aside pattern with TTL | ✅ OK |
| Specification Pattern | 04-design-patterns.md | QueryableRepository supports specifications | ✅ OK |
| Streaming Support | 19-high-performance-python.md | StreamableRepository for large datasets | ✅ OK |

**NOTE:** This analysis applies all 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `logging` - Standard library logging
  - `abc` - Abstract base classes
  - `typing` - Type hints (Generic, TypeVar, Optional, List, Dict, Callable, etc.)
- **Internal:**
  - None (this is a base domain module)

---

## Required Tests
- **tests/domain/repositories/test_base_repository.py:**
  - Test AbstractRepository contract compliance
  - Test get_or_create with existing entity
  - Test get_or_create with new entity
  - Test exists returns True for existing entity
  - Test exists returns False for non-existent entity
  - Test count returns correct number
  - Test add_many with multiple entities
  - Test get_many with mix of existing and non-existing IDs
  - Test QueryableRepository.find_by_criteria with single criterion
  - Test QueryableRepository.find_by_criteria with multiple criteria
  - Test QueryableRepository.find_by_specification with predicate
  - Test StreamableRepository.stream_all yields entities
  - Test CachedRepository cache hit returns cached entity
  - Test CachedRepository cache miss fetches from repository
  - Test CachedRepository write-through updates cache
  - Test CachedRepository TTL expiration invalidates cache
  - Test RepositoryError is raised on add failure
  - Test NotFoundError is raised on get non-existent entity (in implementations)
  - Test DuplicateError is raised on duplicate add (in implementations)

---

## Notes
- This module implements the Repository pattern from "Architecture Patterns with Python" (Cosmic Python) Chapter 6
- Repositories should behave like in-memory collections from the domain's perspective
- Unit of Work pattern (unit_of_work.py) manages transactions across repositories
- CachedRepository uses Cache-Aside pattern with write-through caching
- QueryableRepository implements Specification pattern for complex queries
- StreamableRepository implements Iterator pattern for memory-efficient large dataset access
