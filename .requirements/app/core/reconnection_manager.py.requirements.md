# reconnection_manager.py

## Purpose
Manages reconnection logic with exponential backoff, jitter, and configurable retry limits for resilient 24/7 trading operations.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses dataclasses for configuration and statistics.

### ReconnectionConfig Class
```python
@dataclass
class ReconnectionConfig:
    max_attempts: int = 10                      # REQUIRED - Maximum retry attempts before giving up
    base_delay_seconds: float = 1.0             # REQUIRED - Initial backoff delay (first retry)
    max_delay_seconds: float = 60.0             # REQUIRED - Maximum backoff cap (prevents excessive waits)
    exponential_base: float = 2.0               # REQUIRED - Backoff multiplier (delay doubles each retry)
    jitter: bool = True                         # OPTIONAL - Add random jitter to prevent thundering herd
    jitter_factor: float = 0.1                  # OPTIONAL - Jitter amount (±10% of delay)
    on_attempt: Optional[Callable[[int], None]] = None      # Callback on each attempt (attempt_number)
    on_success: Optional[Callable[[int], None]] = None      # Callback on successful connection
    on_failure: Optional[Callable[[], None]] = None         # Callback after all attempts fail
    alert_after_attempts: int = 3               # Alert threshold - trigger alert after N failures
    alert_callback: Optional[Callable[[int], None]] = None  # Alert callback (attempt_number)
```

### ReconnectionStats Class
```python
@dataclass
class ReconnectionStats:
    total_attempts: int = 0                     # Total connection attempts (success + failure)
    successful_connections: int = 0             # Counter for successful connections
    failed_connections: int = 0                 # Counter for failed connection batches
    last_connection_time: Optional[datetime] = None  # Timestamp of most recent successful connection
    last_failure_time: Optional[datetime] = None    # Timestamp of most recent failed batch
    current_backoff_seconds: float = 0.0        # Current backoff delay (for monitoring)

    @property
    def success_rate(self) -> float:            # Calculated: successful_connections / total_attempts
                                                # Returns 0.0 if total_attempts == 0
```

### ReconnectionManager Class
```python
class ReconnectionManager:
    service_name: str                           # REQUIRED - Name of service being reconnected (for logging)
    config: ReconnectionConfig                  # REQUIRED - Reconnection behavior configuration
    stats: ReconnectionStats                    # COMPOSED - Connection statistics tracking
```

---

## Function Signatures (Contracts)

### `ReconnectionManager.__init__(service_name: str, config: Optional[ReconnectionConfig] = None) -> None`
**Pre:** service_name is non-empty string
**Post:** Manager initialized with default config if none provided, stats at zero
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs initialization message

### `ReconnectionManager.calculate_backoff(attempt: int) -> float`
**Pre:** attempt >= 0 (zero-indexed: 0 = first retry, 1 = second retry, etc.)
**Post:** Returns delay in seconds following exponential backoff with jitter
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Updates stats.current_backoff_seconds

**Formula:**
```
delay = min(base_delay * (exponential_base ^ attempt), max_delay)
if jitter_enabled:
    jitter_amount = delay * jitter_factor
    delay = delay + random.uniform(-jitter_amount, jitter_amount)
delay = max(0, delay)  # Ensure non-negative
return delay
```

### `async ReconnectionManager.connect_with_backoff(connect_func: Callable[[], Any]) -> Optional[Any]`
**Pre:** connect_func is async callable that returns connection object or raises exception
**Post:** Returns connection object if successful, None if all attempts exhausted
**Raises:** ❌ No (catches and logs all exceptions)
**Retry:** ✅ Yes - Up to max_attempts with exponential backoff
**Side Effects:**
- Updates stats (total_attempts, successful_connections, last_connection_time)
- Calls on_attempt callback before each attempt
- Calls on_success callback after successful connection
- Calls on_failure callback after all attempts fail
- Calls alert_callback after alert_after_attempts threshold
- Logs each attempt, success, failure

### `async ReconnectionManager.maintain_connection(connect_func: Callable[[], Any], check_func: Optional[Callable[[], bool]] = None, reconnect_delay: float = 1.0) -> None`
**Pre:** connect_func is async callable, check_func returns bool if provided
**Post:** Runs forever, maintaining connection and reconnecting if lost
**Raises:** asyncio.CancelledError if task is cancelled
**Retry:** ✅ Yes - Infinite reconnection attempts
**Side Effects:**
- Calls connect_with_backoff for initial connection
- Monitors connection health via check_func every 5 seconds
- Reconnects after reconnect_delay if connection lost
- Logs connection loss and reconnection attempts

