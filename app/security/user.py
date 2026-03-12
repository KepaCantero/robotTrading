"""
User Domain Model

Represents authenticated users and their permissions.

Extracted from auth.py to follow Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from typing import Any

# Setup logger
logger = logging.getLogger(__name__)


class UserRoles:
    """Standard user roles for authorization."""

    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    SYSTEM = "system"


class User:
    """
    Authenticated user representation.

    SOLID Principles:
    - SRP: Single responsibility - user representation and permission checking
    """

    def __init__(
        self,
        user_id: str,
        username: str,
        role: str,
        permissions: list[str],
        is_active: bool = True,
    ) -> None:
        """
        Initialize user.

        Args:
            user_id: Unique user identifier
            username: User's username
            role: User's role (admin, trader, viewer, system)
            permissions: List of permissions
            is_active: Whether user account is active
        """
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions
        self.is_active = is_active

    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if user has permission
        """
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """
        Check if user has a specific role.

        Admin role has all permissions.

        Args:
            role: Role to check

        Returns:
            True if user has role or is admin
        """
        return self.role == role or self.role == UserRoles.ADMIN

    def can_trade(self) -> bool:
        """
        Check if user can execute trades.

        Returns:
            True if user can trade
        """
        return self.is_active and (
            self.has_role(UserRoles.TRADER)
            or self.has_role(UserRoles.ADMIN)
            or self.has_role(UserRoles.SYSTEM)
        )

    def can_deploy(self) -> bool:
        """
        Check if user can deploy strategies.

        Returns:
            True if user can deploy
        """
        return self.is_active and (
            self.has_role(UserRoles.ADMIN) or self.has_role(UserRoles.SYSTEM)
        )

    def __repr__(self) -> str:
        """String representation for logging (no sensitive data)."""
        return f"User(id={self.user_id}, username={self.username}, role={self.role})"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert user to dictionary representation.

        Returns:
            Dictionary with user data
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "permissions": self.permissions,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        """
        Create user from dictionary.

        Args:
            data: Dictionary with user data

        Returns:
            User instance
        """
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            role=data["role"],
            permissions=data.get("permissions", []),
            is_active=data.get("is_active", True),
        )
