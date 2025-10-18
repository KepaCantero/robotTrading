"""
Tests for User and Account models and services.

This module tests the User and Account SQLAlchemy models, bcrypt password hashing,
and CRUD operations for the AlgoTrading MVP.
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal

# Set DEBUG mode for tests to avoid SECRET_KEY validation
os.environ["DEBUG"] = "true"

from app.models.user import (
    User, Account, UserRole, AccountStatus,
    create_user, create_account
)
from app.services.user_service import (
    UserService, AccountService,
    get_user_service, get_account_service
)


class TestUserModel:
    """Test User model functionality."""

    def setup_method(self):
        """Reset any global state before each test."""
        pass

    def test_user_creation(self):
        """Test basic user creation."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            role=UserRole.TRADER,
            is_active=True,
            is_verified=False
        )
        
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == UserRole.TRADER
        assert user.is_active is True
        assert user.is_verified is False

    def test_user_full_name_property(self):
        """Test full_name property."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe"
        )
        
        assert user.full_name == "John Doe"

    def test_user_role_properties(self):
        """Test role-based properties."""
        admin_user = User(
            email="admin@example.com",
            password_hash="hashed_password",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN
        )
        
        trader_user = User(
            email="trader@example.com",
            password_hash="hashed_password",
            first_name="Trader",
            last_name="User",
            role=UserRole.TRADER
        )
        
        assert admin_user.is_admin is True
        assert admin_user.is_trader is False
        assert trader_user.is_admin is False
        assert trader_user.is_trader is True

    def test_password_hashing(self):
        """Test password hashing and verification."""
        user = User(
            email="test@example.com",
            password_hash="dummy",
            first_name="John",
            last_name="Doe"
        )
        
        password = "test_password_123"
        user.set_password(password)
        
        # Password hash should be different from original
        assert user.password_hash != password
        assert user.password_hash != "dummy"
        
        # Should be able to verify correct password
        assert user.check_password(password) is True
        
        # Should reject incorrect password
        assert user.check_password("wrong_password") is False

    def test_user_to_dict(self):
        """Test user to dictionary conversion."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            role=UserRole.TRADER,
            bio="Test bio",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        data = user.to_dict()
        
        assert data["id"] == 1
        assert data["email"] == "test@example.com"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["full_name"] == "John Doe"
        assert data["phone"] == "+1234567890"
        assert data["role"] == "trader"
        assert data["bio"] == "Test bio"
        assert data["avatar_url"] == "https://example.com/avatar.jpg"
        assert "password_hash" not in data

    def test_user_to_dict_with_sensitive(self):
        """Test user to dictionary with sensitive data."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            role=UserRole.TRADER
        )
        
        data = user.to_dict(include_sensitive=True)
        assert "password_hash" in data
        assert data["password_hash"] == "hashed_password"

    def test_user_repr(self):
        """Test user string representation."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            role=UserRole.TRADER
        )
        
        repr_str = repr(user)
        assert "User(id=1" in repr_str
        assert "email='test@example.com'" in repr_str
        assert "role='trader'" in repr_str


