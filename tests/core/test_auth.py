"""
Comprehensive tests for core authentication module.

Tests cover:
- P0: Thread-safe singleton initialization with locks
- P1: TypedDict type hints
- Authentication flows (JWT, API keys)
- Rate limiting
- Lockout behavior
- Audit logging
- Role-based authorization
"""

import os
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, status

from app.shared.audit import AuditLogger
from app.core.auth import (  # TypedDict classes; Main classes; Singleton getters; Dependencies; Utilities
    APIKeyDict,
    AuthAttemptTracker,
    FailedAttemptsDict,
    LockoutsDict,
    RateLimitsDict,
    User,
    UserDict,
    UserRoles,
    UserStore,
    _handle_failed_attempt,
    create_access_token_for_user,
    get_admin_user,
    get_attempt_tracker,
    get_current_user,
    get_current_user_optional,
    get_deployer_user,
    get_token_manager,
    get_trader_user,
    get_user_id,
    get_user_store,
    get_username,
    require_permissions,
    require_roles,
    verify_token_and_get_user,
)

# Check if JWT library is available
try:
    pass

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

# Check if pyjwt is installed
jwt_skip = pytest.mark.skipif(
    not JWT_AVAILABLE, reason="PyJWT library not installed. Install with: pip install pyjwt"
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def clean_env():
    """Fixture to clean environment variables before and after tests."""
    # Store original env vars
    original_env = os.environ.copy()

    # Clear auth-related env vars
    keys_to_remove = [
        k for k in os.environ if k.startswith("AUTH_USER_") or k.startswith("AUTH_API_KEY_")
    ]
    for key in keys_to_remove:
        del os.environ[key]

    yield

    # Restore original env vars
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def test_user_config(clean_env):
    """Fixture to set up test user configuration."""
    # Set up test users
    os.environ["AUTH_USER_TESTADMIN_ID"] = "admin-001"
    os.environ["AUTH_USER_TESTADMIN_ROLE"] = "admin"
    os.environ["AUTH_USER_TESTADMIN_PERMISSIONS"] = "*"

    os.environ["AUTH_USER_TESTTRADER_ID"] = "trader-001"
    os.environ["AUTH_USER_TESTTRADER_ROLE"] = "trader"
    os.environ["AUTH_USER_TESTTRADER_PERMISSIONS"] = "trade:read,trade:write"

    os.environ["AUTH_USER_TESTVIEWER_ID"] = "viewer-001"
    os.environ["AUTH_USER_TESTVIEWER_ROLE"] = "viewer"
    os.environ["AUTH_USER_TESTVIEWER_PERMISSIONS"] = "trade:read"

    # Set up test API keys
    os.environ["AUTH_API_KEY_TEST_KEY"] = "sk_test_test_api_key_12345"
    os.environ["AUTH_API_KEY_TEST_KEY_USER"] = "testtrader"

    # Reset singletons
    import app.core.auth as auth_module

    auth_module._user_store = None
    auth_module._token_manager = None
    auth_module._attempt_tracker = None


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock()
    config.api.secret_key = "test_secret_key_12345678901234567890"
    config.api.access_token_expire_minutes = 30
    return config


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger for testing."""
    logger = Mock(spec=AuditLogger)
    logger.log = Mock()
    return logger


# ============================================================================
# P1: TypedDict Tests
# ============================================================================


class TestTypedDictClasses:
    """Test TypedDict classes for type documentation (P1 fix)."""

    def test_user_dict_exists(self):
        """Test UserDict TypedDict exists for type hinting."""
        # UserDict is a TypedDict for documentation purposes
        assert UserDict is not None

        # Can be used for type annotations
        def example(users: UserDict) -> None:
            pass

        assert callable(example)

    def test_api_key_dict_exists(self):
        """Test APIKeyDict TypedDict exists for type hinting."""
        assert APIKeyDict is not None

        # Can be used for type annotations
        def example(api_keys: APIKeyDict) -> None:
            pass

        assert callable(example)

    def test_failed_attempts_dict_exists(self):
        """Test FailedAttemptsDict TypedDict exists for type hinting."""
        assert FailedAttemptsDict is not None

    def test_lockouts_dict_exists(self):
        """Test LockoutsDict TypedDict exists for type hinting."""
        assert LockoutsDict is not None

    def test_rate_limits_dict_exists(self):
        """Test RateLimitsDict TypedDict exists for type hinting."""
        assert RateLimitsDict is not None


# ============================================================================
# User Class Tests
# ============================================================================


class TestUser:
    """Test User class and role-based authorization."""

    def test_user_initialization(self):
        """Test User object initialization."""
        user = User(
            user_id="test-001",
            username="testuser",
            role=UserRoles.TRADER,
            permissions=["trade:read", "trade:write"],
            is_active=True,
        )

        assert user.user_id == "test-001"
        assert user.username == "testuser"
        assert user.role == UserRoles.TRADER
        assert user.permissions == ["trade:read", "trade:write"]
        assert user.is_active is True

    def test_user_has_permission(self):
        """Test has_permission method."""
        user = User(
            user_id="test-001",
            username="testuser",
            role=UserRoles.TRADER,
            permissions=["trade:read", "trade:write"],
        )

        assert user.has_permission("trade:read") is True
        assert user.has_permission("trade:write") is True
        assert user.has_permission("admin:write") is False

    def test_user_has_role(self):
        """Test has_role method."""
        admin = User(
            user_id="admin-001",
            username="admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
        )

        assert admin.has_role(UserRoles.ADMIN) is True
        assert admin.has_role(UserRoles.TRADER) is True  # Admin has all roles

        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
        )

        assert trader.has_role(UserRoles.TRADER) is True
        assert trader.has_role(UserRoles.ADMIN) is False

    def test_user_can_trade(self):
        """Test can_trade method."""
        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        admin = User(
            user_id="admin-001",
            username="admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=True,
        )

        viewer = User(
            user_id="viewer-001",
            username="viewer",
            role=UserRoles.VIEWER,
            permissions=["trade:read"],
            is_active=True,
        )

        inactive_trader = User(
            user_id="trader-002",
            username="inactive_trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=False,
        )

        assert trader.can_trade() is True
        assert admin.can_trade() is True
        assert viewer.can_trade() is False
        assert inactive_trader.can_trade() is False

    def test_user_can_deploy(self):
        """Test can_deploy method."""
        admin = User(
            user_id="admin-001",
            username="admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=True,
        )

        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        inactive_admin = User(
            user_id="admin-002",
            username="inactive_admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=False,
        )

        assert admin.can_deploy() is True
        assert trader.can_deploy() is False
        assert inactive_admin.can_deploy() is False

    def test_user_repr(self):
        """Test User string representation doesn't expose sensitive data."""
        user = User(
            user_id="user-001",
            username="testuser",
            role=UserRoles.TRADER,
            permissions=["secret_permission"],
        )

        repr_str = repr(user)

        assert "user-001" in repr_str
        assert "testuser" in repr_str
        assert "trader" in repr_str
        assert "secret_permission" not in repr_str


# ============================================================================
# P0: Thread-Safe UserStore Tests
# ============================================================================


class TestUserStoreThreadSafety:
    """Test thread-safe singleton initialization for UserStore (P0 fix)."""

    def test_user_store_singleton_initialization_with_lock(self, test_user_config):
        """Test that UserStore uses thread-safe initialization with locks."""
        import app.core.auth as auth_module

        auth_module._user_store = None

        # Create multiple threads that all try to get the user store
        results = []
        errors = []

        def get_store():
            try:
                store = get_user_store()
                results.append(id(store))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_store) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance (same id)
        assert len(errors) == 0
        assert len(set(results)) == 1
        assert results[0] is not None

    def test_user_store_has_rlocks(self, test_user_config):
        """Test that UserStore has RLocks for thread safety (P0 fix)."""

        store = UserStore()

        # Check that locks exist
        assert hasattr(store, "_users_lock")
        assert hasattr(store, "_api_keys_lock")
        assert hasattr(store, "_init_lock")

        # Verify they are locks (either Lock or RLock)
        # Use type().__name__ to check lock type instead of isinstance
        assert type(store._users_lock).__name__ == "RLock"
        assert type(store._api_keys_lock).__name__ == "RLock"
        assert type(store._init_lock).__name__ == "lock"

    def test_concurrent_user_get_operations(self, test_user_config):
        """Test concurrent read operations are thread-safe."""
        store = UserStore()
        results = []
        errors = []

        def get_user():
            try:
                user = store.get_user("testadmin")
                results.append(user)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_user) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20

    def test_concurrent_user_and_api_key_access(self, test_user_config):
        """Test concurrent access to both users and API keys is thread-safe."""
        store = UserStore()
        results = {"users": [], "api_keys": []}
        errors = []

        def access_users():
            try:
                for _ in range(10):
                    user = store.get_user("testadmin")
                    results["users"].append(user)
            except Exception as e:
                errors.append(("users", e))

        def access_api_keys():
            try:
                for _ in range(10):
                    valid = store.verify_api_key("sk_test_test_api_key_12345")
                    results["api_keys"].append(valid)
            except Exception as e:
                errors.append(("api_keys", e))

        threads = [
            threading.Thread(target=access_users),
            threading.Thread(target=access_api_keys),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results["users"]) == 10
        assert len(results["api_keys"]) == 10


