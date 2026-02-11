# strategy_type.py

## Purpose
Enumeration of trading strategy types mapped to investment objectives based on academic research literature.

---

## Type Definitions / Data Classes

### StrategyType Class (Enum)
```python
class StrategyType(str, Enum):
    MOMENTUM = "momentum"              # REQUIRED - Trend following strategy (Gray & Vogel)
    DIVIDEND = "dividend"              # REQUIRED - Dividend investing (Berkin & Swedroe)
    LOW_VOLATILITY = "low_volatility"  # REQUIRED - Low volatility + Risk Parity (Markowitz)
    MULTI_FACTOR = "multi_factor"      # REQUIRED - Fama-French-Carhart factors
    COVERED_CALL = "covered_call"      # REQUIRED - Covered calls + income (Kissell)
```

**Properties:**
- `description: str` - Human-readable description with academic reference
- `requires_leverage: bool` - True if strategy typically requires leverage
- `is_defensive: bool` - True if strategy is defensive (capital preservation)

**Methods:**
- `__str__() -> str` - Returns enum value

**Validation Rules:**
- Inherits from `str` and `Enum` for JSON serialization
- All values are lowercase strings
- `requires_leverage` returns True for MULTI_FACTOR and COVERED_CALL
- `is_defensive` returns True for LOW_VOLATILITY and DIVIDEND

---

## Function Signatures (Contracts)

### `StrategyType.description` (property)
**Pre:** None
**Post:** Returns human-readable description with academic reference
**Raises:** KeyError if enum value not in descriptions dict (internal error)
**Retry:** N/A
**Side Effects:** None (read-only property)

### `StrategyType.requires_leverage` (property)
**Pre:** None
**Post:** Returns True if strategy typically requires leverage
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `StrategyType.is_defensive` (property)
**Pre:** None
**Post:** Returns True if strategy is defensive (capital preservation focus)
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

---

## Acceptance Criteria
- [ ] All enum values are lowercase strings for consistency
- [ ] Each strategy maps to exactly one investment objective
- [ ] Each strategy has academic research reference in docstring
- [ ] `requires_leverage` correctly identifies leverage-dependent strategies
- [ ] `is_defensive` correctly identifies capital preservation strategies
- [ ] Enum is JSON serializable (inherits from str)

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-003 | 05-architecture.md | Domain has no framework dependencies | ✅ OK - Pure enum, no imports |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK - Properties typed |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK - Clear naming |
| TRD-003 | BASE_RULES.md | Position limits enforcement | ⚠️ NOT APPLIED - Enum only, no enforcement |
| TRD-004 | BASE_RULES.md | Audit trail | ⚠️ NOT APPLIED - Enum only, no operations |

**NOTE:** This is a pure domain enum with no behavior requiring trading-specific rules.

---

## Dependencies
- **External:** `enum` (stdlib)
- **Internal:** None

---

## Required Tests
- **test_strategy_type.py:**
  - Test all enum values are accessible
  - Test description property returns correct references
  - Test requires_leverage returns True for MULTI_FACTOR and COVERED_CALL
  - Test is_defensive returns True for LOW_VOLATILITY and DIVIDEND
  - Test enum is JSON serializable (inherits from str)
  - Test __str__ returns value

---

## Notes
- Academic references are documented in module docstring for traceability
- Enum inheritance from `str` enables direct JSON serialization
- Strategy-to-objective mapping is documented but not enforced (enforcement in use cases)
