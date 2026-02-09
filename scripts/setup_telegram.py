#!/usr/bin/env python3
"""
Telegram Bot Setup Script

Interactive script to set up Telegram bot for alerting.
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.alerting_system.telegram_helper import (
    TelegramBotHelper,
    setup_telegram_bot_interactive,
)


async def main():
    """Main setup entry point."""
    print("\n" + "=" * 60)
    print("  AlgoTrading - Telegram Bot Setup")
    print("=" * 60 + "\n")

    # Run interactive setup
    config = await setup_telegram_bot_interactive()

    if config:
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print("\nAdd this to your user_config.yaml:")
        print("-" * 60)
        print("notifications:")
        print("  enable_telegram: true")
        print(f'  telegram_chat_id: "{config["chat_id"]}"')
        print("  # Store bot_token securely (use env vars!)")
        print(f'  telegram_bot_token: "{config["bot_token"]}"')
        print("-" * 60)
        print("\nOr set as environment variables:")
        print(f'export TELEGRAM_BOT_TOKEN="{config["bot_token"]}"')

    else:
        print("\nSetup failed. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
