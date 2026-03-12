"""
Tests for User Configuration Module
"""
import pytest
import tempfile
from decimal import Decimal
from pathlib import Path

from app.user_config import (
    UserSettings,
    BrokerType,
    UserConfigManager,
)
import yaml


@pytest.fixture
def temp_config_file():
    """Create a temporary config file."""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "user_id": "test_user",
            "user_name": "Test Trader",
            "trading_profile": {
                "risk_tolerance": "moderate",
                "max_positions": 5,
            },
            "broker_settings": {
                "broker_type": "paper",
                "paper_trading": True,
            },
        }
        yaml.dump(config_data, f)
        return Path(f.name)


class TestUserSettings:
    """Test UserSettings model."""

    def test_defaults(self):
        """Test UserSettings default values."""
        settings = UserSettings()

        assert settings.user_id == "single_user"
        assert settings.user_name == "Trader"
        assert settings.trading_profile.max_positions == 5
        assert settings.broker_settings.broker_type == BrokerType.PAPER
        assert settings.broker_settings.paper_trading is True

    def test_custom_values(self):
        """Test UserSettings with custom values."""
        settings = UserSettings(
            user_id="custom_user",
            user_name="Custom Trader",
            trading_profile={"max_positions": 10},
            broker_settings={"broker_type": BrokerType.ALPACA},
        )

        assert settings.user_id == "custom_user"
        assert settings.user_name == "Custom Trader"
        assert settings.trading_profile.max_positions == 10
        assert settings.broker_settings.broker_type == BrokerType.ALPACA

    def test_symbol_universe_allowed(self):
        """Test symbol universe filtering."""
        settings = UserSettings(
            symbol_universe={
                "allowed_symbols": ["AAPL", "MSFT", "GOOGL"],
                "min_price": Decimal("10"),
                "max_price": Decimal("1000"),
            }
        )

        assert settings.is_symbol_allowed("AAPL") is True
        assert settings.is_symbol_allowed("aapl") is True  # Case insensitive
        assert settings.is_symbol_allowed("TSLA") is False

    def test_get_allowed_symbols(self):
        """Test get_allowed_symbols method."""
        settings = UserSettings(
            symbol_universe={"allowed_symbols": ["AAPL", "MSFT", "GOOGL"]}
        )

        symbols = settings.get_allowed_symbols()
        assert symbols == ["AAPL", "MSFT", "GOOGL"]

    def test_is_paper_trading(self):
        """Test paper trading mode check."""
        settings_paper = UserSettings(broker_settings={"paper_trading": True})
        settings_live = UserSettings(broker_settings={"paper_trading": False})

        assert settings_paper.is_paper_trading() is True
        assert settings_live.is_paper_trading() is False

    def test_log_level_valid(self):
        """Test valid log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = UserSettings(log_level=level.lower())
            assert settings.log_level == level

    def test_log_level_invalid(self):
        """Test invalid log level raises error."""
        with pytest.raises(ValueError, match="Invalid log level"):
            UserSettings(log_level="INVALID")

    def test_trading_profile_defaults(self):
        """Test TradingProfile defaults."""
        profile = UserSettings().trading_profile

        assert profile.profile_name == "default"
        assert profile.risk_tolerance == "moderate"
        assert profile.max_positions == 5
        assert profile.max_capital_per_trade == Decimal("0.2")
        assert profile.default_stop_loss_pct == Decimal("0.05")
        assert profile.default_take_profit_pct == Decimal("0.15")

    def test_risk_limits_defaults(self):
        """Test RiskLimits defaults."""
        limits = UserSettings().risk_limits

        assert limits.max_daily_loss == Decimal("0.05")
        assert limits.max_drawdown == Decimal("0.15")
        assert limits.kill_switch_enabled is True
        assert limits.max_position_size == Decimal("0.2")
        assert limits.max_total_exposure == Decimal("0.8")

    def test_notification_settings_defaults(self):
        """Test NotificationSettings defaults."""
        notifications = UserSettings().notifications

        assert notifications.enable_telegram is False
        assert notifications.telegram_chat_id is None
        assert notifications.enable_email is False
        assert notifications.alert_on_entry is True
        assert notifications.alert_on_exit is True
        assert notifications.alert_on_risk is True


class TestUserConfigManager:
    """Test UserConfigManager."""

    def test_load_creates_default_if_not_exists(self, tmp_path):
        """Test that load creates default config if file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"
        manager = UserConfigManager(config_file)

        settings = manager.load()

        assert settings.user_id == "single_user"
        assert config_file.exists()

    def test_save_and_load(self, tmp_path):
        """Test save and load cycle."""
        config_file = tmp_path / "test_config.yaml"
        manager = UserConfigManager(config_file)

        # Save custom settings
        original_settings = UserSettings(user_name="Save Test")
        manager.save(original_settings)

        # Load settings
        loaded_settings = manager.load()

        assert loaded_settings.user_name == "Save Test"

    def test_get_settings_caches(self, tmp_path):
        """Test that get_settings caches the loaded settings."""
        config_file = tmp_path / "test_config.yaml"
        manager = UserConfigManager(config_file)

        settings1 = manager.get_settings()
        settings2 = manager.get_settings()

        # Should return the same instance
        assert settings1 is settings2

    def test_reload(self, tmp_path):
        """Test reload discards cache and reloads."""
        config_file = tmp_path / "test_config.yaml"
        manager = UserConfigManager(config_file)

        # Load initial settings
        settings1 = manager.get_settings()
        assert settings1.user_name == "Trader"

        # Modify file directly
        import yaml

        with open(config_file, "w") as f:
            yaml.dump({"user_name": "Reloaded"}, f)

        # Reload
        settings2 = manager.reload()
        assert settings2.user_name == "Reloaded"

    def test_validate_config_default(self):
        """Test validation of default config (should pass)."""
        manager = UserConfigManager()
        settings = UserSettings()
        manager._settings = settings

        is_valid, errors = manager.validate_config()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_invalid_risk_limits(self):
        """Test validation catches invalid risk limits."""
        manager = UserConfigManager()

        # Invalid: 50% daily loss is too high
        settings = UserSettings(risk_limits={"max_daily_loss": Decimal("0.5")})
        manager._settings = settings

        is_valid, errors = manager.validate_config()

        assert is_valid is False
        assert any("daily loss" in e.lower() for e in errors)

    def test_validate_config_invalid_drawdown(self):
        """Test validation catches invalid drawdown."""
        manager = UserConfigManager()

        # Invalid: 50% drawdown is too high
        settings = UserSettings(risk_limits={"max_drawdown": Decimal("0.5")})
        manager._settings = settings

        is_valid, errors = manager.validate_config()

        assert is_valid is False
        assert any("drawdown" in e.lower() for e in errors)

    def test_validate_config_empty_symbols(self):
        """Test validation catches empty symbol universe."""
        manager = UserConfigManager()

        # Invalid: no symbols allowed
        settings = UserSettings(symbol_universe={"allowed_symbols": []})
        manager._settings = settings

        is_valid, errors = manager.validate_config()

        assert is_valid is False
        assert any("symbol" in e.lower() for e in errors)

    def test_validate_config_live_trading_no_keys(self):
        """Test validation requires API keys for live trading."""
        manager = UserConfigManager()

        # Invalid: live Alpaca trading without API keys
        settings = UserSettings(
            broker_settings={
                "broker_type": BrokerType.ALPACA,
                "paper_trading": False,
                "alpaca_api_key": None,
                "alpaca_api_secret": None,
            }
        )
        manager._settings = settings

        is_valid, errors = manager.validate_config()

        assert is_valid is False
        assert any("api key" in e.lower() or "api secret" in e.lower() for e in errors)

    def test_load_from_existing_file(self, temp_config_file):
        """Test loading from an existing config file."""
        manager = UserConfigManager(temp_config_file)
        settings = manager.load()

        assert settings.user_id == "test_user"
        assert settings.user_name == "Test Trader"


class TestGetUserConfig:
    """Test get_user_config singleton."""

    def test_returns_singleton(self):
        """Test that get_user_config returns the same instance."""
        from app.user_config import get_user_config

        config1 = get_user_config()
        config2 = get_user_config()

        assert config1 is config2

    def test_custom_path(self, tmp_path):
        """Test get_user_config with custom path."""
        from app.user_config import get_user_config

        custom_path = tmp_path / "custom.yaml"
        config = get_user_config(custom_path)

        assert config.config_path == custom_path
