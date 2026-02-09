"""
Unit tests for ApiKeyManager.

Tests the API key management functionality including:
- Key creation with various permissions
- Key retrieval by ID and name
- Key validation
- Key revocation
- Expiration checking
- Last used updates
"""

import pytest
import os
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

from app.services.security.api_key_manager import (
    ApiKeyManager,
    ApiKey,
    KeyPermission,
    KeyValidationError,
)


@pytest.fixture
def encryption_key():
    """Generate a test encryption key."""
    return Fernet.generate_key()


@pytest.fixture
def api_key_manager(encryption_key):
    """Create an ApiKeyManager instance for testing."""
    return ApiKeyManager(encryption_key=encryption_key)


@pytest.fixture
def sample_api_key():
    """Sample API key for testing."""
    return "test_api_key_1234567890abcdef"


class TestApiKeyManager:
    """Tests for ApiKeyManager class."""

    def test_init_with_explicit_key(self, encryption_key):
        """Test initialization with explicit encryption key."""
        manager = ApiKeyManager(encryption_key=encryption_key)
        assert manager is not None
        assert manager._keys == {}

    def test_init_with_env_variable(self, encryption_key, monkeypatch):
        """Test initialization with environment variable."""
        monkeypatch.setenv("ALGOTRADING_ENCRYPTION_KEY", encryption_key.decode())
        manager = ApiKeyManager()
        assert manager is not None

    def test_init_without_key_raises_error(self, monkeypatch):
        """Test initialization without encryption key raises error."""
        monkeypatch.delenv("ALGOTRADING_ENCRYPTION_KEY", raising=False)
        with pytest.raises(ValueError, match="Encryption key must be provided"):
            ApiKeyManager()

    def test_add_key_success(self, api_key_manager, sample_api_key):
        """Test successful key addition."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        assert key_id is not None
        assert len(api_key_manager._keys) == 1

        key = api_key_manager.get_key(key_id)
        assert key is not None
        assert key.key_name == "test_key"
        assert key.permission == KeyPermission.READ_ONLY
        assert key.is_active is True

    def test_add_key_with_expiration(self, api_key_manager, sample_api_key):
        """Test adding key with expiration."""
        key_id = api_key_manager.add_key(
            key_name="expiring_key",
            api_key=sample_api_key,
            permission=KeyPermission.TRADING,
            expires_in_days=30
        )

        key = api_key_manager.get_key(key_id)
        assert key.expires_at is not None
        assert key.expires_at > datetime.utcnow()

    def test_add_key_invalid_format_too_short(self, api_key_manager):
        """Test adding key with invalid format (too short)."""
        with pytest.raises(KeyValidationError, match="Invalid API key format"):
            api_key_manager.add_key(
                key_name="short_key",
                api_key="short",
                permission=KeyPermission.READ_ONLY
            )

    def test_add_key_invalid_format_whitespace(self, api_key_manager):
        """Test adding key with invalid format (contains whitespace)."""
        with pytest.raises(KeyValidationError, match="Invalid API key format"):
            api_key_manager.add_key(
                key_name="whitespace_key",
                api_key="test key with spaces",
                permission=KeyPermission.READ_ONLY
            )

    def test_add_key_empty_value(self, api_key_manager):
        """Test adding key with empty value."""
        with pytest.raises(KeyValidationError, match="Invalid API key format"):
            api_key_manager.add_key(
                key_name="empty_key",
                api_key="",
                permission=KeyPermission.READ_ONLY
            )

    def test_get_key_by_id(self, api_key_manager, sample_api_key):
        """Test retrieving key by ID."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.ADMIN
        )

        retrieved_key = api_key_manager.get_key(key_id)
        assert retrieved_key is not None
        assert retrieved_key.key_id == key_id
        assert retrieved_key.key_name == "test_key"

    def test_get_key_by_id_not_found(self, api_key_manager):
        """Test retrieving non-existent key by ID."""
        retrieved_key = api_key_manager.get_key("non_existent_id")
        assert retrieved_key is None

    def test_get_key_by_name(self, api_key_manager, sample_api_key):
        """Test retrieving key by name."""
        api_key_manager.add_key(
            key_name="unique_name",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        retrieved_key = api_key_manager.get_key_by_name("unique_name")
        assert retrieved_key is not None
        assert retrieved_key.key_name == "unique_name"

    def test_get_key_by_name_not_found(self, api_key_manager):
        """Test retrieving non-existent key by name."""
        retrieved_key = api_key_manager.get_key_by_name("non_existent_name")
        assert retrieved_key is None

    def test_validate_key_success(self, api_key_manager, sample_api_key):
        """Test successful key validation."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        is_valid = api_key_manager.validate_key(key_id, sample_api_key)
        assert is_valid is True

        # Check that last_used was updated
        key = api_key_manager.get_key(key_id)
        assert key.last_used is not None

    def test_validate_key_wrong_value(self, api_key_manager, sample_api_key):
        """Test key validation with wrong value."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        is_valid = api_key_manager.validate_key(key_id, "wrong_key")
        assert is_valid is False

    def test_validate_key_not_found(self, api_key_manager, sample_api_key):
        """Test key validation with non-existent key ID."""
        is_valid = api_key_manager.validate_key("non_existent_id", sample_api_key)
        assert is_valid is False

    def test_validate_key_inactive(self, api_key_manager, sample_api_key):
        """Test key validation with inactive key."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        # Revoke the key
        api_key_manager.revoke_key(key_id)

        is_valid = api_key_manager.validate_key(key_id, sample_api_key)
        assert is_valid is False

    def test_validate_key_expired(self, api_key_manager, sample_api_key):
        """Test key validation with expired key."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY,
            expires_in_days=-1  # Already expired
        )

        is_valid = api_key_manager.validate_key(key_id, sample_api_key)
        assert is_valid is False

    def test_revoke_key_success(self, api_key_manager, sample_api_key):
        """Test successful key revocation."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        result = api_key_manager.revoke_key(key_id)
        assert result is True

        key = api_key_manager.get_key(key_id)
        assert key.is_active is False

    def test_revoke_key_not_found(self, api_key_manager):
        """Test revoking non-existent key."""
        result = api_key_manager.revoke_key("non_existent_id")
        assert result is False

    def test_list_keys(self, api_key_manager, sample_api_key):
        """Test listing all keys."""
        api_key_manager.add_key("key1", sample_api_key, KeyPermission.READ_ONLY)
        api_key_manager.add_key("key2", sample_api_key, KeyPermission.TRADING)
        api_key_manager.add_key("key3", sample_api_key, KeyPermission.ADMIN)

        keys = api_key_manager.list_keys()
        assert len(keys) == 3

        key_names = [key.key_name for key in keys]
        assert "key1" in key_names
        assert "key2" in key_names
        assert "key3" in key_names

    def test_list_keys_empty(self, api_key_manager):
        """Test listing keys when none exist."""
        keys = api_key_manager.list_keys()
        assert len(keys) == 0

    def test_update_last_used(self, api_key_manager, sample_api_key):
        """Test updating last_used timestamp."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        # Initially last_used should be None
        key = api_key_manager.get_key(key_id)
        assert key.last_used is None

        # Update last used
        api_key_manager.update_last_used(key_id)

        key = api_key_manager.get_key(key_id)
        assert key.last_used is not None
        assert key.last_used > datetime.utcnow() - timedelta(seconds=1)

    def test_check_expiration_no_expired_keys(self, api_key_manager, sample_api_key):
        """Test checking for expired keys when none are expired."""
        api_key_manager.add_key(
            "test_key",
            sample_api_key,
            KeyPermission.READ_ONLY,
            expires_in_days=30
        )

        expired_ids = api_key_manager.check_expiration()
        assert len(expired_ids) == 0

    def test_check_expiration_with_expired_keys(self, api_key_manager, sample_api_key):
        """Test checking for expired keys."""
        key_id = api_key_manager.add_key(
            "test_key",
            sample_api_key,
            KeyPermission.READ_ONLY,
            expires_in_days=-1  # Expired
        )

        expired_ids = api_key_manager.check_expiration()
        assert key_id in expired_ids

    def test_get_decrypted_key(self, api_key_manager, sample_api_key):
        """Test getting decrypted key value."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key=sample_api_key,
            permission=KeyPermission.READ_ONLY
        )

        decrypted_key = api_key_manager.get_decrypted_key(key_id)
        assert decrypted_key == sample_api_key

    def test_get_decrypted_key_not_found(self, api_key_manager):
        """Test getting decrypted key for non-existent key."""
        decrypted_key = api_key_manager.get_decrypted_key("non_existent_id")
        assert decrypted_key is None


class TestApiKey:
    """Tests for ApiKey dataclass."""

    def test_is_expired_no_expiration(self):
        """Test is_expired when key has no expiration."""
        key = ApiKey(
            key_id="test_id",
            key_name="test_key",
            encrypted_key="encrypted",
            permission=KeyPermission.READ_ONLY,
            created_at=datetime.utcnow(),
            expires_at=None
        )

        assert key.is_expired() is False

    def test_is_expired_not_yet(self):
        """Test is_expired when key hasn't expired yet."""
        key = ApiKey(
            key_id="test_id",
            key_name="test_key",
            encrypted_key="encrypted",
            permission=KeyPermission.READ_ONLY,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )

        assert key.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired when key has expired."""
        key = ApiKey(
            key_id="test_id",
            key_name="test_key",
            encrypted_key="encrypted",
            permission=KeyPermission.READ_ONLY,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() - timedelta(days=1)
        )

        assert key.is_expired() is True


class TestKeyPermission:
    """Tests for KeyPermission enum."""

    def test_permission_values(self):
        """Test KeyPermission enum values."""
        assert KeyPermission.READ_ONLY.value == "read_only"
        assert KeyPermission.TRADING.value == "trading"
        assert KeyPermission.ADMIN.value == "admin"

    def test_permission_comparison(self):
        """Test KeyPermission enum comparison."""
        assert KeyPermission.READ_ONLY == KeyPermission.READ_ONLY
        assert KeyPermission.READ_ONLY != KeyPermission.TRADING
