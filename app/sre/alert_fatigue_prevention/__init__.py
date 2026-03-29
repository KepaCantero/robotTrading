"""
Alert Fatigue Prevention - Smart Alerting (SRE Rule 20.11)

Implements Google SRE alert fatigue prevention practices:
- Smart alert grouping
- Rate limiting and throttling
- Alert prioritization
- Noise reduction
- Learning from false positives

Usage:
    preventer = AlertFatiguePreventer(
        service_name="trading_engine",
        config=AlertFatigueConfig()
    )
    filtered_alerts = await preventer.process_alerts(raw_alerts)
"""

from .alert_fatigue_preventer import (
    AlertCategory,
    AlertFatigueConfig,
    AlertFatiguePreventer,
    AlertGroup,
    AlertSeverity,
    AlertStats,
    ProcessedAlert,
)
from .alert_grouper import AlertCluster, AlertGrouper, GroupingStrategy
from .alert_prioritizer import AlertPrioritizer, PriorityScore

__all__ = [
    "AlertCategory",
    "AlertCluster",
    "AlertFatigueConfig",
    "AlertFatiguePreventer",
    "AlertGroup",
    "AlertGrouper",
    "AlertPrioritizer",
    "AlertSeverity",
    "AlertStats",
    "GroupingStrategy",
    "PriorityScore",
    "ProcessedAlert",
]
