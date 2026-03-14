"""
T18.2: Advanced Alerting System Models

Data models for alert rules, events, and notification targets.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """Alert state machine states."""

    TRIGGERED = "triggered"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED_ACKNOWLEDGED = "resolved_acknowledged"


class ComparisonOperator(str, Enum):
    """Comparison operators for threshold-based rules."""

    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="


class LogicOperator(str, Enum):
    """Logic operators for rule composition."""

    AND = "and"
    OR = "or"


class NotificationChannelType(str, Enum):
    """Supported notification channels."""

    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


@dataclass
class NotificationTarget:
    """Configuration for a notification channel."""

    channel_type: NotificationChannelType
    endpoint: str  # URL for webhook, email for EMAIL, channel ID for Slack/Discord
    enabled: bool = True
    retry_count: int = 3
    timeout_seconds: int = 10
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "channel_type": self.channel_type.value,
            "endpoint": self.endpoint,
            "enabled": self.enabled,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "headers": self.headers,
            "metadata": self.metadata,
        }


@dataclass
class ThresholdRule:
    """Single threshold-based rule."""

    metric_name: str
    operator: ComparisonOperator
    threshold: Decimal
    symbol: Optional[str] = None  # Optional symbol filter
    portfolio_id: Optional[str] = None

    def evaluate(self, value: Decimal) -> bool:
        """Evaluate metric against threshold."""
        logger.debug(
            "Evaluating threshold rule",
            extra={
                "metric_name": self.metric_name,
                "operator": self.operator.value,
                "threshold": str(self.threshold),
                "value": str(value),
                "operation": "threshold_evaluate",
            },
        )
        if self.operator == ComparisonOperator.GREATER_THAN:
            result = value > self.threshold
        elif self.operator == ComparisonOperator.GREATER_THAN_OR_EQUAL:
            result = value >= self.threshold
        elif self.operator == ComparisonOperator.LESS_THAN:
            result = value < self.threshold
        elif self.operator == ComparisonOperator.LESS_THAN_OR_EQUAL:
            result = value <= self.threshold
        elif self.operator == ComparisonOperator.EQUAL:
            result = value == self.threshold
        elif self.operator == ComparisonOperator.NOT_EQUAL:
            result = value != self.threshold
        else:
            result = False

        logger.debug(
            "Threshold rule evaluation result",
            extra={"metric_name": self.metric_name, "triggered": result, "symbol": self.symbol},
        )
        return result

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "operator": self.operator.value,
            "threshold": str(self.threshold),
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
        }


@dataclass
class ChangeRule:
    """Percentage change rule over time window."""

    metric_name: str
    change_percent: Decimal  # Trigger if change > this percentage
    window_minutes: int  # Time window to measure change
    symbol: Optional[str] = None
    portfolio_id: Optional[str] = None
    direction: str = "any"  # "up", "down", or "any"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "change_percent": str(self.change_percent),
            "window_minutes": self.window_minutes,
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "direction": self.direction,
        }


@dataclass
class AlertRule:
    """Alert rule definition."""

    rule_id: str
    name: str
    description: str
    severity: AlertSeverity
    enabled: bool = True

    # Rule composition
    threshold_rules: List[ThresholdRule] = field(default_factory=list)
    change_rules: List[ChangeRule] = field(default_factory=list)
    logic_operator: LogicOperator = LogicOperator.OR

    # Notification configuration
    notification_targets: List[NotificationTarget] = field(default_factory=list)

    # De-duplication
    deduplicate_minutes: int = 5  # Don't trigger same alert within N minutes

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "threshold_rules": [r.to_dict() for r in self.threshold_rules],
            "change_rules": [r.to_dict() for r in self.change_rules],
            "logic_operator": self.logic_operator.value,
            "notification_targets": [t.to_dict() for t in self.notification_targets],
            "deduplicate_minutes": self.deduplicate_minutes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
        }


@dataclass
class AlertEvent:
    """Alert event triggered by rule."""

    event_id: str
    rule_id: str
    severity: AlertSeverity
    state: AlertState = AlertState.TRIGGERED

    # Context
    metric_name: str = ""
    metric_value: Optional[Decimal] = None
    symbol: Optional[str] = None
    portfolio_id: Optional[str] = None

    # Timeline
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None

    # Message
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Notifications sent
    notifications_sent: int = 0
    last_notification_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "state": self.state.value,
            "metric_name": self.metric_name,
            "metric_value": str(self.metric_value) if self.metric_value else None,
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "message": self.message,
            "details": self.details,
            "notifications_sent": self.notifications_sent,
            "last_notification_at": (
                self.last_notification_at.isoformat() if self.last_notification_at else None
            ),
        }


@dataclass
class AlertHistory:
    """Alert history entry."""

    history_id: str
    event_id: str
    rule_id: str
    action: str  # "triggered", "resolved", "acknowledged", "notification_sent"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "history_id": self.history_id,
            "event_id": self.event_id,
            "rule_id": self.rule_id,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class AlertEvaluationContext:
    """Context for alert rule evaluation."""

    metric_name: str
    current_value: Decimal
    symbol: Optional[str] = None
    portfolio_id: Optional[str] = None
    previous_value: Optional[Decimal] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    window_data: List[Decimal] = field(default_factory=list)  # Historical values for window

    def calculate_change_percent(self) -> Optional[Decimal]:
        """Calculate percentage change from first to current value."""
        logger.debug(
            "Calculating change percent",
            extra={
                "metric_name": self.metric_name,
                "window_data_length": len(self.window_data),
                "operation": "calculate_change_percent",
            },
        )
        if not self.window_data or len(self.window_data) < 2:
            logger.debug(
                "Insufficient data for change calculation",
                extra={
                    "metric_name": self.metric_name,
                    "window_data_length": len(self.window_data),
                },
            )
            return None
        first_value = self.window_data[0]
        if first_value == 0:
            logger.debug(
                "First value is zero, cannot calculate change",
                extra={"metric_name": self.metric_name},
            )
            return None
        change = ((self.current_value - first_value) / first_value) * 100
        logger.debug(
            "Change percent calculated",
            extra={
                "metric_name": self.metric_name,
                "change_percent": float(change),
                "first_value": float(first_value),
                "current_value": float(self.current_value),
            },
        )
        return change


@dataclass
class NotificationPayload:
    """Payload for notification delivery."""

    event_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    metric_value: Optional[Decimal] = None
    symbol: Optional[str] = None
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": str(self.metric_value) if self.metric_value else None,
            "symbol": self.symbol,
            "triggered_at": self.triggered_at.isoformat(),
            "details": self.details,
        }
