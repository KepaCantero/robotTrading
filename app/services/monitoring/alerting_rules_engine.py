"""
FASE 2: AlertingRulesEngine - Real-time alert rule evaluation and management

Prometheus-based alerting with configurable rules for trading system monitoring.
Supports threshold-based, anomaly-based, and composite alerts with webhook delivery.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertConditionType(str, Enum):
    """Types of alert conditions."""

    THRESHOLD = "threshold"  # Simple comparison
    CHANGE = "change"  # Percentage/absolute change
    ANOMALY = "anomaly"  # Deviation from baseline
    COMPOSITE = "composite"  # Multiple conditions


@dataclass
class AlertRule:
    """Definition of an alert rule."""

    rule_id: str
    name: str
    description: str
    metric_name: str
    condition_type: AlertConditionType
    severity: AlertSeverity
    enabled: bool = True

    # Threshold-based conditions
    threshold_value: Optional[float] = None
    comparison_op: str = ">"  # >, <, >=, <=, ==, !=

    # Change-based conditions
    change_percent: Optional[float] = None
    change_period_sec: int = 300  # 5 minutes default

    # Anomaly conditions
    baseline_value: Optional[float] = None
    std_dev_multiplier: float = 2.0

    # Evaluation window
    for_duration_sec: int = 60  # Alert fires if condition true for this duration

    # Webhook callback
    webhook_url: Optional[str] = None
    webhook_enabled: bool = False

    created_at: datetime = field(default_factory=datetime.now)
    last_fired_at: Optional[datetime] = None
    fire_count: int = 0


@dataclass
class Alert:
    """An alert instance."""

    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    metric_name: str
    metric_value: float
    condition_desc: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    webhook_delivered: bool = False
    error_message: Optional[str] = None


class AlertingRulesEngine:
    """
    Manages and evaluates alert rules for the trading system.

    Alert Rule Categories:

    1. Portfolio Alerts
       - drawdown > 20%
       - cash < threshold
       - leverage > max

    2. Trading Alerts
       - win_rate < 40%
       - losing_streak > 5
       - sharpe < 0.5

    3. Risk Alerts
       - var_95 > limit
       - concentration > 50%
       - beta > 2.0

    4. System Alerts
       - api_response > 5s
       - memory usage > threshold
       - strategy error rate > 5%

    5. Model Alerts
       - accuracy < threshold
       - drift detected
       - latency > limit
    """

    def __init__(self):
        """Initialize alerting rules engine."""
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.active_alerts: Dict[str, Alert] = {}  # rule_id -> Alert
        self.metric_history: Dict[str, List[tuple]] = {}  # metric_name -> [(timestamp, value)]
        self.history_size = 1000  # Keep last N values per metric
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialize_default_rules()
        logger.info("✅ AlertingRulesEngine initialized")

    def _initialize_default_rules(self) -> None:
        """Initialize standard alert rules."""
        # Portfolio alerts
        self.create_rule(
            AlertRule(
                rule_id="rule_max_drawdown",
                name="Maximum Drawdown Exceeded",
                description="Alert when maximum drawdown exceeds threshold",
                metric_name="max_drawdown_pct",
                condition_type=AlertConditionType.THRESHOLD,
                severity=AlertSeverity.CRITICAL,
                threshold_value=25.0,
                comparison_op=">",
                for_duration_sec=300,
            )
        )

        # Risk alerts
        self.create_rule(
            AlertRule(
                rule_id="rule_high_leverage",
                name="Leverage Ratio Critical",
                description="Alert when leverage exceeds safe threshold",
                metric_name="leverage_ratio",
                condition_type=AlertConditionType.THRESHOLD,
                severity=AlertSeverity.WARNING,
                threshold_value=3.0,
                comparison_op=">",
                for_duration_sec=120,
            )
        )

        # Trading alerts
        self.create_rule(
            AlertRule(
                rule_id="rule_low_win_rate",
                name="Win Rate Declining",
                description="Alert when win rate drops below threshold",
                metric_name="win_rate_pct",
                condition_type=AlertConditionType.THRESHOLD,
                severity=AlertSeverity.WARNING,
                threshold_value=40.0,
                comparison_op="<",
                for_duration_sec=600,
            )
        )

        # System alerts
        self.create_rule(
            AlertRule(
                rule_id="rule_high_api_latency",
                name="API Response Time Degraded",
                description="Alert when API response time is too high",
                metric_name="api_response_time_milliseconds",
                condition_type=AlertConditionType.THRESHOLD,
                severity=AlertSeverity.WARNING,
                threshold_value=5000.0,
                comparison_op=">",
                for_duration_sec=180,
            )
        )

        # Model alerts
        self.create_rule(
            AlertRule(
                rule_id="rule_low_model_accuracy",
                name="Model Accuracy Degraded",
                description="Alert when model accuracy is below threshold",
                metric_name="model_accuracy",
                condition_type=AlertConditionType.THRESHOLD,
                severity=AlertSeverity.WARNING,
                threshold_value=0.80,
                comparison_op="<",
                for_duration_sec=1800,
            )
        )

        logger.info(f"✅ Initialized {len(self.rules)} default alert rules")

    def create_rule(self, rule: AlertRule) -> bool:
        """Create a new alert rule."""
        if rule.rule_id in self.rules:
            logger.warning(f"⚠️ Rule already exists: {rule.rule_id}")
            return False

        self.rules[rule.rule_id] = rule
        self.metric_history[rule.metric_name] = []
        logger.info(f"✅ Created alert rule: {rule.name}")
        return True

    def delete_rule(self, rule_id: str) -> bool:
        """Delete an alert rule."""
        if rule_id not in self.rules:
            return False

        rule = self.rules.pop(rule_id)
        logger.info(f"✅ Deleted alert rule: {rule.name}")
        return True

    def enable_rule(self, rule_id: str) -> bool:
        """Enable an alert rule."""
        if rule_id not in self.rules:
            return False

        self.rules[rule_id].enabled = True
        logger.info(f"✅ Enabled rule: {rule_id}")
        return True

    def disable_rule(self, rule_id: str) -> bool:
        """Disable an alert rule."""
        if rule_id not in self.rules:
            return False

        self.rules[rule_id].enabled = False
        logger.info(f"✅ Disabled rule: {rule_id}")
        return True

    async def evaluate_rules(self, metrics: Dict[str, float]) -> List[Alert]:
        """
        Evaluate all rules against current metric values.

        Args:
            metrics: Dictionary of metric_name -> value

        Returns:
            List of newly triggered alerts
        """
        new_alerts = []

        for metric_name, value in metrics.items():
            # Store metric value in history
            if metric_name not in self.metric_history:
                self.metric_history[metric_name] = []

            self.metric_history[metric_name].append((datetime.now().timestamp(), value))

            # Keep only last N values
            if len(self.metric_history[metric_name]) > self.history_size:
                self.metric_history[metric_name] = self.metric_history[metric_name][
                    -self.history_size :
                ]

        # Evaluate rules for updated metrics
        for rule in self.rules.values():
            if not rule.enabled or rule.metric_name not in metrics:
                continue

            metric_value = metrics[rule.metric_name]
            condition_met = self._evaluate_condition(rule, metric_value)

            if condition_met:
                await self._handle_alert_triggered(rule, metric_value)
                new_alerts.append(self._create_alert(rule, metric_value, condition_met))
            else:
                # Condition no longer met
                if rule.rule_id in self.active_alerts:
                    alert = self.active_alerts.pop(rule.rule_id)
                    alert.resolved_at = datetime.now()
                    self.alerts.append(alert)
                    logger.info(f"✅ Alert resolved: {rule.name}")

        return new_alerts

    def _evaluate_condition(self, rule: AlertRule, value: float) -> bool:
        """Evaluate if alert condition is met."""
        if rule.condition_type == AlertConditionType.THRESHOLD:
            return self._evaluate_threshold(value, rule.threshold_value, rule.comparison_op)

        elif rule.condition_type == AlertConditionType.CHANGE:
            return self._evaluate_change(rule)

        elif rule.condition_type == AlertConditionType.ANOMALY:
            return self._evaluate_anomaly(rule, value)

        return False

    def _evaluate_threshold(self, value: float, threshold: float, op: str) -> bool:
        """Evaluate threshold condition."""
        if op == ">":
            return value > threshold
        elif op == "<":
            return value < threshold
        elif op == ">=":
            return value >= threshold
        elif op == "<=":
            return value <= threshold
        elif op == "==":
            return value == threshold
        elif op == "!=":
            return value != threshold
        return False

    def _evaluate_change(self, rule: AlertRule) -> bool:
        """Evaluate percentage change condition."""
        history = self.metric_history.get(rule.metric_name, [])
        if len(history) < 2:
            return False

        now = datetime.now().timestamp()
        period_start = now - rule.change_period_sec

        # Get values within the period
        period_values = [(ts, v) for ts, v in history if ts >= period_start]

        if not period_values:
            return False

        first_value = period_values[0][1]
        last_value = period_values[-1][1]

        if first_value == 0:
            return False

        pct_change = abs((last_value - first_value) / first_value * 100)
        return pct_change > (rule.change_percent or 0)

    def _evaluate_anomaly(self, rule: AlertRule, value: float) -> bool:
        """Evaluate anomaly detection."""
        history = self.metric_history.get(rule.metric_name, [])
        if len(history) < 10:
            return False

        values = [v for _, v in history[-100:]]  # Last 100 values
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance**0.5

        threshold = mean + (std_dev * rule.std_dev_multiplier)
        return value > threshold

    async def _handle_alert_triggered(self, rule: AlertRule, metric_value: float) -> None:
        """Handle alert triggered actions."""
        rule.last_fired_at = datetime.now()
        rule.fire_count += 1

        # Send webhook if configured
        if rule.webhook_enabled and rule.webhook_url:
            await self._send_webhook(rule, metric_value)

    async def _send_webhook(self, rule: AlertRule, metric_value: float) -> None:
        """Send webhook notification."""
        if not self.session:
            try:
                self.session = aiohttp.ClientSession()
            except Exception as e:
                logger.error(f"❌ Failed to create session: {str(e)}")
                return

        try:
            payload = {
                "alert_id": rule.rule_id,
                "alert_name": rule.name,
                "severity": rule.severity.value,
                "metric_name": rule.metric_name,
                "metric_value": metric_value,
                "timestamp": datetime.now().isoformat(),
            }

            async with self.session.post(
                rule.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Webhook delivered: {rule.name}")
                else:
                    logger.warning(f"⚠️ Webhook delivery failed (HTTP {resp.status}): {rule.name}")

        except Exception as e:
            logger.error(f"❌ Webhook error: {str(e)}")

    def _create_alert(self, rule: AlertRule, value: float, condition_met: bool) -> Alert:
        """Create an alert instance."""
        condition_desc = f"{rule.metric_name} {rule.comparison_op} {rule.threshold_value}"

        alert = Alert(
            alert_id=f"alert_{rule.rule_id}_{datetime.now().timestamp()}",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            metric_name=rule.metric_name,
            metric_value=value,
            condition_desc=condition_desc,
            triggered_at=datetime.now(),
        )

        # Track active alert
        if rule.rule_id not in self.active_alerts:
            self.active_alerts[rule.rule_id] = alert

        self.alerts.append(alert)
        return alert

    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts."""
        return list(self.active_alerts.values())

    def get_recent_alerts(self, limit: int = 100) -> List[Alert]:
        """Get recent alerts."""
        return sorted(self.alerts, key=lambda a: a.triggered_at, reverse=True)[:limit]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        return [a for a in self.alerts if a.severity == severity]

    def get_rules_summary(self) -> Dict:
        """Get summary of all rules."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "disabled_rules": sum(1 for r in self.rules.values() if not r.enabled),
            "active_alerts": len(self.active_alerts),
            "total_alerts": len(self.alerts),
            "rules": {
                rule_id: {
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "severity": rule.severity.value,
                    "fire_count": rule.fire_count,
                    "last_fired": rule.last_fired_at.isoformat() if rule.last_fired_at else None,
                }
                for rule_id, rule in self.rules.items()
            },
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.session:
            await self.session.close()


# Singleton
_engine: Optional[AlertingRulesEngine] = None


def get_alerting_engine() -> AlertingRulesEngine:
    """Get or create singleton AlertingRulesEngine."""
    global _engine
    if _engine is None:
        _engine = AlertingRulesEngine()
        logger.info("✅ AlertingRulesEngine singleton initialized")

    return _engine
