# profile_generator.py

## Purpose
Generates backtest profile combinations for batch testing. Handles profile creation, configuration mapping, and tier conversions.

---

## Type Definitions / Data Classes

### ProfileGenerator Class
```python
class ProfileGenerator:
    config_path: Path                                    # REQUIRED - Path to configuration YAML
    config: ConfigDict                                   # REQUIRED - Loaded configuration
    profile_mapper: ProfileStrategyMapper | None         # OPTIONAL - May be None if init fails
```

**Validation Rules:**
- `config_path` must exist and be valid YAML
- `profile_mapper` can be None if initialization fails (fallback to manual config)
- Configuration must contain investment_horizons or defaults used

### Type Aliases
```python
ConfigDict = Dict[str, Any]                              # Configuration dictionary
MetricsDict = Dict[str, Union[float, int, str, bool, None]]  # Metrics dictionary
StrategyConfigDict = Dict[str, Any]                      # Strategy configuration
```

---

## Function Signatures (Contracts)

### `ProfileGenerator.__init__(config_path: str | Path) -> None`
**Pre:** config_path must point to valid YAML file
**Post:** ProfileGenerator initialized with config loaded, profile_mapper initialized or None
**Raises:** FileNotFoundError, yaml.YAMLError
**Retry:** No
**Side Effects:** Loads YAML, attempts to initialize ProfileStrategyMapper

### `ProfileGenerator._load_config() -> ConfigDict`
**Pre:** config_path must exist and be valid YAML
**Post:** Returns configuration dictionary
**Raises:** FileNotFoundError, yaml.YAMLError
**Retry:** No
**Side Effects:** Reads and parses YAML file

### `ProfileGenerator._load_investment_horizons() -> List[int]`
**Pre:** config must be loaded
**Post:** Returns list of horizon values in months (positive integers)
**Raises:** No (returns defaults on failure)
**Retry:** No
**Side Effects:** Logs warnings for invalid horizons

### `ProfileGenerator.generate_all_profiles() -> List[InputProfile]`
**Pre:** config must be loaded with capital_tiers defined
**Post:** Returns list of all InputProfile combinations (objectives × risks × tiers × horizons)
**Raises:** ValueError, KeyError for missing config
**Retry:** No
**Side Effects:** None (generates profiles in memory)

### `ProfileGenerator.get_capital_tier_key(profile: InputProfile) -> str`
**Pre:** profile must have valid capital_flag
**Post:** Returns mapped tier key for config lookups (bajo, medio, or alto)
**Raises:** No (returns "medio" fallback on failure)
**Retry:** No
**Side Effects:** None (uses map_profile_tier_to_config with fallback)

### `ProfileGenerator.create_profile_config(profile: InputProfile, output_dir: Path) -> ConfigDict`
**Pre:** profile must be valid InputProfile, output_dir must exist
**Post:** Returns configuration dictionary for backtesting
**Raises:** ValueError, TypeError, KeyError on config generation failure
**Retry:** No
**Side Effects:** None (generates config dict in memory)

### `ProfileGenerator.create_profile_id(profile: InputProfile) -> str`
**Pre:** profile must be valid InputProfile
**Post:** Returns unique profile ID string
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] generate_all_profiles() returns correct combinations: objectives × risks × tiers × horizons
- [ ] _load_investment_horizons() handles dict format with labels
- [ ] _load_investment_horizons() handles list format
- [ ] _load_investment_horizons() returns default [12, 24, 36, 60] when not configured
- [ ] _load_investment_horizons() validates horizons are positive integers
- [ ] _load_investment_horizons() logs warning for horizons outside 1-360 range
- [ ] get_capital_tier_key() uses unified tier mapping from map_profile_tier_to_config
- [ ] get_capital_tier_key() returns fallback mapping on tier mapper failure
- [ ] create_profile_config() uses ProfileStrategyMapper when available
- [ ] create_profile_config() falls back to manual configuration when mapper fails
- [ ] create_profile_config() includes _strategy_mapping metadata
- [ ] create_profile_id() generates unique, deterministic IDs
- [ ] ProfileStrategyMapper initialization failure is handled gracefully

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - No mutable defaults |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ PARTIAL - Some exceptions lack exc_info |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All functions have type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Domain/application layer |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Profile generation only |
| CFG-002 | BASE_RULES.md | Environment variables | ⚠️ NOT APPLIED - Uses YAML config |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - Config from file |
| LOG-003 | BASE_RULES.md | Appropriate logging levels | ✅ OK - Uses info, warning, error appropriately |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** yaml, logging, decimal, pathlib, typing
- **Internal:**
  - `app.core.models.input_profile.InputProfile, ObjectivoInversion, RiskTolerance`
  - `app.core.tier_mapper.map_profile_tier_to_config`
  - `app.services.profile_driven_trading.profile_strategy_mapper.create_profile_mapper`

---

## Required Tests
- **tests/backtesting/profile_batch/test_profile_generator.py:**
  - Test __init__() loads config successfully
  - Test __init__() handles ProfileStrategyMapper initialization failure
  - Test _load_investment_horizons() with dict format
  - Test _load_investment_horizons() with list format
  - Test _load_investment_horizons() returns defaults when not configured
  - Test _load_investment_horizons() validates positive integers
  - Test _load_investment_horizons() rejects non-integer values
  - Test _load_investment_horizons() warns for out-of-range values
  - Test generate_all_profiles() returns correct combinations count
  - Test generate_all_profiles() creates profiles with correct capital amounts
  - Test get_capital_tier_key() maps small->bajo, medium->medio, large->alto
  - Test get_capital_tier_key() returns fallback on mapper failure
  - Test create_profile_config() uses ProfileStrategyMapper when available
  - Test create_profile_config() falls back to manual config
  - Test create_profile_config() includes _strategy_mapping metadata
  - Test create_profile_id() generates unique IDs
  - Test create_profile_id() generates deterministic IDs for same profile

---

## Notes
- ProfileStrategyMapper is optional - graceful fallback to manual configuration
- Investment horizons support both dict (with labels) and list formats
- Default horizons [12, 24, 36, 60] months used when not configured
- Tier mapping uses unified map_profile_tier_to_config function
- Profile IDs follow pattern: {objective}_{risk}_{tier}_{horizon}m
- Profile combinations: 5 objectives × 3 risks × 3 tiers × N horizons
