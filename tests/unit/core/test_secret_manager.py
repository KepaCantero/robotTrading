"""
Test Secret Manager - Rule 28 Compliance

Tests for centralized secret management following:
- Rule 28: Security and secrets management
- Rule 25: Clean code principles
- Rule 16: Cosmic Python (configuration as service)

Test Coverage:
1. No hardcoded secrets in code
2. Environment variable loading
3. Secret validation
4. Connection string building
5. Secret masking in logs
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.core.secret_manager import (
    SecretManager,
    get_secret,
    require_secret,
    validate_secrets_configured,
    get_connection_string,
    mask_secret,
    is_production,
    SecretDefinition,
    SecretCategory,
    SecretValidationError,
    SecretNotConfiguredError,
    SecretValidationReport,
)


class TestSecretManager:
    """Test SecretManager class."""

    def test_get_secret_with_value(self):
        """Test getting a secret that exists."""
        with patch.dict(os.environ, {'TEST_SECRET': 'my_secret_value'}):
            manager = SecretManager()
            value = manager.get('TEST_SECRET', mask=False)
            assert value == 'my_secret_value'

    def test_get_secret_with_default(self):
        """Test getting a secret with default value."""
        manager = SecretManager()
        value = manager.get('NONEXISTENT_SECRET', default='default_value')
        assert value == 'default_value'

    def test_get_secret_missing_no_default(self):
        """Test getting missing secret without default raises error."""
        manager = SecretManager()
        with pytest.raises(SecretNotConfiguredError):
            manager.get('NONEXISTENT_SECRET')

    def test_require_secret_success(self):
        """Test requiring a secret that exists."""
        with patch.dict(os.environ, {'REQUIRED_SECRET': 'required_value'}):
            manager = SecretManager()
            value = manager.require('REQUIRED_SECRET', mask=False)
            assert value == 'required_value'

    def test_require_secret_missing(self):
        """Test requiring a missing secret raises error."""
        manager = SecretManager()
        with pytest.raises(SecretNotConfiguredError):
            manager.require('MISSING_SECRET')

    def test_mask_value(self):
        """Test masking secret values."""
        manager = SecretManager()
        # Very short strings get fully masked
        short = manager.mask_value("ab")
        assert "**" == short or "***" == short

        # Medium strings show first and last chars
        medium = manager.mask_value("abcdefghij")
        assert "..." in medium
        assert medium.startswith("a")
        assert medium.endswith("j")

        # Long strings are truncated
        long = manager.mask_value("a" * 50)
        assert "..." in long
        assert len(long) < 50

    def test_mask_value_custom_chars(self):
        """Test masking with custom visible characters."""
        manager = SecretManager()
        masked = manager.mask_value("my_api_key_12345", visible_chars=2)
        assert "..." in masked
        assert masked.startswith("my")
        assert masked.endswith("45")

    def test_is_masked(self):
        """Test checking if value is masked."""
        manager = SecretManager()
        manager.get('SECRET_VALUE', default='secret123')

        assert manager.is_masked('secret123')
        assert not manager.is_masked('not_secret')


class TestSecretValidation:
    """Test secret validation functionality."""

    def test_validate_secret_success(self):
        """Test validating a valid secret."""
        manager = SecretManager()

        definition = SecretDefinition(
            name="VALID_SECRET",
            category=SecretCategory.API_KEY,
            description="Valid API key",
            required_in_production=True,
            min_length=20,
            requires_uppercase=False,
            requires_lowercase=False,
            requires_digit=False,
        )

        with patch.dict(os.environ, {'VALID_SECRET': 'a' * 30}):
            assert manager.validate_secret(definition) is True

    def test_validate_secret_too_short(self):
        """Test validating a secret that's too short."""
        manager = SecretManager()

        definition = SecretDefinition(
            name="SHORT_SECRET",
            category=SecretCategory.API_KEY,
            description="Short API key",
            required_in_production=True,
            min_length=32,
        )

        with patch.dict(os.environ, {'SHORT_SECRET': 'short'}):
            with pytest.raises(SecretValidationError):
                manager.validate_secret(definition)

    def test_validate_secret_weak_pattern(self):
        """Test validating a secret with weak pattern."""
        manager = SecretManager()

        definition = SecretDefinition(
            name="WEAK_SECRET",
            category=SecretCategory.DATABASE,
            description="Weak password",
            required_in_production=True,
            min_length=8,
            requires_uppercase=False,
            requires_lowercase=False,
            requires_digit=False,
        )

        # Weak pattern should return False (warning)
        with patch.dict(os.environ, {'WEAK_SECRET': 'password'}):
            result = manager.validate_secret(definition)
            assert result is False

    def test_validate_all_secrets(self):
        """Test validating all secrets."""
        manager = SecretManager()

        # Mock required secrets
        with patch.dict(
            os.environ,
            {
                'SECRET_KEY': 'a' * 40,
                'DB_PASSWORD': 'secure_password_123',
                'ALPACA_API_KEY': 'alpaca_key_' + 'a' * 20,
            },
        ):
            report = manager.validate_all()

            assert isinstance(report, SecretValidationReport)
            assert hasattr(report, 'is_valid')
            assert hasattr(report, 'compliance_score')
            assert hasattr(report, 'missing_secrets')
            assert hasattr(report, 'weak_secrets')


