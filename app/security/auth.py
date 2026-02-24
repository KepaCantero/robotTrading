"""
Authentication and Authorization Module for API Endpoints

This module provides:
- API key authentication dependencies
- JWT token authentication dependencies
- Role-based authorization decorators
- Current user extraction helpers
- Audit logging for auth events
- Account lockout protection

SEC-001: No hardcoded credentials - uses environment variables
SEC-002: Secure token validation
SEC-003: Role-based access control
SEC-005: Audit logging for auth attempts
"""

import hashlib
import hmac
import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, TypedDict

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.shared.audit import AuditAction, AuditLogger, get_audit_logger
from app.shared.config.environment_config import get_config

# Setup logger
logger = logging.getLogger(__name__)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


class UserRoles:
    """Standard user roles for authorization."""

    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    SYSTEM = "system"


# Type definitions for dictionaries (TYP-001 fix)
class UserDict(TypedDict):
    """Typed dictionary for user storage mapping."""


class APIKeyDict(TypedDict):
    """Typed dictionary for API key to username mapping."""


class FailedAttemptsDict(TypedDict):
    """Typed dictionary for failed attempts tracking."""


class LockoutsDict(TypedDict):
    """Typed dictionary for lockout expiry tracking."""


class RateLimitsDict(TypedDict):
    """Typed dictionary for rate limit tracking."""


class User:
    """Authenticated user representation."""

    def __init__(
        self,
        user_id: str,
        username: str,
        role: str,
        permissions: List[str],
        is_active: bool = True,
    ):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions
        self.is_active = is_active

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return self.role == role or self.role == UserRoles.ADMIN

    def can_trade(self) -> bool:
        """Check if user can execute trades."""
        return self.is_active and (
            self.has_role(UserRoles.TRADER)
            or self.has_role(UserRoles.ADMIN)
            or self.has_role(UserRoles.SYSTEM)
        )

    def can_deploy(self) -> bool:
        """Check if user can deploy strategies."""
        return self.is_active and (
            self.has_role(UserRoles.ADMIN) or self.has_role(UserRoles.SYSTEM)
        )

    def __repr__(self) -> str:
        """String representation for logging (no sensitive data)."""
        return f"User(id={self.user_id}, username={self.username}, role={self.role})"


# ============================================================================
# GAP-001 FIX: Database-backed user store abstraction
# ============================================================================


class UserStore:
    """
    Abstract user store for authentication.

    GAP-001: Replace hardcoded users with pluggable backend.
    Default implementation uses environment variables for production setup.

    Thread-safe: All operations on internal dictionaries are protected by locks.
    """

    def __init__(self):
        """Initialize user store from environment configuration."""
        self.config = get_config()
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, str] = {}  # hashed_key -> username
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

    def verify_api_key(self, api_key: str) -> Optional[str]:
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

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username (thread-safe)."""
        with self._users_lock:
            return self._users.get(username)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (thread-safe)."""
        with self._users_lock:
            # Create a snapshot of the users to avoid holding lock during iteration
            users_snapshot = list(self._users.values())

        for user in users_snapshot:
            if user.user_id == user_id:
                return user
        return None


# Global user store instance with thread-safe initialization
_user_store: Optional[UserStore] = None
_user_store_lock = threading.Lock()


def get_user_store() -> UserStore:
    """
    Get the global user store instance with thread-safe initialization.

    Uses double-checked locking pattern for thread safety.
    """
    global _user_store
    if _user_store is None:
        with _user_store_lock:
            # Double-check inside the lock
            if _user_store is None:
                logger.info("Initializing user store")
                _user_store = UserStore()
    return _user_store


# ============================================================================
# GAP-002 FIX: JWT Token Validation
# ============================================================================


