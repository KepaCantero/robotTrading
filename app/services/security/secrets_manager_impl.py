"""
Secrets Manager implementation for secure credential storage.

This module provides secure storage and retrieval of secrets with:
- Environment variable integration
- Encrypted file-based storage
- Secure credential retrieval
- Credential versioning
- Automatic credential rotation support

R29: Security Hardening
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Protocol
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


@dataclass
class SecretValue:
    """Data model for secret values."""
    key: str
    value: str  # encrypted
    version: int
    created_at: datetime
    updated_at: datetime


class SecretStorage(Protocol):
    """
    Protocol for secret storage backends.

    A secret storage backend must implement these methods to be
    compatible with SecretsManagerImpl.
    """

    def store(self, key: str, value: str) -> None:
        """Store a secret value."""
        ...

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve a secret value."""
        ...

    def delete(self, key: str) -> bool:
        """Delete a secret value."""
        ...

    def list_keys(self) -> List[str]:
        """List all stored secret keys."""
        ...


class EnvironmentStorage:
    """
    Environment variable storage backend for secrets.

    This storage backend reads and writes secrets from environment
    variables. Note that writing to environment variables only
    affects the current process.
    """

    def store(self, key: str, value: str) -> None:
        """
        Store a secret in an environment variable.

        Args:
            key: The secret key (will be uppercased with prefix)
            value: The secret value
        """
        env_key = f"SECRET_{key.upper()}"
        os.environ[env_key] = value
        logger.debug(f"Stored secret in environment variable: {env_key}")

    def retrieve(self, key: str) -> Optional[str]:
        """
        Retrieve a secret from environment variables.

        Args:
            key: The secret key

        Returns:
            The secret value or None if not found
        """
        env_key = f"SECRET_{key.upper()}"
        return os.environ.get(env_key)

    def delete(self, key: str) -> bool:
        """
        Delete a secret from environment variables.

        Args:
            key: The secret key

        Returns:
            True if deleted, False if not found
        """
        env_key = f"SECRET_{key.upper()}"
        if env_key in os.environ:
            del os.environ[env_key]
            logger.debug(f"Deleted secret from environment variable: {env_key}")
            return True
        return False

    def list_keys(self) -> List[str]:
        """
        List all secret keys in environment variables.

        Returns:
            List of secret keys
        """
        prefix = "SECRET_"
        return [
            key[len(prefix):].lower()
            for key in os.environ
            if key.startswith(prefix)
        ]