class TestConnectionStrings:
    """Test connection string building."""

    def test_postgresql_connection_string(self):
        """Test building PostgreSQL connection string."""
        with patch.dict(
            os.environ,
            {
                'DB_HOST': 'localhost',
                'DB_PORT': '5432',
                'DB_USER': 'trader',
                'DB_PASSWORD': 'secure_pass',
                'DB_NAME': 'trading_db',
            },
        ):
            manager = SecretManager()
            conn_str = manager.get_connection_string('postgresql')

            assert 'postgresql://' in conn_str
            assert 'trader:secure_pass@' in conn_str
            assert 'localhost:5432' in conn_str
            assert 'trading_db' in conn_str

    def test_redis_connection_string_with_password(self):
        """Test building Redis connection string with password."""
        with patch.dict(
            os.environ,
            {
                'REDIS_HOST': 'localhost',
                'REDIS_PORT': '6379',
                'REDIS_DB': '0',
                'REDIS_PASSWORD': 'redis_pass',
            },
        ):
            manager = SecretManager()
            conn_str = manager.get_connection_string('redis')

            assert conn_str == 'redis://:redis_pass@localhost:6379/0'

    def test_redis_connection_string_without_password(self):
        """Test building Redis connection string without password."""
        with patch.dict(
            os.environ,
            {
                'REDIS_HOST': 'localhost',
                'REDIS_PORT': '6379',
                'REDIS_DB': '0',
                'REDIS_PASSWORD': '',  # Empty password
            },
        ):
            manager = SecretManager()
            conn_str = manager.get_connection_string('redis')

            assert conn_str == 'redis://localhost:6379/0'

    def test_questdb_connection_string(self):
        """Test building QuestDB connection string."""
        with patch.dict(
            os.environ,
            {
                'QUESTDB_HOST': 'localhost',
                'QUESTDB_PORT': '9009',
                'QUESTDB_USER': 'admin',
                'QUESTDB_PASSWORD': 'quest_pass',
                'QUESTDB_DATABASE': 'qdb',
            },
        ):
            manager = SecretManager()
            conn_str = manager.get_connection_string('questdb')

            assert 'postgresql://admin:quest_pass@localhost:9009/qdb' == conn_str

    def test_postgresql_missing_password_raises_error(self):
        """Test that missing DB password raises error."""
        with patch.dict(
            os.environ,
            {
                'DB_HOST': 'localhost',
                'DB_PORT': '5432',
                'DB_USER': 'trader',
                'DB_NAME': 'trading_db',
            },
            clear=True,
        ):
            manager = SecretManager()
            with pytest.raises(SecretNotConfiguredError):
                manager.get_connection_string('postgresql')

    def test_unknown_database_type_raises_error(self):
        """Test that unknown database type raises error."""
        manager = SecretManager()
        with pytest.raises(ValueError, match="Unknown database type"):
            manager.get_connection_string('mongodb')


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_secret_function(self):
        """Test get_secret convenience function."""
        with patch.dict(os.environ, {'API_KEY': 'test_key'}):
            value = get_secret('API_KEY', mask=False)
            assert value == 'test_key'

    def test_require_secret_function(self):
        """Test require_secret convenience function."""
        with patch.dict(os.environ, {'DB_PASSWORD': 'test_pass'}):
            value = require_secret('DB_PASSWORD', mask=False)
            assert value == 'test_pass'

    def test_get_connection_string_function(self):
        """Test get_connection_string convenience function."""
        # Clear cache to ensure fresh values
        import app.core.secret_manager as sm_module

        sm_module._secret_manager.clear_cache()

        with patch.dict(
            os.environ,
            {
                'DB_HOST': 'localhost',
                'DB_PORT': '5432',
                'DB_USER': 'user',
                'DB_PASSWORD': 'pass',
                'DB_NAME': 'db',
            },
        ):
            conn_str = get_connection_string('postgresql')
            # Check that connection string is built correctly
            assert 'postgresql://user:pass@localhost:5432/db' == conn_str

    def test_mask_secret_function(self):
        """Test mask_secret convenience function."""
        masked = mask_secret('my_secret_key_12345')
        assert '...' in masked
        assert masked.startswith('my')
        assert masked.endswith('45')

    def test_is_production_function(self):
        """Test is_production function."""
        # Need to patch at the module level since is_production uses the global instance
        import app.core.secret_manager as sm_module

        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            # Create new instance to pick up the environment
            sm_module._secret_manager = sm_module.SecretManager()
            assert is_production() is True

        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            sm_module._secret_manager = sm_module.SecretManager()
            assert is_production() is False

    def test_validate_secrets_configured_function(self):
        """Test validate_secrets_configured convenience function."""
        with patch.dict(
            os.environ,
            {
                'SECRET_KEY': 'a' * 40,
                'DB_PASSWORD': 'secure_password',
            },
        ):
            report = validate_secrets_configured()

            assert isinstance(report, SecretValidationReport)
            assert hasattr(report, 'is_valid')
            assert hasattr(report, 'compliance_score')


