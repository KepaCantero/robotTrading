# Memory Monitor - Quick Reference Guide

## Overview

The Memory Monitor protects against memory leaks in 24/7 trading operations by monitoring memory usage and taking configurable actions when limits are exceeded.

## Quick Start

### Basic Usage

```python
from app.services.monitoring import (
    get_memory_monitor,
    MemoryConfig,
    MemoryAction,
)

# Create configuration
config = MemoryConfig(
    memory_limit_mb=4096,        # 4GB limit
    warning_threshold_mb=3072,   # 3GB warning
    check_interval_seconds=300,  # 5 minutes
    action=MemoryAction.ALERT_ONLY,
)

# Get monitor instance
monitor = get_memory_monitor(config=config)

# Start monitoring
await monitor.start()
```

### With State Persistence

```python
async def save_trading_state():
    """Save state before restart."""
    # Save portfolio, positions, orders, etc.
    await portfolio.save_state()
    await order_manager.save_state()

monitor = get_memory_monitor(
    config=MemoryConfig(
        action=MemoryAction.RESTART,
        save_state_before_restart=True,
    ),
    state_saver=save_trading_state,
)
```

### With Position Management

```python
async def close_all_positions():
    """Close positions before restart."""
    await trading_engine.close_all_positions()

monitor = get_memory_monitor(
    config=MemoryConfig(
        action=MemoryAction.RESTART,
        close_positions_on_restart=True,
    ),
    position_closer=close_all_positions,
)
```

### With Alerting

```python
def send_alert(message: str):
    """Send alert on memory issues."""
    # Send to Slack, email, etc.
    slack_client.send_message(f"Memory Alert: {message}")
    email_client.send_email("Memory Alert", message)

config = MemoryConfig(
    alert_callback=send_alert,
)

monitor = get_memory_monitor(config=config)
```

## Configuration Options

### MemoryAction Enum

| Action | Description |
|--------|-------------|
| `ALERT_ONLY` | Send alert, take no other action |
| `GARBAGE_COLLECT` | Force Python garbage collection |
| `CLOSE_POSITIONS` | Close all positions |
| `RESTART` | Graceful process restart |

### MemoryConfig Parameters

```python
MemoryConfig(
    memory_limit_mb=4096,              # Critical threshold (MB)
    warning_threshold_mb=3072,         # Warning threshold (MB)
    check_interval_seconds=300.0,      # Check frequency (seconds)
    action=MemoryAction.ALERT_ONLY,    # Action to take
    close_positions_on_restart=False,  # Close positions on restart
    save_state_before_restart=True,    # Save state on restart
    alert_callback=None,               # Alert callback function
)
```

## API Methods

### Monitoring Control

```python
# Start monitoring
await monitor.start()

# Stop monitoring
await monitor.stop()

# Check if monitoring
is_running = monitor._is_monitoring
```

### Memory Statistics

```python
# Get current memory usage
memory_mb = monitor.get_memory_usage()

# Get detailed statistics
stats = monitor.get_detailed_stats()
# Returns: {
#     "rss_mb": 100.5,
#     "vms_mb": 200.3,
#     "percent": 2.5,
#     "available_mb": 8000.0,
#     "gc_objects": 10000,
#     "limit_mb": 4096,
#     "warning_mb": 3072,
# }

# Get monitor statistics
stats = monitor.get_statistics()
# Returns: {
#     "is_monitoring": True,
#     "current_memory": {...},
#     "restart_count": 0,
#     "last_restart": null,
#     "config": {...},
#     "snapshots_count": 10,
# }
```

### Snapshots

```python
# Take a snapshot
snapshot = monitor.take_snapshot()
# Returns: MemorySnapshot(
#     timestamp=datetime(...),
#     rss_mb=100.5,
#     vms_mb=200.3,
#     percent=2.5,
#     available_mb=8000.0,
#     gc_objects=10000,
# )

# Get recent snapshots
snapshots = monitor.get_snapshots(limit=10)

# Convert snapshot to dict
data = snapshot.to_dict()
```

## Production Setup

### Recommended Configuration

```python
from app.services.monitoring import get_memory_monitor, MemoryConfig, MemoryAction

# Production configuration
config = MemoryConfig(
    memory_limit_mb=4096,           # 4GB limit
    warning_threshold_mb=3072,      # 3GB warning
    check_interval_seconds=300.0,   # 5 minutes
    action=MemoryAction.RESTART,    # Auto-restart
    close_positions_on_restart=True,
    save_state_before_restart=True,
    alert_callback=send_alert,
)

# Initialize with callbacks
monitor = get_memory_monitor(
    config=config,
    state_saver=save_trading_state,
    position_closer=close_all_positions,
)

# Start monitoring
await monitor.start()
```

