"""
Independent Tests for Centralized Configuration System
TASK-10: Centralización de Configuración
"""

import sys
from pathlib import Path

import pytest

from app.shared.config.centralized_config import (
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
    get_config_summary,
    get_strategy_config,
    get_trading_threshold,
    reload_config,
    set_config,
    update_strategy_config,
    validate_configuration,
)

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTradingThresholds:
    """Test TradingThresholds configuration."""

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
        assert thresholds.daily_loss_limit == 0.05
        assert thresholds.max_drawdown_limit == 0.15
        assert thresholds.max_total_exposure == 0.8
        assert thresholds.max_sector_exposure == 0.3
        assert thresholds.max_correlation == 0.7
        assert thresholds.circuit_breaker_daily_loss == 0.03
        assert thresholds.circuit_breaker_drawdown == 0.1
        assert thresholds.circuit_breaker_volatility == 0.05
        assert thresholds.circuit_breaker_error_rate == 0.05
        assert thresholds.max_latency_ms == 1000
        assert thresholds.max_execution_time_ms == 500

    def test_validation_max_position_size(self):
        """Test max_position_size validation."""
        # Valid values
        TradingThresholds(max_position_size=0.1)
        TradingThresholds(max_position_size=0.5)
        TradingThresholds(max_position_size=1.0)

        # Invalid values
        with pytest.raises(ValueError, match="Percentage values must be between 0 and 1"):
            TradingThresholds(max_position_size=1.1)

        with pytest.raises(ValueError, match="Percentage values must be between 0 and 1"):
            TradingThresholds(max_position_size=-0.1)

    def test_validation_stop_loss(self):
        """Test stop_loss_pct validation."""
        # Valid values
        TradingThresholds(stop_loss_pct=0.01)
        TradingThresholds(stop_loss_pct=0.05)
        TradingThresholds(stop_loss_pct=0.5)

        # Invalid values
        with pytest.raises(ValueError, match="Stop loss percentage must be between 0 and 0.5"):
            TradingThresholds(stop_loss_pct=0.6)

        with pytest.raises(ValueError, match="Stop loss percentage must be between 0 and 0.5"):
            TradingThresholds(stop_loss_pct=-0.1)


class TestStrategyConfig:
    """Test StrategyConfig configuration."""

    def test_default_values(self):
        """Test default strategy config values."""
        config = StrategyConfig(name="test_strategy")

        assert config.name == "test_strategy"
        assert config.enabled is True
        assert config.weight == 1.0
        assert config.parameters == {}
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
            weight=1.5,
            parameters={"rsi_threshold": 40, "momentum_threshold": 0.02},
            max_position_size=0.1,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            min_sharpe_ratio=1.2,
            max_drawdown=0.12,
            min_win_rate=0.45,
        )
        assert config.name == "momentum"
        assert config.enabled is False
        assert config.weight == 1.5
        assert config.parameters["rsi_threshold"] == 40
        assert config.parameters["momentum_threshold"] == 0.02
        assert config.max_position_size == 0.1
        assert config.stop_loss_pct == 0.05
        assert config.take_profit_pct == 0.10
        assert config.min_sharpe_ratio == 1.2
        assert config.max_drawdown == 0.12
        assert config.min_win_rate == 0.45


class TestDatabaseConfig:
    """Test DatabaseConfig configuration."""

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

    def test_connection_string(self):
        """Test database connection string generation."""
        config = DatabaseConfig(
            host="db.example.com",
            port=5433,
            name="trading_db",
            user="trader",
            password="secret123",
        )
        expected = "postgresql://trader:secret123@db.example.com:5433/trading_db"
        assert config.connection_string == expected


class TestRedisConfig:
    """Test RedisConfig configuration."""

    def test_default_values(self):
        """Test default Redis config values."""
        config = RedisConfig()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.password is None
        assert config.db == 0
        assert config.max_connections == 20
        assert config.socket_timeout == 5

    def test_connection_string_without_password(self):
        """Test Redis connection string without password."""
        config = RedisConfig(host="redis.example.com", port=6380, db=1)

        expected = "redis://redis.example.com:6380/1"
        assert config.connection_string == expected

    def test_connection_string_with_password(self):
        """Test Redis connection string with password."""
        config = RedisConfig(host="redis.example.com", port=6380, password="secret", db=1)
        expected = "redis://:secret@redis.example.com:6380/1"
        assert config.connection_string == expected


