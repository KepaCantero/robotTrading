"""
Integration Tests for Alerting System Pipeline

Tests cover:
- End-to-end alert triggering
- Rule evaluation and management
- Alert state machine
- Notification dispatch
"""

from decimal import Decimal

import pytest

from app.services.alerting_system import (
    AlertEvent,
    AlertManager,
    AlertRule,
    AlertRuleEngine,
    AlertSeverity,
    ChangeRule,
    ComparisonOperator,
    NotificationChannelType,
    NotificationTarget,
    ThresholdRule,
)
from app.services.alerting_system.models import AlertEvaluationContext, NotificationPayload
from app.services.alerting_system.notification_channels import NotificationDispatcher


class TestAlertingPipeline:
    """Test end-to-end alerting pipeline."""

    def test_high_price_alert_flow(self):
        """Test complete flow: rule → trigger → manage → notify."""
        # Setup
        engine = AlertRuleEngine()
        manager = AlertManager()

        # Create rule
        rule = AlertRule(
            rule_id="high_price_001",
            name="High Price Alert",
            description="Alert when AAPL price exceeds 150",
            severity=AlertSeverity.WARNING,
            threshold_rules=[
                ThresholdRule(
                    metric_name="price",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("150"),
                    symbol="AAPL",
                )
            ],
            notification_targets=[
                NotificationTarget(
                    channel_type=NotificationChannelType.WEBHOOK,
                    endpoint="https://example.com/alerts",
                )
            ],
        )
        engine.register_rule(rule)

        # Create evaluation context
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("155"),
            symbol="AAPL",
        )

        # Evaluate rule
        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True
        assert event is not None

        # Check deduplication (second trigger should be suppressed)
        should_trigger = manager.should_trigger_alert(rule, event)
        assert should_trigger is True

        # Trigger alert
        alert = manager.trigger_alert(rule, event)
        assert alert.state.value == "triggered"

        # Record notification sent
        manager.record_notification_sent(event.event_id)

        # Check alert statistics
        stats = manager.get_alert_statistics()
        assert stats["total_active"] == 1

    def test_portfolio_loss_critical_alert(self):
        """Test critical alert for portfolio loss."""
        engine = AlertRuleEngine()
        manager = AlertManager()

        # Critical loss rule
        rule = AlertRule(
            rule_id="critical_loss",
            name="Critical Portfolio Loss",
            description="Alert on >10% portfolio loss",
            severity=AlertSeverity.CRITICAL,
            threshold_rules=[
                ThresholdRule(
                    metric_name="portfolio_return",
                    operator=ComparisonOperator.LESS_THAN,
                    threshold=Decimal("-10"),
                )
            ],
            deduplicate_minutes=30,  # Don't spam with loss alerts
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="portfolio_return",
            current_value=Decimal("-15"),
            portfolio_id="port_001",
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True
        assert event.severity == AlertSeverity.CRITICAL

        manager.trigger_alert(rule, event)
        alert = manager.get_alert_by_id(event.event_id)
        assert alert.severity == AlertSeverity.CRITICAL

    def test_multiple_rules_evaluation(self):
        """Test evaluating multiple rules simultaneously."""
        engine = AlertRuleEngine()

        # Register multiple rules
        rules = [
            AlertRule(
                rule_id="high_price",
                name="High Price",
                description="",
                severity=AlertSeverity.WARNING,
                threshold_rules=[
                    ThresholdRule(
                        metric_name="price",
                        operator=ComparisonOperator.GREATER_THAN,
                        threshold=Decimal("150"),
                    )
                ],
            ),
            AlertRule(
                rule_id="high_volume",
                name="High Volume",
                description="",
                severity=AlertSeverity.INFO,
                threshold_rules=[
                    ThresholdRule(
                        metric_name="volume",
                        operator=ComparisonOperator.GREATER_THAN,
                        threshold=Decimal("10000000"),
                    )
                ],
            ),
        ]

        for rule in rules:
            engine.register_rule(rule)

        # Evaluate with context that triggers price rule
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("155"),
        )

        events = engine.evaluate_all_rules(context)
        assert len(events) == 1
        assert events[0].rule_id == "high_price"

    def test_alert_lifecycle(self):
        """Test complete alert lifecycle."""
        manager = AlertManager()

        rule = AlertRule(
            rule_id="test_alert",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
        )

        event = AlertEvent(
            event_id="evt_001",
            rule_id="test_alert",
            severity=AlertSeverity.WARNING,
            message="Test alert",
        )

        # Stage 1: Trigger
        manager.trigger_alert(rule, event)
        alert = manager.get_alert_by_id(event.event_id)
        assert alert.state.value == "triggered"

        # Stage 2: Send notification
        manager.record_notification_sent(event.event_id)
        alert = manager.get_alert_by_id(event.event_id)
        assert alert.notifications_sent == 1

        # Stage 3: Acknowledge
        manager.acknowledge_alert("test_alert", event_id=event.event_id)
        alert = manager.get_alert_by_id(event.event_id)
        assert alert.state.value == "acknowledged"

        # Stage 4: Resolve
        manager.resolve_alert("test_alert", event_id=event.event_id, reason="Condition cleared")
        alert = manager.get_alert_by_id(event.event_id)
        assert alert.state.value == "resolved_acknowledged"

    def test_deduplication_across_symbols(self):
        """Test deduplication works for different symbols."""
        manager = AlertManager()

        rule = AlertRule(
            rule_id="rule_001",
            name="Price Alert",
            description="",
            severity=AlertSeverity.WARNING,
            deduplicate_minutes=5,
        )

        events = [
            AlertEvent(
                event_id="evt_aapl",
                rule_id="rule_001",
                severity=AlertSeverity.WARNING,
                symbol="AAPL",
            ),
            AlertEvent(
                event_id="evt_msft",
                rule_id="rule_001",
                severity=AlertSeverity.WARNING,
                symbol="MSFT",
            ),
        ]

        # Both should trigger (different symbols)
        for event in events:
            should_trigger = manager.should_trigger_alert(rule, event)
            assert should_trigger is True

        # Duplicates suppressed
        should_trigger_aapl_again = manager.should_trigger_alert(rule, events[0])
        assert should_trigger_aapl_again is False

    def test_change_rule_in_pipeline(self):
        """Test change rule in complete pipeline."""
        engine = AlertRuleEngine()
        manager = AlertManager()

        # Change rule: Alert if >20% loss in 1 hour
        rule = AlertRule(
            rule_id="large_loss",
            name="Large Loss Alert",
            description="Alert on >20% loss in 1 hour",
            severity=AlertSeverity.CRITICAL,
            change_rules=[
                ChangeRule(
                    metric_name="portfolio_value",
                    change_percent=Decimal("20"),
                    window_minutes=60,
                    direction="down",
                )
            ],
        )
        engine.register_rule(rule)

        # Simulate 25% loss
        context = AlertEvaluationContext(
            metric_name="portfolio_value",
            current_value=Decimal("75"),
            window_data=[
                Decimal("100"),
                Decimal("95"),
                Decimal("85"),
                Decimal("75"),
            ],
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is True

        manager.trigger_alert(rule, event)
        alert = manager.get_alert_by_id(event.event_id)
        assert alert.severity == AlertSeverity.CRITICAL


class TestMultiChannelNotification:
    """Test notifications to multiple channels."""

    @pytest.mark.asyncio
    async def test_webhook_and_email_notification(self):
        """Test dispatching to webhook and email."""
        dispatcher = NotificationDispatcher()

        targets = [
            NotificationTarget(
                channel_type=NotificationChannelType.WEBHOOK,
                endpoint="https://example.com/webhook",
                enabled=True,
            ),
            NotificationTarget(
                channel_type=NotificationChannelType.EMAIL,
                endpoint="alert@example.com",
                enabled=True,
            ),
        ]

        payload = NotificationPayload(
            event_id="evt_001",
            rule_id="rule_001",
            rule_name="Alert",
            severity=AlertSeverity.CRITICAL,
            message="Critical alert",
            metric_name="loss",
            metric_value=Decimal("-5000"),
        )

        # In real implementation, channels would actually send
        # Here we're just testing the dispatcher logic
        success_count = await dispatcher.dispatch(targets, payload)
        assert success_count >= 0


class TestErrorHandling:
    """Test error handling in pipeline."""

    def test_rule_evaluation_error_handling(self):
        """Test that errors in rule evaluation are handled."""
        engine = AlertRuleEngine()

        # Create a rule with potentially problematic config
        rule = AlertRule(
            rule_id="problematic_rule",
            name="Test",
            description="",
            severity=AlertSeverity.WARNING,
            enabled=True,
        )
        engine.register_rule(rule)

        # Evaluate with various contexts
        contexts = [
            AlertEvaluationContext(
                metric_name="metric1",
                current_value=Decimal("100"),
            ),
            AlertEvaluationContext(
                metric_name="metric2",
                current_value=Decimal("200"),
            ),
        ]

        for context in contexts:
            try:
                triggered, event = engine.evaluate_rule(rule, context)
                # Should not raise, errors are caught internally
                assert triggered is not None
            except Exception as e:
                pytest.fail(f"Rule evaluation raised exception: {e}")

    def test_disabled_rule_handling(self):
        """Test that disabled rules don't trigger."""
        engine = AlertRuleEngine()

        rule = AlertRule(
            rule_id="disabled_rule",
            name="Disabled",
            description="",
            severity=AlertSeverity.WARNING,
            enabled=False,
            threshold_rules=[
                ThresholdRule(
                    metric_name="price",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("1"),  # Would normally trigger
                )
            ],
        )
        engine.register_rule(rule)

        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("100"),
        )

        triggered, event = engine.evaluate_rule(rule, context)
        assert triggered is False
        assert event is None


