#!/usr/bin/env python3
"""
Entry point for running the AlgoTrading Dashboard.

Usage:
    python run_dashboard.py
    
Or directly:
    streamlit run app/dashboard/main.py

This script provides a clean entry point for the dashboard application.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import subprocess
    
    dashboard_path = project_root / "app" / "dashboard" / "main.py"
    
    print("🚀 Starting AlgoTrading Dashboard...")
    print(f"📂 Dashboard path: {dashboard_path}")
    print(f"🌐 Opening browser at http://localhost:8501\n")
    
    # Run Streamlit with the dashboard
    subprocess.run([
        "streamlit", "run", str(dashboard_path),
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false",
    ])

