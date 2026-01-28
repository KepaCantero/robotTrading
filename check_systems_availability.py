#!/usr/bin/env python3
"""
Check which systems are missing from ComplianceEngine.

This script:
1. Imports the ComplianceEngine
2. Gets the system availability
3. Lists which systems are False (not available)
4. For each missing system, identifies the ImportError
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import traceback

# Import the ComplianceEngine
try:
    from app.core.compliance_engine import ComplianceEngine
    print("Successfully imported ComplianceEngine")
except ImportError as e:
    print(f"ERROR: Could not import ComplianceEngine: {e}")
    traceback.print_exc()
    sys.exit(1)

# Initialize engine
try:
    engine = ComplianceEngine()
    status = engine.get_system_status()
except Exception as e:
    print(f"ERROR: Could not initialize ComplianceEngine: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("SYSTEM AVAILABILITY CHECK")
print("=" * 80)

availability = status['availability']['systems']
missing = [name for name, available in availability.items() if not available]

print(f"\nAvailable: {status['availability']['available_systems']}/{status['availability']['total_systems']}")
print(f"Percentage: {status['availability']['availability_percentage']:.0f}%")

# Display all systems status
print("\n" + "-" * 80)
print("ALL SYSTEMS STATUS:")
print("-" * 80)
for system, available in sorted(availability.items()):
    status_icon = "✅" if available else "❌"
    print(f"  {status_icon} {system}")

if missing:
    print(f"\n" + "=" * 80)
    print(f"MISSING SYSTEMS ({len(missing)}):")
    print("=" * 80)

    # Define import checks for each system
    import_checks = {
        "backtesting_engine": (
            "from app.backtesting.engine import SimpleBacktester",
            lambda: __import__("app.backtesting.engine", fromlist=["SimpleBacktester"])
        ),
        "live_trading": (
            "from app.services.live_trading.broker_connector import BrokerConnector",
            lambda: __import__("app.services.live_trading.broker_connector", fromlist=["BrokerConnector"])
        ),
        "paper_trading": (
            "from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter",
            lambda: __import__("app.services.live_trading.broker_adapters.paper_adapter", fromlist=["PaperAdapter"])
        ),
        "strategies": (
            "from app.strategies.base import BaseStrategy",
            lambda: __import__("app.strategies.base", fromlist=["BaseStrategy"])
        ),
        "risk_engine": (
            "from app.engines.risk_engine import RiskEngine",
            lambda: __import__("app.engines.risk_engine", fromlist=["RiskEngine"])
        ),
        "portfolio_engine": (
            "from app.engines.portfolio_engine import PortfolioEngine",
            lambda: __import__("app.engines.portfolio_engine", fromlist=["PortfolioEngine"])
        ),
        "data_engine": (
            "from app.engines.data_engine import DataEngine",
            lambda: __import__("app.engines.data_engine", fromlist=["DataEngine"])
        ),
        "context_engine": (
            "from app.engines.context_engine import ContextEngine",
            lambda: __import__("app.engines.context_engine", fromlist=["ContextEngine"])
        ),
        "execution_engine": (
            "from app.engines.execution_engine import ExecutionEngine",
            lambda: __import__("app.engines.execution_engine", fromlist=["ExecutionEngine"])
        ),
        "ernest_chan": (
            "from app.services.regime_detection_chan import get_regime_detector",
            lambda: __import__("app.services.regime_detection_chan", fromlist=["get_regime_detector"])
        ),
        "narang": (
            "from app.services.portfolio_construction_narang import get_portfolio_constructor",
            lambda: __import__("app.services.portfolio_conaruction_narang", fromlist=["get_portfolio_constructor"])
        ),
        "lopez_de_prado": (
            "from app.backtesting.labeling.meta_labeling import get_meta_labeling",
            lambda: __import__("app.backtesting.labeling.meta_labeling", fromlist=["get_meta_labeling"])
        ),
        "tomasini": (
            "# Tomasini is architecture-based (always available)",
            lambda: True
        ),
        "hastie": (
            "from app.backtesting.validation.cross_validation import PurgedKFold",
            lambda: __import__("app.backtesting.validation.cross_validation", fromlist=["PurgedKFold"])
        ),
        "harris": (
            "from app.engines.execution_engine.microstructure.harris_integration import get_harris_integrator",
            lambda: __import__("app.engines.execution_engine.microstructure.harris_integration", fromlist=["get_harris_integrator"])
        ),
        "ohara": (
            "from app.microstructure.liquidity import get_liquidity_analyzer",
            lambda: __import__("app.microstructure.liquidity", fromlist=["get_liquidity_analyzer"])
        ),
        "percival": (
            "# Percival is architecture-based (always available)",
            lambda: True
        ),
        "hull": (
            "from app.engines.risk_engine.var_calculators.var_calculators import get_var_calculator",
            lambda: __import__("app.engines.risk_engine.var_calculators.var_calculators", fromlist=["get_var_calculator"])
        ),
        "google_sre": (
            "from app.sre.monitoring.golden_signals import get_golden_signals_monitor",
            lambda: __import__("app.sre.monitoring.golden_signals", fromlist=["get_golden_signals_monitor"])
        ),
        "beck_tdd": (
            "# Beck TDD is architecture-based (always available)",
            lambda: True
        ),
        "martin_arch": (
            "# Martin Clean Arch is architecture-based (always available)",
            lambda: True
        ),
    }

    for system in missing:
        print(f"\n❌ {system.upper()}")
        print("-" * 40)

        if system in import_checks:
            import_statement, check_func = import_checks[system]
            print(f"Import statement: {import_statement}")

            try:
                result = check_func()
                if result is True:
                    print(f"  ⚠️  Check passed but system marked as unavailable")
                else:
                    print(f"  ✓ Import successful: {type(result)}")
            except ImportError as e:
                print(f"  🔴 ImportError: {e}")
            except AttributeError as e:
                print(f"  🔴 AttributeError (module exists but function missing): {e}")
            except Exception as e:
                print(f"  🔴 Error ({type(e).__name__}): {e}")
                print(f"  Traceback:")
                tb_lines = traceback.format_exc().split('\n')
                for line in tb_lines[-5:]:
                    if line.strip():
                        print(f"    {line}")
        else:
            print(f"  ⚠️  No import check defined for {system}")

    # Summary of fixes needed
    print("\n" + "=" * 80)
    print("SUMMARY OF FIXES NEEDED:")
    print("=" * 80)

    # Categorize missing systems
    missing_files = []
    missing_functions = []
    architecture_based = []

    for system in missing:
        if system in ["tomasini", "percival", "beck_tdd", "martin_arch"]:
            architecture_based.append(system)
        else:
            # Check if file exists
            import_checks.get(system, ("", None))
            # This is a simplified check - in reality we'd check file paths

    if architecture_based:
        print(f"\n⚠️  Architecture-based systems (should always be available):")
        for s in architecture_based:
            print(f"  - {s}: Check why availability check returns False")

else:
    print("\n✅ ALL SYSTEMS AVAILABLE!")

print("=" * 80)
