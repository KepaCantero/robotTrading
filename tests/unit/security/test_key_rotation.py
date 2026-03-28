"""
Unit tests for KeyRotationManager.

Tests the key rotation functionality including:
- Rotation scheduling
- Due rotation checking
- Key rotation execution
- Rollback functionality
- Schedule listing
"""

import pytest
from datetime import datetime, timedelta

from app.services.security.key_rotation import (
    KeyRotationManager,
    RotationSchedule,
    RotationResult,
    RotationError,
    RotationStatus,
)
from app.services.security.api_key_manager import (
    ApiKeyManager,
    KeyPermission,
)
from app.services.security.secrets_manager_impl import (
    SecretsManagerImpl,
)


@pytest.fixture
def encryption_key():
    """Generate a test encryption key."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key()


@pytest.fixture
def rotation_manager():
    """Create a KeyRotationManager instance for testing."""
    return KeyRotationManager()


@pytest.fixture
def api_key_manager(encryption_key):
    """Create an ApiKeyManager instance for testing."""
    return ApiKeyManager(encryption_key=encryption_key)


@pytest.fixture
def secrets_manager(encryption_key, monkeypatch):
    """Create a SecretsManagerImpl instance for testing."""
    monkeypatch.setenv("ALGOTRADING_ENCRYPTION_KEY", encryption_key.decode())
    return SecretsManagerImpl()


class TestKeyRotationManager:
    """Tests for KeyRotationManager class."""

    def test_init(self, rotation_manager):
        """Test initialization."""
        assert rotation_manager is not None
        assert rotation_manager._schedules == {}
        assert rotation_manager._rotation_history == []

    def test_schedule_rotation(self, rotation_manager):
        """Test scheduling a rotation."""
        schedule = rotation_manager.schedule_rotation(
            key_id="test_key_id", interval_days=30, grace_period_days=7
        )

        assert schedule.key_id == "test_key_id"
        assert schedule.rotation_interval_days == 30
        assert schedule.grace_period_days == 7
        assert schedule.rotation_status == RotationStatus.PENDING

        # Check next_rotation is set correctly
        expected_next = datetime.utcnow() + timedelta(days=30)
        # Allow 1 second tolerance
        assert abs((schedule.next_rotation - expected_next).total_seconds()) < 1

    def test_schedule_rotation_with_start_date(self, rotation_manager):
        """Test scheduling rotation with a specific start date."""
        start_date = datetime(2026, 1, 1, 12, 0, 0)

        schedule = rotation_manager.schedule_rotation(
            key_id="test_key_id", interval_days=30, start_from=start_date
        )

        assert schedule.last_rotation == start_date
        assert schedule.next_rotation == start_date + timedelta(days=30)

    def test_schedule_rotation_invalid_interval(self, rotation_manager):
        """Test scheduling rotation with invalid interval."""
        with pytest.raises(RotationError, match="Rotation interval must be positive"):
            rotation_manager.schedule_rotation(key_id="test_key_id", interval_days=0)

        with pytest.raises(RotationError, match="Rotation interval must be positive"):
            rotation_manager.schedule_rotation(key_id="test_key_id", interval_days=-5)

    def test_check_rotations_due_empty(self, rotation_manager):
        """Test checking due rotations when none are scheduled."""
        due_keys = rotation_manager.check_rotations_due()
        assert len(due_keys) == 0

    def test_check_rotations_due_not_due(self, rotation_manager):
        """Test checking due rotations when none are due yet."""
        rotation_manager.schedule_rotation(
            key_id="test_key_id", interval_days=30  # Not due for 30 days
        )

        due_keys = rotation_manager.check_rotations_due()
        assert len(due_keys) == 0

    def test_check_rotations_due(self, rotation_manager):
        """Test checking due rotations."""
        # Use a past start date to make rotation due
        past_date = datetime.utcnow() - timedelta(days=35)
        rotation_manager.schedule_rotation(
            key_id="test_key_id", interval_days=30, start_from=past_date
        )

        due_keys = rotation_manager.check_rotations_due()
        assert len(due_keys) == 1
        assert "test_key_id" in due_keys

    def test_check_rotations_due_multiple(self, rotation_manager):
        """Test checking due rotations with multiple keys."""
        rotation_manager.schedule_rotation("key1", interval_days=30)
        # Use past start date to make these due
        past_date = datetime.utcnow() - timedelta(days=35)
        rotation_manager.schedule_rotation("key2", interval_days=30, start_from=past_date)  # Due
        rotation_manager.schedule_rotation("key3", interval_days=30, start_from=past_date)  # Due
        rotation_manager.schedule_rotation("key4", interval_days=30)

        due_keys = rotation_manager.check_rotations_due()
        assert len(due_keys) == 2
        assert "key2" in due_keys
        assert "key3" in due_keys

    def test_rotate_key_as_api_key(self, rotation_manager, api_key_manager):
        """Test rotating an API key."""
        # Add initial key
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key="initial_key_value_123456789",
            permission=KeyPermission.READ_ONLY,
        )

        # Schedule rotation
        rotation_manager.schedule_rotation(key_id=key_id, interval_days=30)

        # Rotate the key
        result = rotation_manager.rotate_key(
            key_id=key_id, new_value="new_key_value_987654321", api_key_manager=api_key_manager
        )

        assert result.success is True
        assert result.key_id == key_id
        assert result.old_key_id == key_id
        assert result.new_key_id is not None
        assert result.new_key_id != key_id

    def test_rotate_key_with_auto_generation(self, rotation_manager, api_key_manager):
        """Test rotating a key with auto-generated value."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key="initial_key_value_123456789",
            permission=KeyPermission.READ_ONLY,
        )

        rotation_manager.schedule_rotation(key_id=key_id, interval_days=30)

        # Rotate without providing new value
        result = rotation_manager.rotate_key(key_id=key_id, api_key_manager=api_key_manager)

        assert result.success is True
        assert result.new_key_id is not None

    def test_rotate_key_not_found(self, rotation_manager, api_key_manager):
        """Test rotating a non-existent key."""
        result = rotation_manager.rotate_key(
            key_id="non_existent_id", api_key_manager=api_key_manager
        )

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_rotate_key_as_secret(self, rotation_manager, secrets_manager):
        """Test rotating a secret."""
        secrets_manager.set_secret("test_secret", "initial_value")

        rotation_manager.schedule_rotation(key_id="test_secret", interval_days=30)

        result = rotation_manager.rotate_key(
            key_id="test_secret", new_value="new_value", secrets_manager=secrets_manager
        )

        assert result.success is True
        assert result.key_id == "test_secret"
        assert result.old_key_id == "test_secret"
        assert result.new_key_id == "test_secret"  # Secrets keep same ID

    def test_rotate_key_without_manager(self, rotation_manager):
        """Test rotating a key without providing a manager."""
        result = rotation_manager.rotate_key(key_id="test_key_id")
        # Returns a failed result instead of raising exception
        assert result.success is False
        assert result.error_message is not None
        assert "Either api_key_manager or secrets_manager" in result.error_message

    def test_get_rotation_schedule(self, rotation_manager):
        """Test getting a rotation schedule."""
        rotation_manager.schedule_rotation(key_id="test_key_id", interval_days=30)

        schedule = rotation_manager.get_rotation_schedule("test_key_id")

        assert schedule is not None
        assert schedule.key_id == "test_key_id"
        assert schedule.rotation_interval_days == 30

    def test_get_rotation_schedule_not_found(self, rotation_manager):
        """Test getting a non-existent rotation schedule."""
        schedule = rotation_manager.get_rotation_schedule("non_existent")
        assert schedule is None

    def test_list_schedules(self, rotation_manager):
        """Test listing all rotation schedules."""
        rotation_manager.schedule_rotation("key1", interval_days=30)
        rotation_manager.schedule_rotation("key2", interval_days=60)
        rotation_manager.schedule_rotation("key3", interval_days=90)

        schedules = rotation_manager.list_schedules()

        assert len(schedules) == 3
        key_ids = [s.key_id for s in schedules]
        assert "key1" in key_ids
        assert "key2" in key_ids
        assert "key3" in key_ids

    def test_cancel_schedule(self, rotation_manager):
        """Test cancelling a rotation schedule."""
        rotation_manager.schedule_rotation(key_id="test_key_id", interval_days=30)

        result = rotation_manager.cancel_schedule("test_key_id")

        assert result is True
        assert rotation_manager.get_rotation_schedule("test_key_id") is None

    def test_cancel_schedule_not_found(self, rotation_manager):
        """Test cancelling a non-existent schedule."""
        result = rotation_manager.cancel_schedule("non_existent")
        assert result is False

    def test_update_schedule_interval(self, rotation_manager):
        """Test updating rotation interval."""
        rotation_manager.schedule_rotation(key_id="test_key_id", interval_days=30)

        result = rotation_manager.update_schedule(key_id="test_key_id", interval_days=60)

        assert result is True

        schedule = rotation_manager.get_rotation_schedule("test_key_id")
        assert schedule.rotation_interval_days == 60

    def test_update_schedule_grace_period(self, rotation_manager):
        """Test updating grace period."""
        rotation_manager.schedule_rotation(
            key_id="test_key_id", interval_days=30, grace_period_days=7
        )

        result = rotation_manager.update_schedule(key_id="test_key_id", grace_period_days=14)

        assert result is True

        schedule = rotation_manager.get_rotation_schedule("test_key_id")
        assert schedule.grace_period_days == 14

    def test_update_schedule_not_found(self, rotation_manager):
        """Test updating a non-existent schedule."""
        result = rotation_manager.update_schedule(key_id="non_existent", interval_days=60)
        assert result is False

    def test_update_schedule_invalid_interval(self, rotation_manager):
        """Test updating schedule with invalid interval."""
        rotation_manager.schedule_rotation(key_id="test_key_id", interval_days=30)

        result = rotation_manager.update_schedule(key_id="test_key_id", interval_days=0)
        assert result is False

    def test_get_rotation_history(self, rotation_manager, api_key_manager):
        """Test getting rotation history."""
        key_id = api_key_manager.add_key(
            key_name="test_key",
            api_key="initial_key_value_123456789",
            permission=KeyPermission.READ_ONLY,
        )

        rotation_manager.schedule_rotation(key_id=key_id, interval_days=30)

        # Perform rotation
        result1 = rotation_manager.rotate_key(
            key_id=key_id, new_value="new_value_1", api_key_manager=api_key_manager
        )

        # Get all history
        all_history = rotation_manager.get_rotation_history()
        assert len(all_history) == 1
        assert all_history[0].key_id == key_id

        # Get filtered history
        key_history = rotation_manager.get_rotation_history(key_id=key_id)
        assert len(key_history) == 1
        assert key_history[0].new_key_id == result1.new_key_id

    def test_get_rotation_history_empty(self, rotation_manager):
        """Test getting rotation history when empty."""
        history = rotation_manager.get_rotation_history()
        assert len(history) == 0


