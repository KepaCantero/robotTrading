"""
Reconciliation Services

R16: Reconciliación Diaria - Daily position reconciliation between broker and internal system

This module provides services for detecting and reconciling discrepancies between
broker positions and internal database records.

Classes:
    DailyReconciler: Main reconciler for daily position comparison
    DiscrepancyDetector: Detector for specific types of discrepancies
    Position: Data class for position information
    ReconciliationResult: Result data class for reconciliation reports

Usage:
    from app.application.reconciliation import DailyReconciler, DiscrepancyDetector, Position

    reconciler = DailyReconciler()
    result = await reconciler.reconcile_positions(
        broker_positions=[...],
        internal_positions=[...]
    )
"""

from app.application.reconciliation.daily_reconciler import (
    DailyReconciler,
    Position,
    ReconciliationResult,
)
from app.services.reconciliation.discrepancy_detector import DiscrepancyDetector

__all__ = [
    "DailyReconciler",
    "DiscrepancyDetector",
    "Position",
    "ReconciliationResult",
]
