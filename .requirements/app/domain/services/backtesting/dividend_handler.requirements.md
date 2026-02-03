# dividend_handler.py

## Purpose
Handles dividend payments and dividend reinvestment (DRIP) in backtesting including regular/special dividends, tax withholding, and portfolio dividend yield calculations following Lopez de Prado's advances in financial machine learning.

---

## Type Definitions / Data Classes

### DividendType Enum
```python
class DividendType(str, Enum):
    REGULAR = "regular"      # Regular quarterly dividend
    SPECIAL = "special"      # One-time special dividend
    FINAL = "final"          # Final dividend before liquidation
    INTERIM = "interim"      # Interim dividend
    STOCK = "stock"          # Stock dividend
```
**Validation Rules:** Must be one of the five defined dividend types

### DividendReinvestmentStrategy Enum
```python
class DividendReinvestmentStrategy(str, Enum):
    REINVEST = "reinvest"        # Reinvest all dividends
    CASH = "cash"                # Keep dividends as cash
    THRESHOLD = "threshold"      # Reinvest only above threshold
    MANUAL = "manual"            # Manual reinvestment
```
**Validation Rules:** Must be one of the four defined strategies

### DividendPayment DataClass
```python
@dataclass
class DividendPayment:
    symbol: str                      # REQUIRED - Trading symbol
    ex_date: date                    # REQUIRED - Ex-dividend date
    record_date: date                # REQUIRED - Record date
    payable_date: date               # REQUIRED - Payment date
    amount_per_share: Decimal        # REQUIRED - Dividend per share
    dividend_type: DividendType      # REQUIRED - Type of dividend
    frequency: Optional[int] = None  # OPTIONAL - Payments per year (4=quarterly)
```
**Validation Rules:**
- `amount_per_share` must be >= 0
- `payable_date` >= `ex_date` >= `record_date`
- `frequency` in [1, 2, 4, 12] if provided

### DividendPayment.annualized_amount -> Decimal
**Post:** Returns amount_per_share * frequency
**Post:** Defaults to quarterly (* 4) if frequency is None

### DividendReinvestment DataClass
```python
@dataclass
class DividendReinvestment:
    symbol: str                    # REQUIRED - Symbol reinvested in
    reinvestment_date: date        # REQUIRED - Date of reinvestment
    dividend_amount: Decimal       # REQUIRED - Amount reinvested
    shares_purchased: Decimal      # REQUIRED - Shares acquired
    price_per_share: Decimal       # REQUIRED - Price at reinvestment
    fractional_shares: bool = True # OPTIONAL - Whether fractional allowed
```
**Validation Rules:**
- `dividend_amount` >= 0
- `shares_purchased` >= 0
- `price_per_share` > 0

---

## Function Signatures (Contracts)

### `DividendHandler.__init__(reinatement_strategy, reinvestment_threshold, fractional_shares, tax_withholding_rate)`
**Pre:** reinvestment_threshold >= 0, tax_withholding_rate in [0, 1]
**Post:** Handler initialized with specified reinvestment strategy
**Raises:** None
**Retry:** No
**Side Effects:** Initializes internal dividend and reinvestment tracking

### `DividendHandler.add_dividend(dividend) -> None`
**Pre:** dividend is valid DividendPayment
**Post:** Dividend added to tracking for symbol
**Raises:** None
**Side Effects:** Appends dividend to internal _dividends dict

### `DividendHandler.get_dividend(symbol, as_of_date) -> Optional[DividendPayment]`
**Pre:** symbol is valid string, as_of_date is valid date
**Post:** Returns most recent dividend before as_of_date or None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `DividendHandler.calculate_dividend_yield(symbol, current_price, as_of_date) -> float`
**Pre:** current_price > 0, as_of_date valid
**Post:** Returns dividend yield as percentage (e.g., 0.04 = 4%)
**Formula:** annualized_amount / current_price
**Raises:** None (returns 0.0 if no dividend or zero price)
**Retry:** No
**Side Effects:** None

### `DividendHandler.process_dividend_payment(symbol, quantity, payment_date, current_price) -> Tuple[Decimal, Optional[DividendReinvestment]]`
**Pre:** quantity >= 0, current_price > 0
**Post:** Returns (net_dividend, reinvestment_info) tuple
**Post:** Net dividend = gross * (1 - tax_withholding_rate)
**Post:** Reinvests if strategy matches and threshold met
**Raises:** None
**Side Effects:** May add reinvestment to _reinvestments list

### `DividendHandler._reinvest_dividend(symbol, dividend_amount, reinvestment_date, price) -> DividendReinvestment`
**Pre:** dividend_amount >= 0, price >= 0
**Post:** Returns DividendReinvestment with shares calculated
**Post:** If fractional_shares: shares = amount / price
**Post:** If not fractional: shares = amount // price
**Post:** If price is 0: shares_purchased = 0
**Raises:** None
**Retry:** No
**Side Effects:** Appends reinvestment to _reinvestments list

