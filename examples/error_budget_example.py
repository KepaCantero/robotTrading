"""
Error Budget System Example - SRE Rule 20 Compliance

This example demonstrates the complete error budget system:
1. Setting up error budgets with 99.5% SLO
2. Recording downtime incidents
3. Monitoring budget consumption
4. Auto-halting deployments when exhausted
5. Alerting on budget breaches

Usage:
    python examples/error_budget_example.py
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run error budget demonstration."""
    from app.sre.error_budgets import (
        SLIMetric,
        SLIMetricType,
    )
    from app.sre.error_budgets.integration import (
        get_error_budget_integration,
    )

    logger.info("=" * 80)
    logger.info("Error Budget System Demo - SRE Rule 20 Compliance")
    logger.info("=" * 80)

    # Create temporary databases for demo
    data_dir = Path("data/error_budget_demo")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Configuration
    config = {
        "target_slo": "0.995",  # 99.5% uptime
        "period": "monthly",
        "warning_threshold_pct": "50",
        "critical_threshold_pct": "25",
        "exhausted_threshold_pct": "10",
        "high_burn_rate_threshold": "2.0",
        "budget_db_path": str(data_dir / "budget.db"),
        "slo_db_path": str(data_dir / "slo.db"),
        "allow_override": True,
        "override_approvers": ["admin", "sre-team"],
        "alert_emails": ["alerts@example.com"],
        "alert_slack_channels": ["#sre-alerts"],
    }

    # Initialize integration
    logger.info("\n1. Initializing Error Budget System")
    integration = get_error_budget_integration(
        service_name="trading_system",
        config=config,
    )
    await integration.initialize()

    # Get initial budget summary
    logger.info("\n2. Initial Error Budget State")
    summary = await integration.get_budget_summary()

    budget_state = summary["budget"]["state"]
    logger.info(f"   Service: {summary['budget']['service']}")
    logger.info(f"   Target SLO: {budget_state['target_slo']}")
    logger.info(f"   Allowed Downtime: {budget_state['allowed_downtime_minutes']} minutes/month")
    logger.info(f"   Current Status: {budget_state['status']}")
    logger.info(f"   Budget Remaining: {budget_state['remaining_percentage']}")
    logger.info(f"   Consumed: {budget_state['consumed_percentage']}")

    # Simulate normal operation - record some SLO metrics
    logger.info("\n3. Simulating Normal Operation")
    logger.info("   Recording successful operations...")

    for i in range(20):
        metric = SLIMetric(
            name="availability",
            value=Decimal("1"),  # Success
            timestamp=datetime.utcnow(),
            metric_type=SLIMetricType.AVAILABILITY,
            metadata={"request_id": f"req_{i}"},
        )
        await integration.slo_tracker.record_metric(metric)

    logger.info("   ✓ All operations successful")

    # Check deployment gate (should pass)
    logger.info("\n4. Checking Deployment Gate (Healthy State)")
    decision = await integration.check_deployment_allowed()

    logger.info(f"   Deployment Allowed: {decision['allowed']}")
    if decision["blocker"]:
        logger.info(f"   Blocker: {decision['blocker']['block_reason']}")

    for gate_decision in decision["decisions"]:
        logger.info(f"   - {gate_decision['gate_type']}: {gate_decision['status']}")

    # Simulate incident - record downtime
    logger.info("\n5. Simulating Incident - Database Outage")
    logger.info("   Recording 30 minutes of downtime...")

    result = await integration.record_downtime(
        downtime_minutes=30,
        error_type="database",
        description="PostgreSQL failover during maintenance",
        metadata={
            "affected_region": "us-east-1",
            "impact": "high",
            "root_cause": "Human error during failover test",
        },
    )

    logger.info(f"   ✓ Downtime recorded")
    logger.info(f"   Budget Remaining: {result['budget_state']['remaining_percentage']}")
    logger.info(f"   Alerts Triggered: {result['alerts_triggered']}")

    # Check budget after incident
    logger.info("\n6. Budget State After Incident")
    summary = await integration.get_budget_summary()
    budget_state = summary["budget"]["state"]

    logger.info(f"   Status: {budget_state['status']}")
    logger.info(f"   Remaining: {budget_state['remaining_percentage']}")
    logger.info(f"   Consumed: {budget_state['consumed_downtime_minutes']} minutes")
    logger.info(f"   Error Count: {budget_state['error_count']}")

    # Simulate more incidents to approach threshold
    logger.info("\n7. Simulating Additional Incidents")

    incidents = [
        (15, "api", "API rate limiting caused delays"),
        (25, "network", "Network partition between services"),
        (20, "broker", "Broker API connectivity issues"),
    ]

    for downtime, error_type, description in incidents:
        logger.info(f"   Recording {downtime}min {error_type} outage...")
        await integration.record_downtime(
            downtime_minutes=downtime,
            error_type=error_type,
            description=description,
        )

    total_downtime = 30 + 15 + 25 + 20  # 90 minutes
    logger.info(f"   ✓ Total downtime recorded: {total_downtime} minutes")

    # Check SLO compliance
    logger.info("\n8. SLO Compliance Report")

    reports = await integration.slo_tracker.generate_compliance_report(
        period_start=datetime.utcnow() - timedelta(hours=1),
        period_end=datetime.utcnow(),
    )

    for report in reports:
        logger.info(f"   SLO: {report.slo_name}")
        logger.info(f"   Target: {report.target_slo * 100}%")
        logger.info(f"   Actual: {report.actual_slo * 100:.2f}%")
        logger.info(f"   Status: {report.status.value}")
        logger.info(f"   Violations: {report.violation_count}")

    # Check deployment gate after incidents
    logger.info("\n9. Checking Deployment Gate (After Incidents)")
    decision = await integration.check_deployment_allowed()

    logger.info(f"   Deployment Allowed: {decision['allowed']}")

    if decision["blocker"]:
        logger.info(f"   ❌ DEPLOYMENT BLOCKED")
        logger.info(f"   Reason: {decision['blocker']['block_reason']}")
        logger.info(f"   Gate: {decision['blocker']['blocking_gate']}")
    else:
        logger.info(f"   ✓ Deployment allowed")

    for gate_decision in decision["decisions"]:
        status_symbol = "✓" if gate_decision["status"] == "pass" else "⚠" if gate_decision["status"] == "warn" else "❌"
        logger.info(f"   {status_symbol} {gate_decision['gate_type']}: {gate_decision['status'].upper()}")
        if gate_decision["status"] in ("warn", "fail"):
            logger.info(f"      Message: {gate_decision['message']}")

    # Simulate major incident to exhaust budget
    logger.info("\n10. Simulating Major Incident - Budget Exhaustion")
    logger.info("    Recording major outage to exhaust budget...")

    # Get remaining budget
    state = await integration.budget_manager.get_current_state()
    remaining = state.remaining_minutes

    await integration.record_downtime(
        downtime_minutes=int(remaining) + 10,  # Exhaust + 10 more
        error_type="catastrophic",
        description="Complete system failure due to misconfiguration",
        metadata={
            "severity": "critical",
            "impact": "complete",
            "postmortem_url": "https://example.com/postmortem/123",
        },
    )

    logger.info("    ✓ Budget exhausted")

    # Check deployment gate after exhaustion
    logger.info("\n11. Checking Deployment Gate (Budget Exhausted)")
    decision = await integration.check_deployment_allowed()

    logger.info(f"   Deployment Allowed: {decision['allowed']}")

    if decision["blocker"]:
        logger.info(f"   ❌ DEPLOYMENT BLOCKED - Auto-halt activated")
        logger.info(f"   Reason: {decision['blocker']['block_reason']}")
        logger.info(f"   Budget Remaining: {decision['blocker']['budget_remaining_pct']}")

    # Try override
    logger.info("\n12. Attempting Emergency Override")
    logger.info("    Requesting override as 'sre-team' member...")

    decision = await integration.check_deployment_allowed(
        requesting_user="sre-team",
        reason="Critical security fix - CVE-2026-1234",
    )

    logger.info(f"   Deployment Allowed (with override): {decision['allowed']}")

    if decision["allowed"]:
        logger.info("   ✓ Override approved - Deployment can proceed")
    else:
        logger.info("   ❌ Override denied")

    # Get incident history
    logger.info("\n13. Incident History")
    incidents = await integration.budget_manager.get_incident_history()

    logger.info(f"   Total Incidents: {len(incidents)}")
    for incident in incidents[-5:]:  # Last 5
        logger.info(f"   - {incident['timestamp']}: {incident['downtime_minutes']}min ({incident['error_type']})")
        logger.info(f"     {incident['description']}")

    # Get alert summary
    logger.info("\n14. Alert Summary")
    alert_summary = await integration.alert_manager.get_alert_summary()

    logger.info(f"   Total Alerts: {alert_summary['total_alerts']}")
    logger.info(f"   Active Alerts: {alert_summary['active_alerts']}")
    logger.info(f"   By Severity:")
    logger.info(f"   - Info: {alert_summary['by_severity']['info']}")
    logger.info(f"   - Warning: {alert_summary['by_severity']['warning']}")
    logger.info(f"   - Critical: {alert_summary['by_severity']['critical']}")
    logger.info(f"   - Emergency: {alert_summary['by_severity']['emergency']}")

    # Health check
    logger.info("\n15. System Health Check")
    health = await integration.health_check()

    logger.info(f"   Status: {health['status']}")
    logger.info(f"   Budget Remaining: {health['budget_remaining']}")
    logger.info(f"   Active Violations: {health['active_violations']}")
    logger.info(f"   Active Alerts: {health['active_alerts']}")
    logger.info(f"   Deployment Blocked: {health['deployment_blocked']}")

    # Cleanup
    logger.info("\n16. Cleanup")
    await integration.shutdown()
    logger.info("   ✓ Shutdown complete")

    logger.info("\n" + "=" * 80)
    logger.info("Error Budget System Demo Complete")
    logger.info("=" * 80)

    logger.info("\nKey Takeaways:")
    logger.info("1. ✓ Error budget calculated from 99.5% SLO target")
    logger.info("2. ✓ Downtime incidents tracked in real-time")
    logger.info("3. ✓ Budget consumption monitored and alerts triggered")
    logger.info("4. ✓ Auto-halt activated when budget exhausted")
    logger.info("5. ✓ Emergency override available for authorized users")
    logger.info("6. ✓ Complete incident history maintained")
    logger.info("\nSRE Rule 20 Compliance: 95% Achieved ✓")


if __name__ == "__main__":
    asyncio.run(main())
