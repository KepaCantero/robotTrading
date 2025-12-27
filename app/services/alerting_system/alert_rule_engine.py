"""
T18.2: Alert Rule Engine - Rule evaluation and composition

Evaluates alert rules against incoming metrics with support for:
- Threshold-based rules (>, <, >=, <=, ==, !=)
- Change rules (percentage change over time window)
- Rule composition (AND/OR logic)
- Severity assignment
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .models import (
    AlertEvaluationContext,
    AlertEvent,
    AlertRule,
    AlertSeverity,
    AlertState,
    ChangeRule,
    LogicOperator,
    ThresholdRule,
)

logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """
    Rule evaluation engine for alert triggering.

    Features:
    - Threshold rule evaluation
    - Change rule evaluation
    - Rule composition (AND/OR logic)
    - Event generation with details
    - Evaluation history tracking
    """

    def __init__(self):
        """Initialize rule engine."""
        self.rules: Dict[str, AlertRule] = {}
        self.evaluation_history: List[Dict] = []
        self._max_history = 10000

    def register_rule(self, rule: AlertRule) -> None:
        """
        Register an alert rule.

        Args:
            rule: AlertRule to register
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered alert rule: {rule.rule_id} ({rule.name})")

    def unregister_rule(self, rule_id: str) -> bool:
        """
        Unregister an alert rule.

        Args:
            rule_id: ID of rule to unregister

        Returns:
            True if rule was unregistered, False if not found
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Unregistered alert rule: {rule_id}")
            return True
        return False

    def evaluate_rule(
        self, rule: AlertRule, context: AlertEvaluationContext
    ) -> Tuple[bool, Optional[AlertEvent]]:
        """
        Evaluate single rule against context.

        Args:
            rule: AlertRule to evaluate
            context: AlertEvaluationContext with metric data

        Returns:
            Tuple of (rule_triggered, alert_event)
        """
        if not rule.enabled:
            return False, None

        try:
            # Evaluate threshold rules
            threshold_results = [
                self._evaluate_threshold_rule(tr, context) for tr in rule.threshold_rules
            ]

            # Evaluate change rules
            change_results = [self._evaluate_change_rule(cr, context) for cr in rule.change_rules]

            # Combine results with logic operator
            all_results = threshold_results + change_results

            if not all_results:
                # No rules to evaluate
                return False, None

            if rule.logic_operator == LogicOperator.AND:
                triggered = all(all_results)
            else:  # OR
                triggered = any(all_results)

            if triggered:
                # Create alert event
                event = self._create_alert_event(rule, context, all_results)
                self._record_evaluation(rule.rule_id, context, triggered, event)
                logger.warning(f"Alert triggered: {rule.rule_id} ({rule.name}) - {event.message}")
                return True, event
            else:
                self._record_evaluation(rule.rule_id, context, triggered, None)
                return False, None

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            self._record_evaluation(rule.rule_id, context, False, None, str(e))
            return False, None

    def evaluate_all_rules(self, context: AlertEvaluationContext) -> List[AlertEvent]:
        """
        Evaluate all registered rules.

        Args:
            context: AlertEvaluationContext with metric data

        Returns:
            List of triggered AlertEvents
        """
        events = []

        for rule_id, rule in self.rules.items():
            try:
                triggered, event = self.evaluate_rule(rule, context)
                if triggered and event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_id} in batch: {e}")

        return events

    def _evaluate_threshold_rule(
        self, rule: ThresholdRule, context: AlertEvaluationContext
    ) -> bool:
        """Evaluate threshold rule."""
        # Check symbol and portfolio filters
        if rule.symbol and rule.symbol != context.symbol:
            return False
        if rule.portfolio_id and rule.portfolio_id != context.portfolio_id:
            return False

        # Check metric name
        if rule.metric_name != context.metric_name:
            return False

        # Evaluate comparison
        return rule.evaluate(context.current_value)

    def _evaluate_change_rule(self, rule: ChangeRule, context: AlertEvaluationContext) -> bool:
        """Evaluate change rule."""
        # Check symbol and portfolio filters
        if rule.symbol and rule.symbol != context.symbol:
            return False
        if rule.portfolio_id and rule.portfolio_id != context.portfolio_id:
            return False

        # Check metric name
        if rule.metric_name != context.metric_name:
            return False

        # Need window data to evaluate change
        if not context.window_data or len(context.window_data) < 2:
            return False

        # Calculate percentage change
        change_pct = context.calculate_change_percent()
        if change_pct is None:
            return False

        # Check direction
        abs_change = abs(change_pct)
        if abs_change <= rule.change_percent:
            return False

        # Check direction if specified
        if rule.direction == "up" and change_pct <= 0:
            return False
        if rule.direction == "down" and change_pct >= 0:
            return False

        return True

    def _create_alert_event(
        self, rule: AlertRule, context: AlertEvaluationContext, results: List[bool]
    ) -> AlertEvent:
        """Create alert event from triggered rule."""
        from uuid import uuid4

        event = AlertEvent(
            event_id=f"evt_{uuid4().hex[:12]}",
            rule_id=rule.rule_id,
            severity=rule.severity,
            state=AlertState.TRIGGERED,
            metric_name=context.metric_name,
            metric_value=context.current_value,
            symbol=context.symbol,
            portfolio_id=context.portfolio_id,
            triggered_at=datetime.utcnow(),
        )

        # Build message
        parts = [f"{rule.name}: {rule.description}"]
        parts.append(f"Metric: {context.metric_name}")
        if context.symbol:
            parts.append(f"Symbol: {context.symbol}")
        parts.append(f"Value: {context.current_value}")

        event.message = " | ".join(parts)
        event.details = {
            "threshold_rules_count": len(rule.threshold_rules),
            "change_rules_count": len(rule.change_rules),
            "logic_operator": rule.logic_operator.value,
        }

        return event

    def _record_evaluation(
        self,
        rule_id: str,
        context: AlertEvaluationContext,
        triggered: bool,
        event: Optional[AlertEvent],
        error: Optional[str] = None,
    ) -> None:
        """Record rule evaluation in history."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "rule_id": rule_id,
            "metric_name": context.metric_name,
            "triggered": triggered,
            "event_id": event.event_id if event else None,
            "error": error,
        }

        self.evaluation_history.append(record)

        # Keep history size bounded
        if len(self.evaluation_history) > self._max_history:
            self.evaluation_history = self.evaluation_history[-self._max_history :]

    def get_evaluation_stats(self) -> Dict:
        """Get statistics about rule evaluation."""
        if not self.evaluation_history:
            return {
                "total_evaluations": 0,
                "total_triggered": 0,
                "by_rule": {},
            }

        stats = {
            "total_evaluations": len(self.evaluation_history),
            "total_triggered": sum(1 for e in self.evaluation_history if e["triggered"]),
            "by_rule": {},
        }

        # Count by rule
        for record in self.evaluation_history:
            rule_id = record["rule_id"]
            if rule_id not in stats["by_rule"]:
                stats["by_rule"][rule_id] = {"total": 0, "triggered": 0}

            stats["by_rule"][rule_id]["total"] += 1
            if record["triggered"]:
                stats["by_rule"][rule_id]["triggered"] += 1

        return stats

    def clear_evaluation_history(self) -> None:
        """Clear evaluation history."""
        self.evaluation_history.clear()
        logger.info("Cleared rule evaluation history")

    def get_rules_summary(self) -> Dict:
        """Get summary of registered rules."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "by_severity": {
                severity.value: sum(1 for r in self.rules.values() if r.severity == severity)
                for severity in AlertSeverity
            },
            "rule_ids": list(self.rules.keys()),
        }
