# tier_mapper.py

## Purpose
Unified tier mapping system for algorithmic trading. Provides centralized, consistent mapping between different tier naming conventions (capital_flag, YAML, Spanish) used across the system.

---

## Type Definitions / Data Classes

### TierSystem Enum
```python
class TierSystem(str, Enum):
    CAPITAL_FLAG = "capital_flag"    # InputProfile.capital_flag: small, medium, large
    YAML = "yaml"                    # investment_profiles.yaml: micro, small, medium, large
    SPANISH = "spanish"              # Config expectations: bajo, medio, alto
    STANDARD = "standard"            # Internal standard: micro, small, medium, large
```

### TierThresholds Dict
```python
THRESHOLDS: Dict[str, Decimal] = {
    "micro": Decimal("0")            # < €15k
    "small": Decimal("15000")        # €15k - €50k
    "medium": Decimal("50000")       # €50k - €250k
    "large": Decimal("250000")       # >= €250k
}
```

**Validation Rules:**
- Thresholds loaded from config/capital_tiers.yaml
- Fallback to hardcoded values if config unavailable (with error)
- Thresholds must be in ascending order
- All thresholds are positive Decimal values

---

## Function Signatures (Contracts)

### `TierMapper._load_thresholds_from_config(cls) -> None`
**Pre:** config module available
**Post:** Thresholds loaded from config or raise error
**Raises:** FileNotFoundError, ValueError, KeyError, TypeError
**Retry:** No
**Side Effects:** Updates cls.THRESHOLDS, logs result

### `TierMapper.get_thresholds(cls) -> Dict[str, Decimal]`
**Pre:** None
**Post:** Returns thresholds dict (excluding "loaded" key)
**Raises:** No (loads from config if needed)
**Retry:** No
**Side Effects:** Calls _load_thresholds_from_config if needed

### `TierMapper.get_tier_from_capital(cls, capital: Decimal) -> str`
**Pre:** capital >= 0
**Post:** Returns tier: "micro", "small", "medium", or "large"
**Raises:** FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError
**Retry:** No
**Side Effects:** Loads config, logs result

**Capital ranges:**
- micro: < €15k
- small: €15k - €50k
- medium: €50k - €250k
- large: >= €250k

### `TierMapper.get_capital_flag_tier(cls, capital: Decimal) -> str`
**Pre:** capital >= 0
**Post:** Returns tier: "small", "medium", or "large"
**Raises:** No
**Retry:** No
**Side Effects:** None

**Capital ranges (3-tier system):**
- small: < €50k
- medium: €50k - €250k
- large: >= €250k

### `TierMapper.to_yaml_tier(cls, tier: str, source_system: Optional[TierSystem] = None) -> str`
**Pre:** tier is valid in source system
**Post:** Returns tier in YAML format (4-tier)
**Raises:** ValueError if invalid or conversion not possible
**Retry:** No
**Side Effects:** Auto-detects source system if None

### `TierMapper.to_spanish(cls, tier: str, source_system: Optional[TierSystem] = None) -> str`
**Pre:** tier is valid in source system
**Post:** Returns tier in Spanish format (bajo, medio, alto)
**Raises:** ValueError if invalid or conversion not possible
**Retry:** No
**Side Effects:** Auto-detects source system if None

**YAML to Spanish mapping:**
- micro -> bajo
- small -> bajo
- medium -> medio
- large -> alto

### `TierMapper.to_capital_flag(cls, tier: str, source_system: Optional[TierSystem] = None) -> str`
**Pre:** tier is valid in source system
**Post:** Returns tier in capital_flag format (3-tier)
**Raises:** ValueError if invalid or conversion not possible
**Retry:** No
**Side Effects:** Auto-detects source system if None

### `TierMapper.detect_system(cls, tier: str) -> TierSystem`
**Pre:** tier is non-empty
**Post:** Returns detected TierSystem
**Raises:** ValueError if tier not recognized
**Retry:** No
**Side Effects:** None

**Detection priority:**
- "bajo", "medio", "alto" -> SPANISH
- "micro" -> YAML
- "small", "medium", "large" -> CAPITAL_FLAG (preferred)

### `TierMapper.is_valid_tier(cls, tier: str, system: Optional[TierSystem] = None) -> bool`
**Pre:** tier is non-empty
**Post:** Returns True if tier valid
**Raises:** No
**Retry:** No
**Side Effects:** None

### `TierMapper.list_all_valid_tiers(cls) -> Dict[str, Tuple[str, ...]]`
**Pre:** None
**Post:** Returns dict of system -> valid tiers
**Raises:** No
**Retry:** No
**Side Effects:** None

