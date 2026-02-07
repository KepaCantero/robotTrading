# Requirements: services/position_monitor/stop_executor.py

## Source File Analysis
- **File Path**: `app/services/position_monitor/stop_executor.py`
- **Lines of Code:** 400
- **Status:** AUDIT COMPLETE

## Purpose
Stop Executor - Executes stop-loss and take-profit orders with immediate placement, broker error handling, detailed logging, and execution results.

## Dependencies
- Internal:
  - `app.core.decimal_utils.to_decimal`
  - `.position_monitor.MonitoredPosition` (TYPE_CHECKING only)
- External:
  - `asyncio`, `logging`, `dataclasses`, `datetime`, `decimal`, `enum`, `typing`

## Classes/Functions

### Enums
- `StopType`: STOP_LOSS, TAKE_PROFIT

### Data Classes
- `StopExecutionResult`: success, stop_type, symbol, quantity, prices, order_id, error, timing, response

### Main Class: StopExecutor
- `__init__(broker, order_timeout)`: Initialize with broker and timeout
- `execute_stop_loss(position, retry_attempts)`: Execute stop-loss with retries
- `execute_take_profit(position, retry_attempts)`: Execute take-profit with retries
- `_execute_order(...)`: Execute order with timeout
- `execute_stop_order(...)`: Direct stop order execution

## Business Logic
1. **CRITICAL Operation**: Stop-loss requires immediate exit
2. **Retry Logic**: 2 default retry attempts with 1 second delay
3. **Order Side**: Opposite of position side (LONG->SELL, SHORT->BUY)
4. **Timeout Protection**: 30 second default timeout
5. **Detailed Results**: Order ID, executed price, timing, broker response

## Data Models
- StopExecutionResult with comprehensive execution details
- Uses TYPE_CHECKING for MonitoredPosition import

## API Contracts
- Requires broker with `place_order()` method
- Returns StopExecutionResult with full details
- Uses market orders for emergency exits

## Error Handling
- Exception types: `(ValueError, KeyError, AttributeError, IndexError, TypeError)`
- `asyncio.TimeoutError` handled separately
- Retry on transient failures
- Final failure with attempt count

## Performance Considerations
- asyncio.wait_for for timeout enforcement
- Minimal processing in execution path
- Timing captured for all operations

## Testing Strategy
- Test stop-loss execution
- Test take-profit execution
- Test timeout handling
- Test retry logic
- Test result serialization

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Critical component with robust implementation

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Descriptive names (StopType, StopExecutionResult)
- ✅ CC-006: Explicit error handling
- ✅ LOG-004: Critical/error logging with context
- ✅ LOG-005: No sensitive data logged
- ✅ LOG-006: Timing captured (execution_time_ms)
- ✅ SEC-005: Audit logging (all stops logged)
- ✅ ASYNC-001: Proper async def usage
- ✅ ASYNC-002: All async calls awaited
- ✅ ASYNC-004: No time.sleep() (uses asyncio.sleep())
- ✅ ASYNC-005: Timeouts implemented (30s default)
- ✅ ASYNC-006: Handles asyncio.TimeoutError
- ✅ TRD-004: Audit trail (StopExecutionResult)
- ✅ FMT-007: No mutable defaults

**Minor Notes:**
- TYPE_CHECKING import is correct pattern
- All critical operations have detailed logging

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0078*
