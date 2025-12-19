"""
Advanced Dashboard Entry Point
Redirige al dashboard avanzado
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.dashboard.advanced_dashboard import main

if __name__ == "__main__":
    main()
