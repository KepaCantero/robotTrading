# money.py

## Purpose
Money Value Object - Immutable monetary value with currency support and arithmetic operations.

---

## Type Definitions / Data Classes

### Money (frozen=True)
```python
@dataclass(frozen=True)
class Money:
    amount: Decimal               # REQUIRED - Monetary amount (non-negative)
    currency: str                 # Default: "USD" - Currency code
```

**Properties:**
- Immutable (frozen=True)
- Value object (defined by amount and currency, no identity)
- Supports arithmetic operations (+, -, *, /)
- Supports comparisons (<, <=, >, >=, ==)
- Hashable (can be used in sets and dicts)

**Invariants (enforced in __post_init__):**
- `amount` >= 0 (cannot be negative)
- `currency` must be non-empty

---

## Function Signatures (Contracts)

### `Money.__post_init__() -> None`
**Pre:** None
**Post:** Money validated
**Raises:** `ValueError` if amount < 0 or currency is empty
**Retry:** No
**Side Effects:** None (validation only)

### `Money.__add__(other) -> Money`
**Pre:** other is Money with same currency
**Post:** Returns new Money with amount = self.amount + other.amount
**Raises:** `ValueError` if currencies differ
**Retry:** No
**Side Effects:** None (returns new Money)

### `Money.__sub__(other) -> Money`
**Pre:** other is Money with same currency
**Post:** Returns new Money with amount = self.amount - other.amount
**Raises:** `ValueError` if currencies differ or result < 0
**Retry:** No
**Side Effects:** None (returns new Money)

### `Money.__mul__(multiplier) -> Money`
**Pre:** multiplier is int, float, or Decimal
**Post:** Returns new Money with amount = self.amount × multiplier
**Raises:** `ValueError` if result < 0
**Retry:** No
**Side Effects:** None (returns new Money)

### `Money.__truediv__(divisor) -> Money`
**Pre:** divisor is non-zero int, float, or Decimal
**Post:** Returns new Money with amount = self.amount / divisor
**Raises:** `ZeroDivisionError` if divisor = 0
**Retry:** No
**Side Effects:** None (returns new Money)

### `Money.__eq__(other) -> bool`
**Pre:** None
**Post:** Returns True if other is Money AND amount equal AND currency equal
**Raises:** None
**Retry:** No
**Side Effects:** None (pure comparison)

### `Money.__lt__(other) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount < other.amount
**Raises:** `ValueError` if currencies differ
**Retry:** No
**Side Effects:** None (pure comparison)

### `Money.__le__(other) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount <= other.amount
**Raises:** `ValueError` if currencies differ
**Retry:** No
**Side Effects:** None (pure comparison)

### `Money.__gt__(other) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount > other.amount
**Raises:** `ValueError` if currencies differ
**Retry:** No
**Side Effects:** None (pure comparison)

### `Money.__ge__(other) -> bool`
**Pre:** other is Money with same currency
**Post:** Returns True if self.amount >= other.amount
**Raises:** `ValueError` if currencies differ
**Retry:** No
**Side Effects:** None (pure comparison)

### `Money.__hash__() -> int`
**Pre:** None
**Post:** Returns hash of (amount, currency)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure function)

### `Money.__str__() -> str`
**Pre:** None
**Post:** Returns "{amount} {currency}"
**Raises:** None
**Retry:** No
**Side Effects:** None (string conversion)

### `Money.__repr__() -> str`
**Pre:** None
**Post:** Returns "Money(amount={amount}, currency='{currency}')"
**Raises:** None
**Retry:** No
**Side Effects:** None (debug representation)

