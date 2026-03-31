"""
T18.2: Advanced Alerting System - Alerting Orchestrator Tests

Tests for the main orchestrator that manages the alerting system lifecycle
and coordinates all alerting components.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.alerting.alerting_orchestrator import AlertingHealth, AlertingOrchestrator
from app.services.alerting_system.metrics_driven_alerter import MetricQueryConfig
from app.services.alerting_system.models import (
    AlertEvent,
    AlertRule,
    AlertSeverity,
    AlertState,
    ComparisonOperator,
    ThresholdRule,
)
from app.services.alerting_system.rule_templates import AlertRuleTemplates


@pytest.fixture
def orchestrator():
    """Create AlertingOrchestrator instance."""
    return AlertingOrchestrator()


@pytest.fixture
def sample_rule():
    """Create sample alert rule."""
    return AlertRule(
        rule_id="test_rule",
        name="Test Rule",
        description="Test alert rule",
        severity=AlertSeverity.WARNING,
        threshold_rules=[
            ThresholdRule(
                metric_name="TEST_METRIC",
                operator=ComparisonOperator.GREATER_THAN,
                threshold=Decimal("10.0"),
            )
        ],
    )


@pytest.fixture
def metric_config():
    """Create metric query config."""
    return MetricQueryConfig("TEST_METRIC", lookback_minutes=5)


class TestOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_orchestrator_creation(self, orchestrator):
        """Test orchestrator can be created."""
        assert orchestrator is not None
        assert orchestrator.is_running is False
        assert len(orchestrator.registered_rules) == 0

    def test_components_initialized(self, orchestrator):
        """Test all components are initialized."""
        assert orchestrator.alert_rule_engine is not None
        assert orchestrator.alert_manager is not None
        assert orchestrator.notification_dispatcher is not None

    def test_statistics_initialization(self, orchestrator):
        """Test statistics are initialized."""
        stats = orchestrator.statistics
        assert stats.total_rules == 0
        assert stats.enabled_rules == 0
        assert stats.total_evaluations == 0
        assert stats.total_alerts_triggered == 0

    @pytest.mark.asyncio
    async def test_initialize_with_no_metrics_engine(self, orchestrator):
        """Test initialization without metrics engine."""
        await orchestrator.initialize(metrics_query_engine=None, auto_register_templates=False)
        assert orchestrator.metrics_alerter is None

    @pytest.mark.asyncio
    async def test_initialize_with_auto_register_templates(self, orchestrator):
        """Test initialization with auto-registration of templates."""
        await orchestrator.initialize(
            metrics_query_engine=MagicMock(),
            auto_register_templates=True,
        )
        # Should have registered 12 templates
        assert len(orchestrator.registered_rules) == 12


class TestDefaultRuleRegistration:
    """Test registration of default rule templates."""

    @pytest.mark.asyncio
    async def test_register_default_rules(self, orchestrator):
        """Test registering all default rule templates."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.register_metric_alert_rule = MagicMock()

        await orchestrator.register_default_rules()

        assert len(orchestrator.registered_rules) == 12
        assert orchestrator.statistics.total_rules == 12
        assert "portfolio_drawdown_warning" in orchestrator.registered_rules

    @pytest.mark.asyncio
    async def test_register_default_rules_counts_enabled(self, orchestrator):
        """Test that enabled rule count is tracked."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.register_metric_alert_rule = MagicMock()

        await orchestrator.register_default_rules()

        # All default templates should be enabled
        enabled = sum(1 for r in orchestrator.registered_rules.values() if r.enabled)
        assert enabled == orchestrator.statistics.enabled_rules

    @pytest.mark.asyncio
    async def test_register_default_rules_without_alerter(self, orchestrator):
        """Test registering rules without metrics alerter."""
        orchestrator.metrics_alerter = None

        await orchestrator.register_default_rules()

        # Should still register rules locally
        assert len(orchestrator.registered_rules) == 12


class TestCustomRuleRegistration:
    """Test custom rule registration."""

    @pytest.mark.asyncio
    async def test_register_custom_rule(self, orchestrator, sample_rule, metric_config):
        """Test registering a custom rule."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.register_metric_alert_rule = AsyncMock()

        await orchestrator.register_custom_rule(sample_rule, metric_config)

        assert "test_rule" in orchestrator.registered_rules
        assert orchestrator.registered_rules["test_rule"] == sample_rule
        assert orchestrator.statistics.total_rules == 1

    @pytest.mark.asyncio
    async def test_register_multiple_custom_rules(self, orchestrator, metric_config):
        """Test registering multiple custom rules."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.register_metric_alert_rule = AsyncMock()

        for i in range(3):
            rule = AlertRule(
                rule_id=f"custom_rule_{i}",
                name=f"Custom Rule {i}",
                description="Test",
                severity=AlertSeverity.WARNING,
            )
            await orchestrator.register_custom_rule(rule, metric_config)

        assert orchestrator.statistics.total_rules == 3


class TestRuleEnableDisable:
    """Test enabling and disabling rules."""

    @pytest.mark.asyncio
    async def test_disable_rule(self, orchestrator, sample_rule):
        """Test disabling a rule."""
        orchestrator.registered_rules["test_rule"] = sample_rule
        orchestrator.statistics.total_rules = 1
        orchestrator.statistics.enabled_rules = 1

        await orchestrator.disable_rule("test_rule")

        assert orchestrator.registered_rules["test_rule"].enabled is False
        assert orchestrator.statistics.enabled_rules == 0

    @pytest.mark.asyncio
    async def test_enable_rule(self, orchestrator, sample_rule):
        """Test enabling a disabled rule."""
        sample_rule.enabled = False
        orchestrator.registered_rules["test_rule"] = sample_rule
        orchestrator.statistics.total_rules = 1

        await orchestrator.enable_rule("test_rule")

        assert orchestrator.registered_rules["test_rule"].enabled is True
        assert orchestrator.statistics.enabled_rules == 1

    @pytest.mark.asyncio
    async def test_disable_nonexistent_rule(self, orchestrator):
        """Test disabling a rule that doesn't exist."""
        await orchestrator.disable_rule("nonexistent")
        # Should not raise error


