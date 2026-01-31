# tax_calculator.py

## Purpose
Domain service for calculating tax liabilities based on tax residence, holding periods, and trade characteristics. Supports capital gains tax calculations (short-term vs long-term), dividend tax, tax lot tracking, and tax-loss harvesting optimization.

---

## Type Definitions / Data Classes

### TaxLiability Class (DataClass)
```python
@dataclass
class TaxLiability:
    gross_profit: Decimal        # REQUIRED - Total profit before taxes
    taxable_profit: Decimal       # REQUIRED - Profit subject to tax (max(0, gross_profit))
    tax_rate: Decimal            # REQUIRED - Effective tax rate applied
    tax_amount: Decimal          # REQUIRED - Total tax liability
    net_profit: Decimal          # REQUIRED - Profit after taxes
    short_term_gains: Decimal    # REQUIRED - Gains from holdings < 365 days
    long_term_gains: Decimal     # REQUIRED - Gains from holdings >= 365 days
    short_term_tax: Decimal      # REQUIRED - Tax on short-term gains
    long_term_tax: Decimal       # REQUIRED - Tax on long-term gains
```

**Validation Rules:**
- All Decimal fields must be non-negative except gross_profit and net_profit
- tax_amount = short_term_tax + long_term_tax
- net_profit = gross_profit - tax_amount
- taxable_profit = short_term_gains + long_term_gains

### TaxLot Class (DataClass)
```python
@dataclass
class TaxLot:
    symbol: str                  # REQUIRED - Trading symbol/ticker
    quantity: Decimal           # REQUIRED - Number of shares/contracts
    cost_basis: Decimal         # REQUIRED - Original purchase price per unit
    acquisition_date: datetime  # REQUIRED - When position was acquired
    is_long_term: bool          # REQUIRED - True if held >= 365 days
```

**Validation Rules:**
- quantity must be > 0
- cost_basis must be > 0
- is_long_term = (current_date - acquisition_date).days >= 365

---

## Function Signatures (Contracts)

### `__init__(tax_residence: TaxResidence) -> None`
**Pre:** tax_residence is a valid TaxResidence value object with configured rates
**Post:** TaxCalculator instance initialized with residence configuration
**Raises:** None
**Retry:** No
**Side Effects:** None (state initialization only)

### `calculate_trade_tax(trade: Trade) -> TaxLiability`
**Pre:** trade is a completed Trade with valid entry_date, exit_date, and PnL
**Post:** Returns TaxLiability with appropriate short/long-term tax rates applied
**Raises:** None (defaults to 0 tax for invalid trades)
**Retry:** No
**Side Effects:** None (pure calculation)

### `calculate_period_tax(trades: List[Trade], start_date: datetime, end_date: datetime) -> TaxLiability`
**Pre:** trades is a list of completed Trades; start_date < end_date
**Post:** Returns aggregated TaxLiability for all trades in the date range
**Raises:** None (empty list returns zero liability)
**Retry:** No
**Side Effects:** None (pure calculation)

### `calculate_dividend_tax(dividend_amount: Decimal, source_region: str = "domestic") -> Decimal`
**Pre:** dividend_amount >= 0; source_region is valid region key
**Post:** Returns tax amount based on withholding rate for region
**Raises:** KeyError if source_region not configured in TaxResidence
**Retry:** No
**Side Effects:** None (pure calculation)

### `create_tax_lots_from_position(position: Position) -> List[TaxLot]`
**Pre:** position is valid with entry_date and quantity
**Post:** Returns list with one TaxLot representing the position
**Raises:** None
**Retry:** No
**Side Effects:** None (pure calculation)

### `optimize_tax_loss_harvesting(open_positions: List[Position], current_prices: Dict[str, Decimal]) -> List[str]`
**Pre:** open_positions has valid Position objects; current_prices has prices for position symbols
**Post:** Returns list of symbols recommended for tax-loss harvesting
**Raises:** None
**Retry:** No
**Side Effects:** None (pure calculation, analysis only)

### `estimate_year_end_tax(year_trades: List[Trade], open_positions: List[Position], current_prices: Dict[str, Decimal]) -> TaxLiability`
**Pre:** year_trades contains trades from the tax year; open_positions and current_prices are valid
**Post:** Returns estimated TaxLiability including realized and unrealized gains
**Raises:** IndexError if year_trades is empty (assumes current year)
**Retry:** No
**Side Effects:** None (pure calculation, estimation)

