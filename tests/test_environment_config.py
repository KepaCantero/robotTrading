"""
Tests for Environment Configuration System
TASK-5: Configuración de variables de entorno
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.core.environment_config import (
    CentralizedConfig,
    DatabaseConfig,
    RedisConfig,
    APIConfig,
    TradingConfig,
    LoggingConfig,
    MonitoringConfig,
    Environment,
    LogLevel,
    get_config,
    reload_config,
    set_config,
    load_config_from_file,
    create_config_for_environment
)
from app.exceptions import ConfigurationError


class TestEnvironmentEnum:
    """Tests for Environment enum."""

    def test_environment_values(self):
        """Test Environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"


class TestLogLevelEnum:
    """Tests for LogLevel enum."""

    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_database_config_defaults(self):
        """Test DatabaseConfig default values."""
        config = DatabaseConfig()
        
        assert config.db_host == "localhost"
        assert config.db_port == 5432
        assert config.db_name == "algotrading"
        assert config.db_user == "postgres"
        assert config.db_password == ""
        assert config.db_pool_size == 10
        assert config.db_max_overflow == 20
        assert config.db_pool_timeout == 30
        assert config.db_ssl_mode == "prefer"

    def test_database_config_with_env_vars(self):
        """Test DatabaseConfig with environment variables."""
        with patch.dict(os.environ, {
            'DB_HOST': 'test-host',
            'DB_PORT': '3306',
            'DB_NAME': 'test-db',
            'DB_USER': 'test-user',
            'DB_PASSWORD': 'test-password'
        }):
            config = DatabaseConfig()
            
            assert config.db_host == "test-host"
            assert config.db_port == 3306
            assert config.db_name == "test-db"
            assert config.db_user == "test-user"
            assert config.db_password == "test-password"

    def test_database_config_validation(self):
        """Test DatabaseConfig validation."""
        # Test invalid port
        with pytest.raises(ValueError):
            DatabaseConfig(db_port=0)
        
        with pytest.raises(ValueError):
            DatabaseConfig(db_port=70000)
        
        # Test invalid pool size
        with pytest.raises(ValueError):
            DatabaseConfig(db_pool_size=0)

    def test_database_connection_string(self):
        """Test database connection string generation."""
        config = DatabaseConfig(
            db_host="test-host",
            db_port=5432,
            db_name="test-db",
            db_user="test-user",
            db_password="test-password",
            db_ssl_mode="require"
        )
        
        connection_string = config.connection_string
        assert "postgresql://test-user:test-password@test-host:5432/test-db" in connection_string
        assert "sslmode=require" in connection_string

    def test_database_url_override(self):
        """Test database URL override."""
        config = DatabaseConfig(db_url="postgresql://user:pass@host:5432/db")
        
        assert config.connection_string == "postgresql://user:pass@host:5432/db"


class TestRedisConfig:
    """Tests for RedisConfig."""

    def test_redis_config_defaults(self):
        """Test RedisConfig default values."""
        config = RedisConfig()
        
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_password is None
        assert config.redis_db == 0
        assert config.redis_max_connections == 10
        assert config.redis_ssl is False

    def test_redis_config_with_env_vars(self):
        """Test RedisConfig with environment variables."""
        with patch.dict(os.environ, {
            'REDIS_HOST': 'redis-host',
            'REDIS_PORT': '6380',
            'REDIS_PASSWORD': 'redis-password',
            'REDIS_DB': '2'
        }):
            config = RedisConfig()
            
            assert config.redis_host == "redis-host"
            assert config.redis_port == 6380
            assert config.redis_password == "redis-password"
            assert config.redis_db == 2

    def test_redis_connection_string(self):
        """Test Redis connection string generation."""
        config = RedisConfig(
            redis_host="redis-host",
            redis_port=6379,
            redis_password="redis-password",
            redis_db=1,
            redis_ssl=True
        )
        
        connection_string = config.connection_string
        assert "rediss://:redis-password@redis-host:6379/1" == connection_string

    def test_redis_url_override(self):
        """Test Redis URL override."""
        config = RedisConfig(redis_url="redis://user:pass@host:6379/0")
        
        assert config.connection_string == "redis://user:pass@host:6379/0"


