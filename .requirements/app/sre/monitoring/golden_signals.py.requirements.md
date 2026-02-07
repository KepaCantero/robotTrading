# Requirements: sre/monitoring/golden_signals.py

## Source File Analysis
- **File Path**: `app/sre/monitoring/golden_signals.py`
- **Lines of Code**: 1041
- **Status**: PASSED
- **Audit Date**: 2026-02-07

## Purpose
Implements Google SRE's Golden Signals monitoring for algorithmic trading systems. Monitors the four critical signals that indicate system health: Latency, Traffic, Errors, and Saturation. Key objectives:
- Real-time metrics collection for all four golden signals
- SLO compliance checking against predefined targets
- Health status evaluation based on signal thresholds
- Historical data tracking and trend analysis
- Intelligent alerting on threshold violations

## Dependencies
- Internal: None (standalone SRE module)
- External:
  - `aiosqlite`: Async SQLite database for persistence
  - `psutil`: System resource monitoring (CPU, memory, disk, network)
  - `asyncio`: Async/await patterns
  - `dataclasses`: Data structures
  - `pathlib`: Path operations
  - `os`: System operations (load average)

## Classes/Functions

### Enums
- `HealthStatus(str, Enum)`: HEALTHY, WARNING, DEGRADED, CRITICAL
- `SignalType(str, Enum)`: LATENCY, TRAFFIC, ERRORS, SATURATION

### Data Classes (Frozen - Immutable)
- `LatencyMetrics`: Latency signal measurements (p50, p95, p99, p999, max, mean)
- `TrafficMetrics`: Traffic signal measurements (RPS, connections)
- `ErrorMetrics`: Error signal measurements (error rate, critical errors)
- `SaturationMetrics`: Saturation signal measurements (CPU, memory, disk, network)
- `GoldenSignalMetrics`: Container for all golden signal measurements
- `SLOTarget`: SLO target for a golden signal
  - `is_compliant(actual_value)`: Check if actual value meets SLO target

### Configuration
- `GoldenSignalsConfig`: Configuration for golden signals monitor
  - SLO targets for each signal type
  - Alert thresholds (warning/critical)
  - Collection settings (interval, history size)
  - Callbacks for health changes and SLO violations

### Helper Classes
- `RequestTracker`: Track requests for traffic/error metrics
  - `record_request()`: Record a request
  - `get_metrics()`: Get request metrics
- `LatencyCollector`: Collect latency measurements
  - `record_latency()`: Record a latency measurement
  - `get_metrics()`: Get latency metrics

### Main Class
- `GoldenSignalsMonitor`: Monitor golden signals for the trading system
  - `initialize()`: Initialize the monitor
  - `start_collection()`: Start automatic metrics collection
  - `stop_collection()`: Stop automatic metrics collection
  - `collect_metrics()`: Collect all golden signal metrics
  - `get_current_metrics()`: Get most recent metrics
  - `get_metrics_history()`: Get metrics history
  - `get_metrics_summary()`: Get comprehensive metrics summary
  - `check_slo_compliance()`: Check compliance with all SLO targets

### Private Methods
- `_init_database()`: Initialize SQLite schema
- `_initialize_network_baseline()`: Initialize network usage baseline
- `_collection_loop()`: Main collection loop for automatic collection
- `_collect_latency()`: Collect latency metrics
- `_collect_traffic()`: Collect traffic metrics
- `_collect_errors()`: Collect error metrics
- `_collect_saturation()`: Collect saturation metrics
- `_calculate_network_utilization()`: Calculate network utilization percentage
- `_get_connection_count()`: Get current connection count
- `_evaluate_overall_health()`: Evaluate overall system health
- `_check_health_change()`: Check if health status has changed
- `_check_slo_compliance()`: Check SLO compliance for all targets
- `_get_metric_value()`: Get metric value from metrics based on SLO target
- `_persist_metrics()`: Persist metrics to database

## Business Logic

### Google SRE Golden Signals
1. **Latency**: Time to process requests (p50, p95, p99, p999)
2. **Traffic**: Request rate (requests per second)
3. **Errors**: Rate of failed requests (error percentage)
4. **Saturation**: How full is the service (CPU, memory, disk, network)

### Default SLO Targets
- **Latency**: p95 < 500ms (5-minute window)
- **Errors**: Error rate < 0.5% (5-minute window)
- **CPU**: Usage < 80% (5-minute window)
- **Memory**: Usage < 85% (5-minute window)

### Health Status Determination
```python
# Count critical and warning violations
critical_count = count of signals above critical thresholds
warning_count = count of signals above warning thresholds

# Determine overall health
if critical_count >= 2: CRITICAL
elif critical_count >= 1 or warning_count >= 3: DEGRADED
elif warning_count >= 1: WARNING
else: HEALTHY
```

### Alert Thresholds (Defaults)
| Signal | Warning | Critical |
|--------|---------|----------|
| Latency (p99) | 500ms | 1000ms |
| Error Rate | 1% | 5% |
| CPU Usage | 70% | 90% |
| Memory Usage | 75% | 90% |
| Disk Usage | 80% | 95% |

## Data Models

### Database Schema
```sql
CREATE TABLE golden_signals_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    latency_p50 REAL,
    latency_p95 REAL,
    latency_p99 REAL,
    traffic_rps REAL,
    error_rate_pct REAL,
    saturation_cpu REAL,
    saturation_memory REAL,
    saturation_disk REAL,
    health_status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('utc'))
)

CREATE INDEX idx_signals_service_timestamp
ON golden_signals_history(service_name, timestamp)
```

