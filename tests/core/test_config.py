"""
Comprehensive tests for app/core/config.py.

Tests the Settings configuration class with focus on:
- P1: extra="forbid" catches typos in environment variables
- Settings loaded from environment
- SECRET_KEY validation (length and weak keys)
- Log level validation
- CORS parsing (string and list)
- Database URL async conversion
- Singleton pattern
- Pydantic validation errors
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ConfigDict, ValidationError

# Import directly from shared/config/config.py (was previously app/core/config.py)
config_py_path = Path(__file__).parent.parent.parent / "app" / "shared" / "config" / "config.py"

# Import the module directly using importlib to avoid the config/ directory
import importlib.util

spec = importlib.util.spec_from_file_location("app.core.config_module", config_py_path)
config_module = importlib.util.module_from_spec(spec)
sys.modules["app.core.config_module"] = config_module
spec.loader.exec_module(config_module)

# Import what we need from the loaded module
Settings = config_module.Settings
get_global_settings = config_module.get_global_settings
get_settings = config_module.get_settings
get_database_url = config_module.get_database_url
get_redis_url = config_module.get_redis_url
get_secret_key = config_module.get_secret_key
is_debug_mode = config_module.is_debug_mode
get_cors_config = config_module.get_cors_config
get_celery_config = config_module.get_celery_config
_settings_instance = config_module._settings_instance


@pytest.fixture
def clean_env():
    """
    Fixture to provide a clean environment for testing.

    This clears environment variables and prevents loading from .env file.
    """
    # Save original environment
    original_env = os.environ.copy()

    # Clear all environment variables that might interfere
    env_prefixes = (
        'ALPACA_',
        'IB_',
        'REDIS_',
        'DB_',
        'LOG_',
        'API_',
        'SECRET_',
        'DEBUG',
        'TESTING',
        'DASHBOARD_',
        'CORS_',
        'CELERY_',
        'ENVIRONMENT',
        'SMTP_',
        'NOTIFICATION_',
        'TELEGRAM_',
        'NEO4J_',
        'MLFLOW_',
        'DAGSTER_',
        'POLYGON_',
        'ALPHA_',
        'YAHOO_',
        'FMP_',
        'NEWS_',
        'MARKETAUX_',
        'TWITTER_',
        'REDDIT_',
        'QUESTDB_',
        'BACKTESTING_',
        'PAPER_',
        'DEFAULT_',
        'RISK_',
        'MAX_',
        'STRATEGY_',
        'RATE_LIMIT_',
        'PASSWORD_',
        'TOKEN_',
        'ACCESS_TOKEN_',
        'REFRESH_TOKEN_',
        'PORT',
        'HOST',
        'ALLOW_WEAK_',
    )
    env_keys_to_clear = [k for k in os.environ if k.startswith(env_prefixes)]
    for key in env_keys_to_clear:
        os.environ.pop(key, None)

    # Temporarily rename .env file to prevent loading
    import shutil
    from pathlib import Path as FilePath

    project_root = FilePath(__file__).parent.parent.parent
    env_file = project_root / ".env"
    env_backup = None

    if env_file.exists():
        # Create a temp backup path
        env_backup = env_file.with_suffix('.env.backup_test')
        shutil.move(str(env_file), str(env_backup))

    yield

    # Restore .env file if it was backed up
    if env_backup and env_backup.exists():
        shutil.move(str(env_backup), str(env_file))

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def settings_with_no_env_file(clean_env):
    """
    Fixture that creates Settings without loading from .env file.

    This is needed because .env file may contain extra fields that would
    trigger extra="forbid" validation.
    """

    # Create a Settings subclass that doesn't load from .env
    class TestSettings(Settings):
        model_config = ConfigDict(
            env_file=None,  # Don't load from .env
            env_file_encoding="utf-8",
            case_sensitive=False,
            env_nested_delimiter="__",
            extra="forbid",
        )

    return TestSettings


class TestSettingsExtraForbid:
    """
    Test suite for P1: extra="forbid" behavior.

    This ensures that typos in environment variables are caught early.
    """

    def test_extra_forbid_rejects_unknown_fields(self, settings_with_no_env_file):
        """
        Test that extra="forbid" rejects unknown environment variables.

        This is the P1 fix - typos in env vars should raise ValidationError.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        env_vars = {
            "SECRET_KEY": "a" * 32,
            "UNKNOWN_FIELD": "some_value",  # This should cause validation error
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TestSettings(**env_vars)

        # Check that the error message mentions extra fields
        error_detail = str(exc_info.value)
        assert "extra" in error_detail.lower() or "forbidden" in error_detail.lower()
        assert "UNKNOWN_FIELD" in error_detail

    def test_extra_forbid_with_typo_in_secret_key(self, settings_with_no_env_file):
        """
        Test that typos in SECRET_KEY (like SECRETT_KEY) are caught.

        This demonstrates the value of extra="forbid".
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        env_vars = {
            "SECRETT_KEY": "a" * 32,  # Typo: double T
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TestSettings(**env_vars)

        error_detail = str(exc_info.value)
        # Should complain about missing secret_key and unknown secrett_key
        assert "secret_key" in error_detail.lower()

    def test_extra_forbid_with_valid_fields_only(self, settings_with_no_env_file):
        """
        Test that valid fields pass validation with extra="forbid".
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act - use environment variables instead of kwargs
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32, "DEBUG": "true", "LOG_LEVEL": "INFO"}):
            settings = TestSettings()

        # Assert
        assert settings.secret_key == "a" * 32
        assert settings.debug is True
        assert settings.log_level == "INFO"

    def test_extra_forbid_multiple_unknown_fields(self, settings_with_no_env_file):
        """
        Test that multiple unknown fields are all reported.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        env_vars = {
            "SECRET_KEY": "a" * 32,
            "UNK_VAR_1": "value1",
            "UNK_VAR_2": "value2",
            "UNK_VAR_3": "value3",
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TestSettings(**env_vars)

        error_detail = str(exc_info.value)
        # Should mention all unknown fields
        assert "UNK_VAR_1" in error_detail
        assert "UNK_VAR_2" in error_detail
        assert "UNK_VAR_3" in error_detail


class TestSettingsDefaults:
    """
    Test suite for default values in Settings.
    """

    def test_default_application_settings(self, settings_with_no_env_file):
        """
        Test default application settings are loaded correctly.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act - pass SECRET_KEY via environment to avoid extra field error
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            settings = TestSettings()

        # Assert - Application Settings
        assert settings.app_name == "AlgoTrading MVP"
        assert settings.app_version == "1.0.0"
        assert settings.app_description == "Algorithmic Trading System MVP"
        assert settings.debug is False

    def test_default_api_settings(self, settings_with_no_env_file):
        """
        Test default API settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            settings = TestSettings()

        # Assert - API Settings
        assert settings.api_v1_prefix == "/api/v1"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.api_reload is False

    def test_default_database_settings(self, settings_with_no_env_file):
        """
        Test default database settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act - explicitly clear DATABASE_URL from environment to test defaults
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}, clear=True):
            settings = TestSettings()

        # Assert - Database Settings
        assert (
            settings.database_url
            == "postgresql://algotrading:algotrading@localhost:5432/algotrading"
        )
        assert settings.database_echo is False
        assert settings.database_pool_size == 10
        assert settings.database_max_overflow == 20

    def test_default_redis_settings(self, settings_with_no_env_file):
        """
        Test default Redis settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            settings = TestSettings()

        # Assert - Redis Settings
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.redis_password is None
        assert settings.redis_db == 0
        assert settings.redis_max_connections == 10

    def test_default_trading_settings(self, settings_with_no_env_file):
        """
        Test default trading settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            settings = TestSettings()

        # Assert - Trading Settings
        assert settings.default_currency == "USD"
        assert settings.max_position_size == 10000.0
        assert settings.risk_free_rate == 0.02

    def test_default_paper_trading_settings(self, settings_with_no_env_file):
        """
        Test default paper trading settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            settings = TestSettings()

        # Assert - Paper Trading Settings
        assert settings.paper_trading_initial_capital == 100000.0
        assert settings.paper_trading_commission_per_trade == 1.0


class TestSecretKeyValidation:
    """
    Test suite for SECRET_KEY validation.

    P1: SECRET_KEY must be at least 32 characters in ALL environments.
    """

    def test_secret_key_too_short_raises_error(self, settings_with_no_env_file):
        """
        Test that SECRET_KEY shorter than 32 characters raises ValidationError.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        short_keys = [
            "",  # Empty
            "a" * 1,  # 1 character
            "a" * 10,  # 10 characters
            "a" * 31,  # 31 characters - just below threshold
        ]

        # Act & Assert
        for short_key in short_keys:
            with pytest.raises(ValidationError) as exc_info:
                TestSettings(secret_key=short_key)

            error_msg = str(exc_info.value)
            assert "32 characters" in error_msg
            assert f"{len(short_key)}" in error_msg

    def test_secret_key_exactly_32_characters_passes(self, settings_with_no_env_file):
        """
        Test that SECRET_KEY with exactly 32 characters passes validation.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        valid_key = "a" * 32

        # Act
        settings = TestSettings(secret_key=valid_key)

        # Assert
        assert settings.secret_key == valid_key

    def test_secret_key_longer_than_32_characters_passes(self, settings_with_no_env_file):
        """
        Test that SECRET_KEY longer than 32 characters passes validation.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        valid_key = "a" * 64

        # Act
        settings = TestSettings(secret_key=valid_key)

        # Assert
        assert settings.secret_key == valid_key

    def test_weak_secret_key_rejected_by_default(self, settings_with_no_env_file):
        """
        Test that known weak keys are rejected by default.

        This requires ALLOW_WEAK_SECRET_KEY=true to override.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        # weak keys from the config (ensure they're at least 32 chars)
        weak_keys = [
            'your_secret_key_change_this_in_production',
            '0123456789abcdef0123456789abcdef',
            'change-this-secret-key-in-production-min-32-chars',
            '12345678901234567890123456789012',
        ]

        # Act & Assert - each weak key should fail
        for weak_key in weak_keys:
            with pytest.raises(ValidationError) as exc_info:
                TestSettings(secret_key=weak_key)

            error_msg = str(exc_info.value)
            assert "Weak SECRET_KEY" in error_msg or "weak" in error_msg.lower()

    def test_weak_secret_key_allowed_with_override(self, settings_with_no_env_file):
        """
        Test that weak keys are allowed when ALLOW_WEAK_SECRET_KEY=true.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        weak_key = '12345678901234567890123456789012'  # 32 chars - weak pattern

        # Act & Assert - with override, should pass
        with patch.dict(os.environ, {'ALLOW_WEAK_SECRET_KEY': 'true'}):
            settings = TestSettings(secret_key=weak_key)
            assert settings.secret_key == weak_key

    def test_valid_secret_key_passes(self, settings_with_no_env_file):
        """
        Test that a valid, strong secret key passes validation.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        # generate a strong key
        strong_key = "super_secure_random_key_with_32_chars_or_more"

        # Act
        settings = TestSettings(secret_key=strong_key)

        # Assert
        assert settings.secret_key == strong_key


class TestLogLevelValidation:
    """
    Test suite for log level validation.
    """

    def test_valid_log_levels_uppercase(self, settings_with_no_env_file):
        """
        Test that valid uppercase log levels pass validation.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        # Act & Assert
        for level in valid_levels:
            settings = TestSettings(secret_key="a" * 32, log_level=level)
            assert settings.log_level == level

    def test_valid_log_levels_lowercase_converted_to_uppercase(self, settings_with_no_env_file):
        """
        Test that lowercase log levels are converted to uppercase.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        lowercase_levels = ["debug", "info", "warning", "error", "critical"]

        # Act & Assert
        for level in lowercase_levels:
            settings = TestSettings(secret_key="a" * 32, log_level=level)
            assert settings.log_level == level.upper()

    def test_invalid_log_level_raises_error(self, settings_with_no_env_file):
        """
        Test that invalid log levels raise ValidationError.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        invalid_levels = ["TRACE", "VERBOSE", "INVALID", "NOTAREALEVEL", "", "123"]

        # Act & Assert
        for level in invalid_levels:
            with pytest.raises(ValidationError) as exc_info:
                TestSettings(secret_key="a" * 32, log_level=level)

            error_msg = str(exc_info.value)
            assert "Log level" in error_msg or "log_level" in str(exc_info.value)


