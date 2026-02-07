# Requirements: sre/state_machine/wal_persistence.py

## Source File Analysis
- **File Path**: `app/sre/state_machine/wal_persistence.py`
- **Lines of Code**: 441
- **Status:** AUDITED - PASSED
- **Audit Date:** 2026-02-07
- **Batch:** 0088

## Purpose
CRITICAL SRE COMPONENT: Implements Write-Ahead Logging (WAL) for order state machine to prevent "orphaned positions" - a critical issue where the broker has a position open but the system doesn't know about it due to crashes between broker ACK and database save. CRITICAL: Order state MUST be saved to database BEFORE sending to broker to ensure crash recovery can reconcile any orphaned positions.

## Dependencies
### Internal
- None (standalone SRE module)

### External
- `aiofiles`: Async file operations
- `aiosqlite`: Async SQLite database operations
- `asyncio`: Async operations
- `dataclasses`: Data structures
- `datetime`: Time handling (datetime, timezone)
- `decimal`: Decimal for financial precision
- `enum`: Enumerations
- `json`: JSON serialization
- `pathlib`: File operations
- `typing`: Type hints
- `logging`: Logging

## Classes/Functions

### Enums
- `OrderState`: Order states with WAL persistence guarantees
  - PENDING: Initial state
  - SUBMITTING: CRITICAL - Saved BEFORE broker call
  - SUBMITTED: Sent to broker
  - ACK_RECEIVED: Broker acknowledged
  - OPEN: Active in market
  - PARTIAL_FILLED: Partial execution
  - FILLED: Fully executed
  - CANCELLED: Cancelled by user
  - REJECTED: Broker rejected
  - FAILED: System failure

### Data Classes
- `OrderLog`: WAL entry for order state transitions
  - Attributes: order_id, state, timestamp, symbol, side, quantity, price, error, broker_order_id, metadata
  - Methods:
    - `to_dict()`: Convert to dictionary for JSON serialization
    - `from_dict(data)`: Create from dictionary

### Main Classes

#### OrderStateMachine
Order state machine with WAL persistence.

**CRITICAL PATTERN**: This prevents orphaned positions by ensuring state transitions are persisted BEFORE external operations.

**State Machine Flow**:
```
PENDING -> SUBMITTING -> SUBMITTED -> ACK_RECEIVED -> OPEN -> FILLED
                  |              |
                  v              v
                REJECTED      CANCELLED
```

- Methods:
  - `initialize()`: Create database schema
  - `write_state(log)`: Write order state to WAL (database and file)
  - `get_order_history(order_id)`: Get all state transitions for an order
  - `get_orders_in_state(state)`: Get all orders in specific state
  - `get_pending_orders()`: Get orders in SUBMITTING or SUBMITTED state (may be orphaned)

#### WALOrderManager
High-level order manager with WAL guarantees.

**CRITICAL USAGE PATTERN**:
1. Save state as SUBMITTING (BEFORE broker call)
2. Call broker API
3. Save state as ACK_RECEIVED (AFTER broker ACK)
4. Save final state (FILLED/OPEN/REJECTED)

- Methods:
  - `initialize()`: Initialize state machine
  - `submit_order()`: Submit order with WAL protection
  - `recover_orphaned_orders()`: Detect and report orphaned orders for recovery

## Business Logic

### WAL Persistence Pattern
The critical pattern that prevents orphaned positions:

```python
# BAD: Order lost if crash occurs here
result = await broker.submit(order)
await db.save_order(result)  # Never executes if crash

# GOOD: Order saved before broker call
await wal.write(OrderLog(state="SUBMITTING", order_id=order.id))
result = await broker.submit(order)
await wal.write(OrderLog(state="ACK_RECEIVED", ...))
```

### Orphaned Order Recovery
On system startup:
1. Query for orders in SUBMITTING/SUBMITTED state
2. Check with broker if order actually exists
3. If broker has order as OPEN/PARTIAL_FILLED: Orphaned position detected
4. Set recovery action: SET_STOP_LOSS (Critical!)
5. Alert and log for manual intervention if needed

## Data Models

### Database Schema
```sql
CREATE TABLE order_wal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    state TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT,
    error TEXT,
    broker_order_id TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### Indexes
- `idx_order_id`: For order history queries
- `idx_state`: For pending order queries

### File WAL
- Append-only JSON log file for redundancy
- Format: JSON per line
- Path: Configurable via `wal_path`

## API Contracts

### OrderStateMachine Interface
```python
# Initialize
machine = OrderStateMachine(db_path="...", wal_path="...")
await machine.initialize()

# Write state
log = OrderLog(
    order_id="123",
    state=OrderState.SUBMITTING,
    timestamp=datetime.now(timezone.utc),
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100")
)
await machine.write_state(log)