class JWTTokenManager:
    """
    JWT token management and validation.

    GAP-002 FIX: Implement proper JWT token validation.
    Supports token creation, validation, and refresh.
    """

    def __init__(self):
        """Initialize JWT manager from configuration."""
        self.config = get_config()
        self.secret_key = self.config.api.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = self.config.api.access_token_expire_minutes

    def create_access_token(
        self, data: Dict[str, str], expires_delta: Optional[timedelta] = None
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

    def verify_token(self, token: str) -> Optional[Dict[str, str]]:
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

    def decode_token(self, token: str) -> Optional[Dict[str, str]]:
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


# Global token manager instance with thread-safe initialization
_token_manager: Optional[JWTTokenManager] = None
_token_manager_lock = threading.Lock()


def get_token_manager() -> JWTTokenManager:
    """
    Get the global token manager instance with thread-safe initialization.

    Uses double-checked locking pattern for thread safety.
    """
    global _token_manager
    if _token_manager is None:
        with _token_manager_lock:
            # Double-check inside the lock
            if _token_manager is None:
                logger.info("Initializing JWT token manager")
                _token_manager = JWTTokenManager()
    return _token_manager


# ============================================================================
# GAP-004 FIX: Rate Limiting & Account Lockout
# ============================================================================


class AuthAttemptTracker:
    """
    Track authentication attempts for rate limiting and lockout.

    GAP-004 FIX: Add rate limiting and account lockout after failed attempts.
    GAP-006 FIX: Log all auth attempts to audit trail.
    """

    # Maximum failed attempts before lockout
    MAX_FAILED_ATTEMPTS = 5
    # Lockout duration in seconds
    LOCKOUT_DURATION = 900  # 15 minutes
    # Rate limit window in seconds
    RATE_LIMIT_WINDOW = 60
    # Max requests per window
    MAX_REQUESTS_PER_WINDOW = 20

    def __init__(self):
        """Initialize attempt tracker."""
        # Track failed attempts per identifier (IP, username, etc.)
        self._failed_attempts: Dict[str, int] = defaultdict(int)
        # Track lockout expiry times
        self._lockouts: Dict[str, float] = {}
        # Track rate limit attempts
        self._rate_limits: Dict[str, List[float]] = defaultdict(list)
        # Audit logger
        self._audit = get_audit_logger()
        # Lock for thread-safe initialization
        self._init_lock = threading.Lock()

    def record_failed_attempt(self, identifier: str, auth_method: str) -> bool:
        """
        Record a failed authentication attempt.

        Args:
            identifier: Unique identifier (IP, username, etc.)
            auth_method: Authentication method (api_key, jwt, etc.)

        Returns:
            True if account should be locked out
        """
        self._failed_attempts[identifier] += 1
        attempts = self._failed_attempts[identifier]

        # GAP-006 FIX: Log failed auth attempt to audit trail
        self._audit.log(
            action=AuditAction.AUTH_FAILED,
            user_id=None,
            username=identifier,
            details={
                "auth_method": auth_method,
                "failed_attempt": attempts,
                "max_attempts": self.MAX_FAILED_ATTEMPTS,
            },
            success=False,
            error_message=f"Failed authentication attempt {attempts}/{self.MAX_FAILED_ATTEMPTS}",
        )

        logger.warning(
            f"Failed authentication attempt {attempts}/{self.MAX_FAILED_ATTEMPTS} for {identifier}",
            extra={
                "identifier": identifier,
                "auth_method": auth_method,
                "attempts": attempts,
            },
        )

        # Check if should lock out
        if attempts >= self.MAX_FAILED_ATTEMPTS:
            self._lockouts[identifier] = time.time() + self.LOCKOUT_DURATION
            logger.error(
                f"Account locked out for {identifier}",
                extra={
                    "identifier": identifier,
                    "lockout_duration": self.LOCKOUT_DURATION,
                },
            )
            return True

        return False

    def record_successful_attempt(self, identifier: str, username: str) -> None:
        """
        Record a successful authentication attempt.

        Args:
            identifier: Unique identifier (IP, username, etc.)
            username: Authenticated username
        """
        # Clear failed attempts on success
        if identifier in self._failed_attempts:
            del self._failed_attempts[identifier]
        if identifier in self._lockouts:
            del self._lockouts[identifier]

        # GAP-006 FIX: Log successful auth to audit trail
        self._audit.log(
            action=AuditAction.USER_LOGIN,
            user_id=username,
            username=username,
            details={"auth_identifier": identifier},
            success=True,
        )

        logger.info(
            f"Successful authentication for {username}",
            extra={"identifier": identifier, "username": username},
        )

    def is_locked_out(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if identifier is currently locked out.

        Args:
            identifier: Unique identifier to check

        Returns:
            Tuple of (is_locked, seconds_remaining)
        """
        if identifier not in self._lockouts:
            return False, None

        expiry = self._lockouts[identifier]
        remaining = int(expiry - time.time())

        if remaining <= 0:
            # Lockout expired
            del self._lockouts[identifier]
            if identifier in self._failed_attempts:
                del self._failed_attempts[identifier]
            return False, None

        return True, remaining

    def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if identifier has exceeded rate limit.

        Args:
            identifier: Unique identifier to check

        Returns:
            True if within rate limit, False if exceeded
        """
        now = time.time()
        window_start = now - self.RATE_LIMIT_WINDOW

        # Clean old entries
        self._rate_limits[identifier] = [
            t for t in self._rate_limits[identifier] if t > window_start
        ]

        # Check limit
        if len(self._rate_limits[identifier]) >= self.MAX_REQUESTS_PER_WINDOW:
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                extra={
                    "identifier": identifier,
                    "request_count": len(self._rate_limits[identifier]),
                },
            )
            return False

        # Add current attempt
        self._rate_limits[identifier].append(now)
        return True

    def cleanup(self) -> None:
        """Clean up expired entries."""
        now = time.time()

        # Clean expired lockouts
        expired_lockouts = [k for k, v in self._lockouts.items() if v < now]
        for k in expired_lockouts:
            del self._lockouts[k]
            if k in self._failed_attempts:
                del self._failed_attempts[k]

        # Clean old rate limit entries
        window_start = now - self.RATE_LIMIT_WINDOW
        for identifier in list(self._rate_limits.keys()):
            self._rate_limits[identifier] = [
                t for t in self._rate_limits[identifier] if t > window_start
            ]
            if not self._rate_limits[identifier]:
                del self._rate_limits[identifier]


# Global attempt tracker instance with thread-safe initialization
_attempt_tracker: Optional[AuthAttemptTracker] = None
_attempt_tracker_lock = threading.Lock()


def get_attempt_tracker() -> AuthAttemptTracker:
    """
    Get the global attempt tracker instance with thread-safe initialization.

    Uses double-checked locking pattern for thread safety.
    """
    global _attempt_tracker
    if _attempt_tracker is None:
        with _attempt_tracker_lock:
            # Double-check inside the lock
            if _attempt_tracker is None:
                logger.info("Initializing auth attempt tracker")
                _attempt_tracker = AuthAttemptTracker()
    return _attempt_tracker


def _handle_failed_attempt(
    request_id: str,
    auth_method: str,
    attempt_tracker: AuthAttemptTracker,
    audit_logger: Optional[AuditLogger] = None,
) -> bool:
    """
    Handle a failed authentication attempt with lockout logic.

    This helper method centralizes the duplicate lockout handling code
    that was previously repeated in get_current_user_optional.

    Args:
        request_id: Request identifier (IP address or similar)
        auth_method: Authentication method used (api_key, jwt, etc.)
        attempt_tracker: AuthAttemptTracker instance
        audit_logger: Optional AuditLogger instance

    Returns:
        True if account should be locked out, False otherwise
    """
    should_lock = attempt_tracker.record_failed_attempt(request_id, auth_method)

    if audit_logger:
        audit_logger.log(
            action=AuditAction.AUTH_FAILED,
            user_id=None,
            username=request_id,
            details={"auth_method": auth_method},
            success=False,
            error_message="Authentication failed",
        )

    if should_lock:
        logger.warning(
            f"Account locked out after failed {auth_method} authentication",
            extra={"request_id": request_id},
        )

    return should_lock


# ============================================================================
# Authentication Dependencies
# ============================================================================


@contextmanager
def _audit_auth_context(
    action: AuditAction,
    auth_method: str,
    identifier: Optional[str] = None,
):
    """
    Context manager for auth audit logging.

    GAP-006 FIX: Log all auth attempts to audit trail.
    """
    audit = get_audit_logger()
    success = False
    error = None

    try:
        yield
        success = True
    except Exception as e:
        error = str(e)
        raise
    finally:
        # Only log failures here (successes are logged separately)
        if not success and error:
            audit.log(
                action=action,
                user_id=None,
                username=identifier,
                details={"auth_method": auth_method},
                success=False,
                error_message=error,
            )


async def get_current_user_optional(
    request_id: str = "unknown",
    api_key: Optional[str] = Security(api_key_header),
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> Optional[User]:
    """
    Get current user from API key or bearer token (optional).

    Returns None if no valid credentials provided.
    Used for endpoints that work with or without authentication.

    GAP-002 FIX: Implement proper JWT token validation.
    GAP-003 FIX: Use hashed API key verification.
    GAP-004 FIX: Add rate limiting.
    GAP-006 FIX: Log auth attempts to audit trail.
    """
    user_store = get_user_store()
    attempt_tracker = get_attempt_tracker()
    audit = get_audit_logger()

    # Check rate limit
    if not attempt_tracker.check_rate_limit(request_id):
        logger.warning("Rate limit exceeded for auth attempt", extra={"request_id": request_id})
        audit.log(
            action=AuditAction.AUTH_FAILED,
            user_id=None,
            username=request_id,
            details={"auth_method": "rate_limit"},
            success=False,
            error_message="Rate limit exceeded",
        )
        return None

    # Check lockout
    is_locked, remaining = attempt_tracker.is_locked_out(request_id)
    if is_locked:
        logger.warning(
            "Auth attempt blocked due to lockout",
            extra={"request_id": request_id, "remaining_seconds": remaining},
        )
        audit.log(
            action=AuditAction.AUTH_FAILED,
            user_id=None,
            username=request_id,
            details={
                "auth_method": "lockout",
                "remaining_seconds": remaining,
            },
            success=False,
            error_message=f"Account locked out. Try again in {remaining} seconds.",
        )
        return None

    # Try API key authentication
    if api_key:
        username = user_store.verify_api_key(api_key)
        if username:
            user = user_store.get_user(username)
            if user and user.is_active:
                attempt_tracker.record_successful_attempt(request_id, username)
                logger.info(
                    f"API key authentication successful for {username}",
                    extra={"request_id": request_id, "username": username},
                )
                return user
            else:
                # Invalid API key or inactive user
                _handle_failed_attempt(request_id, "api_key", attempt_tracker, audit)
                return None

    # Try bearer token authentication (GAP-002 FIX)
    if auth_header:
        token = auth_header.credentials

        try:
            token_manager = get_token_manager()
            payload = token_manager.verify_token(token)

            if payload:
                user_id = payload.get("sub")
                if user_id:
                    user = user_store.get_user_by_id(user_id)
                    if user and user.is_active:
                        attempt_tracker.record_successful_attempt(request_id, user.username)
                        logger.info(
                            f"JWT authentication successful for {user.username}",
                            extra={"request_id": request_id, "username": user.username},
                        )
                        return user
                    else:
                        # User not found or inactive
                        _handle_failed_attempt(request_id, "jwt", attempt_tracker, audit)
                        return None
            else:
                # Invalid token
                _handle_failed_attempt(request_id, "jwt", attempt_tracker, audit)
                return None

        except ImportError:
            # JWT library not available, log error
            logger.error("JWT authentication failed: library not available", exc_info=True)
            _handle_failed_attempt(request_id, "jwt", attempt_tracker, audit)
            return None
        except Exception as e:
            logger.error(
                f"JWT authentication error: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True,
            )
            _handle_failed_attempt(request_id, "jwt", attempt_tracker, audit)
            return None

    # No valid credentials provided
    return None


async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """
    Get authenticated user (required).

    Raises HTTPException if no valid credentials provided.
    Use for endpoints that require authentication.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get authenticated admin user.

    Raises HTTPException if user is not an admin.
    Use for endpoints that require admin privileges.
    """
    if not current_user.has_role(UserRoles.ADMIN):
        logger.warning(
            f"Admin access denied for {current_user.username}",
            extra={"username": current_user.username, "role": current_user.role},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user


async def get_trader_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get authenticated trader user.

    Raises HTTPException if user cannot trade.
    Use for trading endpoints.
    """
    if not current_user.can_trade():
        logger.warning(
            f"Trading access denied for {current_user.username}",
            extra={"username": current_user.username, "role": current_user.role},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trading privileges required",
        )

    return current_user


async def get_deployer_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get authenticated deployment user.

    Raises HTTPException if user cannot deploy strategies.
    Use for deployment endpoints.
    """
    if not current_user.can_deploy():
        logger.warning(
            f"Deployment access denied for {current_user.username}",
            extra={"username": current_user.username, "role": current_user.role},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deployment privileges required",
        )

    return current_user


def require_roles(*roles: str):
    """
    Dependency factory that requires specific roles.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            user: User = Depends(require_roles(UserRoles.ADMIN, UserRoles.SYSTEM))
        ):
            ...
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_role(role) for role in roles):
            logger.warning(
                f"Role check failed for {current_user.username}",
                extra={
                    "username": current_user.username,
                    "user_role": current_user.role,
                    "required_roles": list(roles),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return current_user

    return role_checker


def require_permissions(*permissions: str):
    """
    Dependency factory that requires specific permissions.

    Usage:
        @router.get("/trades")
        async def trades_endpoint(
            user: User = Depends(require_permissions("trade:read"))
        ):
            ...
    """

    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(
            current_user.has_permission(perm) or current_user.has_permission("*")
            for perm in permissions
        ):
            logger.warning(
                f"Permission check failed for {current_user.username}",
                extra={
                    "username": current_user.username,
                    "user_permissions": current_user.permissions,
                    "required_permissions": list(permissions),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of permissions: {', '.join(permissions)}",
            )
        return current_user

    return permission_checker


def get_user_id(current_user: User = Depends(get_current_user)) -> str:
    """
    Get user ID from authenticated user.

    Convenience dependency for logging and audit trails.
    """
    return current_user.user_id


def get_username(current_user: User = Depends(get_current_user)) -> str:
    """
    Get username from authenticated user.

    Convenience dependency for logging and audit trails.
    """
    return current_user.username


# ============================================================================
# Utility Functions
# ============================================================================


def create_access_token_for_user(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create access token for a user.

    Args:
        user: User to create token for
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token

    Raises:
        ImportError: If jwt library is not available
    """
    token_manager = get_token_manager()
    return token_manager.create_access_token(
        data={"sub": user.user_id, "username": user.username, "role": user.role},
        expires_delta=expires_delta,
    )


def verify_token_and_get_user(token: str) -> Optional[User]:
    """
    Verify token and return user.

    Args:
        token: JWT token to verify

    Returns:
        User if token is valid, None otherwise
    """
    token_manager = get_token_manager()
    payload = token_manager.verify_token(token)

    if payload:
        user_id = payload.get("sub")
        if user_id:
            user_store = get_user_store()
            return user_store.get_user_by_id(user_id)

    return None
