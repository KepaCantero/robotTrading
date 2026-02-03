# investment_horizon.py

## Purpose
InvestmentHorizon Value Object - Time period for investments with categorization and risk tolerance assessment.

---

## Type Definitions / Data Classes

### HorizonCategory (str, Enum)
```python
class HorizonCategory(str, Enum):
    VERY_SHORT_TERM = "very_short_term"    # < 6 months
    SHORT_TERM = "short_term"              # 6-12 months
    MEDIUM_TERM = "medium_term"            # 1-3 years
    LONG_TERM = "long_term"                # 3-10 years
    VERY_LONG_TERM = "very_long_term"      # > 10 years
```

### InvestmentHorizon (frozen=True)
```python
@dataclass(frozen=True)
class InvestmentHorizon:
    months: int                             # REQUIRED - Investment horizon in months
```

**Properties:**
- Immutable (frozen=True)
- Value object (defined by months, no identity)

**Invariants (enforced in __post_init__):**
- `months` > 0
- `months` <= 600 (50 years maximum)

**Category Thresholds:**
- **VERY_SHORT_TERM:** < 6 months
- **SHORT_TERM:** 6-11 months
- **MEDIUM_TERM:** 12-35 months (1-3 years)
- **LONG_TERM:** 36-119 months (3-10 years)
- **VERY_LONG_TERM:** >= 120 months (10+ years)

---

## Function Signatures (Contracts)

### `InvestmentHorizon.__post_init__() -> None`
**Pre:** None
**Post:** Horizon validated
**Raises:** `ValueError` if months <= 0 or months > 600
**Retry:** No
**Side Effects:** None (validation only)

### `years (property) -> float`
**Pre:** None
**Post:** Returns months / 12 rounded to 2 decimal places
**Raises:** None
**Retry:** No
**Side Effects:** None (property getter)

**Formula:** `years = round(months / 12, 2)`

### `category (property) -> HorizonCategory`
**Pre:** None
**Post:** Returns appropriate HorizonCategory based on months
**Raises:** None
**Retry:** No
**Side Effects:** None (property getter)

**Category Mapping:**
| Months | Category |
|--------|----------|
| < 6 | VERY_SHORT_TERM |
| 6-11 | SHORT_TERM |
| 12-35 | MEDIUM_TERM |
| 36-119 | LONG_TERM |
| >= 120 | VERY_LONG_TERM |

### `is_short_term (property) -> bool`
**Pre:** None
**Post:** Returns True if months < 12
**Raises:** None
**Retry:** No
**Side Effects:** None (property getter)

### `is_long_term (property) -> bool`
**Pre:** None
**Post:** Returns True if months > 36
**Raises:** None
**Retry:** No
**Side Effects:** None (property getter)

### `allows_high_risk() -> bool`
**Pre:** None
**Post:** Returns True if months >= 12 (1 year or more)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Risk Principle:** Horizons >= 12 months can tolerate volatility and higher-risk strategies

### `allows_very_high_risk() -> bool`
**Pre:** None
**Post:** Returns True if months >= 36 (3 years or more)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Risk Principle:** Only very long horizons (3+ years) should use aggressive/very high-risk strategies

### `InvestmentHorizon.from_months(months: int) -> InvestmentHorizon` (classmethod)
**Pre:** months > 0
**Post:** Returns InvestmentHorizon with specified months
**Raises:** `ValueError` if months <= 0 or > 600
**Retry:** No
**Side Effects:** None (factory method)

### `InvestmentHorizon.from_years(years: int | float) -> InvestmentHorizon` (classmethod)
**Pre:** years > 0
**Post:** Returns InvestmentHorizon with months = years × 12
**Raises:** `ValueError` if result <= 0 or > 600
**Retry:** No
**Side Effects:** None (factory method)

**Conversion:** 1 year → 12 months, 2.5 years → 30 months

### `InvestmentHorizon.__str__() -> str`
**Pre:** None
**Post:** Returns "X months" if < 12, "X years" otherwise
**Raises:** None
**Retry:** No
**Side Effects:** None (string conversion)

### `InvestmentHorizon.__repr__() -> str`
**Pre:** None
**Post:** Returns "InvestmentHorizon(months=X, category='...')"
**Raises:** None
**Retry:** No
**Side Effects:** None (debug representation)

---

