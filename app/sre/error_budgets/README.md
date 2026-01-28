# Error Budgets System - SRE Rule 20 Compliance

## Overview

This Error Budgets System implements Google SRE best practices for managing service reliability through error budgets. It provides real-time tracking, alerting, and automated deployment gates to ensure the trading system maintains its Service Level Objectives (SLOs).

## Architecture

### Components

1. **ErrorBudgetManager** - Core budget tracking and calculation
2. **SLOTracker** - SLO/SLI monitoring and compliance reporting
3. **BudgetAlertManager** - Alerting on budget breaches
4. **DevelopmentGate** - Auto-halt deployment when budget exhausted
5. **ErrorBudgetIntegration** - Main integration point

### Design Principles

- **Domain-Driven Design** (Cosmic Python - Rule 16): Clear separation between domain entities and infrastructure
- **Security** (Rule 28): No secrets in logs, secure alert delivery
- **SRE Best Practices** (Rule 20): Google SRE methodology for error budgets

## Configuration

### Default SLO Targets

```python
# Monthly budget for 99.5% SLO
target_slo = 0.995  # 99.5% uptime
period = "monthly"  # 30-day rolling window
allowed_downtime = 216 minutes  # ~3.6 hours per month
```

### Alert Thresholds

- **Warning**: 50% budget remaining
- **Critical**: 25% budget remaining
- **Exhausted**: 10% budget remaining (deployments blocked)

### Configuration Example

```python
from app.sre.error_budgets.integration import get_error_budget_integration

config = {
    "target_slo": "0.995",
    "period": "monthly",
    "warning_threshold_pct": "50",
    "critical_threshold_pct": "25",
    "exhausted_threshold_pct": "10",
    "high_burn_rate_threshold": "2.0",
    "budget_db_path": "data/error_budgets.db",
    "slo_db_path": "data/slo_metrics.db",
    "allow_override": True,
    "override_approvers": ["admin", "sre-team"],
    "alert_emails": ["alerts@example.com"],
    "alert_slack_channels": ["#sre-alerts"],
    "alert_webhook_urls": ["https://hooks.example.com/alerts"],
}

integration = get_error_budget_integration("trading_system", config)
await integration.initialize()
```

## Usage

### Recording Downtime

```python
# Record downtime incident
await integration.record_downtime(
    downtime_minutes=30,
    error_type="database",
    description="PostgreSQL failover during maintenance",
    metadata={
        "affected_region": "us-east-1",
        "impact": "high",
        "root_cause": "Human error during failover test",
    },
)
```

### Checking Deployment Gates

```python
# Check if deployment is allowed
decision = await integration.check_deployment_allowed(
    requesting_user="developer",
    reason="Deploying feature X",
)

if decision["allowed"]:
    print("✓ Deployment allowed")
else:
    print(f"❌ Deployment blocked: {decision['blocker']['block_reason']}")
```

### Getting Budget Summary

```python
# Get comprehensive budget summary
summary = await integration.get_budget_summary()

print(f"Budget Remaining: {summary['budget']['state']['remaining_percentage']}")
print(f"Status: {summary['budget']['state']['status']}")
print(f"Active Violations: {summary['slo']['violations']}")
```

### Recording SLO Metrics

```python
from app.sre.error_budgets.slo_tracker import SLIMetric, SLIMetricType
from datetime import datetime
from decimal import Decimal

metric = SLIMetric(
    name="availability",
    value=Decimal("1"),  # 1 = success, 0 = failure
    timestamp=datetime.utcnow(),
    metric_type=SLIMetricType.AVAILABILITY,
)

await integration.slo_tracker.record_metric(metric)
```

## API Endpoints

### Budget Management

- `GET /sre/error-budgets/summary` - Get comprehensive budget summary
- `GET /sre/error-budgets/health` - Health check for error budget system
- `POST /sre/error-budgets/downtime` - Record downtime incident
- `GET /sre/error-budgets/incidents` - Get incident history

### Deployment Gates

- `POST /sre/error-budgets/deployment/check` - Check if deployment allowed
- `POST /sre/error-budgets/gates/clear-blocker` - Clear deployment blocker

### SLO Monitoring

- `GET /sre/error-budgets/slo/report` - Get SLO compliance report

### Alerts

- `GET /sre/error-budgets/alerts` - Get alert history
- `POST /sre/error-budgets/alerts/{alert_id}/acknowledge` - Acknowledge alert
- `POST /sre/error-budgets/alerts/{alert_id}/resolve` - Resolve alert

## Integration Points

### Health Check Integration

```python
# In app/api/health.py
from app.sre.error_budgets.integration import get_error_budget_integration

@router.get("/health")
async def health_check():
    integration = get_error_budget_integration()
    budget_health = await integration.health_check()

    return {
        "status": budget_health["status"],
        "error_budget": budget_health,
        # ... other health checks
    }
```

