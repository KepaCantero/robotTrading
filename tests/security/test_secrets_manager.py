"""
Tests for app/security/secrets_manager.py
"""

import os
from datetime import datetime, timedelta

import pytest

from app.security.secrets_manager import (
    Secret,
    SecretsManager,
    SecretValidationError,
    get_secret,
    get_secrets_manager,
    rotate_secret,
    set_secret,
)


class TestSecret:
    """Test Secret model."""

    def test_secret_creation(self):
        """Test creating a secret."""
        secret = Secret(
            name="test_secret",
            value="encrypted_value",
        )
        assert secret.name == "test_secret"
        assert secret.value == "encrypted_value"
        assert secret.version == 1

    def test_secret_expiration(self):
        """Test secret expiration."""
        secret = Secret(
            name="test_secret",
            value="encrypted_value",
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
        assert secret.is_expired() is False

    def test_secret_expired(self):
        """Test expired secret."""
        secret = Secret(
            name="test_secret",
            value="encrypted_value",
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        assert secret.is_expired() is True

    def test_secret_needs_rotation(self):
        """Test secret rotation needed."""
        secret = Secret(
            name="test_secret",
            value="encrypted_value",
            rotated_at=datetime.utcnow() - timedelta(days=100),
        )
        assert secret.needs_rotation(rotation_period_days=90) is True

    def test_to_dict(self):
        """Test secret to dictionary conversion."""
        secret = Secret(
            name="test_secret",
            value="encrypted_value",
            version=2,
        )
        data = secret.to_dict(include_value=True)
        assert data["name"] == "test_secret"
        assert data["value"] == "encrypted_value"
        assert data["version"] == 2

        data_no_value = secret.to_dict(include_value=False)
        assert "value" not in data_no_value


class TestSecretsManager:
    """Test secrets management."""

    def test_initialization(self):
        """Test secrets manager initialization."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        assert manager is not None
        assert manager.auto_rotate is True

    def test_validate_environment_missing(self):
        """Test environment validation with missing secrets."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")

        # Clear environment
        os.environ.pop("SECRET_KEY", None)
        os.environ.pop("DATABASE_URL", None)

        with pytest.raises(SecretValidationError):
            manager.validate_environment()

    def test_set_secret(self):
        """Test setting a secret."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        secret = manager.set_secret(
            name="test_secret",
            value="test_value_12345",
        )
        assert secret.name == "test_secret"
        assert secret.version == 1

    def test_set_secret_with_expiration(self):
        """Test setting secret with expiration."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        secret = manager.set_secret(
            name="test_secret",
            value="test_value_12345",
            expires_in_days=30,
        )
        assert secret.expires_at is not None
        assert secret.expires_at > datetime.utcnow()

    def test_get_secret(self):
        """Test getting a secret."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        manager.set_secret(name="test_secret", value="test_value_12345")

        value = manager.get_secret("test_secret")
        assert value == "test_value_12345"

    def test_get_secret_default(self):
        """Test getting secret with default value."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        value = manager.get_secret("nonexistent", default="default_value")
        assert value == "default_value"

    def test_get_secret_not_found(self):
        """Test getting non-existent secret."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")

        with pytest.raises(SecretValidationError):
            manager.get_secret("nonexistent")

    def test_rotate_secret(self):
        """Test secret rotation."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        manager.set_secret(name="test_secret", value="old_value_12345")

        new_secret = manager.rotate_secret("test_secret")
        assert new_secret.version == 2
        assert new_secret.value != "old_value_12345"

    def test_delete_secret(self):
        """Test deleting a secret."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        manager.set_secret(name="test_secret", value="test_value_12345")

        result = manager.delete_secret("test_secret")
        assert result is True

        # Secret should no longer exist
        with pytest.raises(SecretValidationError):
            manager.get_secret("test_secret")

    def test_delete_nonexistent_secret(self):
        """Test deleting non-existent secret."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        result = manager.delete_secret("nonexistent")
        assert result is False

    def test_list_secrets(self):
        """Test listing secrets."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        manager.set_secret(name="secret1", value="value1_12345")
        manager.set_secret(name="secret2", value="value2_12345")

        secrets = manager.list_secrets()
        assert len(secrets) == 2
        assert all("value" not in s for s in secrets)  # Values not included

    def test_export_secrets(self):
        """Test exporting secrets."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        manager.set_secret(name="test_secret", value="test_value_12345")

        export = manager.export_secrets(include_values=False)
        assert "secrets" in export
        assert len(export["secrets"]) == 1

    def test_import_secrets(self):
        """Test importing secrets."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")

        data = {
            "secrets": [
                {
                    "name": "imported_secret",
                    "value": "imported_value_12345",
                    "version": 1,
                }
            ]
        }

        count = manager.import_secrets(data)
        assert count == 1

    def test_get_audit_log(self):
        """Test getting audit log."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        manager.set_secret(name="test_secret", value="test_value_12345")

        log = manager.get_audit_log(limit=10)
        assert len(log) > 0
        assert log[0]["action"] == "secret_created"

    def test_clear_audit_log(self):
        """Test clearing audit log."""
        manager = SecretsManager(encryption_key="test_encryption_key_32_bytes_long!!")
        manager.set_secret(name="test_secret", value="test_value_12345")
        manager.clear_audit_log(older_than_days=0)

        log = manager.get_audit_log()
        assert len(log) == 0


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_secrets_manager(self):
        """Test getting global secrets manager."""
        manager = get_secrets_manager()
        assert manager is not None
        assert isinstance(manager, SecretsManager)

    def test_set_secret_global(self):
        """Test global set_secret function."""
        secret = set_secret("test_global_secret", "test_value_12345")
        assert secret.name == "test_global_secret"

    def test_get_secret_global(self):
        """Test global get_secret function."""
        set_secret("test_get_secret", "test_value_12345")
        value = get_secret("test_get_secret")
        assert value == "test_value_12345"

    def test_rotate_secret_global(self):
        """Test global rotate_secret function."""
        set_secret("test_rotate_secret", "old_value_12345")
        new_secret = rotate_secret("test_rotate_secret")
        assert new_secret.version >= 1
