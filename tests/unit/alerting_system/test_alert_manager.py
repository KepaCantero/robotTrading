"""
Tests for Alert Manager - Alert lifecycle and state management

Tests cover:
- Alert state machine
- Deduplication logic
- Alert history
- Event aggregation
"""

from datetime import datetime, timedelta
from decimal import Decimal


from app.services.alerting_system import (
    AlertEvent,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertState,
)


class TestAlertDeduplication:
    """Test alert deduplication."""

    def test_duplicate_alert_suppressed(self):
        """Test that duplicate alert is suppressed."""
        manager = AlertManager(dedup_minutes=5)
        rule = AlertRule(
            rule_id="rule_001",
            name="High Price",
            description="",
            severity=AlertSeverity.WARNING,
        )

        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            metric_name="price",
            metric_value=Decimal("105"),
            symbol="AAPL",
        )

        # First alert should trigger
        should_trigger = manager.should_trigger_alert(rule, event)
        assert should_trigger is True

        # Immediate duplicate should be suppressed
        should_trigger = manager.should_trigger_alert(rule, event)
        assert should_trigger is False

    def test_deduplication_expires(self):
        """Test that deduplication window expires."""
        manager = AlertManager(dedup_minutes=1)
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.INFO,
            deduplicate_minutes=1,
        )

        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.INFO,
        )

        # First trigger
        assert manager.should_trigger_alert(rule, event) is True

        # Duplicate suppressed
        assert manager.should_trigger_alert(rule, event) is False

        # Simulate time passing
        key = manager._make_dedup_key(rule, event)
        manager.last_triggered_times[key] = datetime.utcnow() - timedelta(minutes=2)

        # Should trigger again after expiry
        assert manager.should_trigger_alert(rule, event) is True

    def test_different_symbols_not_deduplicated(self):
        """Test that different symbols have separate dedup."""
        manager = AlertManager(dedup_minutes=5)
        rule = AlertRule(
            rule_id="rule_001",
            name="Price Alert",
            description="",
            severity=AlertSeverity.WARNING,
        )

        event_aapl = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
        )

        event_msft = AlertEvent(
            event_id="evt_002",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="MSFT",
        )

        # Both should trigger (different symbols)
        assert manager.should_trigger_alert(rule, event_aapl) is True
        assert manager.should_trigger_alert(rule, event_msft) is True


class TestAlertStateMachine:
    """Test alert state transitions."""

    def test_trigger_alert(self):
        """Test triggering an alert."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test Alert",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            message="Test message",
        )

        result = manager.trigger_alert(rule, event)
        assert result.event_id == "evt_001"
        assert result.state == AlertState.TRIGGERED
        assert len(manager.active_alerts) == 1

    def test_resolve_alert(self):
        """Test resolving an alert."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        # Trigger first
        manager.trigger_alert(rule, event)
        assert len(manager.active_alerts) == 1

        # Resolve
        resolved = manager.resolve_alert("rule_001", reason="Condition cleared")
        assert resolved is not None
        assert resolved.state == AlertState.RESOLVED
        assert resolved.resolved_at is not None

    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        # Trigger alert
        manager.trigger_alert(rule, event)

        # Acknowledge
        acknowledged = manager.acknowledge_alert("rule_001", acknowledged_by="user@example.com")
        assert acknowledged is not None
        assert acknowledged.state == AlertState.ACKNOWLEDGED
        assert acknowledged.acknowledged_at is not None

    def test_state_transition_triggered_to_resolved(self):
        """Test state transition from triggered to resolved."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.CRITICAL,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.CRITICAL,
        )

        # Start: TRIGGERED
        manager.trigger_alert(rule, event)

        # Transition: RESOLVED
        resolved = manager.resolve_alert("rule_001")
        assert resolved.state == AlertState.RESOLVED

        # Acknowledge resolved alert
        final = manager.acknowledge_alert("rule_001")
        assert final.state == AlertState.RESOLVED_ACKNOWLEDGED


class TestActiveAlerts:
    """Test managing active alerts."""

    def test_get_active_alerts(self):
        """Test retrieving active alerts."""
        manager = AlertManager()

        # Create and trigger 3 alerts
        for i in range(3):
            rule = AlertRule(
                rule_id=f"rule_{i:03d}",
                name=f"Alert {i}",
                description="",
                severity=AlertSeverity.WARNING,
            )
            event = AlertEvent(
                event_id=f"evt_{i:03d}",
                rule_id=f"rule_{i:03d}",
                severity=AlertSeverity.WARNING,
            )
            manager.trigger_alert(rule, event)

        active = manager.get_active_alerts()
        assert len(active) == 3

    def test_get_active_alerts_by_rule(self):
        """Test filtering active alerts by rule ID."""
        manager = AlertManager()
        rule1 = AlertRule(
            rule_id="rule_001",
            name="Test 1",
            description="",
            severity=AlertSeverity.WARNING,
        )
        rule2 = AlertRule(
            rule_id="rule_002",
            name="Test 2",
            description="",
            severity=AlertSeverity.WARNING,
        )

        event1 = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )
        event2 = AlertEvent(
            event_id="evt_002",
            rule_id="rule_002",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule1, event1)
        manager.trigger_alert(rule2, event2)

        active_rule1 = manager.get_active_alerts("rule_001")
        assert len(active_rule1) == 1
        assert active_rule1[0].rule_id == "rule_001"

    def test_get_alert_by_id(self):
        """Test getting specific alert by ID."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            message="Test message",
        )

        manager.trigger_alert(rule, event)

        found = manager.get_alert_by_id("evt_001")
        assert found is not None
        assert found.message == "Test message"

    def test_get_nonexistent_alert(self):
        """Test getting non-existent alert."""
        manager = AlertManager()
        found = manager.get_alert_by_id("nonexistent")
        assert found is None