class TestAccountModel:
    """Test Account model functionality."""

    def setup_method(self):
        """Reset any global state before each test."""
        pass

    def test_account_creation(self):
        """Test basic account creation."""
        account = Account(
            user_id=1,
            account_name="Trading Account",
            account_type="trading",
            default_currency="USD",
            risk_tolerance="medium",
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00"),
            status=AccountStatus.ACTIVE,
            is_primary=False
        )
        
        assert account.user_id == 1
        assert account.account_name == "Trading Account"
        assert account.account_type == "trading"
        assert account.default_currency == "USD"
        assert account.risk_tolerance == "medium"
        assert account.balance == Decimal("1000.00")
        assert account.available_balance == Decimal("1000.00")
        assert account.status == AccountStatus.ACTIVE
        assert account.is_primary is False

    def test_account_display_name(self):
        """Test account display name property."""
        account = Account(
            user_id=1,
            account_name="Trading Account",
            default_currency="USD"
        )
        
        assert account.display_name == "Trading Account (USD)"

    def test_account_is_active_property(self):
        """Test account is_active property."""
        active_account = Account(
            user_id=1,
            account_name="Active Account",
            status=AccountStatus.ACTIVE
        )
        
        inactive_account = Account(
            user_id=1,
            account_name="Inactive Account",
            status=AccountStatus.INACTIVE
        )
        
        assert active_account.is_active is True
        assert inactive_account.is_active is False

    def test_account_can_trade(self):
        """Test account can_trade method."""
        # Create mock user
        mock_user = User(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            is_active=True
        )
        
        # Active account with balance
        active_account = Account(
            user_id=1,
            account_name="Active Account",
            status=AccountStatus.ACTIVE,
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00")
        )
        active_account.user = mock_user
        
        # Inactive account
        inactive_account = Account(
            user_id=1,
            account_name="Inactive Account",
            status=AccountStatus.INACTIVE,
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00")
        )
        inactive_account.user = mock_user
        
        # Account with zero balance
        zero_balance_account = Account(
            user_id=1,
            account_name="Zero Balance Account",
            status=AccountStatus.ACTIVE,
            balance=Decimal("0.00"),
            available_balance=Decimal("0.00")
        )
        zero_balance_account.user = mock_user
        
        assert active_account.can_trade() is True
        assert inactive_account.can_trade() is False
        assert zero_balance_account.can_trade() is False

    def test_account_update_balance(self):
        """Test account balance update."""
        account = Account(
            user_id=1,
            account_name="Test Account",
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00")
        )
        
        account.update_balance(Decimal("1500.00"), Decimal("1200.00"))
        
        assert account.balance == Decimal("1500.00")
        assert account.available_balance == Decimal("1200.00")

    def test_account_update_balance_default_available(self):
        """Test account balance update with default available balance."""
        account = Account(
            user_id=1,
            account_name="Test Account",
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00")
        )
        
        account.update_balance(Decimal("1500.00"))
        
        assert account.balance == Decimal("1500.00")
        assert account.available_balance == Decimal("1500.00")

    def test_account_to_dict(self):
        """Test account to dictionary conversion."""
        # Create mock user
        mock_user = User(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            is_active=True
        )
        
        account = Account(
            id=1,
            user_id=1,
            account_name="Trading Account",
            account_type="trading",
            status=AccountStatus.ACTIVE,
            is_primary=True,
            default_currency="USD",
            risk_tolerance="medium",
            max_position_size=Decimal("5000.00"),
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00"),
            settings='{"theme": "dark"}'
        )
        account.user = mock_user
        
        data = account.to_dict()
        
        assert data["id"] == 1
        assert data["user_id"] == 1
        assert data["account_name"] == "Trading Account"
        assert data["account_type"] == "trading"
        assert data["status"] == "active"
        assert data["is_primary"] is True
        assert data["default_currency"] == "USD"
        assert data["risk_tolerance"] == "medium"
        assert data["max_position_size"] == 5000.0
        assert data["balance"] == 1000.0
        assert data["available_balance"] == 1000.0
        assert data["settings"] == '{"theme": "dark"}'
        assert data["can_trade"] is True

    def test_account_repr(self):
        """Test account string representation."""
        account = Account(
            id=1,
            user_id=1,
            account_name="Trading Account",
            status=AccountStatus.ACTIVE
        )
        
        repr_str = repr(account)
        assert "Account(id=1" in repr_str
        assert "user_id=1" in repr_str
        assert "name='Trading Account'" in repr_str
        assert "status='active'" in repr_str


class TestUserService:
    """Test UserService CRUD operations."""

    def setup_method(self):
        """Reset any global state before each test."""
        pass

    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test user creation through service."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe"
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        service = UserService(mock_db)
        
        with patch('app.services.user_service.create_user', return_value=mock_user):
            user = await service.create_user(
                email="test@example.com",
                password="test_password",
                first_name="John",
                last_name="Doe"
            )
            
            assert user == mock_user
            mock_db.add.assert_called_once_with(mock_user)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        """Test get user by ID."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        service = UserService(mock_db)
        user = await service.get_user_by_id(1)
        
        assert user == mock_user
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_email(self):
        """Test get user by email."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        service = UserService(mock_db)
        user = await service.get_user_by_email("test@example.com")
        
        assert user == mock_user
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            is_active=True
        )
        mock_user.check_password = MagicMock(return_value=True)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        service = UserService(mock_db)
        user = await service.authenticate_user("test@example.com", "test_password")
        
        assert user == mock_user
        mock_user.check_password.assert_called_once_with("test_password")

    @pytest.mark.asyncio
    async def test_authenticate_user_failure(self):
        """Test failed user authentication."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            is_active=True
        )
        mock_user.check_password = MagicMock(return_value=False)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        service = UserService(mock_db)
        user = await service.authenticate_user("test@example.com", "wrong_password")
        
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user(self):
        """Test user update."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = UserService(mock_db)
        user = await service.update_user(1, first_name="Jane")
        
        assert user == mock_user
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user(self):
        """Test user deletion."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = UserService(mock_db)
        result = await service.delete_user(1)
        
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """Test user deletion when user not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = UserService(mock_db)
        result = await service.delete_user(999)
        
        assert result is False
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_user(self):
        """Test user verification."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            is_verified=False
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = UserService(mock_db)
        user = await service.verify_user(1)
        
        assert user == mock_user
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_user(self):
        """Test user deactivation."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            is_active=True
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = UserService(mock_db)
        user = await service.deactivate_user(1)
        
        assert user == mock_user
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_users_with_filters(self):
        """Test get users with role and active filters."""
        mock_db = AsyncMock()
        mock_users = [
            User(id=1, email="trader1@example.com", first_name="Trader", last_name="One", role=UserRole.TRADER),
            User(id=2, email="trader2@example.com", first_name="Trader", last_name="Two", role=UserRole.TRADER)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db.execute.return_value = mock_result
        
        service = UserService(mock_db)
        users = await service.get_users(role=UserRole.TRADER, is_active=True)
        
        assert users == mock_users
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_with_password(self):
        """Test user update with password change."""
        mock_db = AsyncMock()
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash="old_hash",
            first_name="John",
            last_name="Doe"
        )
        mock_user.set_password = MagicMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = UserService(mock_db)
        user = await service.update_user(1, password="new_password", first_name="Jane")
        
        assert user == mock_user
        mock_user.set_password.assert_called_once_with("new_password")
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()


