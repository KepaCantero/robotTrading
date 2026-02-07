# Requirements: sre/error_budgets/slo_tracker.py

## Source File Analysis
- **File Path**: `app/sre/error_budgets/slo_tracker.py`
- **Lines of Code**: 857
- **Status**: PASSED
- **Audit Date**: 2026-02-07

## Purpose
Implements SLO/SLI monitoring and compliance tracking (SRE Rule 20). Monitors Service Level Objectives (SLOs) and Service Level Indicators (SLIs), tracks compliance, detects violations, and generates compliance reports. Key objectives:
- Track SLI metrics over time (latency, error rate, availability, throughput)
- Calculate SLO compliance in rolling windows
- Detect SLO violations in real-time
- Generate comprehensive compliance reports
- Persist SLO data for historical analysis

## Dependencies
- Internal: None (standalone SRE module)
- External:
  - `aiosqlite`: Async SQLite database for persistence
  - `asyncio`: Async/await patterns
  - `decimal`: Precision calculations
  - `dataclasses`: Data structures
  - `pathlib`: Path operations

## Classes/Functions

### Enums
- `SLIMetricType(str, Enum)`: AVAILABILITY, LATENCY, ERROR_RATE, THROUGHPUT, SATISFACTION
- `SLOComplianceStatus(str, Enum)`: COMPLIANT, VIOLATION, AT_RISK, INSUFFICIENT_DATA

### Data Classes
- `SLIMetric`: Service Level Indicator measurement
  - `to_dict()`: Convert to dictionary
- `SLOConfig`: Service Level Objective configuration
  - `is_compliant(actual_value)`: Check if actual value meets SLO target
  - `to_dict()`: Convert to dictionary
- `SLOViolation`: Record of an SLO violation
  - `duration_minutes()`: Calculate violation duration
  - `to_dict()`: Convert to dictionary
- `SLOComplianceReport`: SLO compliance report for a time period
  - `compliance_percentage`: Calculate compliance as percentage of target
  - `violation_count`: Get number of violations
  - `total_violation_minutes`: Get total minutes in violation state
  - `to_dict()`: Convert to dictionary

### Main Class
- `SLOTracker`: SLO/SLI monitoring and compliance tracking
  - `initialize()`: Initialize SLO tracker
  - `register_slo()`: Register an SLO configuration
  - `record_metric()`: Record an SLI metric measurement
  - `generate_compliance_report()`: Generate SLO compliance report
  - `get_active_violations()`: Get list of active violations
  - `get_slo_configs()`: Get all SLO configurations
  - `get_summary()`: Get SLO tracker summary

### Private Methods
- `_init_database()`: Initialize SQLite schema
- `_load_active_violations()`: Load active violations from database
- `_register_default_slos()`: Register default SLOs for trading system
- `_save_metric()`: Save metric to database
- `_check_slo_violations()`: Check for SLO violations based on recent metrics
- `_calculate_slo_value()`: Calculate SLO value from metrics
- `_handle_violation()`: Handle SLO violation
- `_resolve_violation()`: Resolve SLO violation
- `_generate_report_for_slo()`: Generate compliance report for a single SLO

## Business Logic

### SLO/SLI Concepts
- **SLI (Service Level Indicator)**: A measured metric (e.g., request latency)
- **SLO (Service Level Objective)**: Target value for an SLI (e.g., 95% of requests under 1s)
- **Compliance**: Measurement of actual vs target performance
- **Violation**: Period where actual performance is below SLO target

### Default SLOs for Trading System
1. **Availability**: 99.5% uptime (30-day rolling window)
2. **API Latency**: 95% of requests under 1 second (5-minute window)
3. **Error Rate**: 99% success rate (10-minute window)

### SLO Value Calculation by Type
- **AVAILABILITY**: Percentage of successful measurements
- **LATENCY**: Percentage of requests under threshold
- **ERROR_RATE**: Success rate (inverse of error rate)
- **THROUGHPUT**: Average throughput relative to target
- **SATISFACTION**: Average of values

### Violation Detection
```python
# Check if actual value meets SLO target
if actual_value < violation_threshold:
    # Critical violation
    await self._handle_violation(slo_name, actual_value, target, "critical")
elif actual_value < warning_threshold:
    # Warning violation
    await self._handle_violation(slo_name, actual_value, target, "warning")
```

### Compliance Status Determination
- **COMPLIANT**: Actual SLO >= Target SLO
- **VIOLATION**: Actual SLO < Target SLO
- **AT_RISK**: Actual SLO < 95% of Target SLO
- **INSUFFICIENT_DATA**: Not enough samples for valid measurement

## Data Models

### Database Schema
```sql
-- SLI metrics table
CREATE TABLE slo_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('utc'))
)

-- SLO configurations table
CREATE TABLE slo_configs (
    service_name TEXT NOT NULL,
    slo_name TEXT NOT NULL,
    slo_target TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    window_minutes INTEGER NOT NULL,
    description TEXT,
    warning_threshold TEXT,
    violation_threshold TEXT,
    min_samples INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('utc')),
    UNIQUE(service_name, slo_name)
)

-- SLO violations table
CREATE TABLE slo_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    slo_name TEXT NOT NULL,
    violation_start TEXT NOT NULL,
    violation_end TEXT,
    actual_value TEXT NOT NULL,
    target_value TEXT NOT NULL,
    severity TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('utc'))
)

-- Indexes
CREATE INDEX idx_metrics_service_timestamp ON slo_metrics(service_name, timestamp)
CREATE INDEX idx_violations_service_active ON slo_violations(service_name, resolved)
```