class EncryptedFileStorage:
    """
    Encrypted file-based storage backend for secrets.

    This storage backend stores secrets in an encrypted JSON file.
    The file is encrypted using Fernet symmetric encryption.
    """

    def __init__(self, file_path: str, encryption_key: Optional[bytes] = None):
        """
        Initialize encrypted file storage.

        Args:
            file_path: Path to the encrypted storage file
            encryption_key: Fernet encryption key. If None, reads from
                          ALGOTRADING_ENCRYPTION_KEY environment variable.
        """
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        if encryption_key is None:
            key = os.environ.get("ALGOTRADING_ENCRYPTION_KEY")
            if not key:
                raise ValueError(
                    "Encryption key must be provided or set in "
                    "ALGOTRADING_ENCRYPTION_KEY environment variable"
                )
            encryption_key = key.encode()

        self._fernet = Fernet(encryption_key)
        self._data: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load encrypted data from file."""
        if not self._file_path.exists():
            self._data = {}
            return

        try:
            encrypted_content = self._file_path.read_bytes()
            if not encrypted_content:
                self._data = {}
                return

            decrypted_content = self._fernet.decrypt(encrypted_content)
            self._data = json.loads(decrypted_content.decode())
        except InvalidToken:
            logger.error(f"Failed to decrypt secrets file: {self._file_path}")
            self._data = {}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse secrets file: {e}")
            self._data = {}

    def _save(self) -> None:
        """Save encrypted data to file."""
        content = json.dumps(self._data).encode()
        encrypted_content = self._fernet.encrypt(content)
        self._file_path.write_bytes(encrypted_content)

    def store(self, key: str, value: str) -> None:
        """
        Store a secret in the encrypted file.

        Args:
            key: The secret key
            value: The secret value
        """
        self._data[key] = value
        self._save()
        logger.debug(f"Stored secret in encrypted file: {key}")

    def retrieve(self, key: str) -> Optional[str]:
        """
        Retrieve a secret from the encrypted file.

        Args:
            key: The secret key

        Returns:
            The secret value or None if not found
        """
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        """
        Delete a secret from the encrypted file.

        Args:
            key: The secret key

        Returns:
            True if deleted, False if not found
        """
        if key in self._data:
            del self._data[key]
            self._save()
            logger.debug(f"Deleted secret from encrypted file: {key}")
            return True
        return False

    def list_keys(self) -> List[str]:
        """
        List all secret keys in the encrypted file.

        Returns:
            List of secret keys
        """
        return list(self._data.keys())


class SecretsError(Exception):
    """Exception for secrets errors."""
    pass


class SecretsManagerImpl:
    """
    Secrets manager for secure credential storage and retrieval.

    This class provides a unified interface for managing secrets
    with support for multiple storage backends.
    """

    def __init__(self, storage_backend: Optional[SecretStorage] = None):
        """
        Initialize the secrets manager.

        Args:
            storage_backend: Storage backend to use. If None, uses
                           EnvironmentStorage by default.
        """
        if storage_backend is None:
            storage_backend = EnvironmentStorage()

        self._storage = storage_backend
        self._secrets: Dict[str, SecretValue] = {}
        self._fernet: Optional[Fernet] = None

        # Initialize encryption for in-memory values
        encryption_key = os.environ.get("ALGOTRADING_ENCRYPTION_KEY")
        if encryption_key:
            self._fernet = Fernet(encryption_key.encode())

    def set_storage_backend(self, backend: SecretStorage) -> None:
        """
        Set a new storage backend.

        Args:
            backend: The new storage backend
        """
        self._storage = backend
        logger.info("Storage backend changed")

    def _encrypt(self, value: str) -> str:
        """Encrypt a secret value."""
        if self._fernet is None:
            raise SecretsError(
                "Encryption not available. Set ALGOTRADING_ENCRYPTION_KEY "
                "environment variable."
            )
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, encrypted_value: str) -> str:
        """Decrypt a secret value."""
        if self._fernet is None:
            raise SecretsError(
                "Encryption not available. Set ALGOTRADING_ENCRYPTION_KEY "
                "environment variable."
            )
        return self._fernet.decrypt(encrypted_value.encode()).decode()

    def set_secret(self, key: str, value: str) -> None:
        """
        Store a secret.

        Args:
            key: The secret key
            value: The secret value (will be encrypted)
        """
        encrypted_value = self._encrypt(value)

        now = datetime.utcnow()

        # Check if updating existing secret
        if key in self._secrets:
            old_version = self._secrets[key].version
            self._secrets[key] = SecretValue(
                key=key,
                value=encrypted_value,
                version=old_version + 1,
                created_at=self._secrets[key].created_at,
                updated_at=now
            )
        else:
            self._secrets[key] = SecretValue(
                key=key,
                value=encrypted_value,
                version=1,
                created_at=now,
                updated_at=now
            )

        # Also store in backend
        self._storage.store(key, encrypted_value)

        logger.info(f"Secret '{key}' stored (version {self._secrets[key].version})")

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret.

        Args:
            key: The secret key

        Returns:
            The decrypted secret value or None if not found
        """
        # First check in-memory cache
        if key in self._secrets:
            try:
                return self._decrypt(self._secrets[key].value)
            except Exception:
                pass

        # Fall back to storage backend
        encrypted_value = self._storage.retrieve(key)
        if encrypted_value:
            try:
                return self._decrypt(encrypted_value)
            except Exception:
                pass

        return None

    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: The secret key

        Returns:
            True if deleted, False if not found
        """
        deleted = False

        if key in self._secrets:
            del self._secrets[key]
            deleted = True

        if self._storage.delete(key):
            deleted = True

        if deleted:
            logger.info(f"Secret '{key}' deleted")

        return deleted

    def rotate_secret(self, key: str, new_value: str) -> bool:
        """
        Rotate a secret to a new value.

        Args:
            key: The secret key
            new_value: The new secret value

        Returns:
            True if rotated, False if key not found
        """
        if key not in self._secrets and self._storage.retrieve(key) is None:
            return False

        self.set_secret(key, new_value)
        logger.info(f"Secret '{key}' rotated")
        return True

    def list_secrets(self) -> List[str]:
        """
        List all secret keys.

        Returns:
            List of secret keys
        """
        keys = set(self._secrets.keys())
        keys.update(self._storage.list_keys())
        return list(keys)

    def get_secret_metadata(self, key: str) -> Optional[SecretValue]:
        """
        Get metadata about a secret without revealing the value.

        Args:
            key: The secret key

        Returns:
            SecretValue metadata or None if not found
        """
        return self._secrets.get(key)
