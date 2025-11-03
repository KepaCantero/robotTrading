#!/usr/bin/env python3
"""
Entry point for running the AlgoTrading Dashboard.

Usage:
    python run_dashboard.py
    
Or directly:
    streamlit run app/dashboard/main.py

This script provides a clean entry point for the dashboard application.
"""

# ============================================================================
# SOLUCIÓN DEFINITIVA: Configurar variables de entorno ANTES de cualquier import
# Esto previene bloqueos de threading con mutex.cc
# Debe ir ANTES de importar numpy, pandas, torch, o cualquier otra librería
# ============================================================================
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCH_USE_CUDA_DSA'] = '0'

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import subprocess
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Ejecutar dashboard de backtesting')
    parser.add_argument(
        '--mode',
        choices=['objectives', 'advanced', 'main'],
        default='objectives',
        help='Modo del dashboard: objectives (simplificado, por defecto), advanced (completo), main (legacy)'
    )
    
    args = parser.parse_args()
    
    # Select dashboard based on mode
    if args.mode == 'advanced':
        dashboard_path = project_root / "app" / "dashboard" / "advanced_dashboard.py"
        print("🚀 Starting Advanced AlgoTrading Dashboard (modo completo)...")
    elif args.mode == 'main':
        dashboard_path = project_root / "app" / "dashboard" / "main.py"
        print("📊 Starting AlgoTrading Dashboard (legacy)...")
    else:  # objectives (default)
        dashboard_path = project_root / "app" / "dashboard" / "objectives_dashboard.py"
        print("🎯 Starting Backtesting Objectives Dashboard (modo simplificado)...")
        print("💡 Enfocado en validación de métricas y cumplimiento de límites")
    
    print(f"📂 Dashboard path: {dashboard_path}")
    print(f"🌐 Opening browser at http://localhost:8501\n")
    
    # Run Streamlit with the dashboard
    subprocess.run([
        "streamlit", "run", str(dashboard_path),
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false",
    ])