### `is_zero() -> bool`
**Pre:** None
**Post:** Returns True if amount == 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_positive() -> bool`
**Pre:** None
**Post:** Returns True if amount > 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `to_float() -> float`
**Pre:** None
**Post:** Returns amount as float
**Raises:** None
**Retry:** No
**Side Effects:** None (type conversion)

---

## Acceptance Criteria
- [ ] **AC-001:** amount must be non-negative (>= 0)
- [ ] **AC-002:** currency must be non-empty
- [ ] **AC-003:** Cannot add different currencies
- [ ] **AC-004:** Cannot subtract different currencies
- [ ] **AC-005:** Cannot compare different currencies
- [ ] **AC-006:** Subtraction cannot result in negative amount
- [ ] **AC-007:** Division by zero raises ZeroDivisionError
- [ ] **AC-008:** Value object is immutable (frozen=True)
- [ ] **AC-009:** Hashable for use in sets/dicts
- [ ] **AC-010:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Money Value Object):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Value object | DDD (Evans) | Immutable, no identity | ✅ OK - frozen=True |
| Non-negative amount | Money standard | amount >= 0 | ✅ OK - __post_init__ |
| Currency required | Money standard | currency non-empty | ✅ OK - __post_init__ |
| Addition | Money arithmetic | Returns new Money | ✅ OK - __add__ |
| Subtraction | Money arithmetic | Returns new Money, no negative | ✅ OK - __sub__ |
| Multiplication | Money arithmetic | Returns new Money | ✅ OK - __mul__ |
| Division | Money arithmetic | Returns new Money | ✅ OK - __truediv__ |
| Currency mismatch | Money standard | Error on mixed currency ops | ✅ OK - Validated |
| Comparison | Money standard | Full comparison support | ✅ OK - __lt__, __le__, __gt__, __ge__ |
| Equality | Value object | amount + currency equality | ✅ OK - __eq__ |
| Hashable | Value object | Can use in sets/dicts | ✅ OK - __hash__ |
| is_zero() | Money utility | Check zero amount | ✅ OK - Implemented |
| is_positive() | Money utility | Check positive amount | ✅ OK - Implemented |
| to_float() | Type conversion | Float conversion | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and DDD (Evans 2003) for value object patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `decimal` (std), `typing` (std)
- **Internal:** None (value object)

---

## Required Tests
- **test_money_value_object.py:**
  - `test_create_valid_money()` - Valid money created
  - `test_negative_amount()` - Raises ValueError
  - `test_empty_currency()` - Raises ValueError
  - `test_add_same_currency()` - Returns new Money
  - `test_add_different_currency()` - Raises ValueError
  - `test_sub_same_currency()` - Returns new Money
  - `test_sub_different_currency()` - Raises ValueError
  - `test_sub_negative_result()` - Raises ValueError
  - `test_mul_int()` - Multiplies by int
  - `test_mul_float()` - Multiplies by float
  - `test_mul_decimal()` - Multiplies by Decimal
  - `test_div_int()` - Divides by int
  - `test_div_zero()` - Raises ZeroDivisionError
  - `test_eq_same_values()` - True
  - `test_eq_different_amount()` - False
  - `test_eq_different_currency()` - False
  - `test_comparison_operators()` - <, <=, >, >= work
  - `test_comparison_different_currency()` - Raises ValueError
  - `test_hashable()` - Can use in set/dict
  - `test_is_zero_true()` - amount == 0
  - `test_is_zero_false()` - amount > 0
  - `test_is_positive_true()` - amount > 0
  - `test_is_positive_false()` - amount == 0
  - `test_to_float()` - Returns float
  - `test_str_representation()` - "100.00 USD"
  - `test_repr_representation()` - "Money(amount=...)"
  - `test_immutability()` - Cannot modify attributes
  - `test_add_returns_new()` - Original unchanged

---

## Notes
- **Critical:** Money is a VALUE OBJECT (immutable, defined by amount and currency, no identity)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Value Object pattern
- **Frozen Dataclass:** @dataclass(frozen=True) ensures immutability
- **Non-Negative Amount:** Money cannot be negative (use signed amounts or separate tracking for liabilities)
- **Currency:** ISO 4217 currency code (USD, EUR, GBP, etc.)
- **Value Object Equality:** Two Money instances are equal if both amount AND currency are equal
- **Arithmetic Operations:** All operations return new Money instances (original is unchanged)
- **Currency Safety:** Arithmetic and comparisons only work with same currency (raises ValueError otherwise)
- **Addition:** Money + Money = Money (same currency)
- **Subtraction:** Money - Money = Money (same currency, result must be non-negative)
- **Multiplication:** Money × scalar = Money (int, float, or Decimal)
- **Division:** Money / scalar = Money (divisor must be non-zero)
- **Comparisons:** Full rich comparison support (<, <=, >, >=) for same currency
- **Hashable:** Implements __hash__ so Money can be used in sets and as dict keys
- **String Representations:** __str__ for display, __repr__ for debugging
- **Utility Methods:** is_zero(), is_positive(), to_float() for common checks
- **Type Conversion:** to_float() converts Decimal to float (be aware of precision loss)
- **Default Currency:** USD is default if not specified
- **Usage Pattern:** Money is used throughout the domain for monetary values to avoid using raw Decimal/float

---

**File Reference:** `app/domain/value_objects/money.py`
**Last Audited:** 2026-02-01
