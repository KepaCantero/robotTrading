# tax_calculator.py

## Purpose
Domain service for calculating tax liabilities based on tax residence, holding period (short/long term), and trade characteristics with structured audit logging.

---

## Type Definitions / Data Classes

### TaxLiability (dataclass)
```python
gross_profit: Decimal        # Total profit before tax
taxable_profit: Decimal      # Profit subject to tax
tax_rate: Decimal            # Effective tax rate applied
tax_amount: Decimal          # Total tax liability
net_profit: Decimal          # Profit after tax
short_term_gains: Decimal    # Short-term capital gains
long_term_gains: Decimal     # Long-term capital gains
short_term_tax: Decimal      # Tax on short-term gains
long_term_tax: Decimal       # Tax on long-term gains
```

### TaxLot (dataclass)
```python
symbol: str                  # Asset symbol
quantity: Decimal            # Number of shares
cost_basis: Decimal          # Purchase cost
acquisition_date: datetime   # Purchase date
is_long_term: bool           # Whether held > 365 days
```

### TaxCalculator (class)
```python
_tax_residence: TaxResidence  # Tax configuration (country, rates)
LONG_TERM_HOLDING_DAYS: int = 365  # Days for long-term classification
```

---

## Function Signatures (Contracts)

### `TaxCalculator.__init__(tax_residence)`
**Pre:** tax_residence is valid TaxResidence
**Post:** Calculator initialized with tax rules
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_trade_tax(trade) -> TaxLiability`
**Pre:** trade is completed Trade with entry_date, exit_date, pnl
**Post:** Returns TaxLiability with calculated taxes
**Raises:** None
**Retry:** No
**Side Effects:** Logs tax calculation with all details (TRD-004, LOG-001)

### `calculate_period_tax(trades, start_date, end_date) -> TaxLiability`
**Pre:** trades is list of Trade objects
**Post:** Returns aggregated TaxLiability for period
**Raises:** None
**Retry:** No
**Side Effects:** Logs period tax calculation (TRD-004, LOG-001)

### `calculate_dividend_tax(dividend_amount, source_region) -> Decimal`
**Pre:** dividend_amount >= 0, source_region valid
**Post:** Returns tax amount on dividend
**Raises:** None
**Retry:** No
**Side Effects:** Logs dividend tax (TRD-004, LOG-001)

### `create_tax_lots_from_position(position) -> List[TaxLot]`
**Pre:** position has symbol, quantity, cost_basis, entry_date
**Post:** Returns list of TaxLot objects
**Raises:** None
**Retry:** No
**Side Effects:** None

### `optimize_tax_loss_harvesting(open_positions, current_prices) -> List[str]`
**Pre:** open_positions have unrealized PnL, current_prices provided
**Post:** Returns list of symbols recommended for harvesting
**Raises:** None
**Retry:** No
**Side Effects:** Logs analysis and candidates (TRD-004, LOG-001)

### `estimate_year_end_tax(year_trades, open_positions, current_prices) -> TaxLiability`
**Pre:** year_trades from current year, positions with prices
**Post:** Returns estimated TaxLiability including unrealized gains
**Raises:** None
**Retry:** No
**Side Effects:** Logs estimation (TRD-004, LOG-001)

### `_is_long_term(trade) -> bool`
**Pre:** trade has exit_date
**Post:** Returns True if held >= 365 days
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Long-term classification: holding_days >= 365
- [ ] Short-term rate applied to holdings < 365 days
- [ ] Long-term rate applied to holdings >= 365 days
- [ ] Tax calculation: tax_amount = profit * tax_rate
- [ ] Short-term and long-term gains tracked separately
- [ ] Period tax aggregates all trades in date range
- [ ] Dividend tax uses withholding rate by region
- [ ] Tax lots track cost basis and acquisition date
- [ ] Tax-loss harvesting identifies unrealized losses
- [ ] Wash sale rule: 30-day waiting period applied if applicable
- [ ] Year-end estimate includes unrealized gains (conservative: short-term rate)
- [ ] All tax calculations logged with structured data (TRD-004, LOG-001)
- [ ] Log includes: trade_id, symbol, profit, holding_period, rates, amounts

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-004 | BASE_RULES | Audit trail for tax calculations | ✅ OK - All calculations logged |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All operations logged with context |
| LOG-003 | BASE_RULES | Appropriate log levels | ✅ OK - debug/info/error used appropriately |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |
| TYP-001 | BASE_RULES | Type hints | ✅ OK - Full type coverage |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Each method handles one tax scenario |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - No exceptions raised, graceful handling |

---

## Dependencies
- **External:** logging, dataclasses, decimal, datetime, typing
- **Internal:**
  - app.domain.entities.trade (Trade, ExitReason)
  - app.domain.entities.position (Position)
  - app.domain.value_objects.tax_residence (TaxResidence)

---

## Required Tests
- **test_tax_calculator.py:**
  - Trade tax calculation (short-term)
  - Trade tax calculation (long-term)
  - Trade tax calculation with loss (no tax)
  - Period tax calculation with multiple trades
  - Period tax filters by date range
  - Dividend tax calculation (domestic)
  - Dividend tax calculation (foreign)
  - Tax lot creation from position
  - Tax lot long-term classification
  - Tax-loss harvesting identifies losses
  - Tax-loss harvesting applies wash sale rule
  - Tax-loss harvesting when wash sale disabled
  - Year-end tax estimation with realized gains
  - Year-end tax estimation with unrealized gains
  - Year-end tax uses conservative short-term rate
  - Holding period calculation
  - Long-term classification (365 days)
  - Structured logging for all calculations
  - Log includes all required fields
  - TaxResidence rate lookups

---

## Notes
Tax Calculator is domain service with pure business logic. All tax rules configured via TaxResidence value object. Comprehensive logging required for audit compliance. No external dependencies (no database, no APIs).
