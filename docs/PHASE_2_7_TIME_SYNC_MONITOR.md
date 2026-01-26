# Phase 2.7: Time Sync Monitor Documentation

## Overview

The **Time Sync Monitor** is a critical system component that monitors and validates system clock synchronization to prevent order rejections and incorrect timestamps in the FIFO database.

## Problem Statement

System clock drift can cause:
- **Order rejections** from broker APIs that validate timestamps
- **Incorrect timestamps** in FIFO database leading to tax calculation errors
- **Data inconsistencies** across the trading system

## Solution

The TimeSyncMonitor continuously monitors clock drift against NTP (Network Time Protocol) servers and validates orders before submission to ensure timestamp accuracy.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TimeSyncMonitor                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   NTP Client │───▶│  Status      │───▶│  Callbacks   │ │
│  │              │    │  Tracker     │    │              │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         �                                      ▲            │
│         │                                      │            │
│         ▼                                      │            │
│  ┌──────────────┐                              │            │
│  │  Monitor     │                              │            │
│  │  Loop       ────────────────────────────────┘            │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## Features

### 1. Continuous Monitoring
- Monitors clock drift every 60 seconds (configurable)
- Checks against multiple NTP servers for redundancy
- Automatic fallback if NTP is unavailable

### 2. Threshold-Based Alerts
- **Warning threshold**: 1.0 second drift (default)
- **Critical threshold**: 5.0 seconds drift (default)
- Configurable callbacks for custom alert handling

### 3. Order Validation
- Validates orders before submission
- Rejects orders if clock drift exceeds threshold
- Prevents broker rejections due to timestamp errors

### 4. Status Tracking
- Total checks performed
- Failed checks count
- Current drift measurement
- Last successful sync time

## Usage

### Basic Usage

```python
from app.services.monitoring.time_sync_monitor import get_time_sync_monitor

# Get monitor instance
monitor = get_time_sync_monitor()

# Start monitoring
await monitor.start()

# Check if clock is synced
if monitor.is_synced():
    print("Clock is synced")

# Get current drift
drift = monitor.get_drift_seconds()
print(f"Current drift: {drift:.3f}s")

# Validate order before submission
order = {"symbol": "AAPL", "quantity": 100}
is_valid = await monitor.validate_order_timestamp(order)

# Stop monitoring
await monitor.stop()
```

### Advanced Configuration

```python
from app.services.monitoring.time_sync_monitor import (
    TimeSyncConfig,
    TimeSyncMonitor,
)

# Define callbacks
def on_drift(drift: float):
    logger.warning(f"Clock drift detected: {drift:.3f}s")

def on_critical(drift: float):
    logger.critical(f"CRITICAL drift: {drift:.3f}s")
    # Send alert, halt trading, etc.

# Create custom config
config = TimeSyncConfig(
    check_interval_seconds=30.0,  # Check every 30 seconds
    drift_threshold_seconds=0.5,  # Alert at 0.5s drift
    critical_threshold_seconds=2.0,  # Critical at 2s drift
    on_drift_detected=on_drift,
    on_critical_drift=on_critical,
)

# Create monitor with custom config
monitor = TimeSyncMonitor(config)
await monitor.start()
```

### Force Check

```python
# Perform an immediate time sync check
result = await monitor.force_check()

print(f"Drift: {result['drift_seconds']:.3f}s")
print(f"Is Synced: {result['is_synced']}")
print(f"NTP Server: {result['ntp_server']}")
```

### Clock Synchronization

```python
# Attempt to sync system clock (requires root)
success = await monitor.sync_clock()

if success:
    print("Clock synced successfully")
else:
    print("Clock sync failed (may require root privileges)")
```

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `check_interval_seconds` | 60.0 | How often to check clock drift |
| `drift_threshold_seconds` | 1.0 | Alert threshold for clock drift |
| `critical_threshold_seconds` | 5.0 | Critical threshold for clock drift |
| `max_retries` | 3 | Number of retries for NTP requests |
| `timeout_seconds` | 5.0 | Timeout for NTP requests |
| `on_drift_detected` | None | Callback for drift detection |
| `on_critical_drift` | None | Callback for critical drift |
| `on_sync_error` | None | Callback for sync errors |

## NTP Servers

The monitor uses the following NTP servers (in order):
1. `pool.ntp.org` - NTP Pool Project
2. `time.google.com` - Google NTP
3. `time.cloudflare.com` - Cloudflare NTP
4. `time.nist.gov` - NIST NTP

## Integration with Trading System

### Order Validation

```python
from app.services.monitoring.time_sync_monitor import get_time_sync_monitor

class OrderExecutor:
    def __init__(self):
        self.time_monitor = get_time_sync_monitor()

    async def submit_order(self, order: dict) -> bool:
        # Validate timestamp before submission
        if not await self.time_monitor.validate_order_timestamp(order):
            logger.error("Order rejected: Clock not synced")
            return False

        # Submit order to broker
        return await self._broker.submit_order(order)
```

