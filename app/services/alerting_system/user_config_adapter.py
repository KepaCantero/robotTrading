"""
Adapter to convert UserSettings to Alerting System configuration.
"""

import logging
import os

from app.infrastructure.config.user_settings import UserSettings
from app.services.alerting_system.models import NotificationChannelType, NotificationTarget

logger = logging.getLogger(__name__)


def user_settings_to_notification_targets(settings: UserSettings) -> list[NotificationTarget]:
    """
    Convert UserSettings notification preferences to NotificationTarget list.

    Args:
        settings: UserSettings instance

    Returns:
        List of NotificationTarget objects
    """
    logger.debug(
        "Converting user settings to notification targets",
        extra={
            "component": "user_config_adapter",
            "operation": "convert_settings",
            "telegram_enabled": settings.notifications.enable_telegram,
            "email_enabled": settings.notifications.enable_email,
        },
    )

    targets = []
    notifications = settings.notifications

    # Telegram
    if notifications.enable_telegram and notifications.telegram_chat_id:
        # Get bot_token from environment or secure storage
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

        logger.info(
            "Adding Telegram notification target",
            extra={
                "component": "user_config_adapter",
                "operation": "add_telegram_target",
                "chat_id_configured": bool(notifications.telegram_chat_id),
                "bot_token_configured": bool(bot_token),
            },
        )

        targets.append(
            NotificationTarget(
                channel_type=NotificationChannelType.TELEGRAM,
                endpoint=notifications.telegram_chat_id or "",
                enabled=notifications.enable_telegram,
                headers={
                    "telegram_bot_token": bot_token,
                    "telegram_chat_id": notifications.telegram_chat_id or "",
                },
            )
        )

    # Email
    if notifications.enable_email and notifications.email_address:
        # SMTP config from environment
        smtp_host = os.environ.get("SMTP_HOST", "localhost")
        smtp_port = os.environ.get("SMTP_PORT", "587")
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_password = os.environ.get("SMTP_PASSWORD", "")
        from_address = os.environ.get("SMTP_FROM", "alerts@algotrading.local")

        logger.info(
            "Adding Email notification target",
            extra={
                "component": "user_config_adapter",
                "operation": "add_email_target",
                "email_address": notifications.email_address,
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
            },
        )

        targets.append(
            NotificationTarget(
                channel_type=NotificationChannelType.EMAIL,
                endpoint=notifications.email_address or "",
                enabled=notifications.enable_email,
                headers={
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port,
                    "smtp_user": smtp_user,
                    "smtp_password": smtp_password,
                    "smtp_use_tls": "true",
                    "from_address": from_address,
                },
            )
        )

    logger.info(
        "Notification targets conversion complete",
        extra={
            "component": "user_config_adapter",
            "operation": "convert_settings_complete",
            "total_targets": len(targets),
        },
    )

    return targets
