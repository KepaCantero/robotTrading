#!/usr/bin/env python3
"""
AlgoTrading Launcher Script

This script provides a convenience entry point for the AlgoTrading system.
It can launch either the API server or the Dashboard depending on arguments.

Usage:
    # Launch Dashboard (default)
    python scripts/launcher.py

    # Launch Dashboard explicitly
    python scripts/launcher.py dashboard

    # Launch API Server
    python scripts/launcher.py api

    # Launch both (requires two terminals or background processes)
    python scripts/launcher.py all

Alternative:
    # Direct API launch (recommended for production)
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

    # Direct Dashboard launch
    streamlit run app/dashboard/main.py
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


def launch_dashboard():
    """Launch the Streamlit dashboard."""
    import subprocess

    print("🚀 Starting AlgoTrading Dashboard...")
    print("🌐 Dashboard will open at http://localhost:8501")
    print("⚠️  Make sure Streamlit is installed: pip install streamlit\n")

    dashboard_path = project_root / "app" / "dashboard" / "main.py"

    subprocess.run(
        [
            "streamlit",
            "run",
            str(dashboard_path),
            "--server.headless",
            "false",
            "--browser.gatherUsageStats",
            "false",
        ]
    )


def launch_api():
    """Launch the FastAPI server."""
    import subprocess

    print("🚀 Starting AlgoTrading API Server...")
    print("🌐 API will be available at http://localhost:8000")
    print("📖 API docs at http://localhost:8000/docs\n")

    # Run uvicorn with the FastAPI app
    subprocess.run(
        [
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ]
    )


def main():
    """Main entry point."""
    command = sys.argv[1] if len(sys.argv) > 1 else "dashboard"

    if command == "dashboard":
        launch_dashboard()
    elif command == "api":
        launch_api()
    elif command == "all":
        print("⚠️  Use two separate terminals:")
        print("   Terminal 1: python scripts/launcher.py dashboard")
        print("   Terminal 2: python scripts/launcher.py api")
        sys.exit(1)
    else:
        print(f"❌ Unknown command: {command}")
        print("\nUsage:")
        print("  python scripts/launcher.py          # Launch dashboard (default)")
        print("  python scripts/launcher.py dashboard")
        print("  python scripts/launcher.py api")
        sys.exit(1)


if __name__ == "__main__":
    main()
