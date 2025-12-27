"""
T18.2: Advanced Alerting System - Metrics-Driven Alerter

Component that queries metrics from T18.1 and evaluates alert rules.
Provides the bridge between real-time metrics and rule-based alerting.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import uuid4

from app.services.alerting_system.alert_manager import AlertManager
from app.services.alerting_system.alert_rule_engine import AlertRuleEngine
from app.services.alerting_system.models import AlertEvent, AlertRule, AlertState, ChangeRule

logger = logging.getLogger(__name__)


@dataclass
class MetricQueryConfig:
    """Configuration for metric queries."""

    metric_name: str
    lookback_minutes: int = 5
    aggregation_window_minutes: int = 1


@dataclass
class EvaluationStatistics:
    """Statistics about rule evaluations."""

    rules_evaluated: int = 0
    rules_triggered: int = 0
    evaluation_errors: int = 0
    total_evaluations: int = 0
    avg_evaluation_time_ms: float = 0.0
    last_evaluation_at: Optional[datetime] = None
    evaluation_start_time: datetime = field(default_factory=datetime.utcnow)

    def add_evaluation(self, triggered: bool, duration_ms: float, error: bool = False):
        """Record an evaluation."""
        self.total_evaluations += 1
        if triggered:
            self.rules_triggered += 1
        if error:
            self.evaluation_errors += 1
        # Update average evaluation time
        if self.avg_evaluation_time_ms == 0:
            self.avg_evaluation_time_ms = duration_ms
        else:
            self.avg_evaluation_time_ms = (
                self.avg_evaluation_time_ms * (self.total_evaluations - 1) + duration_ms
            ) / self.total_evaluations
        self.last_evaluation_at = datetime.utcnow()

    def reset(self):
        """Reset statistics."""
        self.rules_evaluated = 0
        self.rules_triggered = 0
        self.evaluation_errors = 0
        self.total_evaluations = 0
        self.avg_evaluation_time_ms = 0.0
        self.last_evaluation_at = None
        self.evaluation_start_time = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        uptime_seconds = (datetime.utcnow() - self.evaluation_start_time).total_seconds()
        return {
            "rules_evaluated": self.rules_evaluated,
            "rules_triggered": self.rules_triggered,
            "evaluation_errors": self.evaluation_errors,
            "total_evaluations": self.total_evaluations,
            "avg_evaluation_time_ms": round(self.avg_evaluation_time_ms, 2),
            "last_evaluation_at": (
                self.last_evaluation_at.isoformat() if self.last_evaluation_at else None
            ),
            "uptime_seconds": round(uptime_seconds, 0),
        }


class MetricsDrivenAlerter:
    """
    Evaluates alert rules against real-time metrics.

    This class acts as a bridge between the MetricsQueryEngine (T18.1) and
    the AlertRuleEngine/AlertManager (T18.2). It:
    1. Registers metric-specific alert rules
    2. Periodically queries metrics from the database
    3. Evaluates rules against metric values
    4. Triggers alerts via AlertManager
    """

    def __init__(
        self,
        alert_rule_engine: AlertRuleEngine,
        alert_manager: AlertManager,
    ):
        """Initialize the alerter."""
        self.alert_rule_engine = alert_rule_engine
        self.alert_manager = alert_manager
        self.registered_rules: Dict[str, AlertRule] = {}
        self.metric_query_configs: Dict[str, MetricQueryConfig] = {}
        self.evaluation_stats = EvaluationStatistics()
        self.is_running = False
        self._evaluation_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_metric_alert_rule(
        self,
        rule: AlertRule,
        metric_query_config: MetricQueryConfig,
    ) -> None:
        """
        Register an alert rule tied to a specific metric.

        Args:
            rule: The AlertRule to register
            metric_query_config: Configuration for querying the metric
        """
        self.registered_rules[rule.rule_id] = rule
        self.metric_query_configs[rule.rule_id] = metric_query_config
        self.logger.info(
            f"Registered alert rule: {rule.rule_id} for metric {metric_query_config.metric_name}"
        )

    def register_rules(
        self,
        rules: List[AlertRule],
        metric_query_config: MetricQueryConfig,
    ) -> None:
        """Register multiple alert rules with same metric config."""
        for rule in rules:
            self.register_metric_alert_rule(rule, metric_query_config)

    async def evaluate_metric_rules(
        self,
        metric_queries: Dict[str, Dict],
    ) -> Dict:
        """
        Single evaluation cycle - evaluate all registered rules.

        Args:
            metric_queries: Dict mapping rule_id to metric query results
                          Example: {
                            "portfolio_drawdown_warning": {
                              "current_value": Decimal("8.5"),
                              "previous_value": Decimal("7.2"),
                              "window_data": [...]
                            }
                          }

        Returns:
            Dict with evaluation results and triggered alerts
        """
        evaluation_start = datetime.utcnow()
        results = {
            "total_rules": len(self.registered_rules),
            "triggered_alerts": [],
            "errors": [],
            "evaluation_time_ms": 0,
        }

        for rule_id, rule in self.registered_rules.items():
            if not rule.enabled:
                continue

            try:
                # Get metric data for this rule
                if rule_id not in metric_queries:
                    self.logger.warning(f"No metric data for rule {rule_id}")
                    continue

                metric_data = metric_queries[rule_id]
                current_value = metric_data.get("current_value")

                if current_value is None:
                    self.logger.warning(f"No current value for rule {rule_id}")
                    continue

                # Evaluate rule thresholds
                should_trigger = await self._evaluate_threshold_rules(
                    rule, current_value, metric_data
                )

                if should_trigger:
                    # Create and trigger alert
                    alert_event = await self._create_and_trigger_alert(rule, metric_data)
                    results["triggered_alerts"].append(
                        {
                            "rule_id": rule_id,
                            "event_id": alert_event.event_id,
                            "severity": alert_event.severity.value,
                        }
                    )
                    self.evaluation_stats.rules_triggered += 1

                self.evaluation_stats.rules_evaluated += 1

            except Exception as e:
                error_msg = f"Error evaluating rule {rule_id}: {str(e)}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                self.evaluation_stats.evaluation_errors += 1

        # Update statistics
        duration_ms = (datetime.utcnow() - evaluation_start).total_seconds() * 1000
        results["evaluation_time_ms"] = round(duration_ms, 2)
        self.evaluation_stats.add_evaluation(
            triggered=len(results["triggered_alerts"]) > 0,
            duration_ms=duration_ms,
            error=len(results["errors"]) > 0,
        )

        return results

    async def _evaluate_threshold_rules(
        self,
        rule: AlertRule,
        current_value: Decimal,
        metric_data: Dict,
    ) -> bool:
        """
        Evaluate threshold-based rules.

        Args:
            rule: The AlertRule to evaluate
            current_value: Current metric value
            metric_data: Complete metric data

        Returns:
            True if rule should trigger, False otherwise
        """
        threshold_results = []

        # Evaluate threshold rules
        for threshold_rule in rule.threshold_rules:
            result = threshold_rule.evaluate(current_value)
            threshold_results.append(result)

        # Evaluate change rules
        for change_rule in rule.change_rules:
            result = self._evaluate_change_rule(change_rule, metric_data)
            threshold_results.append(result)

        # Combine results with logic operator
        if not threshold_results:
            return False

        if rule.logic_operator.value == "and":
            return all(threshold_results)
        else:  # OR logic (default)
            return any(threshold_results)

    def _evaluate_change_rule(self, change_rule: ChangeRule, metric_data: Dict) -> bool:
        """
        Evaluate percentage change rule.

        Args:
            change_rule: The ChangeRule to evaluate
            metric_data: Metric data with window history

        Returns:
            True if change exceeds threshold, False otherwise
        """
        window_data = metric_data.get("window_data", [])
        if not window_data or len(window_data) < 2:
            return False

        first_value = window_data[0]
        current_value = metric_data.get("current_value")

        if first_value == 0 or current_value is None:
            return False

        change_percent = ((current_value - first_value) / first_value) * 100

        # Check direction
        if change_rule.direction == "up":
            return change_percent > float(change_rule.change_percent)
        elif change_rule.direction == "down":
            return change_percent < float(change_rule.change_percent)
        else:  # "any"
            abs_change = abs(change_percent)
            abs_threshold = abs(float(change_rule.change_percent))
            return abs_change > abs_threshold

    async def _create_and_trigger_alert(
        self,
        rule: AlertRule,
        metric_data: Dict,
    ) -> AlertEvent:
        """
        Create and trigger an alert event.

        Args:
            rule: The rule that triggered
            metric_data: The metric data that caused trigger

        Returns:
            The created AlertEvent
        """
        current_value = metric_data.get("current_value")
        symbol = metric_data.get("symbol")
        portfolio_id = metric_data.get("portfolio_id")

        # Create alert event
        event = AlertEvent(
            event_id=str(uuid4()),
            rule_id=rule.rule_id,
            severity=rule.severity,
            state=AlertState.TRIGGERED,
            metric_name=self.metric_query_configs.get(
                rule.rule_id, MetricQueryConfig("unknown")
            ).metric_name,
            metric_value=current_value,
            symbol=symbol,
            portfolio_id=portfolio_id,
            message=f"Alert triggered: {rule.name}",
            details={
                "rule_description": rule.description,
                "threshold_rules": [r.to_dict() for r in rule.threshold_rules],
                "change_rules": [r.to_dict() for r in rule.change_rules],
                "metric_value": str(current_value) if current_value else None,
            },
        )

        # Trigger via alert manager
        await self.alert_manager.trigger_alert(rule, event)

        return event

    async def start_continuous_evaluation(
        self,
        interval_seconds: int = 60,
        metric_query_fn=None,
    ) -> None:
        """
        Start background continuous evaluation loop.

        Args:
            interval_seconds: Evaluation interval in seconds
            metric_query_fn: Async function that returns metric queries dict
        """
        if self.is_running:
            self.logger.warning("Evaluation already running")
            return

        self.is_running = True
        self.logger.info(f"Starting continuous evaluation with {interval_seconds}s interval")

        async def evaluation_loop():
            while self.is_running:
                try:
                    # Query metrics if function provided
                    metric_queries = {}
                    if metric_query_fn:
                        metric_queries = await metric_query_fn(self.registered_rules)

                    # Evaluate all rules
                    await self.evaluate_metric_rules(metric_queries)

                except Exception as e:
                    self.logger.error(f"Error in evaluation loop: {str(e)}")
                    self.evaluation_stats.evaluation_errors += 1

                # Wait before next evaluation
                await asyncio.sleep(interval_seconds)

        self._evaluation_task = asyncio.create_task(evaluation_loop())

    async def stop_continuous_evaluation(self) -> None:
        """Stop the continuous evaluation loop."""
        if not self.is_running:
            return

        self.is_running = False
        self.logger.info("Stopping continuous evaluation")

        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass

    def get_evaluation_statistics(self) -> Dict:
        """Get current evaluation statistics."""
        return self.evaluation_stats.to_dict()

    def get_registered_rules(self) -> Dict[str, AlertRule]:
        """Get all registered rules."""
        return dict(self.registered_rules)

    def get_rule_count(self) -> int:
        """Get number of registered rules."""
        return len(self.registered_rules)

    def get_enabled_rule_count(self) -> int:
        """Get number of enabled rules."""
        return sum(1 for r in self.registered_rules.values() if r.enabled)

    def is_evaluating(self) -> bool:
        """Check if evaluation is running."""
        return self.is_running

    def reset_statistics(self) -> None:
        """Reset evaluation statistics."""
        self.evaluation_stats.reset()