### `ReconnectionManager.get_stats() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with all statistics and computed success_rate
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] calculate_backoff(0) returns base_delay (1.0s by default)
- [ ] calculate_backoff(1) returns 2.0s (1.0 * 2^1)
- [ ] calculate_backoff(2) returns 4.0s (1.0 * 2^2)
- [ ] calculate_backoff(10) caps at max_delay (60.0s)
- [ ] Jitter adds ±10% random variation when enabled
- [ ] Jitter is disabled when jitter=False
- [ ] connect_with_backoff attempts connection up to max_attempts times
- [ ] connect_with_backoff returns connection object on success
- [ ] connect_with_backoff returns None after all attempts fail
- [ ] connect_with_backoff calls on_attempt callback before each attempt
- [ ] connect_with_backoff calls on_success callback on successful connection
- [ ] connect_with_backoff calls on_failure callback after all attempts fail
- [ ] connect_with_backoff calls alert_callback after alert_after_attempts failures
- [ ] connect_with_backoff updates stats correctly
- [ ] connect_with_backoff logs each attempt with attempt number
- [ ] connect_with_backoff catches asyncio.TimeoutError
- [ ] connect_with_backoff catches ConnectionError and OSError
- [ ] connect_with_backoff catches generic Exception
- [ ] connect_with_backoff uses 30 second timeout for connection attempts
- [ ] maintain_connection runs indefinitely until cancelled
- [ ] maintain_connection calls check_func every 5 seconds if provided
- [ ] maintain_connection reconnects after reconnect_delay if connection lost
- [ ] get_stats returns dict with all stats fields
- [ ] get_stats includes calculated success_rate
- [ ] get_stats serializes datetime objects to ISO format strings
- [ ] stats.success_rate returns 0.0 when total_attempts is 0

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ASYNC-001 | BASE_RULES.md | Use async def for async functions | ✅ OK |
| ASYNC-002 | BASE_RULES.md | Await async calls | ✅ OK |
| ASYNC-003 | BASE_RULES.md | Use async context managers for async resources | ⚠️ NOT APPLIED - No async resources used |
| ASYNC-004 | BASE_RULES.md | No blocking in async functions | ✅ OK - No time.sleep() |
| ASYNC-005 | BASE_RULES.md | Set timeouts for external calls | ✅ OK - 30s timeout on connect_func |
| ASYNC-006 | BASE_RULES.md | Handle asyncio.TimeoutError | ✅ OK |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ PARTIAL - Logs exception message, not full traceback |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - All exceptions caught |
| CC-007 | BASE_RULES.md | Small functions (< 20 lines) | ⚠️ PARTIAL - Some functions exceed 20 lines |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |

### Resilience-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| RES-001 | Exponential backoff prevents server overload | ✅ OK |
| RES-002 | Jitter prevents thundering herd | ✅ OK |
| RES-003 | Max delay cap prevents excessive waits | ✅ OK |
| RES-004 | Timeouts prevent hanging connections | ✅ OK |
| RES-005 | All exceptions are caught and logged | ✅ OK |
| RES-006 | Stats tracking enables monitoring | ✅ OK |
| RES-007 | Callbacks enable custom alerting | ✅ OK |
| RES-008 | Infinite retry for maintain_connection | ✅ OK |

---

## Dependencies
- **External:** None (standard library only)
- **Internal:** `app.core.timezone_utils.utc_now` (for timestamp tracking)
- **Standard Library:** `asyncio`, `logging`, `random`, `datetime`, `dataclasses`, `typing`

---

## Required Tests
- **tests/core/test_reconnection_manager.py:**
  - Test calculate_backoff(0) returns base_delay
  - Test calculate_backoff(1) returns base_delay * 2
  - Test calculate_backoff(2) returns base_delay * 4
  - Test calculate_backoff(10) caps at max_delay
  - Test calculate_backoff with jitter adds random variation
  - Test calculate_backoff without jitter is deterministic
  - Test calculate_backoff updates stats.current_backoff_seconds
  - Test connect_with_backoff succeeds on first attempt
  - Test connect_with_backoff retries on failure
  - Test connect_with_backoff returns None after max_attempts
  - Test connect_with_backoff calls on_attempt callback
  - Test connect_with_backoff calls on_success callback
  - Test connect_with_backoff calls on_failure callback
  - Test connect_with_backoff calls alert_callback after threshold
  - Test connect_with_backoff updates stats.total_attempts
  - Test connect_with_backoff updates stats.successful_connections
  - Test connect_with_backoff updates stats.last_connection_time
  - Test connect_with_backoff handles asyncio.TimeoutError
  - Test connect_with_backoff handles ConnectionError
  - Test connect_with_backoff handles OSError
  - Test connect_with_backoff handles generic Exception
  - Test connect_with_backoff uses 30 second timeout
  - Test maintain_connection runs until cancelled
  - Test maintain_connection calls check_func every 5 seconds
  - Test maintain_connection reconnects after check_func returns False
  - Test maintain_connection reconnects after reconnect_delay
  - Test maintain_connection handles asyncio.CancelledError
  - Test get_stats returns dict with all fields
  - Test get_stats includes calculated success_rate
  - Test get_stats serializes datetimes to ISO format
  - Test stats.success_rate returns 0.0 when total_attempts is 0
  - Test stats.success_rate calculates correctly for various totals
  - Edge case: max_attempts = 0 (no attempts)
  - Edge case: max_attempts = 1 (single attempt)
  - Edge case: base_delay = 0 (no initial delay)
  - Edge case: max_delay < base_delay (immediate cap)
  - Edge case: jitter_factor = 0 (no jitter even if enabled)
  - Edge case: jitter_factor = 1 (100% variation)
  - Edge case: alert_after_attempts > max_attempts (never called)

---

## Notes
- **Exponential Backoff:** Default sequence is 1s, 2s, 4s, 8s, 16s, 32s, 60s, 60s, 60s, 60s (capped at 60s).
- **Jitter Purpose:** Random variation prevents multiple clients from retrying simultaneously (thundering herd problem).
- **Timeout:** 30 second timeout is hardcoded. Consider making configurable via ReconnectionConfig for production.
- **Callback Safety:** Callbacks are called from async context. Ensure they don't perform blocking operations.
- **Stats Thread Safety:** stats object is not thread-safe. If used from multiple tasks, add locking.
- **Maintain Connection:** Runs forever. Must be cancelled via asyncio.Task.cancel() or wrapped in asyncio.TaskGroup.
- **Logging Level:** Connection failures are logged as WARNING, not ERROR. This prevents log spam during transient outages.
- **Production Tuning:** For production, consider:
  - Increase max_attempts to 20-30 for longer outages
  - Set alert_after_attempts to 5 for earlier alerting
  - Use monitoring service with alert_callback to page on-call
  - Increase timeout to 60s for slow connections