# Query history
history = await machine.get_order_history("123")
pending = await machine.get_pending_orders()
```

### WALOrderManager Interface
```python
# Initialize
manager = WALOrderManager(db_path="...", wal_path="...", broker_client=broker)
await manager.initialize()

# Submit order with WAL protection
result = await manager.submit_order(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150.00")
)

# Recover orphaned orders on startup
orphaned = await manager.recover_orphaned_orders()
```

## Error Handling

### Exception Handling Strategy
- `write_state()`: Catches asyncio.TimeoutError, ConnectionError, OSError
- `submit_order()`: Catches ConnectionError, TimeoutError, HTTPError, ValueError
- `recover_orphaned_orders()`: Catches ValueError, KeyError, AttributeError, IndexError, TypeError
- All errors logged with CRITICAL level for WAL failures

### Error Recovery
- WAL write failures raise exception (order should not proceed)
- Broker API failures logged but state preserved
- Orphaned order detection failures logged per order
- File WAL and database WAL provide redundancy

## Performance Considerations
- Async operations throughout
- Database connection pooling via aiosqlite
- Dual WAL (database + file) for redundancy
- Indexed queries for fast lookups
- Minimal memory footprint

## Testing Strategy

### Unit Tests
1. Test OrderLog serialization/deserialization
2. Test state transitions
3. Test database schema creation
4. Test file WAL append operations
5. Test pending order queries

### Integration Tests
1. Test full order submission flow
2. Test crash recovery scenarios
3. Test orphaned order detection
4. Test database + file WAL consistency
5. Test concurrent order submissions

### Edge Cases
1. Crash during SUBMITTING state
2. Crash during broker call
3. Crash after ACK but before final state
4. Broker API unavailable
5. Database unavailable
6. File system full

## SRE Specific Requirements

### Critical Safety (SRE Rules)
- **SRE-001**: WAL prevents orphaned positions
- **SRE-002**: State persisted BEFORE external operations
- **SRE-003**: Crash recovery capability
- **SRE-004**: Dual WAL for redundancy (DB + file)
- **SRE-005**: Orphaned order detection on startup
- **SRE-006**: Critical logging for all state changes

### Operational Requirements
- On startup: Check for orphaned orders
- On orphaned detection: Set emergency stop-loss
- Manual intervention: Alert when automatic recovery fails
- Audit trail: All state transitions logged

## Security Considerations
- No hardcoded credentials (broker_client injected)
- Database path configurable
- File WAL path configurable
- No sensitive data in logs (order IDs only)
- Audit trail for compliance

## Compliance & Standards
- Type hints throughout
- Comprehensive docstrings
- Structured logging with context
- Decimal for financial precision
- Timezone-aware datetime (timezone.utc)
- Async/await patterns
- Immutable data patterns where possible

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0088 GAP Audit)
**Batch:** 0088

### BASE_RULES Verification

✅ **SEC-001**: No hardcoded secrets detected
✅ **SEC-002**: Broker client injected, credentials configurable
✅ **LOG-003**: CRITICAL level logging for WAL failures
✅ **LOG-004**: Comprehensive error logging with context
✅ **LOG-005**: No sensitive data in logs (order metadata only)
✅ **LOG-006**: Structured logging with logger instance
✅ **ERR-001**: Proper exception handling with specific types
✅ **ERR-002**: All exceptions logged with context
✅ **DAT-001**: Uses timezone-aware datetime (datetime.now(timezone.utc))
✅ **DAT-002**: Proper Decimal handling for financial precision
✅ **FIN-001**: Decimal used for all financial calculations
✅ **TRD-001**: Trading safety via WAL pattern
✅ **TRD-002**: Order validation before submission
✅ **SRE-001**: WAL prevents orphaned positions
✅ **SRE-002**: State persisted before external operations
✅ **SRE-003**: Crash recovery implemented
✅ **SRE-004**: Dual WAL (database + file) for redundancy

### Critical Safety Notes
- This is a CRITICAL SRE component for position safety
- The SUBMITTING state MUST be persisted BEFORE broker API call
- Orphaned positions detected during recovery have NO stop-loss protection
- Dual WAL (database + file) provides redundancy
- Recovery must be run on EVERY startup

### Notes
- Code is well-documented with clear critical patterns
- Proper separation of concerns (state machine vs manager)
- Comprehensive error handling
- Production-ready with no P0 or P1 violations
- Clear documentation of the BAD vs GOOD pattern

### Recommendations (Future Enhancements)
1. Add Prometheus metrics for WAL operations
2. Implement WAL compaction/cleanup for old orders
3. Add snapshot capability for faster recovery
4. Consider adding WAL integrity checksums
5. Add configuration for custom state timeouts
6. Implement order state timeout detection

---
*Requirements updated: 2026-02-07*
*Audit completed: Batch 0088*