class TestOrchestrationLifecycle:
    """Test orchestrator start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_orchestrator(self, orchestrator):
        """Test starting the orchestrator."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.start_continuous_evaluation = AsyncMock()

        await orchestrator.start(evaluation_interval_seconds=60)

        assert orchestrator.is_running is True
        orchestrator.metrics_alerter.start_continuous_evaluation.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_without_alerter(self, orchestrator):
        """Test starting without metrics alerter."""
        orchestrator.metrics_alerter = None

        await orchestrator.start()

        assert orchestrator.is_running is False

    @pytest.mark.asyncio
    async def test_cannot_start_twice(self, orchestrator):
        """Test that starting twice is handled."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.start_continuous_evaluation = AsyncMock()

        await orchestrator.start()
        assert orchestrator.is_running is True

        # Try to start again
        await orchestrator.start()

        # Should still be running
        assert orchestrator.is_running is True

    @pytest.mark.asyncio
    async def test_stop_orchestrator(self, orchestrator):
        """Test stopping the orchestrator."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.stop_continuous_evaluation = AsyncMock()
        orchestrator.is_running = True

        await orchestrator.stop()

        assert orchestrator.is_running is False
        orchestrator.metrics_alerter.stop_continuous_evaluation.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, orchestrator):
        """Test stopping when not running."""
        orchestrator.is_running = False

        await orchestrator.stop()

        assert orchestrator.is_running is False


