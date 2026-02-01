# decimal_utils.py

## Purpose
Decimal arithmetic utilities for precise financial calculations avoiding floating-point rounding errors in trading system.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### Global Precision Configuration
```python
# Decimal context settings
getcontext().prec = 28                    # Sufficient for most financial calculations
getcontext().rounding = ROUND_HALF_UP     # Standard banking rounding

# Currency precision mappings
CURRENCY_PRECISIONS: Dict[str, int] = {
    "USD": 2,   # US Dollar
    "EUR": 2,   # Euro
    "GBP": 2,   # British Pound
    "JPY": 0,   # Japanese Yen (no decimal)
    "BTC": 8,   # Bitcoin (Satoshi precision)
    "ETH": 18,  # Ethereum (Wei precision)
}

# Asset class precisions
ASSET_CLASS_PRECISIONS: Dict[str, int] = {
    "equity": 2,     # Stocks: 2 decimal places (e.g., $150.25)
    "forex": 5,     # Forex pairs: up to 5 decimal places
    "crypto": 8,    # Crypto pairs: up to 8 decimal places
    "commodity": 2, # Commodities: 2 decimal places
    "bond": 4,      # Bonds: 4 decimal places
    "index": 2,     # Indices: 2 decimal places
}

# Forex pair specific precisions
FOREX_PAIR_PRECISIONS: Dict[str, int] = {
    # Japanese Yen pairs: 2 decimals
    "USD/JPY": 2, "EUR/JPY": 2, "GBP/JPY": 2,
    # All other major pairs: 4-5 decimals
    "EUR/USD": 5, "GBP/USD": 5, "USD/CHF": 5,
}

# Crypto pair specific precisions
CRYPTO_PAIR_PRECISIONS: Dict[str, int] = {
    "BTC/USD": 8, "BTC/EUR": 8,
    "ETH/USD": 8, "ETH/BTC": 8,
    "SAT/BTC": 8,      # 1 BTC = 100,000,000 SAT
    "SHIB/USD": 8,
}
```

**Validation Rules:**
- All financial calculations use Decimal (not float)
- Decimal precision is 28 digits (sufficient for all trading calculations)
- Rounding mode is ROUND_HALF_UP (standard banking practice)
- Float conversion must go through string to avoid precision loss
- Asset class specific precisions must be used for price rounding

---

## Function Signatures (Contracts)

### `to_decimal(value: Union[int, float, str, Decimal, None]) -> Optional[Decimal]`
**Pre:** value is numeric, numeric string, or None
**Post:** Returns Decimal representation or None if input is None
**Raises:** ValueError if value cannot be converted, InvalidOperation for invalid strings
**Retry:** ❌ No
**Side Effects:** None (pure conversion function)

**Critical Behavior:**
- Float conversion: `Decimal(str(value))` NOT `Decimal(value)` to avoid precision loss
- String cleaning: Removes currency symbols ($, €, £) and commas
- None returns None (not Decimal(0))

### `to_decimal_required(value: Union[int, float, str, Decimal]) -> Decimal`
**Pre:** value is numeric or numeric string (not None)
**Post:** Returns Decimal representation
**Raises:** ValueError if value is None or cannot be converted
**Retry:** ❌ No
**Side Effects:** None

### `safe_decimal_divide(numerator: Union[int, float, str, Decimal], denominator: Union[int, float, str, Decimal], default: Optional[Decimal] = None) -> Optional[Decimal]`
**Pre:** numerator and denominator are numeric
**Post:** Returns division result as Decimal, or default if division by zero
**Raises:** ❌ No (returns default on error)
**Retry:** ❌ No
**Side Effects:** Logs warning on error

### `validate_price(value: Union[int, float, str, Decimal], min_value: Decimal = Decimal("0.01"), max_value: Decimal = Decimal("1000000")) -> Decimal`
**Pre:** value is numeric, min_value <= max_value
**Post:** Returns validated Decimal price within bounds
**Raises:** ValueError if price outside valid bounds or cannot be converted
**Retry:** ❌ No
**Side Effects:** None