### `DividendHandler.calculate_annual_dividend_income(positions, prices, as_of_date) -> Decimal`
**Pre:** positions dict has quantities >= 0, prices dict has values > 0
**Post:** Returns sum of annual dividend income from all positions
**Formula:** sum(annualized_amount * quantity for each position)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `DividendHandler.calculate_portfolio_dividend_yield(positions, prices, as_of_date) -> float`
**Pre:** positions and prices dicts are valid and non-empty
**Post:** Returns portfolio dividend yield as percentage
**Formula:** total_annual_dividends / total_portfolio_value
**Raises:** None (returns 0.0 if total_value is 0)
**Retry:** No
**Side Effects:** None

### `DividendHandler.estimate_next_dividend_date(symbol, as_of_date) -> Optional[date]`
**Pre:** symbol valid, as_of_date valid
**Post:** Returns estimated next ex-dividend date or None
**Post:** Uses frequency to calculate days between payments
**Post:** Defaults to 91 days (quarterly) if no frequency
**Raises:** None
**Retry:** No
**Side Effects:** None

### `DividendHandler.get_dividend_history(symbol, start_date, end_date) -> List[DividendPayment]`
**Pre:** start_date <= end_date
**Post:** Returns list of dividends in date range (inclusive)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `DividendHandler.calculate_dividend_growth_rate(symbol, years) -> float`
**Pre:** years >= 1, symbol has dividend history
**Post:** Returns annualized dividend growth rate (CAGR)
**Post:** Returns 0.0 if less than 8 dividends (2 years quarterly)
**Formula:** (newest/oldest)^(1/periods) - 1, then * 4 to annualize
**Raises:** None
**Retry:** No
**Side Effects:** None

### `DividendHandler.get_total_reinvested() -> Decimal`
**Pre:** None
**Post:** Returns sum of all dividend amounts reinvested
**Raises:** None
**Retry:** No
**Side Effects:** None

### `DividendHandler.get_total_shares_from_reinvestment(symbol) -> Decimal`
**Pre:** symbol is valid string
**Post:** Returns total shares acquired from DRIP for symbol
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-DIV-001: DividendPayment.annualized_amount defaults to quarterly (*4)
- [ ] AC-DIV-002: Tax withholding applied to gross dividends
- [ ] AC-DIV-003: REINVEST strategy always reinvests dividends
- [ ] AC-DIV-004: THRESHOLD strategy only reinvests above threshold
- [ ] AC-DIV-005: Fractional shares allow exact amount/price calculation
- [ ] AC-DIV-006: Non-fractional uses integer division (amount // price)
- [ ] AC-DIV-007: Zero price results in zero shares purchased
- [ ] AC-DIV-008: calculate_dividend_yield returns 0.0 for no dividend
- [ ] AC-DIV-009: Portfolio yield returns 0.0 for zero total value
- [ ] AC-DIV-010: Dividend growth rate returns 0.0 with insufficient data
- [ ] AC-DIV-011: Next dividend date estimated using frequency
- [ ] AC-DIV-012: Default 91 days between dividends (quarterly)

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

**Reglas universales:** See `../../BASE_RULES.md` for 96+ universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-011 | papers/lopez-de-prado | Dividends significantly affect total return | ✅ OK |
| ARCH-003 | BASE_RULES | Domain has no framework dependencies | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Safe calculations |
| LOG-004 | BASE_RULES | Error logging | ⚠️ NOT APPLIED - Pure functions |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - All defaults are immutable |

---

## Dependencies
- **External:** None (std lib only)
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/domain/services/backtesting/test_dividend_handler.py:**
  - Test add_dividend and get_dividend retrieval
  - Test DividendPayment.annualized_amount with/without frequency
  - Test calculate_dividend_yield with valid dividend
  - Test calculate_dividend_yield returns 0.0 for no dividend
  - Test process_dividend_payment with REINVEST strategy
  - Test process_dividend_payment with THRESHOLD strategy
  - Test process_dividend_payment with CASH strategy
  - Test tax withholding applied correctly
  - Test fractional shares reinvestment
  - Test non-fractional shares (integer division)
  - Test zero price returns zero shares
  - Test calculate_annual_dividend_income for multiple positions
  - Test calculate_portfolio_dividend_yield
  - Test estimate_next_dividend_date with frequency
  - Test estimate_next_dividend_date defaults to 91 days
  - Test calculate_dividend_growth_rate CAGR calculation
  - Test calculate_dividend_growth_rate with insufficient data
  - Test get_total_reinvested aggregation
  - Test get_total_shares_from_reinvestment per symbol

---

## Notes
Reference: Lopez de Prado, M. "Advances in Financial Machine Learning" - Dividends are critical component of total return that must be included in realistic backtesting. DRIP can compound returns significantly over time.
