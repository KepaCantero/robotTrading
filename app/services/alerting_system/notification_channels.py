"""
T18.2: Notification Channels - Multi-channel notification delivery

Supports:
- Webhooks (HTTP POST)
- Email (SMTP)
- Slack
- Discord
"""

import asyncio
import logging

from .models import NotificationChannelType, NotificationPayload, NotificationTarget

logger = logging.getLogger(__name__)


class NotificationChannel:
    """Base class for notification channels."""

    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        """
        Send notification.

        Args:
            target: NotificationTarget with endpoint config
            payload: NotificationPayload to send

        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError


class WebhookChannel(NotificationChannel):
    """HTTP Webhook notification channel."""

    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        """Send notification via webhook."""
        if not target.enabled:
            logger.debug(f"Webhook channel disabled: {target.endpoint}")
            return False

        try:
            import httpx

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "AlgoTrading-AlertSystem/1.0",
            }
            headers.update(target.headers)

            data = payload.to_dict()

            async with httpx.AsyncClient(timeout=target.timeout_seconds) as client:
                response = await client.post(
                    target.endpoint,
                    json=data,
                    headers=headers,
                )

                if response.status_code in [200, 201, 202, 204]:
                    logger.info(
                        f"Webhook sent successfully: {target.endpoint} "
                        f"(status: {response.status_code})"
                    )
                    return True
                else:
                    logger.warning(
                        f"Webhook failed: {target.endpoint} " f"(status: {response.status_code})"
                    )
                    return False

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Webhook error: {target.endpoint} - {e}")
            return False


class EmailChannel(NotificationChannel):
    """Email notification channel using SMTP."""

    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        """
        Send notification via email using SMTP.

        Supports configuration via target.headers:
            - smtp_host: SMTP server hostname (default: localhost)
            - smtp_port: SMTP port (default: 587)
            - smtp_user: SMTP username for authentication
            - smtp_password: SMTP password
            - smtp_use_tls: Whether to use TLS (default: True)
            - from_address: Sender email address

        Args:
            target: NotificationTarget with email endpoint and SMTP config
            payload: NotificationPayload to send

        Returns:
            bool: True if email sent successfully
        """
        if not target.enabled:
            logger.debug(f"Email channel disabled: {target.endpoint}")
            return False

        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        import aiosmtplib  # type: ignore # pylint: disable=import-error

        try:
            # Extract SMTP configuration from target headers
            smtp_host = target.headers.get("smtp_host", "localhost")
            smtp_port = int(target.headers.get("smtp_port", 587))
            smtp_user = target.headers.get("smtp_user", "")
            smtp_password = target.headers.get("smtp_password", "")
            smtp_use_tls = target.headers.get("smtp_use_tls", "true").lower() == "true"
            from_address = target.headers.get("from_address", "alerts@algotrading.local")

            # Build email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{payload.severity.value.upper()}] {payload.rule_name}"
            msg["From"] = from_address
            msg["To"] = target.endpoint

            # Plain text version
            text_content = f"""
AlgoTrading Alert System
========================

Rule: {payload.rule_name}
Severity: {payload.severity.value.upper()}
Time: {payload.triggered_at.isoformat()}

Message: {payload.message}

Metric: {payload.metric_name}
Value: {payload.metric_value}
Symbol: {payload.symbol or 'N/A'}

