# Requirements: services/position_monitor/position_monitor.py

## Source File Analysis
- **File Path**: `app/services/position_monitor/position_monitor.py`
- **Lines of Code**: 977
- **Status**: PASSED
- **Audit Date**: 2026-02-07

---

## Purpose

**CRITICAL PRODUCTION COMPONENT**: Continuously monitors open positions and executes stop-loss/take-profit orders automatically.

This is a **LIFE-THREATENING CRITICAL** component for production trading:
- Checks positions every second (configurable)
- Executes stop-loss automatically when hit
- Executes take-profit automatically when hit
- Survives process restart (reads from DB)
- Handles broker disconnections gracefully

---

## BASE_RULES Compliance

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

### Critical Rules Applied
- **ASYNC-001/ASYNC-002**: All async functions properly marked with `async def` and `await`
- **LOG-004**: All exceptions logged with stack traces
- **TRD-002**: Risk validation - orders validated before execution
- **TRD-004**: Audit trail - all position changes logged
- **SEC-005**: Audit logging enabled for all trading operations

### Audit Status: **PASSED**

---

## Dependencies

### Internal Dependencies
- `app.core.decimal_utils.to_decimal`, `validate_price` - Decimal utilities for price handling
- `app.database.get_sync_db` - Database access for state persistence
- `app.database.models.PositionState` - Model for persisted position state
- `.stop_executor` - Local import for stop execution

### External Dependencies
- `asyncio` - Async/await for concurrent operations
- `decimal.Decimal` - Precise financial calculations
- `sqlalchemy` - Database operations (DataError, DatabaseError, etc.)
- `requests.exceptions.HTTPError` - HTTP error handling
- `logging` - Structured logging
- `dataclasses` - Data structures (MonitoredPosition, PositionMonitorConfig)
- `typing` - Type hints (Dict, List, Optional, Callable, Any)

---

## Classes/Functions

### 1. `PositionStatus` (Enum)
**Purpose**: Status of a monitored position

**Values**:
- `ACTIVE` - Position is active and being monitored
- `STOP_LOSS_TRIGGERED` - Stop-loss was triggered
- `TAKE_PROFIT_TRIGGERED` - Take-profit was triggered
- `CLOSED` - Position is closed
- `ERROR` - Error occurred during monitoring

### 2. `MonitoredPosition` (Dataclass)
**Purpose**: A position being monitored for stop-loss/take-profit execution

**Attributes**:
- `position_id: str` - Unique identifier
- `symbol: str` - Trading symbol
- `side: str` - "LONG" or "SHORT"
- `entry_price: Decimal` - Entry price
- `quantity: Decimal` - Position size
- `current_price: Decimal` - Current market price
- `stop_loss_price: Optional[Decimal]` - Absolute stop-loss price
- `stop_loss_pct: Optional[Decimal]` - Stop-loss percentage
- `take_profit_price: Optional[Decimal]` - Absolute take-profit price
- `take_profit_pct: Optional[Decimal]` - Take-profit percentage
- `status: PositionStatus` - Current status
- `opened_at: datetime` - When position was opened
- `last_checked: datetime` - Last check time
- `check_count: int` - Number of checks performed

**Methods**:
- `should_trigger_stop_loss() -> bool` - Check if stop-loss should trigger
- `should_trigger_take_profit() -> bool` - Check if take-profit should trigger
- `calculate_stop_loss_price() -> Optional[Decimal]` - Calculate stop-loss from percentage
- `calculate_take_profit_price() -> Optional[Decimal]` - Calculate take-profit from percentage
- `update_current_price(price: Decimal) -> None` - Update current price and timestamp
- `calculate_pnl() -> Decimal` - Calculate unrealized P&L
- `calculate_pnl_percentage() -> Optional[Decimal]` - Calculate P&L as percentage
- `to_dict() -> Dict[str, Any]` - Serialize to dictionary
- `from_dict(data: Dict) -> MonitoredPosition` - Deserialize from dictionary

### 3. `PositionMonitorConfig` (Dataclass)
**Purpose**: Configuration for position monitor

**Attributes**:
- `check_interval_seconds: float = 1.0` - How often to check positions
- `max_price_fetch_retries: int = 3` - Max retries for price fetching
- `price_fetch_timeout_seconds: float = 5.0` - Timeout for price fetching
- `auto_restart: bool = True` - Auto-restart on errors
- `log_all_checks: bool = False` - Log every position check (verbose)
- `audit_log_enabled: bool = True` - Enable audit logging
- `persist_state: bool = True` - Persist state to database
- `state_sync_interval_seconds: float = 10.0` - State sync interval
- `execute_stops_automatically: bool = True` - Auto-execute stops when triggered
- `stop_execution_timeout_seconds: float = 30.0` - Stop execution timeout

### 4. `PositionMonitor` (Class)
**Purpose**: Continuously monitors open positions and executes stops automatically

**Key Methods**:

