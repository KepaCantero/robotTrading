import sys
from pathlib import Path

from app.dashboard.advanced_dashboard import main

"""
Advanced Dashboard Entry Point
Redirige al dashboard avanzado
"""


project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


if __name__ == "__main__":
    main()
