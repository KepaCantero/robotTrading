"""
T18.2: Advanced Alerting System Package

Provides rule-based alerting with webhook/email/Slack/Discord integration:
- Alert rule engine for metric evaluation
- Alert manager for state machine and deduplication
- Notification dispatcher for multi-channel delivery
"""

from .alert_manager import AlertManager
from .alert_rule_engine import AlertRuleEngine
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
from .notification_channels import NotificationDispatcher

__all__ = [
    # Services
    "AlertRuleEngine",
    "AlertManager",
    "NotificationDispatcher",
    # Models
    "AlertRule",
    "AlertEvent",
    "AlertHistory",
    "AlertSeverity",
    "AlertState",
    "ThresholdRule",
    "ChangeRule",
    "ComparisonOperator",
    "LogicOperator",
    "NotificationChannelType",
    "NotificationTarget",
]

__version__ = "1.0.0"
__author__ = "MAESTRO Team"