class TestAPIConfig:
    """Tests for APIConfig."""

    def test_api_config_defaults(self):
        """Test APIConfig default values."""
        config = APIConfig()
        
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8000
        assert config.api_workers == 1
        assert config.secret_key == "your-secret-key-here"
        assert config.access_token_expire_minutes == 30
        assert config.refresh_token_expire_days == 7
        assert config.cors_origins == ["*"]
        assert config.rate_limit_requests == 100

    def test_api_config_validation(self):
        """Test APIConfig validation."""
        # Test invalid port
        with pytest.raises(ValueError):
            APIConfig(api_port=0)
        
        # Test short secret key
        with pytest.raises(ValueError):
            APIConfig(secret_key="short")


class TestTradingConfig:
    """Tests for TradingConfig."""

    def test_trading_config_defaults(self):
        """Test TradingConfig default values."""
        config = TradingConfig()
        
        assert config.default_strategy == "momentum"
        assert config.max_position_size == 0.1
        assert config.max_daily_loss == 0.05
        assert config.max_drawdown == 0.15
        assert config.stop_loss_percentage == 0.02
        assert config.take_profit_percentage == 0.04
        assert config.position_sizing_method == "fixed"
        assert config.market_data_provider == "yahoo"
        assert config.broker_name == "paper"
        assert config.broker_sandbox is True

    def test_trading_config_validation(self):
        """Test TradingConfig validation."""
        # Test invalid position size
        with pytest.raises(ValueError):
            TradingConfig(max_position_size=1.5)
        
        with pytest.raises(ValueError):
            TradingConfig(max_position_size=0)
        
        # Test invalid daily loss
        with pytest.raises(ValueError):
            TradingConfig(max_daily_loss=1.5)
        
        # Test invalid stop loss
        with pytest.raises(ValueError):
            TradingConfig(stop_loss_percentage=1.5)


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig default values."""
        config = LoggingConfig()
        
        assert config.log_level == LogLevel.INFO
        assert config.log_file_enabled is True
        assert config.log_file_path == "logs/app.log"
        assert config.log_file_max_size == 10485760
        assert config.log_file_backup_count == 5
        assert config.log_console_enabled is True
        assert config.elk_enabled is False

    def test_logging_config_validation(self):
        """Test LoggingConfig validation."""
        # Test invalid file size
        with pytest.raises(ValueError):
            LoggingConfig(log_file_max_size=500)


class TestMonitoringConfig:
    """Tests for MonitoringConfig."""

    def test_monitoring_config_defaults(self):
        """Test MonitoringConfig default values."""
        config = MonitoringConfig()
        
        assert config.prometheus_enabled is True
        assert config.prometheus_port == 9090
        assert config.prometheus_path == "/metrics"
        assert config.health_check_enabled is True
        assert config.health_check_interval == 30
        assert config.alerts_enabled is False

    def test_monitoring_config_validation(self):
        """Test MonitoringConfig validation."""
        # Test invalid port
        with pytest.raises(ValueError):
            MonitoringConfig(prometheus_port=0)


class TestCentralizedConfig:
    """Tests for CentralizedConfig."""

    def test_centralized_config_defaults(self):
        """Test CentralizedConfig default values."""
        config = CentralizedConfig()
        
        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is False
        assert config.app_name == "AlgoTrading"
        assert config.app_version == "1.0.0"
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.trading, TradingConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.monitoring, MonitoringConfig)

    def test_centralized_config_with_env_vars(self):
        """Test CentralizedConfig with environment variables."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'DEBUG': 'false',
            'APP_NAME': 'TestApp',
            'APP_VERSION': '2.0.0'
        }):
            config = CentralizedConfig()
            
            assert config.environment == Environment.PRODUCTION
            assert config.debug is False
            assert config.app_name == "TestApp"
            assert config.app_version == "2.0.0"

    def test_centralized_config_validation(self):
        """Test CentralizedConfig validation."""
        # Test production with debug enabled
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'DEBUG': 'true'
        }):
            with pytest.raises(ConfigurationError):
                CentralizedConfig()
        
        # Test production with default secret key
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'SECRET_KEY': 'your-secret-key-here'
        }):
            with pytest.raises(ConfigurationError):
                CentralizedConfig()

    def test_centralized_config_methods(self):
        """Test CentralizedConfig utility methods."""
        config = CentralizedConfig()
        
        # Test get_config_dict
        config_dict = config.get_config_dict()
        assert isinstance(config_dict, dict)
        assert "environment" in config_dict
        assert "database" in config_dict
        assert "redis" in config_dict
        
        # Test environment checks
        assert config.is_development() is True
        assert config.is_production() is False
        assert config.is_testing() is False

    def test_centralized_config_production(self):
        """Test CentralizedConfig in production mode."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'DEBUG': 'false',
            'SECRET_KEY': 'production-secret-key-32-chars-minimum',
            'DB_PASSWORD': 'production-password',
            'BROKER_API_KEY': 'production-broker-key'
        }):
            config = CentralizedConfig()
            
            assert config.is_production() is True
            assert config.is_development() is False
            assert config.debug is False


class TestConfigFunctions:
    """Tests for configuration utility functions."""

    def test_get_config(self):
        """Test get_config function."""
        config = get_config()
        assert isinstance(config, CentralizedConfig)

    def test_reload_config(self):
        """Test reload_config function."""
        config = reload_config()
        assert isinstance(config, CentralizedConfig)

    def test_set_config(self):
        """Test set_config function."""
        config = CentralizedConfig()
        set_config(config)
        assert get_config() is config

    def test_load_config_from_file(self):
        """Test load_config_from_file function."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write("ENVIRONMENT=testing\n")
            f.write("DEBUG=true\n")
            f.write("APP_NAME=TestApp\n")
            temp_file = f.name
        
        try:
            config = load_config_from_file(temp_file)
            assert config.environment == Environment.TESTING
            assert config.debug is True
            assert config.app_name == "TestApp"
        finally:
            os.unlink(temp_file)

    def test_load_config_from_nonexistent_file(self):
        """Test load_config_from_file with nonexistent file."""
        with pytest.raises(ConfigurationError):
            load_config_from_file("nonexistent.env")

    def test_create_config_for_environment(self):
        """Test create_config_for_environment function."""
        config = create_config_for_environment(Environment.TESTING)
        assert config.environment == Environment.TESTING
        assert config.debug is True
        
        config = create_config_for_environment(Environment.PRODUCTION)
        assert config.environment == Environment.PRODUCTION
        assert config.debug is False


