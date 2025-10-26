"""
Tests for configuration management.

Tests the configuration loading, validation, and default values.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import (Settings, get_database_url, get_redis_url,
                             get_settings)


class TestSettings:
    """Test suite for Settings class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = Settings()

        # Application settings
        assert settings.app_name == "AlgoTrading MVP"
        assert settings.app_version == "1.0.0"
        assert settings.app_description == "Algorithmic Trading System MVP"
        assert settings.debug is True  # Changed because DEBUG=true is set in test_main.py

        # API settings
        assert settings.api_v1_prefix == "/api/v1"
        # Changed to empty string (new default)
        assert settings.secret_key == ""
        assert settings.access_token_expire_minutes == 30
        assert settings.refresh_token_expire_days == 7

        # Database settings
        assert (
            settings.database_url
            == "postgresql://algotrading:algotrading@localhost:5432/algotrading"
        )
        assert settings.database_echo is False
        assert settings.database_pool_size == 10
        assert settings.database_max_overflow == 20

        # Redis settings
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.redis_password is None
        assert settings.redis_db == 0
        assert settings.redis_max_connections == 10

        # Celery settings
        assert settings.celery_broker_url == "redis://localhost:6379/1"
        assert settings.celery_result_backend == "redis://localhost:6379/2"
        assert settings.celery_task_serializer == "json"
        assert settings.celery_result_serializer == "json"
        assert settings.celery_accept_content == ["json"]

        # Trading settings
        assert settings.default_currency == "USD"
        assert settings.max_position_size == 10000.0
        assert settings.risk_free_rate == 0.02

        # Logging settings
        assert settings.log_level == "INFO"
        assert settings.log_format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert settings.log_file is None

        # CORS settings
        assert settings.cors_origins == ["*"]
        assert settings.cors_allow_credentials is True
        assert settings.cors_allow_methods == ["*"]
        assert settings.cors_allow_headers == ["*"]

        # Security settings
        assert settings.password_min_length == 8
        assert settings.password_require_uppercase is True
        assert settings.password_require_lowercase is True
        assert settings.password_require_numbers is True
        assert settings.password_require_special is True

        # Rate limiting
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60

    def test_environment_variable_loading(self):
        """Test that environment variables are loaded correctly."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Test App",
                "DEBUG": "true",
                "SECRET_KEY": "test-secret-key",
                "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
                "LOG_LEVEL": "DEBUG",
            },
        ):
            settings = Settings()

            assert settings.app_name == "Test App"
            assert settings.debug is True
            assert settings.secret_key == "test-secret-key"
            assert settings.database_url == "postgresql://test:test@localhost:5432/test"
            assert settings.log_level == "DEBUG"

    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                settings = Settings()
                assert settings.log_level == level

        # Invalid log level
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            with pytest.raises(ValidationError):
                Settings()

    def test_secret_key_validation(self):
        """Test secret key validation."""
        # Test with debug mode (should allow empty secret key)
        with patch.dict(os.environ, {"DEBUG": "true", "SECRET_KEY": ""}):
            settings = Settings()
            assert settings.secret_key == ""

        # Test with production mode and no secret key (should fail)
        with patch.dict(os.environ, {"DEBUG": "false", "SECRET_KEY": ""}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "SECRET_KEY is required in production" in str(exc_info.value)

        # Test with short secret key (should fail)
        with patch.dict(os.environ, {"DEBUG": "false", "SECRET_KEY": "short"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "SECRET_KEY must be at least 32 characters long" in str(exc_info.value)

        # Test with valid secret key (should pass)
        valid_key = "a" * 32  # 32 character key
        with patch.dict(os.environ, {"DEBUG": "false", "SECRET_KEY": valid_key}):
            settings = Settings()
            assert settings.secret_key == valid_key

    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from string."""
        # Test with JSON array format (Pydantic v2 preferred)
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": '["http://localhost:3000","https://example.com"]'},
        ):
            settings = Settings()
            assert settings.cors_origins == [
                "http://localhost:3000",
                "https://example.com",
            ]

    def test_cors_methods_parsing(self):
        """Test CORS methods parsing from string."""
        # Test with JSON array format (Pydantic v2 preferred)
        with patch.dict(os.environ, {"CORS_ALLOW_METHODS": '["GET","POST","PUT","DELETE"]'}):
            settings = Settings()
            assert settings.cors_allow_methods == ["GET", "POST", "PUT", "DELETE"]

    def test_cors_headers_parsing(self):
        """Test CORS headers parsing from string."""
        # Test with JSON array format (Pydantic v2 preferred)
        with patch.dict(os.environ, {"CORS_ALLOW_HEADERS": '["Authorization","Content-Type"]'}):
            settings = Settings()
            assert settings.cors_allow_headers == ["Authorization", "Content-Type"]

    def test_celery_content_parsing(self):
        """Test Celery content types parsing from string."""
        # Test with JSON array format (Pydantic v2 preferred)
        with patch.dict(os.environ, {"CELERY_ACCEPT_CONTENT": '["json","pickle"]'}):
            settings = Settings()
            assert settings.celery_accept_content == ["json", "pickle"]

    def test_database_url_methods(self):
        """Test database URL methods."""
        settings = Settings()

        # Sync URL
        sync_url = settings.get_database_url_sync()
        assert sync_url == "postgresql://algotrading:algotrading@localhost:5432/algotrading"

        # Async URL
        async_url = settings.get_database_url_async()
        assert (
            async_url == "postgresql+asyncpg://algotrading:algotrading@localhost:5432/algotrading"
        )

    def test_environment_detection(self):
        """Test environment detection methods."""
        # Development mode
        with patch.dict(os.environ, {"DEBUG": "true"}):
            settings = Settings()
            assert settings.is_development() is True
            assert settings.is_production() is False

        # Production mode (with valid secret key)
        with patch.dict(os.environ, {"DEBUG": "false", "SECRET_KEY": "a" * 32}):
            settings = Settings()
            assert settings.is_development() is False
            assert settings.is_production() is True

    def test_cors_config(self):
        """Test CORS configuration method."""
        settings = Settings()
        cors_config = settings.get_cors_config()

        expected_config = {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

        assert cors_config == expected_config

    def test_celery_config(self):
        """Test Celery configuration method."""
        settings = Settings()
        celery_config = settings.get_celery_config()

        expected_config = {
            "broker_url": "redis://localhost:6379/1",
            "result_backend": "redis://localhost:6379/2",
            "task_serializer": "json",
            "result_serializer": "json",
            "accept_content": ["json"],
            "timezone": "UTC",
            "enable_utc": True,
        }

        assert celery_config == expected_config


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    def test_get_settings(self):
        """Test get_settings function."""
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert settings.app_name == "AlgoTrading MVP"

    def test_get_database_url(self):
        """Test get_database_url function."""
        url = get_database_url()
        assert url == "postgresql://algotrading:algotrading@localhost:5432/algotrading"

    def test_get_redis_url(self):
        """Test get_redis_url function."""
        url = get_redis_url()
        assert url == "redis://localhost:6379/0"

    def test_get_secret_key(self):
        """Test get_secret_key function."""
        from app.core.config import get_secret_key

        key = get_secret_key()
        assert key == ""  # Changed to empty string (new default)

    def test_is_debug_mode(self):
        """Test is_debug_mode function."""
        from app.core.config import is_debug_mode

        debug = is_debug_mode()
        assert debug is True  # Changed because DEBUG=true is set in test_main.py

    def test_get_cors_config(self):
        """Test get_cors_config function."""
        from app.core.config import get_cors_config

        config = get_cors_config()
        assert config["allow_origins"] == ["*"]
        assert config["allow_credentials"] is True

    def test_get_celery_config(self):
        """Test get_celery_config function."""
        from app.core.config import get_celery_config

        config = get_celery_config()
        assert config["broker_url"] == "redis://localhost:6379/1"
        assert config["result_backend"] == "redis://localhost:6379/2"


class TestConfigurationIntegration:
    """Test configuration integration with FastAPI."""

    def test_settings_singleton(self):
        """Test that settings instance is a singleton."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_configuration_import(self):
        """Test that configuration can be imported correctly."""
        from app.core.config import get_settings

        # Test that get_settings works
        settings = get_settings()
        assert settings is not None
        assert get_settings() is not None
        assert settings.app_name == "AlgoTrading MVP"

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Override Test",
                "SECRET_KEY": "override-secret",
                "DATABASE_URL": "postgresql://override:override@localhost:5432/override",
            },
        ):
            # Create new settings instance to pick up environment changes
            settings = Settings()

            assert settings.app_name == "Override Test"
            assert settings.secret_key == "override-secret"
            assert settings.database_url == "postgresql://override:override@localhost:5432/override"

    def test_boolean_environment_variables(self):
        """Test boolean environment variable parsing."""
        # Test true values
        true_values = ["true", "True", "TRUE", "1"]
        for value in true_values:
            with patch.dict(os.environ, {"DEBUG": value}):
                settings = Settings()
                assert settings.debug is True

        # Test false values (with valid secret key for production mode)
        false_values = ["false", "False", "FALSE", "0"]
        for value in false_values:
            with patch.dict(os.environ, {"DEBUG": value, "SECRET_KEY": "a" * 32}):
                settings = Settings()
                assert settings.debug is False

    def test_numeric_environment_variables(self):
        """Test numeric environment variable parsing."""
        with patch.dict(
            os.environ,
            {
                "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
                "DATABASE_POOL_SIZE": "20",
                "MAX_POSITION_SIZE": "50000.0",
                "RISK_FREE_RATE": "0.03",
            },
        ):
            settings = Settings()

            assert settings.access_token_expire_minutes == 60
            assert settings.database_pool_size == 20
            assert settings.max_position_size == 50000.0
            assert settings.risk_free_rate == 0.03

    def test_list_environment_variables(self):
        """Test list environment variable parsing."""
        # Use JSON array format for Pydantic v2
        with patch.dict(
            os.environ,
            {
                "CORS_ORIGINS": '["http://localhost:3000","https://app.example.com","https://admin.example.com"]',
                "CORS_ALLOW_METHODS": '["GET","POST","PUT","DELETE","OPTIONS"]',
                "CELERY_ACCEPT_CONTENT": '["json","pickle","msgpack"]',
            },
        ):
            settings = Settings()

            assert settings.cors_origins == [
                "http://localhost:3000",
                "https://app.example.com",
                "https://admin.example.com",
            ]
            assert settings.cors_allow_methods == [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
            ]
            assert settings.celery_accept_content == ["json", "pickle", "msgpack"]