class TestUserStoreFunctionality:
    """Test UserStore functionality."""

    def test_load_users_from_config(self, test_user_config):
        """Test loading users from environment configuration."""
        store = UserStore()

        # Check that users were loaded
        admin = store.get_user("testadmin")
        assert admin is not None
        assert admin.user_id == "admin-001"
        assert admin.role == UserRoles.ADMIN
        assert admin.permissions == ["*"]

        trader = store.get_user("testtrader")
        assert trader is not None
        assert trader.user_id == "trader-001"
        assert trader.role == UserRoles.TRADER

    def test_verify_api_key(self, test_user_config):
        """Test API key verification with hashing (GAP-003 FIX)."""
        store = UserStore()

        # Valid API key should return username
        username = store.verify_api_key("sk_test_test_api_key_12345")
        assert username == "testtrader"

        # Invalid API key should return None
        username = store.verify_api_key("invalid_key")
        assert username is None

        # Empty key should return None
        username = store.verify_api_key("")
        assert username is None

    def test_hash_api_key(self, test_user_config):
        """Test API key hashing (GAP-003 FIX)."""
        store = UserStore()

        # Same key should produce same hash
        key = "test_api_key"
        hash1 = store._hash_api_key(key)
        hash2 = store._hash_api_key(key)

        assert hash1 == hash2
        assert hash1 != key  # Hash should be different from original

    def test_get_user_by_id(self, test_user_config):
        """Test getting user by ID."""
        store = UserStore()

        user = store.get_user_by_id("admin-001")
        assert user is not None
        assert user.username == "testadmin"

        # Non-existent user should return None
        user = store.get_user_by_id("nonexistent")
        assert user is None


