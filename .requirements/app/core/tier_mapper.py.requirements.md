# tier_mapper.py Requirements

**File:** `app/core/tier_mapper.py`  
**Purpose:** Unified Tier Mapping System  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.287299

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **Related Files:**
  - `app/core/config/strategy_config_loader.py` (get_strategy_config)
  - Investment profile modules
  - Risk configuration modules

---

## Purpose & Scope

This module provides a centralized, consistent mapping between different tier naming conventions used across the algorithmic trading system:

1. **InputProfile.capital_flag:** "small", "medium", "large" (English, 3 tiers)
2. **investment_profiles.yaml:** "micro", "small", "medium", "large" (English, 4 tiers)
3. **Config expectations:** "bajo", "medio", "alto" (Spanish, 3 tiers)

**Critical for Production:** Ensures consistency across different parts of the system and prevents configuration errors.

---

## Classes & Functions

### Classes

| Class | Purpose | Methods/Attributes |
|-------|---------|-------------------|
| `TierSystem` | Enum of tier systems | CAPITAL_FLAG, YAML, SPANISH, STANDARD |
| `TierMapper` | Centralized tier mapping | Conversion methods, validation, capital-based tier determination |

### Functions

| Function | Purpose | Return Type |
|----------|---------|-------------|
| `get_tier()` | Get tier from capital | `str` |
| `normalize_tier()` | Normalize tier to system | `str` |
| `map_profile_tier_to_config()` | Map capital_flag to config format | `str` |
| `validate_tier_mapping()` | Validate tier consistency | `Tuple[bool, list[str]]` |

---

## File-Specific Requirements

### TIER-001: Capital-Based Tier Determination
**Priority:** P0 (Critical - Correct risk limits)

**Requirement:** Tier must be determined from capital amount using 4-tier system.

**Acceptance Criteria:**
```python
# Micro tier: < €15k
assert TierMapper.get_tier_from_capital(Decimal("10000")) == "micro"

# Small tier: €15k - €50k
assert TierMapper.get_tier_from_capital(Decimal("30000")) == "small"

# Medium tier: €50k - €250k
assert TierMapper.get_tier_from_capital(Decimal("100000")) == "medium"

# Large tier: >= €250k
assert TierMapper.get_tier_from_capital(Decimal("500000")) == "large"
```

**Check:** Tier boundaries are correct

---

### TIER-002: System Conversion Accuracy
**Priority:** P0 (Critical - Configuration consistency)

**Requirement:** Conversions between tier systems must be accurate and bidirectional.

**Acceptance Criteria:**
```python
# Spanish to YAML
assert TierMapper.to_spanish("micro") == "bajo"
assert TierMapper.to_spanish("small") == "bajo"
assert TierMapper.to_spanish("medium") == "medio"
assert TierMapper.to_spanish("large") == "alto"

# YAML to Spanish (reverse)
assert TierMapper.to_yaml_tier("bajo", TierSystem.SPANISH) in ["micro", "small"]
```

**Check:** Conversion mappings are correct

---

### TIER-003: Capital Flag Mapping
**Priority:** P0 (Critical - InputProfile compatibility)

**Requirement:** Capital flag (3-tier) must map correctly to config systems.

**Acceptance Criteria:**
```python
# Capital flag uses 3-tier system
assert TierMapper.get_capital_flag_tier(Decimal("30000")) == "small"  # < €50k
assert TierMapper.get_capital_flag_tier(Decimal("100000")) == "medium"  # €50k-€250k
assert TierMapper.get_capital_flag_tier(Decimal("500000")) == "large"  # >= €250k
```

**Check:** Capital flag logic matches InputProfile

---

### TIER-004: Config Integration
**Priority:** P1 (High - Configuration consistency)

**Requirement:** Tier thresholds must be loaded from centralized config.

**Acceptance Criteria:**
```python
# Should use config/capital_tiers.yaml if available
config = get_strategy_config()
tier = config.get_tier_from_capital(Decimal("100000"))
assert tier in ["micro", "small", "medium", "large", "institutional"]
```

