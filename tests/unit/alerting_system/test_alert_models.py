"""
Tests for Alert Models - Data models for alerting system

Tests cover:
- Model initialization and validation
- Threshold rule evaluation
- Change rule evaluation
- State transitions
"""

from datetime import datetime
from decimal import Decimal

from app.services.alerting_system import (
    AlertEvent,
    AlertHistory,
    AlertRule,
    AlertSeverity,
    AlertState,
    ChangeRule,
    ComparisonOperator,
    NotificationChannelType,
    NotificationTarget,
    ThresholdRule,
)
from app.services.alerting_system.models import AlertEvaluationContext


class TestThresholdRule:
    """Test ThresholdRule model."""

    def test_greater_than_evaluation(self):
        """Test greater than comparison."""
        rule = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
        )

        assert rule.evaluate(Decimal("101")) is True
        assert rule.evaluate(Decimal("100")) is False
        assert rule.evaluate(Decimal("99")) is False

    def test_less_than_evaluation(self):
        """Test less than comparison."""
        rule = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.LESS_THAN,
            threshold=Decimal("100"),
        )

        assert rule.evaluate(Decimal("99")) is True
        assert rule.evaluate(Decimal("100")) is False
        assert rule.evaluate(Decimal("101")) is False

    def test_equal_evaluation(self):
        """Test equality comparison."""
        rule = ThresholdRule(
            metric_name="count",
            operator=ComparisonOperator.EQUAL,
            threshold=Decimal("5"),
        )

        assert rule.evaluate(Decimal("5")) is True
        assert rule.evaluate(Decimal("4")) is False
        assert rule.evaluate(Decimal("6")) is False

    def test_threshold_rule_with_symbol_filter(self):
        """Test threshold rule with symbol filter."""
        rule = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
            symbol="AAPL",
        )

        assert rule.symbol == "AAPL"
        assert rule.evaluate(Decimal("101")) is True

    def test_threshold_rule_to_dict(self):
        """Test threshold rule to_dict method."""
        rule = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
            symbol="AAPL",
        )

        d = rule.to_dict()
        assert d["metric_name"] == "price"
        assert d["operator"] == ">"
        assert d["threshold"] == "100"
        assert d["symbol"] == "AAPL"


class TestChangeRule:
    """Test ChangeRule model."""

    def test_change_rule_initialization(self):
        """Test change rule initialization."""
        rule = ChangeRule(
            metric_name="portfolio_value",
            change_percent=Decimal("5"),
            window_minutes=60,
        )

        assert rule.metric_name == "portfolio_value"
        assert rule.change_percent == Decimal("5")
        assert rule.window_minutes == 60

    def test_change_rule_with_direction(self):
        """Test change rule with direction."""
        rule = ChangeRule(
            metric_name="price",
            change_percent=Decimal("10"),
            window_minutes=30,
            direction="down",
        )

        assert rule.direction == "down"

    def test_change_rule_to_dict(self):
        """Test change rule to_dict method."""
        rule = ChangeRule(
            metric_name="price",
            change_percent=Decimal("5.5"),
            window_minutes=60,
            symbol="MSFT",
        )

        d = rule.to_dict()
        assert d["metric_name"] == "price"
        assert d["change_percent"] == "5.5"
        assert d["window_minutes"] == 60
        assert d["symbol"] == "MSFT"


