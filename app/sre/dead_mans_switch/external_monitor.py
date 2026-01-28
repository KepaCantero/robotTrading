"""
External Monitor - Third-Party Health Check Monitoring

Provides external monitoring service for dead man's switch.
Can be hosted separately from the main service for independence.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class AlertChannel(str, Enum):
    """Types of alert channels."""

    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    TWILIO = "twilio"
    WEBHOOK = "webhook"


@dataclass
class MonitorConfig:
    """Configuration for external monitor."""

    # Service to monitor
    service_name: str
    health_check_url: str
    expected_status_code: int = 200

    # Monitoring interval
    check_interval_seconds: int = 60
    timeout_seconds: int = 30

    # Failure detection
    max_consecutive_failures: int = 3
    alert_after_minutes: int = 5  # Alert after N minutes of failures

    # Alert channels
    alert_channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.EMAIL])

    # Channel configs
    email_config: Dict[str, Any] = field(default_factory=dict)
    slack_config: Dict[str, Any] = field(default_factory=dict)
    pagerduty_config: Dict[str, Any] = field(default_factory=dict)
    twilio_config: Dict[str, Any] = field(default_factory=dict)
    webhook_config: Dict[str, Any] = field(default_factory=dict)

    # Database
    db_path: str = "data/external_monitor.db"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "health_check_url": self.health_check_url,
            "expected_status_code": self.expected_status_code,
            "check_interval_seconds": self.check_interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "max_consecutive_failures": self.max_consecutive_failures,
            "alert_after_minutes": self.alert_after_minutes,
            "alert_channels": [c.value for c in self.alert_channels],
        }


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    timestamp: datetime
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "consecutive_failures": self.consecutive_failures,
        }


class ExternalMonitor:
    """
    External health check monitor.

    Responsibilities:
    - Periodic health checks of service
    - Failure detection and alerting
    - Independent monitoring (separate from service)
    - Multiple alert channel support

    Usage:
        monitor = ExternalMonitor(config)
        await monitor.start()

        # Runs in background, checking health periodically
    """

    def __init__(
        self,
        config: MonitorConfig,
    ):
        """
        Initialize external monitor.

        Args:
            config: Monitor configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.service_name}")

        # State
        self._running = False
        self._consecutive_failures = 0
        self._last_failure_time: Optional[datetime] = None
        self._alert_sent = False

        # History
        self._check_history: List[HealthCheckResult] = []

        # Task
        self._monitor_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize external monitor."""
        try:
            await self._init_database()
            self.logger.info("ExternalMonitor initialized")
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error initializing: {e}")
            raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS health_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        success INTEGER NOT NULL,
                        status_code INTEGER,
                        response_time_ms REAL,
                        error_message TEXT,
                        consecutive_failures INTEGER NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """)

                await db.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        sent_at TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        success INTEGER NOT NULL,
                        error_message TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """)

                # Indexes
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_health_checks_service_timestamp
                    ON health_checks(service_name, timestamp)
                """)

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def start(self) -> None:
        """Start external monitoring."""
        if self._running:
            self.logger.warning("Monitor already running")
            return

        self._running = True
        self.logger.info("Starting external monitor")

        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop external monitoring."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Stopped external monitor")

    async def _monitor_loop(self) -> None:
        """Monitor loop."""
        while self._running:
            try:
                # Perform health check
                result = await self._perform_health_check()
                self._check_history.append(result)

                # Save to database
                await self._save_health_check(result)

                # Handle failures
                if not result.success:
                    self._consecutive_failures += 1
                    self._last_failure_time = result.timestamp

                    # Check if we should alert
                    await self._check_alert_conditions(result)

                else:
                    self._consecutive_failures = 0
                    self._alert_sent = False

                # Trim history
                if len(self._check_history) > 1000:
                    self._check_history = self._check_history[-500:]

                # Wait before next check
                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")

    async def _perform_health_check(self) -> HealthCheckResult:
        """Perform health check."""
        start_time = datetime.utcnow()

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.health_check_url,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    await response.read()

                    success = response.status == self.config.expected_status_code

                    return HealthCheckResult(
                        timestamp=start_time,
                        success=success,
                        status_code=response.status,
                        response_time_ms=response_time,
                        consecutive_failures=0 if success else self._consecutive_failures + 1,
                    )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                timestamp=start_time,
                success=False,
                error_message=f"Timeout after {self.config.timeout_seconds}s",
                consecutive_failures=self._consecutive_failures + 1,
            )

        except Exception as e:
            return HealthCheckResult(
                timestamp=start_time,
                success=False,
                error_message=str(e),
                consecutive_failures=self._consecutive_failures + 1,
            )

    async def _check_alert_conditions(self, result: HealthCheckResult) -> None:
        """Check if alert should be sent."""
        # Already alerted
        if self._alert_sent:
            return

        # Check consecutive failures
        if self._consecutive_failures >= self.config.max_consecutive_failures:
            await self._send_alert(result)
            return

        # Check time-based alert
        if self._last_failure_time:
            time_since_failure = (datetime.utcnow() - self._last_failure_time).total_seconds()

            if time_since_failure >= self.config.alert_after_minutes * 60:
                await self._send_alert(result)
                return

    async def _send_alert(self, result: HealthCheckResult) -> None:
        """Send alert to configured channels."""
        self.logger.critical(
            f"SERVICE DOWN: {self.config.service_name} "
            f"({self._consecutive_failures} consecutive failures)"
        )

        self._alert_sent = True

        for channel in self.config.alert_channels:
            try:
                success = await self._send_alert_to_channel(channel, result)

                # Save alert
                await self._save_alert(channel, success, None if success else "Failed to send")

            except Exception as e:
                self.logger.error(f"Error sending alert to {channel.value}: {e}")
                await self._save_alert(channel, False, str(e))

    async def _send_alert_to_channel(
        self,
        channel: AlertChannel,
        result: HealthCheckResult,
    ) -> bool:
        """Send alert to specific channel."""
        if channel == AlertChannel.EMAIL:
            return await self._send_email_alert(result)

        elif channel == AlertChannel.SLACK:
            return await self._send_slack_alert(result)

        elif channel == AlertChannel.PAGERDUTY:
            return await self._send_pagerduty_alert(result)

        elif channel == AlertChannel.TWILIO:
            return await self._send_twilio_alert(result)

        elif channel == AlertChannel.WEBHOOK:
            return await self._send_webhook_alert(result)

        return False

    async def _send_email_alert(self, result: HealthCheckResult) -> bool:
        """Send email alert."""
        # Placeholder implementation
        # In production, use SMTP or email service
        self.logger.info(f"EMAIL ALERT: Service {self.config.service_name} is down")
        return True

    async def _send_slack_alert(self, result: HealthCheckResult) -> bool:
        """Send Slack alert."""
        webhook_url = self.config.slack_config.get("webhook_url")

        if not webhook_url:
            self.logger.warning("Slack webhook URL not configured")
            return False

        try:
            import aiohttp

            message = {
                "text": f"🚨 *SERVICE DOWN*: {self.config.service_name}",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🚨 SERVICE DOWN: {self.config.service_name}",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Consecutive Failures:*\n{self._consecutive_failures}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Last Error:*\n{result.error_message or 'Unknown'}",
                            },
                        ],
                    },
                ],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=message) as response:
                    return response.status == 200

        except Exception as e:
            self.logger.error(f"Error sending Slack alert: {e}")
            return False

    async def _send_pagerduty_alert(self, result: HealthCheckResult) -> bool:
        """Send PagerDuty alert."""
        # Placeholder implementation
        self.logger.info(f"PAGERDUTY ALERT: Service {self.config.service_name} is down")
        return True

    async def _send_twilio_alert(self, result: HealthCheckResult) -> bool:
        """Send Twilio SMS alert."""
        # Placeholder implementation
        self.logger.info(f"TWILIO ALERT: Service {self.config.service_name} is down")
        return True

    async def _send_webhook_alert(self, result: HealthCheckResult) -> bool:
        """Send webhook alert."""
        webhook_url = self.config.webhook_config.get("url")

        if not webhook_url:
            self.logger.warning("Webhook URL not configured")
            return False

        try:
            import aiohttp

            payload = {
                "service": self.config.service_name,
                "status": "down",
                "consecutive_failures": self._consecutive_failures,
                "error": result.error_message,
                "timestamp": result.timestamp.isoformat(),
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200

        except Exception as e:
            self.logger.error(f"Error sending webhook alert: {e}")
            return False

    async def _save_health_check(self, result: HealthCheckResult) -> None:
        """Save health check to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO health_checks
                    (service_name, timestamp, success, status_code, response_time_ms,
                     error_message, consecutive_failures)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.config.service_name,
                        result.timestamp.isoformat(),
                        1 if result.success else 0,
                        result.status_code,
                        result.response_time_ms,
                        result.error_message,
                        result.consecutive_failures,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving health check: {e}")

    async def _save_alert(
        self,
        channel: AlertChannel,
        success: bool,
        error_message: Optional[str],
    ) -> None:
        """Save alert to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO alerts
                    (service_name, sent_at, channel, success, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        self.config.service_name,
                        datetime.utcnow().isoformat(),
                        channel.value,
                        1 if success else 0,
                        error_message,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving alert: {e}")

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    @property
    def consecutive_failures(self) -> int:
        """Get consecutive failure count."""
        return self._consecutive_failures

    def get_summary(self) -> Dict[str, Any]:
        """Get monitor summary."""
        success_count = sum(1 for c in self._check_history if c.success)
        total_count = len(self._check_history)

        return {
            "service": self.config.service_name,
            "running": self._running,
            "consecutive_failures": self._consecutive_failures,
            "last_check": self._check_history[-1].to_dict() if self._check_history else None,
            "uptime_pct": (
                f"{(success_count / total_count * 100):.1f}%" if total_count > 0 else "N/A"
            ),
            "total_checks": total_count,
            "alert_sent": self._alert_sent,
        }
