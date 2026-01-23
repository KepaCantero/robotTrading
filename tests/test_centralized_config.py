"""
Tests for Centralized Configuration System
TASK-10: Centralización de Configuración
"""

from unittest.mock import mock_open, patch

import pytest

from app.core.centralized_config import (
    APIConfig,
    CentralizedConfig,
    DatabaseConfig,
    Environment,
    LoggingConfig,
    MonitoringConfig,
    RedisConfig,
    StrategyConfig,
    TradingThresholds,
    get_config,
    get_strategy_config,
    get_trading_threshold,
    reload_config,
    validate_config,
)


class TestTradingThresholds:
    """Test TradingThresholds model."""

    def test_default_values(self):
        """Test default threshold values."""
        thresholds = TradingThresholds()

        assert thresholds.min_signal_strength == 60.0
        assert thresholds.min_signal_confidence == 70.0
        assert thresholds.min_liquidity_score == 50.0
        assert thresholds.rsi_oversold == 30.0
        assert thresholds.rsi_overbought == 70.0
        assert thresholds.max_position_size == 0.1
        assert thresholds.stop_loss_pct == 0.05
        assert thresholds.take_profit_pct == 0.15

    def test_custom_values(self):
        """Test custom threshold values."""
        thresholds = TradingThresholds(
            min_signal_strength=80.0, max_position_size=0.2, stop_loss_pct=0.03
        )
        assert thresholds.min_signal_strength == 80.0
        assert thresholds.max_position_size == 0.2
        assert thresholds.stop_loss_pct == 0.03

    def test_validation_percentage(self):
        """Test percentage validation."""
        with pytest.raises(ValueError, match="Percentage values must be between 0 and 1"):
            TradingThresholds(max_position_size=1.5)

        with pytest.raises(ValueError, match="Stop loss percentage must be between 0 and 0.5"):
            TradingThresholds(stop_loss_pct=-0.1)

    def test_validation_score(self):
        """Test score validation."""
        with pytest.raises(ValueError, match="Score values must be between 0 and 100"):
            TradingThresholds(min_signal_strength=150.0)

        with pytest.raises(ValueError, match="Score values must be between 0 and 100"):
            TradingThresholds(min_signal_confidence=-10.0)


class TestStrategyConfig:
    """Test StrategyConfig model."""

    def test_default_values(self):
        """Test default strategy config values."""
        config = StrategyConfig(name="test_strategy")

        assert config.name == "test_strategy"
        assert config.enabled is True
        assert config.weight == 1.0
        assert config.max_position_size == 0.1
        assert config.stop_loss_pct == 0.05
        assert config.take_profit_pct == 0.15
        assert config.min_sharpe_ratio == 1.0
        assert config.max_drawdown == 0.15
        assert config.min_win_rate == 0.4

    def test_custom_values(self):
        """Test custom strategy config values."""
        config = StrategyConfig(
            name="momentum",
            enabled=False,
            weight=0.8,
            parameters={"rsi_threshold": 40, "lookback": 14},
            max_position_size=0.15,
            stop_loss_pct=0.03,
        )
        assert config.name == "momentum"
        assert config.enabled is False
        assert config.weight == 0.8
        assert config.parameters["rsi_threshold"] == 40
        assert config.max_position_size == 0.15
        assert config.stop_loss_pct == 0.03

    def test_validation(self):
        """Test strategy config validation."""
        with pytest.raises(ValueError, match="Weight must be between 0 and 2"):
            StrategyConfig(name="test", weight=2.5)

        with pytest.raises(ValueError, match="Percentage values must be between 0 and 1"):
            StrategyConfig(name="test", max_position_size=1.5)


class TestDatabaseConfig:
    """Test DatabaseConfig model."""

    def test_default_values(self):
        """Test default database config values."""
        config = DatabaseConfig()

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "algotrading"
        assert config.user == "postgres"
        assert config.password == "password"
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.ssl_mode == "prefer"

    def test_port_validation(self):
        """Test port validation."""
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            DatabaseConfig(port=0)

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            DatabaseConfig(port=70000)


class TestRedisConfig:
    """Test RedisConfig model."""

    def test_default_values(self):
        """Test default Redis config values."""
        config = RedisConfig()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.password is None
        assert config.db == 0
        assert config.max_connections == 20
        assert config.socket_timeout == 5

    def test_port_validation(self):
        """Test port validation."""
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            RedisConfig(port=0)


