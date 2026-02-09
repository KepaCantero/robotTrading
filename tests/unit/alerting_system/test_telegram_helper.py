"""
Tests for TelegramBotHelper.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.alerting_system.telegram_helper import TelegramBotHelper


@pytest.mark.asyncio
async def test_test_bot_token_valid():
    """Test bot token validation with valid token."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {"id": 123, "username": "test_bot", "first_name": "Test Bot"},
        }

        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        result = await TelegramBotHelper.test_bot_token("test_token")

        assert result["valid"] is True
        assert result["bot_info"]["username"] == "test_bot"


@pytest.mark.asyncio
async def test_test_bot_token_invalid():
    """Test bot token validation with invalid token."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "description": "Unauthorized",
        }

        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        result = await TelegramBotHelper.test_bot_token("invalid_token")

        assert result["valid"] is False
        assert "Unauthorized" in result["error"]


@pytest.mark.asyncio
async def test_get_chat_id():
    """Test getting chat_id from bot updates."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": [
                {
                    "message": {
                        "chat": {"id": 123456789},
                        "text": "/start",
                    }
                }
            ],
        }

        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        chat_id = await TelegramBotHelper.get_chat_id("test_token")

        assert chat_id == 123456789


@pytest.mark.asyncio
async def test_send_test_message():
    """Test sending a test message."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await TelegramBotHelper.send_test_message("test_token", 123456789, "Test message")

        assert result is True


@pytest.mark.asyncio
async def test_get_chat_id_no_updates():
    """Test getting chat_id when no updates exist."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": [],
        }

        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        chat_id = await TelegramBotHelper.get_chat_id("test_token")

        assert chat_id is None


@pytest.mark.asyncio
async def test_send_test_message_failure():
    """Test sending a test message when API fails."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False}

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await TelegramBotHelper.send_test_message("test_token", 123456789, "Test message")

        assert result is False
