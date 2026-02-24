# Market Scheduler - Phase 3.1

## Overview

The Market Scheduler is a critical component for multi-market algorithmic trading operations. It efficiently manages task execution based on market hours, ensuring CPU resources are used optimally by:

- Running 24/7 tasks continuously for crypto and forex markets
- Scheduling stock market tasks only during open hours (US: 9:30-16:00 ET, EU: 9:00-17:30 CET, Asia: 9:00-15:00 JST)
- Respecting market holidays and weekends
- Handling timezone differences across global markets
- Providing graceful startup and shutdown

## Problem Statement

**Criticality**: HIGH for multi-market operations

The system was originally designed for stock market hours (6.5 hours/day). However, crypto and forex markets operate 24/7. Without proper scheduling:

- CPU cycles are wasted polling closed markets
- Tasks run at inappropriate times
- System resources are inefficiently utilized

## Solution

The Market Scheduler provides intelligent task scheduling that:

1. **Separates task execution by market type**: Each market type (crypto, forex, stocks) has its own execution loop
2. **Optimizes CPU usage**: Only runs tasks when markets are open (or when configured to run always)
3. **Respects market schedules**: Handles holidays, weekends, and trading hours correctly
4. **Supports timezone awareness**: Properly handles US, EU, and Asian market timezones

## Architecture

```
MarketScheduler
├── Task Loops (one per market type)
│   ├── Crypto Loop (24/7)
│   ├── Forex Loop (24/5)
│   ├── US Stocks Loop (9:30-16:00 ET)
│   ├── EU Stocks Loop (9:00-17:30 CET)
│   └── Asia Stocks Loop (9:00-15:00 JST)
└── Scheduled Tasks
    ├── Task ID
    ├── Market Types
    ├── Handler (async callable)
    └── Configuration (enabled, run_when_closed, etc.)
```

## Installation

The scheduler is part of the algoTrading system. No additional dependencies are required beyond the existing project dependencies.

## Quick Start

```python
from app.services.scheduling import MarketScheduler, MarketType

# Create scheduler
scheduler = MarketScheduler(
    check_interval_24_7=60.0,      # Check every 60 seconds for 24/7 markets
    check_interval_scheduled=60.0, # Check every 60 seconds for scheduled markets
)

# Define your task handler
async def crypto_monitoring_task():
    # Your trading logic here
    print("Monitoring crypto markets...")

# Schedule the task
scheduler.schedule_task(
    task_id="crypto_monitor",
    name="Crypto Market Monitor",
    market_types=[MarketType.CRYPTO],
    handler=crypto_monitoring_task,
)

# Start the scheduler
await scheduler.start()

# Let it run...
# In production, run indefinitely

# Stop when done
await scheduler.stop()
```

## Market Types

| Market Type | Hours | Timezone | Weekends |
|-------------|-------|----------|----------|
| CRYPTO | 24/7 | UTC | Yes |
| FOREX | 24/5 | UTC | No |
| STOCKS_US | 9:30-16:00 | America/New_York | No |
| STOCKS_EU | 9:00-17:30 | Europe/Madrid | No |
| STOCKS_ASIA | 9:00-15:00 | Asia/Tokyo | No |

## Market Status

The scheduler can report the current status of any market:

- `OPEN`: Market is open for trading
- `CLOSED`: Market is closed (outside trading hours)
- `PRE_MARKET`: Pre-market trading (for some markets)
- `AFTER_HOURS`: After-hours trading (for some markets)
- `HOLIDAY`: Market is closed for holiday
- `WEEKEND`: Market is closed for weekend

```python
status = await scheduler.get_market_status(MarketType.STOCKS_US)
if status == MarketStatus.OPEN:
    print("US stock market is open")
```

## Task Configuration

### Basic Task

```python
scheduler.schedule_task(
    task_id="my_task",
    name="My Trading Task",
    market_types=[MarketType.CRYPTO],
    handler=my_async_handler,
)
```

### Multi-Market Task

```python
scheduler.schedule_task(
    task_id="multi_market_task",
    name="Multi-Market Strategy",
    market_types=[MarketType.CRYPTO, MarketType.FOREX],
    handler=my_async_handler,
)
```

### Maintenance Task (Run When Closed)

```python
scheduler.schedule_task(
    task_id="data_sync",
    name="Data Synchronization",
    market_types=[MarketType.STOCKS_US],
    handler=data_sync_handler,
    run_when_closed=True,  # Runs even when market is closed
)
```

### Disabled Task (Registered But Not Executed)

```python
scheduler.schedule_task(
    task_id="future_task",
    name="Future Task",
    market_types=[MarketType.CRYPTO],
    handler=my_async_handler,
    enabled=False,  # Registered but won't execute until enabled
)
```

## Task Management

### Enable/Disable Tasks

```python
scheduler.disable_task("crypto_monitor")
scheduler.enable_task("crypto_monitor")
```

### Remove Tasks

```python
scheduler.unschedule_task("crypto_monitor")
```

### Run Task Once (Manual Execution)

```python
await scheduler.run_task_once("crypto_monitor")
```

