# Toil Tracking System

Google SRE-compliant toil tracking and automation opportunity identification.

## Overview

**Toil** is manual, repetitive operational work that could be automated. Following Google SRE principles, this system helps teams track toil and reduce it to less than 50% of total work time.

### Key Concepts

- **Toil**: Manual work (incident response, deployment, monitoring, etc.)
- **Engineering**: Sustainable work that reduces future toil
- **Target**: Toil should be <50% of total work time
- **Automation Coverage**: Percentage of work that is automated

## Installation

The toil tracker is included in the SRE automation package:

```python
from app.sre.automation import ToilTracker, ToilCategory
```

## Quick Start

```python
from app.sre.automation import ToilTracker, ToilCategory

# Create tracker
tracker = ToilTracker("my_service")
await tracker.initialize()

# Log work
tracker.log_work(
    task="Manual deployment to production",
    category="deployment",
    duration=45,  # minutes
    automated=False,
    assignable=True,
)

# Calculate toil percentage
toil_pct = tracker.calculate_toil_percentage(days=30)

# Generate report
report = await tracker.generate_report(days=30)
```

## Toil Categories

The tracker recognizes these toil categories:

- `incident_response`: Handling incidents and outages
- `deployment`: Manual deployments and releases
- `monitoring`: Manual monitoring and dashboard work
- `capacity_planning`: Capacity management tasks
- `maintenance`: System maintenance and patching
- `support`: User support and tickets
- `documentation`: Writing and updating docs
- `troubleshooting`: Debugging and investigation
- `configuration`: Manual configuration changes
- `manual_data`: Manual data entry/processing
- `on_call`: On-call related tasks
- `review`: Code and design reviews
- `other`: Other manual work

## Features

### 1. Work Logging

Log any work as toil or engineering:

```python
# Manual toil
tracker.log_work(
    task="Investigate database alert",
    category="incident_response",
    duration=30,
    automated=False,
    engineer="alice",
)

# Automated work (not toil)
tracker.log_work(
    task="Automated deployment",
    category="deployment",
    duration=5,
    automated=True,
    engineer="system",
)

# Engineering work (reduces future toil)
tracker.log_work(
    task="Build deployment automation",
    category="other",
    duration=120,
    automated=False,
    assignable=False,  # Not assignable - it's engineering
)
```

### 2. Toil Percentage Calculation

Track your toil over time:

```python
# Overall toil percentage
toil_pct = tracker.calculate_toil_percentage(days=30)

# Per-engineer breakdown
breakdown = tracker.get_engineer_breakdown(days=30)
for engineer, metrics in breakdown.items():
    print(f"{engineer}: {metrics.toil_percentage:.1f}% toil")
```

### 3. Top Toil Sources

Identify where toil is coming from:

```python
# By category
top_sources = tracker.get_top_toil_sources(days=30, limit=10)
for category, minutes in top_sources:
    print(f"{category}: {minutes} minutes")

# By specific task
top_tasks = tracker.get_top_toil_tasks(days=30, limit=10)
for task, minutes in top_tasks:
    print(f"{task}: {minutes} minutes")
```

### 4. Automation Opportunities

Get prioritized automation recommendations:

```python
opportunities = tracker.generate_automation_opportunities(days=30)
for opp in opportunities[:5]:
    print(f"Task: {opp.task_pattern}")
    print(f"  Priority: {opp.priority}/100")
    print(f"  Frequency: {opp.frequency} times/month")
    print(f"  Savings: {opp.estimated_savings_hours:.1f} hours/month")
    print(f"  Effort: {opp.implementation_effort}")
```

### 5. Comprehensive Reports

Generate full reports with recommendations:

```python
report = await tracker.generate_report(days=30)

# Metrics
print(f"Toil: {report.metrics.toil_percentage:.1f}%")
print(f"Automation: {report.metrics.automation_coverage:.1f}%")

# Recommendations
for rec in report.recommendations:
    print(f"- {rec}")

# Export to JSON
json_data = tracker.export_to_json(days=30, filepath="toil_report.json")
```

## Configuration

Customize thresholds and targets:

```python
from app.sre.automation import ToilConfig

config = ToilConfig(
    toil_warning_threshold=50.0,   # Alert at 50% toil
    toil_critical_threshold=70.0,  # Critical at 70% toil
    automation_target_coverage=80.0,  # Target 80% automation
)

tracker = ToilTracker("my_service", config)
```

## Best Practices

### 1. Log Consistently

Log ALL work, not just toil:

