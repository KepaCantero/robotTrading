# yaml_config_updater.py

## Purpose
Updates YAML configuration files with optimized parameters while maintaining backup history and validation.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### YAMLConfigUpdater Class
```python
class YAMLConfigUpdater:
    config_dir: Path              # REQUIRED - Directory containing YAML config files
    backup_dir: Path              # REQUIRED - Directory for backup files (created if missing)
    _change_history: list         # PRIVATE - List of change records with timestamps
```

**Validation Rules:**
- `config_dir` must exist and be readable
- `backup_dir` is created if it doesn't exist (mkdir parents=True)
- All YAML operations must validate structure before/after changes
- All optimized_params must pass validation via `_validate_optimized_params()`

---

## Function Signatures (Contracts)

### `__init__(config_dir: Path = Path("config"), backup_dir: Optional[Path] = None) -> None`
**Pre:** config_dir must be a valid directory path
**Post:** backup_dir created, change_history initialized
**Raises:** None (logs warning on issues)
**Retry:** ❌ No
**Side Effects:** Creates backup_dir if missing, logs initialization

### `_validate_optimized_params(params: Dict[str, Any], param_type: str = "general") -> bool`
**Pre:** params is dict, param_type is valid type
**Post:** Returns True if validation passes
**Raises:** TypeError if params not dict, ValueError if validation fails
**Retry:** ❌ No
**Side Effects:** Logs warnings for validation issues

**Validation Rules by Type:**
- `filter`: thresholds must be numeric, typical range 0-100
- `detector`: periods/windows must be positive integers
- `strategy`: exposure must be 0-1
- `learning`: depends on parameter name
- `general`: numeric ranges checked (exposure, threshold, position_size, etc.)

### `update_filter_thresholds(filter_name: str, optimized_params: Dict[str, float], tier: Optional[str] = None, preset: Optional[str] = None) -> bool`
**Pre:** momentum_filters.yaml must exist and be valid YAML
**Post:** Filter thresholds updated, backup created, change registered
**Raises:** Returns False on error ( FileNotFoundError, ValueError, KeyError, TypeError )
**Retry:** ❌ No
**Side Effects:** File system write (config file + backup), change history append

### `update_detector_params(detector_name: str, optimized_params: Dict[str, Any], tier: Optional[str] = None) -> bool`
**Pre:** market_detectors.yaml must exist
**Post:** Detector parameters updated, backup created, change registered
**Raises:** Returns False on error ( FileNotFoundError, ValueError, KeyError, TypeError )
**Retry:** ❌ No
**Side Effects:** File system write, change history append

### `update_strategy_params(strategy_name: str, optimized_params: Dict[str, Any], tier: Optional[str] = None) -> bool`
**Pre:** strategy_defaults.yaml must exist
**Post:** Strategy parameters updated, backup created, change registered
**Raises:** Returns False on error ( FileNotFoundError, ValueError, KeyError, TypeError )
**Retry:** ❌ No
**Side Effects:** File system write, change history append

### `update_learning_params(section: str, optimized_params: Dict[str, Any], tier: Optional[str] = None) -> bool`
**Pre:** learning_parameters.yaml must exist or be creatable
**Post:** Learning parameters updated or section created, backup created
**Raises:** Returns False on error ( ValueError, TypeError, KeyError, AttributeError )
**Retry:** ❌ No
**Side Effects:** File system write, change history append

### `update_multiple_filters(filter_updates: Dict[str, Dict[str, float]], tier: Optional[str] = None) -> Dict[str, bool]`
**Pre:** filter_updates is dict of {filter_name: {param: value}}
**Post:** Returns dict of {filter_name: success} for each filter
**Raises:** ❌ No (returns False for individual failures)
**Retry:** ❌ No
**Side Effects:** Multiple file writes via update_filter_thresholds

### `update_from_optimization_results(optimization_results: Dict[str, Any], tier: Optional[str] = None) -> bool`
**Pre:** optimization_results matches expected schema with filters/detectors/strategies/learning keys
**Post:** All config sections updated atomically
**Raises:** ❌ No (returns False on partial failures)
**Retry:** ❌ No
**Side Effects:** Multiple file writes, change history updates