### FIFO Database Integration

```python
from app.services.monitoring.time_sync_monitor import get_time_sync_monitor
from app.core.timezone_utils import utc_now

class FIFOQueue:
    def __init__(self):
        self.time_monitor = get_time_sync_monitor()

    async def add_position(self, position: dict) -> None:
        # Ensure clock is synced before adding position
        if not self.time_monitor.is_synced():
            raise ValueError("Cannot add position: Clock not synced")

        # Use timezone-aware timestamp
        position["timestamp"] = utc_now()
        self._db.insert(position)
```

## Monitoring and Alerts

### Prometheus Metrics

```python
from app.services.monitoring import get_prometheus_collector
from app.services.monitoring.time_sync_monitor import get_time_sync_monitor

# Expose time sync metrics
monitor = get_time_sync_monitor()
prometheus = get_prometheus_collector()

status = monitor.get_status()
prometheus.set_gauge("time_sync_drift_seconds", status.drift_seconds)
prometheus.set_gauge("time_sync_is_synced", 1 if status.is_synced else 0)
prometheus.set_gauge("time_sync_checks_total", status.checks_total)
prometheus.set_gauge("time_sync_checks_failed", status.checks_failed)
```

### Alert Rules

```python
from app.services.monitoring.alerting_rules_engine import (
    AlertRule,
    AlertSeverity,
    AlertConditionType,
    get_alerting_engine,
)

# Create alert rule for critical clock drift
rule = AlertRule(
    name="critical_clock_drift",
    description="Critical clock drift detected",
    severity=AlertSeverity.CRITICAL,
    condition_type=AlertConditionType.GREATER_THAN,
    threshold=5.0,
    metric_name="time_sync_drift_seconds",
)

alerting = get_alerting_engine()
alerting.add_rule(rule)
```

## Testing

### Unit Tests

```bash
# Run unit tests
python -m pytest tests/unit/services/monitoring/test_time_sync_monitor.py -v
```

### Integration Tests

```bash
# Run integration tests
python -m pytest tests/integration/monitoring/test_time_sync_monitor_integration.py -v
```

### Demo Script

```bash
# Run the demo script
python app/scripts/demo_time_sync_monitor.py
```

## Dependencies

- `ntplib>=0.4.0` - NTP client library
- `asyncio` - Async/await support
- `datetime` - Time handling
- `logging` - Logging support

## Installation

Add to `requirements.txt`:

```txt
ntplib>=0.4.0  # NTP time synchronization for TimeSyncMonitor (Phase 2.7)
```

Install:

```bash
pip install -r requirements.txt
```

## Error Handling

### NTP Unavailable

If `ntplib` is not installed, the monitor will:
- Log a warning message
- Assume system time is correct
- Continue operation with `drift_seconds = 0.0`
- Set `is_synced = True`

### All NTP Servers Fail

If all NTP servers fail:
- Increment `checks_failed` counter
- Set `is_synced = False`
- Call `on_sync_error` callback if provided
- Continue monitoring (will retry on next check)

### Clock Sync Failure

If automatic clock sync fails:
- Log warning message
- Return `False` from `sync_clock()`
- May be due to lack of root privileges
- User must manually sync system clock

## Best Practices

1. **Always validate orders** before submission
2. **Monitor drift metrics** in your observability platform
3. **Set appropriate thresholds** for your use case
4. **Handle sync errors** with proper callbacks
5. **Test clock sync** in your environment before deployment
6. **Monitor the monitor** - ensure TimeSyncMonitor is running

## Troubleshooting

### High Clock Drift

If you consistently see high clock drift:
1. Check system time settings
2. Verify NTP server connectivity
3. Consider running `ntpdate` manually
4. Check for VM time sync issues (if in VM)

### Frequent Order Rejections

If orders are frequently rejected:
1. Lower `drift_threshold_seconds`
2. Check broker's timestamp tolerance
3. Ensure system clock is accurate
4. Consider using broker's time for validation

### NTP Connection Failures

If NTP connections fail:
1. Check firewall rules
2. Verify DNS resolution
3. Try alternative NTP servers
4. Check network connectivity

## Future Enhancements

- [ ] Broker time comparison (optional)
- [ ] Automatic clock sync with systemd-timedate
- [ ] Historical drift tracking and alerting
- [ ] Per-broker drift thresholds
- [ ] Drift prediction and proactive alerts
- [ ] Integration with cloud time sync services

## References

- [NTP Protocol](https://www.ntp.org/)
- [FIFO Tax Database](../app/tax/database/fifo_schema.py)
- [Timezone Utils](../app/core/timezone_utils.py)
- [Monitoring Services](../app/services/monitoring/)

## License

This component is part of the algoTrading system and follows the same license.
