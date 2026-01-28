#!/usr/bin/env python3
"""
Quick verification script for Error Budgets System.

This script verifies the implementation without running the full system.
"""

import sys
from pathlib import Path

def verify_files_exist():
    """Verify all required files exist."""
    print("Verifying files exist...")

    required_files = [
        "app/sre/error_budgets/__init__.py",
        "app/sre/error_budgets/error_budget_manager.py",
        "app/sre/error_budgets/slo_tracker.py",
        "app/sre/error_budgets/budget_alerts.py",
        "app/sre/error_budgets/development_gates.py",
        "app/sre/error_budgets/integration.py",
        "app/sre/error_budgets/README.md",
        "tests/sre/error_budgets/__init__.py",
        "tests/sre/error_budgets/test_error_budget_manager.py",
        "tests/sre/error_budgets/test_development_gates.py",
        "examples/error_budget_example.py",
    ]

    all_exist = True
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} MISSING")
            all_exist = False

    return all_exist


def verify_imports():
    """Verify all modules can be imported."""
    print("\nVerifying imports...")

    try:
        from app.sre.error_budgets import (
            ErrorBudgetManager,
            get_error_budget_manager,
            SLOTracker,
            BudgetAlertManager,
            DevelopmentGate,
            ErrorBudgetIntegration,
            get_error_budget_integration,
        )
        print("  ✓ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def verify_classes():
    """Verify all required classes exist."""
    print("\nVerifying classes...")

    try:
        from app.sre.error_budgets.error_budget_manager import (
            ErrorBudgetManager,
            ErrorBudgetConfig,
            ErrorBudgetState,
            BudgetPeriod,
            BudgetStatus,
            BudgetAllowance,
            TimeWindow,
        )

        from app.sre.error_budgets.slo_tracker import (
            SLOTracker,
            SLOConfig,
            SLIMetric,
            SLOComplianceReport,
            SLOViolation,
        )

        from app.sre.error_budgets.budget_alerts import (
            BudgetAlertManager,
            BudgetAlertConfig,
            AlertSeverity,
            AlertChannel,
        )

        from app.sre.error_budgets.development_gates import (
            DevelopmentGate,
            GateStatus,
            GateType,
            DeploymentBlocker,
        )

        print("  ✓ All required classes available")
        return True
    except ImportError as e:
        print(f"  ✗ Class verification failed: {e}")
        return False


def verify_api_router():
    """Verify API router can be created."""
    print("\nVerifying API router...")

    try:
        from app.sre.error_budgets.integration import create_error_budget_router

        router = create_error_budget_router()
        print(f"  ✓ API router created with {len(router.routes)} routes")
        return True
    except Exception as e:
        print(f"  ✗ API router creation failed: {e}")
        return False


def verify_configuration():
    """Verify configuration defaults."""
    print("\nVerifying configuration...")

    try:
        from decimal import Decimal
        from app.sre.error_budgets.error_budget_manager import (
            ErrorBudgetConfig,
            BudgetPeriod,
        )

        config = ErrorBudgetConfig()

        assert config.target_slo == Decimal("0.995"), "Default SLO should be 99.5%"
        assert config.period == BudgetPeriod.MONTHLY, "Default period should be monthly"
        assert config.warning_threshold_pct == Decimal("50"), "Warning threshold should be 50%"
        assert config.critical_threshold_pct == Decimal("25"), "Critical threshold should be 25%"
        assert config.exhausted_threshold_pct == Decimal("10"), "Exhausted threshold should be 10%"

        print("  ✓ Configuration defaults correct")
        return True
    except AssertionError as e:
        print(f"  ✗ Configuration verification failed: {e}")
        return False


def verify_budget_calculation():
    """Verify error budget calculations."""
    print("\nVerifying budget calculations...")

    try:
        from decimal import Decimal
        from app.sre.error_budgets.error_budget_manager import (
            BudgetAllowance,
            BudgetPeriod,
        )

        # Test monthly budget calculation
        allowance = BudgetAllowance.from_slo(
            total_minutes=43200,  # 30 days
            slo_percentage=Decimal("0.995"),
            period=BudgetPeriod.MONTHLY,
        )

        assert allowance.allowed_downtime_minutes == 216, "Should allow 216 minutes downtime"
        assert allowance.allowed_downtime_seconds == 12960, "Should allow 12960 seconds downtime"

        print("  ✓ Budget calculations correct")
        print(f"    - Monthly budget for 99.5% SLO: {allowance.allowed_downtime_minutes} minutes")
        print(f"    - That's {allowance.allowed_downtime_minutes / 60:.1f} hours per month")
        return True
    except AssertionError as e:
        print(f"  ✗ Budget calculation verification failed: {e}")
        return False


def print_summary(results):
    """Print verification summary."""
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(results.values())

    for test, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test}")

    print("\n" + "-" * 70)
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All verification checks passed!")
        print("✓ Error Budgets System is ready for use (SRE Rule 20 Compliance)")
        return 0
    else:
        print(f"\n✗ {total - passed} verification check(s) failed")
        return 1


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("ERROR BUDGETS SYSTEM VERIFICATION")
    print("SRE Rule 20 Compliance Check")
    print("=" * 70)
    print()

    results = {
        "Files Exist": verify_files_exist(),
        "Imports": verify_imports(),
        "Classes": verify_classes(),
        "API Router": verify_api_router(),
        "Configuration": verify_configuration(),
        "Budget Calculation": verify_budget_calculation(),
    }

    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
