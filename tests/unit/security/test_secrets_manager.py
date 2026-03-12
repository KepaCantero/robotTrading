"""
Unit tests for SecretsManagerImpl.

Tests the secrets management functionality including:
- EnvironmentStorage backend
- EncryptedFileStorage backend
- Secret storage and retrieval
- Secret rotation
- Secret deletion
- Storage backend switching
"""

import pytest
import os
import tempfile
from datetime import datetime
from cryptography.fernet import Fernet

from app.services.security.secrets_manager_impl import (
    SecretsManagerImpl,
    SecretValue,
    EnvironmentStorage,
    EncryptedFileStorage,
)


@pytest.fixture
def encryption_key():
    """Generate a test encryption key."""
    return Fernet.generate_key()


@pytest.fixture
def secrets_manager(encryption_key, monkeypatch):
    """Create a SecretsManagerImpl instance for testing."""
    monkeypatch.setenv("ALGOTRADING_ENCRYPTION_KEY", encryption_key.decode())
    return SecretsManagerImpl()


@pytest.fixture
def temp_file_path(encryption_key):
    """Create a temporary file path for encrypted storage testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        path = f.name
    yield path
    # Cleanup
    try:
        os.unlink(path)
    except OSError:
        pass


class TestEnvironmentStorage:
    """Tests for EnvironmentStorage class."""

    def test_store_and_retrieve(self):
        """Test storing and retrieving secrets."""
        storage = EnvironmentStorage()
        storage.store("test_key", "test_value")

        retrieved = storage.retrieve("test_key")
        assert retrieved == "test_value"

    def test_store_uppercases_key(self):
        """Test that stored keys are uppercased with prefix."""
        storage = EnvironmentStorage()
        storage.store("my_key", "my_value")

        # Check that the environment variable was set correctly
        assert os.environ.get("SECRET_MY_KEY") == "my_value"

    def test_retrieve_not_found(self):
        """Test retrieving non-existent secret."""
        storage = EnvironmentStorage()
        retrieved = storage.retrieve("non_existent")
        assert retrieved is None

    def test_delete(self):
        """Test deleting a secret."""
        storage = EnvironmentStorage()
        storage.store("test_key", "test_value")

        result = storage.delete("test_key")
        assert result is True

        # Verify it's gone
        retrieved = storage.retrieve("test_key")
        assert retrieved is None

    def test_delete_not_found(self):
        """Test deleting non-existent secret."""
        storage = EnvironmentStorage()
        result = storage.delete("non_existent")
        assert result is False

    def test_list_keys(self, monkeypatch):
        """Test listing all secret keys."""
        # Clear existing environment variables to avoid test pollution
        for key in list(os.environ.keys()):
            if key.startswith("SECRET_"):
                monkeypatch.delenv(key, raising=False)

        storage = EnvironmentStorage()
        storage.store("key1", "value1")
        storage.store("key2", "value2")
        storage.store("key3", "value3")

        keys = storage.list_keys()
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys


class TestEncryptedFileStorage:
    """Tests for EncryptedFileStorage class."""

    def test_store_and_retrieve(self, temp_file_path, encryption_key):
        """Test storing and retrieving secrets."""
        storage = EncryptedFileStorage(temp_file_path, encryption_key)

        storage.store("test_key", "test_value")
        retrieved = storage.retrieve("test_key")

        assert retrieved == "test_value"

    def test_store_creates_directory(self, encryption_key):
        """Test that storing creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "subsubdir", "secrets.json")
            storage = EncryptedFileStorage(path, encryption_key)

            storage.store("test_key", "test_value")

            assert os.path.exists(path)

    def test_retrieve_not_found(self, temp_file_path, encryption_key):
        """Test retrieving non-existent secret."""
        storage = EncryptedFileStorage(temp_file_path, encryption_key)
        retrieved = storage.retrieve("non_existent")
        assert retrieved is None

    def test_delete(self, temp_file_path, encryption_key):
        """Test deleting a secret."""
        storage = EncryptedFileStorage(temp_file_path, encryption_key)

        storage.store("test_key", "test_value")
        result = storage.delete("test_key")

        assert result is True
        assert storage.retrieve("test_key") is None

    def test_delete_not_found(self, temp_file_path, encryption_key):
        """Test deleting non-existent secret."""
        storage = EncryptedFileStorage(temp_file_path, encryption_key)
        result = storage.delete("non_existent")
        assert result is False

    def test_list_keys(self, temp_file_path, encryption_key):
        """Test listing all secret keys."""
        storage = EncryptedFileStorage(temp_file_path, encryption_key)

        storage.store("key1", "value1")
        storage.store("key2", "value2")
        storage.store("key3", "value3")

        keys = storage.list_keys()
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_persists_across_instances(self, temp_file_path, encryption_key):
        """Test that secrets persist across storage instances."""
        # Create first instance and store a secret
        storage1 = EncryptedFileStorage(temp_file_path, encryption_key)
        storage1.store("persistent_key", "persistent_value")

        # Create second instance and retrieve the secret
        storage2 = EncryptedFileStorage(temp_file_path, encryption_key)
        retrieved = storage2.retrieve("persistent_key")

        assert retrieved == "persistent_value"

    def test_encryption(self, temp_file_path, encryption_key):
        """Test that data is actually encrypted in the file."""
        storage = EncryptedFileStorage(temp_file_path, encryption_key)
        storage.store("test_key", "test_value")

        # Read the raw file content
        with open(temp_file_path, 'rb') as f:
            content = f.read()

        # Content should be encrypted (not plain JSON)
        assert b"test_value" not in content
        assert b"test_key" not in content


