"""
Authentication middleware for AlgoTrading MVP.

This module provides authentication middleware for FastAPI applications
with JWT token validation and role-based access control.
"""

from typing import Optional, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.auth_service import auth_service


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication and role-based access control."""

    def __init__(
        self,
        app: ASGIApp,
        protected_paths: Optional[List[str]] = None,
        excluded_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.protected_paths = protected_paths or ["/api/"]
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/token",
            "/auth/refresh",
        ]

    async def dispatch(self, request: Request, call_next):
        """
        Process request through authentication middleware.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response: Processed response
        """
        # Check if path requires authentication
        if not self._requires_auth(request.url.path):
            return await call_next(request)

        # Extract token from Authorization header
        token = self._extract_token(request)
        if not token:
            return self._unauthorized_response("Missing authentication token")

        try:
            # Verify token
            payload = auth_service.verify_token(token)

            # Check token type
            if payload.get("type") != "access":
                return self._unauthorized_response("Invalid token type")

            # Add user info to request state
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.user_role = payload.get("role")
            request.state.user_active = payload.get("is_active", False)
            request.state.user_verified = payload.get("is_verified", False)

            # Check if user is active
            if not request.state.user_active:
                return self._forbidden_response("Inactive user")

            return await call_next(request)

        except HTTPException as e:
            return self._unauthorized_response(e.detail)
        except Exception:
            return self._unauthorized_response("Invalid authentication token")

    def _requires_auth(self, path: str) -> bool:
        """
        Check if path requires authentication.

        Args:
            path: Request path

        Returns:
            bool: True if authentication required
        """
        # Check excluded paths first
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return False

        # Check protected paths
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header.

        Args:
            request: FastAPI request

        Returns:
            Optional[str]: JWT token or None
        """
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None

    def _unauthorized_response(self, detail: str) -> JSONResponse:
        """Create unauthorized response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": detail, "error": "unauthorized"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _forbidden_response(self, detail: str) -> JSONResponse:
        """Create forbidden response."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN, content={"detail": detail, "error": "forbidden"}
        )


class RoleBasedAccessMiddleware(BaseHTTPMiddleware):
    """Middleware for role-based access control."""

    def __init__(
        self,
        app: ASGIApp,
        role_requirements: Optional[dict] = None,
    ):
        super().__init__(app)
        self.role_requirements = role_requirements or {}

    async def dispatch(self, request: Request, call_next):
        """
        Process request through role-based access control.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response: Processed response
        """
        # Check if path has role requirements
        required_role = self._get_required_role(request.url.path)
        if not required_role:
            return await call_next(request)

        # Get user role from request state
        user_role = getattr(request.state, "user_role", None)
        if not user_role:
            return self._forbidden_response("User role not found")

        # Check role permissions
        if not self._has_permission(user_role, required_role):
            return self._forbidden_response(f"Requires {required_role} role or higher")

        return await call_next(request)

    def _get_required_role(self, path: str) -> Optional[str]:
        """
        Get required role for path.

        Args:
            path: Request path

        Returns:
            Optional[str]: Required role or None
        """
        for path_pattern, required_role in self.role_requirements.items():
            if path.startswith(path_pattern):
                return required_role
        return None

    def _has_permission(self, user_role: str, required_role: str) -> bool:
        """
        Check if user has required permission.

        Args:
            user_role: User's role
            required_role: Required role

        Returns:
            bool: True if user has permission
        """
        # Admin has access to everything
        if user_role == "admin":
            return True

        # Role hierarchy: admin > trader > viewer
        role_hierarchy = {"admin": 3, "trader": 2, "viewer": 1}

        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level

    def _forbidden_response(self, detail: str) -> JSONResponse:
        """Create forbidden response."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN, content={"detail": detail, "error": "forbidden"}
        )


# Utility functions for middleware configuration


def create_auth_middleware(
    app: ASGIApp,
    protected_paths: Optional[List[str]] = None,
    excluded_paths: Optional[List[str]] = None,
) -> AuthenticationMiddleware:
    """
    Create authentication middleware instance.

    Args:
        app: FastAPI application
        protected_paths: Paths that require authentication
        excluded_paths: Paths excluded from authentication

    Returns:
        AuthenticationMiddleware: Configured middleware instance
    """
    return AuthenticationMiddleware(
        app=app,
        protected_paths=protected_paths,
        excluded_paths=excluded_paths,
    )


def create_rbac_middleware(
    app: ASGIApp,
    role_requirements: Optional[dict] = None,
) -> RoleBasedAccessMiddleware:
    """
    Create role-based access control middleware instance.

    Args:
        app: FastAPI application
        role_requirements: Path to role mapping

    Returns:
        RoleBasedAccessMiddleware: Configured middleware instance
    """
    return RoleBasedAccessMiddleware(
        app=app,
        role_requirements=role_requirements,
    )


# Default middleware configurations

DEFAULT_PROTECTED_PATHS = [
    "/api/users/",
    "/api/accounts/",
    "/api/strategies/",
    "/api/orders/",
    "/api/backtest/",
]

DEFAULT_EXCLUDED_PATHS = [
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/token",
    "/auth/refresh",
    "/auth/register",
]

DEFAULT_ROLE_REQUIREMENTS = {
    "/api/admin/": "admin",
    "/api/trading/": "trader",
    "/api/strategies/": "trader",
    "/api/orders/": "trader",
    "/api/backtest/": "trader",
    "/api/users/": "admin",
    "/api/accounts/": "trader",
}