#### `__init__(broker, config, on_stop_triggered)`
- Initialize monitor with broker connection and configuration
- Creates unique monitor_id for state persistence

#### `async start() -> bool`
- Start monitoring positions
- Loads existing positions from broker
- Loads persisted state from database
- Starts monitoring loop and state sync loop

#### `async stop() -> bool`
- Stop monitoring positions
- Cancel async tasks
- Final state sync before shutdown
- Log statistics

#### `async add_position(position: MonitoredPosition) -> bool`
- Add a position to monitoring
- Calculate stop/take prices from percentages if needed
- Add to audit log

#### `async remove_position(position_id: str) -> bool`
- Remove a position from monitoring
- Add to audit log

#### `async _load_positions_from_broker() -> None`
- Load open positions from broker
- Handle different broker position formats
- Add to monitored positions

#### `async _load_state_from_db() -> None`
- CRITICAL: Load persisted state for recovery after restart
- Deserialize positions from JSON
- Restore in-memory state

#### `async _monitor_loop() -> None`
- Main monitoring loop - checks positions every second
- Auto-restart on errors if configured

#### `async _check_all_positions() -> None`
- Check all monitored positions for stop/take triggers
- Fetch current prices
- Update position prices
- Trigger stops when conditions met

#### `async _fetch_current_prices(symbols: List[str]) -> Dict[str, Decimal]`
- Fetch current prices for multiple symbols
- Support for different broker APIs (get_quote, get_market_data)
- Timeout handling

#### `async _on_stop_loss_triggered(position: MonitoredPosition) -> None`
- Handle stop-loss trigger
- Log critical alert
- Execute stop if configured
- Call callback if provided

#### `async _on_take_profit_triggered(position: MonitoredPosition) -> None`
- Handle take-profit trigger
- Log info
- Execute take-profit if configured
- Call callback if provided

#### `async _state_sync_loop() -> None`
- Periodically sync state to database

#### `async _sync_state() -> None`
- CRITICAL: Sync current state to database for recovery
- Serialize positions to JSON
- Update or create PositionState record

#### Getter Methods
- `get_monitored_positions() -> List[MonitoredPosition]`
- `get_active_positions() -> List[MonitoredPosition]`
- `get_position(position_id: str) -> Optional[MonitoredPosition]`
- `get_positions_by_symbol(symbol: str) -> List[MonitoredPosition]`
- `get_audit_log(limit: int = 100) -> List[Dict]`
- `get_statistics() -> Dict[str, Any]`
- `get_position_summary() -> Dict[str, Any]`

---

## Business Logic

### Stop-Loss/TP Trigger Logic

**LONG Position**:
- Stop-loss triggers when: `current_price <= stop_loss_price`
- Take-profit triggers when: `current_price >= take_profit_price`

**SHORT Position**:
- Stop-loss triggers when: `current_price >= stop_loss_price`
- Take-profit triggers when: `current_price <= take_profit_price`

### P&L Calculation

**LONG P&L**: `(current_price - entry_price) * quantity`
**SHORT P&L**: `(entry_price - current_price) * quantity`

### State Persistence
- Positions serialized to JSON in PositionState table
- Syncs every 10 seconds (configurable)
- Survives process restart

### Monitoring Loop
1. Sleep for check_interval_seconds
2. Fetch current prices for all symbols
3. Check each position for stop/TP triggers
4. Execute stops if triggered
5. Update statistics

---

## Data Models

### `MonitoredPosition`
```python
@dataclass
class MonitoredPosition:
    position_id: str
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry_price: Decimal
    quantity: Decimal
    current_price: Decimal
    stop_loss_price: Optional[Decimal] = None
    stop_loss_pct: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    take_profit_pct: Optional[Decimal] = None
    status: PositionStatus = PositionStatus.ACTIVE
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_checked: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    check_count: int = 0
```

### `PositionMonitorConfig`
```python
@dataclass
class PositionMonitorConfig:
    check_interval_seconds: float = 1.0
    max_price_fetch_retries: int = 3
    price_fetch_timeout_seconds: float = 5.0
    auto_restart: bool = True
    log_all_checks: bool = False
    audit_log_enabled: bool = True
    persist_state: bool = True
    state_sync_interval_seconds: float = 10.0
    execute_stops_automatically: bool = True
    stop_execution_timeout_seconds: float = 30.0
```

---

## API Contracts

### Public API

#### Adding a Position
```python
position = MonitoredPosition(
    position_id="pos_1",
    symbol="AAPL",
    side="LONG",
    entry_price=Decimal("150.0"),
    quantity=Decimal("100"),
    current_price=Decimal("150.0"),
    stop_loss_pct=Decimal("0.05"),  # 5% stop-loss
)
await monitor.add_position(position)
```

#### Getting Position Status
```python
position = monitor.get_position("pos_1")
print(position.status)
print(position.calculate_pnl())
```

#### Getting Statistics
```python
stats = monitor.get_statistics()
print(stats["active_positions"])
print(stats["stop_loss_triggered_count"])
```

