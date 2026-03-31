"""
Authentication Attempt Tracker Module

Tracks authentication attempts for rate limiting and account lockout.

Extracted from auth.py to follow Single Responsibility Principle.

Security Features:
- GAP-004: Rate limiting and account lockout after failed attempts
- GAP-006: Audit logging for all auth attempts
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict

from app.shared.audit import AuditAction, AuditLogger, get_audit_logger

# Setup logger
logger = logging.getLogger(__name__)


class AuthAttemptTracker:
    """
    Track authentication attempts for rate limiting and lockout.

    GAP-004 FIX: Add rate limiting and account lockout after failed attempts.
    GAP-006 FIX: Log all auth attempts to audit trail.

    SOLID Principles:
    - SRP: Single responsibility - auth attempt tracking only
    - OCP: Extensible via inheritance
    - DIP: Can be injected via AuthAttemptTrackerProtocol
    """

    # Maximum failed attempts before lockout
    MAX_FAILED_ATTEMPTS: int = 5
    # Lockout duration in seconds
    LOCKOUT_DURATION: int = 900  # 15 minutes
    # Rate limit window in seconds
    RATE_LIMIT_WINDOW: int = 60
    # Max requests per window
    MAX_REQUESTS_PER_WINDOW: int = 20

    def __init__(self, audit_logger: AuditLogger | None = None) -> None:
        """
        Initialize attempt tracker.

        Args:
            audit_logger: Optional audit logger for dependency injection
        """
        # Track failed attempts per identifier (IP, username, etc.)
        self._failed_attempts: dict[str, int] = defaultdict(int)
        # Track lockout expiry times
        self._lockouts: dict[str, float] = {}
        # Track rate limit attempts
        self._rate_limits: dict[str, list[float]] = defaultdict(list)
        # Audit logger - inject or use default
        self._audit = audit_logger or get_audit_logger()
        # Lock for thread-safe operations
        self._lock = threading.RLock()

    def record_failed_attempt(self, identifier: str, auth_method: str) -> bool:
        """
        Record a failed authentication attempt.

        Args:
            identifier: Unique identifier (IP, username, etc.)
            auth_method: Authentication method (api_key, jwt, etc.)

        Returns:
            True if account should be locked out
        """
        with self._lock:
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
        with self._lock:
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

    def is_locked_out(self, identifier: str) -> tuple[bool, int | None]:
        """
        Check if identifier is currently locked out.

        Args:
            identifier: Unique identifier to check

        Returns:
            Tuple of (is_locked, seconds_remaining)
        """
        with self._lock:
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
        with self._lock:
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
        with self._lock:
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

    def get_failed_attempts(self, identifier: str) -> int:
        """
        Get the number of failed attempts for an identifier.

        Args:
            identifier: Unique identifier to check

        Returns:
            Number of failed attempts
        """
        with self._lock:
            return self._failed_attempts.get(identifier, 0)

    def reset_attempts(self, identifier: str) -> None:
        """
        Reset failed attempts for an identifier.

        Args:
            identifier: Unique identifier to reset
        """
        with self._lock:
            if identifier in self._failed_attempts:
                del self._failed_attempts[identifier]
            if identifier in self._lockouts:
                del self._lockouts[identifier]
            if identifier in self._rate_limits:
                del self._rate_limits[identifier]
            logger.info(f"Reset attempts for {identifier}", extra={"identifier": identifier})


# Global attempt tracker instance with thread-safe initialization
_attempt_tracker: AuthAttemptTracker | None = None
_attempt_tracker_lock = threading.Lock()


def get_attempt_tracker() -> AuthAttemptTracker:
    """
    Get the global attempt tracker instance with thread-safe initialization.

    Uses double-checked locking pattern for thread safety.

    This function maintains backward compatibility with existing code
    that doesn't use dependency injection.
    """
    global _attempt_tracker
    if _attempt_tracker is None:
        with _attempt_tracker_lock:
            # Double-check inside the lock
            if _attempt_tracker is None:
                logger.info("Initializing auth attempt tracker")
                _attempt_tracker = AuthAttemptTracker()
    return _attempt_tracker


def set_attempt_tracker(tracker: AuthAttemptTracker) -> None:
    """
    Set the global attempt tracker instance.

    Used for dependency injection in tests or custom configurations.

    Args:
        tracker: AuthAttemptTracker instance to use globally
    """
    global _attempt_tracker
    with _attempt_tracker_lock:
        _attempt_tracker = tracker
        logger.info("Attempt tracker instance set externally")
