# Requirements: sre/error_budgets/error_budget_manager.py

## Source File Analysis
- **File Path**: `app/sre/error_budgets/error_budget_manager.py`
- **Lines of Code**: 805
- **Status**: PASSED
- **Audit Date**: 2026-02-07

## Purpose
Implements Google SRE error budget methodology (SRE Rule 20). Tracks service availability against SLO targets, calculating error budgets that define how much downtime is acceptable. Key goals:
- Calculate error budgets based on SLO targets (e.g., 99.5% = 216 minutes/month)
- Track real-time budget consumption from incidents
- Monitor burn rate (consumption velocity)
- Trigger alerts when budget is exhausted
- Support deployment gating based on budget status

## Dependencies
- Internal: None (standalone SRE module)
- External:
  - `aiosqlite`: Async SQLite database for persistence
  - `asyncio`: Async/await patterns
  - `decimal`: Precision financial calculations
  - `dataclasses`: Data structures
  - `pathlib`: Path operations

## Classes/Functions

### Enums
- `BudgetPeriod(str, Enum)`: HOURLY, DAILY, WEEKLY, MONTHLY, QUARTERLY
- `BudgetStatus(str, Enum)`: HEALTHY (>50%), WARNING (25-50%), CRITICAL (10-25%), EXHAUSTED (<10%), BURN_RATE_HIGH

### Value Objects (Cosmic Python - Frozen)
- `TimeWindow`: Value object for time windows
  - `duration_minutes`: Duration in minutes
  - `duration_hours`: Duration in hours
  - `contains(timestamp)`: Check if timestamp is within window
- `BudgetAllowance`: Value object for budget allowance
  - `allowed_downtime_minutes`: Calculate from SLO
  - `allowed_downtime_seconds`: Calculate from SLO
  - `from_slo()`: Class method to create from SLO target

### Domain Entities
- `BudgetConsumption`: Value object for budget consumption tracking
  - `add_incident()`: Add incident to consumption
- `ErrorBudgetState`: Domain entity representing current error budget state
  - `remaining_minutes`: Calculate remaining budget
  - `remaining_percentage`: Calculate remaining as percentage
  - `consumed_percentage`: Calculate consumed as percentage
  - `actual_slo`: Calculate actual SLO achieved
  - `is_exhausted()`: Check if budget is exhausted
  - `to_dict()`: Convert to dictionary

### Configuration
- `ErrorBudgetConfig`: Configuration for error budget manager
  - SLO targets: target_slo, period
  - Alert thresholds: warning, critical, exhausted
  - Burn rate thresholds: high_burn_rate_threshold
  - Callbacks: on_budget_exhausted, on_burn_rate_high

### Main Class
- `ErrorBudgetManager`: Main error budget tracking and calculation
  - `initialize()`: Initialize database and load state
  - `record_downtime()`: Record downtime and update budget
  - `get_current_state()`: Get current error budget state
  - `get_budget_summary()`: Get comprehensive summary
  - `get_incident_history()`: Get incident history
  - `check_deployment_allowed()`: Check if deployment is allowed

### Private Methods
- `_init_database()`: Initialize SQLite schema
- `_load_current_state()`: Load current state from database
- `_create_initial_state()`: Create initial error budget state
- `_save_state()`: Save current state to database
- `_save_incident()`: Save incident to database
- `_recalculate_state()`: Recalculate error budget state
- `_check_alerts()`: Check if alerts should be triggered

## Business Logic

### Error Budget Calculation (Google SRE)
For a 99.5% monthly SLO:
- Total minutes in month: 43,200 (30 days × 24 hours × 60 minutes)
- Allowed downtime: 216 minutes (0.5% of 43,200)
- Each minute of outage consumes budget
- Budget resets monthly

### Budget Status Thresholds
- **HEALTHY**: >50% budget remaining
- **WARNING**: 25-50% budget remaining
- **CRITICAL**: 10-25% budget remaining
- **EXHAUSTED**: <10% budget remaining
- **BURN_RATE_HIGH**: Consuming too fast (>2x normal rate)

### Burn Rate Calculation
```python
burn_rate = consumed_minutes / elapsed_hours
# Normal rate = 216 minutes / 720 hours (30 days) = 0.3 min/hr
# High burn rate = 2x normal = 0.6 min/hr
```

### Deployment Gating
```python
def check_deployment_allowed(self) -> tuple[bool, str]:
    # Block if budget exhausted (<10% remaining)
    if self._current_state.is_exhausted(threshold_pct=10):
        return False, "Error budget exhausted"

    # Warn if high burn rate
    if self._current_state.burn_rate > 2.0:
        return True, "High burn rate, proceed with caution"

    return True, "Deployment allowed"
```

## Data Models

### Database Schema
```sql
-- Error budgets table
CREATE TABLE error_budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    period TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    target_slo TEXT NOT NULL,
    allowed_downtime_minutes INTEGER NOT NULL,
    consumed_downtime_minutes INTEGER NOT NULL,
    error_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    burn_rate TEXT,
    calculated_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('utc')),
    UNIQUE(service_name, period, window_start)
)

-- Budget incidents table
CREATE TABLE budget_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    incident_timestamp TEXT NOT NULL,
    downtime_minutes INTEGER NOT NULL,
    error_type TEXT,
    description TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('utc'))
)

-- Indexes
CREATE INDEX idx_budget_service_period ON error_budgets(service_name, period)
CREATE INDEX idx_incidents_service_timestamp ON budget_incidents(service_name, incident_timestamp)
```

