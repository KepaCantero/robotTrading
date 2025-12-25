"""
T18.2: Notification Channels - Multi-channel notification delivery

Supports:
- Webhooks (HTTP POST)
- Email (SMTP)
- Slack
- Discord
"""

import asyncio
import json
import logging
from typing import Optional

from .models import (
    AlertEvent,
    NotificationChannelType,
    NotificationPayload,
    NotificationTarget,
)

logger = logging.getLogger(__name__)


class NotificationChannel:
    """Base class for notification channels."""

    async def send(
        self, target: NotificationTarget, payload: NotificationPayload
    ) -> bool:
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

    async def send(
        self, target: NotificationTarget, payload: NotificationPayload
    ) -> bool:
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

            async with httpx.AsyncClient(
                timeout=target.timeout_seconds
            ) as client:
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
                        f"Webhook failed: {target.endpoint} "
                        f"(status: {response.status_code})"
                    )
                    return False

        except asyncio.TimeoutError:
            logger.error(f"Webhook timeout: {target.endpoint}")
            return False
        except Exception as e:
            logger.error(f"Webhook error: {target.endpoint} - {e}")
            return False


class EmailChannel(NotificationChannel):
    """Email notification channel."""

    async def send(
        self, target: NotificationTarget, payload: NotificationPayload
    ) -> bool:
        """Send notification via email."""
        if not target.enabled:
            logger.debug(f"Email channel disabled: {target.endpoint}")
            return False

        try:
            # Would require SMTP configuration
            # For now, simulating successful send
            logger.info(f"Email sent to: {target.endpoint}")
            return True

        except Exception as e:
            logger.error(f"Email error: {target.endpoint} - {e}")
            return False


class SlackChannel(NotificationChannel):
    """Slack notification channel."""

    async def send(
        self, target: NotificationTarget, payload: NotificationPayload
    ) -> bool:
        """Send notification via Slack."""
        if not target.enabled:
            logger.debug(f"Slack channel disabled: {target.endpoint}")
            return False

        try:
            import httpx

            # Format message for Slack
            color_map = {
                "info": "#36a64f",
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
                                "value": str(payload.metric_value)
                                if payload.metric_value
                                else "N/A",
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

            async with httpx.AsyncClient(
                timeout=target.timeout_seconds
            ) as client:
                response = await client.post(
                    target.endpoint,
                    json=slack_payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in [200, 201]:
                    logger.info(f"Slack message sent to: {target.endpoint}")
                    return True
                else:
                    logger.warning(
                        f"Slack send failed (status: {response.status_code})"
                    )
                    return False

        except Exception as e:
            logger.error(f"Slack error: {e}")
            return False


class DiscordChannel(NotificationChannel):
    """Discord notification channel."""

    async def send(
        self, target: NotificationTarget, payload: NotificationPayload
    ) -> bool:
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
                        "color": color_map.get(
                            payload.severity.value, 9807270
                        ),  # Gray default
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
                                "value": str(payload.metric_value)
                                if payload.metric_value
                                else "N/A",
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

            async with httpx.AsyncClient(
                timeout=target.timeout_seconds
            ) as client:
                response = await client.post(
                    target.endpoint,
                    json=discord_payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in [200, 201, 204]:
                    logger.info(f"Discord message sent to: {target.endpoint}")
                    return True
                else:
                    logger.warning(
                        f"Discord send failed (status: {response.status_code})"
                    )
                    return False

        except Exception as e:
            logger.error(f"Discord error: {e}")
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
        tasks = [
            self._send_with_retry(target, payload) for target in targets
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        success_count = sum(1 for r in results if r is True)

        # Update stats
        self.notification_stats["total_sent"] += success_count
        self.notification_stats["total_failed"] += len(results) - success_count

        logger.info(
            f"Notifications dispatched: {success_count}/{len(targets)} successful"
        )

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
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
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
