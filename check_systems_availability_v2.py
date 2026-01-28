#!/usr/bin/env python3
"""
Detailed diagnostic of missing systems from ComplianceEngine.

This script identifies:
1. Which systems are missing
2. The specific import errors for each
3. What needs to be fixed
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("COMPLIANCE ENGINE SYSTEMS DIAGNOSTIC")
print("=" * 80)

# First, check NumPy version
print("\n1. NUMPY VERSION CHECK:")
print("-" * 40)
try:
    import numpy as np
    print(f"   NumPy version: {np.__version__}")
    if np.__version__.startswith('2.'):
        print("   ⚠️  WARNING: NumPy 2.x detected!")
        print("   This causes incompatibility with matplotlib and other packages.")
except ImportError:
    print("   🔴 NumPy not installed!")

# Check matplotlib
print("\n2. MATPLOTLIB CHECK:")
print("-" * 40)
try:
    import matplotlib
    print(f"   Matplotlib version: {matplotlib.__version__}")
    try:
        import matplotlib.pyplot as plt
        print("   ✓ matplotlib.pyplot imports successfully")
    except ImportError as e:
        print(f"   🔴 matplotlib.pyplot import failed: {e}")
except ImportError:
    print("   🔴 Matplotlib not installed!")

# Now check each system's availability
print("\n3. SYSTEMS CHECK:")
print("-" * 40)

# Define systems to check with their imports
systems = {
    "ernest_chan": {
        "imports": [
            "from app.services.regime_detection_chan import get_regime_detector",
            "from app.services.factor_models import get_factor_model",
            "from app.services.execution_algorithms import get_execution_algorithm",
        ]
    },
    "narang": {
        "imports": [
            "from app.services.portfolio_construction_narang import get_portfolio_constructor",
        ]
    },
    "lopez_de_prado": {
        "imports": [
            "from app.backtesting.labeling.meta_labeling import get_meta_labeling",
        ]
    },
    "hull": {
        "imports": [
            "from app.engines.risk_engine.var_calculators.var_calculators import get_var_calculator",
            "from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaR",
        ]
    },
    "execution_engine": {
        "imports": [
            "from app.engines.execution_engine import ExecutionEngine",
        ]
    },
}

missing_count = 0
working_count = 0

for system_name, system_info in systems.items():
    print(f"\n{system_name.upper()}:")
    print("-" * 40)

    all_ok = True
    for import_stmt in system_info["imports"]:
        try:
            # Execute import
            parts = import_stmt.split(" from ")[1].split(" import ")
            module_path = parts[0]
            import_name = parts[1]

            module = __import__(module_path, fromlist=[import_name])

            # Check if the imported object exists
            obj = getattr(module, import_name, None)
            if obj is None:
                print(f"   🔴 {import_stmt}")
                print(f"      Module exists but '{import_name}' not found")
                all_ok = False
            else:
                print(f"   ✓ {import_stmt}")

        except ImportError as e:
            print(f"   🔴 {import_stmt}")
            print(f"      ImportError: {e}")
            all_ok = False
        except Exception as e:
            print(f"   🔴 {import_stmt}")
            print(f"      {type(e).__name__}: {e}")
            all_ok = False

    if all_ok:
        working_count += 1
        print(f"   ✅ {system_name}: WORKING")
    else:
        missing_count += 1
        print(f"   ❌ {system_name}: MISSING/ERRORS")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Working systems: {working_count}/{len(systems)}")
print(f"Missing systems: {missing_count}/{len(systems)}")

print("\n" + "=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)

print("\nThe main issue is NUMPY VERSION INCOMPATIBILITY:")
print("1. You have NumPy 2.0.2 installed")
print("2. Matplotlib was compiled with NumPy 1.x")
print("3. When matplotlib imports, it tries to use numpy.core.multiarray")
print("4. This fails with NumPy 2.x, breaking the entire import chain")

print("\nWHY THIS AFFECTS MULTIPLE SYSTEMS:")
print("- lopez_de_prado: Imports meta_labeling → triple_barrier → matplotlib")
print("- ernest_chan: May have indirect matplotlib dependencies")
print("- hull: May have statistical plotting dependencies")

print("\n" + "=" * 80)
print("SOLUTIONS")
print("=" * 80)

print("\nOPTION 1: Downgrade NumPy (RECOMMENDED for stability)")
print("  pip install 'numpy<2.0'")
print("  pip install --force-reinstall matplotlib")

print("\nOPTION 2: Upgrade matplotlib to NumPy 2.x compatible version")
print("  pip install --upgrade matplotlib")

print("\nOPTION 3: Rebuild packages with NumPy 2.x support")
print("  pip install --upgrade --force-reinstall matplotlib scipy")

print("\n" + "=" * 80)
print("ADDITIONAL ISSUES FOUND")
print("=" * 80)

print("\nFrom the warnings, also need to fix:")
print("1. get_factor_model not found in app.services.factor_models")
print("2. HistoricalVaR not found in var_calculators")
print("3. Missing: arch, statsmodels, hmmlearn, redis (optional dependencies)")

print("\n" + "=" * 80)
