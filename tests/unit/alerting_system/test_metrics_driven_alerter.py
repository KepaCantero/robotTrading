"""
T18.2: Advanced Alerting System - Metrics-Driven Alerter Tests

Tests for the MetricsDrivenAlerter component that bridges metrics to alerts.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.alerting_system.alert_manager import AlertManager
from app.services.alerting_system.alert_rule_engine import AlertRuleEngine
from app.services.alerting_system.metrics_driven_alerter import (
    EvaluationStatistics,
    MetricQueryConfig,
    MetricsDrivenAlerter,
)
from app.services.alerting_system.models import (
    AlertRule,
    AlertSeverity,
    ComparisonOperator,
    ThresholdRule,
)


@pytest.fixture
def mock_alert_rule_engine():
    """Create mock alert rule engine."""
    return MagicMock(spec=AlertRuleEngine)


@pytest.fixture
def mock_alert_manager():
    """Create mock alert manager."""
    manager = MagicMock(spec=AlertManager)
    manager.trigger_alert = AsyncMock()
    return manager


@pytest.fixture
def alerter(mock_alert_rule_engine, mock_alert_manager):
    """Create MetricsDrivenAlerter instance."""
    return MetricsDrivenAlerter(mock_alert_rule_engine, mock_alert_manager)


class TestMetricsDrivenAlerterInitialization:
    """Test alerter initialization."""

    def test_alerter_creation(self, alerter):
        """Test alerter can be created."""
        assert alerter is not None
        assert len(alerter.registered_rules) == 0
        assert alerter.is_running is False

    def test_alerter_statistics_initialization(self, alerter):
        """Test statistics are initialized."""
        stats = alerter.evaluation_stats
        assert stats.rules_evaluated == 0
        assert stats.rules_triggered == 0
        assert stats.evaluation_errors == 0


class TestRuleRegistration:
    """Test rule registration."""

    def test_register_single_rule(self, alerter):
        """Test registering a single rule."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test",
            severity=AlertSeverity.WARNING,
            threshold_rules=[
                ThresholdRule(
                    metric_name="TEST_METRIC",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("10.0"),
                )
            ],
        )
        config = MetricQueryConfig("TEST_METRIC", lookback_minutes=5)

        alerter.register_metric_alert_rule(rule, config)

        assert "test_rule" in alerter.registered_rules
        assert alerter.get_rule_count() == 1

    def test_register_multiple_rules(self, alerter):
        """Test registering multiple rules."""
        rules = [
            AlertRule(
                rule_id=f"rule_{i}",
                name=f"Rule {i}",
                description="Test",
                severity=AlertSeverity.WARNING,
            )
            for i in range(3)
        ]
        config = MetricQueryConfig("TEST_METRIC")

        alerter.register_rules(rules, config)

        assert alerter.get_rule_count() == 3

    def test_get_registered_rules(self, alerter):
        """Test retrieving registered rules."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
        )
        config = MetricQueryConfig("TEST_METRIC")
        alerter.register_metric_alert_rule(rule, config)

        rules = alerter.get_registered_rules()
        assert "test_rule" in rules
        assert rules["test_rule"].name == "Test"


class TestThresholdEvaluation:
    """Test threshold rule evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_greater_than_threshold_true(self, alerter):
        """Test greater than threshold evaluation."""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            threshold_rules=[
                ThresholdRule(
                    metric_name="TEST",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("10.0"),
                )
            ],
        )

        result = await alerter._evaluate_threshold_rules(
            rule, Decimal("15.0"), {"current_value": Decimal("15.0")}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_greater_than_threshold_false(self, alerter):
        """Test greater than threshold when not exceeded."""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            threshold_rules=[
                ThresholdRule(
                    metric_name="TEST",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("10.0"),
                )
            ],
        )

        result = await alerter._evaluate_threshold_rules(
            rule, Decimal("5.0"), {"current_value": Decimal("5.0")}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_less_than_threshold(self, alerter):
        """Test less than threshold evaluation."""
        rule = AlertRule(
            rule_id="test",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            threshold_rules=[
                ThresholdRule(
                    metric_name="TEST",
                    operator=ComparisonOperator.LESS_THAN,
                    threshold=Decimal("10.0"),
                )
            ],
        )

        result = await alerter._evaluate_threshold_rules(
            rule, Decimal("5.0"), {"current_value": Decimal("5.0")}
        )
        assert result is True


class TestChangeRuleEvaluation:
    """Test change rule evaluation."""

    def test_evaluate_change_rule_decline(self, alerter):
        """Test percentage change rule for decline."""
        from app.services.alerting_system.models import ChangeRule

        change_rule = ChangeRule(
            metric_name="TEST",
            change_percent=Decimal("-20.0"),
            window_minutes=60,
            direction="down",
        )

        metric_data = {
            "current_value": Decimal("75.0"),  # More than 20% decline from 100
            "window_data": [Decimal("100.0"), Decimal("90.0"), Decimal("75.0")],
        }

        result = alerter._evaluate_change_rule(change_rule, metric_data)
        # 25% decline from 100 to 75, which exceeds -20% threshold
        assert result is True

    def test_evaluate_change_rule_no_data(self, alerter):
        """Test change rule with insufficient data."""
        from app.services.alerting_system.models import ChangeRule

        change_rule = ChangeRule(
            metric_name="TEST",
            change_percent=Decimal("-20.0"),
            window_minutes=60,
            direction="down",
        )

        metric_data = {"current_value": Decimal("80.0"), "window_data": []}

        result = alerter._evaluate_change_rule(change_rule, metric_data)
        assert result is False


class TestAlertCreation:
    """Test alert event creation."""

    @pytest.mark.asyncio
    async def test_create_and_trigger_alert(self, alerter, mock_alert_manager):
        """Test alert creation and triggering."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test alert",
            severity=AlertSeverity.WARNING,
        )
        config = MetricQueryConfig("TEST_METRIC")
        alerter.register_metric_alert_rule(rule, config)

        metric_data = {
            "current_value": Decimal("15.0"),
            "symbol": "EUR/USD",
            "portfolio_id": "port_001",
        }

        alert_event = await alerter._create_and_trigger_alert(rule, metric_data)

        assert alert_event.event_id
        assert alert_event.rule_id == "test_rule"
        assert alert_event.severity == AlertSeverity.WARNING
        assert alert_event.symbol == "EUR/USD"
        assert mock_alert_manager.trigger_alert.called


class TestEvaluationCycle:
    """Test complete evaluation cycle."""

    @pytest.mark.asyncio
    async def test_evaluate_metric_rules(self, alerter):
        """Test evaluating all metric rules."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            enabled=True,
            threshold_rules=[
                ThresholdRule(
                    metric_name="TEST",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=Decimal("10.0"),
                )
            ],
        )
        config = MetricQueryConfig("TEST_METRIC")
        alerter.register_metric_alert_rule(rule, config)

        metric_queries = {
            "test_rule": {
                "current_value": Decimal("15.0"),
                "symbol": "EUR/USD",
            }
        }

        results = await alerter.evaluate_metric_rules(metric_queries)

        assert results["total_rules"] == 1
        assert len(results["triggered_alerts"]) > 0

    @pytest.mark.asyncio
    async def test_evaluate_disabled_rule(self, alerter):
        """Test that disabled rules are not evaluated."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            enabled=False,
        )
        config = MetricQueryConfig("TEST_METRIC")
        alerter.register_metric_alert_rule(rule, config)

        metric_queries = {"test_rule": {"current_value": Decimal("15.0")}}

        results = await alerter.evaluate_metric_rules(metric_queries)

        assert results["total_rules"] == 1
        assert len(results["triggered_alerts"]) == 0


class TestStatistics:
    """Test evaluation statistics."""

    def test_statistics_initialization(self):
        """Test statistics initialization."""
        stats = EvaluationStatistics()
        assert stats.rules_evaluated == 0
        assert stats.rules_triggered == 0

    def test_add_evaluation(self):
        """Test adding evaluation result."""
        stats = EvaluationStatistics()
        stats.add_evaluation(triggered=True, duration_ms=100.0, error=False)

        assert stats.total_evaluations == 1
        assert stats.rules_triggered == 1

    def test_statistics_to_dict(self):
        """Test statistics serialization."""
        stats = EvaluationStatistics()
        stats.add_evaluation(triggered=True, duration_ms=50.0)

        stats_dict = stats.to_dict()
        assert "total_evaluations" in stats_dict
        assert "rules_triggered" in stats_dict
        assert "uptime_seconds" in stats_dict

    def test_reset_statistics(self, alerter):
        """Test resetting statistics."""
        alerter.evaluation_stats.add_evaluation(triggered=True, duration_ms=50.0)
        assert alerter.evaluation_stats.total_evaluations > 0

        alerter.reset_statistics()
        assert alerter.evaluation_stats.total_evaluations == 0


class TestContinuousEvaluation:
    """Test continuous evaluation loop."""

    @pytest.mark.asyncio
    async def test_is_evaluating_flag(self, alerter):
        """Test is_evaluating flag."""
        assert alerter.is_evaluating() is False

        # Start with mock function
        async def mock_query_fn(rules):
            return {}

        await alerter.start_continuous_evaluation(interval_seconds=1, metric_query_fn=mock_query_fn)
        assert alerter.is_evaluating() is True

        await alerter.stop_continuous_evaluation()
        assert alerter.is_evaluating() is False

    @pytest.mark.asyncio
    async def test_cannot_start_duplicate_evaluation(self, alerter):
        """Test that starting evaluation twice is handled."""

        async def mock_query_fn(rules):
            return {}

        await alerter.start_continuous_evaluation(interval_seconds=1, metric_query_fn=mock_query_fn)
        assert alerter.is_evaluating() is True

        # Try to start again - should log warning
        await alerter.start_continuous_evaluation(interval_seconds=1, metric_query_fn=mock_query_fn)
        assert alerter.is_evaluating() is True

        await alerter.stop_continuous_evaluation()


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_evaluation_with_missing_metric_data(self, alerter):
        """Test evaluation when metric data is missing."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            enabled=True,
        )
        config = MetricQueryConfig("TEST_METRIC")
        alerter.register_metric_alert_rule(rule, config)

        # Empty metric queries
        results = await alerter.evaluate_metric_rules({})

        assert results["total_rules"] == 1
        assert len(results["triggered_alerts"]) == 0

    @pytest.mark.asyncio
    async def test_evaluation_with_none_current_value(self, alerter):
        """Test evaluation with None current value."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
            enabled=True,
        )
        config = MetricQueryConfig("TEST_METRIC")
        alerter.register_metric_alert_rule(rule, config)

        metric_queries = {
            "test_rule": {
                "current_value": None,
            }
        }

        results = await alerter.evaluate_metric_rules(metric_queries)

        assert results["total_rules"] == 1
        assert len(results["triggered_alerts"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
