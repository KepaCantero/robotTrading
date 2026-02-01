# profile_generator.py

## Purpose
Generates backtest profile combinations (objectives × risks × tiers × horizons) and maps profiles to backtest configurations using ProfileStrategyMapper.

---

## Type Definitions / Data Classes
No custom dataclasses defined - uses InputProfile from core.models.

---

## Function Signatures (Contracts)

### `generate_all_profiles() -> List[InputProfile]`
**Pre:** config has capital_tiers dict
**Post:** Returns list of InputProfile objects (5 objectives × 3 risks × 3 tiers × N horizons)
**Raises:** None (returns empty list on config error)
**Retry:** No
**Side Effects:** None (object creation)

### `_load_investment_horizons() -> List[int]`
**Pre:** config YAML loaded successfully
**Post:** Returns list of horizon values in months (positive integers)
**Raises:** Returns default horizons [12, 24, 36, 60] on error
**Retry:** No
**Side Effects:** None (reads config)

### `get_capital_tier_key(profile) -> str`
**Pre:** profile has valid capital_flag
**Post:** Returns tier key: "bajo", "medio", or "alto"
**Raises:** Returns "medio" default if mapper fails
**Retry:** No
**Side Effects:** None (mapping logic)

### `create_profile_config(profile, output_dir) -> Dict[str, Any]`
**Pre:** profile is valid InputProfile, output_dir is writable
**Post:** Returns complete config dict for backtesting with input, modules, risk_management, strategy sections
**Raises:** Returns fallback config if ProfileStrategyMapper fails
**Retry:** No
**Side Effects:** None (dict construction)

### `create_profile_id(profile) -> str`
**Pre:** profile has objetivo_inversion, risk_tolerance, capital_flag, investment_horizon
**Post:** Returns profile_id string: "{objective}_{risk}_{tier}_{horizon}m"
**Raises:** None
**Retry:** No
**Side Effects:** None (string formatting)

---

## Acceptance Criteria
- [ ] generate_all_profiles() creates 5 × 3 × 3 × N profiles (objectives × risks × tiers × horizons)
- [ ] Objectives: all values from ObjectivoInversion enum
- [ ] Risk tolerances: bajo, medio, alto (from RiskTolerance enum)
- [ ] Capital tiers: bajo, medio, alto
- [ ] Investment horizons loaded from config (dict or list format)
- [ ] Horizon validation: must be positive integer, warning if outside 1-360 range
- [ ] Default horizons: [12, 24, 36, 60] if not configured
- [ ] ProfileStrategyMapper used when available, falls back to manual config
- [ ] Manual config includes risk_params, objective_params from config
- [ ] Tier mapping uses map_profile_tier_to_config() with fallback to simple dict
- [ ] Profile ID format: "{objective}_{risk}_{tier}_{horizon}m"

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ FIXED - 2026-02-01 - Added type aliases (ConfigDict, MetricsDict, StrategyConfigDict) and updated all return types |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Catches FileNotFoundError, ValueError, etc. |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ⚠️ ACCEPTED - create_profile_config() is ~100 lines due to: 1) Complex multi-strategy config construction, 2) ProfileStrategyMapper integration with fallback, 3) Nested dictionary structure for input/modules/risk_management/strategy sections, 4) Risk parameter calculations with Decimal arithmetic, 5) Strategy mapping metadata extraction. Lower priority code style issue, no functional impact. Future refactoring could extract strategy config builder and risk config builder helper methods. |
| CFG-002 | BASE_RULES | Environment variables | ⚠️ NOT APPLIED - Uses YAML config |
| CFG-003 | BASE_RULES | Configuration validation | ✅ OK - Validates horizons |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - Logging provides audit trail |

**NOTE:** ProfileStrategyMapper integration is optional - code falls back to manual configuration if mapper fails or not available.

---

## Dependencies
- **External:** logging, decimal, pathlib, typing, yaml
- **Internal:**
  - `app.core.models.input_profile.InputProfile`
  - `app.core.models.input_profile.ObjectivoInversion`
  - `app.core.models.input_profile.RiskTolerance`
  - `app.core.tier_mapper.map_profile_tier_to_config`
  - `app.services.profile_driven_trading.profile_strategy_mapper.create_profile_mapper`

---

## Required Tests
- **tests/backtesting/profile_batch/test_profile_generator.py:**
  - Test generate_all_profiles() returns correct count
  - Test generate_all_profiles() includes all objective enum values
  - Test generate_all_profiles() includes all risk tolerance enum values
  - Test _load_investment_horizons() with dict format
  - Test _load_investment_horizons() with list format
  - Test _load_investment_horizons() with missing config (returns defaults)
  - Test _load_investment_horizons() validates positive integers
  - Test _load_investment_horizons() warns on out-of-range values
  - Test get_capital_tier_key() uses unified mapper
  - Test get_capital_tier_key() fallback on mapper failure
  - Test create_profile_config() with ProfileStrategyMapper available
  - Test create_profile_config() fallback when mapper fails
  - Test create_profile_config() includes all required sections
  - Test create_profile_id() format matches expected pattern
  - Test manual config includes risk_params and objective_params

---

## Notes
Investment horizon config supports both labeled dict format (e.g., {"short": 12, "medium": 24}) and simple list format [12, 24, 36, 60].

**Known issues (GAPs):** create_profile_config() exceeds ARCH-004 guideline (<20 lines) - **ARCH-004 ACCEPTED** as documented above (lower priority, complex config construction logic).