## API Contracts

### Initialization
```python
monitor = GoldenSignalsMonitor(
    service_name="trading-engine",
    config=GoldenSignalsConfig()
)
await monitor.initialize()
```

### Recording Requests and Latency
```python
# Record a request
monitor.record_request(success=True, error_type=None)

# Record latency
monitor.record_latency(latency_ms=150)
```

### Starting/Stopping Automatic Collection
```python
await monitor.start_collection()
# ... runs in background ...
await monitor.stop_collection()
```

### Manual Metrics Collection
```python
metrics = await monitor.collect_metrics()
print(f"Health: {metrics.overall_health.value}")
print(f"Latency p99: {metrics.latency.p99_ms}ms")
print(f"Error Rate: {metrics.errors.error_rate_pct}%")
print(f"CPU: {metrics.saturation.cpu_usage_pct}%")
```

### Checking SLO Compliance
```python
compliance = await monitor.check_slo_compliance()
for slo_description, is_compliant in compliance.items():
    status = "OK" if is_compliant else "VIOLATION"
    print(f"{slo_description}: {status}")
```

### Getting Metrics Summary
```python
summary = await monitor.get_metrics_summary()
print(json.dumps(summary, indent=2))
```

## Error Handling
- Database errors: Logged with context
- Timeout errors: Caught with context-rich logging
- System metric errors: Return zeros on error (graceful degradation)
- Collection errors: Logged but don't stop collection loop

### Exception Handling Pattern
```python
try:
    # System operation
except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
    self.logger.error(f"Context: {e}")
    # Handle gracefully, don't crash
```

## Performance Considerations
- **In-memory history**: Deque with maxlen for O(1) append/pop
- **Async collection**: All I/O is non-blocking
- **Database indexing**: Indexes on service_name, timestamp
- **Collection interval**: Default 60 seconds (configurable)
- **History size**: Default 1440 samples (24 hours at 1-minute intervals)

### Optimization Notes
- Deque for O(1) history operations
- psutil calls cached within collection cycle
- Network baseline calculated incrementally
- Metrics persisted asynchronously
- Automatic history trimming

## Testing Strategy

### Unit Tests Needed
1. Health status evaluation logic
2. SLO compliance checking
3. Metric collection accuracy
4. Request tracking accuracy
5. Latency percentile calculation

### Integration Tests Needed
1. Database persistence and recovery
2. Automatic collection loop
3. Callback triggering on health changes
4. Network baseline calculation
5. Historical data accuracy

### Edge Cases to Test
1. Empty metrics history
2. All metrics at zero
3. All metrics at critical levels
4. System without psutil support
5. Database connection failures
6. Clock skew (timestamp issues)
7. Rapid health status changes

### Example Test Cases
```python
# Test health status evaluation
metrics = GoldenSignalMetrics(
    service_name="test",
    latency=LatencyMetrics(p99_ms=600, ...),  # Warning
    traffic=TrafficMetrics(requests_per_second=100, ...),
    errors=ErrorMetrics(error_rate_pct=2.0, ...),  # Warning
    saturation=SaturationMetrics(cpu_usage_pct=85, ...),  # Warning
    overall_health=HealthStatus.WARNING,
    collected_at=datetime.utcnow()
)

# Should be WARNING (1 critical + multiple warnings)
health = monitor._evaluate_overall_health(metrics)
assert health == HealthStatus.WARNING

# Test SLO compliance
slo_target = SLOTarget(
    signal_type=SignalType.LATENCY,
    metric_name="p99_ms",
    target_value=Decimal("500"),
    comparison_op="lte",
    window_minutes=5,
    description="p99 latency under 500ms"
)

assert slo_target.is_compliant(400) == True
assert slo_target.is_compliant(600) == False
```

## Audit Status: PASSED

### Compliance Summary
- **Structure**: Well-organized following Google SRE principles
- **Documentation**: Comprehensive docstrings with usage examples
- **Error Handling**: Proper exception handling with context
- **Type Hints**: Complete type annotations using `from __future__ import annotations`
- **Async/Await**: Correct async patterns throughout
- **Data Classes**: Proper use of frozen dataclasses for immutability
- **Database**: Proper schema with indexes for performance
- **Logging**: Context-aware logging at appropriate levels
- **Configuration**: Sensible defaults with override capability
- **Singleton Pattern**: Module-level singleton management

### Strengths
1. Complete implementation of Google SRE Golden Signals
2. Real-time metrics collection with psutil
3. Flexible SLO targeting system
4. Automatic collection loop with async support
5. Health status evaluation with multiple thresholds
6. Network utilization tracking with baseline
7. Connection tracking for traffic metrics
8. Comprehensive historical data persistence

### No Critical Issues Found
All code follows best practices for:
- Google SRE Book principles
- Clean Architecture patterns
- Async Python programming
- System monitoring with psutil
- Database operations
- Error handling
- Type safety

### Integration Points
- Feeds into error budget calculations
- Integrates with SLO tracker
- Connects to health check endpoints
- Works with alert fatigue prevention system

### Google SRE Compliance
This module implements Google SRE's Golden Signals monitoring:
1. **Latency**: p50, p95, p99, p999 percentiles
2. **Traffic**: Requests per second, connections
3. **Errors**: Error rate, critical errors
4. **Saturation**: CPU, memory, disk, network usage

---
*Audited on 2026-02-07*
