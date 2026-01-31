# file_backtest_repository.py

## Purpose
File-Based Backtest Repository Implementation - A file-system based implementation of the backtest repository for persisting backtest results to disk as JSON files.

---

## Type Definitions / Data Classes

### FileBacktestRepository(BacktestRepository)
```python
class FileBacktestRepository(BacktestRepository):
    """
    File-system implementation of backtest repository.

    This implementation stores backtests as JSON files on disk,
    organized by status and date.
    """
```

**Directory Structure:**
```
data/backtests/
├── pending/
├── running/
├── completed/
├── failed/
```

**Inheritance:** Implements `BacktestRepository` (domain repository interface)

---

## Function Signatures (Contracts)

### `FileBacktestRepository.__init__(base_dir: str = "data/backtests") -> None`
**Pre:** base_dir is valid path string
**Post:** Repository initialized with subdirectories for each status
**Raises:** None (creates directories if needed)
**Retry:** No
**Side Effects:** Creates base_dir and status subdirectories

**Directory Creation:** `base_dir/{pending,running,completed,failed}/`

### `FileBacktestRepository.save(backtest: Backtest) -> None`
**Pre:** backtest is valid entity
**Post:** Backtest saved as JSON file
**Raises:** IOError if file write fails
**Retry:** No
**Side Effects:** Creates/overwrites JSON file on disk

**File Path:** `base_dir/{status.value}/{backtest_id}.json`

**Serialization:** Uses `_serialize_backtest()` to convert to dict

### `FileBacktestRepository.find_by_id(backtest_id: str) -> Optional[Backtest]`
**Pre:** backtest_id is non-empty string
**Post:** Returns Backtest entity or None if not found
**Raises:** None (returns None on error)
**Retry:** No
**Side Effects:** Reads from disk (pure query)

**Search:** Scans all status directories

**Deserialization:** Uses `_deserialize_backtest()` to convert from JSON

### `FileBacktestRepository.find_by_status(status: BacktestStatus) -> List[Backtest]`
**Pre:** status is valid BacktestStatus
**Post:** Returns list of backtests with that status
**Raises:** None (logs warnings, skips invalid files)
**Retry:** No
**Side Effects:** Reads from disk (pure query)

**Directory:** Only searches `base_dir/{status.value}/`

**Error Handling:** Logs warning for each failed deserialization, continues

### `FileBacktestRepository.find_by_type(backtest_type: BacktestType) -> List[Backtest]`
**Pre:** backtest_type is valid BacktestType
**Post:** Returns list of backtests of that type
**Raises:** None
**Retry:** No
**Side Effects:** Reads from disk (pure query)

**Implementation:** Calls `find_all()`, filters by `config.backtest_type`

### `FileBacktestRepository.find_all(limit: int = 100, offset: int = 0) -> List[Backtest]`
**Pre:** limit >= 0; offset >= 0
**Post:** Returns paginated list of backtests
**Raises:** None (logs warnings, skips invalid files)
**Retry:** No
**Side Effects:** Reads from disk (pure query)

**Sorting:** By `created_at` descending (newest first)

**Pagination:** Applied after sorting (offset, limit)

### `FileBacktestRepository.delete(backtest_id: str) -> bool`
**Pre:** backtest_id is non-empty string
**Post:** Returns True if deleted, False if not found
**Raises:** None
**Retry:** No
**Side Effects:** Deletes file from disk

**Search:** Scans all status directories, deletes first match

### `FileBacktestRepository.count_by_status(status: BacktestStatus) -> int`
**Pre:** status is valid BacktestStatus
**Post:** Returns count of JSON files in status directory
**Raises:** None
**Retry:** No
**Side Effects:** None (pure query)

**Implementation:** Counts `*.json` files in directory

### `FileBacktestRepository.get_recent_completed(limit: int = 10) -> List[Backtest]`
**Pre:** limit >= 0
**Post:** Returns list of recently completed backtests
**Raises:** None
**Retry:** No
**Side Effects:** Reads from disk (pure query)

**Sorting:** By `completed_at` or `created_at` descending

**Limit:** Returns top `limit` results

### `FileBacktestRepository._serialize_backtest(backtest: Backtest) -> Dict`
**Pre:** backtest is valid entity
**Post:** Returns dictionary representation
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Output Fields:**
- backtest_id, status, error_message
- created_at, started_at, completed_at (ISO format)
- config (via `config.to_dict()`)
- result (via `result.to_dict()`)

### `FileBacktestRepository._deserialize_backtest(file_path: Path) -> Optional[Backtest]`
**Pre:** file_path exists and is valid JSON
**Post:** Returns Backtest entity or None if deserialization fails
**Raises:** JSONDecodeError for invalid JSON
**Retry:** No
**Side Effects:** Reads file from disk

**Process Flow:**
1. Load JSON from file
2. Parse config via `BacktestConfigValue.from_dict()`
3. Parse result manually (all 18 fields)
4. Parse status, dates
5. Return Backtest entity

