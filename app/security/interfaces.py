"""
Security Interfaces and Protocols

This module defines Protocol interfaces for security components,
enabling dependency injection and extensibility.

SOLID Principles:
- OCP: Open for extension via Protocol interfaces
- DIP: Depend on abstractions, not concretions
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import timedelta


@runtime_checkable
class UserStoreProtocol(Protocol):
    """
    Protocol for user storage backends.

    Enables pluggable user storage (database, LDAP, environment variables, etc.)
    """

    def verify_api_key(self, api_key: str) -> str | None:
        """
        Verify API key and return username.

        Args:
            api_key: API key to verify

        Returns:
            Username if valid, None otherwise
        """
        ...

    def get_user(self, username: str) -> Any | None:
        """
        Get user by username.

        Args:
            username: Username to look up

        Returns:
            User object if found, None otherwise
        """
        ...

    def get_user_by_id(self, user_id: str) -> Any | None:
        """
        Get user by ID.

        Args:
            user_id: User ID to look up

        Returns:
            User object if found, None otherwise
        """
        ...


@runtime_checkable
class JWTTokenManagerProtocol(Protocol):
    """
    Protocol for JWT token management.

    Enables pluggable token implementations (JWT, Paseto, etc.)
    """

    def create_access_token(
        self, data: dict[str, str], expires_delta: timedelta | None = None
    ) -> str:
        """
        Create access token.

        Args:
            data: Data to encode in token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded token string
        """
        ...

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """
        Verify and decode token.

        Args:
            token: Token to verify

        Returns:
            Decoded payload if valid, None otherwise
        """
        ...

    def decode_token(self, token: str) -> dict[str, Any] | None:
        """
        Decode token without verification (for debugging only).

        WARNING: This does NOT verify the signature.

        Args:
            token: Token to decode

        Returns:
            Decoded payload or None
        """
        ...


@runtime_checkable
class AuthAttemptTrackerProtocol(Protocol):
    """
    Protocol for authentication attempt tracking.

    Enables pluggable tracking backends (in-memory, Redis, database, etc.)
    """

    def record_failed_attempt(self, identifier: str, auth_method: str) -> bool:
        """
        Record a failed authentication attempt.

        Args:
            identifier: Unique identifier (IP, username, etc.)
            auth_method: Authentication method (api_key, jwt, etc.)

        Returns:
            True if account should be locked out
        """
        ...

    def record_successful_attempt(self, identifier: str, username: str) -> None:
        """
        Record a successful authentication attempt.

        Args:
            identifier: Unique identifier (IP, username, etc.)
            username: Authenticated username
        """
        ...

    def is_locked_out(self, identifier: str) -> tuple[bool, int | None]:
        """
        Check if identifier is currently locked out.

        Args:
            identifier: Unique identifier to check

        Returns:
            Tuple of (is_locked, seconds_remaining)
        """
        ...

    def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if identifier has exceeded rate limit.

        Args:
            identifier: Unique identifier to check

        Returns:
            True if within rate limit, False if exceeded
        """
        ...

    def cleanup(self) -> None:
        """Clean up expired entries."""
        ...
