# Task 19: Security Hardening - Implementation Prompt

## Objective

Implement security hardening for the algoTrading system by creating API key management, secrets management, and key rotation utilities.

## Context

You are implementing Task 19 (Security Hardening) of the algoTrading system. This is Phase 7 (Security Layer), which is a P1 priority task.

## Requirements

### R29: Security Hardening

The system must have secure credential management with:
1. API key management with encrypted storage
2. Secrets manager for secure credential storage
3. Key rotation utilities

## Implementation Steps

### Step 1: Create Security Package Structure

Create the security package directory:
```bash
mkdir -p app/services/security
mkdir -p tests/unit/security
```

### Step 2: Implement API Key Manager

Create `app/services/security/api_key_manager.py` with:

1. **ApiKey** dataclass:
   - key_id: str (unique identifier)
   - key_name: str (human-readable name)
   - encrypted_key: str (encrypted API key value)
   - permission: KeyPermission (enum: READ_ONLY, TRADING, ADMIN)
   - created_at: datetime
   - expires_at: Optional[datetime]
   - last_used: Optional[datetime]
   - is_active: bool

2. **KeyPermission** enum:
   - READ_ONLY: Can only read data
   - TRADING: Can execute trades
   - ADMIN: Full access

3. **ApiKeyManager** class with methods:
   - `add_key(key_name: str, api_key: str, permission: KeyPermission, expires_in_days: Optional[int] = None) -> str`
   - `get_key(key_id: str) -> Optional[ApiKey]`
   - `get_key_by_name(key_name: str) -> Optional[ApiKey]`
   - `validate_key(key_id: str, provided_key: str) -> bool`
   - `revoke_key(key_id: str) -> bool`
   - `list_keys() -> List[ApiKey]`
   - `update_last_used(key_id: str) -> None`
   - `check_expiration() -> List[str]` (returns expired key IDs)

4. **KeyValidationError** exception

### Step 3: Implement Secrets Manager

Create `app/services/security/secrets_manager_impl.py` with:

1. **SecretValue** dataclass:
   - key: str
   - value: str (encrypted)
   - version: int
   - created_at: datetime
   - updated_at: datetime

2. **SecretStorage** protocol (typing.Protocol):
   - `store(key: str, value: str) -> None`
   - `retrieve(key: str) -> Optional[str]`
   - `delete(key: str) -> bool`
   - `list_keys() -> List[str]`

3. **EnvironmentStorage** class:
   - Stores/retrieves secrets from environment variables
   - Implements SecretStorage protocol

4. **EncryptedFileStorage** class:
   - Stores secrets in encrypted JSON file
   - Uses Fernet symmetric encryption
   - Implements SecretStorage protocol

5. **SecretsManagerImpl** class with methods:
   - `set_secret(key: str, value: str) -> None`
   - `get_secret(key: str) -> Optional[str]`
   - `delete_secret(key: str) -> bool`
   - `rotate_secret(key: str, new_value: str) -> bool`
   - `list_secrets() -> List[str]`
   - `set_storage_backend(backend: SecretStorage) -> None`

6. **SecretsError** exception

### Step 4: Implement Key Rotation

Create `app/services/security/key_rotation.py` with:

1. **RotationSchedule** dataclass:
   - key_id: str
   - rotation_interval_days: int
   - last_rotation: datetime
   - next_rotation: datetime
   - grace_period_days: int (days old key remains valid)

2. **RotationResult** dataclass:
   - key_id: str
   - old_key_id: str
   - new_key_id: str
   - rotated_at: datetime
   - success: bool
   - error_message: Optional[str]

3. **KeyRotationManager** class with methods:
   - `schedule_rotation(key_id: str, interval_days: int, grace_period_days: int = 7) -> None`
   - `check_rotations_due() -> List[str]` (returns key IDs due for rotation)
   - `rotate_key(key_id: str, new_value: Optional[str] = None) -> RotationResult`
   - `rollback_rotation(key_id: str) -> bool`
   - `get_rotation_schedule(key_id: str) -> Optional[RotationSchedule]`
   - `list_schedules() -> List[RotationSchedule]`

