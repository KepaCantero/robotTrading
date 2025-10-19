"""
JWT Authentication Service for AlgoTrading MVP.

This module provides JWT token generation, validation, and OAuth 2.0 password flow
implementation with role-based access control.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.user import User, UserRole
from app.services.user_service import get_user_service

# Initialize settings
settings = get_settings()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class JWTAuthService:
    """JWT Authentication service with OAuth 2.0 password flow."""

    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            str: JWT access token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "type": "access"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            str: JWT refresh token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({"exp": expire, "type": "refresh"})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Dict[str, Any]: Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def authenticate_user(
        self, email: str, password: str, db_session: AsyncSession
    ) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: User password
            db_session: Database session

        Returns:
            Optional[User]: Authenticated user or None
        """
        user_service = get_user_service(db_session)
        user = await user_service.authenticate_user(email, password)
        return user

    async def create_tokens_for_user(self, user: User) -> Dict[str, str]:
        """
        Create access and refresh tokens for user.

        Args:
            user: User instance

        Returns:
            Dict[str, str]: Dictionary with access_token and refresh_token
        """
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        }

        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(
        self, refresh_token: str, db_session: AsyncSession
    ) -> Dict[str, str]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: JWT refresh token
            db_session: Database session

        Returns:
            Dict[str, str]: New access token

        Raises:
            HTTPException: If refresh token is invalid
        """
        try:
            payload = self.verify_token(refresh_token)

            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )

            user_service = get_user_service(db_session)
            user = await user_service.get_user_by_id(int(user_id))

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )

            return await self.create_tokens_for_user(user)

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token",
            )


# Global auth service instance
auth_service = JWTAuthService()


# Dependency functions for FastAPI


async def get_current_user(
    token: str = Depends(oauth2_scheme), db_session: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        token: JWT access token
        db_session: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        payload = auth_service.verify_token(token)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        user_service = get_user_service(db_session)
        user = await user_service.get_user_by_id(int(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
            )

        return user

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        User: Active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


async def get_current_verified_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Get current verified user.

    Args:
        current_user: Current active user

    Returns:
        User: Verified user

    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not verified")
    return current_user


# Role-based access control dependencies


def require_role(required_role: UserRole):
    """
    Create dependency for role-based access control.

    Args:
        required_role: Required user role

    Returns:
        Dependency function
    """

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
        return current_user

    return role_checker


def require_admin_role():
    """Create dependency for admin-only access."""
    return require_role(UserRole.ADMIN)


def require_trader_role():
    """Create dependency for trader or admin access."""
    return require_role(UserRole.TRADER)


# OAuth 2.0 password flow endpoints


async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_session: AsyncSession = Depends(get_db_session),
) -> Dict[str, str]:
    """
    OAuth 2.0 password flow login endpoint.

    Args:
        form_data: OAuth2 password form data
        db_session: Database session

    Returns:
        Dict[str, str]: Access and refresh tokens

    Raises:
        HTTPException: If authentication fails
    """
    user = await auth_service.authenticate_user(
        form_data.username, form_data.password, db_session  # OAuth2 uses 'username' field for email
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    return await auth_service.create_tokens_for_user(user)


async def refresh_access_token_endpoint(
    refresh_token: str, db_session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Refresh access token endpoint.

    Args:
        refresh_token: JWT refresh token
        db_session: Database session

    Returns:
        Dict[str, str]: New access token
    """
    return await auth_service.refresh_access_token(refresh_token, db_session)


# Utility functions


def get_token_expiration_time() -> datetime:
    """Get token expiration time."""
    return datetime.utcnow() + timedelta(minutes=auth_service.access_token_expire_minutes)


def get_refresh_token_expiration_time() -> datetime:
    """Get refresh token expiration time."""
    return datetime.utcnow() + timedelta(days=auth_service.refresh_token_expire_days)


def create_token_payload(user: User) -> Dict[str, Any]:
    """
    Create token payload for user.

    Args:
        user: User instance

    Returns:
        Dict[str, Any]: Token payload
    """
    return {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "iat": datetime.utcnow(),
    }
