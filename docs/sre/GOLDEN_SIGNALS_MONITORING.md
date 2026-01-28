# Golden Signals Monitoring

Comprehensive implementation of Google SRE's Four Golden Signals for the algorithmic trading system.

## Overview

The Golden Signals Monitor implements Google SRE's proven methodology for monitoring distributed systems by tracking the four most critical signals:

1. **Latency**: Time taken to service a request
2. **Traffic**: How much demand is being placed on the system
3. **Errors**: Rate of failed requests
4. **Saturation**: How "full" the service is

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│            Golden Signals Monitor                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐    │
│  │  Latency    │  │   Traffic   │  │    Errors    │    │
│  │  Collector  │  │   Tracker   │  │    Tracker   │    │
│  └─────────────┘  └─────────────┘  └──────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Saturation Collector (psutil)            │   │
│  │  CPU │ Memory │ Disk │ Network │ Load │ Files   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Health Evaluator                        │   │
│  │   SLO Compliance │ Alerting │ Trends              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Basic Setup

```python
from app.sre.monitoring import get_golden_signals_monitor

# Create monitor instance
monitor = get_golden_signals_monitor(service_name="trading-engine")
await monitor.initialize()

# Start automatic collection
await monitor.start_collection()
```

### Recording Metrics

```python
# Record a request
monitor.record_request(success=True)

# Record a failed request
monitor.record_request(success=False, error_type="timeout")

# Record latency
monitor.record_latency(latency_ms=123.4)
```

### Getting Metrics

```python
# Get current metrics
metrics = await monitor.get_current_metrics()

print(f"Latency P99: {metrics.latency.p99_ms} ms")
print(f"Error Rate: {metrics.errors.error_rate_pct}%")
print(f"CPU Usage: {metrics.saturation.cpu_usage_pct}%")

# Get summary
summary = await monitor.get_metrics_summary()

# Get history
history = await monitor.get_metrics_history(limit=100)
```

### Health Status

```python
# Get current health
health = monitor.evaluate_health()

# Possible values:
# - HealthStatus.HEALTHY: All signals within normal ranges
# - HealthStatus.WARNING: One or more signals elevated
# - HealthStatus.DEGRADED: Multiple signals elevated
# - HealthStatus.CRITICAL: System in critical state
```

### SLO Compliance

```python
# Check SLO compliance
compliance = await monitor.check_slo_compliance()

for description, is_compliant in compliance.items():
    status = "✓" if is_compliant else "✗"
    print(f"{status} {description}")
```

## Configuration

### Default Configuration

```python
from app.sre.monitoring import GoldenSignalsConfig, SLOTarget, SignalType

config = GoldenSignalsConfig(
    service_name="trading-engine",

    # Latency thresholds
    latency_warning_ms=500.0,
    latency_critical_ms=1000.0,

    # Error rate thresholds
    error_rate_warning_pct=1.0,
    error_rate_critical_pct=5.0,

    # Saturation thresholds
    cpu_warning_pct=70.0,
    cpu_critical_pct=90.0,
    memory_warning_pct=75.0,
    memory_critical_pct=90.0,
    disk_warning_pct=80.0,
    disk_critical_pct=95.0,

    # Collection settings
    collection_interval_seconds=60,
    history_size=1440,  # 24 hours
)
```

### Custom SLO Targets

```python
from decimal import Decimal

config = GoldenSignalsConfig(
    service_name="trading-engine",
    slo_targets=[
        SLOTarget(
            signal_type=SignalType.LATENCY,
            metric_name="p95_ms",
            target_value=Decimal("500"),
            comparison_op="lte",
            window_minutes=5,
            description="95th percentile latency under 500ms",
        ),
        SLOTarget(
            signal_type=SignalType.ERRORS,
            metric_name="error_rate_pct",
            target_value=Decimal("0.5"),
            comparison_op="lte",
            window_minutes=5,
            description="Error rate under 0.5%",
        ),
    ],
)
```

### Callbacks

