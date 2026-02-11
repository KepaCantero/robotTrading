# tax_optimizer.py

## Purpose
Tax Optimization Service - Provides tax optimization strategies based on jurisdiction including tax lot accounting (FIFO, LIFO, HIFO), tax loss harvesting, dividend tax optimization, and wash sale avoidance.

---

## Type Definitions / Data Classes

### TaxMethod (str, Enum)
```python
class TaxMethod(str, Enum):
    FIFO = "fifo"        # First In, First Out
    LIFO = "lifo"        # Last In, First Out
    HIFO = "hifo"        # Highest In, First Out (minimizes taxes)
    MIN_TAX = "min_tax"  # Minimize current tax liability
    MAX_TAX = "max_tax"  # Maximize current tax liability (tax loss harvesting)
```

### TaxJurisdiction (str, Enum)
```python
class TaxJurisdiction(str, Enum):
    SPAIN = "spain"
    USA = "usa"
    UK = "uk"
    GERMANY = "germany"
    FRANCE = "france"
    DEFAULT = "default"
```

### TaxLot
```python
@dataclass
class TaxLot:
    """A single tax lot for position tracking."""
    lot_id: str
    symbol: str
    quantity: Decimal
    acquisition_date: date
    acquisition_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    holding_period_days: int

    @property
    def is_long_term(self) -> bool:
        """Check if lot qualifies for long-term treatment."""
        return self.holding_period_days >= 365

    @property
    def realized_pnl(self) -> Decimal:
        """Calculate realized P&L if sold now."""
        return (self.current_price - self.acquisition_price) * self.quantity
```

### TaxCalculation
```python
@dataclass
class TaxCalculation:
    """Tax calculation result."""
    short_term_gains: Decimal      # Short-term capital gains
    long_term_gains: Decimal       # Long-term capital gains
    dividend_income: Decimal       # Dividend income
    short_term_tax: Decimal        # Tax on short-term gains
    long_term_tax: Decimal         # Tax on long-term gains
    dividend_tax: Decimal          # Tax on dividends
    total_tax: Decimal             # Total tax liability
    effective_tax_rate: float      # Effective tax rate
    tax_los_harvesting_opportunity: Decimal  # Losses available to harvest
```

### TaxOptimizer
```python
class TaxOptimizer:
    """
    Tax optimization service.

    Provides tax optimization strategies based on jurisdiction:
    - Tax lot accounting (FIFO, LIFO, HIFO, Min Tax)
    - Tax loss harvesting
    - Dividend tax optimization
    - Wash sale avoidance

    Reference: López de Prado tax optimization techniques
    """
```

**Class Constants (initialized in __init__):**
- `_tax_rates: Dict[TaxJurisdiction, Dict]` - Tax rates by jurisdiction
- `_wash_sale_periods: Dict[TaxJurisdiction, int]` - Wash sale periods by jurisdiction

**Spain Rates:** short_term=28%, long_term=21%, dividend=19%
**USA Rates:** short_term=35%, long_term=15%, dividend=15%
**UK Rates:** short_term=20%, long_term=10%, dividend=8.75%

---

## Function Signatures (Contracts)

### `TaxOptimizer.__init__() -> None`
**Pre:** None
**Post:** Tax optimizer initialized with jurisdiction-specific rates
**Raises:** None
**Retry:** No
**Side Effects:** Initializes tax rates and wash sale periods

**Jurisdictions Supported:** Spain, USA, UK, Germany, France, Default

### `TaxOptimizer.configure_for_residence(country: str) -> Dict[str, Any]`
**Pre:** country is non-empty string
**Post:** Returns tax configuration for residence
**Raises:** None (defaults to DEFAULT jurisdiction)
**Retry:** No
**Side Effects:** None (pure computation)

**Output:**
```python
{
    "jurisdiction": str,
    "short_term_rate": float,
    "long_term_rate": float,
    "dividend_rate": float,
    "withholding_rate": float,
    "tax_method": TaxMethod,
    "wash_sale_period": int
}
```

**Default Methods:**
- USA: HIFO (minimize taxes)
- Spain/UK: FIFO (common in Europe)
- Other: FIFO

