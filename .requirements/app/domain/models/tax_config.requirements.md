# tax_config.py

## Purpose
Pydantic model defining tax optimization parameters based on investor's tax residence, referencing López de Prado's tax optimization principles.

---

## Type Definitions / Data Classes

### TaxConfig Class (Pydantic BaseModel)
```python
class TaxConfig(BaseModel):
    # Identification
    country_code: str                           # REQUIRED, len=2 - ISO 3166-1 alpha-2 country code
    base_currency: str = "EUR"                  # OPTIONAL - Base currency for calculations

    # Tax rates
    capital_gains_rate_short: Decimal           # REQUIRED, 0 <= x <= 1 - Short-term capital gains rate
    capital_gains_rate_long: Decimal            # REQUIRED, 0 <= x <= 1 - Long-term capital gains rate
    dividend_tax_rate: Decimal                  # REQUIRED, 0 <= x <= 1 - Dividend tax rate

    # Withholding tax optimization
    withholding_tax_domestic: Decimal = 0.00    # OPTIONAL, 0 <= x <= 1 - Domestic withholding rate
    withholding_tax_eu: Decimal = 0.00          # OPTIONAL, 0 <= x <= 1 - EU withholding rate
    withholding_tax_us: Decimal = 0.30          # OPTIONAL, 0 <= x <= 1 - US withholding rate (standard 30%)

    # Country-specific rules
    applies_wash_sale_rule: bool = False        # OPTIONAL - Whether wash sale rule applies (US-specific)
    allows_loss_carryforward: bool = True       # OPTIONAL - Whether losses can be carried forward
    loss_carryforward_years: Optional[int] = None # OPTIONAL, x >= 0 - Years losses can be carried forward

    # Optimization preferences
    prefer_long_term: bool = True               # OPTIONAL - Prefer long-term holdings for tax efficiency
    min_holding_period_days: Optional[int] = None # OPTIONAL, x >= 1 - Days to qualify for long-term rate

    # Currency hedging
    requires_currency_hedging: bool = False     # OPTIONAL - Whether currency hedging is recommended
    hedging_instruments: list[str] = []         # OPTIONAL - Available currency hedging instruments
```

**Model Config:**
- `strict=True` - Strict type checking
- `validate_assignment=True` - Validate on attribute assignment
- `extra="forbid"` - Forbid extra attributes (catch typos)

**Properties:**
- `has_long_term_advantage: bool` - True if long-term rate < short-term rate
- `long_term_advantage: Decimal` - Difference between short-term and long-term rates
- `is_tax_friendly: bool` - True if long-term gains < 20% and dividends < 20%

**Validation Rules:**
- `country_code` must be exactly 2 characters (ISO 3166-1 alpha-2)
- All tax rates must be between 0 and 1 (0-100%)
- `loss_carryforward_years` must be non-negative
- `min_holding_period_days` must be at least 1
- `hedging_instruments` defaults to empty list (not None)

---

## Function Signatures (Contracts)

### `TaxConfig.has_long_term_advantage` (property)
**Pre:** TaxConfig instance is valid
**Post:** Returns True if long-term rate < short-term rate
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `TaxConfig.long_term_advantage` (property)
**Pre:** TaxConfig instance is valid
**Post:** Returns tax advantage as Decimal (short_rate - long_rate)
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `TaxConfig.is_tax_friendly` (property)
**Pre:** TaxConfig instance is valid
**post:** Returns True if long-term gains < 20% and dividends < 20%
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

---

## Acceptance Criteria
- [ ] All Decimal fields use precise decimal arithmetic (no float)
- [ ] `extra="forbid"` prevents typos in field names
- [ ] `validate_assignment=True` ensures validation on all updates
- [ ] `country_code` validates length (exactly 2 characters)
- [ ] All tax rates are in range 0-1 (0-100%)
- [ ] `withholding_tax_us` defaults to 0.30 (standard US rate)
- [ ] `prefer_long_term` defaults to True (tax-efficient default)
- [ ] `hedging_instruments` defaults to empty list (mutable default handled correctly)
- [ ] Model is serializable to dict for logging

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | 08-configuration.md | Pydantic Settings for type-safe config | ✅ OK - Using Pydantic BaseModel |
| CFG-003 | 08-configuration.md | Validate all configuration values | ✅ OK - Field validation with ge/le/min_length |
| CFG-004 | 08-configuration.md | Extra forbid to catch typos | ✅ OK - extra="forbid" set |
| TYP-001 | 02-type-hints.md | All fields have type hints | ✅ OK - All fields typed |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ⚠️ CHECK - hedging_instruments uses default_factory |
| SEC-007 | 28-security-and-secrets.md | Input validation | ✅ OK - Field constraints validate inputs |

**NOTE:** `hedging_instruments: list[str] = Field(default_factory=list)` correctly uses `default_factory` instead of `[]` to avoid mutable default anti-pattern.

---

## Dependencies
- **External:** `decimal` (stdlib), `typing` (stdlib), `pydantic` (Pydantic 2.x)
- **Internal:** None

---

## Required Tests
- **test_tax_config.py:**
  - Test valid TaxConfig creation with all fields
  - Test country_code validation (exactly 2 characters)
  - Test capital_gains_rate_short validation (0 <= x <= 1)
  - Test capital_gains_rate_long validation (0 <= x <= 1)
  - Test dividend_tax_rate validation (0 <= x <= 1)
  - Test withholding_tax_us defaults to 0.30
  - Test prefer_long_term defaults to True
  - Test has_long_term_advantage when long_rate < short_rate
  - Test long_term_advantage calculates correct difference
  - Test is_tax_friendly when rates < 20%
  - Test applies_wash_sale_rule defaults to False
  - Test allows_loss_carryforward defaults to True
  - Test hedging_instruments defaults to empty list
  - Test extra="forbid" rejects unknown fields
  - Test validate_assignment=True works on updates
  - Test serialization to dict

---

## Notes
- Based on López de Prado's "Machine Learning for Asset Managers" (46-lopez-de-prado-machine-learning-asset-managers.md)
- Supports country-specific rules (wash sale, loss carryforward)
- Optimization preferences guide strategy selection for tax efficiency
- Currency hedging recommendations for international investors