class TestAccountService:
    """Test AccountService CRUD operations."""

    def setup_method(self):
        """Reset any global state before each test."""
        pass

    @pytest.mark.asyncio
    async def test_create_account(self):
        """Test account creation through service."""
        mock_db = AsyncMock()
        mock_account = Account(
            id=1,
            user_id=1,
            account_name="Trading Account",
            account_type="trading",
            default_currency="USD"
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        service = AccountService(mock_db)
        
        with patch('app.services.user_service.create_account', return_value=mock_account):
            account = await service.create_account(
                user_id=1,
                account_name="Trading Account",
                account_type="trading",
                default_currency="USD"
            )
            
            assert account == mock_account
            mock_db.add.assert_called_once_with(mock_account)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_account)

    @pytest.mark.asyncio
    async def test_get_account_by_id(self):
        """Test get account by ID."""
        mock_db = AsyncMock()
        mock_account = Account(
            id=1,
            user_id=1,
            account_name="Trading Account",
            account_type="trading"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result
        
        service = AccountService(mock_db)
        account = await service.get_account_by_id(1)
        
        assert account == mock_account
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_accounts(self):
        """Test get user accounts."""
        mock_db = AsyncMock()
        mock_accounts = [
            Account(id=1, user_id=1, account_name="Account 1"),
            Account(id=2, user_id=1, account_name="Account 2")
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_accounts
        mock_db.execute.return_value = mock_result
        
        service = AccountService(mock_db)
        accounts = await service.get_user_accounts(1)
        
        assert accounts == mock_accounts
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_account_balance(self):
        """Test account balance update."""
        mock_db = AsyncMock()
        mock_account = Account(
            id=1,
            user_id=1,
            account_name="Trading Account",
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00")
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        account = await service.update_account_balance(1, 1500.0, 1200.0)
        
        assert account == mock_account
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_primary_account(self):
        """Test set primary account."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        result = await service.set_primary_account(1, 1)
        
        assert result is True
        assert mock_db.execute.call_count == 2  # Two update queries
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_primary_account_not_found(self):
        """Test set primary account when account not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        result = await service.set_primary_account(1, 999)
        
        assert result is False
        assert mock_db.execute.call_count == 2  # Two update queries
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_primary_account(self):
        """Test get primary account."""
        mock_db = AsyncMock()
        mock_account = Account(
            id=1,
            user_id=1,
            account_name="Primary Account",
            is_primary=True
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result
        
        service = AccountService(mock_db)
        account = await service.get_primary_account(1)
        
        assert account == mock_account
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_suspend_account(self):
        """Test account suspension."""
        mock_db = AsyncMock()
        mock_account = Account(
            id=1,
            user_id=1,
            account_name="Test Account",
            status=AccountStatus.ACTIVE
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        account = await service.suspend_account(1)
        
        assert account == mock_account
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_account(self):
        """Test account activation."""
        mock_db = AsyncMock()
        mock_account = Account(
            id=1,
            user_id=1,
            account_name="Test Account",
            status=AccountStatus.SUSPENDED
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        account = await service.activate_account(1)
        
        assert account == mock_account
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_account(self):
        """Test account deletion."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        result = await service.delete_account(1)
        
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_account_not_found(self):
        """Test account deletion when account not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        result = await service.delete_account(999)
        
        assert result is False
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_accounts_with_filters(self):
        """Test get user accounts with status and primary filters."""
        mock_db = AsyncMock()
        mock_accounts = [
            Account(id=1, user_id=1, account_name="Account 1", status=AccountStatus.ACTIVE),
            Account(id=2, user_id=1, account_name="Account 2", status=AccountStatus.ACTIVE)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_accounts
        mock_db.execute.return_value = mock_result
        
        service = AccountService(mock_db)
        accounts = await service.get_user_accounts(1, status=AccountStatus.ACTIVE, is_primary=False)
        
        assert accounts == mock_accounts
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_account_balance_default_available(self):
        """Test account balance update with default available balance."""
        mock_db = AsyncMock()
        mock_account = Account(
            id=1,
            user_id=1,
            account_name="Trading Account",
            balance=Decimal("1000.00"),
            available_balance=Decimal("1000.00")
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        service = AccountService(mock_db)
        account = await service.update_account_balance(1, 1500.0)  # No available_balance provided
        
        assert account == mock_account
        mock_db.execute.assert_called()
        mock_db.commit.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_user_function(self):
        """Test create_user utility function."""
        user = create_user(
            email="test@example.com",
            password="test_password",
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            role=UserRole.TRADER,
            bio="Test bio"
        )
        
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.phone == "+1234567890"
        assert user.role == UserRole.TRADER
        assert user.bio == "Test bio"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.check_password("test_password") is True

    def test_create_account_function(self):
        """Test create_account utility function."""
        account = create_account(
            user_id=1,
            account_name="Trading Account",
            account_type="trading",
            default_currency="USD",
            risk_tolerance="medium",
            max_position_size=5000.0,
            is_primary=True
        )
        
        assert account.user_id == 1
        assert account.account_name == "Trading Account"
        assert account.account_type == "trading"
        assert account.default_currency == "USD"
        assert account.risk_tolerance == "medium"
        assert account.max_position_size == Decimal("5000.0")
        assert account.is_primary is True
        assert account.status == AccountStatus.ACTIVE
        assert account.balance == Decimal("0.0")
        assert account.available_balance == Decimal("0.0")

    def test_get_user_service(self):
        """Test get_user_service function."""
        mock_db = AsyncMock()
        service = get_user_service(mock_db)
        
        assert isinstance(service, UserService)
        assert service.db == mock_db

    def test_get_account_service(self):
        """Test get_account_service function."""
        mock_db = AsyncMock()
        service = get_account_service(mock_db)
        
        assert isinstance(service, AccountService)
        assert service.db == mock_db


class TestEnums:
    """Test enum classes."""

    def test_user_role_enum(self):
        """Test UserRole enum values."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.TRADER == "trader"
        assert UserRole.VIEWER == "viewer"

    def test_account_status_enum(self):
        """Test AccountStatus enum values."""
        assert AccountStatus.ACTIVE == "active"
        assert AccountStatus.INACTIVE == "inactive"
        assert AccountStatus.SUSPENDED == "suspended"
        assert AccountStatus.PENDING == "pending"


# Integration tests
class TestModelIntegration:
    """Integration tests for models and services."""

    def setup_method(self):
        """Reset any global state before each test."""
        pass

    def test_user_account_relationship(self):
        """Test user-account relationship."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe"
        )
        
        account1 = Account(
            id=1,
            user_id=1,
            account_name="Account 1"
        )
        
        account2 = Account(
            id=2,
            user_id=1,
            account_name="Account 2"
        )
        
        # Test relationship
        user.accounts = [account1, account2]
        account1.user = user
        account2.user = user
        
        assert len(user.accounts) == 2
        assert account1.user == user
        assert account2.user == user
        assert account1 in user.accounts
        assert account2 in user.accounts

    def test_password_security(self):
        """Test password security features."""
        user1 = User(
            email="user1@example.com",
            password_hash="dummy",
            first_name="User",
            last_name="One"
        )
        
        user2 = User(
            email="user2@example.com",
            password_hash="dummy",
            first_name="User",
            last_name="Two"
        )
        
        password = "same_password"
        user1.set_password(password)
        user2.set_password(password)
        
        # Same password should produce different hashes
        assert user1.password_hash != user2.password_hash
        assert user1.password_hash != password
        assert user2.password_hash != password
        
        # Both should verify correctly
        assert user1.check_password(password) is True
        assert user2.check_password(password) is True
        
        # Both should reject wrong passwords
        assert user1.check_password("wrong") is False
        assert user2.check_password("wrong") is False
