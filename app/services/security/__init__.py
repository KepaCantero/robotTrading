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
    # API Key Manager
    "ApiKeyManager",
    "ApiKey",
    "KeyPermission",
    "KeyValidationError",
    # Secrets Manager
    "SecretsManagerImpl",
    "SecretValue",
    "SecretStorage",
    "EnvironmentStorage",
    "EncryptedFileStorage",
    "SecretsError",
    # Key Rotation
    "KeyRotationManager",
    "RotationSchedule",
    "RotationResult",
    "RotationError",
    "RotationStatus",
]
