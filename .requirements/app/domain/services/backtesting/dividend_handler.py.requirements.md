# Requirements: app/domain/services/backtesting/dividend_handler.py

## Source File Analysis
- **File Path**: `app/domain/services/backtesting/dividend_handler.py`
- **Lines of Code**: 420
- **Status**: Analysis Complete

## Purpose
Handles dividend payments and reinvestment (DRIP) for backtesting. Dividends significantly affect total return in long-term strategies, and DRIP can compound returns significantly.

Reference: López de Prado (2018) "Advances in Financial Machine Learning" - Dividend handling importance for accurate backtesting

## Dependencies

### Internal
None - Pure domain service

### External
- `dataclasses`: Data class decorators
- `datetime.date`, `datetime.timedelta`: Date handling
- `decimal.Decimal`: Precise financial calculations
- `enum.Enum`: Enumeration types
- `typing`: Type hints (Dict, List, Optional, Tuple)

## Classes/Functions

### class DividendType(str, Enum)
**Purpose**: Types of dividends

**Values**:
- `REGULAR = "regular"` - Regular quarterly dividend
- `SPECIAL = "special"` - One-time special dividend
- `FINAL = "final"` - Final dividend before liquidation
- `INTERIM = "interim"` - Interim dividend
- `STOCK = "stock"` - Stock dividend

---

### class DividendReinvestmentStrategy(str, Enum)
**Purpose**: Dividend reinvestment strategies

**Values**:
- `REINVEST = "reinvest"` - Reinvest all dividends
- `CASH = "cash"` - Keep dividends as cash
- `THRESHOLD = "threshold"` - Reinvest only above threshold
- `MANUAL = "manual"` - Manual reinvestment

---

### @dataclass class DividendPayment
**Purpose**: Record of a dividend payment

**Attributes**:
- `symbol: str` - Trading symbol
- `ex_date: date` - Ex-dividend date
- `record_date: date` - Record date
- `payable_date: date` - Payment date
- `amount_per_share: Decimal` - Dividend per share
- `dividend_type: DividendType` - Type of dividend
- `frequency: Optional[int]` - Payments per year

**Properties**:
- `annualized_amount: Decimal` - Annualized dividend (assumes 4x if not specified)

---

### @dataclass class DividendReinvestment
**Purpose**: Record of dividend reinvestment

**Attributes**:
- `symbol: str` - Symbol reinvested in
- `reinvestment_date: date` - Date of reinvestment
- `dividend_amount: Decimal` - Amount reinvested
- `shares_purchased: Decimal` - Shares acquired
- `price_per_share: Decimal` - Price per share
- `fractional_shares: bool` - Whether fractional shares allowed

---

### class DividendHandler
**Purpose**: Handles dividend payments and reinvestment

**Key Methods**:

#### `__init__(strategy, threshold, fractional_shares, tax_rate)`
Initialize with reinvestment strategy parameters

#### `add_dividend(dividend) -> None`
Add a dividend payment to tracking

#### `get_dividend(symbol, as_of_date) -> Optional[DividendPayment]`
Get most recent dividend for symbol before date

#### `calculate_dividend_yield(symbol, price, as_of_date) -> float`
Calculate dividend yield as percentage

#### `process_dividend_payment(symbol, quantity, date, price) -> Tuple[Decimal, Optional[DividendReinvestment]]`
Process dividend payment for a position, returns (dividend_amount, reinvestment_info)

#### `calculate_annual_dividend_income(positions, prices, as_of_date) -> Decimal`
Calculate expected annual dividend income from all positions

#### `calculate_portfolio_dividend_yield(positions, prices, as_of_date) -> float`
Calculate portfolio-level dividend yield

#### `estimate_next_dividend_date(symbol, as_of_date) -> Optional[date]`
Estimate next ex-dividend date based on history

#### `calculate_dividend_growth_rate(symbol, years) -> float`
Calculate CAGR of dividend payments

## Business Logic

### Dividend Processing Flow
1. Match payable date to dividend records
2. Calculate gross dividend (amount_per_share × quantity)
3. Apply tax withholding
4. Apply reinvestment strategy:
   - REINVEST: Always reinvest
   - CASH: Keep as cash
   - THRESHOLD: Reinvest only above minimum

### Reinvestment Calculation
- Fractional shares: `shares = dividend / price`
- Whole shares only: `shares = dividend // price`
- Tracks all reinvestments for reporting

### Dividend Growth Rate
- Uses CAGR formula: `(newest/oldest)^(1/periods) - 1`
- Annualized: `growth_rate * 4` for quarterly

## Data Models

### Core Value Objects
- `DividendPayment` - Immutable dividend record
- `DividendReinvestment` - Immutable reinvestment record
- Enums for types and strategies

### State Management
- `_dividends: Dict[str, List[DividendPayment]]` - All tracked dividends
- `_reinvestments: List[DividendReinvestment]` - All reinvestments
- `_strategy: DividendReinvestmentStrategy` - Current strategy
- `_threshold: Decimal` - Minimum for threshold reinvestment
- `_fractional_shares: bool` - Allow fractional shares
- `_tax_rate: Decimal` - Withholding rate

## API Contracts

### Public Interface
```python
handler = DividendHandler(strategy=REINVEST)
handler.add_dividend(dividend)

# Process payments
dividend, reinvestment = handler.process_dividend_payment(
    symbol, quantity, date, price
)

# Calculate metrics
yield_pct = handler.calculate_dividend_yield(symbol, price, date)
portfolio_yield = handler.calculate_portfolio_dividend_yield(positions, prices, date)
```

## Error Handling

### Edge Cases Handled
- Zero price returns 0 shares purchased
- Empty reinvestment list returns Decimal("0")
- Zero price for yield calculation returns 0.0
- Missing dividend history returns None/0.0

## Performance Considerations

### Computational Complexity
- `get_dividend`: O(n) where n = dividends per symbol
- `process_dividend_payment`: O(n) for matching payable date
- `calculate_*_yield`: O(n) for iterating positions

### Memory Usage
- Stores all dividends and reinvestments in memory

## Testing Strategy

### Unit Tests Needed
- Dividend addition and retrieval
- Yield calculation accuracy
- Reinvestment with/without fractional shares
- Tax withholding application
- Threshold strategy behavior
- Growth rate calculation with limited data
- Edge cases (empty data, zero prices)

### Integration Tests Needed
- Integration with backtest engine
- Multi-year dividend history
- Portfolio with multiple dividend-paying stocks

## Critical Rules (from BASE_RULES.md)

### TYP-001: Type hints
- ✅ All functions have complete type hints
- ✅ Uses `from __future__ import annotations`

### ARCH-001: Layered architecture
- ✅ Domain layer - no framework dependencies
- ✅ Pure domain service

### CC-001: Descriptive names
- ✅ Clear, self-documenting names

### QL-001: Complexity
- ✅ Good average complexity (8.0)

### ERR-001: Error handling
- ✅ Handles edge cases gracefully
- ⚠️ No error logging (domain service - acceptable)

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:21:00Z |
| **Audit Status** | PASSED |

**Notes**:
- Fixed: Type casting for sum() operations (lines 415, 419)
- Clean domain service with comprehensive dividend handling
- Good separation of concerns with strategy pattern
