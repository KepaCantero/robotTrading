# backtest_repository.py

## Purpose
Backtest Repository Interface - Abstract contract for backtest persistence. Defines the contract for backtest data access without specifying the implementation. Implementations are in the infrastructure layer.

---

## Type Definitions / Data Classes

### BacktestRepository(ABC)
```python
class BacktestRepository(ABC):
    """
    Repository interface for backtest persistence.

    This abstract base class defines the contract that all backtest
    repository implementations must follow.
    """
```

**Pattern:** Repository Pattern (DDD)
**Purpose:** Abstract data access from domain logic
**Implementations:** FileBacktestRepository, InMemoryBacktestRepository (infrastructure layer)

---

## Function Signatures (Contracts)

### `BacktestRepository.save(backtest: Backtest) -> None`
**Pre:** backtest is valid entity
**Post:** Backtest persisted to storage
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** Stores backtest (implementation-specific)

**Implementation Notes:**
- Must handle new backtests (create)
- Must handle existing backtests (update)
- Implementations choose storage mechanism

### `BacktestRepository.find_by_id(backtest_id: str) -> Optional[Backtest]`
**Pre:** backtest_id is string
**Post:** Returns Backtest entity or None if not found
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)

**Implementation Notes:**
- Returns None if backtest_id not found
- Implementations scan all storage locations

### `BacktestRepository.find_by_status(status: BacktestStatus) -> List[Backtest]`
**Pre:** status is valid BacktestStatus
**Post:** Returns list of backtests with that status
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)

**Implementation Notes:**
- Filter by status field
- Return empty list if no matches

### `BacktestRepository.find_by_type(backtest_type: BacktestType) -> List[Backtest]`
**Pre:** backtest_type is valid BacktestType
**Post:** Returns list of backtests of that type
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)

**Implementation Notes:**
- Filter by `config.backtest_type`
- Return empty list if no matches

### `BacktestRepository.find_all(limit: int = 100, offset: int = 0) -> List[Backtest]`
**Pre:** limit >= 0; offset >= 0
**Post:** Returns paginated list of backtests
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)

**Default Parameters:**
- limit = 100
- offset = 0

**Implementation Notes:**
- Should apply consistent sorting (typically by created_at descending)
- Apply pagination after sorting

### `BacktestRepository.delete(backtest_id: str) -> bool`
**Pre:** backtest_id is string
**Post:** Returns True if deleted, False if not found
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** Removes backtest from storage

**Implementation Notes:**
- Return False if backtest_id not found
- Return True if successfully deleted

### `BacktestRepository.count_by_status(status: BacktestStatus) -> int`
**Pre:** status is valid BacktestStatus
**Post:** Returns count of backtests with that status
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)

**Implementation Notes:**
- Count backtests matching status
- Return 0 if no matches

### `BacktestRepository.get_recent_completed(limit: int = 10) -> List[Backtest]`
**Pre:** limit >= 0
**Post:** Returns list of recently completed backtests
**Raises:** Implementation-defined
**Retry:** No
**Side Effects:** None (pure query)

**Default Parameters:**
- limit = 10

**Implementation Notes:**
- Filter by BacktestStatus.COMPLETED
- Sort by completed_at (or created_at if completed_at is None)
- Return top `limit` results

---

## Acceptance Criteria
- [ ] **AC-001:** BacktestRepository is an abstract base class (ABC)
- [ ] **AC-002:** All methods have @abstractmethod decorator
- [ ] **AC-003:** save() accepts Backtest entity
- [ ] **AC-004:** find_by_id() returns Optional[Backtest]
- [ ] **AC-005:** find_by_status() filters by BacktestStatus
- [ ] **AC-006:** find_by_type() filters by BacktestType
- [ ] **AC-007:** find_all() has default limit=100, offset=0
- [ ] **AC-008:** delete() returns bool (True if deleted, False if not found)
- [ ] **AC-009:** count_by_status() returns int count
- [ ] **AC-010:** get_recent_completed() has default limit=10
- [ ] **AC-011:** All methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Backtest Repository Interface):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Repository pattern | DDD | Abstract repository in domain | ✅ OK - BacktestRepository(ABC) |
| Interface contract | DDD | All methods abstract | ✅ OK - @abstractmethod |
| Dependency inversion | SOLID | Domain defines abstraction | ✅ OK - Domain layer |
| Infrastructure separation | Clean Architecture | Implementations in infrastructure | ✅ OK - Docstring |
| CRUD operations | Repository pattern | save, find, delete | ✅ OK - Complete CRUD |
| Pagination | Repository pattern | limit/offset support | ✅ OK - find_all() |
| Filtering | Repository pattern | find_by_status, find_by_type | ✅ OK - Filter methods |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All methods documented | ✅ OK - Complete |

**NOTE:** This is an INTERFACE - implementations in infrastructure layer must follow this contract.

---

## Dependencies
- **External:** None (std lib only: abc, typing)
- **Internal:**
  - `app.domain.entities.backtest.Backtest`
  - `app.domain.entities.backtest.BacktestStatus`
  - `app.domain.entities.backtest.BacktestType`

---

## Required Tests
- **test_backtest_repository_interface.py:**
  - `test_backtest_repository_is_abc()` - Cannot instantiate ABC
  - `test_save_is_abstract()` - Has @abstractmethod
  - `test_find_by_id_is_abstract()` - Has @abstractmethod
  - `test_find_by_status_is_abstract()` - Has @abstractmethod
  - `test_find_by_type_is_abstract()` - Has @abstractmethod
  - `test_find_all_is_abstract()` - Has @abstractmethod
  - `test_delete_is_abstract()` - Has @abstractmethod
  - `test_count_by_status_is_abstract()` - Has @abstractmethod
  - `test_get_recent_completed_is_abstract()` - Has @abstractmethod

**Implementation Tests (for concrete implementations):**
  - `test_save_persists_backtest()` - Stores backtest
  - `test_find_by_id_returns_backtest()` - Returns entity when found
  - `test_find_by_id_returns_none()` - Returns None when not found
  - `test_find_by_status_filters()` - Returns only matching status
  - `test_find_by_type_filters()` - Returns only matching type
  - `test_find_all_applies_pagination()` - Uses limit/offset
  - `test_delete_removes_backtest()` - Deletes and returns True
  - `test_delete_not_found_returns_false()` - Returns False when not found
  - `test_count_by_status_counts()` - Returns correct count
  - `test_get_recent_completed_filters()` - Returns only completed
  - `test_get_recent_completed_sorts()` - Sorted by completed_at

---

## Notes
- **Critical:** This is an INTERFACE - domain defines contract
- **Repository Pattern (DDD):**
  - Domain layer defines repository interfaces
  - Infrastructure layer provides implementations
  - Application layer depends on abstraction (interface)
  - Enables testing with mock implementations
- **Interface Contract:**
  - Implementations MUST provide all 8 methods
  - Methods MUST follow specified signatures
  - Return types MUST match interface
  - Implementations choose storage mechanism (file, database, memory)
- **Clean Architecture:**
  - Domain knows nothing about storage implementation
  - Infrastructure imports domain (not vice versa)
  - Application depends on domain interface
- **Dependency Inversion Principle:**
  - High-level modules (application) depend on abstractions
  - Low-level modules (infrastructure) implement abstractions
  - Both depend on the interface, not concretions
- **Current Implementations:**
  - `FileBacktestRepository` - JSON file storage
  - `InMemoryBacktestRepository` - Dict storage (testing)
- **Production Rule:** Always depend on this interface, never concrete implementations

---

**File Reference:** `app/domain/repositories/backtest_repository.py`
**Last Audited:** 2026-02-01