class TestRotationSchedule:
    """Tests for RotationSchedule dataclass."""

    def test_is_due_true(self):
        """Test is_due when rotation is due."""
        schedule = RotationSchedule(
            key_id="test_key",
            rotation_interval_days=30,
            last_rotation=datetime.utcnow() - timedelta(days=31),
            next_rotation=datetime.utcnow() - timedelta(days=1),  # Past
        )

        assert schedule.is_due() is True

    def test_is_due_false(self):
        """Test is_due when rotation is not due."""
        schedule = RotationSchedule(
            key_id="test_key",
            rotation_interval_days=30,
            last_rotation=datetime.utcnow(),
            next_rotation=datetime.utcnow() + timedelta(days=30),  # Future
        )

        assert schedule.is_due() is False

    def test_is_in_grace_period_true(self):
        """Test is_in_grace_period when in grace period."""
        schedule = RotationSchedule(
            key_id="test_key",
            rotation_interval_days=30,
            last_rotation=datetime.utcnow() - timedelta(days=1),
            next_rotation=datetime.utcnow() + timedelta(days=29),
            grace_period_days=7,
            rotation_status=RotationStatus.COMPLETED,
        )

        assert schedule.is_in_grace_period() is True

    def test_is_in_grace_period_false_expired(self):
        """Test is_in_grace_period when grace period has expired."""
        schedule = RotationSchedule(
            key_id="test_key",
            rotation_interval_days=30,
            last_rotation=datetime.utcnow() - timedelta(days=10),
            next_rotation=datetime.utcnow() + timedelta(days=20),
            grace_period_days=7,
            rotation_status=RotationStatus.COMPLETED,
        )

        assert schedule.is_in_grace_period() is False

    def test_is_in_grace_period_false_not_completed(self):
        """Test is_in_grace_period when rotation not completed."""
        schedule = RotationSchedule(
            key_id="test_key",
            rotation_interval_days=30,
            last_rotation=datetime.utcnow(),
            next_rotation=datetime.utcnow() + timedelta(days=30),
            grace_period_days=7,
            rotation_status=RotationStatus.PENDING,
        )

        assert schedule.is_in_grace_period() is False


