"""
JWT Token Manager Module

Handles JWT token creation and validation.

Extracted from auth.py to follow Single Responsibility Principle.

Security Features:
- GAP-002: Proper JWT token validation
- SEC-002: Secure token validation with expiration checking
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Any

from app.shared.config.environment_config import get_config

# Setup logger
logger = logging.getLogger(__name__)


class JWTTokenManager:
    """
    JWT token management and validation.

    GAP-002 FIX: Implement proper JWT token validation.
    Supports token creation, validation, and refresh.

    SOLID Principles:
    - SRP: Single responsibility - JWT token management only
    - OCP: Extensible via inheritance
    - DIP: Can be injected via JWTTokenManagerProtocol
    """

    def __init__(self) -> None:
        """Initialize JWT manager from configuration."""
        self.config = get_config()
        self.secret_key = self.config.api.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = self.config.api.access_token_expire_minutes

    def create_access_token(
        self, data: dict[str, str], expires_delta: timedelta | None = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Data to encode in token (e.g., {"sub": user_id})
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token

        Raises:
            ImportError: If jwt library is not available
        """
        try:
            import jwt
        except ImportError:
            logger.error(
                "JWT library not available. Install with: pip install pyjwt", exc_info=True
            )
            raise ImportError("JWT library not available. Install with: pip install pyjwt")

        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        logger.info(
            "Created access token",
            extra={"user_id": data.get("sub"), "expires": expire.isoformat()},
        )

        return encoded_jwt

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """
        Verify and decode JWT token.

        GAP-002 FIX: Implement proper token validation with expiration checking.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token payload if valid, None otherwise

        Raises:
            ImportError: If jwt library is not available
        """
        try:
            import jwt
        except ImportError:
            logger.error(
                "JWT library not available. Install with: pip install pyjwt", exc_info=True
            )
            raise ImportError("JWT library not available. Install with: pip install pyjwt")

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            token_type = payload.get("type")
            if token_type != "access":
                logger.warning(
                    f"Invalid token type: {token_type}", extra={"token_type": token_type}
                )
                return None

            # Check expiration (jwt.decode already does this, but log it)
            exp = payload.get("exp")
            if exp:
                expire_time = datetime.fromtimestamp(exp)
                if expire_time < datetime.utcnow():
                    logger.warning("Token expired", extra={"expires": expire_time.isoformat()})
                    return None

            user_id = payload.get("sub")
            logger.info(f"Token verified for user: {user_id}")

            return payload

        except ImportError:
            logger.error("JWT library error during token verification", exc_info=True)
            raise
        except Exception as e:
            logger.warning(
                f"Token verification failed: {str(e)}", extra={"error": str(e)}, exc_info=True
            )
            return None

    def decode_token(self, token: str) -> dict[str, Any] | None:
        """
        Decode token without verification (for debugging only).

        WARNING: This does NOT verify the signature. Use verify_token for security.

        Args:
            token: JWT token to decode

        Returns:
            Decoded token payload or None
        """
        try:
            import jwt
        except ImportError:
            logger.error("JWT library not available", exc_info=True)
            return None

        try:
            # Decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.warning(f"Token decode failed: {str(e)}", exc_info=True)
            return None

    def refresh_token(self, token: str) -> str | None:
        """
        Refresh an existing token.

        Args:
            token: Existing valid token

        Returns:
            New token with extended expiration, or None if invalid
        """
        payload = self.verify_token(token)
        if not payload:
            return None

        # Create new token with same data but fresh expiration
        data = {k: v for k, v in payload.items() if k not in ["exp", "iat", "type"]}
        return self.create_access_token(data)


# Global token manager instance with thread-safe initialization
_token_manager: JWTTokenManager | None = None
_token_manager_lock = threading.Lock()


def get_token_manager() -> JWTTokenManager:
    """
    Get the global token manager instance with thread-safe initialization.

    Uses double-checked locking pattern for thread safety.

    This function maintains backward compatibility with existing code
    that doesn't use dependency injection.
    """
    global _token_manager
    if _token_manager is None:
        with _token_manager_lock:
            # Double-check inside the lock
            if _token_manager is None:
                logger.info("Initializing JWT token manager")
                _token_manager = JWTTokenManager()
    return _token_manager


def set_token_manager(manager: JWTTokenManager) -> None:
    """
    Set the global token manager instance.

    Used for dependency injection in tests or custom configurations.

    Args:
        manager: JWTTokenManager instance to use globally
    """
    global _token_manager
    with _token_manager_lock:
        _token_manager = manager
        logger.info("Token manager instance set externally")