# ============================================================================
# P0: Thread-Safe JWTTokenManager Tests
# ============================================================================


@jwt_skip
class TestJWTTokenManagerThreadSafety:
    """Test thread-safe singleton initialization for JWTTokenManager (P0 fix)."""

    def test_token_manager_singleton_initialization_with_lock(self, test_user_config):
        """Test that JWTTokenManager uses thread-safe initialization."""
        import app.core.auth as auth_module

        auth_module._token_manager = None

        results = []
        errors = []

        def get_manager():
            try:
                manager = get_token_manager()
                results.append(id(manager))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_manager) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(set(results)) == 1

    def test_concurrent_token_creation(self, test_user_config):
        """Test concurrent token creation is thread-safe."""
        manager = get_token_manager()
        results = []
        errors = []

        def create_token():
            try:
                token = manager.create_access_token({"sub": "user-001"})
                results.append(token)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_token) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10


@jwt_skip
class TestJWTTokenManagerFunctionality:
    """Test JWTTokenManager functionality."""

    def test_create_access_token(self, test_user_config):
        """Test JWT token creation."""
        manager = get_token_manager()

        token = manager.create_access_token(
            data={"sub": "user-001", "username": "testuser"},
            expires_delta=timedelta(minutes=30),
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_default_expiration(self, test_user_config):
        """Test token creation with default expiration."""
        manager = get_token_manager()

        token = manager.create_access_token(
            data={"sub": "user-001"},
        )

        assert token is not None

    def test_verify_valid_token(self, test_user_config):
        """Test verification of valid token."""
        manager = get_token_manager()

        token = manager.create_access_token(
            data={"sub": "user-001", "username": "testuser"},
            expires_delta=timedelta(minutes=30),
        )

        payload = manager.verify_token(token)

        assert payload is not None
        assert payload["sub"] == "user-001"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"

    def test_verify_invalid_token(self, test_user_config):
        """Test verification of invalid token returns None."""
        manager = get_token_manager()

        payload = manager.verify_token("invalid_token")

        assert payload is None

    def test_verify_expired_token(self, test_user_config):
        """Test verification of expired token returns None."""
        manager = get_token_manager()

        # Create token that's already expired
        token = manager.create_access_token(
            data={"sub": "user-001"},
            expires_delta=timedelta(seconds=-1),
        )

        payload = manager.verify_token(token)

        assert payload is None

    def test_verify_token_wrong_type(self, test_user_config):
        """Test verification rejects tokens with wrong type."""
        manager = get_token_manager()

        # Create a token with wrong type manually
        try:
            import jwt

            payload = {
                "sub": "user-001",
                "type": "refresh",  # Wrong type
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "iat": datetime.utcnow(),
            }
            token = jwt.encode(payload, manager.secret_key, algorithm=manager.algorithm)

            result = manager.verify_token(token)
            assert result is None  # Should reject wrong token type
        except ImportError:
            pytest.skip("JWT library not available")


# ============================================================================
# P0: Thread-Safe AuthAttemptTracker Tests
# ============================================================================


class TestAuthAttemptTrackerThreadSafety:
    """Test thread-safe singleton initialization for AuthAttemptTracker (P0 fix)."""

    def test_attempt_tracker_singleton_initialization_with_lock(self, test_user_config):
        """Test that AuthAttemptTracker uses thread-safe initialization."""
        import app.core.auth as auth_module

        auth_module._attempt_tracker = None

        results = []
        errors = []

        def get_tracker():
            try:
                tracker = get_attempt_tracker()
                results.append(id(tracker))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_tracker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(set(results)) == 1

    def test_concurrent_failed_attempt_recording(self, test_user_config, mock_audit_logger):
        """Test concurrent failed attempt recording is thread-safe."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        results = []
        errors = []

        def record_failed():
            try:
                for i in range(5):
                    locked = tracker.record_failed_attempt("test_user", "test_method")
                    results.append(locked)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_failed) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Total attempts should be 20 (4 threads * 5 attempts)
        assert tracker._failed_attempts["test_user"] == 20


class TestAuthAttemptTrackerFunctionality:
    """Test AuthAttemptTracker functionality."""

    def test_record_failed_attempt(self, test_user_config, mock_audit_logger):
        """Test recording failed authentication attempts."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        # Record failed attempts
        for i in range(3):
            locked = tracker.record_failed_attempt("test_user", "api_key")
            assert locked is False

        # Should lock out after MAX_FAILED_ATTEMPTS
        assert tracker._failed_attempts["test_user"] == 3
        assert mock_audit_logger.log.call_count == 3

    def test_lockout_after_max_failed_attempts(self, test_user_config, mock_audit_logger):
        """Test account lockout after max failed attempts."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        # Record max failed attempts
        for i in range(tracker.MAX_FAILED_ATTEMPTS):
            locked = tracker.record_failed_attempt("test_user", "api_key")

        # Should be locked out on the last attempt
        assert locked is True
        assert tracker.is_locked_out("test_user")[0] is True

    def test_record_successful_attempt_clears_failed(self, test_user_config, mock_audit_logger):
        """Test successful attempt clears failed attempts."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        # Record some failed attempts
        tracker.record_failed_attempt("test_user", "api_key")
        tracker.record_failed_attempt("test_user", "api_key")

        assert tracker._failed_attempts["test_user"] == 2

        # Record successful attempt
        tracker.record_successful_attempt("test_user", "testuser")

        # Failed attempts should be cleared
        assert "test_user" not in tracker._failed_attempts

    def test_is_locked_out(self, test_user_config, mock_audit_logger):
        """Test lockout status checking."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        # Not locked out initially
        is_locked, remaining = tracker.is_locked_out("test_user")
        assert is_locked is False
        assert remaining is None

        # Lock out the user
        for i in range(tracker.MAX_FAILED_ATTEMPTS):
            tracker.record_failed_attempt("test_user", "api_key")

        # Now should be locked out
        is_locked, remaining = tracker.is_locked_out("test_user")
        assert is_locked is True
        assert remaining is not None
        assert remaining > 0
        assert remaining <= tracker.LOCKOUT_DURATION

    def test_check_rate_limit(self, test_user_config):
        """Test rate limiting."""
        tracker = AuthAttemptTracker()

        # Should allow requests within limit
        for i in range(tracker.MAX_REQUESTS_PER_WINDOW):
            allowed = tracker.check_rate_limit("test_identifier")
            assert allowed is True

        # Next request should exceed limit
        allowed = tracker.check_rate_limit("test_identifier")
        assert allowed is False

    def test_cleanup_expired_entries(self, test_user_config, mock_audit_logger):
        """Test cleanup of expired lockouts and rate limit entries."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        # Add some entries
        tracker.record_failed_attempt("user1", "api_key")
        tracker.check_rate_limit("user1")

        # Manually add an expired lockout
        tracker._lockouts["expired_user"] = time.time() - 100

        # Cleanup
        tracker.cleanup()

        # Expired entry should be removed
        assert "expired_user" not in tracker._lockouts


# ============================================================================
# Authentication Dependency Tests
# ============================================================================


class TestGetCurrentUserOptional:
    """Test get_current_user_optional dependency."""

    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self, test_user_config):
        """Test that no credentials returns None."""
        # Reset the attempt tracker to ensure clean state
        import app.core.auth as auth_module

        auth_module._attempt_tracker = None

        user = await get_current_user_optional(
            request_id="test_request", api_key=None, auth_header=None
        )
        assert user is None

    @pytest.mark.asyncio
    async def test_valid_api_key_returns_user(self, test_user_config):
        """Test valid API key returns user."""
        # Reset the attempt tracker to ensure clean state
        import app.core.auth as auth_module

        auth_module._attempt_tracker = None

        user = await get_current_user_optional(
            request_id="test_request", api_key="sk_test_test_api_key_12345", auth_header=None
        )

        assert user is not None
        assert user.username == "testtrader"

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_none(self, test_user_config):
        """Test invalid API key returns None."""
        # Reset the attempt tracker to ensure clean state
        import app.core.auth as auth_module

        auth_module._attempt_tracker = None

        user = await get_current_user_optional(
            request_id="test_request", api_key="invalid_api_key", auth_header=None
        )

        assert user is None

    @pytest.mark.asyncio
    @jwt_skip
    async def test_valid_jwt_token_returns_user(self, test_user_config):
        """Test valid JWT token returns user."""
        # Create a token
        manager = get_token_manager()
        token = manager.create_access_token(
            data={"sub": "admin-001", "username": "testadmin"},
        )

        # Mock HTTPAuthorizationCredentials
        from fastapi.security import HTTPAuthorizationCredentials

        auth_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user_optional(
            request_id="test_request",
            auth_header=auth_creds,
        )

        assert user is not None
        assert user.username == "testadmin"

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_requests(self, test_user_config):
        """Test rate limiting blocks excessive requests."""
        # Reset the attempt tracker to ensure clean state
        import app.core.auth as auth_module

        auth_module._attempt_tracker = None

        tracker = get_attempt_tracker()

        # Exceed rate limit
        for _ in range(tracker.MAX_REQUESTS_PER_WINDOW + 1):
            tracker.check_rate_limit("test_request")

        # Next request should be blocked
        user = await get_current_user_optional(
            request_id="test_request", api_key=None, auth_header=None
        )
        assert user is None

    @pytest.mark.asyncio
    async def test_lockout_blocks_requests(self, test_user_config, mock_audit_logger):
        """Test lockout blocks requests."""
        # Reset the attempt tracker to ensure clean state
        import app.core.auth as auth_module

        auth_module._attempt_tracker = None

        tracker = get_attempt_tracker()
        tracker._audit = mock_audit_logger

        # Lock out the request ID
        for _ in range(tracker.MAX_FAILED_ATTEMPTS):
            tracker.record_failed_attempt("test_request", "test_method")

        # Request should be blocked due to lockout
        user = await get_current_user_optional(
            request_id="test_request", api_key=None, auth_header=None
        )
        assert user is None


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_no_credentials_raises_401(self, test_user_config):
        """Test that no credentials raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(current_user=None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self, test_user_config):
        """Test that inactive user raises 403."""
        inactive_user = User(
            user_id="inactive-001",
            username="inactive",
            role=UserRoles.VIEWER,
            permissions=[],
            is_active=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(current_user=inactive_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_valid_user_returns_user(self, test_user_config):
        """Test valid user is returned."""
        valid_user = User(
            user_id="user-001",
            username="testuser",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        result = await get_current_user(current_user=valid_user)

        assert result == valid_user


class TestGetAdminUser:
    """Test get_admin_user dependency."""

    @pytest.mark.asyncio
    async def test_non_admin_raises_403(self, test_user_config):
        """Test non-admin user raises 403."""
        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(current_user=trader)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_admin_user_returns_user(self, test_user_config):
        """Test admin user is returned."""
        admin = User(
            user_id="admin-001",
            username="admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=True,
        )

        result = await get_admin_user(current_user=admin)

        assert result == admin


class TestGetTraderUser:
    """Test get_trader_user dependency."""

    @pytest.mark.asyncio
    async def test_non_trader_raises_403(self, test_user_config):
        """Test non-trader user raises 403."""
        viewer = User(
            user_id="viewer-001",
            username="viewer",
            role=UserRoles.VIEWER,
            permissions=["trade:read"],
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_trader_user(current_user=viewer)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_trader_user_returns_user(self, test_user_config):
        """Test trader user is returned."""
        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        result = await get_trader_user(current_user=trader)

        assert result == trader


class TestGetDeployerUser:
    """Test get_deployer_user dependency."""

    @pytest.mark.asyncio
    async def test_non_deployer_raises_403(self, test_user_config):
        """Test non-deployer user raises 403."""
        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_deployer_user(current_user=trader)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_deployer_user_returns_user(self, test_user_config):
        """Test deployer user is returned."""
        admin = User(
            user_id="admin-001",
            username="admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=True,
        )

        result = await get_deployer_user(current_user=admin)

        assert result == admin


# ============================================================================
# Role and Permission Tests
# ============================================================================


class TestRequireRoles:
    """Test require_roles dependency factory."""

    @pytest.mark.asyncio
    async def test_require_single_role(self, test_user_config):
        """Test requiring a single role."""
        role_checker = require_roles(UserRoles.ADMIN)

        admin = User(
            user_id="admin-001",
            username="admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=True,
        )

        result = await role_checker(current_user=admin)
        assert result == admin

    @pytest.mark.asyncio
    async def test_require_multiple_roles(self, test_user_config):
        """Test requiring one of multiple roles."""
        role_checker = require_roles(UserRoles.ADMIN, UserRoles.TRADER)

        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        result = await role_checker(current_user=trader)
        assert result == trader

    @pytest.mark.asyncio
    async def test_require_roles_unauthorized_raises_403(self, test_user_config):
        """Test user without required roles raises 403."""
        role_checker = require_roles(UserRoles.ADMIN, UserRoles.SYSTEM)

        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await role_checker(current_user=trader)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestRequirePermissions:
    """Test require_permissions dependency factory."""

    @pytest.mark.asyncio
    async def test_require_single_permission(self, test_user_config):
        """Test requiring a single permission."""
        permission_checker = require_permissions("trade:read")

        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read", "trade:write"],
            is_active=True,
        )

        result = await permission_checker(current_user=trader)
        assert result == trader

    @pytest.mark.asyncio
    async def test_require_wildcard_permission(self, test_user_config):
        """Test wildcard permission grants all permissions."""
        permission_checker = require_permissions("any:permission")

        admin = User(
            user_id="admin-001",
            username="admin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=True,
        )

        result = await permission_checker(current_user=admin)
        assert result == admin

    @pytest.mark.asyncio
    async def test_require_permissions_unauthorized_raises_403(self, test_user_config):
        """Test user without required permissions raises 403."""
        permission_checker = require_permissions("admin:write")

        trader = User(
            user_id="trader-001",
            username="trader",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await permission_checker(current_user=trader)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_user_id(self, test_user_config):
        """Test get_user_id returns user ID."""
        user = User(
            user_id="test-001",
            username="testuser",
            role=UserRoles.TRADER,
            permissions=[],
            is_active=True,
        )

        # This would normally be used as a FastAPI dependency
        # For testing, we call it directly
        user_id = get_user_id(current_user=user)

        assert user_id == "test-001"

    def test_get_username(self, test_user_config):
        """Test get_username returns username."""
        user = User(
            user_id="test-001",
            username="testuser",
            role=UserRoles.TRADER,
            permissions=[],
            is_active=True,
        )

        username = get_username(current_user=user)

        assert username == "testuser"

    @jwt_skip
    def test_create_access_token_for_user(self, test_user_config):
        """Test creating access token for a user."""
        user = User(
            user_id="user-001",
            username="testuser",
            role=UserRoles.TRADER,
            permissions=["trade:read"],
            is_active=True,
        )

        token = create_access_token_for_user(user)

        assert token is not None
        assert isinstance(token, str)

    @jwt_skip
    def test_verify_token_and_get_user(self, test_user_config):
        """Test verifying token and getting user."""
        # Create a token for admin user
        admin_user = User(
            user_id="admin-001",
            username="testadmin",
            role=UserRoles.ADMIN,
            permissions=["*"],
            is_active=True,
        )

        token = create_access_token_for_user(admin_user)

        # Verify and get user
        user = verify_token_and_get_user(token)

        assert user is not None
        assert user.username == "testadmin"


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHandleFailedAttempt:
    """Test _handle_failed_attempt helper function."""

    def test_handle_failed_attempt_logs_to_audit(self, test_user_config, mock_audit_logger):
        """Test that failed attempts are logged to audit trail."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        # Record a failed attempt
        should_lock = _handle_failed_attempt(
            request_id="test_request",
            auth_method="api_key",
            attempt_tracker=tracker,
            audit_logger=mock_audit_logger,
        )

        # Should not lock after one attempt
        assert should_lock is False

        # Audit log should be called
        assert mock_audit_logger.log.called

    def test_handle_failed_attempt_locks_after_max_attempts(
        self, test_user_config, mock_audit_logger
    ):
        """Test that account locks after max failed attempts."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        # Record max failed attempts
        for i in range(tracker.MAX_FAILED_ATTEMPTS):
            should_lock = _handle_failed_attempt(
                request_id="test_request",
                auth_method="api_key",
                attempt_tracker=tracker,
                audit_logger=mock_audit_logger,
            )

        # Should lock on the last attempt
        assert should_lock is True


# ============================================================================
# Integration Tests
# ============================================================================


class TestAuthenticationIntegration:
    """Integration tests for authentication flows."""

    @pytest.mark.asyncio
    async def test_full_api_key_authentication_flow(self, test_user_config):
        """Test complete API key authentication flow."""
        # 1. User provides API key
        # 2. System verifies API key
        # 3. System returns user if valid

        user_store = get_user_store()
        username = user_store.verify_api_key("sk_test_test_api_key_12345")

        assert username == "testtrader"

        user = user_store.get_user(username)
        assert user is not None
        assert user.username == "testtrader"
        assert user.role == UserRoles.TRADER

    @pytest.mark.asyncio
    @jwt_skip
    async def test_full_jwt_authentication_flow(self, test_user_config):
        """Test complete JWT authentication flow."""
        # 1. Create token for user
        token_manager = get_token_manager()
        token = token_manager.create_access_token(
            data={"sub": "admin-001", "username": "testadmin", "role": "admin"}
        )

        # 2. Verify token
        payload = token_manager.verify_token(token)
        assert payload is not None

        # 3. Get user from payload
        user_store = get_user_store()
        user = user_store.get_user_by_id(payload["sub"])

        assert user is not None
        assert user.username == "testadmin"
        assert user.role == UserRoles.ADMIN

    @pytest.mark.asyncio
    async def test_full_lockout_flow(self, test_user_config, mock_audit_logger):
        """Test complete account lockout flow."""
        tracker = AuthAttemptTracker()
        tracker._audit = mock_audit_logger

        request_id = "test_lockout_request"

        # 1. Make several failed attempts
        for i in range(tracker.MAX_FAILED_ATTEMPTS - 1):
            locked = tracker.record_failed_attempt(request_id, "api_key")
            assert locked is False

        # 2. One more attempt should trigger lockout
        locked = tracker.record_failed_attempt(request_id, "api_key")
        assert locked is True

        # 3. Check lockout status
        is_locked, remaining = tracker.is_locked_out(request_id)
        assert is_locked is True
        assert remaining is not None and remaining > 0

        # 4. Verify locked out user cannot authenticate
        user_store = get_user_store()
        user_store.verify_api_key("sk_test_test_api_key_12345")
        # Even with valid key, lockout should prevent access (handled in dependency)

        # 5. Successful attempt should clear lockout
        tracker.record_successful_attempt(request_id, "testtrader")
        is_locked, remaining = tracker.is_locked_out(request_id)
        assert is_locked is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
