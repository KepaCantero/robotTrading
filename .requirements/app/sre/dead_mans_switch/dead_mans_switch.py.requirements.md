# Requirements: sre/dead_mans_switch/dead_mans_switch.py

## Source File Analysis
- **File Path**: `app/sre/dead_mans_switch/dead_mans_switch.py`
- **Lines of Code**: 756
- **Purpose**: Dead man's switch health check monitoring
- **Audit Status**: PASSED

## Purpose
Implements dead man's switch for service health:
- Periodic health check pings
- Missed ping detection
- Auto-recovery actions
- Alerting on failures

## Dependencies

### External Dependencies
- `aiosqlite`: Async database operations
- `asyncio`: Async operations
- `signal`: Process signaling
- `subprocess`: Process execution

### Internal Dependencies
None

## Classes/Functions

### Main Classes

1. **SwitchStatus (Enum)**
   - ACTIVE, TRIGGERED, DISABLED, RECOVERING

2. **HealthCheckConfig (dataclass)**
   - Ping interval, timeout, grace period
   - Alerting config
   - Auto-recovery settings

3. **HeartbeatRecord (dataclass)**
   - Individual ping record

4. **IncidentRecord (dataclass)**
   - Incident details and recovery

5. **DeadMansSwitch** (Main class)
   - `__init__(service_name, config)`
   - `initialize()`
   - `start()`, `stop()`
   - `ping(metadata) -> bool`
   - `resolve_incident(incident_id) -> bool`
   - `_monitor_loop()`
   - `_handle_timeout()`
   - `_attempt_recovery(incident)`

## Business Logic

### Monitoring Logic
- Expects pings every `ping_interval_seconds`
- Triggers after `timeout_seconds` without ping
- Requires `require_consecutive_failures` consecutive failures

### Recovery Actions
1. Execute restart command if configured
2. Send SIGTERM to process
3. Enter degraded mode

### Callbacks
- `on_trigger`: Called when switch triggers
- `on_recover`: Called when incident resolved
- `on_degraded`: Called when entering degraded mode

## API Contracts

### ping()
```python
async def ping(metadata: Optional[Dict[str, Any]] = None) -> bool
```

**Preconditions:**
- Switch is initialized

**Postconditions:**
- Heartbeat recorded
- Consecutive failures reset on success

## Compliance with BASE_RULES.md

### Passed Rules
- **TYP-001**: Type hints
- **ASYNC-001**: Proper async
- **LOG-001**: Structured logging
- **SOL-001**: Single responsibility
- **DP-004**: Dependency injection

### Audit Status: PASSED

Excellent dead man's switch implementation:
1. Configurable timing
2. Auto-recovery actions
3. Incident tracking
4. Callback system
5. Grace period support

---
*Audited on 2025-02-07*
*Reference: BASE_RULES.md*
