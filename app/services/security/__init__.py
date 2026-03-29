"""
Security services for the algoTrading system.

This package provides security hardening features including:
- API key management with encrypted storage
- Secrets management for secure credential storage
- Key rotation utilities for automated credential rotation

R29: Security Hardening
"""

from .api_key_manager import ApiKey, ApiKeyManager, KeyPermission, KeyValidationError
from .key_rotation import (
    KeyRotationManager,
    RotationError,
    RotationResult,
    RotationSchedule,
    RotationStatus,
)
from .secrets_manager_impl import (
    EncryptedFileStorage,
    EnvironmentStorage,
    SecretsError,
    SecretsManagerImpl,
    SecretStorage,
    SecretValue,
)

__all__ = [
    "ApiKey",
    # API Key Manager
    "ApiKeyManager",
    "EncryptedFileStorage",
    "EnvironmentStorage",
    "KeyPermission",
    # Key Rotation
    "KeyRotationManager",
    "KeyValidationError",
    "RotationError",
    "RotationResult",
    "RotationSchedule",
    "RotationStatus",
    "SecretStorage",
    "SecretValue",
    "SecretsError",
    # Secrets Manager
    "SecretsManagerImpl",
]