**Check:** Config loading works

---

### TIER-005: Validation Consistency
**Priority:** P1 (High - Data integrity)

**Requirement:** Tier mappings must be internally consistent.

**Acceptance Criteria:**
```python
is_valid, warnings = TierMapper.validate_consistency()
assert is_valid == True
assert len(warnings) == 0
```

**Check:** Validation catches inconsistencies

---

### TIER-006: Auto-Detection
**Priority:** P2 (Medium - Developer experience)

**Requirement:** Tier system should be auto-detected from tier name.

**Acceptance Criteria:**
```python
assert TierMapper.detect_system("bajo") == TierSystem.SPANISH
assert TierMapper.detect_system("micro") == TierSystem.YAML
assert TierMapper.detect_system("small") == TierSystem.CAPITAL_FLAG
```

**Check:** Detection works for all tiers

---

### TIER-007: Error Handling
**Priority:** P1 (High - Robustness)

**Requirement:** Invalid tier names must raise clear errors.

**Acceptance Criteria:**
```python
try:
    TierMapper.detect_system("invalid")
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "not recognized" in str(e)
```

**Check:** Error messages are informative

---

### TIER-008: Bidirectional Consistency
**Priority:** P1 (High - Data integrity)

**Requirement:** Round-trip conversions must preserve tier meaning.

**Acceptance Criteria:**
```python
# Spanish -> YAML -> Spanish should preserve meaning
original = "medio"
yaml = TierMapper.to_yaml_tier(original, TierSystem.SPANISH)
back = TierMapper.to_spanish(yaml, TierSystem.YAML)
assert back == original
```

**Check:** Bidirectional mappings are consistent

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **CC-006:** Explicit error handling ✅
- **CFG-002:** Environment variables used ✅ (via config)

### High Priority (P1)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **LOG-002:** Context in logs ✅

### Medium Priority (P2)
- **QL-001:** Complexity reasonable ✅
- **CC-007:** Small methods ✅

---

## Known Issues & Technical Debt

### Issues
1. **Hardcoded thresholds** - Should be entirely in config
2. **No institutional tier** - 5-tier system not fully supported
3. **Config coupling** - Tight coupling to strategy_config_loader

### Technical Debt
1. **Move all thresholds to config** - Remove hardcoded values
2. **Add 5-tier support** - Support micro, small, medium, large, institutional
3. **Decouple from config** - Make config optional with better defaults

---

## Testing Requirements

### Unit Tests
- [ ] Test capital-based tier determination
- [ ] Test system conversion accuracy
- [ ] Test capital flag mapping
- [ ] Test auto-detection
- [ ] Test error handling
- [ ] Test bidirectional consistency
- [ ] Test validation consistency

### Integration Tests
- [ ] Test with actual config files
- [ ] Test with InputProfile
- [ ] Test with investment_profiles.yaml

---

## Security Considerations

1. **No injection attacks** ✅ (enum validation)
2. **No sensitive data** ✅ (tier names only)
3. **Input validation** ✅ (tier validation)

---

## Performance Considerations

1. **Config loading** - Cached after first load ✅
2. **Mapping lookups** - O(1) dict lookups ✅
3. **Validation overhead** - Minimal ✅

---

## Dependencies

**External:**
- `logging` (stdlib)
- `decimal` (stdlib)
- `enum` (stdlib)
- `typing` (stdlib)

**Internal:**
- `app.core.config.strategy_config_loader` (get_strategy_config)

---

## Migration Notes

**From unmapped tiers:**
1. Identify all tier usage
2. Replace with TierMapper methods
3. Update config files
4. Test tier conversions

**To tier-mapped code:**
1. Import TierMapper
2. Use get_tier() for capital-based tiers
3. Use normalize_tier() for conversions
4. Validate tier consistency

---

## Changelog

### Version 1.0.0 (Initial)
- Unified tier mapping
- Multi-system support
- Capital-based tier determination
- Bidirectional conversion
- Validation and consistency checking

---

**Last Updated:** 2026-02-06  
**Next Review:** After 5-tier system implementation