---
This is an automated alert from the AlgoTrading system.
            """

            # HTML version
            severity_colors = {
                "info": "#17a2b8",
                "warning": "#ffc107",
                "critical": "#dc3545",
            }
            severity_color = severity_colors.get(payload.severity.value, "#6c757d")

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ background-color: {severity_color}; color: white; padding: 15px; }}
        .content {{ padding: 20px; }}
        .metric {{ background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid {severity_color}; }}
        .footer {{ font-size: 12px; color: #6c757d; padding: 10px; border-top: 1px solid #dee2e6; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🚨 {payload.rule_name}</h2>
        <span>Severity: {payload.severity.value.upper()}</span>
    </div>
    <div class="content">
        <p><strong>Message:</strong> {payload.message}</p>
        <div class="metric">
            <p><strong>Metric:</strong> {payload.metric_name}</p>
            <p><strong>Value:</strong> {payload.metric_value}</p>
            <p><strong>Symbol:</strong> {payload.symbol or 'N/A'}</p>
        </div>
        <p><strong>Time:</strong> {payload.triggered_at.isoformat()}</p>
    </div>
    <div class="footer">
        <p>This is an automated alert from the AlgoTrading Alert System.</p>
    </div>
</body>
</html>
            """

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send email
            if smtp_user and smtp_password:
                # Authenticated SMTP
                await aiosmtplib.send(
                    msg,
                    hostname=smtp_host,
                    port=smtp_port,
                    username=smtp_user,
                    password=smtp_password,
                    start_tls=smtp_use_tls,
                    timeout=target.timeout_seconds,
                )
            else:
                # Unauthenticated SMTP (local relay)
                await aiosmtplib.send(
                    msg,
                    hostname=smtp_host,
                    port=smtp_port,
                    start_tls=False,
                    timeout=target.timeout_seconds,
                )

            logger.info(f"✅ Email sent to: {target.endpoint}")
            return True

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Email error: {target.endpoint} - {e}")
            return False


