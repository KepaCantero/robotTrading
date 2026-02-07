# decimal_utils.py Requirements

**File:** `app/core/decimal_utils.py`  
**Purpose:** Decimal Utilities for Financial Calculations  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.290489

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **Financial Precision:** Decimal arithmetic for monetary values
- **Related Files:** All trading/financial calculation modules

---

## Purpose & Scope

This module provides utility functions for handling Decimal arithmetic in financial calculations to ensure precision and avoid floating-point errors. 

**Critical for Production:** Using float for financial calculations causes rounding errors that can lead to incorrect trading decisions and accounting issues.

---

## Functions

| Function | Purpose | Return Type |
|----------|---------|-------------|
| `to_decimal()` | Safe conversion to Decimal | `Optional[Decimal]` |
| `to_decimal_required()` | Convert to Decimal, error on None | `Decimal` |
| `safe_decimal_divide()` | Division with zero-check | `Optional[Decimal]` |
| `validate_price()` | Validate price range | `Decimal` |
| `validate_quantity()` | Validate quantity range | `Decimal` |
| `round_decimal()` | Round to precision | `Decimal` |
| `format_currency()` | Format as currency string | `str` |
| `calculate_percentage()` | Safe percentage calculation | `Optional[Decimal]` |
| `round_to_currency_precision()` | Round by currency | `Decimal` |
| `get_price_precision()` | Get precision for asset class | `int` |
| `round_price()` | Round price for asset class | `Decimal` |
| `validate_price_for_asset_class()` | Validate and round price | `Decimal` |

---

## File-Specific Requirements

### DEC-001: Float to Decimal Conversion Safety
**Priority:** P0 (Critical - Prevents precision loss)

**Requirement:** Float must be converted via string to avoid floating-point precision issues.

**Rationale:** `Decimal(0.1) != Decimal('0.1')` - the float 0.1 is actually 0.1000000000000000055511151231257827021181583404541015625

**Acceptance Criteria:**
```python
# Float conversion must use string representation
result = to_decimal(0.1)
assert result == Decimal("0.1")
assert str(result) == "0.1"
```

**Check:** Code converts float -> str -> Decimal

---

### DEC-002: Division By Zero Handling
**Priority:** P0 (Critical - Prevents crashes)

**Requirement:** All division operations must handle division by zero gracefully.

**Acceptance Criteria:**
```python
result = safe_decimal_divide("100", "0")
assert result is None  # Returns None, doesn't crash

result = safe_decimal_divide("100", "0", Decimal("0"))
assert result == Decimal("0")
```

**Check:** safe_decimal_divide() handles zero denominator

---

### DEC-003: Asset Class Precision
**Priority:** P0 (Critical - Trading accuracy)

**Requirement:** Prices must be rounded to correct precision for asset class (equity: 2, forex: 5, crypto: 8).

**Acceptance Criteria:**
```python
# Crypto needs 8 decimals
btc_price = round_price("1.08452712345678", "crypto", "BTC/USD")
assert btc_price == Decimal("1.08452712")

# Forex needs 5 decimals
forex_price = round_price("1.084527", "forex", "EUR/USD")
assert forex_price == Decimal("1.08453")

# Equity needs 2 decimals
stock_price = round_price("100.456", "equity")
assert stock_price == Decimal("100.46")
```

**Check:** round_price() uses correct precision

---

### DEC-004: Price Range Validation
**Priority:** P1 (High - Prevents invalid data)

**Requirement:** Prices must be within valid range for asset class.

**Acceptance Criteria:**
```python
# Equity: $0.01 - $1,000,000
validate_price_for_asset_class("0.001", "equity")  # Should fail
validate_price_for_asset_class("2000000", "equity")  # Should fail

# Crypto: $0.00000001 - $1,000,000
validate_price_for_asset_class("0.000000001", "crypto")  # Should fail
```

**Check:** Validation enforces min/max prices

---

### DEC-005: Currency Symbol Removal
**Priority:** P2 (Medium - Data cleaning)

**Requirement:** String conversion must remove currency symbols ($, €, £) and commas.