## API Contracts

### Initialization
```python
tracker = SLOTracker(
    service_name="trading_engine",
    db_path="data/slo_metrics.db"
)
await tracker.initialize()
```

### Registering SLOs
```python
config = SLOConfig(
    name="api_latency_p99",
    slo_target=Decimal("0.95"),  # 95% under threshold
    metric_type=SLIMetricType.LATENCY,
    measurement_window_minutes=5,
    description="99th percentile latency under 1 second",
    min_samples=10
)
await tracker.register_slo(config)
```

### Recording Metrics
```python
metric = SLIMetric(
    name="api_latency",
    value=Decimal("150"),  # 150ms
    timestamp=datetime.utcnow(),
    metric_type=SLIMetricType.LATENCY,
    metadata={"endpoint": "/api/orders"}
)
await tracker.record_metric(metric)
```

### Generating Reports
```python
reports = await tracker.generate_compliance_report(
    slo_name="api_latency",
    period_start=datetime.utcnow() - timedelta(days=7),
    period_end=datetime.utcnow()
)
for report in reports:
    print(f"SLO: {report.slo_name}")
    print(f"Compliance: {report.compliance_percentage:.2f}%")
    print(f"Status: {report.status.value}")
```

### Setting Callbacks
```python
def on_violation(violation: SLOViolation):
    send_alert(f"SLO Violation: {violation.slo_name}")

def on_resolution(violation: SLOViolation):
    send_alert(f"SLO Restored: {violation.slo_name}")

tracker.set_violation_callback(on_violation)
tracker.set_resolution_callback(on_resolution)
```

## Error Handling
- Database errors: Logged with context
- Timeout errors: Caught with context-rich logging
- Invalid metrics: Logged but don't block processing
- State corruption: Rebuilds from database on initialization

### Exception Handling Pattern
```python
try:
    # Database operation
except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
    self.logger.error(f"Context: {e}")
    raise
```

## Performance Considerations
- **In-memory buffering**: Recent metrics kept in memory for fast violation detection
- **Database indexing**: Indexes on service_name, timestamp, resolved
- **Async operations**: All I/O is non-blocking
- **Metric buffer trimming**: Keep last 500 metrics per SLO
- **Lazy loading**: Violations loaded on demand

### Optimization Notes
- Deque for metric buffers (O(1) operations)
- Time-based filtering for rolling windows
- Batch violation checking
- Efficient violation state tracking

## Testing Strategy

### Unit Tests Needed
1. SLO value calculation for each metric type
2. Compliance status determination
3. Violation detection and resolution
4. SLO compliance checking (is_compliant method)
5. Report generation accuracy

### Integration Tests Needed
1. Database persistence and recovery
2. Active violation reconstruction
3. Default SLO registration
4. Callback triggering on violations
5. Historical report generation

### Edge Cases to Test
1. Empty metric buffer
2. Insufficient samples for SLO calculation
3. Violation during initialization
4. Clock skew (timestamp issues)
5. Database connection failures
6. Concurrent metric recording
7. SLO config updates (target changes)

### Example Test Cases
```python
# Test SLO compliance checking
config = SLOConfig(
    name="test_slo",
    slo_target=Decimal("0.95"),
    metric_type=SLIMetricType.LATENCY,
    measurement_window_minutes=5
)

# Test compliant
assert config.is_compliant(Decimal("0.96")) == True

# Test violation
assert config.is_compliant(Decimal("0.90")) == False

# Test violation tracking
violation = SLOViolation(
    slo_name="test_slo",
    violation_start=datetime.utcnow(),
    violation_end=None,
    actual_value=Decimal("0.90"),
    target_value=Decimal("0.95"),
    severity="critical"
)
assert violation.resolved == False
assert violation.duration_minutes() is None
```

## Audit Status: PASSED

### Compliance Summary
- **Structure**: Well-organized following Google SRE principles
- **Documentation**: Comprehensive docstrings with usage examples
- **Error Handling**: Proper exception handling with context
- **Type Hints**: Complete type annotations
- **Async/Await**: Correct async patterns throughout
- **Data Classes**: Proper use of dataclasses
- **Database**: Proper schema with indexes for performance
- **Logging**: Context-aware logging at appropriate levels
- **Configuration**: Sensible defaults with override capability
- **Callback System**: Flexible violation notification

### Strengths
1. Complete implementation of SLO/SLI monitoring
2. Real-time violation detection and tracking
3. Comprehensive compliance reporting
4. Flexible SLO configuration system
5. Callback-based alerting
6. Default SLOs for trading systems
7. Historical data persistence
8. Support for multiple metric types

### No Critical Issues Found
All code follows best practices for:
- Google SRE Book principles
- Clean Architecture patterns
- Async Python programming
- Database operations
- Error handling
- Type safety
- Domain modeling

### Integration Points
- Feeds into error budget calculations
- Connects to health check endpoints
- Monitors application metrics
- Integrates with alerting systems

---
*Audited on 2026-02-07*