4. **RotationError** exception

### Step 5: Create Package Exports

Create `app/services/security/__init__.py` with exports:
```python
from .api_key_manager import (
    ApiKeyManager,
    ApiKey,
    KeyPermission,
    KeyValidationError,
)
from .secrets_manager_impl import (
    SecretsManagerImpl,
    SecretValue,
    SecretStorage,
    EnvironmentStorage,
    EncryptedFileStorage,
    SecretsError,
)
from .key_rotation import (
    KeyRotationManager,
    RotationSchedule,
    RotationResult,
    RotationError,
)

__all__ = [
    "ApiKeyManager",
    "ApiKey",
    "KeyPermission",
    "KeyValidationError",
    "SecretsManagerImpl",
    "SecretValue",
    "SecretStorage",
    "EnvironmentStorage",
    "EncryptedFileStorage",
    "SecretsError",
    "KeyRotationManager",
    "RotationSchedule",
    "RotationResult",
    "RotationError",
]
```

### Step 6: Create Unit Tests

Create comprehensive unit tests:

1. **tests/unit/security/test_api_key_manager.py**:
   - Test key creation with various permissions
   - Test key retrieval by ID and name
   - Test key validation
   - Test key revocation
   - Test expiration checking
   - Test last_used updates

2. **tests/unit/security/test_secrets_manager.py**:
   - Test EnvironmentStorage backend
   - Test EncryptedFileStorage backend
   - Test secret storage and retrieval
   - Test secret rotation
   - Test secret deletion
   - Test storage backend switching

3. **tests/unit/security/test_key_rotation.py**:
   - Test rotation scheduling
   - Test due rotation checking
   - Test key rotation execution
   - Test rollback functionality
   - Test schedule listing

### Step 7: Implementation Notes

1. Use `cryptography` library for encryption:
   ```python
   from cryptography.fernet import Fernet
   ```

2. Generate encryption key securely:
   ```python
   from cryptography.fernet import Fernet
   key = Fernet.generate_key()
   f = Fernet(key)
   encrypted = f.encrypt(plaintext.encode())
   decrypted = f.decrypt(encrypted).decode()
   ```

3. Store master encryption key separately:
   - Use environment variable: `ALGOTRADING_ENCRYPTION_KEY`
   - Or use keyring library for system key storage

4. Never log actual secret values - only metadata

5. Validate all inputs to prevent injection attacks

## Validation

After implementation:

1. Compile all Python files:
   ```bash
   python -m py_compile app/services/security/*.py
   ```

2. Run unit tests:
   ```bash
   python -m pytest tests/unit/security/ -v
   ```

3. Check for hardcoded secrets:
   ```bash
   grep -r "api_key.*=.*['\"]" app/services/security/
   # Should return nothing
   ```

4. Verify package exports:
   ```python
   from app.services.security import ApiKeyManager, SecretsManagerImpl, KeyRotationManager
   ```

## Integration Points

- **User config system (Task 14)**: Use for storing secure credentials
- **Alerting system (Task 15)**: Send notifications on rotation events
- **CLI (Task 13)**: Add commands for secure credential setup

## Checkpoint

Update `.ralph/checkpoints/19_security_hardening_checkpoint.json`:
```json
{
  "task": "19_security_hardening",
  "status": "completed",
  "completed_at": "2026-02-09T...Z",
  "files_created": [
    "app/services/security/__init__.py",
    "app/services/security/api_key_manager.py",
    "app/services/security/secrets_manager_impl.py",
    "app/services/security/key_rotation.py",
    "tests/unit/security/__init__.py",
    "tests/unit/security/test_api_key_manager.py",
    "tests/unit/security/test_secrets_manager.py",
    "tests/unit/security/test_key_rotation.py"
  ],
  "tests_passed": true,
  "security_hardening_implemented": true
}
```

## Next Task

After completing this task, the remaining tasks are:
- Task 18: Additional Rules (P2 - OPTIONAL, may skip)
- Task 99: Final Cleanup (MUST BE LAST)