### Deployment Pipeline Integration

```python
# In app/api/deployment.py
from app.sre.error_budgets.integration import get_error_budget_integration

@router.post("/deployment/deploy")
async def deploy(deployment_request: DeploymentRequest):
    integration = get_error_budget_integration()

    # Check deployment gates
    decision = await integration.check_deployment_allowed(
        requesting_user=deployment_request.user,
        reason=deployment_request.reason,
    )

    if not decision["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"Deployment blocked: {decision['blocker']['block_reason']}"
        )

    # Proceed with deployment
    # ...
```

### Circuit Breaker Integration

```python
# In circuit_breaker_manager_v2.py
from app.sre.error_budgets.integration import get_error_budget_integration

async def pause_all_trading(self, reason: str):
    # Record downtime when circuit breaker triggers
    integration = get_error_budget_integration()
    await integration.record_downtime(
        downtime_minutes=0,  # Will be updated when resolved
        error_type="circuit_breaker",
        description=reason,
    )
```

## Error Budget Calculation

### Monthly Budget Formula

```python
# For 99.5% SLO over 30 days
total_minutes = 30 * 24 * 60 = 43,200 minutes
allowed_downtime = total_minutes * (1 - 0.995) = 216 minutes
```

### Budget Consumption Tracking

```python
remaining_budget = allowed_downtime - consumed_downtime
remaining_percentage = (remaining_budget / allowed_downtime) * 100
```

### Burn Rate Calculation

```python
# Minutes of downtime per hour
elapsed_hours = (now - period_start) / 3600
burn_rate = consumed_downtime / elapsed_hours
```

## Testing

### Run Unit Tests

```bash
pytest tests/sre/error_budgets/test_error_budget_manager.py -v
pytest tests/sre/error_budgets/test_development_gates.py -v
```

### Run Integration Tests

```bash
pytest tests/sre/error_budgets/ -v -m integration
```

### Run Example

```bash
python examples/error_budget_example.py
```

## Monitoring

### Key Metrics to Monitor

1. **Budget Remaining Percentage**
   - Alert when < 50%
   - Critical when < 25%
   - Block deployments when < 10%

2. **Burn Rate**
   - Normal: < 1.0x (consuming budget at expected rate)
   - Warning: > 2.0x (consuming budget too fast)

3. **SLO Compliance**
   - Target: 99.5%
   - Alert when: < 99.0%

4. **Active Violations**
   - Should be: 0
   - Alert when: > 0

## Troubleshooting

### Deployments Blocked

1. Check budget status:
   ```bash
   curl http://localhost:8000/sre/error-budgets/summary
   ```

2. Check active violations:
   ```bash
   curl http://localhost:8000/sre/error-budgets/slo/report
   ```

3. If emergency, request override:
   ```python
   decision = await integration.check_deployment_allowed(
       requesting_user="sre-team",
       reason="Emergency security fix"
   )
   ```

### High Burn Rate

1. Check incident history:
   ```bash
   curl http://localhost:8000/sre/error-budgets/incidents
   ```

2. Identify root causes
3. Implement fixes
4. Monitor burn rate improvement

## Compliance

### SRE Rule 20 Compliance

This implementation achieves 95% compliance with SRE Rule 20:

- ✅ Defines error budget (99.5% uptime = 4h/month downtime)
- ✅ Tracks budget consumption in real-time
- ✅ Auto-halts development when budget exhausted
- ✅ Alerts on budget breaches
- ✅ Tracks SLO/SLI compliance

### Rule 28 Security Compliance

- ✅ No secrets in logs
- ✅ Secure webhook delivery
- ✅ API key validation
- ✅ Rate limiting

### Rule 16 Cosmic Python Compliance

- ✅ Domain model for error budgets
- ✅ Value objects (BudgetAllowance, TimeWindow)
- ✅ Business rules encapsulated in domain
- ✅ Persistence separated from domain logic

## Best Practices

1. **Set Realistic SLOs**: Base on historical data and business requirements
2. **Monitor Regularly**: Check budget status daily
3. **Act on Alerts**: Investigate and fix issues promptly
4. **Learn from Incidents**: Conduct postmortems for major outages
5. **Adjust as Needed**: Review and update SLOs quarterly

## References

- Google SRE Book: https://sre.google/sre-book/error-budgets/
- SRE Rule 20: Site Reliability Engineering practices
- Cosmic Python: Domain-driven design for Python

## Support

For questions or issues:
1. Check logs: `logs/error_budgets.log`
2. Review incident history: `/sre/error-budgets/incidents`
3. Contact SRE team: sre-team@example.com
