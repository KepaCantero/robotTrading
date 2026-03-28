#!/usr/bin/env python3
"""
Toil Tracker Example Usage.

Demonstrates how to use the Toil Tracker system to measure and reduce
operational toil following Google SRE principles.
"""

import asyncio
import sys

sys.path.insert(0, '/Users/kepa.cantero/Projects/algoTrading')

from app.sre.automation.toil_tracker import (
    ToilTracker,
    ToilConfig,
)


async def main():
    """Run toil tracker demonstration."""

    print("=" * 60)
    print("Toil Tracker Demonstration")
    print("=" * 60)
    print()

    # Create tracker with custom config
    config = ToilConfig(
        toil_warning_threshold=50.0,
        toil_critical_threshold=70.0,
        automation_target_coverage=80.0,
    )

    tracker = ToilTracker("algo_trading_system", config)
    await tracker.initialize()

    print("Initialized Toil Tracker for algo_trading_system")
    print()

    # -----------------------------------------------------------------
    # Log some sample work entries
    # -----------------------------------------------------------------
    print("Logging work entries...")
    print()

    # Manual toil work
    tracker.log_work(
        task="Manual deployment to production",
        category="deployment",
        duration=45,
        automated=False,
        assignable=True,
        automation_potential="high",
        engineer="alice",
        tags=["production", "urgent"],
        notes="Manual process, should be automated",
    )

    tracker.log_work(
        task="Investigate database alert",
        category="incident_response",
        duration=30,
        automated=False,
        assignable=True,
        automation_potential="medium",
        engineer="bob",
        tags=["database", "sev3"],
    )

    tracker.log_work(
        task="Manual capacity planning spreadsheet",
        category="capacity_planning",
        duration=60,
        automated=False,
        assignable=True,
        automation_potential="high",
        engineer="alice",
    )

    tracker.log_work(
        task="Respond to support tickets",
        category="support",
        duration=90,
        automated=False,
        assignable=True,
        automation_potential="low",
        engineer="charlie",
    )

    tracker.log_work(
        task="Manual configuration update",
        category="configuration",
        duration=20,
        automated=False,
        assignable=True,
        automation_potential="medium",
        engineer="bob",
    )

    # Automated work (not toil)
    tracker.log_work(
        task="Automated deployment (CI/CD)",
        category="deployment",
        duration=5,
        automated=True,
        assignable=True,
        engineer="system",
    )

    tracker.log_work(
        task="Feature development",
        category="other",
        duration=120,
        automated=False,
        assignable=False,
        engineer="alice",
        notes="Building new trading strategy",
    )

    tracker.log_work(
        task="Code review",
        category="review",
        duration=60,
        automated=False,
        assignable=False,
        engineer="bob",
    )

    print("Logged 8 work entries")
    print()

    # -----------------------------------------------------------------
    # Calculate toil percentage
    # -----------------------------------------------------------------
    print("Calculating toil metrics...")
    print()

    toil_pct = tracker.calculate_toil_percentage(days=30)
    print(f"Toil Percentage: {toil_pct:.1f}%")

    if toil_pct > config.toil_critical_threshold:
        print(f"  ❌ CRITICAL: Above {config.toil_critical_threshold}% threshold")
    elif toil_pct > config.toil_warning_threshold:
        print(f"  ⚠️  WARNING: Above {config.toil_warning_threshold}% threshold")
    else:
        print(f"  ✓ Good: Below {config.toil_warning_threshold}% target")
    print()

    # -----------------------------------------------------------------
    # Get top toil sources
    # -----------------------------------------------------------------
    print("Top Toil Sources:")
    print()

    top_sources = tracker.get_top_toil_sources(days=30, limit=5)
    for i, (source, minutes) in enumerate(top_sources, 1):
        hours = minutes / 60
        print(f"  {i}. {source}: {minutes} minutes ({hours:.1f} hours)")
    print()

    # -----------------------------------------------------------------
    # Get top toil tasks
    # -----------------------------------------------------------------
    print("Top Toil Tasks:")
    print()

    top_tasks = tracker.get_top_toil_tasks(days=30, limit=5)
    for i, (task, minutes) in enumerate(top_tasks, 1):
        print(f"  {i}. {task}: {minutes} minutes")
    print()

    # -----------------------------------------------------------------
    # Generate automation opportunities
    # -----------------------------------------------------------------
    print("Automation Opportunities:")
    print()

    opportunities = tracker.generate_automation_opportunities(days=30)
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"  {i}. {opp.task_pattern}")
        print(f"     Category: {opp.category.value}")
        print(f"     Frequency: {opp.frequency} times/month")
        print(f"     Total toil: {opp.total_toil_minutes} minutes")
        print(f"     Potential savings: {opp.estimated_savings_hours:.1f} hours/month")
        print(f"     Implementation effort: {opp.implementation_effort}")
        print(f"     Priority: {opp.priority}/100")
        print()

    # -----------------------------------------------------------------
    # Engineer breakdown
    # -----------------------------------------------------------------
    print("Engineer Breakdown:")
    print()

    breakdown = tracker.get_engineer_breakdown(days=30)
    for engineer, metrics in breakdown.items():
        print(f"  {engineer}:")
        print(f"    Total: {metrics.total_minutes} minutes")
        print(f"    Toil: {metrics.toil_percentage:.1f}%")
        print(f"    Engineering: {metrics.engineering_percentage:.1f}%")
        print()

    # -----------------------------------------------------------------
    # Generate comprehensive report
    # -----------------------------------------------------------------
    print("=" * 60)
    print("Comprehensive Toil Report")
    print("=" * 60)
    print()

    report = await tracker.generate_report(days=30)

    print(f"Period: {report.period_start.date()} to {report.period_end.date()}")
    print()

    print("Overall Metrics:")
    print(f"  Total time: {report.metrics.total_minutes} minutes")
    print(f"  Toil: {report.metrics.toil_minutes} minutes ({report.metrics.toil_percentage:.1f}%)")
    print(
        f"  Engineering: {report.metrics.engineering_minutes} minutes ({report.metrics.engineering_percentage:.1f}%)"
    )
    print(
        f"  Automated: {report.metrics.automated_minutes} minutes ({report.metrics.automation_coverage:.1f}%)"
    )
    print()

    print("Recommendations:")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {i}. {rec}")
    print()

    # -----------------------------------------------------------------
    # Export to JSON
    # -----------------------------------------------------------------
    print("Exporting to JSON...")

    tracker.export_to_json(days=30, filepath="data/toil_report.json")

    print("Exported to data/toil_report.json")
    print()

    # -----------------------------------------------------------------
    # Save entries to database
    # -----------------------------------------------------------------
    print("Saving entries to database...")
    await tracker.save_all_entries()
    print("Entries saved")
    print()

    print("=" * 60)
    print("Toil Tracker Demonstration Complete")
    print("=" * 60)
    print()
    print("Key Takeaways:")
    print("  1. Track all work (toil vs. engineering)")
    print("  2. Calculate toil percentage regularly")
    print("  3. Identify top toil sources")
    print("  4. Prioritize automation opportunities")
    print("  5. Monitor progress toward <50% toil goal")
    print()


if __name__ == "__main__":
    asyncio.run(main())
