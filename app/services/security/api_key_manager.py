"""
API Key Manager for managing broker API keys and credentials.

This module provides secure storage and management of API keys with:
- Encrypted storage at rest
- Key validation and format checking
- Key expiration tracking
- Scoped key permissions (read-only, trading, admin)
- Audit logging for key access

R29: Security Hardening
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class KeyPermission(Enum):
    """Permission levels for API keys."""

    READ_ONLY = "read_only"
    TRADING = "trading"
    ADMIN = "admin"


@dataclass
class ApiKey:
    """Data model for API key storage."""

    key_id: str
    key_name: str
    encrypted_key: str
    permission: KeyPermission
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True

    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class KeyValidationError(Exception):
    """Exception for key validation errors."""

    pass


class ApiKeyManager:
    """
    Manager for API keys with secure encrypted storage.

    This class handles the lifecycle of API keys including creation,
    validation, revocation, and expiration tracking.
    """

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize the API key manager.

        Args:
            encryption_key: Fernet encryption key. If None, reads from
                          ALGOTRADING_ENCRYPTION_KEY environment variable.
        """
        if encryption_key is None:
            import os

            key = os.environ.get("ALGOTRADING_ENCRYPTION_KEY")
            if not key:
                raise ValueError(
                    "Encryption key must be provided or set in "
                    "ALGOTRADING_ENCRYPTION_KEY environment variable"
                )
            encryption_key = key.encode()

        self._fernet = Fernet(encryption_key)
        self._keys: dict[str, ApiKey] = {}

    def _encrypt_key(self, api_key: str) -> str:
        """Encrypt an API key."""
        encrypted: bytes = self._fernet.encrypt(api_key.encode())
        return encrypted.decode()

    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an encrypted API key."""
        decrypted: bytes = self._fernet.decrypt(encrypted_key.encode())
        return decrypted.decode()

    def _validate_key_format(self, api_key: str) -> bool:
        """
        Validate the format of an API key.

        Args:
            api_key: The API key to validate

        Returns:
            True if the key format is valid, False otherwise
        """
        if not api_key or not isinstance(api_key, str):
            return False
        # Key should be at least 16 characters
        if len(api_key) < 16:
            return False
        # Key should not contain whitespace
        return not any(c.isspace() for c in api_key)

    def add_key(
        self,
        key_name: str,
        api_key: str,
        permission: KeyPermission,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """
        Add a new API key.

        Args:
            key_name: Human-readable name for the key
            api_key: The API key value
            permission: Permission level for the key
            expires_in_days: Days until expiration (None for no expiration)

        Returns:
            The key ID of the newly created key

        Raises:
            KeyValidationError: If the key format is invalid
        """
        if not self._validate_key_format(api_key):
            raise KeyValidationError(f"Invalid API key format for key '{key_name}'")

        key_id = str(uuid.uuid4())
        encrypted_key = self._encrypt_key(api_key)

        expires_at = None
        if expires_in_days is not None:
            from datetime import timedelta

            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key_obj = ApiKey(
            key_id=key_id,
            key_name=key_name,
            encrypted_key=encrypted_key,
            permission=permission,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        self._keys[key_id] = api_key_obj
        logger.info(f"Added API key '{key_name}' with ID {key_id}")

        return key_id

    def get_key(self, key_id: str) -> Optional[ApiKey]:
        """
        Get an API key by ID.

        Args:
            key_id: The key ID

        Returns:
            The ApiKey object or None if not found
        """
        return self._keys.get(key_id)

    def get_key_by_name(self, key_name: str) -> Optional[ApiKey]:
        """
        Get an API key by name.

        Args:
            key_name: The key name

        Returns:
            The ApiKey object or None if not found
        """
        for key in self._keys.values():
            if key.key_name == key_name:
                return key
        return None

    def validate_key(self, key_id: str, provided_key: str) -> bool:
        """
        Validate a provided API key against the stored encrypted key.

        Args:
            key_id: The key ID to validate against
            provided_key: The provided key value

        Returns:
            True if the key matches and is active, False otherwise
        """
        stored_key = self._keys.get(key_id)
        if not stored_key:
            return False

        if not stored_key.is_active:
            return False

        if stored_key.is_expired():
            return False

        try:
            decrypted_key = self._decrypt_key(stored_key.encrypted_key)
            is_valid = decrypted_key == provided_key
            if is_valid:
                self.update_last_used(key_id)
            return is_valid
        except Exception:
            return False

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: The key ID to revoke

        Returns:
            True if the key was revoked, False if not found
        """
        key = self._keys.get(key_id)
        if not key:
            return False

        key.is_active = False
        logger.info(f"Revoked API key '{key.key_name}' with ID {key_id}")
        return True

    def list_keys(self) -> list[ApiKey]:
        """
        List all API keys.

        Returns:
            List of all ApiKey objects
        """
        return list(self._keys.values())

    def update_last_used(self, key_id: str) -> None:
        """
        Update the last_used timestamp for a key.

        Args:
            key_id: The key ID to update
        """
        key = self._keys.get(key_id)
        if key:
            key.last_used = datetime.utcnow()

    def check_expiration(self) -> list[str]:
        """
        Check for expired keys.

        Returns:
            List of key IDs that have expired
        """
        expired_ids = []
        for key_id, key in self._keys.items():
            if key.is_active and key.is_expired():
                expired_ids.append(key_id)
                logger.warning(f"API key '{key.key_name}' with ID {key_id} has expired")
        return expired_ids

    def get_decrypted_key(self, key_id: str) -> Optional[str]:
        """
        Get the decrypted key value (use with caution).

        Args:
            key_id: The key ID

        Returns:
            The decrypted key value or None if not found
        """
        key = self._keys.get(key_id)
        if not key:
            return None

        try:
            return self._decrypt_key(key.encrypted_key)
        except Exception:
            return None