### `_is_long_term(trade: Trade) -> bool`
**Pre:** trade has exit_date
**Post:** Returns True if holding period >= 365 days
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] **AC-TAX-001:** All Trade calculations use correct tax rates based on holding period (short vs long-term)
- [ ] **AC-TAX-002:** TaxLiability calculations are mathematically consistent (tax_amount = short_term_tax + long_term_tax)
- [ ] **AC-TAX-003:** calculate_period_tax correctly filters trades by date range (inclusive bounds)
- [ ] **AC-TAX-004:** optimize_tax_loss_harvesting respects wash sale rule when configured (30-day restriction)
- [ ] **AC-TAX-005:** estimate_year_end_tax uses conservative short-term rate for unrealized gains
- [ ] **AC-TAX-006:** All monetary calculations use Decimal (no float precision errors)
- [ ] **AC-TAX-007:** create_tax_lots_from_position correctly determines long-term status (>= 365 days)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECIFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | BASE_RULES | Domain layer has no infrastructure dependencies | ✅ OK - Pure domain logic |
| ARCH-003 | BASE_RULES | No framework imports in domain (FastAPI, SQLAlchemy) | ✅ OK - Only stdlib |
| TYP-001 | BASE_RULES | 100% type coverage on all functions | ✅ OK - All typed |
| FMT-007 | BASE_RULES | No mutable defaults in function signatures | ✅ OK - No mutable defaults |
| CC-006 | BASE_RULES | Explicit error handling for edge cases | ⚠️ NOT APPLIED - Defaults gracefully |
| TRD-004 | BASE_RULES | Audit trail for trading operations | ❌ GAP - No logging of tax calculations |
| LOG-001 | BASE_RULES | Structured logging for tax decisions | ❌ GAP - No logging implemented |
| SEC-007 | BASE_RULES | Input validation at boundaries | ⚠️ NOT APPLIED - Domain service assumes valid entities |
| SOL-001 | BASE_RULES | Single Responsibility Principle | ✅ OK - Only tax calculations |
| SOL-005 | BASE_RULES | Dependency Inversion (inject TaxResidence) | ✅ OK - Constructor injection |

### Domain Service Specific Rules

| Rule ID | Rule | Priority | Status |
|---------|------|----------|--------|
| TAX-001 | Decimal precision required for all monetary calculations | **P0** | ✅ OK |
| TAX-002 | Holding period calculation uses exact days (365, not calendar year) | **P0** | ✅ OK |
| TAX-003 | Tax rates must be validated as percentages (0-1) | P1 | ⚠️ NOT APPLIED - Assumes VO validation |
| TAX-004 | Wash sale rule respects 30-day window (US-specific) | P1 | ✅ OK |
| TAX-005 | Tax-loss harvesting only recommends positions with unrealized losses | **P0** | ✅ OK |
| TAX-006 | Year-end estimation is conservative (assumes short-term rate) | P2 | ✅ OK |

---

## Dependencies
- **External:**
  - `dataclasses` (stdlib) - for TaxLiability, TaxLot
  - `decimal.Decimal` (stdlib) - for precise monetary calculations
  - `datetime` (stdlib) - for date calculations
  - `typing.List`, `typing.Optional`, `typing.Dict` (stdlib) - type hints
- **Internal:**
  - `app.domain.entities.trade.Trade`, `app.domain.entities.trade.ExitReason`
  - `app.domain.entities.position.Position`
  - `app.domain.value_objects.tax_residence.TaxResidence`

---

## Required Tests
- **tests/domain/services/test_tax_calculator.py:**
  - **Success paths:**
    - test_calculate_trade_tax_short_term: Confirms short-term capital gains rate applied
    - test_calculate_trade_tax_long_term: Confirms long-term capital gains rate applied
    - test_calculate_trade_tax_loss: Confirms losses result in 0 tax liability
    - test_calculate_period_tax_multiple_trades: Aggregates mixed short/long-term trades correctly
    - test_calculate_dividend_tax_domestic: Applies correct domestic withholding rate
    - test_calculate_dividend_tax_international: Applies correct international rate
    - test_create_tax_lots_from_position_short_term: Creates lot with is_long_term=False
    - test_create_tax_lots_from_position_long_term: Creates lot with is_long_term=True
    - test_optimize_tax_loss_harvesting_no_wash_sale: Recommends all losing positions
    - test_optimize_tax_loss_harvesting_with_wash_sale: Filters positions < 30 days old
    - test_estimate_year_end_tax_with_unrealized_gains: Includes unrealized gains in estimate
  - **Error paths:**
    - test_calculate_trade_tax_no_exit_date: Handles trades without exit gracefully
    - test_calculate_period_tax_empty_list: Returns zero liability for no trades
    - test_calculate_dividend_tax_invalid_region: Raises KeyError for unknown region
  - **Edge cases:**
    - test_is_long_term_exactly_365_days: Boundary test for long-term classification
    - test_is_long_term_364_days: Confirms 364 days is short-term
    - test_tax_liability_with_zero_profit: Returns zero tax amount
    - test_optimize_tax_loss_harvesting_missing_price: Skips positions without current price
    - test_estimate_year_end_tax_empty_trades: Handles empty trade list

---

## Notes
- **Critical:** Tax calculations vary significantly by jurisdiction. This service assumes TaxResidence value object encapsulates country-specific rules (US, Spain, etc.)
- **Holding Period:** Uses 365-day threshold for long-term classification (US standard). Other jurisdictions may require different thresholds.
- **Wash Sale Rule:** Currently implemented as 30-day restriction. May not apply to all tax residences.
- **Conservative Estimation:** Year-end estimates assume short-term rates for unrealized gains to avoid underestimating tax liability.
- **No Rounding:** All calculations use Decimal without rounding. Rounding should be applied at presentation layer if required by tax authority.