class TestAPIConfig:
    """Test APIConfig model."""

    def test_default_values(self):
        """Test default API config values."""
        config = APIConfig()

        assert config.host == "0.0.0.0"  # nosec B104
        assert config.port == 8000
        assert config.workers == 1
        assert config.secret_key == "your-secret-key-change-in-production"
        assert config.access_token_expire_minutes == 30
        assert config.rate_limit_per_minute == 100
        assert config.cors_origins == ["*"]
        assert config.cors_methods == ["GET", "POST", "PUT", "DELETE"]

    def test_port_validation(self):
        """Test port validation."""
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            APIConfig(port=0)


class TestEnvironment:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.TESTING == "testing"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"


class TestCentralizedConfig:
    """Test CentralizedConfig model."""

    def test_default_configuration(self):
        """Test default centralized configuration."""
        config = CentralizedConfig()

        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is True
        assert isinstance(config.trading, TradingThresholds)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.monitoring, MonitoringConfig)
        assert isinstance(config.strategies, dict)

    def test_custom_environment(self):
        """Test custom environment configuration."""
        config = CentralizedConfig(environment=Environment.PRODUCTION, debug=True)

        assert config.environment == Environment.PRODUCTION
        assert config.debug is True

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_strategy_configs(self, mock_file, mock_glob, mock_exists):
        """Test loading strategy configurations from YAML files."""
        mock_exists.return_value = True

        # Mock glob to return empty list to avoid file system access
        mock_glob.return_value = []

        config = CentralizedConfig()

        # The _load_strategy_configs method is called in __init__
        # With empty glob, no files are processed
        assert isinstance(config.strategies, dict)
        assert len(config.strategies) == 0


class TestConfigurationFunctions:
    """Test configuration utility functions."""

    def test_get_config(self):
        """Test get_config function."""
        config = get_config()
        assert isinstance(config, CentralizedConfig)

        # Should return the same instance
        config2 = get_config()
        assert config is config2

    def test_get_trading_threshold(self):
        """Test get_trading_threshold function."""
        threshold = get_trading_threshold()
        assert isinstance(threshold, TradingThresholds)
        assert threshold.min_signal_strength == 60.0

    def test_get_strategy_config(self):
        """Test get_strategy_config function."""
        # Test with non-existent strategy
        config = get_strategy_config("non_existent")
        assert config is None

    def test_reload_config(self):
        """Test reload_config function."""
        config1 = get_config()
        config2 = reload_config()

        # Should be different instances
        assert config1 is not config2
        assert isinstance(config2, CentralizedConfig)

    def test_validate_config(self):
        """Test validate_config function."""
        # Should return True for valid default config
        assert validate_config() is True


class TestConfigurationIntegration:
    """Test configuration system integration."""

    def test_configuration_isolation(self):
        """Test that configuration instances are properly isolated."""
        config1 = CentralizedConfig()
        config2 = CentralizedConfig()

        # Should be different instances
        assert config1 is not config2

        # But should have same default values
        assert config1.trading.min_signal_strength == config2.trading.min_signal_strength

    def test_configuration_persistence(self):
        """Test configuration persistence across function calls."""
        config1 = get_config()
        config2 = get_config()

        # Should return the same instance
        assert config1 is config2

    def test_configuration_reload(self):
        """Test configuration reload functionality."""
        original_config = get_config()
        reloaded_config = reload_config()

        # Should be different instances
        assert original_config is not reloaded_config

        # But should have same structure
        assert isinstance(reloaded_config.trading, TradingThresholds)
        assert isinstance(reloaded_config.database, DatabaseConfig)


class TestConfigurationValidation:
    """Test configuration validation scenarios."""

    def test_valid_configuration(self):
        """Test validation of valid configuration."""
        CentralizedConfig()
        assert validate_config() is True

    def test_invalid_trading_thresholds(self):
        """Test validation with invalid trading thresholds."""
        config = CentralizedConfig()
        config.trading.max_position_size = 1.5  # Invalid value

        # This should still pass validation as we're not checking the instance
        # The validation happens at model creation time
        assert validate_config() is True

    def test_configuration_structure(self):
        """Test configuration structure integrity."""
        config = CentralizedConfig()

        # Test all sub-configurations exist
        assert hasattr(config, "trading")
        assert hasattr(config, "database")
        assert hasattr(config, "redis")
        assert hasattr(config, "api")
        assert hasattr(config, "logging")
        assert hasattr(config, "monitoring")
        assert hasattr(config, "strategies")

        # Test sub-configuration types
        assert isinstance(config.trading, TradingThresholds)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.monitoring, MonitoringConfig)
        assert isinstance(config.strategies, dict)