### `_create_backup(file_path: Path) -> Path`
**Pre:** file_path must exist and be readable
**Post:** Backup created with timestamp in backup_dir
**Raises:** FileNotFoundError, PermissionError (caught by callers)
**Retry:** ❌ No
**Side Effects:** File copy to backup_dir with timestamp

### `restore_from_backup(backup_name: str, original_name: str) -> bool`
**Pre:** backup_name must exist in backup_dir
**Post:** Original file restored from backup
**Raises:** Returns False on error ( FileNotFoundError, PermissionError )
**Retry:** ❌ No
**Side Effects:** Overwrites original file with backup copy

### `_validate_yaml(config: Dict) -> bool`
**Pre:** config is loaded YAML dict
**Post:** Returns True if YAML can be dumped and loaded
**Raises:** ❌ No (returns False on error)
**Retry:** ❌ No
**Side Effects:** Logs validation errors

---

## Acceptance Criteria
- [ ] **AC-YAML-001**: All update methods create backups before modifications
- [ ] **AC-YAML-002**: Backups have timestamp in filename (YYYYMMDD_HHMMSS format)
- [ ] **AC-YAML-003**: YAML validation runs before and after modifications
- [ ] **AC-YAML-004**: Change history tracks all modifications with timestamp, file, section, params
- [ ] **AC-YAML-005**: Tier-specific overrides are supported
- [ ] **AC-YAML-006**: Failed updates log errors and return False (don't crash)
- [ ] **AC-YAML-007**: Restore from backup works correctly
- [ ] **AC-YAML-008**: Input validation prevents invalid parameters (GAP fix implemented)
- [ ] **AC-YAML-009**: All functions have type hints (TYP-001)
- [ ] **AC-YAML-010**: Thread-safe file operations (no concurrent write issues)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-003 | BASE_RULES | Validate all configuration values | ✅ OK - _validate_optimized_params() implements validation |
| YAML-SEC-001 | Security | Use yaml.safe_load/yaml.safe_dump only | ✅ OK - All YAML operations use safe_load/safe_dump |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| LOG-003 | BASE_RULES | Appropriate log levels | ✅ OK - debug/info/error used appropriately |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ OK - exc_info=True used in error handlers |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Specific exceptions caught and logged |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - backup_dir defaults to None, not mutable |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Only handles YAML updates |
| FILE-OP-001 | Custom | All file writes create backups first | ✅ OK - _create_backup() called before writes |

---

## Dependencies
- **External:** `yaml` (PyYAML), `pathlib`, `logging`, `shutil`, `datetime`, `json`
- **Internal:** None (core utility module)

---

## Required Tests
- **test_yaml_config_updater.py:**
  - Success: Backup creation with timestamps
  - Success: update_filter_thresholds creates backup and updates config
  - Success: update_detector_params with tier-specific overrides
  - Success: update_strategy_params creates section if missing
  - Success: update_learning_params creates new section
  - Success: Batch update operations (update_multiple_filters)
  - Success: Full optimization results update (update_from_optimization_results)
  - Success: Change history tracking (all changes recorded)
  - Success: Restore from backup works correctly
  - Validation: _validate_optimized_params rejects invalid params
  - Validation: _validate_optimized_params accepts valid params
  - Validation: YAML validation catches malformed data
  - Error: Missing config file returns False and logs error
  - Error: Invalid YAML structure returns False and logs error
  - Error: Invalid parameter types raise TypeError/ValueError
  - Edge: Empty optimized_params dict handled
  - Edge: Tier not in config handled gracefully
  - Edge: Concurrent updates don't corrupt files
  - Security: yaml.safe_load used (not yaml.load)
  - Security: Backups are never modified

---

## Notes
- Critical configuration management component for optimization workflows
- All operations are atomic (backup before modify)
- Change history supports audit trails
- Input validation added (GAP fix from code review)
- Returns False on errors (fail-safe design)
- Backup files never deleted (manual cleanup required)