class TestCORSParsing:
    """
    Test suite for CORS parsing from string or list.
    """

    def test_cors_origins_as_list(self, settings_with_no_env_file):
        """
        Test that CORS origins can be provided as a list.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        origins = ["http://localhost:3000", "https://example.com"]

        # Act
        settings = TestSettings(secret_key="a" * 32, cors_origins=origins)

        # Assert
        assert settings.cors_origins == origins

    def test_cors_origins_as_string(self, settings_with_no_env_file):
        """
        Test that CORS origins can be provided as a comma-separated string.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        origins_string = "http://localhost:3000,https://example.com,http://localhost:8080"

        # Act
        settings = TestSettings(secret_key="a" * 32, cors_origins=origins_string)

        # Assert
        assert settings.cors_origins == [
            "http://localhost:3000",
            "https://example.com",
            "http://localhost:8080",
        ]

    def test_cors_origins_string_with_spaces(self, settings_with_no_env_file):
        """
        Test that CORS origins string with spaces are trimmed.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        origins_string = " http://localhost:3000 , https://example.com , http://localhost:8080 "

        # Act
        settings = TestSettings(secret_key="a" * 32, cors_origins=origins_string)

        # Assert
        assert settings.cors_origins == [
            "http://localhost:3000",
            "https://example.com",
            "http://localhost:8080",
        ]

    def test_cors_methods_as_list(self, settings_with_no_env_file):
        """
        Test that CORS methods can be provided as a list.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        methods = ["GET", "POST", "PUT", "DELETE"]

        # Act
        settings = TestSettings(secret_key="a" * 32, cors_allow_methods=methods)

        # Assert
        assert settings.cors_allow_methods == methods

    def test_cors_methods_as_string(self, settings_with_no_env_file):
        """
        Test that CORS methods can be provided as a comma-separated string.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        methods_string = "GET,POST,PUT,DELETE,PATCH"

        # Act
        settings = TestSettings(secret_key="a" * 32, cors_allow_methods=methods_string)

        # Assert
        assert settings.cors_allow_methods == ["GET", "POST", "PUT", "DELETE", "PATCH"]

    def test_cors_headers_as_list(self, settings_with_no_env_file):
        """
        Test that CORS headers can be provided as a list.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        headers = ["Content-Type", "Authorization", "X-API-Key"]

        # Act
        settings = TestSettings(secret_key="a" * 32, cors_allow_headers=headers)

        # Assert
        assert settings.cors_allow_headers == headers

    def test_cors_headers_as_string(self, settings_with_no_env_file):
        """
        Test that CORS headers can be provided as a comma-separated string.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        headers_string = "Content-Type,Authorization,X-API-Key,X-Requested-With"

        # Act
        settings = TestSettings(secret_key="a" * 32, cors_allow_headers=headers_string)

        # Assert
        assert settings.cors_allow_headers == [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Requested-With",
        ]

    def test_celery_accept_content_as_list(self, settings_with_no_env_file):
        """
        Test that celery_accept_content can be provided as a list.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        content_types = ["json", "msgpack"]

        # Act
        settings = TestSettings(secret_key="a" * 32, celery_accept_content=content_types)

        # Assert
        assert settings.celery_accept_content == content_types

    def test_celery_accept_content_as_string(self, settings_with_no_env_file):
        """
        Test that celery_accept_content can be provided as a comma-separated string.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        content_string = "json,msgpack,pickle"

        # Act
        settings = TestSettings(secret_key="a" * 32, celery_accept_content=content_string)

        # Assert
        assert settings.celery_accept_content == ["json", "msgpack", "pickle"]


class TestDatabaseURLConversion:
    """
    Test suite for database URL async conversion.
    """

    def test_get_database_url_sync_returns_original(self, settings_with_no_env_file):
        """
        Test that get_database_url_sync returns the original URL.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(
            secret_key="a" * 32, database_url="postgresql://user:pass@localhost/db"
        )

        # Act
        sync_url = settings.get_database_url_sync()

        # Assert
        assert sync_url == "postgresql://user:pass@localhost/db"

    def test_get_database_url_async_postgresql(self, settings_with_no_env_file):
        """
        Test async URL conversion for PostgreSQL.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(
            secret_key="a" * 32, database_url="postgresql://user:pass@localhost:5432/mydb"
        )

        # Act
        async_url = settings.get_database_url_async()

        # Assert
        assert async_url == "postgresql+asyncpg://user:pass@localhost:5432/mydb"
        assert "asyncpg" in async_url

    def test_get_database_url_async_sqlite(self, settings_with_no_env_file):
        """
        Test async URL conversion for SQLite.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32, database_url="sqlite:///./data/test.db")

        # Act
        async_url = settings.get_database_url_async()

        # Assert
        assert async_url == "sqlite+aiosqlite:///./data/test.db"
        assert "aiosqlite" in async_url

    def test_get_database_url_async_other_databases(self, settings_with_no_env_file):
        """
        Test that other database URLs are returned unchanged.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32, database_url="mysql://user:pass@localhost/db")

        # Act
        async_url = settings.get_database_url_async()

        # Assert
        assert async_url == "mysql://user:pass@localhost/db"

    def test_get_database_url_async_with_postgresql_prefix(self, settings_with_no_env_file):
        """
        Test async URL conversion when URL already has postgresql+asyncpg prefix.
        """
        # Arrange - URL already async
        TestSettings = settings_with_no_env_file
        settings = TestSettings(
            secret_key="a" * 32, database_url="postgresql+asyncpg://user:pass@localhost/db"
        )

        # Act
        async_url = settings.get_database_url_async()

        # Assert - should remain unchanged (only replaces first occurrence)
        assert "asyncpg" in async_url


class TestEnvironmentModeMethods:
    """
    Test suite for environment mode detection methods.
    """

    def test_is_production_when_debug_false(self, settings_with_no_env_file):
        """
        Test that is_production returns True when debug is False.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32, debug=False)

        # Act & Assert
        assert settings.is_production() is True
        assert settings.is_development() is False

    def test_is_development_when_debug_true(self, settings_with_no_env_file):
        """
        Test that is_development returns True when debug is True.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32, debug=True)

        # Act & Assert
        assert settings.is_development() is True
        assert settings.is_production() is False


class TestCORSConfig:
    """
    Test suite for get_cors_config method.
    """

    def test_get_cors_config_returns_dict(self, settings_with_no_env_file):
        """
        Test that get_cors_config returns proper configuration dict.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(
            secret_key="a" * 32,
            cors_origins=["http://localhost:3000"],
            cors_allow_credentials=True,
            cors_allow_methods=["GET", "POST"],
            cors_allow_headers=["Content-Type"],
        )

        # Act
        cors_config = settings.get_cors_config()

        # Assert
        assert isinstance(cors_config, dict)
        assert cors_config["allow_origins"] == ["http://localhost:3000"]
        assert cors_config["allow_credentials"] is True
        assert cors_config["allow_methods"] == ["GET", "POST"]
        assert cors_config["allow_headers"] == ["Content-Type"]

    def test_get_cors_config_with_default_values(self, settings_with_no_env_file):
        """
        Test that get_cors_config works with default CORS values.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32)

        # Act
        cors_config = settings.get_cors_config()

        # Assert
        assert cors_config["allow_origins"] == ["*"]
        assert cors_config["allow_credentials"] is True
        assert cors_config["allow_methods"] == ["*"]
        assert cors_config["allow_headers"] == ["*"]


class TestCeleryConfig:
    """
    Test suite for get_celery_config method.
    """

    def test_get_celery_config_returns_dict(self, settings_with_no_env_file):
        """
        Test that get_celery_config returns proper configuration dict.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(
            secret_key="a" * 32,
            celery_broker_url="redis://localhost:6379/1",
            celery_result_backend="redis://localhost:6379/2",
            celery_task_serializer="json",
            celery_result_serializer="json",
            celery_accept_content=["json"],
        )

        # Act
        celery_config = settings.get_celery_config()

        # Assert
        assert isinstance(celery_config, dict)
        assert celery_config["broker_url"] == "redis://localhost:6379/1"
        assert celery_config["result_backend"] == "redis://localhost:6379/2"
        assert celery_config["task_serializer"] == "json"
        assert celery_config["result_serializer"] == "json"
        assert celery_config["accept_content"] == ["json"]
        assert celery_config["timezone"] == "UTC"
        assert celery_config["enable_utc"] is True


