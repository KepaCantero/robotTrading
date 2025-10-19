"""
Services package for AlgoTrading MVP.

This package contains service classes for business logic and CRUD operations.
"""

from .user_service import (
    UserService,
    AccountService,
    get_user_service,
    get_account_service,
)

from .auth_service import (
    JWTAuthService,
    auth_service,
    get_current_user,
    get_current_active_user,
    get_current_verified_user,
    require_role,
    require_admin_role,
    require_trader_role,
    login_for_access_token,
    refresh_access_token_endpoint,
    get_token_expiration_time,
    get_refresh_token_expiration_time,
    create_token_payload,
)

__all__ = [
    "UserService",
    "AccountService",
    "get_user_service",
    "get_account_service",
    "JWTAuthService",
    "auth_service",
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "require_role",
    "require_admin_role",
    "require_trader_role",
    "login_for_access_token",
    "refresh_access_token_endpoint",
    "get_token_expiration_time",
    "get_refresh_token_expiration_time",
    "create_token_payload",
]