```python
async def on_health_change(old_health, new_health):
    print(f"Health changed: {old_health} -> {new_health}")

async def on_slo_violation(slo_target, actual_value):
    print(f"SLO violated: {slo_target.description}")
    print(f"Actual: {actual_value}, Target: {slo_target.target_value}")

config = GoldenSignalsConfig(
    service_name="trading-engine",
    on_health_change=on_health_change,
    on_slo_violation=on_slo_violation,
)
```

## Metrics Reference

### Latency Metrics

```python
@dataclass
class LatencyMetrics:
    p50_ms: float      # Median latency
    p95_ms: float      # 95th percentile
    p99_ms: float      # 99th percentile
    p999_ms: float     # 99.9th percentile
    max_ms: float      # Maximum latency
    mean_ms: float     # Average latency
    timestamp: datetime
```

### Traffic Metrics

```python
@dataclass
class TrafficMetrics:
    requests_per_second: float
    requests_per_minute: float
    requests_per_hour: float
    peak_rps: float
    current_connections: int
    timestamp: datetime
```

### Error Metrics

```python
@dataclass
class ErrorMetrics:
    error_rate_pct: float
    error_count: int
    total_requests: int
    errors_by_type: Dict[str, int]
    critical_errors: int
    timestamp: datetime
```

### Saturation Metrics

```python
@dataclass
class SaturationMetrics:
    cpu_usage_pct: float
    memory_usage_pct: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_pct: float
    disk_used_gb: float
    disk_free_gb: float
    network_utilization_pct: float
    load_average: Tuple[float, float, float]
    open_files: int
    thread_count: int
    timestamp: datetime
```

## Health Evaluation Logic

The system evaluates overall health based on all four golden signals:

### Critical (2+ critical signals)
- Latency P99 > 1000ms
- Error rate > 5%
- CPU > 90%
- Memory > 90%
- Disk > 95%

### Degraded (1 critical or 3+ warnings)
- Any single critical threshold exceeded
- Multiple warning thresholds exceeded

### Warning (1+ warning signals)
- Latency P99 > 500ms
- Error rate > 1%
- CPU > 70%
- Memory > 75%
- Disk > 80%

### Healthy (all signals normal)
- All signals within normal ranges

## Integration with Existing Systems

### FastAPI Integration

```python
from fastapi import Request
from app.sre.monitoring import get_golden_signals_monitor

monitor = get_golden_signals_monitor("api")

@app.middleware("http")
async def track_requests(request: Request, call_next):
    start_time = time.time()
    success = True

    try:
        response = await call_next(request)
        return response
    except Exception as e:
        success = False
        monitor.record_request(success=False, error_type=type(e).__name__)
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        monitor.record_latency(latency_ms)
        monitor.record_request(success=success)
```

### Database Integration

```python
async def track_database_query(query_func):
    monitor = get_golden_signals_monitor("database")

    try:
        result = await query_func()
        monitor.record_request(success=True)
        return result
    except Exception as e:
        monitor.record_request(success=False, error_type="database_error")
        raise
```

## Best Practices

1. **Set Appropriate Thresholds**: Customize thresholds based on your service's requirements
2. **Monitor Trends**: Use metrics history to identify patterns
3. **Alert Intelligently**: Use callbacks to integrate with alerting systems
4. **Review SLOs Regularly**: Adjust SLO targets as your system evolves
5. **Correlate Signals**: Look for relationships between different signals

## Troubleshooting

### High Latency
- Check saturation metrics (CPU, memory)
- Review database query performance
- Analyze traffic patterns

### High Error Rate
- Check error types in `errors_by_type`
- Review application logs
- Verify external dependencies

### High Saturation
- CPU: Profile code for hotspots
- Memory: Check for memory leaks
- Disk: Review log rotation and data retention

## References

- [Google SRE Book - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Site Reliability Engineering](https://sre.google/)
- [The Four Golden Signals](https://sre.google/sre-book/monitoring-distributed-systems/#golden-signals)