class TestHealthAndStatistics:
    """Test health checks and statistics."""

    def test_get_health_status(self, orchestrator):
        """Test getting health status."""
        orchestrator.registered_rules["test_rule"] = AlertRule(
            rule_id="test_rule",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
        )
        orchestrator.is_running = True

        health = orchestrator.get_health_status()

        assert isinstance(health, AlertingHealth)
        assert health.is_running is True
        assert health.rules_registered == 1
        assert "alert_rule_engine" in health.components_status

    def test_get_health_status_with_errors(self, orchestrator):
        """Test health status reflects errors."""
        orchestrator.alert_manager = MagicMock()
        orchestrator.alert_manager.get_alert_statistics = MagicMock(
            side_effect=Exception("Test error")
        )

        health = orchestrator.get_health_status()

        assert health.is_running is False
        assert health.evaluation_errors >= 1

    def test_get_statistics(self, orchestrator):
        """Test getting aggregated statistics."""
        orchestrator.registered_rules["test_rule"] = AlertRule(
            rule_id="test_rule",
            name="Test",
            description="Test",
            severity=AlertSeverity.WARNING,
        )
        orchestrator.alert_manager = MagicMock()
        orchestrator.alert_manager.get_alert_statistics = MagicMock(
            return_value={
                "total_triggered": 5,
                "total_resolved": 3,
                "total_acknowledged": 2,
                "history_size": 10,
            }
        )

        stats = orchestrator.get_statistics()

        assert stats["total_rules"] == 1
        assert stats["total_alerts_triggered"] == 5
        assert stats["total_alerts_resolved"] == 3

    @pytest.mark.asyncio
    async def test_reset_statistics(self, orchestrator):
        """Test resetting statistics."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.reset_statistics = AsyncMock()
        orchestrator.alert_manager = MagicMock()
        orchestrator.alert_manager.clear_resolved_alerts = MagicMock(return_value=0)

        await orchestrator.reset_statistics()

        orchestrator.metrics_alerter.reset_statistics.assert_called_once()
        orchestrator.alert_manager.clear_resolved_alerts.assert_called_once()


class TestRuleRetrieval:
    """Test retrieving registered rules."""

    def test_get_registered_rules(self, orchestrator, sample_rule):
        """Test retrieving all registered rules."""
        orchestrator.registered_rules["test_rule"] = sample_rule

        rules = orchestrator.get_registered_rules()

        assert "test_rule" in rules
        assert rules["test_rule"] == sample_rule

    def test_get_rule_by_id(self, orchestrator, sample_rule):
        """Test retrieving a specific rule by ID."""
        orchestrator.registered_rules["test_rule"] = sample_rule

        rule = orchestrator.get_rule_by_id("test_rule")

        assert rule == sample_rule

    def test_get_rule_by_id_not_found(self, orchestrator):
        """Test retrieving a rule that doesn't exist."""
        rule = orchestrator.get_rule_by_id("nonexistent")

        assert rule is None

    def test_get_rules_by_severity(self, orchestrator):
        """Test retrieving rules by severity."""
        warning_rule = AlertRule(
            rule_id="warning_rule",
            name="Warning",
            description="Test",
            severity=AlertSeverity.WARNING,
        )
        critical_rule = AlertRule(
            rule_id="critical_rule",
            name="Critical",
            description="Test",
            severity=AlertSeverity.CRITICAL,
        )

        orchestrator.registered_rules["warning_rule"] = warning_rule
        orchestrator.registered_rules["critical_rule"] = critical_rule

        critical_rules = orchestrator.get_rules_by_severity(AlertSeverity.CRITICAL)

        assert len(critical_rules) == 1
        assert critical_rules[0].rule_id == "critical_rule"

    def test_get_rules_by_category(self, orchestrator):
        """Test retrieving rules by category tag."""
        risk_rule = AlertRule(
            rule_id="risk_rule",
            name="Risk",
            description="Test",
            severity=AlertSeverity.WARNING,
            tags={"category": "portfolio_risk"},
        )
        system_rule = AlertRule(
            rule_id="system_rule",
            name="System",
            description="Test",
            severity=AlertSeverity.WARNING,
            tags={"category": "system_health"},
        )

        orchestrator.registered_rules["risk_rule"] = risk_rule
        orchestrator.registered_rules["system_rule"] = system_rule

        risk_rules = orchestrator.get_rules_by_category("portfolio_risk")

        assert len(risk_rules) == 1
        assert risk_rules[0].rule_id == "risk_rule"


