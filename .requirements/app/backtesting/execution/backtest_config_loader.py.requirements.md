# backtest_config_loader.py

## Purpose
Loads and validates backtest configurations from YAML files with default value fallback and business rule validation.

---

## Type Definitions / Data Classes

### BacktestConfigLoader Class
```python
class BacktestConfigLoader:
    config_path: Path                      # REQUIRED - Path to YAML configuration file
    raw_config: Dict[str, Any]             # REQUIRED - Merged configuration dictionary
    DEFAULT_CONFIG: Dict[str, Any]         # REQUIRED - Default configuration template
```

**Validation Rules:**
- `config_path` must be a valid file path or non-existent (uses defaults)
- `raw_config` must contain required sections: `input`, `strategy`, `capital`
- Required fields in `input`: `symbols` (non-empty list)
- Required fields in `strategy`: `name` (non-empty string)
- Required fields in `capital`: `initial` (positive number)

### DEFAULT_CONFIG Structure
```python
DEFAULT_CONFIG = {
    'input': {
        'start_date': str,      # YYYY-MM-DD format
        'end_date': str,        # YYYY-MM-DD format
        'symbols': list[str],   # Non-empty list of ticker symbols
    },
    'strategy': {
        'name': str,            # Strategy identifier
        'parameters': dict,     # Strategy-specific parameters
    },
    'capital': {
        'initial': float,       # Initial capital > 0
        'currency': str,        # Currency code (e.g., 'USD')
    },
    'risk': {
        'max_position_size': float,    # Max position size as decimal (0-1)
        'stop_loss': float,            # Stop loss as decimal (0-1)
        'take_profit': float,          # Take profit as decimal (0-1)
    },
    'execution': {
        'commission': float,           # Commission rate as decimal
        'slippage': float,             # Slippage as decimal
    },
    'reporting': {
        'output_directory': str,       # Directory for results
        'save_results': bool,          # Whether to save results
    },
    'parallelization': {
        'enabled': bool,               # Enable parallel execution
        'max_workers': int | None,     # Max worker count or None
    },
    'meta_analysis': {
        'enabled': bool,
        'enable_audit': bool,
        'enable_storage': bool,
        'enable_analysis': bool,
    },
}
```

---

## Function Signatures (Contracts)

### `__init__(config_path: str) -> None`
**Pre:** config_path is a valid string path (file may not exist)
**Post:** raw_config is loaded from file or defaults are used
**Raises:** ❌ No (uses defaults on file load errors)
**Retry:** ❌ No
**Side Effects:** Reads file system, initializes instance state

### `_load_config() -> Dict[str, Any]`
**Pre:** self.config_path is initialized
**Post:** Returns configuration dict with defaults merged
**Raises:** ❌ No (returns defaults on any error)
**Retry:** ❌ No
**Side Effects:** File I/O, logging

### `_merge_with_defaults(config: Dict[str, Any]) -> Dict[str, Any]`
**Pre:** config is a dictionary (possibly empty)
**Post:** Returns merged dict with defaults for missing keys
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function with side effect of copy)

### `get_backtest_config() -> Dict[str, Any]`
**Pre:** raw_config is initialized
**Post:** Returns flattened backtest configuration with all required fields
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `validate() -> List[str]`
**Pre:** raw_config is initialized
**Post:** Returns list of validation error messages (empty if valid)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `is_valid() -> bool`
**Pre:** raw_config is initialized
**Post:** Returns True if configuration passes all validations
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] Configuration file falls back to defaults when not found
- [ ] Configuration file falls back to defaults on parse errors
- [ ] validate() catches missing required top-level sections (input, strategy, capital)
- [ ] validate() catches empty or missing symbols list
- [ ] validate() catches empty or missing strategy name
- [ ] validate() catches non-positive initial capital
- [ ] is_valid() returns False when validate() returns errors
- [ ] get_backtest_config() returns dict with all expected keys
- [ ] Default values are properly merged with user config
- [ ] Logger warnings emitted when config file not found
- [ ] Logger errors emitted on config load failures

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

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-001 | 01-formatting-style.md | Line length ≤ 100 | ✅ OK |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK |
| LOG-004 | 09-logging-observability.md | Error logging with stack traces | ✅ FIXED - Added exc_info=True to all error logs |
| LOG-005 | 09-logging-observability.md | No sensitive data in logs | ✅ OK |
| CFG-001 | 08-configuration.md | Pydantic Settings for config | ✅ FIXED - Added BacktestConfigSettings and nested Pydantic models |
| CFG-003 | 08-configuration.md | Validate all configuration values | ✅ FIXED - Added validate_config() method and field validators |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Only loads/validates config |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ FIXED - Uses specific exceptions (FileNotFoundError, ValueError, etc.) |
| ARCH-002 | 05-architecture.md | Dependencies inward | ⚠️ NOT APPLIED - Infrastructure layer, OK to use yaml |
| TRD-004 | BASE_RULES.md | Audit trail for trading decisions | ✅ OK - Logs config load operations |

---

## Dependencies
- **External:** `yaml` (PyYAML), `logging`, `pathlib`, `typing`
- **Internal:** None (standalone configuration loader)

---

## Required Tests
- **tests/unit/backtesting/test_backtest_config_loader.py:**
  - Test loading valid YAML config file
  - Test fallback to defaults when file not found
  - Test fallback to defaults on YAML parse error
  - Test validate() with missing required sections
  - Test validate() with empty symbols list
  - Test validate() with empty strategy name
  - Test validate() with non-positive initial capital
  - Test is_valid() returns correct boolean
  - Test get_backtest_config() returns all expected keys
  - Test merge_with_defaults() properly merges nested dicts
  - Test merge_with_defaults() adds new top-level keys
  - Test logging behavior on warnings and errors

---

## Notes
- This is an infrastructure/configuration layer component
- Consider migrating to Pydantic Settings for better validation (CFG-001 gap)
- Exception handling should be more specific than bare Exception
- All validation errors are collected before returning (not fail-fast)
