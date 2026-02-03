# position.py.requirements.md

**Layer:** Domain Layer  
**Category:** Entity  
**Status:** PASSED  
**Last Updated:** 2025-01-06

---

## Purpose

Represents a holding in a portfolio with entry/exit information and P&L calculations.

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

### `PositionSide`

*Description needed*

### `PositionStatus`

*Description needed*

### `Position`

*Description needed*

---

## Functions

### `__init__`

*Description needed*

### `_validate`

*Description needed*

### `avg_price`

*Description needed*

### `get_pnl`

*Description needed*

### `get_quantity`

*Description needed*

### `get_current_price`

*Description needed*

### `get_value`

*Description needed*

### `get_cost_basis`

*Description needed*

### `get_unrealized_pnl_amount`

*Description needed*

### `get_unrealized_pnl`

*Description needed*

### `get_realized_pnl_amount`

*Description needed*

### `get_realized_pnl`

*Description needed*

### `get_pnl_percent`

*Description needed*

### `update_price`

*Description needed*

### `add_shares`

*Description needed*

### `remove_shares`

*Description needed*

### `is_stop_loss_hit`

*Description needed*

### `is_take_profit_hit`

*Description needed*

### `get_risk_reward_ratio`

*Description needed*

### `get_age_days`

*Description needed*

### `is_open`

*Description needed*

### `is_closed`

*Description needed*

### `is_profitable`

*Description needed*

### `create_long`

*Description needed*

### `create_short`

*Description needed*

### `to_dict`

*Description needed*

### `__str__`

*Description needed*

---

## GAP Analysis

### Automated Checks

- **File Path:** `/Users/kepa.cantero/Projects/algoTrading/app/domain/entities/position.py`
- **Total Lines:** 480
- **Has Imports:** True
- **Uses Dataclass:** True
- **Frozen Dataclass:** False
- **Has Logging:** False
- **Has Validation:** True
- **Uses Decimal:** True
- **Uses Datetime:** True
- **Has Enums:** False

### Priority Gaps

#### P0 (Critical) - None ✅

No P0 violations found.

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
grep -E "from sqlalchemy|from fastapi|import httpx" app/domain/app/domain/entities/position.py | wc -l
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
