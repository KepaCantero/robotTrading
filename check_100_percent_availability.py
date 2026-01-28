#!/usr/bin/env python3
"""
System Availability Diagnostic Script

This script checks the availability status of all 21 systems in the Compliance Engine.
It provides a detailed breakdown of which systems are available and which are missing.

Expected: 21/21 systems (100%)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.compliance_engine import ComplianceEngine


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)


def print_section(text: str):
    """Print a formatted section."""
    print(f"\n{text}")
    print("-" * len(text))


def main():
    """Main diagnostic function."""
    print_header("SYSTEM AVAILABILITY STATUS")

    # Initialize the compliance engine
    engine = ComplianceEngine(enable_logging=False)

    # Get system status
    status = engine.get_system_status()
    availability = status["availability"]

    total_systems = availability["total_systems"]
    available_systems = availability["available_systems"]
    availability_percentage = availability["availability_percentage"]
    systems = availability["systems"]

    print(f"\nTotal Systems: {total_systems}")
    print(f"Available: {available_systems}/{total_systems} ({availability_percentage:.1f}%)")

    # Separate available and missing systems
    missing_systems = []
    available_systems_list = []

    for system_name, is_available in systems.items():
        if is_available:
            available_systems_list.append(system_name)
        else:
            missing_systems.append(system_name)

    # Print missing systems with details
    if missing_systems:
        print_section("MISSING SYSTEMS:")
        for system_name in sorted(missing_systems):
            reason = get_error_reason(system_name)
            print(f"  ❌ {system_name}: {reason}")

    # Print available systems
    if available_systems_list:
        print_section("AVAILABLE SYSTEMS:")
        for system_name in sorted(available_systems_list):
            print(f"  ✅ {system_name}")

    # Print summary and recommendations
    print_section("SUMMARY:")
    print(f"  Current: {available_systems}/{total_systems} systems available")
    print(f"  Target: {total_systems}/{total_systems} systems (100%)")
    print(f"  Gap: {len(missing_systems)} systems need to be fixed")

    if missing_systems:
        print_section("RECOMMENDED FIXES:")
        for system_name in sorted(missing_systems):
            fix = get_fix_recommendation(system_name)
            print(f"  • {system_name}:")
            print(f"    {fix}")
    else:
        print("\n  🎉 ALL SYSTEMS OPERATIONAL! 100% AVAILABILITY ACHIEVED!")

    print("\n" + "=" * 80)

    # Return exit code based on availability
    return 0 if len(missing_systems) == 0 else 1


def get_error_reason(system_name: str) -> str:
    """Get the specific error reason for a missing system."""
    error_reasons = {
        "backtesting_engine": "Cannot import SimpleBacktester",
        "live_trading": "Cannot import BrokerConnector",
        "paper_trading": "Cannot import PaperAdapter",
        "strategies": "Cannot import BaseStrategy",
        "risk_engine": "Cannot import RiskEngine",
        "portfolio_engine": "Cannot import PortfolioEngine",
        "data_engine": "Cannot import DataEngine",
        "context_engine": "Cannot import ContextEngine",
        "execution_engine": "Cannot import MarketMicrostructureEngine",
        "ernest_chan": "Cannot import regime detection or execution algorithms",
        "narang": "Cannot import portfolio construction or alpha models",
        "lopez_de_prado": "Cannot import meta-labeling",
        "tomasini": "Architecture pattern compliance",
        "hastie": "Cannot import PurgedKFold cross-validation",
        "harris": "Cannot import Harris integrator",
        "ohara": "Cannot import liquidity or order flow analyzers",
        "percival": "Architecture pattern compliance",
        "hull": "Cannot import VaR calculators",
        "google_sre": "Cannot import golden signals monitor",
        "beck_tdd": "TDD pattern compliance",
        "martin_arch": "Clean architecture compliance",
    }
    return error_reasons.get(system_name, "Unknown error")


def get_fix_recommendation(system_name: str) -> str:
    """Get specific fix recommendation for a missing system."""
    fixes = {
        "backtesting_engine": "Create app/backtesting/engine.py with SimpleBacktester class",
        "live_trading": "Create app/services/live_trading/broker_connector.py",
        "paper_trading": "Create app/services/live_trading/broker_adapters/paper_adapter.py",
        "strategies": "Create app/strategies/base.py with BaseStrategy class",
        "risk_engine": "Create app/engines/risk_engine/__init__.py with RiskEngine class",
        "portfolio_engine": "Create app/engines/portfolio_engine/__init__.py with PortfolioEngine class",
        "data_engine": "Create app/engines/data_engine/__init__.py with DataEngine class",
        "context_engine": "Create app/engines/context_engine/__init__.py with ContextEngine class",
        "execution_engine": "Create app/engines/execution_engine/microstructure/__init__.py with get_market_microstructure_engine function",
        "ernest_chan": "Implement app/services/regime_detection_chan.py and app/services/execution_algorithms.py",
        "narang": "Implement app/services/portfolio_construction_narang.py and app/strategies/alpha_models.py",
        "lopez_de_prado": "Implement app/backtesting/labeling/meta_labeling.py with get_meta_labeling function",
        "tomasini": "Ensure architecture patterns are documented (always available)",
        "hastie": "Implement app/backtesting/validation/cross_validation.py with PurgedKFold class",
        "harris": "Implement app/engines/execution_engine/microstructure/harris_integration.py with get_harris_integrator function",
        "ohara": "Implement app/microstructure/liquidity.py and app/microstructure/order_flow.py",
        "percival": "Ensure architecture patterns are documented (always available)",
        "hull": "Implement app/engines/risk_engine/var_calculators/var_calculators.py with calculate_var function",
        "google_sre": "Implement app/sre/monitoring/golden_signals.py with get_golden_signals_monitor function",
        "beck_tdd": "Ensure TDD patterns are followed (always available)",
        "martin_arch": "Ensure clean architecture is followed (always available)",
    }
    return fixes.get(system_name, "Investigate import errors for this system")


if __name__ == "__main__":
    sys.exit(main())