**Result Fields Parsed:**
- initial_capital, final_capital, total_return, total_return_pct
- sharpe_ratio, sortino_ratio, max_drawdown, volatility, var_95
- total_trades, winning_trades, losing_trades, win_rate
- avg_win, avg_loss, profit_factor

---

## Acceptance Criteria
- [ ] **AC-001:** FileBacktestRepository implements BacktestRepository
- [ ] **AC-002:** __init__() creates base_dir and status subdirectories
- [ ] **AC-003:** save() writes JSON to base_dir/{status}/{id}.json
- [ ] **AC-004:** find_by_id() searches all status directories
- [ ] **AC-005:** find_by_status() only searches specified status directory
- [ ] **AC-006:** find_all() sorts by created_at descending
- [ ] **AC-007:** find_all() applies limit and offset pagination
- [ ] **AC-008:** delete() removes file and returns True if found
- [ ] **AC-009:** count_by_status() counts JSON files
- [ ] **AC-010:** get_recent_completed() sorts by completed_at descending
- [ ] **AC-011:** _serialize_backtest() includes config and result
- [ ] **AC-012:** _deserialize_backtest() parses all result fields
- [ ] **AC-013:** find_by_status() logs warnings for invalid files
- [ ] **AC-014:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (File Backtest Repository):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Repository pattern | DDD | Abstract repository in domain | ✅ OK - Implements BacktestRepository |
| Infrastructure layer | Clean Architecture | No domain logic | ✅ OK - Persistence only |
| File system storage | Infrastructure | JSON files on disk | ✅ OK - JSON format |
| Directory organization | Clean code | By status subdirectories | ✅ OK - __init__() creates dirs |
| Error handling | Clean code | Graceful degradation | ✅ OK - Logs warnings, continues |
| Pagination | Repository pattern | limit/offset support | ✅ OK - find_all() |
| Serialization | Clean code | to_dict()/from_dict() | ✅ OK - _serialize/_deserialize |
| Decimal precision | BASE_RULES.md (TYP-002) | Decimal for money | ✅ OK - Decimal types |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and DDD for repository pattern.

---

## Dependencies
- **External:** None (std lib only: json, logging, pathlib, datetime, decimal, typing)
- **Internal:**
  - `app.domain.entities.backtest.Backtest`
  - `app.domain.entities.backtest.BacktestStatus`
  - `app.domain.entities.backtest.BacktestType`
  - `app.domain.repositories.backtest_repository.BacktestRepository`
  - `app.domain.value_objects.backtest_config.BacktestConfigValue`
  - `app.domain.value_objects.backtest_result.BacktestResultValue`

---

## Required Tests
- **test_file_backtest_repository.py:**
  - `test_init_creates_directories()` - Creates base_dir and status dirs
  - `test_save_creates_json_file()` - Writes JSON to disk
  - `test_save_organizes_by_status()` - Uses correct status directory
  - `test_find_by_id_found()` - Returns Backtest entity
  - `test_find_by_id_not_found()` - Returns None
  - `test_find_by_status()` - Returns only backtests with that status
  - `test_find_by_type()` - Filters by backtest_type
  - `test_find_all_sorting()` - Sorted by created_at descending
  - `test_find_all_pagination()` - Applies limit and offset
  - `test_delete_found()` - Deletes file and returns True
  - `test_delete_not_found()` - Returns False
  - `test_count_by_status()` - Returns correct count
  - `test_get_recent_completed_sorting()` - Sorted by completed_at
  - `test_get_recent_completed_limit()` - Returns limit results
  - `test_serialize_backtest()` - Converts to dict correctly
  - `test_deserialize_backtest()` - Converts from JSON correctly
  - `test_deserialize_handles_invalid_files()` - Logs warning, skips file
  - `test_find_by_status_handles_errors()` - Continues on error

---

## Notes
- **Critical:** This is infrastructure code - no business logic
- **Repository Pattern:** DDD pattern for data access abstraction
  - Domain defines `BacktestRepository` interface
  - Infrastructure provides concrete implementation
  - Application layer depends on abstraction, not implementation
- **File Organization:**
  - Backtests organized by status in subdirectories
  - Each backtest is a JSON file named `{backtest_id}.json`
  - Makes it easy to find backtests by status
- **Serialization:**
  - Uses `to_dict()` and `from_dict()` methods on VOs
  - Dates stored as ISO format strings
  - Decimals stored as numbers (JSON default=str)
- **Error Handling:**
  - `find_by_status()` and `find_all()` skip invalid files
  - Logs warnings for each deserialization error
  - Continues processing remaining files
- **Pagination:**
  - `find_all()` supports limit/offset
  - Sorting applied before pagination
  - Default limit = 100
- **Performance Considerations:**
  - File-based approach not suitable for large datasets
  - Each query scans all files in directories
  - Consider database for production with many backtests
- **Testing:**
  - Easy to test with temporary directories
  - No external dependencies
  - Files can be inspected manually
- **Production Rule:** Consider database implementation for production use

---

**File Reference:** `app/infrastructure/persistence/file_backtest_repository.py`
**Last Audited:** 2026-02-01
