"""
T18.2: Advanced Alerting System - Alerting Orchestrator

Main controller that initializes and manages the complete alerting system.
Coordinates MetricsDrivenAlerter, AlertRuleEngine, AlertManager, and
NotificationDispatcher for comprehensive real-time alert monitoring.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

from app.services.alerting_system.alert_manager import AlertManager
from app.services.alerting_system.alert_rule_engine import AlertRuleEngine
from app.services.alerting_system.metrics_driven_alerter import (
    EvaluationStatistics,
    MetricQueryConfig,
    MetricsDrivenAlerter,
)
from app.services.alerting_system.models import AlertEvent, AlertRule, AlertSeverity
from app.services.alerting_system.notification_channels import NotificationDispatcher
from app.services.alerting_system.rule_templates import AlertRuleTemplates

logger = logging.getLogger(__name__)


@dataclass
class AlertingHealth:
    """Health status of the alerting system."""

    is_running: bool
    is_evaluating: bool
    rules_registered: int
    enabled_rules: int
    total_alerts_triggered: int
    total_alerts_resolved: int
    last_evaluation_at: Optional[datetime] = None
    evaluation_errors: int = 0
    avg_evaluation_time_ms: float = 0.0
    components_status: Dict[str, bool] = field(default_factory=dict)


@dataclass
class AlertingStatistics:
    """Aggregated statistics for the alerting system."""

    total_rules: int = 0
    enabled_rules: int = 0
    total_evaluations: int = 0
    total_alerts_triggered: int = 0
    total_alerts_resolved: int = 0
    total_alerts_acknowledged: int = 0
    avg_evaluation_time_ms: float = 0.0
    evaluation_errors: int = 0
    uptime_seconds: float = 0.0
    system_start_time: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        uptime = (datetime.utcnow() - self.system_start_time).total_seconds()
        return {
            "total_rules": self.total_rules,
            "enabled_rules": self.enabled_rules,
            "total_evaluations": self.total_evaluations,
            "total_alerts_triggered": self.total_alerts_triggered,
            "total_alerts_resolved": self.total_alerts_resolved,
            "total_alerts_acknowledged": self.total_alerts_acknowledged,
            "avg_evaluation_time_ms": round(self.avg_evaluation_time_ms, 2),
            "evaluation_errors": self.evaluation_errors,
            "uptime_seconds": round(uptime, 0),
        }


class AlertingOrchestrator:
    """
    Main orchestrator for the alerting system.

    Manages initialization, lifecycle, and coordination of all alerting
    components. Acts as the single point of contact for alert system
    operations.

    Components managed:
    - AlertRuleEngine: Rule evaluation engine
    - AlertManager: Alert lifecycle and deduplication
    - NotificationDispatcher: Multi-channel notification delivery
    - MetricsDrivenAlerter: Metrics querying and rule evaluation
    """

    def __init__(self):
        """Initialize the alerting orchestrator."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_running = False

        # Initialize core components
        self.alert_rule_engine = AlertRuleEngine()
        self.alert_manager = AlertManager()
        self.notification_dispatcher = NotificationDispatcher()
        self.metrics_alerter: Optional[MetricsDrivenAlerter] = None

        # System state
        self.registered_rules: Dict[str, AlertRule] = {}
        self.statistics = AlertingStatistics()
        self._evaluation_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        self.logger.info("AlertingOrchestrator initialized")

    async def initialize(
        self,
        metrics_query_engine=None,
        auto_register_templates: bool = True,
    ) -> None:
        """
        Initialize the alerting orchestrator with metrics engine.

        Args:
            metrics_query_engine: MetricsQueryEngine instance from T18.1
            auto_register_templates: Whether to register default templates
        """
        async with self._lock:
            try:
                # Create MetricsDrivenAlerter with metrics engine
                if metrics_query_engine:
                    self.metrics_alerter = MetricsDrivenAlerter(
                        self.alert_rule_engine,
                        self.alert_manager,
                    )
                    self.logger.info("MetricsDrivenAlerter initialized")
                else:
                    self.logger.warning("No metrics query engine provided")

                # Register default templates if requested
                if auto_register_templates:
                    await self.register_default_rules()

                self.logger.info(
                    f"Alerting orchestrator initialized with {len(self.registered_rules)} rules"
                )

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error during initialization: {str(e)}")
                raise

    async def register_default_rules(self) -> None:
        """Register all pre-configured rule templates."""
        try:
            templates = AlertRuleTemplates.get_all_default_templates()

            for template in templates:
                # Register with metrics alerter
                if self.metrics_alerter:
                    metric_name = "METRIC"  # Default metric name
                    if template.threshold_rules:
                        metric_name = template.threshold_rules[0].metric_name
                    elif template.change_rules:
                        metric_name = template.change_rules[0].metric_name

                    config = MetricQueryConfig(
                        metric_name=metric_name,
                        lookback_minutes=5,
                    )
                    self.metrics_alerter.register_metric_alert_rule(template, config)

                # Track rule
                self.registered_rules[template.rule_id] = template

            self.statistics.total_rules = len(self.registered_rules)
            self.statistics.enabled_rules = sum(
                1 for r in self.registered_rules.values() if r.enabled
            )

            self.logger.info(f"Registered {len(templates)} default alert rule templates")

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error registering default rules: {str(e)}")
            raise

    async def register_custom_rule(
        self,
        rule: AlertRule,
        metric_config: MetricQueryConfig,
    ) -> None:
        """
        Register a custom alert rule.

        Args:
            rule: The AlertRule to register
            metric_config: Metric query configuration
        """
        try:
            if self.metrics_alerter:
                self.metrics_alerter.register_metric_alert_rule(rule, metric_config)

            self.registered_rules[rule.rule_id] = rule
            self.statistics.total_rules = len(self.registered_rules)
            self.statistics.enabled_rules = sum(
                1 for r in self.registered_rules.values() if r.enabled
            )

            self.logger.info(f"Registered custom rule: {rule.rule_id}")

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error registering custom rule: {str(e)}")
            raise

    async def enable_rule(self, rule_id: str) -> None:
        """Enable a specific rule."""
        if rule_id in self.registered_rules:
            self.registered_rules[rule_id].enabled = True
            self.statistics.enabled_rules = sum(
                1 for r in self.registered_rules.values() if r.enabled
            )
            self.logger.info(f"Enabled rule: {rule_id}")

    async def disable_rule(self, rule_id: str) -> None:
        """Disable a specific rule."""
        if rule_id in self.registered_rules:
            self.registered_rules[rule_id].enabled = False
            self.statistics.enabled_rules = sum(
                1 for r in self.registered_rules.values() if r.enabled
            )
            self.logger.info(f"Disabled rule: {rule_id}")

    async def start(
        self,
        evaluation_interval_seconds: int = 60,
        metric_query_fn: Optional[Callable] = None,
    ) -> None:
        """
        Start the alerting system.

        Args:
            evaluation_interval_seconds: Interval between evaluations
            metric_query_fn: Async function that returns metric queries dict
        """
        async with self._lock:
            if self.is_running:
                self.logger.warning("Alerting orchestrator already running")
                return

            if not self.metrics_alerter:
                self.logger.warning("MetricsDrivenAlerter not initialized")
                return

            try:
                self.is_running = True

                # Start continuous evaluation
                await self.metrics_alerter.start_continuous_evaluation(
                    interval_seconds=evaluation_interval_seconds,
                    metric_query_fn=metric_query_fn,
                )

                self.logger.info(
                    f"Alerting orchestrator started with {evaluation_interval_seconds}s interval"
                )

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.is_running = False
                self.logger.error(f"Error starting alerting orchestrator: {str(e)}")
                raise

    async def stop(self) -> None:
        """Stop the alerting system gracefully."""
        async with self._lock:
            if not self.is_running:
                return

            try:
                if self.metrics_alerter:
                    await self.metrics_alerter.stop_continuous_evaluation()

                # Flush any pending operations
                await self._flush_pending_operations()

                self.is_running = False
                self.logger.info("Alerting orchestrator stopped")

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error stopping alerting orchestrator: {str(e)}")

    async def _flush_pending_operations(self) -> None:
        """Flush any pending alerts or operations."""
        try:
            # Give time for any in-flight operations
            await asyncio.sleep(0.5)
            self.logger.info("Flushed pending operations")
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error flushing pending operations: {str(e)}")

    async def trigger_alert_manual(self, alert_event: AlertEvent) -> None:
        """
        Manually trigger an alert (for testing/events).

        Args:
            alert_event: The AlertEvent to trigger
        """
        try:
            if self.alert_manager:
                # Process through alert manager for deduplication
                for rule_id, rule in self.registered_rules.items():
                    if rule.rule_id == alert_event.rule_id:
                        await self.alert_manager.trigger_alert(rule, alert_event)
                        break

            self.logger.info(f"Manually triggered alert: {alert_event.event_id}")

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error triggering manual alert: {str(e)}")

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an active alert.

        Args:
            alert_id: The alert event ID

        Returns:
            True if acknowledged, False otherwise
        """
        try:
            return self.alert_manager.acknowledge_alert(alert_id)
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error acknowledging alert: {str(e)}")
            return False

    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an active alert.

        Args:
            alert_id: The alert event ID

        Returns:
            True if resolved, False otherwise
        """
        try:
            return self.alert_manager.resolve_alert(alert_id)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error resolving alert: {str(e)}")
            return False

    def get_health_status(self) -> AlertingHealth:
        """Get current health status of the alerting system."""
        try:
            alerter_stats = (
                self.metrics_alerter.evaluation_stats
                if self.metrics_alerter
                else EvaluationStatistics()
            )

            manager_stats = self.alert_manager.get_alert_statistics()

            return AlertingHealth(
                is_running=self.is_running,
                is_evaluating=(
                    self.metrics_alerter.is_evaluating() if self.metrics_alerter else False
                ),
                rules_registered=len(self.registered_rules),
                enabled_rules=sum(1 for r in self.registered_rules.values() if r.enabled),
                total_alerts_triggered=manager_stats.get("total_triggered", 0),
                total_alerts_resolved=manager_stats.get("total_resolved", 0),
                last_evaluation_at=alerter_stats.last_evaluation_at,
                evaluation_errors=alerter_stats.evaluation_errors,
                avg_evaluation_time_ms=alerter_stats.avg_evaluation_time_ms,
                components_status={
                    "alert_rule_engine": self.alert_rule_engine is not None,
                    "alert_manager": self.alert_manager is not None,
                    "notification_dispatcher": self.notification_dispatcher is not None,
                    "metrics_alerter": self.metrics_alerter is not None,
                },
            )

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error getting health status: {str(e)}")
            return AlertingHealth(
                is_running=False,
                is_evaluating=False,
                rules_registered=0,
                enabled_rules=0,
                total_alerts_triggered=0,
                total_alerts_resolved=0,
                evaluation_errors=1,
            )

    def get_statistics(self) -> Dict:
        """Get aggregated statistics."""
        try:
            alerter_stats = (
                self.metrics_alerter.evaluation_stats
                if self.metrics_alerter
                else EvaluationStatistics()
            )

            manager_stats = self.alert_manager.get_alert_statistics()

            return {
                "total_rules": len(self.registered_rules),
                "enabled_rules": sum(1 for r in self.registered_rules.values() if r.enabled),
                "total_evaluations": alerter_stats.total_evaluations,
                "rules_triggered": alerter_stats.rules_triggered,
                "evaluation_errors": alerter_stats.evaluation_errors,
                "avg_evaluation_time_ms": round(alerter_stats.avg_evaluation_time_ms, 2),
                "total_alerts_triggered": manager_stats.get("total_triggered", 0),
                "total_alerts_resolved": manager_stats.get("total_resolved", 0),
                "total_alerts_acknowledged": manager_stats.get("total_acknowledged", 0),
                "alert_history_size": manager_stats.get("history_size", 0),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error getting statistics: {str(e)}")
            return {}

    def get_registered_rules(self) -> Dict[str, AlertRule]:
        """Get all registered rules."""
        return dict(self.registered_rules)

    def get_rule_by_id(self, rule_id: str) -> Optional[AlertRule]:
        """Get a specific rule by ID."""
        return self.registered_rules.get(rule_id)

    def get_rules_by_severity(self, severity: AlertSeverity) -> List[AlertRule]:
        """Get all rules with a specific severity."""
        return [r for r in self.registered_rules.values() if r.severity == severity]

    def get_rules_by_category(self, category: str) -> List[AlertRule]:
        """Get all rules with a specific category tag."""
        return [r for r in self.registered_rules.values() if r.tags.get("category") == category]

    async def reset_statistics(self) -> None:
        """Reset all statistics."""
        try:
            if self.metrics_alerter:
                self.metrics_alerter.reset_statistics()

            # Clear resolved alerts from alert manager
            self.alert_manager.clear_resolved_alerts(older_than_hours=0)
            self.statistics = AlertingStatistics()

            self.logger.info("Statistics reset")

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error resetting statistics: {str(e)}")
