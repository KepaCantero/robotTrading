"""
Dashboard module for algo trading monitoring.

Provides data models and services for displaying real-time trading
performance, positions, and system status in a terminal-based dashboard.
"""

from app.dashboard.dashboard_data import (
    DashboardSnapshot,
    PositionSummary,
    PerformanceMetrics,
    SystemStatus,
)
from app.dashboard.dashboard_service import DashboardService, get_dashboard_service

__all__ = [
    "DashboardSnapshot",
    "PositionSummary",
    "PerformanceMetrics",
    "SystemStatus",
    "DashboardService",
    "get_dashboard_service",
]