---

## Error Handling

### Exception Handling Strategy

**Database Errors** (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError):
- Caught in `_sync_state()`
- Logged with `exc_info=True`
- Does not crash the monitor

**Network Errors** (ConnectionError, TimeoutError, HTTPError):
- Caught in `_load_positions_from_broker()` and `_fetch_current_prices()`
- Logged with error level
- Does not crash the monitor

**ValueError, TypeError, KeyError, AttributeError, IndexError**:
- Caught in callbacks and execution
- Logged with error level
- Position marked as ERROR status

**AsyncIO Errors** (asyncio.TimeoutError, asyncio.CancelledError):
- Handled in monitoring loops
- Auto-restart if configured

---

## Performance Considerations

### Critical Performance Requirements

1. **Check Frequency**: Every 1 second (configurable)
   - Must check all positions within check interval
   - Use list() to avoid dictionary changed size errors

2. **Price Fetching**:
   - Timeout: 5 seconds per symbol
   - Max retries: 3
   - Parallel fetching possible for multiple symbols

3. **State Persistence**:
   - Sync every 10 seconds (configurable)
   - Avoid blocking monitoring loop
   - Use sync database session (get_sync_db)

4. **Memory Management**:
   - Audit log can grow - limit with `limit` parameter
   - Positions stored in memory - consider pagination for large portfolios

---

## Testing Strategy

### Unit Tests Required

1. **MonitoredPosition**:
   - Test stop-loss trigger logic for LONG/SHORT
   - Test take-profit trigger logic for LONG/SHORT
   - Test P&L calculation
   - Test serialization/deserialization

2. **PositionMonitor**:
   - Test start/stop lifecycle
   - Test add/remove positions
   - Test state persistence
   - Test state recovery after restart
   - Test stop-loss execution
   - Test take-profit execution

3. **Edge Cases**:
   - Zero quantity
   - Zero/negative prices
   - Missing broker methods
   - Database connection failures
   - Network timeouts

### Integration Tests Required

1. Test with real broker connection
2. Test state persistence across restarts
3. Test stop execution through broker
4. Test concurrent position monitoring

### Test Coverage Target: >90%

This is a **CRITICAL** component - high test coverage is required.

---

## Security Considerations

1. **Audit Trail**: All position changes logged
2. **No Hardcoded Secrets**: Uses broker dependency injection
3. **Input Validation**: Prices validated with `validate_price()`
4. **Database Security**: Uses SQLAlchemy ORM (SQL injection protected)

---

## Compliance with Trading Rules

### TRD-002: Risk Validation
- Prices validated before execution
- Quantity validated (> 0)
- Stop-loss/take-profit prices validated

### TRD-004: Audit Trail
- All position additions logged
- All removals logged with final P&L
- All stop-loss triggers logged (CRITICAL level)
- All take-profit triggers logged (INFO level)
- Audit log accessible via `get_audit_log()`

### TRD-003: Position Limits
- Position sizes tracked via `quantity`
- Concentration visible via `get_position_summary()`

---

## Configuration

### Required Configuration

```yaml
position_monitor:
  check_interval_seconds: 1.0
  max_price_fetch_retries: 3
  price_fetch_timeout_seconds: 5.0
  auto_restart: true
  log_all_checks: false
  audit_log_enabled: true
  persist_state: true
  state_sync_interval_seconds: 10.0
  execute_stops_automatically: true
  stop_execution_timeout_seconds: 30.0
```

---

## Monitoring & Observability

### Key Metrics to Track
- `uptime_seconds` - How long monitor has been running
- `total_checks` - Number of position checks performed
- `stop_loss_triggered` - Number of stop-loss triggers
- `take_profit_triggered` - Number of take-profit triggers
- `execution_failures` - Number of failed stop executions
- `active_positions` - Current number of active positions

### Log Levels Used
- `logger.critical()` - Stop-loss triggered
- `logger.info()` - Take-profit triggered, position added/removed
- `logger.warning()` - Price fetch failures
- `logger.error()` - Execution failures
- `logger.debug()` - State sync, individual checks

---

## Deployment Notes

1. **Database Migration Required**:
   - PositionState table must exist
   - Schema: `monitor_id`, `positions_json`, `last_sync`, `is_active`, `version`

2. **Broker Connection**:
   - Must implement `get_positions()` method
   - Must implement `get_quote()` or `get_market_data()` method

3. **Process Management**:
   - Should run as a daemon/service
   - Auto-restart on crash
   - Monitor health via `get_statistics()`

4. **State Recovery**:
   - Automatically loads state on startup
   - Tests should verify recovery works

---

## Audit Status: **PASSED**

**Date**: 2026-02-07
**Auditor**: GAP Audit Batch 0103
**Violations**: 0
**Notes**: Production-critical component with excellent error handling, state persistence, and audit logging. Code is well-structured with proper async patterns throughout.

---