### Get Task Information

```python
info = scheduler.get_task_info("crypto_monitor")
print(f"Runs: {info['run_count']}")
print(f"Errors: {info['error_count']}")
print(f"Last run: {info['last_run']}")
```

### List All Tasks

```python
# All tasks
all_tasks = scheduler.list_tasks()

# Filtered by market type
crypto_tasks = scheduler.list_tasks(MarketType.CRYPTO)
```

## Holiday Management

```python
from datetime import date

# Add holidays
scheduler.add_holiday(MarketType.STOCKS_US, date(2024, 7, 4))   # Independence Day
scheduler.add_holiday(MarketType.STOCKS_US, date(2024, 12, 25)) # Christmas

# Remove holidays
scheduler.remove_holiday(MarketType.STOCKS_US, date(2024, 12, 25))

# Check holidays
schedule = scheduler.get_market_schedule(MarketType.STOCKS_US)
print(f"Holidays: {schedule.holidays}")
```

## Advanced Usage

### Custom Market Schedules

```python
from app.services.scheduling import MarketSchedule, MarketType

custom_schedule = MarketSchedule(
    market_type=MarketType.STOCKS_US,
    timezone_str="America/New_York",
    open_time=time(9, 30),
    close_time=time(16, 0),
    weekends=False,
)

scheduler = MarketScheduler(
    schedules={MarketType.STOCKS_US: custom_schedule}
)
```

### Waiting for Market Open

```python
# Wait until market opens (useful for initialization)
await scheduler.wait_until_market_open(MarketType.STOCKS_US)

# Then execute your logic
await initialize_strategy()
```

### Dynamic Task Management

```python
# Start scheduler
await scheduler.start()

# Add tasks while running
scheduler.schedule_task(
    task_id="new_task",
    name="New Task",
    market_types=[MarketType.CRYPTO],
    handler=new_handler,
)

# Disable/enable while running
scheduler.disable_task("existing_task")
scheduler.enable_task("existing_task")
```

## Testing

Run the unit tests:

```bash
python -m pytest tests/unit/test_market_scheduler.py -v
```

Run the integration tests:

```bash
python -m pytest tests/integration/test_market_scheduler_integration.py -v
```

Run all tests:

```bash
python -m pytest tests/unit/test_market_scheduler.py tests/integration/test_market_scheduler_integration.py -v
```

## Examples

See `examples.py` for comprehensive usage examples:

1. Basic 24/7 crypto monitoring
2. Multi-market strategy
3. Maintenance tasks
4. Dynamic task management
5. Market status monitoring
6. Holiday management
7. Task metrics
8. Waiting for market open

Run examples:

```bash
python -m app.services.scheduling.examples
```

## Performance Considerations

- **CPU Efficiency**: Tasks only run when markets are open (unless `run_when_closed=True`)
- **Configurable Intervals**: Adjust check intervals based on your needs
- **Async Design**: Non-blocking execution using asyncio
- **Error Isolation**: Task errors don't stop the scheduler

## Best Practices

1. **Use Appropriate Intervals**:
   - High-frequency trading: 1-10 seconds
   - Normal trading: 30-60 seconds
   - Monitoring: 1-5 minutes

2. **Handle Errors Gracefully**:
   ```python
   async def my_handler():
       try:
           # Your logic here
       except Exception as e:
           logger.error(f"Error in task: {e}")
           # Task will continue running despite errors
   ```

3. **Use Descriptive Task IDs and Names**:
   ```python
   scheduler.schedule_task(
       task_id="btc_usd_momentum_strategy",  # Specific ID
       name="BTC/USD Momentum Strategy",     # Descriptive name
       ...
   )
   ```

4. **Monitor Task Metrics**:
   ```python
   info = scheduler.get_task_info("my_task")
   if info['error_count'] > 10:
       logger.warning("Task has high error rate")
   ```

5. **Use Maintenance Tasks for System Operations**:
   ```python
   scheduler.schedule_task(
       task_id="health_check",
       name="System Health Check",
       market_types=[MarketType.CRYPTO],
       handler=health_check,
       run_when_closed=True,  # Runs continuously
   )
   ```

## Acceptance Criteria

- [x] Separate tasks for 24/7 and 6.5h markets
- [x] Efficient CPU usage (no polling when markets closed)
- [x] Respects market holidays
- [x] Handles timezone differences (US, EU, Asia)
- [x] Graceful startup/shutdown
- [x] Comprehensive test coverage (26 unit tests, 13 integration tests)
- [x] Documentation and examples

## Files

- `__init__.py`: Module exports
- `market_scheduler.py`: Main scheduler implementation
- `examples.py`: Usage examples
- `README.md`: This file

## Tests

- `tests/unit/test_market_scheduler.py`: Unit tests
- `tests/integration/test_market_scheduler_integration.py`: Integration tests

## Dependencies

- `pytz`: Timezone handling
- `asyncio`: Async task execution
- `app.core.timezone_utils`: UTC time utilities

## License

Part of the algoTrading system.

## Version

Phase 3.1 - Initial implementation
