"""
User Configuration Manager

Manages loading, saving, and accessing user configuration.
"""
import logging
from decimal import Decimal
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from .user_settings import UserSettings

logger = logging.getLogger(__name__)

# Default config paths
DEFAULT_CONFIG_DIR = Path.home() / ".algotrading"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "user_config.yaml"


class UserConfigManager:
    """Manages user configuration loading and persistence."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the user config manager.

        Args:
            config_path: Path to user config file. Defaults to ~/.algotrading/user_config.yaml
        """
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self._settings: Optional[UserSettings] = None

    def load(self) -> UserSettings:
        """
        Load user settings from config file.

        Returns:
            UserSettings: Loaded user settings

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValidationError: If config is invalid
        """
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            logger.info("Creating default config...")
            return self._create_default_config()

        with open(self.config_path, "r") as f:
            config_data = yaml.safe_load(f)

        try:
            self._settings = UserSettings(**config_data)
            logger.info(f"Loaded user config from: {self.config_path}")
            return self._settings
        except ValidationError as e:
            logger.error(f"Invalid config: {e}")
            raise

    def save(self, settings: UserSettings) -> None:
        """
        Save user settings to config file.

        Args:
            settings: User settings to save
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            yaml.dump(
                settings.model_dump(mode="json"),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

        self._settings = settings
        logger.info(f"Saved user config to: {self.config_path}")

    def get_settings(self) -> UserSettings:
        """
        Get current user settings.

        Returns:
            UserSettings: Current user settings

        Raises:
            RuntimeError: If settings haven't been loaded
        """
        if self._settings is None:
            self._settings = self.load()
        return self._settings

    def reload(self) -> UserSettings:
        """
        Reload settings from config file.

        Returns:
            UserSettings: Reloaded user settings
        """
        self._settings = None
        return self.load()

    def _create_default_config(self) -> UserSettings:
        """
        Create default configuration file.

        Returns:
            UserSettings: Default settings
        """
        default_settings = UserSettings()
        self.save(default_settings)
        return default_settings

    def validate_config(self) -> tuple[bool, list[str]]:
        """
        Validate current configuration.

        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []

        try:
            settings = self.get_settings()

            # Validate critical settings
            if settings.broker_settings.paper_trading:
                # In paper mode, API keys are optional
                pass
            else:
                # In live mode, validate API keys
                if settings.broker_settings.broker_type == "alpaca":
                    if not settings.broker_settings.alpaca_api_key:
                        errors.append("Alpaca API key required for live trading")
                    if not settings.broker_settings.alpaca_api_secret:
                        errors.append("Alpaca API secret required for live trading")

            # Validate risk limits
            if settings.risk_limits.max_daily_loss > Decimal("0.1"):
                errors.append("Max daily loss should not exceed 10%")

            if settings.risk_limits.max_drawdown > Decimal("0.3"):
                errors.append("Max drawdown should not exceed 30%")

            # Validate symbol universe
            if not settings.symbol_universe.allowed_symbols:
                errors.append("At least one symbol must be allowed")

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return (len(errors) == 0, errors)


# Global singleton
_user_config_manager: Optional[UserConfigManager] = None


def get_user_config(config_path: Optional[Path] = None) -> UserConfigManager:
    """
    Get the global user config manager instance.

    Args:
        config_path: Optional path to config file. If provided, creates a new instance
                    with the custom path (not cached as singleton).

    Returns:
        UserConfigManager: User config manager instance
    """
    global _user_config_manager
    if config_path is not None:
        # Custom path - create new instance (not cached)
        return UserConfigManager(config_path)
    if _user_config_manager is None:
        _user_config_manager = UserConfigManager(config_path)
    return _user_config_manager