### `TierMapper.validate_consistency(cls) -> Tuple[bool, List[str]]`
**Pre:** None
**Post:** Returns (is_valid, list_of_warnings)
**Raises:** No
**Retry:** No
**Side Effects:** Checks bidirectional mappings, threshold ordering

---

## Module Functions

### `get_tier(capital: Decimal, system: TierSystem = TierSystem.YAML) -> str`
**Pre:** capital >= 0
**Post:** Returns tier in requested system
**Raises:** No (propagates from TierMapper)
**Retry:** No
**Side Effects:** None

### `normalize_tier(tier: str, target_system: TierSystem = TierSystem.YAML) -> str`
**Pre:** tier is valid
**Post:** Returns normalized tier
**Raises:** ValueError if tier invalid
**Retry:** No
**Side Effects:** Auto-detects source system

### `map_profile_tier_to_config(capital_flag: str, target_format: str = "yaml") -> str`
**Pre:** capital_flag valid, target_format in ["yaml", "spanish"]
**Post:** Returns tier in target format
**Raises:** No (logs warning for unknown format)
**Retry:** No
**Side Effects:** Logs warning for unknown format

### `validate_tier_mapping() -> Tuple[bool, List[str]]`
**Pre:** None
**Post:** Returns validation result
**Raises:** No
**Side Effects:** Logs results

---

## Acceptance Criteria
- [ ] Tier detection auto-detects system
- [ ] Capital thresholds loaded from config (required)
- [ ] Fallback to hardcoded thresholds with error if config fails
- [ ] Three tier systems supported: capital_flag (3), YAML (4), Spanish (3)
- [ ] Bidirectional mapping between all systems
- [ ] Consistency validation on module import
- [ ] Warnings logged for mapping inconsistencies
- [ ] Threshold ordering validated
- [ ] Institutional tier mapped to large for backward compatibility

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| RSK-003 | BASE_RULES.md | Drawdown control | ✅ OK - Tier limits |
| TRD-003 | BASE_RULES.md | Position limits | ✅ OK - Max position size |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - ValueError for invalid tiers |
| CFG-003 | BASE_RULES.md | Validation | ✅ OK - Input validation |
| CFG-002 | BASE_RULES.md | Environment variables | ✅ OK - Config from YAML |
| LOG-004 | BASE_RULES.md | Error logging | ⚠️ PARTIAL - Errors logged but no stack traces |
| TYP-001 | BASE_RULES.md | Type coverage | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses Dict, Optional, Tuple |

**GAPS IDENTIFIED:**
1. **LOG-004 Partial**: Error logging exists but lacks explicit stack traces (`exc_info=True` missing in some error logs)
2. **CFG-002 Risk**: Config loading has fallback to hardcoded values instead of failing fast in production

---

## Dependencies
- **External:** logging, decimal, enum, typing
- **Internal:** app.core.config.strategy_config_loader (get_strategy_config)

---

## Required Tests
- **tests/core/test_tier_mapper.py:**
  - Test get_tier_from_capital() for all thresholds
  - Test get_capital_flag_tier() for 3-tier system
  - Test to_yaml_tier() conversion from all systems
  - Test to_spanish() conversion from all systems
  - Test to_capital_flag() conversion from all systems
  - Test detect_system() for all tier names
  - Test is_valid_tier() for valid/invalid tiers
  - Test list_all_valid_tiers() returns all systems
  - Test validate_consistency() checks mappings
  - Test normalize_tier() auto-detection
  - Test map_profile_tier_to_config() conversion
  - Test get_tier() with different systems
  - Test config loading failure handling
  - Test threshold ordering validation
  - Test institutional -> large mapping

---

## Notes
- **PROBLEM:** System uses 3 different tier systems:
  1. InputProfile.capital_flag: "small", "medium", "large" (3 tiers)
  2. investment_profiles.yaml: "micro", "small", "medium", "large" (4 tiers)
  3. Config expectations: "bajo", "medio", "alto" (Spanish, 3 tiers)
- **SOLUTION:** Unified mapping between all systems with validation
- **Capital thresholds (EUR):**
  - micro: < €15k
  - small: €15k - €50k
  - medium: €50k - €250k
  - large: >= €250k
- **Spanish mapping:**
  - bajo (low): micro, small
  - medio (medium): medium
  - alto (high): large
- **Capital flag mapping (3-tier):**
  - small: < €50k
  - medium: €50k - €250k
  - large: >= €250k