### Integration with Trading Application

```python
from app.services.monitoring import get_memory_monitor, MemoryConfig, MemoryAction

class TradingApplication:
    def __init__(self):
        # Setup memory monitor
        self.memory_monitor = get_memory_monitor(
            config=MemoryConfig(
                memory_limit_mb=4096,
                action=MemoryAction.RESTART,
            ),
            state_saver=self.save_state,
            position_closer=self.close_positions,
        )

    async def start(self):
        # Start monitoring first
        await self.memory_monitor.start()

        # Start trading
        await self.trading_engine.start()

    async def save_state(self):
        """Save trading state."""
        await self.portfolio.save()
        await self.order_manager.save()

    async def close_positions(self):
        """Close all positions."""
        await self.trading_engine.close_all_positions()
```

## Dashboard Integration

### API Endpoint

```python
from fastapi import APIRouter
from app.services.monitoring import get_memory_monitor

router = APIRouter()

@router.get("/api/memory/stats")
async def get_memory_statistics():
    """Get current memory statistics."""
    monitor = get_memory_monitor()
    return monitor.get_statistics()

@router.get("/api/memory/snapshots")
async def get_memory_snapshots(limit: int = 10):
    """Get recent memory snapshots."""
    monitor = get_memory_monitor()
    snapshots = monitor.get_snapshots(limit=limit)
    return [s.to_dict() for s in snapshots]

@router.post("/api/memory/restart")
async def trigger_restart():
    """Manually trigger graceful restart."""
    monitor = get_memory_monitor()
    await monitor.trigger_graceful_restart()
    return {"status": "restarting"}
```

## Monitoring Dashboard

### Key Metrics to Display

1. **Current Memory Usage**
   - RSS (Resident Set Size)
   - VMS (Virtual Memory Size)
   - Percentage of system memory

2. **Monitor Status**
   - Is monitoring active?
   - Last check timestamp
   - Next check countdown

3. **History**
   - Memory trend chart
   - GC object count
   - Restart events

4. **Configuration**
   - Memory limit
   - Warning threshold
   - Action type

## Troubleshooting

### High Memory Usage

1. Check current statistics:
   ```python
   stats = monitor.get_statistics()
   print(stats["current_memory"])
   ```

2. Review snapshot history:
   ```python
   snapshots = monitor.get_snapshots(limit=20)
   for s in snapshots:
       print(f"{s.timestamp}: {s.rss_mb} MB")
   ```

3. Check GC object count:
   ```python
   stats = monitor.get_detailed_stats()
   print(f"GC Objects: {stats['gc_objects']}")
   ```

### Frequent Restarts

1. Increase memory limit:
   ```python
   config = MemoryConfig(memory_limit_mb=8192)  # 8GB
   ```

2. Change action to garbage collection:
   ```python
   config = MemoryConfig(action=MemoryAction.GARBAGE_COLLECT)
   ```

3. Check for memory leaks:
   ```python
   snapshots = monitor.get_snapshots(limit=100)
   # Look for steady growth pattern
   ```

## Testing

### Unit Tests

```bash
# Run all memory monitor tests
pytest tests/unit/services/monitoring/test_memory_monitor.py -v

# Run specific test
pytest tests/unit/services/monitoring/test_memory_monitor.py::TestMemoryMonitorStats::test_get_memory_usage -v
```

### Integration Test

```python
import asyncio
from app.services.monitoring import get_memory_monitor, MemoryConfig

async def test():
    config = MemoryConfig(
        memory_limit_mb=100,
        check_interval_seconds=1.0,
    )
    monitor = get_memory_monitor(config=config)

    await monitor.start()
    await asyncio.sleep(5)
    await monitor.stop()

    print("Test passed!")

asyncio.run(test())
```

## Best Practices

1. **Always use callbacks** for state saving and position closing
2. **Set appropriate limits** based on your system capacity
3. **Use alert callbacks** to notify on memory issues
4. **Monitor statistics regularly** via dashboard
5. **Test configuration** in development before production
6. **Review snapshot history** to detect memory leaks
7. **Use GARBAGE_COLLECT action** before enabling RESTART

## Safety Notes

- Monitor continues running even after errors
- Callback exceptions are caught and logged
- State is saved before any restart action
- Logs are flushed before restart
- Process restart preserves PID and arguments

## Support

For issues or questions:
1. Check the implementation report: `PHASE_3.7_MEMORY_MONITOR_REPORT.md`
2. Review unit tests: `tests/unit/services/monitoring/test_memory_monitor.py`
3. Check the source: `app/services/monitoring/memory_monitor.py`