class SlackChannel(NotificationChannel):
    """Slack notification channel."""

    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        """Send notification via Slack."""
        if not target.enabled:
            logger.debug(f"Slack channel disabled: {target.endpoint}")
            return False

        try:
            import httpx

            # Format message for Slack
            color_map = {
                "info": "#36a64",
                "warning": "#ff9900",
                "critical": "#ff0000",
            }

            slack_payload = {
                "text": payload.message,
                "attachments": [
                    {
                        "color": color_map.get(payload.severity.value, "#808080"),
                        "title": payload.rule_name,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": payload.severity.value.upper(),
                                "short": True,
                            },
                            {
                                "title": "Metric",
                                "value": payload.metric_name,
                                "short": True,
                            },
                            {
                                "title": "Value",
                                "value": (
                                    str(payload.metric_value) if payload.metric_value else "N/A"
                                ),
                                "short": True,
                            },
                            {
                                "title": "Symbol",
                                "value": payload.symbol or "N/A",
                                "short": True,
                            },
                        ],
                        "footer": "AlgoTrading Alert System",
                        "ts": int(payload.triggered_at.timestamp()),
                    }
                ],
            }

            async with httpx.AsyncClient(timeout=target.timeout_seconds) as client:
                response = await client.post(
                    target.endpoint,
                    json=slack_payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in [200, 201]:
                    logger.info(f"Slack message sent to: {target.endpoint}")
                    return True
                else:
                    logger.warning(f"Slack send failed (status: {response.status_code})")
                    return False

        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Slack error: {e}")
            return False


class DiscordChannel(NotificationChannel):
    """Discord notification channel."""

    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        """Send notification via Discord."""
        if not target.enabled:
            logger.debug(f"Discord channel disabled: {target.endpoint}")
            return False

        try:
            import httpx

            # Color codes for Discord embeds
            color_map = {
                "info": 3066993,  # Green
                "warning": 15158332,  # Orange
                "critical": 15548997,  # Red
            }

            discord_payload = {
                "content": f"🚨 **{payload.rule_name}**",
                "embeds": [
                    {
                        "title": payload.message,
                        "color": color_map.get(payload.severity.value, 9807270),  # Gray default
                        "fields": [
                            {
                                "name": "Severity",
                                "value": payload.severity.value.upper(),
                                "inline": True,
                            },
                            {
                                "name": "Metric",
                                "value": payload.metric_name,
                                "inline": True,
                            },
                            {
                                "name": "Current Value",
                                "value": (
                                    str(payload.metric_value) if payload.metric_value else "N/A"
                                ),
                                "inline": True,
                            },
                            {
                                "name": "Symbol",
                                "value": payload.symbol or "N/A",
                                "inline": True,
                            },
                        ],
                        "timestamp": payload.triggered_at.isoformat(),
                    }
                ],
            }

            async with httpx.AsyncClient(timeout=target.timeout_seconds) as client:
                response = await client.post(
                    target.endpoint,
                    json=discord_payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in [200, 201, 204]:
                    logger.info(f"Discord message sent to: {target.endpoint}")
                    return True
                else:
                    logger.warning(f"Discord send failed (status: {response.status_code})")
                    return False

        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Discord error: {e}")
            return False


class TelegramChannel(NotificationChannel):
    """Telegram notification channel using Bot API."""

    async def send(self, target: NotificationTarget, payload: NotificationPayload) -> bool:
        """Send notification via Telegram Bot API."""
        if not target.enabled:
            logger.debug(f"Telegram channel disabled")
            return False

        try:
            import httpx

            # Extract bot token and chat_id from headers
            bot_token = target.headers.get("telegram_bot_token", "")
            chat_id = target.headers.get("telegram_chat_id", target.endpoint)

            if not bot_token or not chat_id:
                logger.error("Telegram bot_token or chat_id missing")
                return False

            # Build message with Markdown formatting
            emoji_map = {
                "info": "ℹ️",
                "warning": "⚠️",
                "critical": "🚨",
            }
            emoji = emoji_map.get(payload.severity.value, "📊")

            message = f"{emoji} *{payload.rule_name}*\n\n"
            message += f"*Severity:* {payload.severity.value.upper()}\n"
            message += f"*Message:* {payload.message}\n"
            message += f"*Metric:* {payload.metric_name}\n"

            if payload.metric_value:
                message += f"*Value:* {payload.metric_value}\n"

            if payload.symbol:
                message += f"*Symbol:* {payload.symbol}\n"

            message += f"\n_:{payload.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}_"

            # Send via Telegram Bot API
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            async with httpx.AsyncClient(timeout=target.timeout_seconds) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )

                if response.status_code == 200:
                    logger.info(f"Telegram message sent to chat_id: {chat_id}")
                    return True
                else:
                    logger.warning(
                        f"Telegram send failed (status: {response.status_code}): {response.text}"
                    )
                    return False

        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Telegram error: {e}")
            return False


class NotificationDispatcher:
    """Dispatch notifications to multiple channels."""

    def __init__(self):
        """Initialize dispatcher."""
        self.channels = {
            NotificationChannelType.WEBHOOK: WebhookChannel(),
            NotificationChannelType.EMAIL: EmailChannel(),
            NotificationChannelType.SLACK: SlackChannel(),
            NotificationChannelType.DISCORD: DiscordChannel(),
            NotificationChannelType.TELEGRAM: TelegramChannel(),
        }
        self.notification_stats = {
            "total_sent": 0,
            "total_failed": 0,
            "by_channel": {},
        }

    async def dispatch(
        self, targets: list[NotificationTarget], payload: NotificationPayload
    ) -> int:
        """
        Dispatch notification to multiple targets.

        Args:
            targets: List of NotificationTargets
            payload: NotificationPayload to send

        Returns:
            Number of successful sends
        """
        if not targets:
            logger.debug("No notification targets configured")
            return 0

        # Send to all targets concurrently
        tasks = [self._send_with_retry(target, payload) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        success_count = sum(1 for r in results if r is True)

        # Update stats
        self.notification_stats["total_sent"] += success_count
        self.notification_stats["total_failed"] += len(results) - success_count

        logger.info(f"Notifications dispatched: {success_count}/{len(targets)} successful")

        return success_count

    async def _send_with_retry(
        self, target: NotificationTarget, payload: NotificationPayload
    ) -> bool:
        """Send with retry logic."""
        channel = self.channels.get(target.channel_type)
        if not channel:
            logger.error(f"Unknown channel type: {target.channel_type}")
            return False

        for attempt in range(target.retry_count):
            try:
                success = await channel.send(target, payload)
                if success:
                    return True

                # Wait before retry
                if attempt < target.retry_count - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Retry {attempt + 1} failed: {e}")
                if attempt == target.retry_count - 1:
                    return False

        return False

    def get_dispatcher_stats(self) -> dict:
        """Get dispatcher statistics."""
        return self.notification_stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.notification_stats = {
            "total_sent": 0,
            "total_failed": 0,
            "by_channel": {},
        }