## Acceptance Criteria
- [ ] **AC-001:** months must be positive (> 0)
- [ ] **AC-002:** months must be <= 600 (50 years max)
- [ ] **AC-003:** years property returns months / 12
- [ ] **AC-004:** category < 6 months = VERY_SHORT_TERM
- [ ] **AC-005:** category 6-11 months = SHORT_TERM
- [ ] **AC-006:** category 12-35 months = MEDIUM_TERM
- [ ] **AC-007:** category 36-119 months = LONG_TERM
- [ ] **AC-008:** category >= 120 months = VERY_LONG_TERM
- [ ] **AC-009:** is_short_term = months < 12
- [ ] **AC-010:** is_long_term = months > 36
- [ ] **AC-011:** allows_high_risk = months >= 12
- [ ] **AC-012:** allows_very_high_risk = months >= 36
- [ ] **AC-013:** from_years() converts correctly
- [ ] **AC-014:** Value object is immutable (frozen=True)
- [ ] **AC-015:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (InvestmentHorizon Value Object):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Value object | DDD (Evans) | Immutable, no identity | ✅ OK - frozen=True |
| Positive horizon | Risk management | months > 0 | ✅ OK - __post_init__ |
| Maximum horizon | Risk management | <= 600 months (50 years) | ✅ OK - __post_init__ |
| Category classification | Risk management | 5 categories | ✅ OK - category property |
| Very short term | Risk management | < 6 months | ✅ OK - Category |
| Short term | Risk management | 6-12 months | ✅ OK - Category |
| Medium term | Risk management | 1-3 years | ✅ OK - Category |
| Long term | Risk management | 3-10 years | ✅ OK - Category |
| Very long term | Risk management | > 10 years | ✅ OK - Category |
| High risk threshold | Risk management | >= 12 months | ✅ OK - allows_high_risk() |
| Very high risk threshold | Risk management | >= 36 months | ✅ OK - allows_very_high_risk() |
| Years conversion | Time math | months / 12 | ✅ OK - years property |
| Factory methods | Clean code | from_months/from_years | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and standard investment risk management principles.

---

## Dependencies
- **External:** `dataclasses` (std), `enum` (std), `typing` (std)
- **Internal:** None (value object)

---

## Required Tests
- **test_investment_horizon_value_object.py:**
  - `test_create_valid_horizon()` - Valid horizon created
  - `test_zero_months()` - Raises ValueError
  - `test_negative_months()` - Raises ValueError
  - `test_exceeds_max_months()` - Raises ValueError ( > 600)
  - `test_years_property()` - Returns months / 12
  - `test_category_very_short_term()` - < 6 months
  - `test_category_short_term()` - 6-11 months
  - `test_category_medium_term()` - 12-35 months
  - `test_category_long_term()` - 36-119 months
  - `test_category_very_long_term()` - >= 120 months
  - `test_category_boundaries()` - Boundary values (6, 12, 36, 120)
  - `test_is_short_term_true()` - < 12 months
  - `test_is_short_term_false()` - >= 12 months
  - `test_is_long_term_true()` - > 36 months
  - `test_is_long_term_false()` - <= 36 months
  - `test_allows_high_risk_true()` - >= 12 months
  - `test_allows_high_risk_false()` - < 12 months
  - `test_allows_very_high_risk_true()` - >= 36 months
  - `test_allows_very_high_risk_false()` - < 36 months
  - `test_from_months()` - Creates from months
  - `test_from_years_int()` - Converts years to months
  - `test_from_years_float()` - Converts decimal years to months
  - `test_str_months()` - "X months" if < 12
  - `test_str_years()` - "X years" if >= 12
  - `test_repr_representation()` - "InvestmentHorizon(...)"
  - `test_immutability()` - Cannot modify after creation

---

## Notes
- **Critical:** InvestmentHorizon is a VALUE OBJECT (immutable, defined by months, no identity)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Value Object pattern
- **Frozen Dataclass:** @dataclass(frozen=True) ensures immutability
- **Horizon Range:** 1 month to 600 months (50 years) - practical limits for trading strategies
- **Years Property:** Converts months to years with 2 decimal place precision
- **Category Classification:** 5 categories based on standard investment horizons
- **Risk Tolerance:**
  - **Very Short Term (< 6 months):** Very low risk tolerance (capital preservation)
  - **Short Term (6-12 months):** Low risk tolerance
  - **Medium Term (1-3 years):** Moderate risk tolerance (allows_high_risk = True)
  - **Long Term (3-10 years):** High risk tolerance (allows_very_high_risk = True)
  - **Very Long Term (> 10 years):** Maximum risk tolerance
- **allows_high_risk():** Returns True for horizons >= 12 months (can tolerate volatility)
- **allows_very_high_risk():** Returns True for horizons >= 36 months (can use aggressive strategies)
- **Factory Methods:**
  - from_months(): Create directly from months
  - from_years(): Convert years to months (handles int and float)
- **String Representation:** Displays in months if < 12, otherwise in years
- **Usage Pattern:** InvestmentHorizon determines appropriate risk levels, strategy selection, and portfolio allocation

---

## GAP Fixes Applied

### GAP-001: Unused Import (FIXED ✅)
**Issue:** Line 11 imported `Any` from `typing` module but never used it in the code.

**Fix Applied (2026-02-04):**
- Removed `from typing import Any` import statement

**Validation:**
```bash
python -m py_compile app/domain/value_objects/investment_horizon.py ✓ PASSED
```

**Impact:** None - cleanup of unused import per BASE_RULES FMT-003 (no unused imports).

---

**File Reference:** `app/domain/value_objects/investment_horizon.py`
**Last Audited:** 2026-02-01
**Last GAP Fix:** 2026-02-04
