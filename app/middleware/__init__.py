"""
Middleware package for AlgoTrading MVP.

This package contains middleware components for authentication,
authorization, and request processing.
"""

from .auth import (
    AuthenticationMiddleware,
    RoleBasedAccessMiddleware,
    create_auth_middleware,
    create_rbac_middleware,
    DEFAULT_PROTECTED_PATHS,
    DEFAULT_EXCLUDED_PATHS,
    DEFAULT_ROLE_REQUIREMENTS,
)

__all__ = [
    "AuthenticationMiddleware",
    "RoleBasedAccessMiddleware",
    "create_auth_middleware",
    "create_rbac_middleware",
    "DEFAULT_PROTECTED_PATHS",
    "DEFAULT_EXCLUDED_PATHS",
    "DEFAULT_ROLE_REQUIREMENTS",
]
