# config_loader.py

## Purpose
YAML configuration loader with validation, caching, and tier-based overrides for multi-environment deployment.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses standard types only (no Pydantic models or dataclasses).

### Internal State
```python
class YAMLConfigLoader:
    config_dir: Path                    # REQUIRED - Directory containing YAML files
    _cache: Dict[str, Any]              # INTERNAL - Cached loaded configurations
```

---

## Function Signatures (Contracts)

### `YAMLConfigLoader.__init__(config_dir: Optional[Path] = None) -> None`
**Pre:** config_dir must be valid directory path if provided
**Post:** Loader initialized with cache empty, config_dir set to "config/" if None provided
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `YAMLConfigLoader.load(filename: str, use_cache: bool = True) -> Dict[str, Any]`
**Pre:** filename must be valid YAML filename in config_dir
**Post:** Returns parsed YAML dict or empty dict if file not found/error
**Raises:** ❌ No (returns {} on error)
**Retry:** ❌ No
**Side Effects:** Updates _cache if use_cache=True

### `YAMLConfigLoader.get_nested(config: Dict[str, Any], key_path: str, default: Any = None, separator: str = ".") -> Any`
**Pre:** config must be valid dict, key_path must be non-empty string
**Post:** Returns nested value or default if not found
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `YAMLConfigLoader.load_with_tier_override(filename: str, tier: Optional[str] = None) -> Dict[str, Any]`
**Pre:** filename must exist, tier must be valid key in config["tiers"] if provided
**Post:** Returns base config merged with tier-specific overrides
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `YAMLConfigLoader.clear_cache() -> None`
**Pre:** None
**Post:** Cache is completely emptied
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Clears _cache dict

### Convenience Functions
```python
def get_config_loader() -> YAMLConfigLoader
def load_strategy_stock_allocator_config(tier: Optional[str] = None) -> Dict[str, Any]
def load_momentum_filters_config(tier: Optional[str] = None) -> Dict[str, Any]
def load_market_detectors_config(tier: Optional[str] = None) -> Dict[str, Any]
def load_strategy_defaults_config(tier: Optional[str] = None) -> Dict[str, Any]
def load_learning_parameters_config(tier: Optional[str] = None) -> Dict[str, Any]
def get_filter_config(filter_name: str, tier: Optional[str] = None, preset: str = "balanced") -> Dict[str, Any]
def get_detector_config(detector_name: str, tier: Optional[str] = None) -> Dict[str, Any]
def get_strategy_config(strategy_name: str, tier: Optional[str] = None) -> Dict[str, Any]
```

---

## Acceptance Criteria
- [ ] YAML files are loaded using yaml.safe_load (not unsafe yaml.load)
- [ ] Missing files return empty dict instead of raising FileNotFoundError
- [ ] Cache invalidation works correctly (clear_cache resets state)
- [ ] Tier overrides merge recursively without losing base config values
- [ ] Nested key access works with dot notation (e.g., "data_validation.lookback_max_days")
- [ ] Singleton pattern returns same instance across multiple calls
- [ ] Malformed YAML logs error and returns empty dict (doesn't crash)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets in YAML paths | ✅ OK |
| CFG-002 | BASE_RULES.md | Use environment variables for deployment paths | ⚠️ NOT APPLIED - config_dir defaults to "config/" |
| CFG-003 | BASE_RULES.md | Validate all configuration values | ❌ GAP - No validation of loaded values |
| LOG-003 | BASE_RULES.md | Appropriate log levels (debug/info/error) | ✅ OK |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK |
| ARCH-005 | BASE_RULES.md | Early returns to reduce nesting | ⚠️ PARTIAL - Some nested logic in get_nested |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |

### Configuration-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| CFG-SEC-001 | YAML files must not contain sensitive data (API keys, passwords) | ⚠️ NOT ENFORCED - No validation |
| CFG-CACHE-001 | Cache must be thread-safe if used in async context | ❌ GAP - No locking mechanism |
| CFG-TIER-001 | Tier overrides must validate tier exists before applying | ⚠️ PARTIAL - Only checks if tier in config |
| CFG-OVERRIDE-002 | Recursive merge must preserve all base values | ✅ OK |

---

## Dependencies
- **External:** `yaml` (PyYAML) - safe_load for YAML parsing
- **Internal:** None (pure utility module)
- **Standard Library:** `logging`, `pathlib.Path`, `typing`

---

## Required Tests
- **tests/core/test_config_loader.py:**
  - Test successful YAML loading with valid file
  - Test missing file returns empty dict
  - Test malformed YAML returns empty dict and logs error
  - Test cache hit when use_cache=True
  - Test cache miss when use_cache=False
  - Test clear_cache empties all cached entries
  - Test get_nested with valid dot notation path
  - Test get_nested with invalid path returns default
  - Test load_with_tier_override merges correctly
  - Test load_with_tier_override with non-existent tier returns base config
  - Test singleton pattern returns same instance
  - Test convenience functions load correct YAML files
  - Test get_filter_config with different presets
  - Test _apply_overrides recursive merge logic
  - Edge case: Empty YAML file returns empty dict
  - Edge case: YAML with only comments returns empty dict
  - Security: Verify yaml.safe_load is used (not yaml.load)

---

## Notes
- **Thread Safety:** Current implementation is NOT thread-safe. Add locking if used in async/multi-threaded context.
- **Error Handling:** Silent failures (returning {}) may hide configuration issues. Consider adding strict mode.
- **Path Handling:** config_dir defaults to relative path "config/" - may cause issues if CWD varies.
