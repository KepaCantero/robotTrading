# Requirements: services/risk_scaling/risk_scaling_monitor.py

## Source File Analysis
- **File Path**: `app/services/risk_scaling/risk_scaling_monitor.py`
- **Lines of Code**: 426
- **Language**: Python 3
- **Purpose**: Dashboard & API interface for risk scaling monitoring

## Purpose
Provides real-time monitoring, alerting, and reporting for risk scaling system:
- Real-time risk scaling status
- Historical tracking and trends
- Alert generation and subscription
- Performance reporting
- Dashboard data aggregation

## Dependencies
- **Internal**:
  - `app.services.risk_scaling.models` - Data models (RiskScalingState, RiskScalingStatus, etc.)
- **External**:
  - `logging` - Structured logging
  - `datetime` - Timestamp handling
  - `typing` - Type hints
  - `decimal.Decimal` - Financial precision

## Classes/Functions

### RiskScalingMonitor
- **Purpose**: Real-time monitoring and alerting
- **Key Methods**:
  - `get_scaling_status()` - Current status for dashboard
  - `get_scaling_history()` - Historical snapshots
  - `subscribe_to_alerts()` - Alert subscription
  - `record_alert()` - Record and dispatch alerts
  - `get_scaling_trends()` - Trend analysis
  - `get_alert_history()` - Filtered alert history
  - `resolve_alert()` - Mark alert as resolved
  - `store_state()` - Store state snapshot
  - `generate_daily_report()` - Daily report
  - `get_portfolio_dashboard_data()` - All dashboard data

## Business Logic

### Risk Level Determination
```python
if drawdown_scale == 0:
    risk_level = RiskLevel.HALT
elif combined_scale < 0.5:
    risk_level = RiskLevel.CRITICAL
elif combined_scale < 0.8:
    risk_level = RiskLevel.WARNING
elif combined_scale < 1.0:
    risk_level = RiskLevel.CAUTION
else:
    risk_level = RiskLevel.SAFE
```

### Alert Dispatch
For each subscription, alert is dispatched if:
- Portfolio matches
- Alert type matches subscription types
- Severity >= min_severity
- Subscription is enabled

### Trend Analysis
Calculates for each scale factor:
- Current value
- Average value
- Min/Max values
- Trend direction (increasing/decreasing)

### History Retention
- Default: 30 days
- Configurable via `history_retention_days`
- Automatic cleanup of old snapshots

## Data Models
Uses models from `app.services.risk_scaling.models`:
- RiskScalingState - Portfolio state
- RiskScalingStatus - Dashboard status
- RiskAlert - Alert instances
- AlertSubscription - Alert subscriptions
- RiskScalingReport - Daily reports
- RiskScalingSnapshot - Historical snapshots

## API Contracts
```python
async def get_scaling_status(
    portfolio_id: str
) -> RiskScalingStatus

async def subscribe_to_alerts(
    portfolio_id: str,
    alert_types: List[RiskAlertType],
    min_severity: RiskLevel = RiskLevel.WARNING
) -> AlertSubscription
```

## Error Handling
- Returns ValueError for missing portfolio
- Handles empty history gracefully
- Logs all alert dispatches
- Catches and logs exceptions

## Performance Considerations
- In-memory state storage (fast but not persistent)
- O(n) history filtering where n = snapshots
- Efficient trend calculation with single pass
- Dashboard data aggregation in one call

## Testing Strategy
- Test status retrieval
- Test alert subscription and dispatch
- Test trend analysis with synthetic data
- Test history cleanup

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings used
- FMT-007: default_factory for mutable defaults

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax (List, Dict, Optional)
- TYP-005: Models properly typed

### Async
- ASYNC-001: All public methods are async
- ASYNC-002: Proper async/await usage

### Clean Code
- CC-001: Descriptive names
- CC-006: Error handling with logging
- CC-007: Functions reasonable length

### Logging
- LOG-001: Uses logging module
- LOG-003: Appropriate levels (info, warning)
- LOG-004: Structured messages

## Audit Status
**Status**: PASSED**

### Strengths
1. Clean async API design
2. Comprehensive monitoring capabilities
3. Good alert subscription system
4. Trend analysis functionality
5. Dashboard data aggregation
6. Proper type hints throughout
7. Good error handling and logging
8. History retention with cleanup

### Minor Observations
1. In-memory storage not persistent (would need database for production)
2. Could add WebSocket support for real-time updates
3. Trend calculation could be more sophisticated

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready for in-memory monitoring
- Suitable for single-instance deployments
- Would need persistence for multi-instance

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0081*
*Status: PASSED*