class TestAlertHistory:
    """Test alert history tracking."""

    def test_history_recorded_on_trigger(self):
        """Test history recorded when alert triggered."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule, event)

        history = manager.get_alert_history()
        assert len(history) > 0
        assert history[-1].action == "triggered"

    def test_history_recorded_on_resolve(self):
        """Test history recorded when alert resolved."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule, event)
        manager.resolve_alert("rule_001", reason="Cleared")

        history = manager.get_alert_history()
        assert any(h.action == "resolved" for h in history)

    def test_history_by_event_id(self):
        """Test filtering history by event ID."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule, event)

        history = manager.get_alert_history("evt_001")
        assert len(history) > 0
        assert all(h.event_id == "evt_001" for h in history)


class TestNotificationTracking:
    """Test notification sending tracking."""

    def test_record_notification_sent(self):
        """Test recording that notification was sent."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule, event)

        result = manager.record_notification_sent("evt_001")
        assert result is True

        # Check notification count incremented
        alert = manager.get_alert_by_id("evt_001")
        assert alert.notifications_sent == 1

    def test_record_notification_nonexistent(self):
        """Test recording notification for non-existent alert."""
        manager = AlertManager()
        result = manager.record_notification_sent("nonexistent")
        assert result is False


class TestRecentAlerts:
    """Test retrieving recent alerts."""

    def test_get_recent_alerts(self):
        """Test getting recently triggered alerts."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule, event)

        recent = manager.get_recent_alerts(minutes=60)
        assert len(recent) == 1

    def test_recent_alerts_respects_time_window(self):
        """Test that recent alerts time window is respected."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule, event)

        # Simulate old trigger
        alert = manager.get_alert_by_id("evt_001")
        alert.triggered_at = datetime.utcnow() - timedelta(hours=2)

        recent = manager.get_recent_alerts(minutes=60)
        assert len(recent) == 0


class TestClearResolvedAlerts:
    """Test clearing old resolved alerts."""

    def test_clear_old_resolved_alerts(self):
        """Test clearing resolved alerts older than threshold."""
        manager = AlertManager()
        rule = AlertRule(
            rule_id="rule_001",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        manager.trigger_alert(rule, event)
        manager.resolve_alert("rule_001")

        assert len(manager.active_alerts) == 1

        # Simulate resolution hours ago
        alert = manager.get_alert_by_id("evt_001")
        alert.resolved_at = datetime.utcnow() - timedelta(hours=2)

        cleared = manager.clear_resolved_alerts(older_than_hours=1)
        assert cleared == 1
        assert len(manager.active_alerts) == 0


class TestStatistics:
    """Test alert statistics."""

    def test_alert_statistics(self):
        """Test collecting alert statistics."""
        manager = AlertManager()

        # Create and trigger some alerts
        for i in range(3):
            rule = AlertRule(
                rule_id=f"rule_{i:03d}",
                name=f"Alert {i}",
                description="",
                severity=AlertSeverity.WARNING,
            )
            event = AlertEvent(
                event_id=f"evt_{i:03d}",
                rule_id=f"rule_{i:03d}",
                severity=AlertSeverity.WARNING,
            )
            manager.trigger_alert(rule, event)

        stats = manager.get_alert_statistics()
        assert stats["total_active"] == 3
        assert stats["by_state"]["triggered"] == 3
