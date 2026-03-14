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

SOLID Principles Applied:
- SRP: Each class has a single responsibility (separated into modules)
- OCP: Protocol interfaces enable extensibility
- DIP: Dependency injection supported via setter functions
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from datetime import timedelta
from typing import Callable

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.shared.audit import AuditAction, AuditLogger, get_audit_logger

# Import extracted components
from .auth_attempt_tracker import AuthAttemptTracker, get_attempt_tracker
from .interfaces import AuthAttemptTrackerProtocol, JWTTokenManagerProtocol, UserStoreProtocol
from .jwt_token_manager import JWTTokenManager, get_token_manager
from .user import User, UserRoles
from .user_store import UserStore, get_user_store

# Setup logger
logger = logging.getLogger(__name__)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)

# Re-export for backward compatibility
__all__ = [
    # User classes
    "User",
    "UserRoles",
    # Store classes
    "UserStore",
    "get_user_store",
    # Token classes
    "JWTTokenManager",
    "get_token_manager",
    # Tracker classes
    "AuthAttemptTracker",
    "get_attempt_tracker",
    # Protocol interfaces
    "UserStoreProtocol",
    "JWTTokenManagerProtocol",
    "AuthAttemptTrackerProtocol",
    # Authentication dependencies
    "get_current_user_optional",
    "get_current_user",
    "get_admin_user",
    "get_trader_user",
    "get_deployer_user",
    "require_roles",
    "require_permissions",
    "get_user_id",
    "get_username",
    # Utility functions
    "create_access_token_for_user",
    "verify_token_and_get_user",
    "_audit_auth_context",
    "_handle_failed_attempt",
]


def _handle_failed_attempt(
    request_id: str,
    auth_method: str,
    attempt_tracker: AuthAttemptTrackerProtocol,
    audit_logger: AuditLogger | None = None,
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


@contextmanager
def _audit_auth_context(
    action: AuditAction,
    auth_method: str,
    identifier: str | None = None,
) -> Generator[None, None, None]:
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
    api_key: str | None = Security(api_key_header),
    auth_header: HTTPAuthorizationCredentials | None = Security(http_bearer),
    user_store: UserStoreProtocol | None = None,
    token_manager: JWTTokenManagerProtocol | None = None,
    attempt_tracker: AuthAttemptTrackerProtocol | None = None,
) -> User | None:
    """
    Get current user from API key or bearer token (optional).

    Returns None if no valid credentials provided.
    Used for endpoints that work with or without authentication.

    GAP-002 FIX: Implement proper JWT token validation.
    GAP-003 FIX: Use hashed API key verification.
    GAP-004 FIX: Add rate limiting.
    GAP-006 FIX: Log auth attempts to audit trail.

    SOLID Principles:
    - DIP: Accepts dependencies via parameters (defaults to global instances)
    """
    # Use injected dependencies or fall back to global instances
    store = user_store or get_user_store()
    tracker = attempt_tracker or get_attempt_tracker()
    jwt_manager = token_manager or get_token_manager()
    audit = get_audit_logger()

    # Check rate limit
    if not tracker.check_rate_limit(request_id):
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
    is_locked, remaining = tracker.is_locked_out(request_id)
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
        username = store.verify_api_key(api_key)
        if username:
            user = store.get_user(username)
            if user and isinstance(user, User) and user.is_active:
                tracker.record_successful_attempt(request_id, username)
                logger.info(
                    f"API key authentication successful for {username}",
                    extra={"request_id": request_id, "username": username},
                )
                return user
            else:
                # Invalid API key or inactive user
                _handle_failed_attempt(request_id, "api_key", tracker, audit)
                return None

    # Try bearer token authentication (GAP-002 FIX)
    if auth_header:
        token = auth_header.credentials

        try:
            payload = jwt_manager.verify_token(token)

            if payload:
                user_id = payload.get("sub")
                if user_id:
                    user = store.get_user_by_id(user_id)
                    if user and isinstance(user, User) and user.is_active:
                        tracker.record_successful_attempt(request_id, user.username)
                        logger.info(
                            f"JWT authentication successful for {user.username}",
                            extra={"request_id": request_id, "username": user.username},
                        )
                        return user
                    else:
                        # User not found or inactive
                        _handle_failed_attempt(request_id, "jwt", tracker, audit)
                        return None
            else:
                # Invalid token
                _handle_failed_attempt(request_id, "jwt", tracker, audit)
                return None

        except ImportError:
            # JWT library not available, log error
            logger.error("JWT authentication failed: library not available", exc_info=True)
            _handle_failed_attempt(request_id, "jwt", tracker, audit)
            return None
        except Exception as e:
            logger.error(
                f"JWT authentication error: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True,
            )
            _handle_failed_attempt(request_id, "jwt", tracker, audit)
            return None

    # No valid credentials provided
    return None


async def get_current_user(
    current_user: User | None = Depends(get_current_user_optional),
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


def require_roles(*roles: str) -> Callable[[User], User]:
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


def require_permissions(*permissions: str) -> Callable[[User], User]:
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


def create_access_token_for_user(user: User, expires_delta: timedelta | None = None) -> str:
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


def verify_token_and_get_user(token: str) -> User | None:
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
