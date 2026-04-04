"""
Tests for TelegramChannel notification channel.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alerting_system.models import (
    AlertSeverity,
    NotificationChannelType,
    NotificationPayload,
    NotificationTarget,
)
from app.services.alerting_system.notification_channels import TelegramChannel


@pytest.fixture
def telegram_channel():
    """Fixture for TelegramChannel."""
    return TelegramChannel()


@pytest.fixture
def notification_target():
    """Fixture for NotificationTarget with Telegram config."""
    return NotificationTarget(
        channel_type=NotificationChannelType.TELEGRAM,
        endpoint="123456789",  # chat_id
        enabled=True,
        headers={
            "telegram_bot_token": "test_bot_token",
            "telegram_chat_id": "123456789",
        },
    )


@pytest.fixture
def notification_payload():
    """Fixture for NotificationPayload."""
    return NotificationPayload(
        event_id="test_event_1",
        rule_id="test_rule",
        rule_name="Test Alert Rule",
        severity=AlertSeverity.WARNING,
        message="This is a test alert message",
        metric_name="test_metric",
        metric_value=Decimal("123.45"),
        symbol="AAPL",
        triggered_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_telegram_send_success(telegram_channel, notification_target, notification_payload):
    """Test successful Telegram message sending."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await telegram_channel.send(notification_target, notification_payload)

        assert result is True
        mock_post.assert_called_once()

        # Verify call arguments
        call_args = mock_post.call_args
        assert "sendMessage" in call_args[0][0]
        assert call_args[1]["json"]["chat_id"] == "123456789"
        assert "parse_mode" in call_args[1]["json"]


@pytest.mark.asyncio
async def test_telegram_send_disabled(telegram_channel, notification_target, notification_payload):
    """Test that disabled channel doesn't send."""
    notification_target.enabled = False

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await telegram_channel.send(notification_target, notification_payload)

        assert result is False
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_send_missing_token(
    telegram_channel, notification_target, notification_payload
):
    """Test handling of missing bot token."""
    notification_target.headers = {}  # Remove bot_token

    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await telegram_channel.send(notification_target, notification_payload)

        assert result is False
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_send_api_error(telegram_channel, notification_target, notification_payload):
    """Test handling of API error response."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await telegram_channel.send(notification_target, notification_payload)

        assert result is False


@pytest.mark.asyncio
async def test_telegram_send_connection_error(
    telegram_channel, notification_target, notification_payload
):
    """Test handling of connection error."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(side_effect=ConnectionError("Network error"))
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await telegram_channel.send(notification_target, notification_payload)

        assert result is False
