#!/usr/bin/env python3
"""
Script de diagnóstico para verificar que todos los imports del dashboard funcionan.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 Verificando imports del dashboard...\n")

errors = []
warnings = []

# Test basic imports
print("1. Testing basic Python imports...")
try:
    import streamlit as st
    print("   ✅ streamlit")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    errors.append(f"streamlit: {e}")
    print(f"   ❌ streamlit: {e}")

try:
    import pandas as pd
    print("   ✅ pandas")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    errors.append(f"pandas: {e}")
    print(f"   ❌ pandas: {e}")

try:
    import plotly.express as px
    import plotly.graph_objects as go
    print("   ✅ plotly")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    errors.append(f"plotly: {e}")
    print(f"   ❌ plotly: {e}")

# Test app imports
print("\n2. Testing app module imports...")
try:
    from app.dashboard.comprehensive_data_loader import ComprehensiveBacktestLoader
    print("   ✅ ComprehensiveBacktestLoader")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    errors.append(f"ComprehensiveBacktestLoader: {e}")
    print(f"   ❌ ComprehensiveBacktestLoader: {e}")

try:
    from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
    print("   ✅ ComprehensiveBacktestRunner")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    errors.append(f"ComprehensiveBacktestRunner: {e}")
    print(f"   ❌ ComprehensiveBacktestRunner: {e}")

try:
    from app.core.logging_config import setup_file_logging
    print("   ✅ setup_file_logging")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    warnings.append(f"setup_file_logging: {e}")
    print(f"   ⚠️ setup_file_logging: {e}")

try:
    from app.backtesting.successful_configs import SuccessfulConfigManager
    print("   ✅ SuccessfulConfigManager")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    warnings.append(f"SuccessfulConfigManager: {e}")
    print(f"   ⚠️ SuccessfulConfigManager: {e}")

# Test loading the dashboard module
print("\n3. Testing dashboard module import...")
try:
    import app.dashboard.advanced_dashboard
    print("   ✅ advanced_dashboard module loaded")
except (ValueError, TypeError, KeyError, AttributeError) as e:
    errors.append(f"advanced_dashboard: {e}")
    print(f"   ❌ advanced_dashboard: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "="*60)
if errors:
    print(f"❌ {len(errors)} error(es) encontrado(s):")
    for err in errors:
        print(f"   - {err}")
    print("\n⚠️ El dashboard NO funcionará correctamente.")
    sys.exit(1)
else:
    print("✅ Todos los imports críticos funcionan correctamente.")
    if warnings:
        print(f"\n⚠️ {len(warnings)} advertencia(s) (no críticas):")
        for warn in warnings:
            print(f"   - {warn}")
    print("\n🎉 El dashboard debería funcionar correctamente.")
    sys.exit(0)

