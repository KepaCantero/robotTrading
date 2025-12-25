"""
T18.2: Alert Manager - Alert lifecycle and state management

Manages:
- Alert state machine (triggered, resolved, acknowledged)
- Deduplication (prevent alert spam)
- Alert history persistence
- Notification dispatching
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from .models import (
    AlertEvent,
    AlertHistory,
    AlertRule,
    AlertState,
)

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Alert lifecycle manager.

    Features:
    - Alert state machine (TRIGGERED -> RESOLVED -> ACKNOWLEDGED)
    - De-duplication (suppresses duplicate alerts within time window)
    - Alert history tracking
    - Event aggregation
    """

    def __init__(self, dedup_minutes: int = 5):
        """
        Initialize alert manager.

        Args:
            dedup_minutes: Default deduplication window in minutes
        """
        self.dedup_minutes = dedup_minutes

        # Active alerts by rule_id
        self.active_alerts: Dict[str, AlertEvent] = {}

        # Alert history
        self.alert_history: List[AlertHistory] = []
        self._max_history = 50000

        # Deduplication tracking: (rule_id, symbol, portfolio_id) -> last_trigger_time
        self.last_triggered_times: Dict[str, datetime] = {}

    def should_trigger_alert(
        self, rule: AlertRule, event: AlertEvent
    ) -> bool:
        """
        Check if alert should be triggered based on deduplication.

        Args:
            rule: AlertRule that triggered
            event: AlertEvent details

        Returns:
            True if alert should be triggered, False if deduplicated
        """
        # Create deduplication key
        dedup_key = self._make_dedup_key(rule, event)

        # Check if we already triggered this alert recently
        last_trigger = self.last_triggered_times.get(dedup_key)
        if last_trigger:
            elapsed = datetime.utcnow() - last_trigger
            dedup_window = timedelta(minutes=rule.deduplicate_minutes)

            if elapsed < dedup_window:
                logger.debug(
                    f"Alert deduplicated: {rule.rule_id} "
                    f"(triggered {elapsed.total_seconds():.1f}s ago)"
                )
                return False

        # Record this trigger
        self.last_triggered_times[dedup_key] = datetime.utcnow()
        return True

    def trigger_alert(self, rule: AlertRule, event: AlertEvent) -> AlertEvent:
        """
        Trigger an alert and manage state.

        Args:
            rule: AlertRule that triggered
            event: AlertEvent with details

        Returns:
            The AlertEvent (may be same or merged with existing)
        """
        alert_key = self._make_alert_key(rule, event)

        # Check if this alert is already active
        existing = self.active_alerts.get(alert_key)
        if existing:
            logger.debug(f"Alert already active: {alert_key}")
            return existing

        # New alert
        self.active_alerts[alert_key] = event
        logger.warning(f"Alert triggered: {event.event_id} ({rule.name})")

        # Record in history
        self._record_history(
            event.event_id,
            event.rule_id,
            "triggered",
            {"severity": event.severity.value, "message": event.message},
        )

        return event

    def resolve_alert(
        self, rule_id: str, event_id: Optional[str] = None, reason: str = ""
    ) -> Optional[AlertEvent]:
        """
        Resolve an alert (move to RESOLVED state).

        Args:
            rule_id: ID of rule that triggered alert
            event_id: Optional specific event ID (if None, resolves all for rule)
            reason: Reason for resolution

        Returns:
            The resolved AlertEvent, or None if not found
        """
        # Find alert to resolve
        alert_key = None
        event = None

        if event_id:
            # Find by event ID
            for key, evt in self.active_alerts.items():
                if evt.event_id == event_id:
                    alert_key = key
                    event = evt
                    break
        else:
            # Find first active alert for this rule (can be TRIGGERED or ACKNOWLEDGED)
            for key, evt in self.active_alerts.items():
                if evt.rule_id == rule_id and evt.state in [
                    AlertState.TRIGGERED,
                    AlertState.ACKNOWLEDGED,
                ]:
                    alert_key = key
                    event = evt
                    break

        if not event:
            logger.warning(
                f"No active alert found to resolve: "
                f"rule_id={rule_id}, event_id={event_id}"
            )
            return None

        # Update state (transition to RESOLVED or RESOLVED_ACKNOWLEDGED if already acknowledged)
        if event.state == AlertState.ACKNOWLEDGED:
            event.state = AlertState.RESOLVED_ACKNOWLEDGED
        else:
            event.state = AlertState.RESOLVED
        event.resolved_at = datetime.utcnow()

        logger.info(f"Alert resolved: {event.event_id}")

        # Record in history
        self._record_history(
            event.event_id,
            event.rule_id,
            "resolved",
            {"reason": reason},
        )

        return event

    def acknowledge_alert(
        self,
        rule_id: str,
        event_id: Optional[str] = None,
        acknowledged_by: str = "system",
    ) -> Optional[AlertEvent]:
        """
        Acknowledge an alert.

        Args:
            rule_id: ID of rule that triggered alert
            event_id: Optional specific event ID
            acknowledged_by: User or system that acknowledged

        Returns:
            The acknowledged AlertEvent, or None if not found
        """
        # Find alert to acknowledge
        alert_key = None
        event = None

        if event_id:
            for key, evt in self.active_alerts.items():
                if evt.event_id == event_id:
                    alert_key = key
                    event = evt
                    break
        else:
            for key, evt in self.active_alerts.items():
                if evt.rule_id == rule_id and evt.state in [
                    AlertState.TRIGGERED,
                    AlertState.RESOLVED,
                ]:
                    alert_key = key
                    event = evt
                    break

        if not event:
            logger.warning(
                f"No active alert found to acknowledge: "
                f"rule_id={rule_id}, event_id={event_id}"
            )
            return None

        # Update state
        if event.state == AlertState.RESOLVED:
            event.state = AlertState.RESOLVED_ACKNOWLEDGED
        else:
            event.state = AlertState.ACKNOWLEDGED

        event.acknowledged_at = datetime.utcnow()

        logger.info(f"Alert acknowledged: {event.event_id} by {acknowledged_by}")

        # Record in history
        self._record_history(
            event.event_id,
            event.rule_id,
            "acknowledged",
            {"acknowledged_by": acknowledged_by},
        )

        return event

    def record_notification_sent(self, event_id: str) -> bool:
        """
        Record that notification was sent for an event.

        Args:
            event_id: ID of alert event

        Returns:
            True if recorded, False if event not found
        """
        for event in self.active_alerts.values():
            if event.event_id == event_id:
                event.notifications_sent += 1
                event.last_notification_at = datetime.utcnow()

                self._record_history(
                    event_id,
                    event.rule_id,
                    "notification_sent",
                    {"count": event.notifications_sent},
                )

                return True

        return False

    def get_active_alerts(
        self, rule_id: Optional[str] = None
    ) -> List[AlertEvent]:
        """
        Get list of active alerts.

        Args:
            rule_id: Optional filter by rule ID

        Returns:
            List of active AlertEvents
        """
        alerts = list(self.active_alerts.values())

        if rule_id:
            alerts = [a for a in alerts if a.rule_id == rule_id]

        return alerts

    def get_alert_by_id(self, event_id: str) -> Optional[AlertEvent]:
        """
        Get alert event by ID.

        Args:
            event_id: ID of alert event

        Returns:
            AlertEvent or None if not found
        """
        for event in self.active_alerts.values():
            if event.event_id == event_id:
                return event
        return None

    def get_recent_alerts(self, minutes: int = 60) -> List[AlertEvent]:
        """
        Get alerts triggered in last N minutes.

        Args:
            minutes: Number of minutes to look back

        Returns:
            List of recent AlertEvents
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            a
            for a in self.active_alerts.values()
            if a.triggered_at >= cutoff
        ]

    def get_alert_statistics(self) -> Dict:
        """
        Get statistics about alerts.

        Returns:
            Dictionary with alert statistics
        """
        stats = {
            "total_active": len(self.active_alerts),
            "by_state": {},
            "by_severity": {},
            "total_history": len(self.alert_history),
        }

        # Count by state
        for event in self.active_alerts.values():
            state = event.state.value
            stats["by_state"][state] = stats["by_state"].get(state, 0) + 1
            severity = event.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

        return stats

    def get_alert_history(
        self, event_id: Optional[str] = None, limit: int = 100
    ) -> List[AlertHistory]:
        """
        Get alert history.

        Args:
            event_id: Optional filter by event ID
            limit: Maximum number of entries to return

        Returns:
            List of AlertHistory entries
        """
        history = self.alert_history

        if event_id:
            history = [h for h in history if h.event_id == event_id]

        return history[-limit:]

    def clear_resolved_alerts(self, older_than_hours: int = 24) -> int:
        """
        Clear resolved and acknowledged alerts older than N hours.

        Args:
            older_than_hours: Remove alerts resolved before this time

        Returns:
            Number of alerts cleared
        """
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        keys_to_remove = []

        for key, event in self.active_alerts.items():
            if event.state in [AlertState.RESOLVED, AlertState.RESOLVED_ACKNOWLEDGED]:
                if event.resolved_at and event.resolved_at < cutoff:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.active_alerts[key]

        logger.info(f"Cleared {len(keys_to_remove)} resolved alerts")
        return len(keys_to_remove)

    def _make_dedup_key(self, rule: AlertRule, event: AlertEvent) -> str:
        """Create deduplication key."""
        return f"{rule.rule_id}:{event.symbol}:{event.portfolio_id}"

    def _make_alert_key(self, rule: AlertRule, event: AlertEvent) -> str:
        """Create unique key for alert."""
        return f"{rule.rule_id}:{event.symbol}:{event.portfolio_id}:{event.metric_name}"

    def _record_history(
        self, event_id: str, rule_id: str, action: str, details: Dict
    ) -> None:
        """Record alert history entry."""
        history = AlertHistory(
            history_id=f"hist_{uuid4().hex[:12]}",
            event_id=event_id,
            rule_id=rule_id,
            action=action,
            timestamp=datetime.utcnow(),
            details=details,
        )

        self.alert_history.append(history)

        # Keep history size bounded
        if len(self.alert_history) > self._max_history:
            self.alert_history = self.alert_history[-self._max_history :]