**Acceptance Criteria:**
```python
assert to_decimal("$1,234.56") == Decimal("1234.56")
assert to_decimal("€1.234,56") == Decimal("1234.56")  # European format
assert to_decimal("£1,000") == Decimal("1000")
```

**Check:** String cleaning removes symbols

---

### DEC-006: Forex Pair Precision
**Priority:** P1 (High - Trading accuracy)

**Requirement:** Forex pairs must use correct precision (JPY pairs: 2, others: 5).

**Acceptance Criteria:**
```python
# USD/JPY: 2 decimals
jpy_price = round_price("149.123", "forex", "USD/JPY")
assert jpy_price == Decimal("149.12")

# EUR/USD: 5 decimals
eur_price = round_price("1.084527", "forex", "EUR/USD")
assert eur_price == Decimal("1.08453")
```

**Check:** FOREX_PAIR_PRECISIONS dictionary

---

### DEC-007: Required Decimal Validation
**Priority:** P1 (High - Prevents None errors)

**Requirement:** to_decimal_required() must raise clear error on None.

**Acceptance Criteria:**
```python
try:
    to_decimal_required(None)
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "cannot be None" in str(e)
```

**Check:** Error message is clear

---

### DEC-008: Percentage Calculation Safety
**Priority:** P2 (Medium - Prevents errors)

**Requirement:** Percentage calculation must handle division by zero.

**Acceptance Criteria:**
```python
assert calculate_percentage("50", "100") == Decimal("50.00")
assert calculate_percentage("50", "0") is None
```

**Check:** Safe division used

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **TRD-005:** Price validation ✅
- **CC-006:** Explicit error handling ✅
- **Financial precision:** Decimal arithmetic ✅

### High Priority (P1)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **QL-001:** Complexity reasonable ✅

### Medium Priority (P2)
- **CC-003:** KISS principle ✅
- **CC-007:** Small functions ✅

---

## Known Issues & Technical Debt

### Issues
1. **No locale support** - European number formats (1.234,56) not fully supported
2. **Hardcoded limits** - Price limits should be configurable
3. **No negative price handling** - Short selling not supported

### Technical Debt
1. Add **locale-aware formatting** for international markets
2. Implement **configurable price limits** per broker
3. Add **negative quantity support** for short positions

---

## Testing Requirements

### Unit Tests
- [ ] Test float to Decimal conversion (precision preservation)
- [ ] Test division by zero handling
- [ ] Test asset class precision rounding
- [ ] Test price range validation
- [ ] Test currency symbol removal
- [ ] Test forex pair precision
- [ ] Test required Decimal validation
- [ ] Test percentage calculation

### Integration Tests
- [ ] Test with real market data from brokers
- [ ] Test rounding doesn't cause cumulative errors
- [ ] Test with high-frequency trading data

---

## Security Considerations

1. **No arithmetic overflow** ✅ (Decimal handles this)
2. **No injection attacks** ✅ (Pydantic would catch, but we use plain Decimal)
3. **Input validation** ✅ (price/quantity ranges)

---

## Performance Considerations

1. **Decimal vs float** - Decimal is slower but necessary for precision
2. **String conversion overhead** - Acceptable for safety
3. **Rounding operations** - Minimal overhead

---

## Dependencies

**External:**
- `decimal` (stdlib)
- `logging` (stdlib)
- `typing` (stdlib)

**Internal:**
- None (standalone module)

---

## Migration Notes

**From float-based code:**
1. Replace all float prices/quantities with Decimal
2. Use to_decimal() for all external data
3. Use round_price() for all price rounding
4. Never use float arithmetic in financial calculations

**To Decimal-based code:**
1. Audit all float usage
2. Replace with Decimal utilities
3. Test precision preservation
4. Monitor performance impact

---

## Changelog

### Version 1.0.0 (Initial)
- Decimal conversion utilities
- Asset class precision handling
- Safe division operations
- Price/quantity validation
- Currency formatting

---

**Last Updated:** 2026-02-06  
**Next Review:** After float migration complete