## API Contracts

### Initialization
```python
manager = ErrorBudgetManager(
    service_name="trading_engine",
    config=ErrorBudgetConfig(
        target_slo=Decimal("0.995"),  # 99.5%
        period=BudgetPeriod.MONTHLY
    )
)
await manager.initialize()
```

### Recording Downtime
```python
state = await manager.record_downtime(
    downtime_minutes=15,
    error_type="database",
    description="Postgres connection pool exhausted",
    metadata={"region": "us-east-1"}
)
```

### Getting Budget Summary
```python
summary = await manager.get_budget_summary()
print(f"SLO: {summary['state']['target_slo']}")
print(f"Remaining: {summary['state']['remaining_percentage']}")
print(f"Status: {summary['state']['status']}")
```

### Checking Deployment Gate
```python
allowed, reason = await manager.check_deployment_allowed()
if not allowed:
    print(f"Deployment blocked: {reason}")
```

## Error Handling
- Database errors: Logged with context
- Timeout errors: Caught with context-rich logging
- Invalid downtime: Raises ValueError
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
- **Database indexing**: Indexes on service_name, period, timestamp
- **Async operations**: All I/O is non-blocking
- **State caching**: Current state kept in memory
- **Time windows**: Pre-calculated for all periods
- **Decimal precision**: Uses Decimal for financial calculations

### Optimization Notes
- Frozen dataclasses for value objects (immutability)
- Time windows calculated once on initialization
- State persisted on every change for durability
- Incident history loaded lazily on demand

## Testing Strategy

### Unit Tests Needed
1. Error budget calculation from SLO
2. Time window calculation (monthly, weekly, daily, hourly)
3. Status determination logic (healthy, warning, critical, exhausted)
4. Burn rate calculation
5. Deployment gating logic

### Integration Tests Needed
1. Database persistence and recovery
2. State reconstruction from database
3. Incident recording and tracking
4. Budget rollover (period transitions)
5. Callback triggering

### Edge Cases to Test
1. Zero SLO (100% uptime)
2. Multiple incidents in quick succession
3. Budget exhaustion exactly at threshold
4. Clock skew (timestamp issues)
5. Database connection failures
6. Concurrent downtime recording
7. Period boundary transitions

### Example Test Cases
```python
# Test budget calculation for 99.5% SLO
allowance = BudgetAllowance.from_slo(
    total_minutes=43200,  # 30 days
    slo_percentage=Decimal("0.995"),
    period=BudgetPeriod.MONTHLY
)
assert allowance.allowed_downtime_minutes == 216

# Test state calculation
state = ErrorBudgetState(
    service_name="test",
    allowance=allowance,
    consumption=BudgetConsumption(downtime_minutes=100, error_count=2),
    current_window=TimeWindow(start, end),
    status=BudgetStatus.WARNING,
    calculated_at=datetime.utcnow()
)
assert state.remaining_minutes == 116
assert state.remaining_percentage == Decimal("53.70")

# Test deployment gating
assert not state.is_exhausted(threshold_pct=Decimal("10"))
allowed, reason = await manager.check_deployment_allowed()
assert allowed == True
```

## Audit Status: PASSED

### Compliance Summary
- **Structure**: Well-organized following Google SRE principles
- **Documentation**: Comprehensive docstrings with usage examples
- **Error Handling**: Proper exception handling with context
- **Type Hints**: Complete type annotations
- **Async/Await**: Correct async patterns throughout
- **Data Classes**: Proper use of frozen dataclasses for value objects
- **Database**: Proper schema with indexes for performance
- **Logging**: Context-aware logging at appropriate levels
- **Configuration**: Sensible defaults with override capability
- **Singleton Pattern**: Module-level singleton management

### Strengths
1. Complete implementation of Google SRE error budget methodology
2. Clean domain model with value objects (Cosmic Python pattern)
3. Proper time window handling for all periods
4. Deployment gating support
5. Burn rate monitoring and alerting
6. Comprehensive incident tracking
7. Decimal precision for financial calculations
8. Callback system for custom alert handling

### No Critical Issues Found
All code follows best practices for:
- Google SRE Book principles
- Clean Architecture patterns
- Domain-Driven Design (DDD)
- Async Python programming
- Database operations
- Error handling
- Type safety

### Domain Model (Cosmic Python Pattern)
- `TimeWindow`: Value object (frozen, immutable)
- `BudgetAllowance`: Value object (frozen, immutable)
- `BudgetConsumption`: Value object
- `ErrorBudgetState`: Domain entity with business logic
- `ErrorBudgetManager`: Application service (uses domain objects)
- Business rules encapsulated in domain methods

### SRE Rule 20 Compliance
This module implements SRE Rule 20 (Error Budgets) by:
- Calculating error budgets from SLO targets
- Tracking real-time budget consumption
- Monitoring burn rate
- Triggering alerts on thresholds
- Supporting deployment gates

---
*Audited on 2026-02-07*
