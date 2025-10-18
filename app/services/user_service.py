"""
User and Account CRUD service for AlgoTrading MVP.

This module provides CRUD operations for User and Account models
with database session management and error handling.
"""

from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.models.user import (
    User,
    Account,
    UserRole,
    AccountStatus,
    create_user,
    create_account,
)


class UserService:
    """Service class for User CRUD operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.TRADER,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """
        Create a new user.

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
            User: Created user instance

        Raises:
            IntegrityError: If email already exists
        """
        user = create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            bio=bio,
            avatar_url=avatar_url,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User: User instance or None if not found
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User: User instance or None if not found
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """
        Get list of users with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role: Filter by user role
            is_active: Filter by active status

        Returns:
            List[User]: List of user instances
        """
        query = select(User)

        if role is not None:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_user(self, user_id: int, **updates: Any) -> Optional[User]:
        """
        Update user fields.

        Args:
            user_id: User ID
            **updates: Fields to update

        Returns:
            User: Updated user instance or None if not found
        """
        # Remove password from updates if present (use set_password method)
        if "password" in updates:
            password = updates.pop("password")
            user = await self.get_user_by_id(user_id)
            if user:
                user.set_password(password)

        if updates:
            await self.db.execute(
                update(User).where(User.id == user_id).values(**updates)
            )
            await self.db.commit()

        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user by ID.

        Args:
            user_id: User ID

        Returns:
            bool: True if deleted, False if not found
        """
        result = await self.db.execute(delete(User).where(User.id == user_id))
        await self.db.commit()
        return result.rowcount > 0

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User: User instance if authentication successful, None otherwise
        """
        user = await self.get_user_by_email(email)
        if user and user.check_password(password) and user.is_active:
            return user
        return None

    async def verify_user(self, user_id: int) -> Optional[User]:
        """
        Mark user as verified.

        Args:
            user_id: User ID

        Returns:
            User: Updated user instance or None if not found
        """
        return await self.update_user(user_id, is_verified=True)

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """
        Deactivate user account.

        Args:
            user_id: User ID

        Returns:
            User: Updated user instance or None if not found
        """
        return await self.update_user(user_id, is_active=False)


class AccountService:
    """Service class for Account CRUD operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_account(
        self,
        user_id: int,
        account_name: str,
        account_type: str = "trading",
        default_currency: str = "USD",
        risk_tolerance: str = "medium",
        max_position_size: Optional[float] = None,
        is_primary: bool = False,
    ) -> Account:
        """
        Create a new account.

        Args:
            user_id: ID of the user who owns the account
            account_name: Name of the account
            account_type: Type of account (default: trading)
            default_currency: Default currency for the account
            risk_tolerance: Risk tolerance level
            max_position_size: Maximum position size allowed
            is_primary: Whether this is the user's primary account

        Returns:
            Account: Created account instance

        Raises:
            IntegrityError: If user_id doesn't exist
        """
        account = create_account(
            user_id=user_id,
            account_name=account_name,
            account_type=account_type,
            default_currency=default_currency,
            risk_tolerance=risk_tolerance,
            max_position_size=max_position_size,
            is_primary=is_primary,
        )

        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """
        Get account by ID.

        Args:
            account_id: Account ID

        Returns:
            Account: Account instance or None if not found
        """
        result = await self.db.execute(select(Account).where(Account.id == account_id))
        return result.scalar_one_or_none()

    async def get_user_accounts(
        self,
        user_id: int,
        status: Optional[AccountStatus] = None,
        is_primary: Optional[bool] = None,
    ) -> List[Account]:
        """
        Get all accounts for a user.

        Args:
            user_id: User ID
            status: Filter by account status
            is_primary: Filter by primary account status

        Returns:
            List[Account]: List of account instances
        """
        query = select(Account).where(Account.user_id == user_id)

        if status is not None:
            query = query.where(Account.status == status)
        if is_primary is not None:
            query = query.where(Account.is_primary == is_primary)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_primary_account(self, user_id: int) -> Optional[Account]:
        """
        Get user's primary account.

        Args:
            user_id: User ID

        Returns:
            Account: Primary account instance or None if not found
        """
        result = await self.db.execute(
            select(Account)
            .where(Account.user_id == user_id)
            .where(Account.is_primary is True)
        )
        return result.scalar_one_or_none()

    async def update_account(
        self, account_id: int, **updates: Any
    ) -> Optional[Account]:
        """
        Update account fields.

        Args:
            account_id: Account ID
            **updates: Fields to update

        Returns:
            Account: Updated account instance or None if not found
        """
        await self.db.execute(
            update(Account).where(Account.id == account_id).values(**updates)
        )
        await self.db.commit()

        return await self.get_account_by_id(account_id)

    async def update_account_balance(
        self, account_id: int, balance: float, available_balance: Optional[float] = None
    ) -> Optional[Account]:
        """
        Update account balance.

        Args:
            account_id: Account ID
            balance: New total balance
            available_balance: New available balance (defaults to balance)

        Returns:
            Account: Updated account instance or None if not found
        """
        updates = {"balance": balance}
        if available_balance is not None:
            updates["available_balance"] = available_balance
        else:
            updates["available_balance"] = balance

        return await self.update_account(account_id, **updates)

    async def set_primary_account(self, user_id: int, account_id: int) -> bool:
        """
        Set an account as the user's primary account.

        Args:
            user_id: User ID
            account_id: Account ID to set as primary

        Returns:
            bool: True if successful, False otherwise
        """
        # First, unset all primary accounts for the user
        await self.db.execute(
            update(Account).where(Account.user_id == user_id).values(is_primary=False)
        )

        # Then set the specified account as primary
        result = await self.db.execute(
            update(Account)
            .where(Account.id == account_id)
            .where(Account.user_id == user_id)
            .values(is_primary=True)
        )

        await self.db.commit()
        return result.rowcount > 0

    async def delete_account(self, account_id: int) -> bool:
        """
        Delete account by ID.

        Args:
            account_id: Account ID

        Returns:
            bool: True if deleted, False if not found
        """
        result = await self.db.execute(delete(Account).where(Account.id == account_id))
        await self.db.commit()
        return result.rowcount > 0

    async def suspend_account(self, account_id: int) -> Optional[Account]:
        """
        Suspend account.

        Args:
            account_id: Account ID

        Returns:
            Account: Updated account instance or None if not found
        """
        return await self.update_account(account_id, status=AccountStatus.SUSPENDED)

    async def activate_account(self, account_id: int) -> Optional[Account]:
        """
        Activate account.

        Args:
            account_id: Account ID

        Returns:
            Account: Updated account instance or None if not found
        """
        return await self.update_account(account_id, status=AccountStatus.ACTIVE)


# Utility functions for service instantiation


def get_user_service(db_session: AsyncSession) -> UserService:
    """
    Get UserService instance.

    Args:
        db_session: Database session

    Returns:
        UserService: Service instance
    """
    return UserService(db_session)


def get_account_service(db_session: AsyncSession) -> AccountService:
    """
    Get AccountService instance.

    Args:
        db_session: Database session

    Returns:
        AccountService: Service instance
    """
    return AccountService(db_session)
