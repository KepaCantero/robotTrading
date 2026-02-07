# Requirements: services/scheduling/market_scheduler.py

## Source File Analysis
- **File Path**: `app/services/scheduling/market_scheduler.py`
- **Lines of Code**: 697
- **Language**: Python 3
- **Purpose**: Schedule tasks based on market hours (24/7, stocks, forex)

## Purpose
Efficiently manages task scheduling based on market hours:
- 24/7 markets (crypto): Continuous operation
- Stock markets (6.5h/day): US, EU, Asia
- Timezone handling (US, EU, Asia)
- Market holidays
- Graceful startup/shutdown
- CPU-efficient by only running when markets open

## Dependencies
- **Internal**:
  - `app.core.timezone_utils.utc_now` - UTC timestamp generation
- **External**:
  - `asyncio` - Async operations
  - `pytz` - Timezone handling
  - `logging` - Structured logging
  - `dataclasses` - Data structures
  - `enum.Enum` - Type-safe enums
  - `typing` - Type hints

## Classes/Functions

### Enums
- **MarketType** (Enum): CRYPTO, FOREX, STOCKS_US, STOCKS_EU, STOCKS_ASIA
- **MarketStatus** (Enum): OPEN, CLOSED, PRE_MARKET, AFTER_HOURS, HOLIDAY, WEEKEND

### Data Classes

#### MarketSchedule (dataclass)
- **Purpose**: Schedule info for a market
- **Fields**: market_type, timezone_str, open_time, close_time, lunch_start, lunch_end, weekends, holidays
- **Methods**: `is_24_7()` - Check if 24/7 market

#### ScheduledTask (dataclass)
- **Purpose**: Task scheduled for market conditions
- **Fields**: task_id, name, market_types, handler, run_when_closed, enabled, last_run, run_count, error_count

### MarketScheduler
- **Purpose**: Main scheduler orchestrator
- **Key Methods**:
  - `start()` - Start all scheduled tasks
  - `stop()` - Stop all tasks gracefully
  - `schedule_task()` - Add a task
  - `unschedule_task()` - Remove a task
  - `enable_task()` / `disable_task()` - Toggle task
  - `get_market_status()` - Get current market status
  - `wait_until_market_open()` - Block until market opens
  - `is_market_open()` - Quick synchronous check
  - `add_holiday()` / `remove_holiday()` - Manage holidays
  - `get_task_info()` - Get task details
  - `list_tasks()` - List all tasks
  - `run_task_once()` - Manual task execution

### Default Market Schedules
```python
MARKET_SCHEDULES = {
    MarketType.CRYPTO: 24/7 (UTC)
    MarketType.FOREX: 24/5 (UTC, weekends off)
    MarketType.STOCKS_US: 9:30-16:00 ET
    MarketType.STOCKS_EU: 9:00-17:30 CET
    MarketType.STOCKS_ASIA: 9:00-15:00 JST (with lunch break)
}
```

## Business Logic

### Task Execution Flow
1. Start creates background asyncio task for each market type
2. Each task loop:
   - Check if market is open
   - Get enabled tasks for this market
   - Run tasks if open or `run_when_closed=True`
   - Wait appropriate interval (60s default)
3. Stop cancels all tasks and waits for completion

### Market Status Determination
For non-24/7 markets:
1. Check weekend (Saturday=5, Sunday=6)
2. Check holidays list
3. Check time range:
   - Before open: CLOSED
   - Between open and close: OPEN (unless lunch)
   - After close: AFTER_HOURS
   - During lunch: CLOSED

### CPU Efficiency
- 24/7 markets: Run every 60s
- Scheduled markets: Only run during open hours
- Tasks for closed markets don't execute (unless `run_when_closed=True`)

### Error Handling
- Catches asyncio.CancelledError (shutdown)
- Catches connection/timeout errors (continues running)
- Logs all errors with task context

## Data Models
- MarketSchedule (dataclass) - Market schedule config
- ScheduledTask (dataclass) - Task configuration
- MARKET_SCHEDULES (dict) - Default schedules

## API Contracts
```python
async def start() -> bool
async def stop() -> bool

def schedule_task(
    task_id: str,
    name: str,
    market_types: List[MarketType],
    handler: Callable,
    run_when_closed: bool = False,
    enabled: bool = True
) -> None

async def get_market_status(market_type: MarketType) -> MarketStatus
```

## Error Handling
- Returns False if already running/stopped
- Raises ValueError if task_id already exists
- Handles asyncio.CancelledError gracefully
- Catches and logs network/timeout errors
- Continues running after errors

## Performance Considerations
- Each market type has its own asyncio task
- 60-second check interval (configurable)
- O(n) task filtering where n = total tasks
- Minimal memory overhead

## Testing Strategy
- Test market status determination
- Test task scheduling/unscheduling
- Test enable/disable
- Test weekend/holiday logic
- Test timezone handling

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits (mostly)
- FMT-002: Proper imports (stdlib → third-party → local)
- FMT-006: F-strings used
- FMT-007: default_factory for mutable defaults

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax (List, Dict, Optional)
- TYP-005: Dataclass fields typed
- TYP-006: Callable properly typed

### Async Patterns
- ASYNC-001: All async functions marked
- ASYNC-002: All async calls properly awaited
- ASYNC-003: Async context manager possible (start/stop pattern)
- ASYNC-004: Uses asyncio.sleep() not time.sleep()
- ASYNC-005: Timeout support via wait parameters
- ASYNC-006: Handles asyncio.CancelledError
- ASYNC-008: Uses asyncio.gather() for shutdown

### Clean Code
- CC-001: Descriptive names
- CC-006: Comprehensive error handling
- CC-007: Reasonable function length (< 50 lines)

### Logging
- LOG-001: Uses logging module
- LOG-003: Appropriate levels (info, warning, error)
- LOG-004: Error logging with exc_info=True
- LOG-006: Logs state changes (start, stop, task scheduling)

### Timezone Handling
- Uses utc_now() for consistent timestamps
- Uses pytz for timezone conversions
- Proper weekend detection with weekday()

### Design Patterns
- DP-005: Singleton-like (one scheduler instance)
- DP-010: Observer pattern (tasks observe market status)

## Audit Status
**Status**: PASSED**

### Strengths
1. Excellent async implementation with proper cancellation handling
2. Comprehensive market type coverage (24/7, stocks, forex)
3. Proper timezone handling with pytz
4. Efficient CPU usage (only runs when markets open)
5. Good error handling with continued operation
6. Task enable/disable functionality
7. Holiday support
8. Graceful shutdown with gather()
9. Proper logging throughout
10. Market status determination is robust

### Minor Observations
1. Some lines slightly exceed 100 chars (minor)
2. Could add WebSocket support for real-time market status
3. Could add task priorities

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready market scheduler
- Proper async patterns throughout
- Timezone-safe implementation
- Efficient resource usage

### Integration Points
- Data fetchers: Only run when markets open
- Strategy execution: Respects market hours
- Risk monitoring: Continuous for 24/7, scheduled for stocks
- Reporting: Run when markets closed

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0081*
*Status: PASSED*
