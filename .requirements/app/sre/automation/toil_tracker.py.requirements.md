# Requirements: sre/automation/toil_tracker.py

## Source File Analysis
- **File Path**: `app/sre/automation/toil_tracker.py`
- **Lines of Code**: 1136
- **Status**: PASSED
- **Audit Date**: 2026-02-07

## Purpose
Implements Google SRE toil tracking system (Google SRE Chapter 1). Tracks manual, repetitive operational work vs. sustainable engineering work with the goal of reducing toil to <50% of total work time. Key objectives:
- Track all operational work (toil vs. engineering)
- Calculate toil percentage over time windows
- Identify top sources of toil for automation
- Generate automation opportunity reports
- Monitor progress toward toil reduction goals

## Dependencies
- Internal: None (standalone SRE module)
- External:
  - `aiosqlite`: Async SQLite database for persistence
  - `asyncio`: Async/await patterns
  - `json`: JSON serialization
  - `dataclasses`: Data structures
  - `pathlib`: Path operations

## Classes/Functions

### Enums
- `ToilCategory(str, Enum)`: INCIDENT_RESPONSE, DEPLOYMENT, MONITORING, CAPACITY_PLANNING, MAINTENANCE, SUPPORT, DOCUMENTATION, TROUBLESHOOTING, CONFIGURATION, MANUAL_DATA, ON_CALL, REVIEW, OTHER
- `AutomationPotential(str, Enum)`: HIGH, MEDIUM, LOW, NONE

### Data Classes
- `ToilEntry`: A single work entry for toil tracking
  - `is_toil` property: Returns True if manual and automatable
- `ToilMetrics`: Metrics for toil analysis
- `AutomationOpportunity`: Identified opportunity for automation
- `ToilReport`: Comprehensive toil report
- `ToilConfig`: Configuration for toil tracker

### Main Class
- `ToilTracker`: Track toil vs engineering work
  - `initialize()`: Initialize database and load recent entries
  - `log_work()`: Log a work entry
  - `calculate_toil_percentage()`: Calculate toil as percentage of total work
  - `get_top_toil_sources()`: Get top sources of toil by category
  - `get_top_toil_tasks()`: Get top individual toil tasks
  - `generate_automation_opportunities()`: Identify automation opportunities
  - `generate_report()`: Generate comprehensive toil report
  - `get_engineer_breakdown()`: Get toil breakdown by engineer
  - `get_trend_data()`: Get historical trend data
  - `export_to_json()`: Export toil data to JSON

### Private Methods
- `_init_database()`: Initialize SQLite schema
- `_load_recent_entries()`: Load recent entries from database
- `_detect_category()`: Auto-detect category from task description
- `_calculate_metrics()`: Calculate metrics from entries
- `_generate_recommendations()`: Generate recommendations based on analysis

## Business Logic

### Toil Definition (Google SRE Chapter 1)
**Toil** = Manual, repetitive work that could be automated
**Engineering** = Sustainable work that reduces future toil
**Target** = Toil should be <50% of total work time

### Toil Detection Logic
```python
def is_toil(self) -> bool:
    """
    Toil is defined as manual work that could be automated.
    Engineering work (assignable=False) is not toil.
    """
    return not self.automated and self.assignable
```

### Work Entry Categories
- **Incident Response**: incident, outage, sev, alert, page, emergency
- **Deployment**: deploy, release, rollout, rollback, promotion
- **Monitoring**: monitor, alert, dashboard, metric, graph
- **Capacity Planning**: capacity, scaling, resource, forecast
- **Maintenance**: maintenance, patch, upgrade, cleanup
- **Support**: support, ticket, help, user issue
- **Documentation**: document, wiki, runbook, sop
- **Troubleshooting**: troubleshoot, debug, investigate, diagnose
- **Configuration**: config, setting, parameter
- **Manual Data**: manual data, data entry, spreadsheet
- **On-Call**: on-call, handoff, escalation
- **Review**: review, audit, check

### Automation Opportunity Scoring
Priority = frequency × (avg_duration / 60) × automation_potential_score
- HIGH potential: 3.0
- MEDIUM potential: 2.0
- LOW potential: 1.0
- NONE potential: 0.0

### Configuration Defaults
- Toil warning threshold: 50%
- Toil critical threshold: 70%
- Automation target coverage: 80%

## Data Models

### Database Schema
```sql
CREATE TABLE toil_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    task TEXT NOT NULL,
    category TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    automated BOOLEAN NOT NULL,
    assignable BOOLEAN NOT NULL,
    automation_potential TEXT NOT NULL,
    engineer TEXT,
    tags TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('utc'))
)

-- Indexes
CREATE INDEX idx_toil_service_timestamp ON toil_entries(service_name, timestamp)
CREATE INDEX idx_toil_category ON toil_entries(category)
CREATE INDEX idx_toil_engineer ON toil_entries(engineer)
```