### `TaxOptimizer.calculate_tax_liability(
    tax_lots: List[TaxLot],
    sold_quantity: Decimal,
    sale_price: Decimal,
    jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
    method: TaxMethod = TaxMethod.FIFO,
) -> Tuple[TaxCalculation, List[TaxLot]]`
**Pre:** tax_lots non-empty; sold_quantity > 0; sale_price > 0
**Post:** Returns (TaxCalculation, remaining_lots)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Process Flow:**
1. Select lots to sell via `_select_lots()`
2. Calculate short-term and long-term gains
3. Apply tax rates based on jurisdiction
4. Handle losses (tax loss harvesting)
5. Return TaxCalculation and remaining lots

**Loss Handling:** Losses can offset gains or carry forward

### `TaxOptimizer._select_lots(
    tax_lots: List[TaxLot],
    quantity: Decimal,
    method: TaxMethod,
) -> Tuple[List[TaxLot], List[TaxLot]]`
**Pre:** tax_lots non-empty; quantity > 0
**Post:** Returns (selected_lots, remaining_lots)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Selection Methods:**
- **FIFO:** Sort by acquisition_date (oldest first)
- **LIFO:** Sort by acquisition_date (newest first)
- **HIFO:** Sort by acquisition_price (highest first) - minimizes gains
- **MIN_TAX:** Sort by (is_long_term=False, realized_pnl) - long-term losses first
- **MAX_TAX:** Sort by (is_long_term, -realized_pnl) - short-term gains first

**Partial Sales:** Splits lots when quantity < lot.quantity

### `TaxOptimizer.find_tax_loss_harvesting_opportunities(
    tax_lots: List[TaxLot],
    jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
    min_loss: Decimal = Decimal("1000"),
) -> List[Tuple[TaxLot, Decimal]]`
**Pre:** tax_lots is list; min_loss > 0
**Post:** Returns list of (lot, potential_tax_savings) sorted by savings
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Filtering:** Only lots with unrealized_pnl < -min_loss

**Savings Calculation:**
- Short-term loss: `abs(loss) * short_term_rate`
- Long-term loss: `abs(loss) * long_term_rate`

**Sorting:** By potential_savings descending

### `TaxOptimizer.should_harvest_loss(
    lot: TaxLot,
    current_date: date,
    jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
) -> bool`
**Pre:** lot is valid; current_date is valid
**Post:** Returns True if should harvest loss
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Checks:**
1. Loss exists (unrealized_pnl < 0)
2. Wash sale period not violated (acquisition_date < current_date - wash_period)
3. Loss is significant (abs(loss) >= $100)

**Wash Sale:** USA has 30-day wash sale period

### `TaxOptimizer.optimize_dividend_tax(
    dividend_income: Decimal,
    jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
    has_tax_treaty: bool = True,
) -> Decimal`
**Pre:** dividend_income >= 0
**Post:** Returns optimized tax amount
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Treaty Handling:** US treaties reduce withholding to 15% when applicable

**Formula:** `dividend_income * dividend_rate` (with treaty adjustment)

### `TaxOptimizer.calculate_after_tax_return(
    pre_tax_return: Decimal,
    holding_period_days: int,
    jurisdiction: TaxJurisdiction = TaxJurisdiction.DEFAULT,
) -> Decimal`
**Pre:** holding_period_days >= 0
**Post:** Returns after-tax return
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Rate Selection:**
- Long-term (>= 365 days): long_term_rate
- Short-term (< 365 days): short_term_rate

**Formulas:**
- Gain: `pre_tax_return - (pre_tax_return * tax_rate)`
- Loss: `pre_tax_return * (1 - tax_rate)` (loss deduction)

---

## Acceptance Criteria
- [ ] **AC-001:** TaxMethod has FIFO, LIFO, HIFO, MIN_TAX, MAX_TAX values
- [ ] **AC-002:** TaxJurisdiction has SPAIN, USA, UK, GERMANY, FRANCE, DEFAULT
- [ ] **AC-003:** TaxLot.is_long_term returns True when holding_period_days >= 365
- [ ] **AC-004:** TaxLot.realized_pnl = (current_price - acquisition_price) * quantity
- [ ] **AC-005:** Spain rates: short_term=28%, long_term=21%, dividend=19%
- [ ] **AC-006:** USA rates: short_term=35%, long_term=15%, dividend=15%
- [ ] **AC-007:** configure_for_residence() returns tax configuration dict
- [ ] **AC-008:** configure_for_residence() defaults to DEFAULT for unknown country
- [ ] **AC-009:** calculate_tax_liability() separates short/long-term gains
- [ ] **AC-010:** _select_lots() implements FIFO (oldest first)
- [ ] **AC-011:** _select_lots() implements HIFO (highest price first)
- [ ] **AC-012:** _select_lots() splits lots on partial sales
- [ ] **AC-013:** find_tax_loss_harvesting_opportunities() filters by min_loss
- [ ] **AC-014:** find_tax_loss_harvesting_opportunities() sorts by savings
- [ ] **AC-015:** should_harvest_loss() checks wash sale period (30 days USA)
- [ ] **AC-016:** should_harvest_loss() requires loss >= $100
- [ ] **AC-017:** optimize_dividend_tax() applies treaty reduction for USA
- [ ] **AC-018:** calculate_after_tax_return() uses long_term_rate for >=365 days
- [ ] **AC-019:** NumPy 2.0 compatible (no np aliases)
- [ ] **AC-020:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Tax Optimizer):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Tax lot accounting | Standard practice | FIFO/LIFO/HIFO methods | ✅ OK - _select_lots() |
| Short-term rates | Tax law | <1 year holding period | ✅ OK - is_long_term property |
| Long-term threshold | Tax law | 365 days | ✅ OK - is_long_term property |
| Wash sale rule | US tax law | 30-day period | ✅ OK - _wash_sale_periods[USA] |
| Tax loss harvesting | López de Prado | Offset gains with losses | ✅ OK - should_harvest_loss() |
| Dividend withholding | Tax law | Varies by jurisdiction | ✅ OK - _tax_rates |
| Treaty benefits | Tax law | Reduced withholding | ✅ OK - optimize_dividend_tax() |
| Partial lot sales | Trading | Split lots correctly | ✅ OK - _select_lots() |
| Decimal precision | BASE_RULES.md (TYP-002) | Decimal for money | ✅ OK - Decimal types |
| Enum for methods | Clean code | TaxMethod enum | ✅ OK - TaxMethod |
| Enum for jurisdictions | Clean code | TaxJurisdiction enum | ✅ OK - TaxJurisdiction |
| Dataclass for results | Clean code | TaxLot, TaxCalculation | ✅ OK - dataclasses |
| Default handling | Clean code | DEFAULT jurisdiction | ✅ OK - configure_for_residence() |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - np unused |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and standard tax practices.

---

## Dependencies
- **External:** `numpy`, `dataclasses` (std), `decimal` (std), `datetime` (std), `enum` (std), `typing` (std)
- **Internal:** None (application service layer)

---

## Required Tests
- **test_tax_optimizer.py:**
  - `test_init()` - Initializes tax rates
  - `test_configure_residence_spain()` - Returns Spain config
  - `test_configure_residence_usa()` - Returns USA config
  - `test_configure_residence_unknown()` - Defaults to DEFAULT
  - `test_tax_lot_is_long_term()` - True when >= 365 days
  - `test_tax_lot_realized_pnl()` - Calculates P&L correctly
  - `test_calculate_tax_liability_fifo()` - Uses FIFO method
  - `test_calculate_tax_liability_hifo()` - Uses HIFO method
  - `test_calculate_tax_liability_lifo()` - Uses LIFO method
  - `test_calculate_tax_liability_min_tax()` - Minimizes taxes
  - `test_calculate_short_term_gain()` - Applies short_term rate
  - `test_calculate_long_term_gain()` - Applies long_term rate
  - `test_calculate_loss_harvesting()` - Handles losses correctly
  - `test_select_lots_fifo()` - Oldest first
  - `test_select_lots_hifo()` - Highest price first
  - `test_select_lots_partial_sale()` - Splits lot correctly
  - `test_find_loss_harvesting_opportunities()` - Filters by min_loss
  - `test_find_loss_harvesting_sorted()` - Sorted by savings
  - `test_should_harvest_loss_wash_sale()` - False for recent purchases
  - `test_should_harvest_loss_small()` - False for < $100 loss
  - `test_should_harvest_loss_valid()` - True for valid loss
  - `test_optimize_dividend_tax_treaty()` - Applies treaty reduction
  - `test_optimize_dividend_tax_no_treaty()` - Uses base rate
  - `test_calculate_after_tax_return_short_term()` - Uses short_term rate
  - `test_calculate_after_tax_return_long_term()` - Uses long_term rate
  - `test_calculate_after_tax_return_loss()` - Applies deduction

---

## Notes
- **Critical:** Tax optimization significantly impacts after-tax returns
- **Tax Lot Accounting Methods:**
  - **FIFO:** First In, First Out - sells oldest lots first (common in Europe)
  - **LIFO:** Last In, First Out - sells newest lots first
  - **HIFO:** Highest In, First Out - sells highest cost lots first (minimizes taxes)
  - **MIN_TAX:** Minimizes current tax - long-term losses, short-term losses first
  - **MAX_TAX:** Maximizes current tax - for tax loss harvesting strategies
- **Jurisdiction-Specific Rules:**
  - **Spain:** 28% short-term, 21% long-term, 19% dividend
  - **USA:** 35% short-term (ordinary income), 15% long-term, 15% dividend
    - 30-day wash sale rule (cannot buy same stock within 30 days)
  - **UK:** 20% basic rate, 10% for gains, 8.75% dividend tax
- **Wash Sale Rule (USA):**
  - Cannot claim loss if same stock bought within 30 days
  - Loss is deferred to new lot's basis
  - Checked in `should_harvest_loss()`
- **Tax Loss Harvesting:**
  - Sell losing positions to offset gains
  - Minimizes current tax liability
  - Losses up to $3000 can offset ordinary income (US)
  - Excess losses carry forward indefinitely
- **Dividend Tax Optimization:**
  - Tax treaties reduce withholding rates
  - US treaties typically reduce to 15%
  - Qualified dividends have lower rates
- **After-Tax Return:**
  - Critical for comparing strategies
  - Long-term holdings benefit from lower rates
  - Short-term gains heavily penalized
- **Production Rule:** Always consider tax implications in trading decisions

---

**File Reference:** `app/application/services/tax_optimizer.py`
**Last Audited:** 2026-02-01