class TestRotationResult:
    """Tests for RotationResult dataclass."""

    def test_rotation_result_fields(self):
        """Test RotationResult has all required fields."""
        now = datetime.utcnow()
        result = RotationResult(
            key_id="test_key",
            old_key_id="old_id",
            new_key_id="new_id",
            rotated_at=now,
            success=True,
        )

        assert result.key_id == "test_key"
        assert result.old_key_id == "old_id"
        assert result.new_key_id == "new_id"
        assert result.rotated_at == now
        assert result.success is True
        assert result.error_message is None
        assert result.status == RotationStatus.COMPLETED

    def test_rotation_result_with_error(self):
        """Test RotationResult with error."""
        now = datetime.utcnow()
        result = RotationResult(
            key_id="test_key",
            old_key_id=None,
            new_key_id=None,
            rotated_at=now,
            success=False,
            error_message="Key not found",
            status=RotationStatus.FAILED,
        )

        assert result.success is False
        assert result.error_message == "Key not found"
        assert result.status == RotationStatus.FAILED


class TestRotationStatus:
    """Tests for RotationStatus enum."""

    def test_rotation_status_values(self):
        """Test RotationStatus enum values."""
        assert RotationStatus.PENDING.value == "pending"
        assert RotationStatus.IN_PROGRESS.value == "in_progress"
        assert RotationStatus.COMPLETED.value == "completed"
        assert RotationStatus.FAILED.value == "failed"
        assert RotationStatus.ROLLED_BACK.value == "rolled_back"

    def test_rotation_status_comparison(self):
        """Test RotationStatus enum comparison."""
        assert RotationStatus.PENDING == RotationStatus.PENDING
        assert RotationStatus.PENDING != RotationStatus.COMPLETED