class TestSecretsManagerImpl:
    """Tests for SecretsManagerImpl class."""

    def test_init_without_encryption_key(self, monkeypatch):
        """Test initialization without encryption key."""
        monkeypatch.delenv("ALGOTRADING_ENCRYPTION_KEY", raising=False)

        manager = SecretsManagerImpl()
        # Should work with EnvironmentStorage default
        assert manager is not None

    def test_set_and_get_secret(self, secrets_manager):
        """Test setting and getting a secret."""
        secrets_manager.set_secret("test_key", "test_value")

        retrieved = secrets_manager.get_secret("test_key")
        assert retrieved == "test_value"

    def test_get_secret_not_found(self, secrets_manager):
        """Test getting non-existent secret."""
        retrieved = secrets_manager.get_secret("non_existent")
        assert retrieved is None

    def test_secret_versioning(self, secrets_manager):
        """Test that updating a secret increments version."""
        secrets_manager.set_secret("versioned_key", "value1")

        metadata1 = secrets_manager.get_secret_metadata("versioned_key")
        assert metadata1.version == 1

        secrets_manager.set_secret("versioned_key", "value2")

        metadata2 = secrets_manager.get_secret_metadata("versioned_key")
        assert metadata2.version == 2

        # Should get the updated value
        retrieved = secrets_manager.get_secret("versioned_key")
        assert retrieved == "value2"

    def test_delete_secret(self, secrets_manager):
        """Test deleting a secret."""
        secrets_manager.set_secret("test_key", "test_value")

        result = secrets_manager.delete_secret("test_key")
        assert result is True

        retrieved = secrets_manager.get_secret("test_key")
        assert retrieved is None

    def test_delete_secret_not_found(self, secrets_manager):
        """Test deleting non-existent secret."""
        result = secrets_manager.delete_secret("non_existent")
        assert result is False

    def test_rotate_secret(self, secrets_manager):
        """Test rotating a secret."""
        secrets_manager.set_secret("rotatable_key", "old_value")

        result = secrets_manager.rotate_secret("rotatable_key", "new_value")
        assert result is True

        retrieved = secrets_manager.get_secret("rotatable_key")
        assert retrieved == "new_value"

    def test_rotate_secret_not_found(self, secrets_manager):
        """Test rotating non-existent secret."""
        result = secrets_manager.rotate_secret("non_existent", "new_value")
        assert result is False

    def test_list_secrets(self, secrets_manager, monkeypatch):
        """Test listing all secrets."""
        # Clear existing environment variables to avoid test pollution
        for key in list(os.environ.keys()):
            if key.startswith("SECRET_"):
                monkeypatch.delenv(key, raising=False)

        secrets_manager.set_secret("key1", "value1")
        secrets_manager.set_secret("key2", "value2")
        secrets_manager.set_secret("key3", "value3")

        keys = secrets_manager.list_secrets()
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_get_secret_metadata(self, secrets_manager):
        """Test getting secret metadata."""
        secrets_manager.set_secret("metadata_key", "metadata_value")

        metadata = secrets_manager.get_secret_metadata("metadata_key")

        assert metadata is not None
        assert metadata.key == "metadata_key"
        assert metadata.version == 1
        assert metadata.created_at is not None
        assert metadata.updated_at is not None

    def test_get_secret_metadata_not_found(self, secrets_manager):
        """Test getting metadata for non-existent secret."""
        metadata = secrets_manager.get_secret_metadata("non_existent")
        assert metadata is None

    def test_set_storage_backend(self, secrets_manager, temp_file_path, encryption_key):
        """Test switching storage backends."""
        new_backend = EnvironmentStorage()
        secrets_manager.set_storage_backend(new_backend)

        # Should use the new backend now
        secrets_manager.set_secret("test_key", "test_value")

        # The secret should be in the environment (encrypted)
        stored_value = os.environ.get("SECRET_TEST_KEY")
        assert stored_value is not None
        # Value should be encrypted (not plain text)
        assert stored_value != "test_value"
        # But we should be able to retrieve it through the manager
        retrieved = secrets_manager.get_secret("test_key")
        assert retrieved == "test_value"


class TestSecretValue:
    """Tests for SecretValue dataclass."""

    def test_secret_value_fields(self):
        """Test SecretValue has all required fields."""
        now = datetime.utcnow()
        value = SecretValue(
            key="test_key",
            value="encrypted_value",
            version=1,
            created_at=now,
            updated_at=now
        )

        assert value.key == "test_key"
        assert value.value == "encrypted_value"
        assert value.version == 1
        assert value.created_at == now
        assert value.updated_at == now
