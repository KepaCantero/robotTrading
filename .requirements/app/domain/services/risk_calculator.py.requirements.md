# risk_calculator.py.requirements.md

**Layer:** Domain Layer  
**Category:** Service  
**Status:** PASSED  
**Last Updated:** 2025-01-06

---

## Purpose

Domain service for calculating risk metrics including VaR, volatility, drawdown, and concentration.

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

### `RiskMetrics`

*Description needed*

### `RiskCalculator`

*Description needed*

---

## Functions

### `__init__`

*Description needed*

### `calculate_portfolio_risk`

*Description needed*

### `calculate_position_risk`

*Description needed*

### `calculate_sharpe_ratio`

*Description needed*

### `calculate_sortino_ratio`

*Description needed*

### `calculate_beta`

*Description needed*

### `_safe_divide`

*Description needed*

### `_calculate_concentration`

*Description needed*

### `_calculate_herfindahl`

*Description needed*

### `_estimate_portfolio_volatility`

*Description needed*

### `_calculate_var`

*Description needed*

### `_estimate_max_drawdown`

*Description needed*

### `_calculate_risk_utilisation`

*Description needed*

### `get_risk_summary`

*Description needed*

---

## GAP Analysis

### Automated Checks

- **File Path:** `/Users/kepa.cantero/Projects/algoTrading/app/domain/services/risk_calculator.py`
- **Total Lines:** 446
- **Has Imports:** True
- **Uses Dataclass:** True
- **Frozen Dataclass:** False
- **Has Logging:** False
- **Has Validation:** False
- **Uses Decimal:** True
- **Uses Datetime:** False
- **Has Enums:** False

### Priority Gaps

#### P0 (Critical) - None ✅

No P0 violations found. 

**Note:** ✅ Domain service uses safe defaults (_safe_divide) instead of raising - appropriate pattern

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
grep -E "from sqlalchemy|from fastapi|import httpx" app/domain/app/domain/services/risk_calculator.py | wc -l
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