class TestSingletonPattern:
    """
    Test suite for singleton pattern in get_global_settings.

    Ensures that the same instance is returned across multiple calls.
    """

    def test_get_global_settings_returns_same_instance(self, clean_env):
        """
        Test that get_global_settings returns the same instance on multiple calls.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        # Set required environment variables
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Act
            settings1 = get_global_settings()
            settings2 = get_global_settings()
            settings3 = get_global_settings()

            # Assert
            assert settings1 is settings2
            assert settings2 is settings3
            assert id(settings1) == id(settings2) == id(settings3)

    def test_get_settings_returns_global_settings(self, clean_env):
        """
        Test that get_settings returns the global settings instance.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Arrange
            global_settings = get_global_settings()

            # Act
            settings = get_settings()

            # Assert
            assert settings is global_settings

    def test_get_database_url_returns_from_global_settings(self, clean_env):
        """
        Test that get_database_url returns URL from global settings.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Arrange
            get_global_settings()  # Ensure instance exists

            # Act
            url = get_database_url()

            # Assert
            assert isinstance(url, str)
            assert url == get_global_settings().database_url

    def test_get_redis_url_returns_from_global_settings(self, clean_env):
        """
        Test that get_redis_url returns URL from global settings.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Arrange
            get_global_settings()  # Ensure instance exists

            # Act
            url = get_redis_url()

            # Assert
            assert isinstance(url, str)
            assert url == get_global_settings().redis_url

    def test_get_secret_key_returns_from_global_settings(self, clean_env):
        """
        Test that get_secret_key returns key from global settings.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Arrange
            get_global_settings()  # Ensure instance exists

            # Act
            key = get_secret_key()

            # Assert
            assert isinstance(key, str)
            assert key == get_global_settings().secret_key

    def test_is_debug_mode_returns_from_global_settings(self, clean_env):
        """
        Test that is_debug_mode returns debug flag from global settings.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Arrange
            get_global_settings()  # Ensure instance exists

            # Act
            debug = is_debug_mode()

            # Assert
            assert isinstance(debug, bool)
            assert debug == get_global_settings().debug

    def test_get_cors_config_returns_from_global_settings(self, clean_env):
        """
        Test that get_cors_config returns config from global settings.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Arrange
            get_global_settings()  # Ensure instance exists

            # Act
            config = get_cors_config()

            # Assert
            assert isinstance(config, dict)
            assert config == get_global_settings().get_cors_config()

    def test_get_celery_config_returns_from_global_settings(self, clean_env):
        """
        Test that get_celery_config returns config from global settings.
        """
        # Arrange - reset the global settings instance
        config_module._settings_instance = None

        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            # Arrange
            get_global_settings()  # Ensure instance exists

            # Act
            config = get_celery_config()

            # Assert
            assert isinstance(config, dict)
            assert config == get_global_settings().get_celery_config()


class TestEnvironmentVariableLoading:
    """
    Test suite for loading settings from environment variables.
    """

    def test_load_secret_key_from_env(self, clean_env):
        """
        Test that SECRET_KEY can be loaded from environment variable.
        """
        # Arrange
        test_key = "test_secret_key_with_32_characters_minimum"
        os.environ["SECRET_KEY"] = test_key

        # Act
        # Create a TestSettings class that doesn't load from .env file
        class TestSettings(Settings):
            model_config = ConfigDict(env_file=None, extra="forbid")

        settings = TestSettings()

        # Assert
        assert settings.secret_key == test_key

    def test_load_debug_from_env(self, clean_env):
        """
        Test that DEBUG can be loaded from environment variable.
        """
        # Arrange
        os.environ["SECRET_KEY"] = "a" * 32
        os.environ["DEBUG"] = "true"

        # Act
        class TestSettings(Settings):
            model_config = ConfigDict(env_file=None, extra="forbid")

        settings = TestSettings()

        # Assert
        assert settings.debug is True

    def test_load_log_level_from_env(self, clean_env):
        """
        Test that LOG_LEVEL can be loaded from environment variable.
        """
        # Arrange
        os.environ["SECRET_KEY"] = "a" * 32
        os.environ["LOG_LEVEL"] = "DEBUG"

        # Act
        class TestSettings(Settings):
            model_config = ConfigDict(env_file=None, extra="forbid")

        settings = TestSettings()

        # Assert
        assert settings.log_level == "DEBUG"

    def test_case_insensitive_env_vars(self, clean_env):
        """
        Test that environment variables are case-insensitive.
        """
        # Arrange
        os.environ["secret_key"] = "b" * 32  # lowercase
        os.environ["DEBUG"] = "true"  # uppercase

        # Act
        class TestSettings(Settings):
            model_config = ConfigDict(env_file=None, extra="forbid")

        settings = TestSettings()

        # Assert
        assert settings.secret_key == "b" * 32
        assert settings.debug is True


class TestOptionalFields:
    """
    Test suite for optional fields in Settings.
    """

    def test_optional_api_keys_default_to_none(self, settings_with_no_env_file):
        """
        Test that optional API key fields default to None.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32)

        # Assert - API Keys
        assert settings.ib_api_key is None
        assert settings.ib_secret is None
        assert settings.alpaca_api_key is None
        assert settings.alpaca_api_secret is None
        assert settings.binance_api_key is None
        assert settings.binance_secret is None
        assert settings.alpha_vantage_api_key is None
        assert settings.polygon_api_key is None

    def test_optional_api_keys_can_be_set(self, settings_with_no_env_file):
        """
        Test that optional API key fields can be set.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings = TestSettings(
            secret_key="a" * 32,
            ib_api_key="test_ib_key",
            alpaca_api_key="test_alpaca_key",
            alpha_vantage_api_key="test_av_key",
        )

        # Assert
        assert settings.ib_api_key == "test_ib_key"
        assert settings.alpaca_api_key == "test_alpaca_key"
        assert settings.alpha_vantage_api_key == "test_av_key"

    def test_redis_password_optional(self, settings_with_no_env_file):
        """
        Test that redis_password is optional.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings1 = TestSettings(secret_key="a" * 32)
        settings2 = TestSettings(secret_key="a" * 32, redis_password="my_redis_pass")

        # Assert
        assert settings1.redis_password is None
        assert settings2.redis_password == "my_redis_pass"

    def test_log_file_optional(self, settings_with_no_env_file):
        """
        Test that log_file is optional.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings1 = TestSettings(secret_key="a" * 32)
        settings2 = TestSettings(secret_key="a" * 32, log_file="/var/log/algotrading.log")

        # Assert
        assert settings1.log_file is None
        assert settings2.log_file == "/var/log/algotrading.log"


class TestSecuritySettings:
    """
    Test suite for security-related settings.
    """

    def test_password_security_defaults(self, settings_with_no_env_file):
        """
        Test default password security settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32)

        # Assert
        assert settings.password_min_length == 8
        assert settings.password_require_uppercase is True
        assert settings.password_require_lowercase is True
        assert settings.password_require_numbers is True
        assert settings.password_require_special is True

    def test_password_security_can_be_configured(self, settings_with_no_env_file):
        """
        Test that password security settings can be configured.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings = TestSettings(
            secret_key="a" * 32,
            password_min_length=12,
            password_require_uppercase=False,
            password_require_special=False,
        )

        # Assert
        assert settings.password_min_length == 12
        assert settings.password_require_uppercase is False
        assert settings.password_require_special is False

    def test_token_expiration_defaults(self, settings_with_no_env_file):
        """
        Test default token expiration settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32)

        # Assert
        assert settings.access_token_expire_minutes == 30
        assert settings.refresh_token_expire_days == 7

    def test_token_expiration_can_be_configured(self, settings_with_no_env_file):
        """
        Test that token expiration can be configured.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings = TestSettings(
            secret_key="a" * 32,
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
        )

        # Assert
        assert settings.access_token_expire_minutes == 60
        assert settings.refresh_token_expire_days == 30

    def test_rate_limiting_defaults(self, settings_with_no_env_file):
        """
        Test default rate limiting settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32)

        # Assert
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60

    def test_rate_limiting_can_be_configured(self, settings_with_no_env_file):
        """
        Test that rate limiting can be configured.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings = TestSettings(
            secret_key="a" * 32,
            rate_limit_requests=200,
            rate_limit_window=120,
        )

        # Assert
        assert settings.rate_limit_requests == 200
        assert settings.rate_limit_window == 120


class TestAlpacaSettings:
    """
    Test suite for Alpaca-specific settings.
    """

    def test_alpaca_defaults(self, settings_with_no_env_file):
        """
        Test default Alpaca settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32)

        # Assert
        assert settings.alpaca_base_url == "https://paper-api.alpaca.markets"
        assert settings.alpaca_paper_trading is True

    def test_alpaca_settings_can_be_configured(self, settings_with_no_env_file):
        """
        Test that Alpaca settings can be configured.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings = TestSettings(
            secret_key="a" * 32,
            alpaca_api_key="test_alpaca_key",
            alpaca_api_secret="test_alpaca_secret",
            alpaca_base_url="https://api.alpaca.markets",
            alpaca_paper_trading=False,
        )

        # Assert
        assert settings.alpaca_api_key == "test_alpaca_key"
        assert settings.alpaca_api_secret == "test_alpaca_secret"
        assert settings.alpaca_base_url == "https://api.alpaca.markets"
        assert settings.alpaca_paper_trading is False


class TestDashboardSettings:
    """
    Test suite for dashboard settings.
    """

    def test_dashboard_defaults(self, settings_with_no_env_file):
        """
        Test default dashboard settings.
        """
        # Arrange
        TestSettings = settings_with_no_env_file
        settings = TestSettings(secret_key="a" * 32)

        # Assert
        assert settings.dashboard_host == "localhost"
        assert settings.dashboard_port == 8501

    def test_dashboard_settings_can_be_configured(self, settings_with_no_env_file):
        """
        Test that dashboard settings can be configured.
        """
        # Arrange
        TestSettings = settings_with_no_env_file

        # Act
        settings = TestSettings(
            secret_key="a" * 32,
            dashboard_host="0.0.0.0",
            dashboard_port=8502,
        )

        # Assert
        assert settings.dashboard_host == "0.0.0.0"
        assert settings.dashboard_port == 8502