## API Contracts

### Initialization
```python
tracker = ToilTracker("trading_system", config=ToilConfig())
await tracker.initialize()
```

### Logging Work
```python
entry = tracker.log_work(
    task="Manual deployment to production",
    category=ToilCategory.DEPLOYMENT,
    duration=45,
    automated=False,
    assignable=True,
    automation_potential="high",
    engineer="john.doe",
    tags=["production", "urgent"],
    notes="Manual rollback required"
)
await tracker.save_entry(entry)
```

### Getting Toil Percentage
```python
toil_pct = tracker.calculate_toil_percentage(days=30)
```

### Generating Report
```python
report = await tracker.generate_report(days=30)
print(f"Toil: {report.metrics.toil_percentage:.1f}%")
print(f"Top opportunities: {report.automation_opportunities}")
```

### Export to JSON
```python
json_str = tracker.export_to_json(days=30, filepath="reports/toil_report.json")
```

## Error Handling
- Database errors: Logged with context
- ValueError: Raised for invalid duration or category
- TypeError: Caught for type conversion issues
- Invalid entries: Logged but don't block processing

### Exception Handling Pattern
```python
try:
    # Database operation
except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
    self.logger.error(f"Context: {e}")
    raise
```

## Performance Considerations
- **In-memory entries**: Recent entries kept in memory for fast queries
- **Database indexing**: Indexes on service_name, timestamp, category, engineer
- **Async operations**: All I/O is non-blocking
- **Lazy loading**: Entries loaded on initialization, then cached
- **JSON serialization**: Efficient JSON export with proper encoding

### Optimization Notes
- List comprehension for filtering (O(n) complexity)
- Dictionary grouping for O(1) lookups
- Sorted() for top-k queries (O(n log n))
- Automatic category detection reduces manual tagging

## Testing Strategy

### Unit Tests Needed
1. Toil detection logic (automated vs assignable)
2. Category auto-detection from task descriptions
3. Toil percentage calculation
4. Automation opportunity priority scoring
5. Metrics calculation accuracy

### Integration Tests Needed
1. Database persistence and recovery
2. Report generation with real data
3. JSON export/import
4. Engineer breakdown accuracy
5. Trend data calculation

### Edge Cases to Test
1. Empty work entry list
2. All automated work (0% toil)
3. All manual work (100% toil)
4. Negative duration (should raise ValueError)
5. Invalid category strings
6. Special characters in task descriptions
7. Concurrent work logging

### Example Test Cases
```python
# Test toil detection
entry = ToilEntry(
    timestamp=datetime.utcnow(),
    task="Manual deployment",
    category=ToilCategory.DEPLOYMENT,
    duration_minutes=30,
    automated=False,
    assignable=True
)
assert entry.is_toil == True

# Test engineering work (not toil)
eng_entry = ToilEntry(
    timestamp=datetime.utcnow(),
    task="Write deployment automation script",
    category=ToilCategory.DEPLOYMENT,
    duration_minutes=120,
    automated=False,
    assignable=False  # Engineering work
)
assert eng_entry.is_toil == False
```

## Audit Status: PASSED

### Compliance Summary
- **Structure**: Well-organized following Google SRE principles
- **Documentation**: Comprehensive docstrings with usage examples
- **Error Handling**: Proper exception handling with context
- **Type Hints**: Complete type annotations
- **Async/Await**: Correct async patterns throughout
- **Data Classes**: Proper use of dataclasses for value objects
- **Database**: Proper schema with indexes for performance
- **Logging**: Context-aware logging at appropriate levels
- **Configuration**: Sensible defaults with override capability
- **Singleton Pattern**: Module-level singleton management

### Strengths
1. Complete implementation of Google SRE toil tracking methodology
2. Intelligent auto-detection of toil categories
3. Comprehensive reporting with automation opportunity analysis
4. Engineer-level breakdown for accountability
5. Trend analysis for historical tracking
6. JSON export for external analysis
7. Priority-based automation opportunity scoring
8. Threshold-based alerting for toil levels

### No Critical Issues Found
All code follows best practices for:
- Google SRE Book Chapter 1 principles
- Clean Architecture patterns
- Async Python programming
- Database operations
- Error handling
- Type safety
- Domain modeling

### Domain Model (Cosmic Python Pattern)
- `ToilEntry`: Entity representing work entry
- `ToilMetrics`: Value object for calculated metrics
- `AutomationOpportunity`: Value object for opportunities
- `ToilReport`: Aggregated report with analysis
- Business logic encapsulated in domain methods

---
*Audited on 2026-02-07*