### `validate_quantity(value: Union[int, float, str, Decimal], min_value: Decimal = Decimal("0.001"), max_value: Decimal = Decimal("1000000000")) -> Decimal`
**Pre:** value is numeric
**Post:** Returns validated Decimal quantity within bounds
**Raises:** ValueError if quantity outside valid bounds or cannot be converted
**Retry:** ❌ No
**Side Effects:** None

### `round_decimal(value: Union[int, float, str, Decimal], precision: int, rounding: str = ROUND_HALF_UP) -> Decimal`
**Pre:** value is numeric, precision >= 0
**Post:** Returns Decimal rounded to specified precision
**Raises:** ValueError if value cannot be converted
**Retry:** ❌ No
**Side Effects:** None

### `format_currency(value: Union[int, float, str, Decimal], symbol: str = "$") -> str`
**Pre:** value is numeric
**Post:** Returns formatted currency string with symbol and 2 decimals
**Raises:** ValueError if value cannot be converted
**Retry:** ❌ No
**Side Effects:** None

### `calculate_percentage(numerator: Union[int, float, str, Decimal], denominator: Union[int, float, str, Decimal], precision: int = 2) -> Optional[Decimal]`
**Pre:** numerator and denominator are numeric
**Post:** Returns percentage as Decimal (multiplied by 100), or None if division by zero
**Raises:** ❌ No (returns None on error)
**Retry:** ❌ No
**Side Effects:** None

### `round_to_currency_precision(value: Union[int, float, str, Decimal], currency: str = "USD") -> Decimal`
**Pre:** value is numeric, currency is valid key in CURRENCY_PRECISIONS
**Post:** Returns Decimal rounded to currency precision
**Raises:** ValueError if value cannot be converted
**Retry:** ❌ No
**Side Effects:** None

### `get_price_precision(asset_class: str = "equity", symbol: Optional[str] = None) -> int`
**Pre:** asset_class is valid key in ASSET_CLASS_PRECISIONS
**Post:** Returns number of decimal places for price precision
**Raises:** ValueError if asset_class is unknown
**Retry:** ❌ No
**Side Effects:** None

### `round_price(value: Union[int, float, str, Decimal], asset_class: str = "equity", symbol: Optional[str] = None, rounding: str = ROUND_HALF_UP) -> Decimal`
**Pre:** value is numeric, asset_class is valid
**Post:** Returns Decimal price rounded to appropriate precision
**Raises:** ValueError if asset_class is unknown or value cannot be converted
**Retry:** ❌ No
**Side Effects:** None

**Critical:** This is the PRIMARY function for price rounding in the system. NEVER use round(price, 2) directly - it breaks Forex and Crypto precision.

