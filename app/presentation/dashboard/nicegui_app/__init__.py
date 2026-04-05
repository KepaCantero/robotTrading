"""NiceGUI backtesting dashboard application.

Professional trading dashboard built with NiceGUI (FastAPI + Quasar + Socket.IO).
Dark mode by default, responsive layout, ECharts financial charts.
"""

from app.presentation.dashboard.nicegui_app.app import create_app

__all__ = ["create_app"]