class TestNotificationTarget:
    """Test NotificationTarget model."""

    def test_webhook_target(self):
        """Test webhook notification target."""
        target = NotificationTarget(
            channel_type=NotificationChannelType.WEBHOOK,
            endpoint="https://example.com/webhook",
            enabled=True,
        )

        assert target.channel_type == NotificationChannelType.WEBHOOK
        assert target.endpoint == "https://example.com/webhook"
        assert target.enabled is True

    def test_slack_target(self):
        """Test Slack notification target."""
        target = NotificationTarget(
            channel_type=NotificationChannelType.SLACK,
            endpoint="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        )

        assert target.channel_type == NotificationChannelType.SLACK

    def test_target_with_custom_headers(self):
        """Test notification target with custom headers."""
        headers = {"Authorization": "Bearer token123"}
        target = NotificationTarget(
            channel_type=NotificationChannelType.WEBHOOK,
            endpoint="https://example.com/webhook",
            headers=headers,
        )

        assert target.headers["Authorization"] == "Bearer token123"

    def test_notification_target_to_dict(self):
        """Test notification target to_dict method."""
        target = NotificationTarget(
            channel_type=NotificationChannelType.WEBHOOK,
            endpoint="https://example.com/webhook",
            enabled=True,
            retry_count=3,
        )

        d = target.to_dict()
        assert d["channel_type"] == "webhook"
        assert d["endpoint"] == "https://example.com/webhook"
        assert d["enabled"] is True
        assert d["retry_count"] == 3


class TestAlertRule:
    """Test AlertRule model."""

    def test_alert_rule_initialization(self):
        """Test alert rule initialization."""
        rule = AlertRule(
            rule_id="rule_001",
            name="High Price Alert",
            description="Alert when price exceeds threshold",
            severity=AlertSeverity.WARNING,
        )

        assert rule.rule_id == "rule_001"
        assert rule.name == "High Price Alert"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True

    def test_alert_rule_with_threshold_rules(self):
        """Test alert rule with threshold rules."""
        threshold = ThresholdRule(
            metric_name="price",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=Decimal("100"),
        )

        rule = AlertRule(
            rule_id="rule_001",
            name="High Price",
            description="Alert on high price",
            severity=AlertSeverity.WARNING,
            threshold_rules=[threshold],
        )

        assert len(rule.threshold_rules) == 1
        assert rule.threshold_rules[0] == threshold

    def test_alert_rule_with_notification_targets(self):
        """Test alert rule with notification targets."""
        target = NotificationTarget(
            channel_type=NotificationChannelType.WEBHOOK,
            endpoint="https://example.com/webhook",
        )

        rule = AlertRule(
            rule_id="rule_001",
            name="Alert",
            description="Test alert",
            severity=AlertSeverity.CRITICAL,
            notification_targets=[target],
        )

        assert len(rule.notification_targets) == 1
        assert rule.notification_targets[0] == target

    def test_alert_rule_to_dict(self):
        """Test alert rule to_dict method."""
        rule = AlertRule(
            rule_id="rule_001",
            name="Test Alert",
            description="Test description",
            severity=AlertSeverity.WARNING,
            enabled=True,
            deduplicate_minutes=10,
        )

        d = rule.to_dict()
        assert d["rule_id"] == "rule_001"
        assert d["name"] == "Test Alert"
        assert d["severity"] == "warning"
        assert d["enabled"] is True


class TestAlertEvent:
    """Test AlertEvent model."""

    def test_alert_event_initialization(self):
        """Test alert event initialization."""
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.CRITICAL,
            metric_name="portfolio_loss",
            metric_value=Decimal("-5000"),
        )

        assert event.event_id == "evt_001"
        assert event.rule_id == "rule_001"
        assert event.severity == AlertSeverity.CRITICAL
        assert event.state == AlertState.TRIGGERED

    def test_alert_event_state_transition(self):
        """Test alert event state transitions."""
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        assert event.state == AlertState.TRIGGERED

        # Resolve
        event.state = AlertState.RESOLVED
        event.resolved_at = datetime.utcnow()
        assert event.state == AlertState.RESOLVED

        # Acknowledge
        event.state = AlertState.RESOLVED_ACKNOWLEDGED
        event.acknowledged_at = datetime.utcnow()
        assert event.state == AlertState.RESOLVED_ACKNOWLEDGED

    def test_alert_event_to_dict(self):
        """Test alert event to_dict method."""
        event = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            message="Price threshold exceeded",
            metric_name="price",
            metric_value=Decimal("105.50"),
        )

        d = event.to_dict()
        assert d["event_id"] == "evt_001"
        assert d["rule_id"] == "rule_001"
        assert d["severity"] == "warning"
        assert d["message"] == "Price threshold exceeded"


class TestAlertHistory:
    """Test AlertHistory model."""

    def test_alert_history_initialization(self):
        """Test alert history initialization."""
        history = AlertHistory(
            history_id="hist_001",
            event_id="evt_001",
            rule_id="rule_001",
            action="triggered",
        )

        assert history.history_id == "hist_001"
        assert history.event_id == "evt_001"
        assert history.action == "triggered"

    def test_alert_history_to_dict(self):
        """Test alert history to_dict method."""
        history = AlertHistory(
            history_id="hist_001",
            event_id="evt_001",
            rule_id="rule_001",
            action="resolved",
            details={"reason": "Threshold no longer exceeded"},
        )

        d = history.to_dict()
        assert d["history_id"] == "hist_001"
        assert d["action"] == "resolved"
        assert d["details"]["reason"] == "Threshold no longer exceeded"


class TestAlertEvaluationContext:
    """Test AlertEvaluationContext model."""

    def test_context_initialization(self):
        """Test context initialization."""
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("105"),
            symbol="AAPL",
        )

        assert context.metric_name == "price"
        assert context.current_value == Decimal("105")
        assert context.symbol == "AAPL"

    def test_calculate_change_percent(self):
        """Test percentage change calculation."""
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("110"),
            window_data=[Decimal("100"), Decimal("105"), Decimal("110")],
        )

        change = context.calculate_change_percent()
        assert change == Decimal("10")  # 10% increase

    def test_calculate_change_percent_negative(self):
        """Test negative percentage change."""
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("80"),
            window_data=[Decimal("100"), Decimal("90"), Decimal("80")],
        )

        change = context.calculate_change_percent()
        assert change == Decimal("-20")  # -20% decrease

    def test_calculate_change_percent_zero_starting(self):
        """Test change calculation with zero starting value."""
        context = AlertEvaluationContext(
            metric_name="price",
            current_value=Decimal("10"),
            window_data=[Decimal("0"), Decimal("5"), Decimal("10")],
        )

        change = context.calculate_change_percent()
        assert change is None  # Can't divide by zero


class TestAlertSeverity:
    """Test AlertSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertState:
    """Test AlertState enum."""

    def test_state_values(self):
        """Test state enum values."""
        assert AlertState.TRIGGERED.value == "triggered"
        assert AlertState.RESOLVED.value == "resolved"
        assert AlertState.ACKNOWLEDGED.value == "acknowledged"
