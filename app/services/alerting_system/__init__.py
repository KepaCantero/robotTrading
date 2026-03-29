"""
T18.2: Advanced Alerting System Package

Provides rule-based alerting with webhook/email/Slack/Discord/Telegram integration:
- Alert rule engine for metric evaluation
- Alert manager for state machine and deduplication
- Notification dispatcher for multi-channel delivery
- Metrics-driven alerter for continuous rule evaluation
- Alerting orchestrator for lifecycle management
"""

from app.application.alerting.alerting_orchestrator import (
    AlertingHealth,
    AlertingOrchestrator,
    AlertingStatistics,
)

from .alert_manager import AlertManager
from .alert_rule_engine import AlertRuleEngine
from .metrics_driven_alerter import MetricQueryConfig, MetricsDrivenAlerter
from .models import (
    AlertEvent,
    AlertHistory,
    AlertRule,
    AlertSeverity,
    AlertState,
    ChangeRule,
    ComparisonOperator,
    LogicOperator,
    NotificationChannelType,
    NotificationTarget,
    ThresholdRule,
)
from .notification_channels import NotificationDispatcher, TelegramChannel
from .rule_templates import AlertRuleTemplates

# Singleton orchestrator instance
_orchestrator: AlertingOrchestrator = None


def get_alerting_orchestrator() -> AlertingOrchestrator:
    """
    Get the singleton AlertingOrchestrator instance.

    Creates if not already instantiated.

    Returns:
        AlertingOrchestrator singleton instance
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AlertingOrchestrator()
    return _orchestrator


async def initialize_alerting_orchestrator(metrics_query_engine=None) -> AlertingOrchestrator:
    """
    Initialize the alerting orchestrator with metrics engine.

    Args:
        metrics_query_engine: MetricsQueryEngine instance from T18.1

    Returns:
        Initialized AlertingOrchestrator instance
    """
    orchestrator = get_alerting_orchestrator()
    await orchestrator.initialize(
        metrics_query_engine=metrics_query_engine, auto_register_templates=True
    )
    return orchestrator


async def start_alerting(
    evaluation_interval_seconds: int = 60,
    metric_query_fn=None,
) -> AlertingOrchestrator:
    """
    Start the alerting system.

    Args:
        evaluation_interval_seconds: Evaluation interval in seconds
        metric_query_fn: Async function that returns metric queries dict

    Returns:
        Running AlertingOrchestrator instance
    """
    orchestrator = get_alerting_orchestrator()
    await orchestrator.start(
        evaluation_interval_seconds=evaluation_interval_seconds, metric_query_fn=metric_query_fn
    )
    return orchestrator


async def stop_alerting() -> None:
    """Stop the alerting system gracefully."""
    orchestrator = get_alerting_orchestrator()
    await orchestrator.stop()


def reset_alerting_orchestrator() -> None:
    """Reset the singleton orchestrator (for testing)."""
    global _orchestrator
    _orchestrator = None


__all__ = [
    "AlertEvent",
    "AlertHistory",
    "AlertManager",
    # Models
    "AlertRule",
    # Services
    "AlertRuleEngine",
    "AlertRuleTemplates",
    "AlertSeverity",
    "AlertState",
    "AlertingHealth",
    "AlertingOrchestrator",
    "AlertingStatistics",
    "ChangeRule",
    "ComparisonOperator",
    "LogicOperator",
    "MetricQueryConfig",
    "MetricsDrivenAlerter",
    "NotificationChannelType",
    "NotificationDispatcher",
    "NotificationTarget",
    "TelegramChannel",
    "ThresholdRule",
    # Functions
    "get_alerting_orchestrator",
    "initialize_alerting_orchestrator",
    "reset_alerting_orchestrator",
    "start_alerting",
    "stop_alerting",
]
