"""
User and Account models for AlgoTrading MVP.

This module defines the User and Account SQLAlchemy models with
bcrypt password hashing and comprehensive user management.
"""

import bcrypt
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, 
    ForeignKey, Numeric, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles for role-based access control."""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class AccountStatus(str, enum.Enum):
    """Account status for trading accounts."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(Base):
    """
    User model for authentication and profile management.
    
    This model handles user authentication, profile data, and
    role-based access control for the AlgoTrading MVP.
    """
    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile fields
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Role and permissions
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.TRADER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Additional profile data
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def is_trader(self) -> bool:
        """Check if user has trader role."""
        return self.role == UserRole.TRADER

    def set_password(self, password: str) -> None:
        """
        Hash and set user password.
        
        Args:
            password: Plain text password to hash
        """
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """
        Verify user password.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary representation.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            dict: User data dictionary
        """
        data = {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
        }
        
        if include_sensitive:
            data["password_hash"] = self.password_hash
            
        return data


class Account(Base):
    """
    Account model for trading account management.
    
    This model handles trading accounts associated with users,
    including account balances, settings, and trading preferences.
    """
    __tablename__ = "accounts"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to user
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Account identification
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), default="trading", nullable=False)
    
    # Account status and settings
    status: Mapped[AccountStatus] = mapped_column(SQLEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Trading settings
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    max_position_size: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Account balances (in default currency)
    balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    available_balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Additional settings
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for additional settings
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, user_id={self.user_id}, name='{self.account_name}', status='{self.status}')>"

    @property
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == AccountStatus.ACTIVE

    @property
    def display_name(self) -> str:
        """Get account display name."""
        return f"{self.account_name} ({self.default_currency})"

    def can_trade(self) -> bool:
        """
        Check if account can perform trading operations.
        
        Returns:
            bool: True if account can trade, False otherwise
        """
        return (
            self.is_active and 
            self.available_balance > 0 and
            self.user.is_active
        )

    def update_balance(self, amount: float, available: Optional[float] = None) -> None:
        """
        Update account balance.
        
        Args:
            amount: New total balance
            available: New available balance (defaults to amount)
        """
        self.balance = amount
        self.available_balance = available if available is not None else amount

    def to_dict(self) -> dict:
        """
        Convert account to dictionary representation.
        
        Returns:
            dict: Account data dictionary
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_name": self.account_name,
            "account_type": self.account_type,
            "status": self.status.value,
            "is_primary": self.is_primary,
            "default_currency": self.default_currency,
            "risk_tolerance": self.risk_tolerance,
            "max_position_size": float(self.max_position_size) if self.max_position_size else None,
            "balance": float(self.balance),
            "available_balance": float(self.available_balance),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "settings": self.settings,
            "can_trade": self.can_trade(),
        }


# Utility functions for user and account management

def create_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    phone: Optional[str] = None,
    role: UserRole = UserRole.TRADER,
    bio: Optional[str] = None,
    avatar_url: Optional[str] = None
) -> User:
    """
    Create a new user with hashed password.
    
    Args:
        email: User email address
        password: Plain text password
        first_name: User's first name
        last_name: User's last name
        phone: User's phone number (optional)
        role: User role (default: TRADER)
        bio: User biography (optional)
        avatar_url: User avatar URL (optional)
        
    Returns:
        User: New user instance
    """
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role=role,
        bio=bio,
        avatar_url=avatar_url,
        is_active=True,
        is_verified=False
    )
    user.set_password(password)
    return user


def create_account(
    user_id: int,
    account_name: str,
    account_type: str = "trading",
    default_currency: str = "USD",
    risk_tolerance: str = "medium",
    max_position_size: Optional[float] = None,
    is_primary: bool = False
) -> Account:
    """
    Create a new trading account.
    
    Args:
        user_id: ID of the user who owns the account
        account_name: Name of the account
        account_type: Type of account (default: trading)
        default_currency: Default currency for the account
        risk_tolerance: Risk tolerance level
        max_position_size: Maximum position size allowed
        is_primary: Whether this is the user's primary account
        
    Returns:
        Account: New account instance
    """
    return Account(
        user_id=user_id,
        account_name=account_name,
        account_type=account_type,
        default_currency=default_currency,
        risk_tolerance=risk_tolerance,
        max_position_size=max_position_size,
        is_primary=is_primary,
        status=AccountStatus.ACTIVE,
        balance=0.0,
        available_balance=0.0
    )
