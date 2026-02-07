# Requirements: services/corporate_actions/handler.py

## Source File Analysis
- **File Path**: `app/services/corporate_actions/handler.py`
- **Lines of Code**: 931
- **Status**: AUDIT COMPLETE

## Purpose
Handle stock splits, dividends, mergers, delistings, and other corporate actions that affect positions. Integrates with broker adapters, position monitoring, portfolio management, and tax calculations (FIFO).

## Dependencies
- Internal:
  - `app.core.timezone_utils` (utc_now)
  - `app.core.interfaces.broker_base` (Order, OrderSide, OrderType)
- External:
  - `logging`
  - `dataclasses`
  - `datetime` (date, datetime)
  - `decimal` (Decimal)
  - `enum` (Enum)
  - `typing`

## Classes/Functions

### Enums
1. **CorporateActionType** (lines 36-48)
   - Values: STOCK_SPLIT, REVERSE_SPLIT, DIVIDEND, SPECIAL_DIVIDEND, MERGER, ACQUISITION, SPINOFF, DELISTING, RIGHTS_OFFERING, SYMBOL_CHANGE

### Data Classes
1. **CorporateAction** (lines 51-106)
   - Purpose: Represents a corporate action event
   - Attributes: action_type, symbol, ex_date, ratio, amount, new_symbol, description, record_date, payable_date, processed_at
   - Methods: `to_dict()`, `__post_init__()` (validation)

### Main Class
1. **CorporateActionsHandler** (lines 109-930)
   - Purpose: Handle corporate events that affect positions

   **Event Handlers (async):**
   - `on_stock_split()` (lines 158-261): Adjust positions for stock splits
   - `on_dividend()` (lines 263-334): Record dividend payment
   - `on_merger()` (lines 336-447): Convert positions to acquiring company
   - `on_delisting()` (lines 449-563): Close positions for delisted symbols
   - `on_spinoff()` (lines 565-669): Create new positions for spin-offs
   - `on_symbol_change()` (lines 671-745): Handle ticker renames

   **Private Helpers:**
   - `_get_open_positions()` (lines 751-774): Get open positions for symbol
   - `_update_position()` (lines 776-818): Update position with new values
   - `_adjust_dividend_baseline()` (lines 820-841): Adjust baseline price for dividend
   - `_get_position_symbol()` (lines 843-849): Extract symbol from position
   - `_get_position_quantity()` (lines 851-869): Extract quantity from position
   - `_get_position_avg_price()` (lines 871-891): Extract average price from position
   - `_get_position_id()` (lines 893-901): Extract position ID from position

   **Query Methods:**
   - `get_processed_actions()` (lines 907-909): Get all processed actions
   - `get_action_for_symbol()` (lines 911-913): Get actions for a symbol
   - `get_action_by_type()` (lines 915-921): Get actions by type
   - `get_stats()` (lines 923-925): Get handler statistics
   - `clear_history()` (lines 927-930): Clear action history

## Business Logic
1. Monitors for corporate actions
2. Adjusts positions accordingly:
   - Stock splits: Quantity × ratio, Price ÷ ratio
   - Dividends: Cash received, baseline price adjusted
   - Mergers: Position converted to acquiring company
   - Delistings: Position closed
   - Spin-offs: New shares received, original cost basis adjusted
3. Maintains audit trail of all processed actions
4. Tracks statistics

## Data Models
- **CorporateAction**: Event representation with validation
- Position data is flexible (handles different broker implementations)

## API Contracts
No REST API - service layer module.

## Error Handling
- ValueError for invalid inputs (ratio <= 0, amount < 0, missing new_symbol)
- Data validation in `__post_init__`
- Exception handling in position update loops
- Comprehensive logging

## Performance Considerations
- Async methods for I/O operations
- In-memory storage of processed actions
- Statistics tracking

## Testing Strategy
Recommended test coverage:
1. Unit tests for each corporate action type
2. Mock broker integration tests
3. Edge cases: invalid ratios, missing symbols, null positions
4. Validation tests for CorporateAction dataclass

## Compliance with BASE_RULES.md

### PASSING Rules:
- ✅ **ARCH-001**: Layered architecture - service layer correctly positioned
- ✅ **ASYNC-001**: Use async def - all event handlers are async
- ✅ **ASYNC-002**: Await async calls - properly awaited
- ✅ **CC-001**: Descriptive names - clear method names
- ✅ **CC-006**: Explicit error handling - ValueErrors and exception catching
- ✅ **LOG-003**: Appropriate logging levels - info/error/critical
- ✅ **LOG-004**: Error logging - exceptions logged with context
- ✅ **TYP-001**: Type hints - comprehensive type coverage
- ✅ **DP-004**: Dependency injection - broker and position_monitor injected

### GAPS IDENTIFIED:
None - Code quality is high. All BASE_RULES are satisfied.

## Audit Status: PASSED

**Audited By:** Claude (Backend Developer Agent)
**Audit Date:** 2026-02-07
**Batches:** 0097

### Summary
This module demonstrates excellent code quality:
- Comprehensive corporate action handling (all major types)
- Proper async patterns throughout
- Flexible position handling (accommodates different brokers)
- Data validation in dataclass
- Comprehensive error handling
- Good separation of concerns (public/private methods)
- Statistics tracking for observability

No critical gaps found. Module is production-ready.

---
*Auto-generated on Thu Feb  5 20:33:01 CET 2026*
*Updated for GAP audit on 2026-02-07*
