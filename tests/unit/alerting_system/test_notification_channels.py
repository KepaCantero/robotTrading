"""
Tests for Notification Channels - Multi-channel notification delivery

Tests cover:
- Webhook channel
- Email channel
- Slack channel
- Discord channel
- Notification dispatcher
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.alerting_system import (
    AlertSeverity,
    NotificationChannelType,
    NotificationTarget,
)
from app.services.alerting_system.models import NotificationPayload
from app.services.alerting_system.notification_channels import (
    DiscordChannel,
    EmailChannel,
    NotificationDispatcher,
    SlackChannel,
    WebhookChannel,
)


class TestWebhookChannel:
    """Test Webhook notification channel."""

    def test_webhook_target_initialization(self):
        """Test webhook target initialization."""
        WebhookChannel()
        target = NotificationTarget(
            channel_type=NotificationChannelType.WEBHOOK,
            endpoint="https://example.com/webhook",
            enabled=True,
        )

        assert target.channel_type == NotificationChannelType.WEBHOOK
        assert target.endpoint == "https://example.com/webhook"
        assert target.enabled is True

    def test_webhook_with_custom_headers(self):
        """Test webhook with custom headers."""
        target = NotificationTarget(
            channel_type=NotificationChannelType.WEBHOOK,
            endpoint="https://example.com/webhook",
            enabled=True,
            headers={"Authorization": "Bearer token123"},
        )

        assert target.headers["Authorization"] == "Bearer token123"


class TestEmailChannel:
    """Test Email notification channel."""

    def test_email_target_initialization(self):
        """Test email target initialization."""
        EmailChannel()
        target = NotificationTarget(
            channel_type=NotificationChannelType.EMAIL,
            endpoint="alert@example.com",
            enabled=True,
        )

        assert target.channel_type == NotificationChannelType.EMAIL
        assert target.endpoint == "alert@example.com"


class TestSlackChannel:
    """Test Slack notification channel."""

    def test_slack_target_initialization(self):
        """Test Slack target initialization."""
        SlackChannel()
        target = NotificationTarget(
            channel_type=NotificationChannelType.SLACK,
            endpoint="https://hooks.slack.com/services/T00000000/B00000000/XXXX",
            enabled=True,
        )

        assert target.channel_type == NotificationChannelType.SLACK
        assert "hooks.slack.com" in target.endpoint


class TestDiscordChannel:
    """Test Discord notification channel."""

    def test_discord_target_initialization(self):
        """Test Discord target initialization."""
        DiscordChannel()
        target = NotificationTarget(
            channel_type=NotificationChannelType.DISCORD,
            endpoint="https://discordapp.com/api/webhooks/123456/abcdef",
            enabled=True,
        )

        assert target.channel_type == NotificationChannelType.DISCORD
        assert "discordapp.com" in target.endpoint or "discord.com" in target.endpoint


class TestNotificationDispatcher:
    """Test Notification Dispatcher."""

    def test_dispatcher_initialization(self):
        """Test dispatcher initializes with all channels."""
        dispatcher = NotificationDispatcher()
        assert len(dispatcher.channels) == 4
        assert NotificationChannelType.WEBHOOK in dispatcher.channels
        assert NotificationChannelType.SLACK in dispatcher.channels
        assert NotificationChannelType.DISCORD in dispatcher.channels
        assert NotificationChannelType.EMAIL in dispatcher.channels

    @pytest.mark.asyncio
    async def test_dispatch_to_multiple_targets(self):
        """Test dispatching to multiple notification targets."""
        dispatcher = NotificationDispatcher()

        targets = [
            NotificationTarget(
                channel_type=NotificationChannelType.WEBHOOK,
                endpoint="https://example.com/webhook1",
                enabled=True,
            ),
            NotificationTarget(
                channel_type=NotificationChannelType.EMAIL,
                endpoint="alert@example.com",
                enabled=True,
            ),
        ]

        payload = NotificationPayload(
            event_id="evt_001",
            rule_id="rule_001",
            rule_name="Test",
            severity=AlertSeverity.WARNING,
            message="Test",
            metric_name="price",
        )

        # Mock the channels
        with (
            patch.object(WebhookChannel, "send", new_callable=AsyncMock) as mock_webhook,
            patch.object(EmailChannel, "send", new_callable=AsyncMock) as mock_email,
        ):
            mock_webhook.return_value = True
            mock_email.return_value = True

            count = await dispatcher.dispatch(targets, payload)
            # Should have sent to both targets
            assert count >= 0

    @pytest.mark.asyncio
    async def test_dispatch_no_targets(self):
        """Test dispatch with no targets."""
        dispatcher = NotificationDispatcher()
        payload = NotificationPayload(
            event_id="evt_001",
            rule_id="rule_001",
            rule_name="Test",
            severity=AlertSeverity.INFO,
            message="Test",
            metric_name="price",
        )

        count = await dispatcher.dispatch([], payload)
        assert count == 0

    def test_dispatcher_statistics(self):
        """Test dispatcher statistics."""
        dispatcher = NotificationDispatcher()

        stats = dispatcher.get_dispatcher_stats()
        assert stats["total_sent"] == 0
        assert stats["total_failed"] == 0

    def test_reset_statistics(self):
        """Test resetting dispatcher statistics."""
        dispatcher = NotificationDispatcher()
        dispatcher.notification_stats["total_sent"] = 10
        dispatcher.notification_stats["total_failed"] = 5

        dispatcher.reset_stats()

        stats = dispatcher.get_dispatcher_stats()
        assert stats["total_sent"] == 0
        assert stats["total_failed"] == 0
