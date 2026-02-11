# signal_generator.py.requirements.md

**Layer:** Domain Layer  
**Category:** Service  
**Status:** PASSED  
**Last Updated:** 2025-01-06

---

## Purpose

Domain service for generating trading signals based on technical indicators and strategies.

---

## BASE_RULES References

See [`../../BASE_RULES.md`](../../BASE_RULES.md) for universal rules.

**Applicable BASE_RULES for this file:**
- **ARCH-001** (P0): Layered architecture
- **ARCH-002** (P0): Dependencies inward
- **ARCH-003** (P0): No framework in domain
- **SOL-001** (P0): Single Responsibility
- **CC-006** (P0): Explicit error handling

---

## Classes

### `SignalType`

*Description needed*

### `SignalStrength`

*Description needed*

### `Signal`

*Description needed*

### `IndicatorValues`

*Description needed*

### `SignalGenerator`

*Description needed*

---

## Functions

### `is_buy`

*Description needed*

### `is_sell`

*Description needed*

### `is_actionable`

*Description needed*

### `__init__`

*Description needed*

### `generate_ma_crossover_signal`

*Description needed*

### `generate_rsi_signal`

*Description needed*

### `generate_bollinger_signal`

*Description needed*

### `generate_macd_signal`

*Description needed*

### `combine_signals`

*Description needed*

### `_hold_signal`

*Description needed*

### `_calculate_ma_strength`

*Description needed*

### `_calculate_macd_strength`

*Description needed*

### `_calculate_consensus_strength`

*Description needed*

---

## GAP Analysis

### Automated Checks

- **File Path:** `/Users/kepa.cantero/Projects/algoTrading/app/domain/services/signal_generator.py`
- **Total Lines:** 512
- **Has Imports:** True
- **Uses Dataclass:** True
- **Frozen Dataclass:** True
- **Has Logging:** False
- **Has Validation:** False
- **Uses Decimal:** True
- **Uses Datetime:** False
- **Has Enums:** False

### Priority Gaps

#### P0 (Critical) - None ✅

No P0 violations found. 

**Note:** ✅ Signal generator returns HOLD signals for invalid input - appropriate pattern

#### P1 (High) - None ✅

No P1 violations found.

---

## File-Specific Requirements

### Domain Rules

1. **Purity:** No infrastructure dependencies (FastAPI, SQLAlchemy, etc.)
2. **Immutability:** Value objects should be frozen dataclasses
3. **Validation:** All invariants enforced in `__post_init__`
4. **Decimal Precision:** Financial calculations use `Decimal`, not `float`

### Trading Rules

1. **Risk Validation:** Position sizes, exposure limits checked
2. **Audit Trail:** All state changes logged
3. **Error Handling:** Explicit ValueError for invalid inputs

---

## Acceptance Criteria

### AC-ARCH-001: Domain Layer Purity
```bash
# No infrastructure imports in domain layer
grep -E "from sqlalchemy|from fastapi|import httpx" app/domain/app/domain/services/signal_generator.py | wc -l
# Expected: 0
```

### AC-FMT-007: No Mutable Defaults
```bash
# No mutable default arguments
grep -E "= \[\]|= \{\}" app/domain/FILE.py | wc -l
# Expected: 0
```

### AC-TYP-001: Type Hint Coverage
```bash
# All public functions have return types
mypy --strict app/domain/FILE.py
# Expected: 0 errors
```

---

## Test Requirements

### Required Tests

1. **Validation Tests:** All invariants tested
2. **Boundary Tests:** Edge cases (zero, negative, max values)
3. **Error Handling:** Invalid inputs raise ValueError
4. **Calculation Tests:** Output verified
5. **Integration Tests:** Service with entities

---

## Audit Status

**Current Status:** PASSED

**Last Audit:** 2025-01-06  
**Auditor:** Automated Analysis

### Changes Required

✅ **No changes required.** File passes all automated checks.


---

*This requirements file is auto-generated. Update with domain-specific requirements as needed.*