class TestRule28Compliance:
    """Test Rule 28 compliance requirements."""

    def test_no_hardcoded_secrets_in_manager(self):
        """Verify no hardcoded secrets in SecretManager."""
        # Read the source code
        import inspect

        source = inspect.getsource(SecretManager)

        # Check for common hardcoded secret patterns
        hardcoded_patterns = [
            'password = "',
            'secret = "',
            'api_key = "',
            "password = '",
            "secret = '",
            "api_key = '",
            '="password"',
            '="secret"',
            '="changeme"',
            "='password'",
            "='secret'",
            "='changeme'",
        ]

        found = []
        for pattern in hardcoded_patterns:
            if pattern in source:
                found.append(pattern)

        assert not found, f"Found potential hardcoded secrets: {found}"

    def test_environment_variable_usage(self):
        """Verify secrets come from environment variables."""
        # This is tested implicitly by other tests
        # but let's explicitly check the implementation
        manager = SecretManager()

        # Should use os.getenv
        with patch('os.getenv', return_value='test_value') as mock_getenv:
            value = manager.get('TEST_KEY', default='default', mask=False)
            assert mock_getenv.called or value == 'test_value'

    def test_secret_masking_in_logs(self):
        """Verify secrets are masked for logging."""
        manager = SecretManager()

        # Get a secret (should be marked for masking)
        manager.get('API_KEY', default='secret_api_key_12345')

        # Check it's masked
        assert manager.is_masked('secret_api_key_12345')

        # Masked version should be different
        masked = manager.mask_value('secret_api_key_12345')
        assert masked != 'secret_api_key_12345'
        assert '...' in masked

    def test_connection_string_no_hardcoded_creds(self):
        """Verify connection strings don't contain hardcoded credentials."""
        # Read the source code
        import inspect

        source = inspect.getsource(SecretManager.get_connection_string)

        # Should not contain hardcoded credentials
        assert '://' not in source or 'user:password@' not in source

    def test_validation_report_compliance_score(self):
        """Test compliance score calculation."""
        manager = SecretManager()

        # Mock all secrets as valid
        with patch.dict(
            os.environ,
            {
                'SECRET_KEY': 'a' * 40,
                'ALPACA_API_KEY': 'key_' + 'a' * 30,
                'ALPACA_SECRET_KEY': 'secret_' + 'a' * 30,
                'POLYGON_API_KEY': 'polygon_' + 'a' * 30,
                'ALPHA_VANTAGE_API_KEY': 'av_' + 'a' * 30,
                'DB_PASSWORD': 'secure_password_123',
                'QUESTDB_PASSWORD': 'quest_pass',
                'REDIS_PASSWORD': 'redis_pass',
                'SMTP_PASSWORD': 'smtp_pass',
                'TELEGRAM_BOT_TOKEN': 'bot_' + 'a' * 30,
                'NEWS_API_KEY': 'news_' + 'a' * 30,
            },
        ):
            report = manager.validate_all()

            # Should have high compliance
            assert report.compliance_score >= 95.0

    def test_production_detection(self):
        """Test production environment detection."""
        # Production detection happens in __init__, so create new instances
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            manager = SecretManager()
            assert manager._is_production is True

        with patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
            manager = SecretManager()
            assert manager._is_production is True

        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = SecretManager()
            assert manager._is_production is False

        with patch.dict(os.environ, {}, clear=True):
            manager = SecretManager()
            assert manager._is_production is False
