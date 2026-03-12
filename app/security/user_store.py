"""
User Store Module

Manages user storage and API key verification.

Extracted from auth.py to follow Single Responsibility Principle.

Security Features:
- SEC-001: No hardcoded credentials - uses environment variables
- GAP-001: Database-backed user store abstraction
- GAP-003: Hash API keys instead of storing plain text
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import threading

from app.shared.config.environment_config import get_config

from .user import User, UserRoles

# Setup logger
logger = logging.getLogger(__name__)


class UserStore:
    """
    Abstract user store for authentication.

    GAP-001: Replace hardcoded users with pluggable backend.
    Default implementation uses environment variables for production setup.

    Thread-safe: All operations on internal dictionaries are protected by locks.

    SOLID Principles:
    - SRP: Single responsibility - user storage only
    - OCP: Extensible via inheritance
    - DIP: Can be injected via UserStoreProtocol
    """

    def __init__(self) -> None:
        """Initialize user store from environment configuration."""
        self.config = get_config()
        self._users: dict[str, User] = {}
        self._api_keys: dict[str, str] = {}  # hashed_key -> username
        self._users_lock = threading.RLock()  # Reentrant lock for users dict
        self._api_keys_lock = threading.RLock()  # Reentrant lock for api_keys dict
        self._init_lock = threading.Lock()  # Lock for initialization
        self._load_users_from_config()

    def _load_users_from_config(self) -> None:
        """
        Load users from environment configuration.

        Environment variables format:
        - AUTH_USER_<username>_ID: user ID
        - AUTH_USER_<username>_ROLE: user role
        - AUTH_USER_<username>_PERMISSIONS: comma-separated permissions
        - AUTH_API_KEY_<keyname>: API key (will be hashed)
        - AUTH_API_KEY_<keyname>_USER: username for this API key

        Example:
        AUTH_USER_TRADER_ID=trader-001
        AUTH_USER_TRADER_ROLE=trader
        AUTH_USER_TRADER_PERMISSIONS=trade:read,trade:write
        AUTH_API_KEY_TRADER_KEY=sk_live_abc123...
        AUTH_API_KEY_TRADER_KEY_USER=trader
        """
        logger.info("Loading users from environment configuration")

        # Load user definitions
        prefix = "AUTH_USER_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Parse key format: AUTH_USER_<USERNAME>_<FIELD>
                parts = key.split("_")
                if len(parts) >= 4:
                    username = parts[2].lower()
                    field = parts[3].lower()

                    with self._users_lock:
                        if username not in self._users:
                            self._users[username] = User(
                                user_id="",
                                username=username,
                                role=UserRoles.VIEWER,
                                permissions=[],
                                is_active=True,
                            )

                        user = self._users[username]

                        if field == "id":
                            user.user_id = value
                        elif field == "role":
                            if value in [
                                UserRoles.ADMIN,
                                UserRoles.TRADER,
                                UserRoles.VIEWER,
                                UserRoles.SYSTEM,
                            ]:
                                user.role = value
                        elif field == "permissions":
                            user.permissions = [p.strip() for p in value.split(",")]
                        elif field == "active":
                            user.is_active = value.lower() == "true"

        # Load API keys
        api_key_prefix = "AUTH_API_KEY_"
        for key, value in os.environ.items():
            if key.startswith(api_key_prefix) and not key.endswith("_USER"):
                parts = key.split("_")
                if len(parts) >= 4:
                    # Key name extraction not needed, just create user_key
                    user_key = f"{key}_USER"

                    if user_key in os.environ:
                        username = os.environ[user_key].lower()
                        # Use both locks for cross-dictionary access
                        with self._users_lock, self._api_keys_lock:
                            if username in self._users:
                                # Hash the API key before storing (GAP-003 FIX)
                                hashed_key = self._hash_api_key(value)
                                self._api_keys[hashed_key] = username
                                logger.info(
                                    f"Loaded API key for user: {username}",
                                    extra={"key_name": "***REDACTED***", "username": username},
                                )

        # Log summary
        with self._users_lock, self._api_keys_lock:
            logger.info(
                f"User store initialized with {len(self._users)} users and {len(self._api_keys)} API keys",
                extra={"user_count": len(self._users), "api_key_count": len(self._api_keys)},
            )

    def _hash_api_key(self, api_key: str) -> str:
        """
        Hash API key using SHA-256.

        GAP-003 FIX: Hash API keys instead of storing plain text.
        Uses HMAC with secret key for additional security.

        Args:
            api_key: Plain text API key

        Returns:
            Hex-encoded hash of the API key
        """
        secret = self.config.api.secret_key.encode()
        key_hash = hmac.new(secret, api_key.encode(), hashlib.sha256).hexdigest()
        return key_hash

    def verify_api_key(self, api_key: str) -> str | None:
        """
        Verify API key and return username.

        GAP-003 FIX: Compare hashed keys.

        Args:
            api_key: API key to verify

        Returns:
            Username if valid, None otherwise
        """
        if not api_key:
            return None

        hashed_key = self._hash_api_key(api_key)

        with self._api_keys_lock:
            username = self._api_keys.get(hashed_key)

        if username:
            logger.debug(f"API key verified for user: {username}")

        return username

    def get_user(self, username: str) -> User | None:
        """Get user by username (thread-safe)."""
        with self._users_lock:
            return self._users.get(username)

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID (thread-safe)."""
        with self._users_lock:
            # Create a snapshot of the users to avoid holding lock during iteration
            users_snapshot = list(self._users.values())

        for user in users_snapshot:
            if user.user_id == user_id:
                return user
        return None

    def add_user(self, user: User) -> None:
        """
        Add a user to the store.

        Args:
            user: User to add
        """
        with self._users_lock:
            self._users[user.username] = user
            logger.info(f"Added user: {user.username}", extra={"username": user.username})

    def remove_user(self, username: str) -> bool:
        """
        Remove a user from the store.

        Args:
            username: Username to remove

        Returns:
            True if user was removed, False if not found
        """
        with self._users_lock:
            if username in self._users:
                del self._users[username]
                logger.info(f"Removed user: {username}", extra={"username": username})
                return True
        return False

    def add_api_key(self, username: str, api_key: str) -> bool:
        """
        Add an API key for a user.

        Args:
            username: Username to associate with API key
            api_key: Plain text API key

        Returns:
            True if API key was added, False if user not found
        """
        with self._users_lock, self._api_keys_lock:
            if username in self._users:
                hashed_key = self._hash_api_key(api_key)
                self._api_keys[hashed_key] = username
                logger.info(
                    f"Added API key for user: {username}",
                    extra={"username": username},
                )
                return True
        return False


# Global user store instance with thread-safe initialization
_user_store: UserStore | None = None
_user_store_lock = threading.Lock()


def get_user_store() -> UserStore:
    """
    Get the global user store instance with thread-safe initialization.

    Uses double-checked locking pattern for thread safety.

    This function maintains backward compatibility with existing code
    that doesn't use dependency injection.
    """
    global _user_store
    if _user_store is None:
        with _user_store_lock:
            # Double-check inside the lock
            if _user_store is None:
                logger.info("Initializing user store")
                _user_store = UserStore()
    return _user_store


def set_user_store(store: UserStore) -> None:
    """
    Set the global user store instance.

    Used for dependency injection in tests or custom configurations.

    Args:
        store: UserStore instance to use globally
    """
    global _user_store
    with _user_store_lock:
        _user_store = store
        logger.info("User store instance set externally")
