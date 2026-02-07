# Requirements: backtesting/liquidity_validator.py

## Source File Analysis
- **File Path:** `app/backtesting/liquidity_validator.py`
- **Lines of Code:** 416
- **Audit Status:** PASSED
- **Audit Date:** 2026-02-07T05:30:00Z

## Purpose
Validates order liquidity and implements realistic fill scenarios for backtesting. Addresses HIGH PRIORITY #1 from audit report including volume-based rejection, partial fills, and market impact calculation.

## Dependencies
- **Internal:**
  - None (domain-level module)
- **External:**
  - `logging`
  - `dataclasses` (dataclass)
  - `decimal` (Decimal)
  - `typing` (Optional, Tuple)

## Classes/Functions

### Data Classes
- **FillResult:** Result of order fill attempt
  - `requested_quantity: Decimal`
  - `filled_quantity: Decimal`
  - `fill_price: Decimal`
  - `fill_status: str` ("FILLED", "PARTIAL", "REJECTED")
  - `rejection_reason: Optional[str] = None`
  - `avg_fill_price: Optional[Decimal] = None`
  - `market_impact: Optional[Decimal] = None`
  - `__post_init__()`: Sets avg_fill_price if not provided

### Main Class
- **LiquidityValidator:** Validates order liquidity
  - **Constants:**
    - `MAX_ORDER_PCT_OF_VOLUME = Decimal("0.10")` (10%)
    - `WARNING_ORDER_PCT_OF_VOLUME = Decimal("0.05")` (5%)
    - `PARTIAL_FILL_PCT = Decimal("0.05")` (5%)
    - `BASE_SLIPPAGE_PCT = Decimal("0.001")` (0.1%)
    - `MAX_ADDITIONAL_SLIPPAGE = Decimal("0.01")` (1%)

  - **Methods:**
    - `__init__(enable_partial_fills: bool = True, ...)`
    - `validate_order(order_quantity: Decimal, symbol: str, current_bar, order_side: str = "buy") -> Tuple[bool, str]`
    - `simulate_fill(order_quantity: Decimal, current_bar, order_side: str = "buy", symbol: str = "UNKNOWN") -> FillResult`
    - `_calculate_buy_fill_price(current_bar, quantity: Optional[Decimal] = None) -> Decimal`
    - `_calculate_sell_fill_price(current_bar, quantity: Optional[Decimal] = None) -> Decimal`
    - `calculate_market_impact(order_quantity: Decimal, current_bar, order_side: str = "buy") -> Decimal`
    - `get_liquidity_metrics(current_bar, order_quantity: Optional[Decimal] = None) -> dict`

## Business Logic

### Order Validation
- Checks for volume data availability
- Validates daily volume > 0
- Calculates order as percentage of daily volume
- Rejects orders exceeding MAX_ORDER_PCT_OF_VOLUME (10%)
- Warns for orders exceeding WARNING_ORDER_PCT_OF_VOLUME (5%)

### Fill Simulation
- Validates order first
- Full fill if order ≤ max_fillable (5% of daily volume)
- Partial fill if enabled and order > max_fillable
- Rejection if order too large and partial fills disabled
- Calculates realistic execution price with slippage

### Market Impact Calculation
- Square-root market impact model
- Base impact = sqrt(order_pct) * 0.1
- Capped at 5% maximum impact
- Buy orders pay more, sell orders receive less

### Price Calculation
- Buy: `base_price * (1 + slippage)`
- Sell: `base_price * (1 - slippage)`
- Base slippage: 0.1%
- Additional slippage based on order size (squared relationship)

## Data Models
- **FillResult:** @dataclass with all fill information
- Uses `Decimal` for all financial calculations (proper precision)

## API Contracts
N/A - This is a library module

## Error Handling
- No exception handling needed (validation logic)
- Returns descriptive rejection reasons
- Logs warnings for large orders and partial fills

## Performance Considerations
- O(1) calculations for all operations
- Minimal memory allocation
- Decimal operations for precision (slightly slower than float)

## Testing Strategy
- Unit tests for validation thresholds
- Test partial fill scenarios
- Verify market impact calculations
- Test price calculation accuracy
- Edge cases: zero volume, negative quantities

## Trading-Specific Rules Compliance
- **TRD-002 (Risk validation):** ✅ Validates orders before execution
- **BT-004 (Realistic costs):** ✅ Includes slippage and market impact
- **EXE-001 (Order validation):** ✅ Validates order parameters

## Audit Notes

### What Was Checked
- ✅ No print() statements (uses logger)
- ✅ No mutable default arguments
- ✅ Proper type hints using Decimal for financial precision
- ✅ Google style docstrings
- ✅ Absolute imports only
- ✅ Specific exception types where used
- ✅ All functions have return type hints
- ✅ Uses Decimal for all monetary calculations (critical for trading)

### BASE_RULES Compliance
See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

**File-specific rules:**
- FMT-007: No mutable defaults ✅
- TYP-001: 100% type coverage ✅
- TYP-003: Specific types (Decimal) used for financial data ✅
- LOG-001: Structured logging ✅
- TRD-002: Risk validation ✅
- BT-004: Realistic transaction costs ✅

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Updated: 2026-02-07T05:30:00Z*