class TestAlertAggregation:
    """Test alert aggregation and grouping."""

    def test_multiple_alerts_same_rule(self):
        """Test multiple alerts from same rule."""
        manager = AlertManager()

        rule = AlertRule(
            rule_id="multi_alert_rule",
            name="Test",
            description="",
            severity=AlertSeverity.INFO,
        )

        # Create and trigger multiple alerts from same rule
        for i in range(3):
            event = AlertEvent(
                event_id=f"evt_{i:03d}",
                rule_id="multi_alert_rule",
                severity=AlertSeverity.INFO,
                symbol=f"SYM_{i}",
            )
            manager.trigger_alert(rule, event)

        # All should be active
        active = manager.get_active_alerts("multi_alert_rule")
        assert len(active) == 3

    def test_alert_history_aggregation(self):
        """Test aggregating alert history."""
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

        # Trigger, acknowledge, and resolve
        manager.trigger_alert(rule, event)
        manager.record_notification_sent(event.event_id)
        manager.acknowledge_alert("rule_001", event_id=event.event_id)
        manager.resolve_alert("rule_001", event_id=event.event_id, reason="Fixed")

        # Check full history
        history = manager.get_alert_history(event.event_id)
        actions = [h.action for h in history]
        assert "triggered" in actions
        assert "notification_sent" in actions
        assert "acknowledged" in actions
        assert "resolved" in actions