class TestAPIConfig:
    """Test APIConfig configuration."""

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

    def test_secret_key_validation(self):
        """Test secret key validation."""
        # Valid secret key
        APIConfig(secret_key="a" * 32)

        # Invalid secret key
        with pytest.raises(ValueError, match="Secret key must be at least 16 characters long"):
            APIConfig(secret_key="short")


class TestCentralizedConfig:
    """Test CentralizedConfig main configuration."""

    def test_default_values(self):
        """Test default centralized config values."""
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

    def test_environment_enum(self):
        """Test environment enum values."""
        config = CentralizedConfig(environment=Environment.PRODUCTION)
        assert config.environment == Environment.PRODUCTION

        config = CentralizedConfig(environment=Environment.STAGING)
        assert config.environment == Environment.STAGING

        config = CentralizedConfig(environment=Environment.TESTING)
        assert config.environment == Environment.TESTING

    def test_get_strategy_config(self):
        """Test getting strategy configuration."""
        config = CentralizedConfig()

        # Add a test strategy
        test_strategy = StrategyConfig(name="test", enabled=True)
        config.strategies["test"] = test_strategy

        # Get existing strategy
        result = config.get_strategy_config("test")
        assert result == test_strategy

        # Get non-existing strategy
        result = config.get_strategy_config("nonexistent")
        assert result is None

    def test_get_trading_threshold(self):
        """Test getting trading threshold values."""
        config = CentralizedConfig()

        # Valid threshold
        result = config.get_trading_threshold("max_position_size")
        assert result == 0.1

        # Invalid threshold
        with pytest.raises(Exception):  # ConfigurationError
            config.get_trading_threshold("invalid_threshold")

    def test_update_strategy_config(self):
        """Test updating strategy configuration."""
        config = CentralizedConfig()

        # Update existing strategy
        config.update_strategy_config("momentum", {"enabled": False, "weight": 1.5})
        assert "momentum" in config.strategies
        assert config.strategies["momentum"].enabled is False
        assert config.strategies["momentum"].weight == 1.5

        # Update non-existing strategy
        config.update_strategy_config("new_strategy", {"enabled": True})
        assert "new_strategy" in config.strategies
        assert config.strategies["new_strategy"].enabled is True

    def test_validate_configuration_success(self):
        """Test successful configuration validation."""
        config = CentralizedConfig()

        # Should not raise any exception
        result = config.validate_configuration()
        assert result is True

    def test_get_config_summary(self):
        """Test getting configuration summary."""
        config = CentralizedConfig()

        summary = config.get_config_summary()

        assert "environment" in summary
        assert "debug" in summary
        assert "trading_thresholds" in summary
        assert "database" in summary
        assert "redis" in summary
        assert "api" in summary
        assert "strategies" in summary

        assert summary["environment"] == "development"
        assert summary["debug"] is True


class TestGlobalConfigFunctions:
    """Test global configuration functions."""

    def test_get_config_singleton(self):
        """Test get_config returns singleton instance."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reload_config(self):
        """Test reloading configuration."""
        config1 = get_config()
        config2 = reload_config()

        assert config1 is not config2

    def test_set_config(self):
        """Test setting global configuration."""
        new_config = CentralizedConfig(environment=Environment.PRODUCTION)
        set_config(new_config)

        current_config = get_config()
        assert current_config is new_config
        assert current_config.environment == Environment.PRODUCTION

    def test_get_trading_threshold_function(self):
        """Test get_trading_threshold function."""
        threshold = get_trading_threshold("max_position_size")
        assert threshold == 0.1

        with pytest.raises(Exception):  # ConfigurationError
            get_trading_threshold("invalid")

    def test_get_strategy_config_function(self):
        """Test get_strategy_config function."""
        config = get_strategy_config("nonexistent")
        assert config is None

    def test_update_strategy_config_function(self):
        """Test update_strategy_config function."""
        update_strategy_config("test", {"enabled": True})

        config = get_strategy_config("test")
        assert config is not None
        assert config.enabled is True

    def test_validate_configuration_function(self):
        """Test validate_configuration function."""
        result = validate_configuration()
        assert result is True

    def test_get_config_summary_function(self):
        """Test get_config_summary function."""
        summary = get_config_summary()

        assert isinstance(summary, dict)
        assert "environment" in summary
        assert "trading_thresholds" in summary


if __name__ == "__main__":
    pytest.main([__file__])
