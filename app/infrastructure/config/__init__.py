"""
User Configuration Module

Provides user-specific configuration for single-user deployment.
Allows individual traders to customize settings without code changes.
"""

from .user_config_manager import UserConfigManager, get_user_config
from .user_settings import (
    BrokerType,
    NotificationSettings,
    OrderPreferences,
    OrderTypePreference,
    RiskLimits,
    SymbolUniverse,
    TradingHours,
    TradingProfile,
    UserSettings,
)

__all__ = [
    "BrokerType",
    "NotificationSettings",
    "OrderPreferences",
    "OrderTypePreference",
    "RiskLimits",
    "SymbolUniverse",
    "TradingHours",
    "TradingProfile",
    "UserConfigManager",
    "UserSettings",
    "get_user_config",
]
