#!/usr/bin/env python3
"""
AlgoTrading Main Entry Point

This script provides the main entry point for the AlgoTrading system.
It can launch either the API server or the Dashboard depending on arguments.

Usage:
    # Launch Dashboard (default)
    python app.py
    
    # Launch Dashboard explicitly
    python app.py dashboard
    
    # Launch API Server
    python app.py api
    
    # Launch both (requires two terminals or background processes)
    python app.py all
"""

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
    
    subprocess.run([
        "streamlit", "run", str(dashboard_path),
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false",
    ])

def launch_api():
    """Launch the FastAPI server."""
    import subprocess
    
    print("🚀 Starting AlgoTrading API Server...")
    print("🌐 API will be available at http://localhost:8000")
    print("📖 API docs at http://localhost:8000/docs\n")
    
    # Run uvicorn with the FastAPI app
    subprocess.run([
        "uvicorn", "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ])

def main():
    """Main entry point."""
    command = sys.argv[1] if len(sys.argv) > 1 else "dashboard"
    
    if command == "dashboard":
        launch_dashboard()
    elif command == "api":
        launch_api()
    elif command == "all":
        print("⚠️  Use two separate terminals:")
        print("   Terminal 1: python app.py dashboard")
        print("   Terminal 2: python app.py api")
        sys.exit(1)
    else:
        print(f"❌ Unknown command: {command}")
        print("\nUsage:")
        print("  python app.py          # Launch dashboard (default)")
        print("  python app.py dashboard")
        print("  python app.py api")
        sys.exit(1)

if __name__ == "__main__":
    main()

