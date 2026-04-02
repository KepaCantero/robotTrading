"""
Telegram Bot Helper

Helper utilities for setting up and testing Telegram bot integration.
"""

from __future__ import annotations

import logging
from typing import cast

import httpx

logger = logging.getLogger(__name__)


class TelegramBotHelper:
    """
    Helper for Telegram bot operations.

    Usage:
        1. Create a bot via @BotFather on Telegram
        2. Get the bot token
        3. Use this helper to get your chat_id
        4. Configure bot_token and chat_id in UserSettings
    """

    API_BASE = "https://api.telegram.org/bot"

    @classmethod
    async def test_bot_token(cls, bot_token: str) -> dict:
        """
        Test if a bot token is valid.

        Args:
            bot_token: Telegram bot token from @BotFather

        Returns:
            dict with 'valid' bool and 'bot_info' if valid
        """
        try:
            url = f"{cls.API_BASE}{bot_token}/getMe"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return {
                        "valid": True,
                        "bot_info": data.get("result", {}),
                    }
                return {"valid": False, "error": data.get("description", "Unknown error")}

            return {"valid": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"valid": False, "error": str(e)}

    @classmethod
    async def get_chat_id(cls, bot_token: str) -> int | None:
        """
        Get the chat_id by sending a test message and polling updates.

        Instructions:
            1. Start a chat with your bot on Telegram
            2. Send any message to the bot (e.g., "/start")
            3. Call this method to get the chat_id

        Args:
            bot_token: Telegram bot token from @BotFather

        Returns:
            chat_id or None if no messages found
        """
        try:
            url = f"{cls.API_BASE}{bot_token}/getUpdates"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    updates = data.get("result", [])
                    if updates:
                        # Get the most recent message's chat_id
                        chat_id = updates[-1].get("message", {}).get("chat", {}).get("id")
                        return cast("int | None", chat_id)

            return None

        except Exception as e:
            logger.error(f"Error getting chat_id: {e}")
            return None

    @classmethod
    async def send_test_message(
        cls, bot_token: str, chat_id: int, message: str = "AlgoTrading bot test message!"
    ) -> bool:
        """
        Send a test message via Telegram.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
            message: Test message to send

        Returns:
            True if message sent successfully
        """
        try:
            url = f"{cls.API_BASE}{bot_token}/sendMessage"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                return bool(data.get("ok", False))

            return False

        except Exception as e:
            logger.error(f"Error sending test message: {e}")
            return False

    @classmethod
    def get_setup_instructions(cls) -> str:
        """Return instructions for setting up Telegram bot."""
        return """
# Telegram Bot Setup for AlgoTrading Alerts

## Step 1: Create a Bot via @BotFather

1. Open Telegram and search for @BotFather
2. Send /newbot command
3. Follow instructions to name your bot (e.g., "MyAlgoTradingBot")
4. Copy the bot token (looks like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)

## Step 2: Get Your Chat ID

1. Start a chat with your bot on Telegram
2. Send any message (e.g., /start)
3. Use the get_chat_id() method to retrieve your chat_id

## Step 3: Configure in User Settings

Update your user_config.yaml:

```yaml
notifications:
  enable_telegram: true
  telegram_chat_id: "YOUR_CHAT_ID"
  telegram_bot_token: "YOUR_BOT_TOKEN"  # Store securely!
  alert_on_entry: true
  alert_on_exit: true
  alert_on_risk: true
  daily_summary: true
```

## Security Notes

- Never commit your bot_token to version control
- Use environment variables for sensitive data
- Consider using a secrets manager for production
        """


async def setup_telegram_bot_interactive() -> dict:
    """
    Interactive setup helper for Telegram bot.

    Returns:
        dict with bot_token and chat_id if successful
    """
    print("=== Telegram Bot Setup ===\n")
    print(TelegramBotHelper.get_setup_instructions())

    bot_token = input("\nEnter your bot token from @BotFather: ").strip()

    # Test bot token
    print("\nTesting bot token...")
    result = await TelegramBotHelper.test_bot_token(bot_token)

    if not result.get("valid"):
        print(f"❌ Invalid bot token: {result.get('error')}")
        return {}

    bot_info = result.get("bot_info", {})
    print(f"✅ Bot validated: @{bot_info.get('username')} ({bot_info.get('first_name')})")

    # Get chat_id
    print("\n" + "=" * 50)
    print("STEP 2: Get Your Chat ID")
    print("=" * 50)
    print("1. Open Telegram and start a chat with your bot")
    print("2. Send any message to the bot (e.g., /start)")
    input("\nPress Enter after sending a message to your bot...")

    print("Retrieving chat_id...")
    chat_id = await TelegramBotHelper.get_chat_id(bot_token)

    if not chat_id:
        print("❌ Could not retrieve chat_id. Make sure you sent a message to your bot.")
        return {}

    print(f"✅ Your chat_id: {chat_id}")

    # Send test message
    print("\nSending test message...")
    success = await TelegramBotHelper.send_test_message(bot_token, chat_id)

    if success:
        print("✅ Test message sent! Check your Telegram.")
    else:
        print("❌ Failed to send test message.")

    return {
        "bot_token": bot_token,
        "chat_id": str(chat_id),
    }
