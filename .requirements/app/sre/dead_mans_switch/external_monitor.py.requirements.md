# Requirements: sre/dead_mans_switch/external_monitor.py

## Source File Analysis
- **File Path**: `app/sre/dead_mans_switch/external_monitor.py`
- **Lines of Code**: 535
- **Purpose**: External health check monitoring service
- **Audit Status**: PASSED

## Purpose
Independent external monitoring service:
- Periodic health checks
- Failure detection and alerting
- Multiple alert channels (Email, Slack, PagerDuty, etc.)
- Database persistence

## Dependencies

### External Dependencies
- `aiosqlite`: Async database operations
- `asyncio`: Async operations
- `aiohttp`: HTTP client for health checks

### Internal Dependencies
None

## Classes/Functions

### Main Classes

1. **AlertChannel (Enum)**
   - EMAIL, SLACK, PAGERDUTY, TWILIO, WEBHOOK

2. **MonitorConfig (dataclass)**
   - Health check URL and intervals
   - Alert thresholds
   - Channel configs

3. **HealthCheckResult (dataclass)**
   - Result of health check

4. **ExternalMonitor** (Main class)
   - `__init__(config)`
   - `initialize()`
   - `start()`, `stop()`
   - `_monitor_loop()`
   - `_perform_health_check() -> HealthCheckResult`
   - `_check_alert_conditions(result)`
   - `_send_alert(result)`
   - `_send_email/slack/pagerduty/twilio/webhook_alert(result)`

## Business Logic

### Alert Conditions
- Consecutive failures >= `max_consecutive_failures`
- Time since first failure >= `alert_after_minutes`

### Alert Channels
- Each channel has dedicated implementation
- Failure of one channel doesn't block others
- All alerts logged to database

## API Contracts

### start()
```python
async def start() -> None
```

**Preconditions:**
- Monitor initialized
- Health check URL configured

**Postconditions:**
- Background monitoring started
- Health checks running periodically

## Compliance with BASE_RULES.md

### Passed Rules
- **TYP-001**: Type hints
- **ASYNC-001**: Proper async
- **LOG-001**: Structured logging
- **SOL-001**: Single responsibility

### Audit Status: PASSED

Clean external monitoring implementation:
1. Independent monitoring (separate from service)
2. Multiple alert channels
3. Database persistence
4. Graceful degradation
5. Comprehensive alerting

---
*Audited on 2025-02-07*
*Reference: BASE_RULES.md*
