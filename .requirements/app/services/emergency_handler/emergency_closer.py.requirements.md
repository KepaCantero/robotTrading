# Requirements: services/emergency_handler/emergency_closer.py

**See ../../BASE_RULES.md for universal rules**

## Source File Analysis
- **File Path**: `app/services/emergency_handler/emergency_closer.py`
- **Lines of Code**: 512
- **Purpose**: Critical safety component for emergency position closure on system failures
- **Status**: PRODUCTION READY

## Module Purpose
EmergencyCloser is a CRITICAL safety component that closes all positions on critical system failures:
- Broker connection loss
- System shutdown (SIGTERM/SIGINT)
- Critical errors (ConnectionError, TimeoutError, MemoryError)
- Manual emergency triggers
- Heartbeat failures
- Memory exceeded thresholds

## Dependencies
### Internal
- `app.core.timezone_utils.utc_now`: UTC timestamp generation

### External
- `asyncio`: Async/await for concurrent operations
- `signal`: Signal handling for graceful shutdown
- `decimal.Decimal`: Precise financial calculations
- `dataclasses`: Data structures (EmergencyCloseResult, EmergencyTrigger enum)
- `requests.exceptions.HTTPError`: HTTP error handling

## Classes and Functions

### Classes
- **`EmergencyTrigger` (Enum)**: Types of emergency triggers
  - CONNECTION_LOST, SYSTEM_SHUTDOWN, CRITICAL_ERROR, MANUAL_TRIGGER, HEARTBEAT_FAILURE, MEMORY_EXCEEDED

- **`EmergencyCloseResult` (dataclass)**: Result of emergency close operation
  - success, trigger, total_positions, closed_positions, failed_positions
  - total_value, execution_time_seconds, errors list, timestamp
  - to_dict() method for serialization

- **`EmergencyCloser`**: Main class for emergency position closure
  - `__init__(broker, alert_callback, require_confirmation, confirmation_timeout_seconds)`
  - `on_connection_lost()`: Handle broker disconnection
  - `on_system_shutdown()`: Handle SIGTERM/SIGINT
  - `on_critical_error(error)`: Handle critical exceptions
  - `manual_trigger(reason)`: Manual emergency activation
  - `close_all_positions(trigger)`: Core closing logic
  - `get_audit_log(limit)`: Retrieve audit trail
  - `_is_error_critical(error)`: Error classification
  - `_get_all_positions()`: Fetch from broker
  - `_close_position(position)`: Close single position
  - `_wait_for_confirmation()`: Optional confirmation flow
  - `_send_alert(message)`: Alert notifications
  - `_setup_signal_handlers()`: Register SIGTERM/SIGINT handlers
  - `_signal_handler(signum, frame)`: Handle signals

## Business Logic

### Emergency Close Flow
1. Trigger received (connection lost, shutdown, error, manual)
2. Send alert notification
3. Optionally wait for confirmation (if require_confirmation=True)
4. Fetch all open positions from broker
5. Close all positions via market orders
6. Log to audit trail
7. Return EmergencyCloseResult with execution details

### Error Classification
Critical error types requiring immediate position closure:
- ConnectionError, TimeoutError, MemoryError (automatic)
- Error messages containing: "connection lost", "authentication failed", "insufficient funds", "order rejected", "market closed"

### Safety Features
- `_is_closing` flag prevents concurrent closures
- Market orders only (no limit orders for speed)
- 30-second timeout per position closure
- Comprehensive audit logging

## Data Models
- **`EmergencyCloseResult`**: Complete execution record with counts, values, errors
- **`EmergencyTrigger`**: Enum of trigger types
- Position objects from broker (expected attributes: symbol, side, quantity)

## API Contracts
```python
async def on_connection_lost() -> EmergencyCloseResult
async def on_system_shutdown() -> EmergencyCloseResult
async def on_critical_error(error: Exception) -> EmergencyCloseResult
async def manual_trigger(reason: str) -> EmergencyCloseResult
```

## Error Handling
- All exceptions caught in close_all_positions()
- Failed positions logged but don't stop closure of others
- asyncio.TimeoutError, ConnectionError, OSError handled for network issues
- ValueError, TypeError, KeyError handled for data issues

## Performance Considerations
- Sequential position closure (could be parallelized for many positions)
- 30-second timeout per position
- Total execution time tracked
- Memory cleanup on completion

## Testing Strategy
- Unit: Mock broker for position closure
- Integration: Test with Alpaca paper trading
- Edge cases: No positions, failed closures, partial fills
- Signal handling: Test SIGTERM/SIGINT reception
- Concurrent triggers: Test _is_closing guard

## Security & Compliance
- Audit trail for all emergency closures
- Alert notifications on activation
- Optional confirmation for non-connection-loss triggers
- No credentials stored (uses injected broker dependency)

## BASE_RULES Compliance

### Critical Rules (P0)
- ✅ **ASYNC-001/002/003**: Proper async/await with async context managers
- ✅ **LOG-004**: Comprehensive error logging with context
- ✅ **TRD-002**: Position validation before closure
- ✅ **TRD-004**: Audit trail of all emergency actions

### Security (SEC-001, SEC-005)
- ✅ **SEC-001**: No hardcoded secrets
- ✅ **SEC-005**: Audit logging implemented

### Logging (LOG-001, LOG-003, LOG-004)
- ✅ Structured logging with context
- ✅ Appropriate log levels (debug/info/warning/critical/error)
- ✅ Exception logging with stack traces

### Error Handling (CC-006)
- ✅ Specific exception types caught
- ✅ Error context preserved in logs
- ✅ Graceful degradation

### Code Quality (QL-001, QL-005)
- ✅ Functions under 50 lines (most methods)
- ✅ Clear separation of concerns

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0070-0071-0072 GAP Audit)
**GAPs Found:** 0 critical, 0 high priority
**Risk Level:** LOW - Critical safety component with proper error handling

### Verification Results
- All BASE_RULES verified against production standards
- No P0/P1 violations found
- Code is production-ready for live trading
- Comprehensive audit trail implemented
- Proper async patterns throughout
- Error handling is robust and well-structured

### Notes
- This is a CRITICAL component for production safety
- Consider parallel position closure for large portfolios (future enhancement)
- Signal handler registration may fail in some environments (properly handled with try/except)
- Optional confirmation flow provides safety against accidental triggers

---
*Updated: 2026-02-07*
*Batch: 0070*
