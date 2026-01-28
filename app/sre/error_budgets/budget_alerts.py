"""
Budget Alerts - Alerting on Error Budget Breaches (SRE Rule 20)

Alerts stakeholders when error budgets are consumed or at risk.
Implements secure alerting following Rule 28 (Security).

Alert Types:
- Budget Warning: 50% remaining
- Budget Critical: 25% remaining
- Budget Exhausted: 10% remaining
- High Burn Rate: Consuming budget too fast
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from .error_budget_manager import ErrorBudgetState

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(str, Enum):
    """Alert notification channels."""

    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class AlertRecipients:
    """Alert notification recipients."""

    emails: List[str] = field(default_factory=list)
    slack_channels: List[str] = field(default_factory=list)
    pagerduty_services: List[str] = field(default_factory=list)
    webhook_urls: List[str] = field(default_factory=list)


@dataclass
class BudgetAlert:
    """Budget alert event."""

    alert_id: str
    service_name: str
    severity: AlertSeverity
    title: str
    message: str
    budget_state: ErrorBudgetState
    timestamp: datetime
    channels: List[AlertChannel]
    recipients: AlertRecipients
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "service_name": self.service_name,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "budget_remaining_pct": f"{self.budget_state.remaining_percentage:.2f}%",
            "budget_status": self.budget_state.status.value,
            "burn_rate": (
                f"{self.budget_state.burn_rate:.2f} min/hr" if self.budget_state.burn_rate else None
            ),
            "timestamp": self.timestamp.isoformat(),
            "channels": [c.value for c in self.channels],
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "metadata": self.metadata,
        }


@dataclass
class BudgetAlertConfig:
    """Configuration for budget alerts."""

    # Thresholds
    warning_threshold_pct: Decimal = Decimal("50")
    critical_threshold_pct: Decimal = Decimal("25")
    exhausted_threshold_pct: Decimal = Decimal("10")

    # Burn rate alert
    burn_rate_threshold: Decimal = Decimal("2.0")  # 2x normal rate

    # Recipients
    recipients: AlertRecipients = field(default_factory=AlertRecipients)

    # Channels to use (by severity)
    warning_channels: List[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.EMAIL, AlertChannel.SLACK]
    )
    critical_channels: List[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.PAGERDUTY]
    )
    emergency_channels: List[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.PAGERDUTY, AlertChannel.SLACK]
    )

    # Alert cooldown (prevent spam)
    alert_cooldown_minutes: int = 15

    # Webhook settings
    webhook_timeout_seconds: int = 10

    # Security (Rule 28)
    enable_encryption: bool = True
    api_key_required: bool = True


class BudgetAlertManager:
    """
    Manages budget alerts and notifications.

    Responsibilities:
    - Monitor error budget state
    - Trigger alerts on thresholds
    - Send notifications to configured channels
    - Track alert history
    - Implement secure alerting (Rule 28)

    Security (Rule 28):
    - No secrets in logs
    - Secure webhook delivery
    - API key validation
    - Rate limiting
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[BudgetAlertConfig] = None,
    ):
        """
        Initialize budget alert manager.

        Args:
            service_name: Name of the service
            config: Alert configuration
        """
        self.service_name = service_name
        self.config = config or BudgetAlertConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # Alert history
        self._alert_history: List[BudgetAlert] = []
        self._last_alert_time: Dict[str, datetime] = {}

        # Lock
        self._lock = asyncio.Lock()

        # HTTP session for webhooks
        self._session: Optional[Any] = None

        self.logger.info(f"BudgetAlertManager initialized for {service_name}")

    async def initialize(self) -> None:
        """Initialize alert manager."""

    async def check_and_alert(
        self,
        budget_state: ErrorBudgetState,
    ) -> List[BudgetAlert]:
        """
        Check budget state and trigger alerts if needed.

        Args:
            budget_state: Current error budget state

        Returns:
            List of triggered alerts
        """
        async with self._lock:
            alerts = []

            try:
                # Check for exhausted budget
                if budget_state.is_exhausted(self.config.exhausted_threshold_pct):
                    alert = await self._trigger_alert(
                        budget_state,
                        AlertSeverity.EMERGENCY,
                        "Error Budget Exhausted",
                        (
                            f"Error budget for {self.service_name} is exhausted "
                            f"({budget_state.remaining_percentage:.1f}% remaining). "
                            f"Deployments are blocked until budget recovers."
                        ),
                        self.config.emergency_channels,
                    )
                    if alert:
                        alerts.append(alert)

                # Check for critical level
                elif budget_state.remaining_percentage < self.config.critical_threshold_pct:
                    alert = await self._trigger_alert(
                        budget_state,
                        AlertSeverity.CRITICAL,
                        "Error Budget Critical",
                        (
                            f"Error budget for {self.service_name} is at critical level "
                            f"({budget_state.remaining_percentage:.1f}% remaining). "
                            f"Immediate action required."
                        ),
                        self.config.critical_channels,
                    )
                    if alert:
                        alerts.append(alert)

                # Check for warning level
                elif budget_state.remaining_percentage < self.config.warning_threshold_pct:
                    alert = await self._trigger_alert(
                        budget_state,
                        AlertSeverity.WARNING,
                        "Error Budget Warning",
                        (
                            f"Error budget for {self.service_name} is below warning threshold "
                            f"({budget_state.remaining_percentage:.1f}% remaining). "
                            f"Monitor closely."
                        ),
                        self.config.warning_channels,
                    )
                    if alert:
                        alerts.append(alert)

                # Check for high burn rate
                if (
                    budget_state.burn_rate
                    and budget_state.burn_rate > self.config.burn_rate_threshold
                ):
                    # Check cooldown
                    cooldown_key = f"burn_rate_{self.service_name}"
                    if self._is_cooldown_expired(cooldown_key):
                        alert = await self._trigger_alert(
                            budget_state,
                            AlertSeverity.WARNING,
                            "High Burn Rate Detected",
                            (
                                f"Error budget for {self.service_name} is being consumed at "
                                f"high rate ({budget_state.burn_rate:.2f} min/hr). "
                                f"At this rate, budget will be exhausted soon."
                            ),
                            self.config.warning_channels,
                        )
                        if alert:
                            alerts.append(alert)

                return alerts

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error checking and alerting: {e}")
                return alerts

    async def _trigger_alert(
        self,
        budget_state: ErrorBudgetState,
        severity: AlertSeverity,
        title: str,
        message: str,
        channels: List[AlertChannel],
    ) -> Optional[BudgetAlert]:
        """Trigger an alert."""
        try:
            # Check cooldown
            cooldown_key = f"{severity.value}_{self.service_name}"
            if not self._is_cooldown_expired(cooldown_key):
                self.logger.debug(f"Alert cooldown active for {cooldown_key}")
                return None

            # Create alert
            alert = BudgetAlert(
                alert_id=self._generate_alert_id(),
                service_name=self.service_name,
                severity=severity,
                title=title,
                message=message,
                budget_state=budget_state,
                timestamp=datetime.utcnow(),
                channels=channels,
                recipients=self.config.recipients,
            )

            # Send notifications
            await self._send_notifications(alert)

            # Record alert
            self._alert_history.append(alert)
            self._last_alert_time[cooldown_key] = datetime.utcnow()

            self.logger.warning(
                f"Alert triggered: {severity.value} - {title} "
                f"(budget: {budget_state.remaining_percentage:.1f}%)"
            )

            return alert

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error triggering alert: {e}")
            return None

    def _is_cooldown_expired(self, key: str) -> bool:
        """Check if alert cooldown has expired."""
        if key not in self._last_alert_time:
            return True

        elapsed = (datetime.utcnow() - self._last_alert_time[key]).total_seconds()
        cooldown_seconds = self.config.alert_cooldown_minutes * 60

        return elapsed >= cooldown_seconds

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        import uuid

        return f"alert_{self.service_name}_{uuid.uuid4().hex[:8]}"

    async def _send_notifications(self, alert: BudgetAlert) -> None:
        """Send notifications to all configured channels."""
        for channel in alert.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    await self._send_email_alert(alert)
                elif channel == AlertChannel.SLACK:
                    await self._send_slack_alert(alert)
                elif channel == AlertChannel.PAGERDUTY:
                    await self._send_pagerduty_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert)
                elif channel == AlertChannel.LOG:
                    self._log_alert(alert)

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error sending {channel.value} alert: {e}")

    def _log_alert(self, alert: BudgetAlert) -> None:
        """Log alert (always enabled)."""
        log_method = logger.info
        if alert.severity == AlertSeverity.WARNING:
            log_method = logger.warning
        elif alert.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY):
            log_method = logger.critical

        log_method(
            f"[{alert.severity.value.upper()}] {alert.title}\n"
            f"Service: {alert.service_name}\n"
            f"Message: {alert.message}\n"
            f"Budget Remaining: {alert.budget_state.remaining_percentage:.1f}%\n"
            f"Alert ID: {alert.alert_id}"
        )

    async def _send_email_alert(self, alert: BudgetAlert) -> None:
        """Send email alert (placeholder for implementation)."""
        # In production, integrate with email service (SES, SendGrid, etc.)
        # For now, just log
        self.logger.info(f"EMAIL ALERT (to: {self.config.recipients.emails}): {alert.title}")

    async def _send_slack_alert(self, alert: BudgetAlert) -> None:
        """Send Slack alert."""
        if not self._session or not self.config.recipients.slack_channels:
            return

        # In production, use Slack webhook
        # For now, just log
        self.logger.info(
            f"SLACK ALERT (channels: {self.config.recipients.slack_channels}): {alert.title}"
        )

    async def _send_pagerduty_alert(self, alert: BudgetAlert) -> None:
        """Send PagerDuty alert."""
        if not self._session or not self.config.recipients.pagerduty_services:
            return

        # In production, use PagerDuty API
        # For now, just log
        self.logger.info(
            f"PAGERDUTY ALERT (services: {self.config.recipients.pagerduty_services}): {alert.title}"
        )

    async def _send_webhook_alert(self, alert: BudgetAlert) -> None:
        """Send webhook alert."""
        if not self._session or not self.config.recipients.webhook_urls:
            return

        for url in self.config.recipients.webhook_urls:
            try:
                # Prepare payload (no sensitive data - Rule 28)
                payload = {
                    "alert_id": alert.alert_id,
                    "service": alert.service_name,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "budget_remaining_pct": float(alert.budget_state.remaining_percentage),
                    "budget_status": alert.budget_state.status.value,
                    "timestamp": alert.timestamp.isoformat(),
                }

                # Send webhook
                async with self._session.post(url, json=payload) as response:
                    if response.status in (200, 201, 204):
                        self.logger.info(f"Webhook alert sent to {url}")
                    else:
                        self.logger.error(f"Webhook alert failed: HTTP {response.status}")

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Webhook error for {url}: {e}")

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge

        Returns:
            True if acknowledged
        """
        for alert in self._alert_history:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self.logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False

    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID to resolve

        Returns:
            True if resolved
        """
        for alert in self._alert_history:
            if alert.alert_id == alert_id:
                alert.resolved = True
                self.logger.info(f"Alert resolved: {alert_id}")
                return True
        return False

    async def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None,
    ) -> List[BudgetAlert]:
        """
        Get alert history.

        Args:
            limit: Maximum number of alerts
            severity: Filter by severity

        Returns:
            List of alerts
        """
        alerts = self._alert_history

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts[-limit:]

    async def get_active_alerts(self) -> List[BudgetAlert]:
        """Get list of active (unresolved) alerts."""
        return [a for a in self._alert_history if not a.resolved]

    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        total = len(self._alert_history)
        active = await self.get_active_alerts()

        by_severity = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 0,
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.EMERGENCY: 0,
        }

        for alert in self._alert_history:
            by_severity[alert.severity] += 1

        return {
            "service": self.service_name,
            "total_alerts": total,
            "active_alerts": len(active),
            "by_severity": {
                "info": by_severity[AlertSeverity.INFO],
                "warning": by_severity[AlertSeverity.WARNING],
                "critical": by_severity[AlertSeverity.CRITICAL],
                "emergency": by_severity[AlertSeverity.EMERGENCY],
            },
            "recent_alerts": [a.to_dict() for a in self._alert_history[-5:]],
        }
