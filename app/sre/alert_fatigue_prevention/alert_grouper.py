"""
Alert Grouper - Groups similar alerts to reduce noise.

Part of Alert Fatigue Prevention (SRE Rule 20.11).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class GroupingStrategy(str, Enum):
    """Strategy for grouping alerts."""

    SIMILARITY = "similarity"
    TEMPORAL = "temporal"
    SERVICE = "service"
    SEVERITY = "severity"


@dataclass
class AlertCluster:
    """A cluster of related alerts."""

    cluster_id: str
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    representative_alert: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertGrouper:
    """
    Groups similar alerts to reduce alert fatigue.

    Uses configurable strategies to cluster related alerts.
    """

    def __init__(self, strategy: GroupingStrategy = GroupingStrategy.SIMILARITY):
        """Initialize the alert grouper."""
        self.strategy = strategy
        self._clusters: Dict[str, AlertCluster] = {}

    def group_alerts(self, alerts: List[Dict[str, Any]]) -> List[AlertCluster]:
        """Group alerts into clusters."""
        # Simple implementation - group by service
        clusters = []
        service_groups: Dict[str, List[Dict[str, Any]]] = {}

        for alert in alerts:
            service = alert.get("service", "unknown")
            if service not in service_groups:
                service_groups[service] = []
            service_groups[service].append(alert)

        for service, group_alerts in service_groups.items():
            cluster = AlertCluster(
                cluster_id=f"cluster_{service}",
                alerts=group_alerts,
                representative_alert=group_alerts[0] if group_alerts else None,
            )
            clusters.append(cluster)

        return clusters

    def add_to_cluster(self, alert: Dict[str, Any], cluster_id: str) -> None:
        """Add an alert to an existing cluster."""
        if cluster_id in self._clusters:
            self._clusters[cluster_id].alerts.append(alert)
            self._clusters[cluster_id].updated_at = datetime.utcnow()

    def get_cluster(self, cluster_id: str) -> Optional[AlertCluster]:
        """Get a cluster by ID."""
        return self._clusters.get(cluster_id)
