# config/profile_config_loader.py

## Purpose
Loads profile optimization configuration from YAML with support for risk profiles (conservative, balanced, aggressive) and capital tiers (micro, small, medium, large).

---

## Type Definitions / Data Classes

### ProfileConfigLoader Class
```python
class ProfileConfigLoader:
    config_path: Path                               # REQUIRED - Path to YAML file
    profile: Optional[str]                          # OPTIONAL - Risk profile
    tier: Optional[str]                             # OPTIONAL - Capital tier
    yaml_loader: YAMLConfigLoader                   # REQUIRED - Delegated loader
    _config: Optional[Dict[str, Any]]               # PRIVATE - Loaded config
```

**Validation Rules:**
- Profiles: conservative, balanced, aggressive, income, growth, dividendos
- Tiers: micro, small, medium, large
- Configuration files must use safe_load

---

## Function Signatures (Contracts)

### `ProfileConfigLoader.__init__(config_dir, profile, tier) -> None`
**Pre:** None
**Post:** Instance initialized with config loaded
**Raises:** None
**Retry:** No
**Side Effects:** Loads YAML file, applies profile/tier overrides

### `ProfileConfigLoader.get(key_path, default) -> Any`
**Pre:** key_path is string
**Post:** Returns nested value or default
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ProfileConfigLoader.get_random_state() -> int`
**Pre:** Config loaded
**Post:** Returns random state seed (default: 42)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ProfileConfigLoader.get_test_size() -> float`
**Pre:** Config loaded
**Post:** Returns test size ratio (default: 0.2)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ProfileConfigLoader.get_cv_folds() -> int`
**Pre:** Config loaded
**Post:** Returns CV fold count (default: 5)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ProfileConfigLoader.get_max_workers(cpu_count) -> Optional[int]`
**Pre:** None
**Post:** Returns max workers for parallel processing
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ProfileConfigLoader.get_model_params(model_type) -> Dict[str, Any]`
**Pre:** model_type is string
**Post:** Returns model parameters dict
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ProfileConfigLoader.get_threshold_config(indicator) -> Dict[str, Any]`
**Pre:** indicator is string
**Post:** Returns threshold optimization config
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ProfileConfigLoader.validate_parameter_range(key_path, value, ...) -> bool`
**Pre:** key_path is string, value is numeric
**Post:** Returns True if value in range
**Raises:** None
**Retry:** No
**Side Effects:** Logs warnings if out of range

### `get_profile_config_loader(profile, tier, config_path) -> ProfileConfigLoader`
**Pre:** None
**Post:** Returns cached or new ProfileConfigLoader
**Raises:** None
**Retry:** No
**Side Effects:** Caches instance by (profile, tier, config_path)

### `get_common_params(profile, tier) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict of common parameters
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_model_params(model_type, profile, tier) -> Dict[str, Any]`
**Pre:** model_type is string
**Post:** Returns model parameters with overrides
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_threshold_ranges(indicator, profile, tier) -> Dict[str, Any]`
**Pre:** indicator is string
**Post:** Returns threshold ranges with overrides
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_rl_config(profile, tier) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns complete RL config
**Raises:** None
**Retry:** No
**Side Effects:** None

### `clear_loader_cache() -> None`
**Pre:** None
**Post:** Loader cache cleared
**Raises:** None
**Retry:** No
**Side Effects:** Clears global _loaders dict

---

## Acceptance Criteria
- [ ] Configuration loaded from YAML with safe_load
- [ ] Profile overrides applied correctly (conservative, balanced, aggressive)
- [ ] Tier overrides applied correctly (micro, small, medium, large)
- [ ] Nested parameter access via dot notation
- [ ] Thread-safe singleton pattern with caching
- [ ] Parameter range validation with warnings
- [ ] Convenience functions return proper defaults
- [ ] Type hints on all functions
- [ ] Error handling with logging (not exceptions)

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-04T00:00:00Z |
| **Audit Status** | AUDITED |
| **BASE_RULES Version** | a1b2c3d (2026-01-10) |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 0 / 0 total |

---

## Critical Rules (MUST NOT BREAK)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-002 | BASE_RULES | Environment variables | ✅ OK - Uses YAMLConfigLoader |
| CFG-003 | BASE_RULES | Config validation | ✅ OK - Parameter validation |
| YAML-SEC-001 | Security | safe_load required | ✅ OK - Delegated to YAMLConfigLoader |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Using logging module |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Only profile config |

---

## Dependencies
- **External:** logging, pathlib, typing
- **Internal:** app.core.config_loader.YAMLConfigLoader

---

## Required Tests
- **tests/unit/core/config/test_profile_config_loader.py:**
  - Test profile override application
  - Test tier override application
  - Test nested parameter access
  - Test get_random_state returns default
  - Test get_model_params for different models
  - Test get_threshold_config returns ranges
  - Test validate_parameter_range checks ranges
  - Test singleton caching with different profiles
  - Test clear_loader_cache clears cache
  - Test convenience functions work correctly

---

## Notes
- **Design Pattern:** Facade over YAMLConfigLoader
- **Caching:** Singleton instances cached by (profile, tier, path) tuple
- **Override Order:** Base config -> Profile override -> Tier override
- **Defaults:** All get methods have sensible defaults
---
