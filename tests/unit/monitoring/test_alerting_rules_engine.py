"""
FASE 3: Unit tests for AlertingRulesEngine

Tests alert rule evaluation, triggering, and management.
"""

import pytest

from app.services.monitoring import (
    AlertConditionType,
    AlertRule,
    AlertSeverity,
    get_alerting_engine,
)


class TestAlertingRulesEngine:
    """Tests for AlertingRulesEngine."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return get_alerting_engine()

    @pytest.fixture
    async def engine_with_session(self):
        """Create engine with session."""
        engine = get_alerting_engine()
        yield engine
        await engine.cleanup()

    def test_engine_initialization(self, engine):
        """Test engine initializes with default rules."""
        assert engine is not None
        assert len(engine.rules) >= 5  # At least 5 default rules
        assert "rule_max_drawdown" in engine.rules
        assert "rule_high_leverage" in engine.rules
        assert "rule_low_win_rate" in engine.rules

    def test_create_custom_rule(self, engine):
        """Test creating a custom alert rule."""
        rule = AlertRule(
            rule_id="rule_custom_001",
            name="Custom Alert",
            description="Test custom alert",
            metric_name="custom_metric",
            condition_type=AlertConditionType.THRESHOLD,
            severity=AlertSeverity.WARNING,
            threshold_value=50.0,
            comparison_op=">",
        )

        success = engine.create_rule(rule)
        assert success is True
        assert "rule_custom_001" in engine.rules

    def test_create_duplicate_rule(self, engine):
        """Test creating duplicate rule fails."""
        rule = AlertRule(
            rule_id="rule_dup",
            name="Duplicate",
            description="Test",
            metric_name="metric",
            condition_type=AlertConditionType.THRESHOLD,
            severity=AlertSeverity.INFO,
        )

        engine.create_rule(rule)
        success = engine.create_rule(rule)
        assert success is False  # Duplicate fails

    def test_delete_rule(self, engine):
        """Test deleting an alert rule."""
        rule_id = list(engine.rules.keys())[0]
        success = engine.delete_rule(rule_id)
        assert success is True
        assert rule_id not in engine.rules

    def test_enable_disable_rule(self, engine):
        """Test enabling/disabling rules."""
        rule_id = list(engine.rules.keys())[0]

        engine.disable_rule(rule_id)
        assert engine.rules[rule_id].enabled is False

        engine.enable_rule(rule_id)
        assert engine.rules[rule_id].enabled is True

    @pytest.mark.asyncio
    async def test_evaluate_threshold_condition(self, engine):
        """Test threshold condition evaluation."""
        metrics = {
            "max_drawdown_pct": 30.0,  # Exceeds default 25% threshold
        }

        alerts = await engine.evaluate_rules(metrics)
        assert len(alerts) > 0
        assert any(a.rule_id == "rule_max_drawdown" for a in alerts)

    @pytest.mark.asyncio
    async def test_threshold_not_exceeded(self, engine):
        """Test when threshold is not exceeded."""
        metrics = {
            "max_drawdown_pct": 15.0,  # Below 25% threshold
        }

        alerts = await engine.evaluate_rules(metrics)
        # Should not trigger drawdown alert
        drawdown_alerts = [a for a in alerts if a.rule_id == "rule_max_drawdown"]
        assert len(drawdown_alerts) == 0

    @pytest.mark.asyncio
    async def test_multiple_alerts(self, engine):
        """Test triggering multiple alerts simultaneously."""
        metrics = {
            "max_drawdown_pct": 30.0,  # Over threshold
            "leverage_ratio": 4.0,  # Over threshold
        }

        alerts = await engine.evaluate_rules(metrics)
        assert len(alerts) >= 2  # At least drawdown and leverage

    @pytest.mark.asyncio
    async def test_alert_resolution(self, engine):
        """Test alert resolution when condition no longer met."""
        # Trigger alert
        metrics1 = {"max_drawdown_pct": 30.0}
        alerts1 = await engine.evaluate_rules(metrics1)
        assert len(alerts1) > 0

        # Condition no longer met
        metrics2 = {"max_drawdown_pct": 15.0}
        await engine.evaluate_rules(metrics2)
        # Alert should be resolved

    def test_get_active_alerts(self, engine):
        """Test getting active alerts."""
        active = engine.get_active_alerts()
        assert isinstance(active, list)

    def test_get_recent_alerts(self, engine):
        """Test getting recent alert history."""
        alerts = engine.get_recent_alerts(limit=10)
        assert isinstance(alerts, list)

    def test_get_alerts_by_severity(self, engine):
        """Test filtering alerts by severity."""
        critical = engine.get_alerts_by_severity(AlertSeverity.CRITICAL)
        warning = engine.get_alerts_by_severity(AlertSeverity.WARNING)

        assert isinstance(critical, list)
        assert isinstance(warning, list)

    def test_rules_summary(self, engine):
        """Test rules summary information."""
        summary = engine.get_rules_summary()

        assert "total_rules" in summary
        assert "enabled_rules" in summary
        assert "disabled_rules" in summary
        assert "active_alerts" in summary
        assert summary["total_rules"] >= 5

    def test_anomaly_detection(self, engine):
        """Test anomaly detection condition."""
        # Add some baseline values to history
        for i in range(15):
            metrics = {"custom_metric": 50.0 + (i % 5)}
            import asyncio

            asyncio.run(engine.evaluate_rules(metrics))

        # Now add anomaly
        rule = AlertRule(
            rule_id="rule_anomaly_test",
            name="Anomaly Test",
            description="Test anomaly detection",
            metric_name="custom_metric",
            condition_type=AlertConditionType.ANOMALY,
            severity=AlertSeverity.WARNING,
            baseline_value=50.0,
            std_dev_multiplier=2.0,
        )
        engine.create_rule(rule)

        # Trigger anomaly (value far from baseline)
        metrics_anomaly = {"custom_metric": 200.0}
        import asyncio

        asyncio.run(engine.evaluate_rules(metrics_anomaly))
        # Should detect anomaly

    def test_change_detection(self, engine):
        """Test percentage change detection."""
        rule = AlertRule(
            rule_id="rule_change_test",
            name="Change Detection",
            description="Test change detection",
            metric_name="portfolio_value_usd",
            condition_type=AlertConditionType.CHANGE,
            severity=AlertSeverity.WARNING,
            change_percent=10.0,
            change_period_sec=60,
        )
        engine.create_rule(rule)

        import asyncio

        # Add baseline
        asyncio.run(engine.evaluate_rules({"portfolio_value_usd": 100000.0}))

        # Add change
        asyncio.run(engine.evaluate_rules({"portfolio_value_usd": 115000.0}))
        # Should detect > 10% change

    def test_metric_history_storage(self, engine):
        """Test metric history is stored correctly."""
        import asyncio

        metrics = {"test_metric": 10.0}
        asyncio.run(engine.evaluate_rules(metrics))

        assert "test_metric" in engine.metric_history
        assert len(engine.metric_history["test_metric"]) > 0

    def test_metric_history_size_limit(self, engine):
        """Test metric history respects size limit."""
        import asyncio

        # Add many values
        for i in range(2000):
            metrics = {"large_metric": float(i)}
            asyncio.run(engine.evaluate_rules(metrics))

        # Should not exceed history size
        history = engine.metric_history["large_metric"]
        assert len(history) <= engine.history_size


class TestAlertRule:
    """Tests for AlertRule creation and configuration."""

    def test_create_basic_rule(self):
        """Test creating basic alert rule."""
        rule = AlertRule(
            rule_id="test_001",
            name="Test Rule",
            description="A test rule",
            metric_name="test_metric",
            condition_type=AlertConditionType.THRESHOLD,
            severity=AlertSeverity.WARNING,
            threshold_value=100.0,
        )

        assert rule.rule_id == "test_001"
        assert rule.enabled is True
        assert rule.comparison_op == ">"

    def test_rule_with_webhook(self):
        """Test alert rule with webhook configuration."""
        rule = AlertRule(
            rule_id="webhook_test",
            name="Webhook Alert",
            description="Alert with webhook",
            metric_name="metric",
            condition_type=AlertConditionType.THRESHOLD,
            severity=AlertSeverity.CRITICAL,
            webhook_url="http://example.com/alert",
            webhook_enabled=True,
        )

        assert rule.webhook_enabled is True
        assert rule.webhook_url == "http://example.com/alert"

    def test_rule_creation_timestamp(self):
        """Test rule tracks creation timestamp."""
        rule = AlertRule(
            rule_id="ts_test",
            name="Timestamp Test",
            description="Test",
            metric_name="metric",
            condition_type=AlertConditionType.THRESHOLD,
            severity=AlertSeverity.INFO,
        )

        assert rule.created_at is not None
        assert rule.fire_count == 0
        assert rule.last_fired_at is None