```python
# Log everything
tracker.log_work("Manual deployment", "deployment", 45, automated=False)
tracker.log_work("Feature work", "other", 120, automated=False)
tracker.log_work("Code review", "review", 60, automated=False)
```

### 2. Be Honest About Assignability

Mark whether tasks COULD be automated:

```python
# Clearly automatable
tracker.log_work(
    "Manual deployment",
    "deployment",
    45,
    automated=False,
    assignable=True,
    automation_potential="high",
)

# Requires human judgment
tracker.log_work(
    "Complex incident diagnosis",
    "incident_response",
    60,
    automated=False,
    assignable=True,
    automation_potential="low",
)
```

### 3. Track Per-Engineer

Understand individual toil burdens:

```python
tracker.log_work(
    "Task",
    "deployment",
    30,
    engineer="alice",  # Track who did the work
)
```

### 4. Review Regularly

Generate weekly or monthly reports:

```python
# Weekly review
weekly_report = await tracker.generate_report(days=7)

# Monthly review
monthly_report = await tracker.generate_report(days=30)
```

### 5. Act on Opportunities

Use the automation opportunities list:

```python
opportunities = tracker.generate_automation_opportunities(days=30)

# Focus on high priority items
high_priority = [o for o in opportunities if o.priority > 50]

for opp in high_priority:
    # Create automation projects for these
    print(f"Project: Automate {opp.task_pattern}")
    print(f"  Expected savings: {opp.estimated_savings_hours:.1f}h/month")
```

## Metrics

### Toil Percentage

Percentage of time spent on toil vs. total work.

```
Toil % = (Toil Minutes / Total Minutes) × 100
```

**Target**: < 50%

### Automation Coverage

Percentage of work that is automated.

```
Automation % = (Automated Minutes / Total Minutes) × 100
```

**Target**: > 80%

### Priority Score

Calculated for each automation opportunity:

```
Priority = Frequency × Avg Duration × Potential Score
```

Where Potential Score is:
- High: 3.0
- Medium: 2.0
- Low: 1.0
- None: 0.0

## Thresholds

Default thresholds:

| Level | Toil % | Action |
|-------|--------|--------|
| Good | < 50% | Continue monitoring |
| Warning | 50-70% | Plan automation initiatives |
| Critical | > 70% | Immediate action required |

## Database Schema

The tracker uses SQLite for persistence:

```sql
CREATE TABLE toil_entries (
    id INTEGER PRIMARY KEY,
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
    created_at TEXT NOT NULL
);
```

## Example Output

```
============================================================
Toil Report: algo_trading_system
============================================================
Period: 2024-01-01 to 2024-01-30

Overall Metrics:
  Total time: 10,000 minutes
  Toil: 6,500 minutes (65.0%)
  Engineering: 3,500 minutes (35.0%)
  Automated: 1,500 minutes (15.0%)

⚠️ WARNING: Toil above 50% target

Top Toil Sources:
  1. deployment: 2,500 minutes (41.7%)
  2. incident_response: 1,800 minutes (30.0%)
  3. monitoring: 1,200 minutes (20.0%)

Automation Opportunities:
  1. Manual deployment (Priority: 90/100)
     Frequency: 50 times/month
     Savings: 33.3 hours/month
     Effort: LOW

Recommendations:
  1. CRITICAL: Toil at 65.0%, above 50% target.
  2. Top toil source: deployment (2,500 minutes).
  3. Highest priority: Automate "Manual deployment"
     (could save ~33.3 hours/month)
```

## Integration with Error Budgets

Combine toil tracking with error budgets:

```python
from app.sre.error_budgets import ErrorBudgetManager
from app.sre.automation import ToilTracker

# Track both
budget_manager = ErrorBudgetManager("my_service")
toil_tracker = ToilTracker("my_service")

# High toil often correlates with budget burn
if toil_pct > 50:
    budget_state = await budget_manager.get_current_state()
    print(f"Toil is high: {toil_pct:.1f}%")
    print(f"Error budget remaining: {budget_state.remaining_percentage:.1f}%")
```

## File Locations

- **Module**: `/app/sre/automation/toil_tracker.py`
- **Tests**: `/tests/sre/automation/test_toil_tracker.py`
- **Example**: `/examples/toil_tracker_example.py`
- **Database**: `data/toil_tracker.db` (default)

## References

- Google SRE Workbook: Chapter 1 - Toil
- Google SRE Book: Chapter 1 - Toil
- https://sre.google/sre-book/toil/
- https://sre.google/workbook/toil/

## License

Part of the algoTrading SRE toolkit.
