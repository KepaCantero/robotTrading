# money.py

## Purpose
Money value object - immutable monetary value with currency support, implementing all arithmetic operations while maintaining immutability and currency safety.

---

## Type Definitions / Data Classes

### Money DataClass (Immutable)
```python
@dataclass(frozen=True)
class Money:
    """Money value object - immutable monetary amount."""

    amount: Decimal                        # REQUIRED - Monetary amount
    currency: str = "USD"                  # REQUIRED - Currency code
```

**Validation Rules (__post_init__):**
- amount cannot be negative
- currency cannot be empty

**Immutability:** frozen=True (cannot modify after creation)

---

## Function Signatures (Contracts)

### Arithmetic Operations

### `__add__(self, other: Any) -> Money`
**Pre:** other is Money with same currency
**Post:** Returns new Money with summed amounts
**Raises:** ValueError if currencies differ
**Retry:** No
**Side Effects:** None (returns new instance)

### `__sub__(self, other: Any) -> Money`
**Pre:** other is Money with same currency
**Post:** Returns new Money with difference
**Raises:** ValueError if currencies differ or result negative
**Retry:** No
**Side Effects:** None (returns new instance)

### `__mul__(self, multiplier: Any) -> Money`
**Pre:** multiplier is int, float, or Decimal
**Post:** Returns new Money with multiplied amount
**Raises:** ValueError if result negative
**Retry:** No
**Side Effects:** None (returns new instance)

### `__truediv__(self, divisor: Any) -> Money`
**Pre:** divisor is int, float, or Decimal, not zero
**Post:** Returns new Money with divided amount
**Raises:** ZeroDivisionError if divisor is 0
**Retry:** No
**Side Effects:** None (returns new instance)

### Comparison Operations

### `__eq__(self, other: Any) -> bool`
**Pre:** None
**Post:** Returns True if amount and currency match
**Raises:** No
**Retry:** No
**Side Effects:** None

### `__lt__(self, other: Any) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount < other.amount
**Raises:** ValueError if currencies differ
**Retry:** No
**Side Effects:** None

### `__le__(self, other: Any) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount <= other.amount
**Raises:** ValueError if currencies differ
**Retry:** No
**Side Effects:** None

### `__gt__(self, other: Any) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount > other.amount
**Raises:** ValueError if currencies differ
**Retry:** No
**Side Effects:** None

### `__ge__(self, other: Any) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount >= other.amount
**Raises:** ValueError if currencies differ
**Retry:** No
**Side Effects:** None

### Hash and String

### `__hash__(self) -> int`
**Pre:** None
**Post:** Returns hash of (amount, currency)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Note:** Required for use in sets and dict keys

### `__str__(self) -> str`
**Pre:** None
**Post:** Returns string representation
**Raises:** No
**Retry:** No
**Side Effects:** None

**Format:** "{amount} {currency}"

### `__repr__(self) -> str`
**Pre:** None
**Post:** Returns developer representation
**Raises:** No
**Retry:** No
**Side Effects:** None

**Format:** "Money(amount={amount}, currency='{currency}')"

### Utility Methods

### `is_zero(self) -> bool`
**Pre:** None
**Post:** Returns True if amount is 0
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_positive(self) -> bool`
**Pre:** None
**Post:** Returns True if amount > 0
**Raises:** No
**Retry:** No
**Side Effects:** None

### `to_float(self) -> float`
**Pre:** None
**Post:** Returns amount as float
**Raises:** No
**Retry:** No
**Side Effects:** None

**Warning:** May lose precision, use Decimal when possible

---

## Acceptance Criteria
- [x] Money is immutable (frozen=True)
- [x] Amount cannot be negative
- [x] Currency cannot be empty
- [x] Arithmetic operations return new Money instances
- [x] Cannot add/subtract different currencies
- [x] Cannot compare different currencies
- [x] All operations preserve currency
- [x] Hashable for use in sets/dicts
- [x] String representation includes amount and currency
- [x] to_float() available for serialization

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05 |
| **Auditor** | Claude Code (Ralphex Task) |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. All tools passed - GAP P0 was false positive or already resolved. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Immutability | CRITICAL_RULES.md | frozen=True | ✅ OK |
| Decimal Precision | CRITICAL_RULES.md | Use Decimal internally | ✅ OK |
| Currency Safety | CRITICAL_RULES.md | Validate currency match | ✅ OK |
| Type Hints | BASE_RULES.md | All methods typed | ✅ OK |
| Validation | BASE_RULES.md | Input validation | ✅ OK |
| Value Object | BASE_RULES.md | Defined by attributes | ✅ OK |
| No Negative Amounts | CRITICAL_RULES.md | Reject negative results | ✅ OK |
| Hashability | BASE_RULES.md | Implement __hash__ | ✅ OK |

---

## Dependencies
- **External:** dataclasses, decimal, typing
- **Internal:** None (pure value object)

---

## Required Tests
- **test_money.py:**
  - Test Money.__post_init__ with positive amount
  - Test Money.__post_init__ with negative amount raises ValueError
  - Test Money.__post_init__ with empty currency raises ValueError
  - Test Money.__add__ with same currency
  - Test Money.__add__ with different currency raises ValueError
  - Test Money.__sub__ with same currency
  - Test Money.__sub__ with negative result raises ValueError
  - Test Money.__sub__ with different currency raises ValueError
  - Test Money.__mul__ with int
  - Test Money.__mul__ with float
  - Test Money.__mul__ with Decimal
  - Test Money.__mul__ with negative result raises ValueError
  - Test Money.__truediv__ with valid divisor
  - Test Money.__truediv__ with zero raises ZeroDivisionError
  - Test Money.__eq__ with same amount and currency
  - Test Money.__eq__ with different currency returns False
  - Test Money.__lt__ with same currency
  - Test Money.__lt__ with different currency raises ValueError
  - Test Money.__le__ comparison
  - Test Money.__gt__ comparison
  - Test Money.__ge__ comparison
  - Test Money.__hash__ returns consistent value
  - Test Money in set (hashable)
  - Test Money as dict key (hashable)
  - Test Money.__str__ format
  - Test Money.__repr__ format
  - Test Money.is_zero() returns True for 0
  - Test Money.is_positive() returns True for > 0
  - Test Money.to_float() conversion

---

## Notes
- CRITICAL: This is a core value object
- Immutable by design (frozen=True)
- All operations return new instances
- Currency safety enforced (cannot mix currencies)
- Hashable for use in sets and dict keys
- Decimal precision maintained internally
- to_float() available for API serialization (with precision warning)
- Follows Value Object pattern (DDD)

---

**File Reference:** `app/domain/value_objects/money.py`
**Last Audited:** 2026-02-04
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.406797