class TestManualAlertTriggering:
    """Test manual alert triggering."""

    @pytest.mark.asyncio
    async def test_trigger_alert_manual(self, orchestrator, sample_rule):
        """Test triggering an alert manually."""
        orchestrator.registered_rules["test_rule"] = sample_rule
        orchestrator.alert_manager = MagicMock()
        orchestrator.alert_manager.trigger_alert = AsyncMock()

        alert_event = AlertEvent(
            event_id="alert_001",
            rule_id="test_rule",
            severity=AlertSeverity.WARNING,
            state=AlertState.TRIGGERED,
            metric_name="TEST_METRIC",
            metric_value=Decimal("15.0"),
            message="Test alert",
        )

        await orchestrator.trigger_alert_manual(alert_event)

        orchestrator.alert_manager.trigger_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, orchestrator):
        """Test acknowledging an alert."""
        orchestrator.alert_manager = MagicMock()
        orchestrator.alert_manager.acknowledge_alert = MagicMock(return_value=True)

        result = await orchestrator.acknowledge_alert("alert_001")

        assert result is True
        orchestrator.alert_manager.acknowledge_alert.assert_called_once_with("alert_001")

    @pytest.mark.asyncio
    async def test_resolve_alert(self, orchestrator):
        """Test resolving an alert."""
        orchestrator.alert_manager = MagicMock()
        orchestrator.alert_manager.resolve_alert = MagicMock(return_value=True)

        result = await orchestrator.resolve_alert("alert_001")

        assert result is True
        orchestrator.alert_manager.resolve_alert.assert_called_once_with("alert_001")


class TestErrorHandling:
    """Test error handling in orchestrator."""

    @pytest.mark.asyncio
    async def test_initialize_error_handling(self, orchestrator):
        """Test error handling during initialization."""
        with patch.object(
            AlertRuleTemplates,
            "get_all_default_templates",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(Exception):
                await orchestrator.initialize(
                    metrics_query_engine=MagicMock(),
                    auto_register_templates=True,
                )

    @pytest.mark.asyncio
    async def test_start_error_handling(self, orchestrator):
        """Test error handling during start."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.start_continuous_evaluation = AsyncMock(
            side_effect=Exception("Test error")
        )

        with pytest.raises(Exception):
            await orchestrator.start()

        assert orchestrator.is_running is False

    @pytest.mark.asyncio
    async def test_acknowledge_alert_error_handling(self, orchestrator):
        """Test error handling when acknowledging alert."""
        orchestrator.alert_manager = MagicMock()
        orchestrator.alert_manager.acknowledge_alert = MagicMock(
            side_effect=Exception("Test error")
        )

        result = await orchestrator.acknowledge_alert("alert_001")

        assert result is False


class TestOrchestratorThreadSafety:
    """Test thread safety of orchestrator."""

    @pytest.mark.asyncio
    async def test_concurrent_register_rules(self, orchestrator, metric_config):
        """Test concurrent rule registration."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.register_metric_alert_rule = AsyncMock()

        rules = [
            AlertRule(
                rule_id=f"rule_{i}",
                name=f"Rule {i}",
                description="Test",
                severity=AlertSeverity.WARNING,
            )
            for i in range(5)
        ]

        # Register rules concurrently
        await asyncio.gather(
            *[orchestrator.register_custom_rule(rule, metric_config) for rule in rules]
        )

        assert len(orchestrator.registered_rules) == 5

    @pytest.mark.asyncio
    async def test_concurrent_start_stop(self, orchestrator):
        """Test concurrent start/stop operations."""
        orchestrator.metrics_alerter = MagicMock()
        orchestrator.metrics_alerter.start_continuous_evaluation = AsyncMock()
        orchestrator.metrics_alerter.stop_continuous_evaluation = AsyncMock()

        # Start and stop concurrently (should be serialized by lock)
        await asyncio.gather(
            orchestrator.start(),
            orchestrator.stop(),
        )

        # Should be stopped
        assert orchestrator.is_running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