class TestConfigIntegration:
    """Tests for configuration integration."""

    def test_config_with_all_components(self):
        """Test configuration with all components."""
        config = CentralizedConfig()
        
        # Test all components are properly initialized
        assert config.database.db_host == "localhost"
        assert config.redis.redis_host == "localhost"
        assert config.api.api_host == "0.0.0.0"
        assert config.trading.default_strategy == "momentum"
        assert config.logging.log_level == LogLevel.INFO
        assert config.monitoring.prometheus_enabled is True

    def test_config_environment_specific_validation(self):
        """Test environment-specific validation."""
        # Test development environment
        dev_config = create_config_for_environment(Environment.DEVELOPMENT)
        assert dev_config.debug is True
        
        # Test production environment
        prod_config = create_config_for_environment(Environment.PRODUCTION)
        assert prod_config.debug is False

    def test_config_override_behavior(self):
        """Test configuration override behavior."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'testing',
            'DB_HOST': 'test-db-host',
            'REDIS_HOST': 'test-redis-host',
            'API_PORT': '9000'
        }):
            config = CentralizedConfig()
            
            assert config.environment == Environment.TESTING
            assert config.database.db_host == "test-db-host"
            assert config.redis.redis_host == "test-redis-host"
            assert config.api.api_port == 9000