### `validate_price_for_asset_class(value: Union[int, float, str, Decimal], asset_class: str = "equity", symbol: Optional[str] = None) -> Decimal`
**Pre:** value is numeric, asset_class is valid
**Post:** Returns validated and rounded Decimal price
**Raises:** ValueError if price is invalid or asset_class is unknown
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] **AC-DEC-001**: All financial calculations use Decimal (not float)
- [ ] **AC-DEC-002**: Float conversion uses Decimal(str(value)) not Decimal(value)
- [ ] **AC-DEC-003**: Decimal context precision is 28 digits
- [ ] **AC-DEC-004**: Rounding mode is ROUND_HALF_UP (banking standard)
- [ ] **AC-DEC-005**: Currency symbols removed from string conversion ($, €, £)
- [ ] **AC-DEC-006**: Asset class specific precisions used (equity=2, forex=5, crypto=8)
- [ ] **AC-DEC-007**: Forex pair specific precisions respected (USD/JPY=2, EUR/USD=5)
- [ ] **AC-DEC-008**: Crypto pair specific precisions respected (SAT/BTC=8)
- [ ] **AC-DEC-009**: Division by zero returns default value (not raise)
- [ ] **AC-DEC-010**: Price validation enforces minimum by asset class
- [ ] **AC-DEC-011**: round_price() is PRIMARY function for price rounding (never use round())
- [ ] **AC-DEC-012**: All functions have type hints (TYP-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Financial precision with Decimal | ✅ OK - All functions use Decimal |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear function names |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Specific ValueError with context |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - No mutable defaults |
| LOG-003 | BASE_RULES | Appropriate log levels | ✅ OK - warning used for division errors |

### Financial-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| FIN-001 | NEVER use float for monetary calculations | ✅ OK - Decimal used everywhere |
| FIN-002 | Convert float via string to avoid precision loss | ✅ OK - Decimal(str(value)) used |
| FIN-003 | Use ROUND_HALF_UP for financial rounding | ✅ OK - Configured in getcontext() |
| FIN-004 | Asset class specific price precisions | ✅ OK - ASSET_CLASS_PRECISIONS defined |
| FIN-005 | Symbol-specific precisions for forex/crypto | ✅ OK - FOREX_PAIR_PRECISIONS and CRYPTO_PAIR_PRECISIONS |
| FIN-006 | Minimum price validation by asset class | ✅ OK - validate_price_for_asset_class() |

---

## Dependencies
- **External:** `decimal` (standard library), `logging`
- **Internal:** None (pure utility module)

---

## Required Tests
- **test_decimal_utils.py:**
  - Success: to_decimal() converts strings, ints, floats correctly
  - Success: to_decimal() returns None for None input
  - Success: to_decimal() removes currency symbols ($100 → 100)
  - Success: to_decimal() removes commas (1,234.56 → 1234.56)
  - Success: to_decimal_required() raises ValueError for None
  - Success: Float conversion preserves precision (via string)
  - Success: safe_decimal_divide() returns result for valid division
  - Success: safe_decimal_divide() returns default for division by zero
  - Success: validate_price() accepts prices within range
  - Error: validate_price() raises ValueError for price < min_value
  - Error: validate_price() raises ValueError for price > max_value
  - Success: validate_quantity() accepts quantities within range
  - Success: round_decimal() rounds correctly with ROUND_HALF_UP
  - Success: format_currency() formats with symbol and commas
  - Success: calculate_percentage() returns percentage multiplied by 100
  - Success: calculate_percentage() returns None for division by zero
  - Success: round_to_currency_precision() rounds correctly for each currency
  - Success: get_price_precision() returns correct precision for asset classes
  - Success: get_price_precision() returns symbol-specific precision for forex
  - Success: get_price_precision() returns symbol-specific precision for crypto
  - Error: get_price_precision() raises ValueError for unknown asset_class
  - Success: round_price() rounds equity to 2 decimals
  - Success: round_price() rounds EUR/USD to 5 decimals
  - Success: round_price() rounds USD/JPY to 2 decimals
  - Success: round_price() rounds SAT/BTC to 8 decimals
  - Success: validate_price_for_asset_class() validates and rounds correctly
  - Edge: Very small crypto prices (0.00000001) handled
  - Edge: Very large prices (1M+) handled
  - Edge: Negative values rejected by validation
  - Type: All functions have return type hints

---

## Notes
- **CRITICAL FOR FINANCIAL CALCULATIONS** - Floating-point errors accumulate in trading systems
- Always use Decimal for money, prices, quantities
- The PRIMARY price rounding function is `round_price()` - NEVER use `round(price, 2)` directly
- Forex pairs have different precisions (JPY pairs: 2 decimals, others: 5 decimals)
- Crypto pairs require up to 8 decimals (Satoshi precision for BTC)
- Float conversion must use `Decimal(str(value))` to avoid precision loss (0.1 is not exactly representable in binary floating-point)
- Decimal context precision of 28 is sufficient for all trading calculations
- ROUND_HALF_UP is the standard banking rounding mode
