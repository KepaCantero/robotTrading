#!/usr/bin/env python3
"""
Verify Toil Tracker Implementation.

Validates that the toil tracking system is properly implemented
following Google SRE principles.
"""

import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/Users/kepa.cantero/Projects/algoTrading')

from app.sre.automation import (
    ToilTracker,
    ToilCategory,
    AutomationPotential,
    ToilConfig,
)


def verify_toil_tracker():
    """Verify toil tracker implementation."""

    print("=" * 60)
    print("Toil Tracker Verification")
    print("=" * 60)
    print()

    checks = []
    tracker = None

    # Check 1: Module imports
    print("✓ Check 1: Module imports")
    checks.append(("Module imports", True))
    print()

    # Check 2: Create tracker
    print("✓ Check 2: Create tracker")
    try:
        import tempfile
        from pathlib import Path
        import time

        # Use unique service name and temp database for verification
        unique_id = f"verify_{int(time.time())}"
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test_toil.db"

        # IMPORTANT: Use absolute path for database
        config = ToilConfig(
            toil_warning_threshold=50.0,
            toil_critical_threshold=70.0,
            db_path=str(db_path.absolute()),
        )
        tracker = ToilTracker(unique_id, config)

        # Initialize tracker (creates DB)
        import asyncio
        asyncio.run(tracker.initialize())

        checks.append(("Create tracker", True))
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        checks.append(("Create tracker", False))
        print()

    # Check 3: Log work entries
    print("✓ Check 3: Log work entries")
    try:
        # Manual toil
        tracker.log_work(
            task="Manual deployment",
            category="deployment",
            duration=45,
            automated=False,
            assignable=True,
            automation_potential="high",
            engineer="alice",
        )

        # Automated work
        tracker.log_work(
            task="Automated deployment",
            category="deployment",
            duration=5,
            automated=True,
            engineer="system",
        )

        # Engineering work
        tracker.log_work(
            task="Feature development",
            category="other",
            duration=120,
            automated=False,
            assignable=False,
            engineer="bob",
        )

        checks.append(("Log work entries", True))
        print(f"  Logged 3 entries")
    except Exception as e:
        print(f"✗ Failed: {e}")
        checks.append(("Log work entries", False))
    print()

    # Check 4: Calculate toil percentage
    print("✓ Check 4: Calculate toil percentage")
    try:
        toil_pct = tracker.calculate_toil_percentage(days=30)
        expected = 45 / (45 + 5 + 120) * 100  # 26.5%

        if abs(toil_pct - expected) < 1:
            checks.append(("Calculate toil percentage", True))
            print(f"  Toil: {toil_pct:.1f}% (expected: {expected:.1f}%)")
        else:
            checks.append(("Calculate toil percentage", False))
            print(f"✗ Wrong: {toil_pct:.1f}% (expected: {expected:.1f}%)")
    except Exception as e:
        print(f"✗ Failed: {e}")
        checks.append(("Calculate toil percentage", False))
    print()

    # Check 5: Get top toil sources
    print("✓ Check 5: Get top toil sources")
    try:
        top_sources = tracker.get_top_toil_sources(days=30, limit=5)

        if len(top_sources) > 0:
            checks.append(("Get top toil sources", True))
            print(f"  Found {len(top_sources)} sources")
            for source, minutes in top_sources:
                print(f"    - {source}: {minutes} minutes")
        else:
            checks.append(("Get top toil sources", False))
            print("✗ No sources found")
    except Exception as e:
        print(f"✗ Failed: {e}")
        checks.append(("Get top toil sources", False))
    print()

    # Check 6: Generate automation opportunities
    print("✓ Check 6: Generate automation opportunities")
    try:
        opportunities = tracker.generate_automation_opportunities(days=30)

        if len(opportunities) > 0:
            checks.append(("Generate automation opportunities", True))
            print(f"  Found {len(opportunities)} opportunities")
            for opp in opportunities[:3]:
                print(f"    - {opp.task_pattern} (priority: {opp.priority})")
        else:
            checks.append(("Generate automation opportunities", False))
            print("✗ No opportunities found")
    except Exception as e:
        print(f"✗ Failed: {e}")
        checks.append(("Generate automation opportunities", False))
    print()

    # Check 7: Engineer breakdown
    print("✓ Check 7: Engineer breakdown")
    try:
        breakdown = tracker.get_engineer_breakdown(days=30)

        if len(breakdown) > 0:
            checks.append(("Engineer breakdown", True))
            print(f"  Found {len(breakdown)} engineers")
            for engineer, metrics in breakdown.items():
                print(f"    - {engineer}: {metrics.toil_percentage:.1f}% toil")
        else:
            checks.append(("Engineer breakdown", False))
            print("✗ No breakdown found")
    except Exception as e:
        print(f"✗ Failed: {e}")
        checks.append(("Engineer breakdown", False))
    print()

    # Check 8: Export to JSON
    print("✓ Check 8: Export to JSON")
    try:
        json_str = tracker.export_to_json(days=30)

        if '"service_name"' in json_str and '"metrics"' in json_str:
            checks.append(("Export to JSON", True))
            print("  JSON export successful")
        else:
            checks.append(("Export to JSON", False))
            print("✗ Invalid JSON format")
    except Exception as e:
        print(f"✗ Failed: {e}")
        checks.append(("Export to JSON", False))
    print()

    # Check 9: Thresholds
    print("✓ Check 9: Thresholds")
    try:
        # Add more toil to exceed threshold
        tracker.log_work(
            task="Incident response",
            category="incident_response",
            duration=300,  # 5 hours
            automated=False,
        )

        toil_pct = tracker.calculate_toil_percentage(days=30)

        if toil_pct > config.toil_warning_threshold:
            checks.append(("Threshold detection", True))
            print(f"  Threshold exceeded: {toil_pct:.1f}% > {config.toil_warning_threshold}%")
        else:
            checks.append(("Threshold detection", False))
            print(f"✗ Threshold not exceeded: {toil_pct:.1f}%")
    except Exception as e:
        print(f"✗ Failed: {e}")
        checks.append(("Threshold detection", False))
    print()

    # Summary
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print()

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    for check, result in checks:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {check}")

    print()
    print(f"Result: {passed}/{total} checks passed")
    print()

    if passed == total:
        print("✓ All checks passed! Toil tracker is working correctly.")
        return 0
    else:
        print(f"✗ {total - passed} check(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = verify_toil_tracker()
    sys.exit(exit_code)
