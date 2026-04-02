"""
Dashboard module for algo trading monitoring.

Provides data models and services for displaying real-time trading
performance, positions, and system status in a terminal-based dashboard.

NOTE: For canonical PerformanceMetrics, use app.backtesting.models.PerformanceMetrics
This module exports DashboardPerformanceMetrics (aliased as PerformanceMetrics for backward compatibility).
"""

from app.presentation.dashboard.dashboard_data import (
    DashboardPerformanceMetrics,
    DashboardSnapshot,
    PerformanceMetrics,
    PositionSummary,
    SystemStatus,
)
from app.presentation.dashboard.dashboard_service import DashboardService, get_dashboard_service

__all__ = [
    "DashboardPerformanceMetrics",
    "DashboardService",
    "DashboardSnapshot",
    "PerformanceMetrics",  # Backward compatibility alias
    "PositionSummary",
    "SystemStatus",
    "get_dashboard_service",
]
