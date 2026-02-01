# config_loader.py

## Purpose
Loads YAML configurations with validation, caching, and tier-specific overrides for the algoTrading system.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### YAMLConfigLoader Class
```python
class YAMLConfigLoader:
    config_dir: Path                      # REQUIRED - Directory containing YAML config files
    _cache: Dict[str, Any]                # PRIVATE - Thread-safe cache for loaded configs
    _cache_lock: threading.RLock          # PRIVATE - Lock for thread-safe cache access
```

**Validation Rules:**
- `config_dir` must exist or warning is logged
- Thread-safe access to `_cache` via `_cache_lock`
- Cache key is the filename
- All loaded configs are validated via `_validate_config()`

---

## Function Signatures (Contracts)

### `YAMLConfigLoader.__init__(config_dir: Optional[Path] = None) -> None`
**Pre:** None
**Post:** Instance initialized with config_dir from env var or parameter
**Raises:** None
**Retry:** ❌ No
**Side Effects:** Reads CONFIG_DIR environment variable, logs warning if config_dir doesn't exist

### `YAMLConfigLoader.load(filename: str, use_cache: bool = True) -> Dict[str, Any]`
**Pre:** filename is non-empty string
**Post:** Returns loaded YAML dict or empty dict on error
**Raises:** Returns {} on error ( FileNotFoundError, YAMLError, OSError )
**Retry:** ❌ No
**Side Effects:** Thread-safe cache read/write, file I/O, logging

### `YAMLConfigLoader.get_nested(config: Dict[str, Any], key_path: str, default: Any = None, separator: str = ".") -> Any`
**Pre:** config is dict, key_path is non-empty string
**Post:** Returns nested value or default if not found
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `YAMLConfigLoader.load_with_tier_override(filename: str, tier: Optional[str] = None) -> Dict[str, Any]`
**Pre:** filename is non-empty string
**Post:** Returns config with tier overrides applied if tier exists
**Raises:** None
**Retry:** ❌ No
**Side Effects:** Calls load(), logs if tier overrides applied

### `YAMLConfigLoader._validate_config(config: Dict[str, Any], filename: str) -> Dict[str, Any]`
**Pre:** config is loaded from YAML
**Post:** Returns validated config or {} if invalid type
**Raises:** None (logs errors)
**Retry:** ❌ No
**Side Effects:** Logging of validation warnings/errors

### `YAMLConfigLoader.clear_cache() -> None`
**Pre:** None
**Post:** Cache is empty
**Raises:** None
**Retry:** ❌ No
**Side Effects:** Thread-safe cache clear

### `get_config_loader() -> YAMLConfigLoader`
**Pre:** None
**Post:** Returns singleton YAMLConfigLoader instance
**Raises:** None
**Retry:** ❌ No
**Side Effects:** Creates singleton if doesn't exist

### Convenience Functions
All return Dict[str, Any] from singleton loader:
- `load_strategy_stock_allocator_config(tier: Optional[str] = None)`
- `load_momentum_filters_config(tier: Optional[str] = None)`
- `load_market_detectors_config(tier: Optional[str] = None)`
- `load_strategy_defaults_config(tier: Optional[str] = None)`
- `load_learning_parameters_config(tier: Optional[str] = None)`
- `get_filter_config(filter_name: str, tier: Optional[str] = None, preset: str = "balanced")`
- `get_detector_config(detector_name: str, tier: Optional[str] = None)`
- `get_strategy_config(strategy_name: str, tier: Optional[str] = None)`

---

## Acceptance Criteria
- [ ] **AC-001**: All YAML files loaded via `yaml.safe_load()` (security requirement)
- [ ] **AC-002**: Thread-safe cache access via `_cache_lock` (concurrent access safe)
- [ ] **AC-003**: CONFIG_DIR environment variable respected (CFG-002)
- [ ] **AC-004**: Sensitive key patterns detected in config (CFG-SEC-001)
- [ ] **AC-005**: Validation rules applied to common config values (CFG-003)
- [ ] **AC-006**: Tier-specific overrides properly merged (recursive merge)
- [ ] **AC-007**: Nested key access works with dot notation
- [ ] **AC-008**: Cache returns same dict object for performance
- [ ] **AC-009**: Invalid/non-existent files return empty dict (not raise)
- [ ] **AC-010**: All functions have type hints (TYP-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-002 | BASE_RULES | Use environment variables for deployment paths | ✅ OK - CONFIG_DIR env var supported |
| CFG-003 | BASE_RULES | Validate all configuration values | ✅ OK - _validate_config() implements validation |
| CFG-SEC-001 | BASE_RULES | Detect sensitive data keys in config | ✅ OK - Checks for password/secret/api_key patterns |
| CFG-CACHE-001 | Custom | Thread-safe cache with locking | ✅ OK - Uses RLock for cache access |
| YAML-SEC-001 | Security | Use yaml.safe_load() not yaml.load() | ✅ OK - All loads use safe_load() |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| LOG-001 | BASE_RULES | Structured logging | ⚠️ NOT APPLIED - Uses standard logging, not structlog |
| LOG-004 | BASE_RULES | Error logging with stack traces | ❌ GAP - Some error handlers use logger.error without exc_info |
| FMT-001 | BASE_RULES | Black formatting | ✅ OK - Code is Black formatted |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Only handles YAML loading |

**GAP Analysis:**
1. **LOG-004 (P0)**: Some error handlers log without `exc_info=True` (lines 104, 107, 235, 297, 302)
   - Impact: Debugging production issues harder without stack traces
   - Fix: Add `exc_info=True` to all `logger.error()` calls in exception handlers

---

## Dependencies
- **External:** `yaml` (PyYAML), `threading`, `pathlib`, `logging`, `os`
- **Internal:** None (core module, no internal imports)

---

## Required Tests
- **test_config_loader.py:**
  - Success: Load valid YAML file
  - Success: Load with tier overrides applied
  - Success: Nested key access with dot notation
  - Success: Thread-safe cache access (concurrent loads)
  - Success: Cache hit returns same object
  - Success: clear_cache() empties cache
  - Success: CONFIG_DIR environment variable respected
  - Error: Invalid YAML returns empty dict
  - Error: Non-existent file returns empty dict
  - Error: Invalid filename returns empty dict
  - Warning: Sensitive keys detected in config
  - Warning: Config directory doesn't exist on init
  - Validation: Common config values validated (exposure 0-1, lookback positive)
  - Singleton: get_config_loader() returns same instance
  - Edge: Empty tier config handled gracefully
  - Edge: Recursive override merge works correctly

---

## Notes
- This is a core infrastructure module used throughout the system
- All errors return empty dict rather than raising (fail-safe design)
- Cache is thread-safe for concurrent access in async/multi-threaded contexts
- Tier-specific overrides support different account sizes (micro/small/medium/large)
- Validation warns but doesn't block invalid configs (fail-soft approach)
