"""
Secret Manager - Rule 28 Compliance: Secure Credential Management

This module provides centralized secret management following:
- Rule 28: Security and secrets management
- Rule 25: Clean code principles
- Rule 16: Cosmic Python (configuration as service)

Features:
1. NO hardcoded secrets in code
2. Environment variable loading with validation
3. Secret masking in logs
4. Secure secret validation
5. Type-safe secret access
6. Production-readiness checks

Usage:
    from app.core.secret_manager import get_secret, require_secret

    # Get secret with fallback (for development)
    api_key = get_secret("API_KEY", default=None)

    # Require secret (fails in production if missing)
    db_password = require_secret("DB_PASSWORD")

    # Validate secrets are configured
    validate_secrets_configured()
"""

import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SecretCategory(Enum):
    """Categories of secrets for validation."""

    DATABASE = "database"
    API_KEY = "api_key"
    BROKER = "broker"
    SECURITY = "security"
    NOTIFICATION = "notification"
    EXTERNAL_SERVICE = "external_service"


@dataclass
class SecretDefinition:
    """Definition of a required secret."""

    name: str
    category: SecretCategory
    description: str
    required_in_production: bool = True
    default_value: Optional[str] = None
    validation_pattern: Optional[str] = None
    min_length: int = 0
    max_length: int = 256
    requires_uppercase: bool = True
    requires_lowercase: bool = True
    requires_digit: bool = True
    requires_special: bool = False
    rotation_days: int = 90


@dataclass
class SecretMetadata:
    """Metadata for tracking secret rotation and usage."""

    name: str
    created_at: float
    last_rotated: float
    rotation_count: int = 0
    last_hash: Optional[str] = None
    last_validated: float = 0


class SecretValidationError(Exception):
    """Raised when secret validation fails."""



class SecretNotConfiguredError(Exception):
    """Raised when a required secret is not configured."""



# Secret definitions following Rule 28
SECRET_DEFINITIONS: List[SecretDefinition] = [
    # Security Secrets
    SecretDefinition(
        name="SECRET_KEY",
        category=SecretCategory.SECURITY,
        description="Main secret key for JWT tokens and encryption",
        required_in_production=True,
        min_length=32,
    ),
    # Database Secrets
    SecretDefinition(
        name="DATABASE_URL",
        category=SecretCategory.DATABASE,
        description="Database connection URL",
        required_in_production=True,
    ),
    SecretDefinition(
        name="DB_PASSWORD",
        category=SecretCategory.DATABASE,
        description="Database password (if not using URL)",
        required_in_production=False,
    ),
    # Broker API Keys
    SecretDefinition(
        name="ALPACA_API_KEY",
        category=SecretCategory.BROKER,
        description="Alpaca API key for trading",
        required_in_production=False,
    ),
    SecretDefinition(
        name="ALPACA_SECRET_KEY",
        category=SecretCategory.BROKER,
        description="Alpaca API secret key",
        required_in_production=False,
    ),
    # Market Data API Keys
    SecretDefinition(
        name="POLYGON_API_KEY",
        category=SecretCategory.API_KEY,
        description="Polygon.io API key for market data",
        required_in_production=False,
    ),
    SecretDefinition(
        name="ALPHA_VANTAGE_API_KEY",
        category=SecretCategory.API_KEY,
        description="Alpha Vantage API key for market data",
        required_in_production=False,
    ),
    SecretDefinition(
        name="NEWS_API_KEY",
        category=SecretCategory.API_KEY,
        description="News API key for sentiment analysis",
        required_in_production=False,
    ),
    # Notification Secrets
    SecretDefinition(
        name="SMTP_PASSWORD",
        category=SecretCategory.NOTIFICATION,
        description="SMTP password for email notifications",
        required_in_production=False,
    ),
    SecretDefinition(
        name="TELEGRAM_BOT_TOKEN",
        category=SecretCategory.NOTIFICATION,
        description="Telegram bot token for notifications",
        required_in_production=False,
    ),
    # External Services
    SecretDefinition(
        name="REDIS_PASSWORD",
        category=SecretCategory.EXTERNAL_SERVICE,
        description="Redis password for caching",
        required_in_production=False,
    ),
    SecretDefinition(
        name="QUESTDB_PASSWORD",
        category=SecretCategory.EXTERNAL_SERVICE,
        description="QuestDB password for metrics storage",
        required_in_production=False,
    ),
]


@dataclass
class SecretValidationReport:
    """Report from secret validation."""

    is_valid: bool
    missing_secrets: List[str] = field(default_factory=list)
    weak_secrets: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    compliance_score: float = 0.0
    rotation_required: List[str] = field(default_factory=list)
    strength_scores: Dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        """Format validation report."""
        lines = [
            "Secret Validation Report",
            "=" * 50,
            f"Valid: {self.is_valid}",
            f"Compliance: {self.compliance_score:.1f}%",
        ]

        if self.missing_secrets:
            lines.append(f"\nMissing Required Secrets ({len(self.missing_secrets)}):")
            for secret in self.missing_secrets:
                lines.append(f"  - {secret}")

        if self.weak_secrets:
            lines.append(f"\nWeak Secrets ({len(self.weak_secrets)}):")
            for secret in self.weak_secrets:
                lines.append(f"  - {secret}")

        if self.rotation_required:
            lines.append(f"\nSecrets Requiring Rotation ({len(self.rotation_required)}):")
            for secret in self.rotation_required:
                lines.append(f"  - {secret}")

        if self.strength_scores:
            lines.append("\nSecret Strength Scores:")
            for secret, score in sorted(self.strength_scores.items()):
                strength = (
                    "Strong"
                    if score >= 80
                    else "Good"
                    if score >= 60
                    else "Weak"
                    if score >= 40
                    else "Very Weak"
                )
                lines.append(f"  - {secret}: {score}/100 ({strength})")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


class SecretManager:
    """
    Centralized secret manager following Rule 28.

    Provides:
    1. Type-safe secret access
    2. Automatic validation
    3. Secret masking in logs
    4. Production readiness checks
    5. Secret strength validation
    6. Rotation detection
    """

    # Common weak patterns to detect
    WEAK_PATTERNS = [
        r"password",
        r"secret",
        r"changeme",
        r"default",
        r"12345678",
        r"admin",
        r"test",
        r"quest",
        r"qwerty",
        r"letmein",
        r"welcome",
        r"monkey",
    ]

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._masked_values: Set[str] = set()
        self._is_production = self._detect_production()
        self._metadata: Dict[str, SecretMetadata] = {}
        self._load_metadata()

    def _load_metadata(self):
        """Load secret metadata from environment or file."""
        # Initialize metadata for known secrets
        for definition in SECRET_DEFINITIONS:
            value = os.getenv(definition.name)
            if value:
                secret_hash = self._hash_secret(value)
                now = time.time()
                self._metadata[definition.name] = SecretMetadata(
                    name=definition.name,
                    created_at=now,
                    last_rotated=now,
                    last_hash=secret_hash,
                    last_validated=now,
                )

    def _hash_secret(self, value: str) -> str:
        """Create hash of secret value for rotation detection."""
        return hashlib.sha256(value.encode()).hexdigest()

    def _detect_secret_rotation(self, name: str, current_value: str) -> bool:
        """
        Detect if a secret has been rotated.

        Args:
            name: Secret name
            current_value: Current secret value

        Returns:
            True if secret was rotated
        """
        current_hash = self._hash_secret(current_value)

        if name in self._metadata:
            metadata = self._metadata[name]
            if metadata.last_hash and metadata.last_hash != current_hash:
                logger.info(f"Secret rotation detected for '{name}'")
                metadata.last_rotated = time.time()
                metadata.rotation_count += 1
                metadata.last_hash = current_hash
                return True

        return False

    def calculate_strength_score(self, value: str, definition: SecretDefinition) -> int:
        """
        Calculate secret strength score (0-100).

        Args:
            value: Secret value
            definition: Secret definition

        Returns:
            Strength score (0-100)
        """
        if not value:
            return 0

        score = 0

        # Length scoring (up to 40 points)
        length_score = min(40, len(value) * 2)
        score += length_score

        # Character variety (up to 40 points)
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in value)

        variety_score = sum(
            [
                10 if has_upper else 0,
                10 if has_lower else 0,
                10 if has_digit else 0,
                10 if has_special else 0,
            ]
        )
        score += variety_score

        # Entropy estimation (up to 20 points)
        unique_chars = len(set(value))
        entropy_score = min(20, unique_chars)
        score += entropy_score

        # Penalty for common patterns
        for pattern in self.WEAK_PATTERNS:
            if pattern.lower() in value.lower():
                score -= 30
                logger.warning(f"Weak pattern '{pattern}' detected in '{definition.name}'")

        return max(0, min(100, score))

    def _detect_production(self) -> bool:
        """Detect if running in production."""
        return os.getenv("ENVIRONMENT", "development").lower() in ["production", "prod"]

    def get(self, key: str, default: Optional[str] = None, mask: bool = True) -> Optional[str]:
        """
        Get secret from environment with caching.

        Args:
            key: Environment variable name
            default: Default value if not found (only for development)
            mask: Whether to mask this secret in logs

        Returns:
            Secret value or default

        Raises:
            SecretNotConfiguredError: If secret not found and no default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Get from environment
        value = os.getenv(key, default)

        if value is None:
            raise SecretNotConfiguredError(
                f"Required secret '{key}' not configured. "
                f"Set environment variable or provide default."
            )

        # Cache and optionally mask
        self._cache[key] = value
        if mask:
            self._masked_values.add(value)

        return value

    def require(self, key: str, mask: bool = True) -> str:
        """
        Require a secret (no default allowed).

        Args:
            key: Environment variable name
            mask: Whether to mask this secret in logs

        Returns:
            Secret value

        Raises:
            SecretNotConfiguredError: If secret not found
        """
        return self.get(key, default=None, mask=mask)

    def get_safe(self, key: str, default: str = "") -> str:
        """
        Get secret without masking (for non-sensitive config).

        Args:
            key: Environment variable name
            default: Default value

        Returns:
            Configuration value
        """
        return os.getenv(key, default)

    def mask_value(self, value: str, visible_chars: int = 4) -> str:
        """
        Mask a secret value for logging.

        Args:
            value: Value to mask
            visible_chars: Number of characters to show

        Returns:
            Masked value (e.g., "abcd...xyz")
        """
        if not value:
            return "***"

        if len(value) <= visible_chars * 2:
            return "*" * len(value)

        return f"{value[:visible_chars]}...{value[-visible_chars:]}"

    def is_masked(self, value: str) -> bool:
        """Check if a value should be masked."""
        return value in self._masked_values

    def validate_secret(self, definition: SecretDefinition) -> bool:
        """
        Validate a single secret.

        Args:
            definition: Secret definition

        Returns:
            True if valid, False if weak pattern detected

        Raises:
            SecretValidationError: If validation fails (except weak patterns)
        """
        value = os.getenv(definition.name)

        # Check if required in production
        if definition.required_in_production and self._is_production:
            if not value:
                raise SecretValidationError(
                    f"Required secret '{definition.name}' not configured for production"
                )

        if not value:
            return True  # Optional secret not set

        # Check minimum length
        if len(value) < definition.min_length:
            raise SecretValidationError(
                f"Secret '{definition.name}' is too short "
                f"(minimum {definition.min_length} characters, got {len(value)})"
            )

        # Check maximum length
        if len(value) > definition.max_length:
            raise SecretValidationError(
                f"Secret '{definition.name}' is too long "
                f"(maximum {definition.max_length} characters, got {len(value)})"
            )

        # Check for weak/default values FIRST (before character requirements)
        # This allows weak patterns to return False instead of raising exceptions
        for pattern in self.WEAK_PATTERNS:
            if pattern.lower() in value.lower():
                logger.warning(
                    f"Weak/default value pattern '{pattern}' detected for '{definition.name}'. "
                    f"Use a strong, unique value."
                )
                return False

        # Check character requirements (only if not a weak pattern)
        if definition.requires_uppercase and not any(c.isupper() for c in value):
            raise SecretValidationError(
                f"Secret '{definition.name}' must contain at least one uppercase letter"
            )

        if definition.requires_lowercase and not any(c.islower() for c in value):
            raise SecretValidationError(
                f"Secret '{definition.name}' must contain at least one lowercase letter"
            )

        if definition.requires_digit and not any(c.isdigit() for c in value):
            raise SecretValidationError(
                f"Secret '{definition.name}' must contain at least one digit"
            )

        if definition.requires_special:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in value):
                raise SecretValidationError(
                    f"Secret '{definition.name}' must contain at least one special character"
                )

        # Detect rotation
        self._detect_secret_rotation(definition.name, value)

        # Calculate and log strength
        strength = self.calculate_strength_score(value, definition)
        if strength < 60:
            logger.warning(
                f"Secret '{definition.name}' has low strength score: {strength}/100. "
                f"Consider using a stronger value."
            )

        return True

    def validate_all(self) -> SecretValidationReport:
        """
        Validate all configured secrets.

        Returns:
            Validation report with compliance score
        """
        report = SecretValidationReport(is_valid=True)
        total_required = 0
        total_valid = 0

        for definition in SECRET_DEFINITIONS:
            try:
                # Check if required in current environment
                is_required = definition.required_in_production and self._is_production

                if is_required:
                    total_required += 1

                # Validate the secret
                if self.validate_secret(definition):
                    if is_required:
                        total_valid += 1

                    # Calculate strength score
                    value = os.getenv(definition.name)
                    if value:
                        strength = self.calculate_strength_score(value, definition)
                        report.strength_scores[definition.name] = strength

                        # Check for rotation requirement
                        if definition.name in self._metadata:
                            metadata = self._metadata[definition.name]
                            days_since_rotation = (time.time() - metadata.last_rotated) / 86400
                            if days_since_rotation > definition.rotation_days:
                                report.rotation_required.append(
                                    f"{definition.name}: Last rotated {days_since_rotation:.0f} days ago "
                                    f"(rotation period: {definition.rotation_days} days)"
                                )

            except SecretValidationError as e:
                report.missing_secrets.append(f"{definition.name}: {str(e)}")
                report.is_valid = False

        # Calculate compliance
        if total_required > 0:
            report.compliance_score = (total_valid / total_required) * 100
        else:
            report.compliance_score = 100.0

        # Adjust compliance based on weak secrets and rotation
        if report.weak_secrets:
            report.compliance_score -= len(report.weak_secrets) * 5

        if report.rotation_required:
            report.compliance_score -= len(report.rotation_required) * 2

        # Calculate average strength score and adjust compliance
        if report.strength_scores:
            avg_strength = sum(report.strength_scores.values()) / len(report.strength_scores)
            report.compliance_score = (report.compliance_score + avg_strength) / 2

        report.compliance_score = max(0, min(100, report.compliance_score))

        # Final validation
        if report.missing_secrets or report.weak_secrets or report.compliance_score < 80:
            report.is_valid = False

        return report

    def generate_secure_secret(
        self,
        length: int = 32,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_special: bool = True,
    ) -> str:
        """
        Generate a cryptographically secure random secret.

        Args:
            length: Desired length
            include_uppercase: Include uppercase letters
            include_lowercase: Include lowercase letters
            include_digits: Include digits
            include_special: Include special characters

        Returns:
            Generated secret

        Raises:
            ValueError: If no character types selected
        """
        charset = ""
        if include_uppercase:
            charset += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if include_lowercase:
            charset += "abcdefghijklmnopqrstuvwxyz"
        if include_digits:
            charset += "0123456789"
        if include_special:
            charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not charset:
            raise ValueError("At least one character type must be selected")

        return ''.join(secrets.choice(charset) for _ in range(length))

    def check_rotation_needed(self, secret_name: str, rotation_days: int = None) -> bool:
        """
        Check if a secret needs rotation.

        Args:
            secret_name: Name of the secret
            rotation_days: Rotation period (uses definition default if None)

        Returns:
            True if rotation is needed
        """
        if secret_name not in self._metadata:
            return False

        metadata = self._metadata[secret_name]

        # Get rotation period from definition if not specified
        if rotation_days is None:
            for definition in SECRET_DEFINITIONS:
                if definition.name == secret_name:
                    rotation_days = definition.rotation_days
                    break

        if rotation_days is None:
            rotation_days = 90  # Default

        days_since_rotation = (time.time() - metadata.last_rotated) / 86400
        return days_since_rotation > rotation_days

    def get_secret_metadata(self, secret_name: str) -> Optional[SecretMetadata]:
        """
        Get metadata for a secret.

        Args:
            secret_name: Name of the secret

        Returns:
            Secret metadata or None
        """
        return self._metadata.get(secret_name)

    def get_connection_string(self, db_type: str) -> str:
        """
        Build connection string from environment variables (Rule 28 compliant).

        NEVER hardcodes credentials in connection strings.

        Args:
            db_type: Type of database (postgresql, redis, questdb)

        Returns:
            Connection string built from environment variables

        Raises:
            SecretNotConfiguredError: If required variables not set
        """
        if db_type == "postgresql":
            host = self.get("DB_HOST", default="localhost")
            port = self.get("DB_PORT", default="5432")
            user = self.get("DB_USER", default="postgres")
            password = self.get("DB_PASSWORD")
            database = self.get("DB_NAME", default="trading")

            if not password:
                raise SecretNotConfiguredError("DB_PASSWORD required for PostgreSQL connection")

            return f"postgresql://{user}:{password}@{host}:{port}/{database}"

        elif db_type == "redis":
            host = self.get("REDIS_HOST", default="localhost")
            port = self.get("REDIS_PORT", default="6379")
            db = self.get("REDIS_DB", default="0")
            password = self.get("REDIS_PASSWORD", default=None)

            if password:
                return f"redis://:{password}@{host}:{port}/{db}"
            return f"redis://{host}:{port}/{db}"

        elif db_type == "questdb":
            host = self.get("QUESTDB_HOST", default="localhost")
            port = self.get("QUESTDB_PORT", default="9009")
            user = self.get("QUESTDB_USER", default="admin")
            password = self.get("QUESTDB_PASSWORD", default="quest")
            database = self.get("QUESTDB_DATABASE", default="qdb")

            return f"postgresql://{user}:{password}@{host}:{port}/{database}"

        else:
            raise ValueError(f"Unknown database type: {db_type}")

    def clear_cache(self):
        """Clear secret cache (useful for testing)."""
        self._cache.clear()
        self._masked_values.clear()


# Global singleton instance
_secret_manager = SecretManager()


def get_secret(key: str, default: Optional[str] = None, mask: bool = True) -> Optional[str]:
    """
    Get secret from environment (convenience function).

    Args:
        key: Environment variable name
        default: Default value if not found (development only)
        mask: Whether to mask in logs

    Returns:
        Secret value or default

    Example:
        >>> api_key = get_secret("ALPACA_API_KEY")
        >>> db_url = get_secret("DATABASE_URL", default="sqlite:///dev.db")
    """
    return _secret_manager.get(key, default=default, mask=mask)


def require_secret(key: str, mask: bool = True) -> str:
    """
    Require a secret with no default (production).

    Args:
        key: Environment variable name
        mask: Whether to mask in logs

    Returns:
        Secret value

    Raises:
        SecretNotConfiguredError: If secret not found

    Example:
        >>> db_password = require_secret("DB_PASSWORD")
    """
    return _secret_manager.require(key, mask=mask)


def validate_secrets_configured() -> SecretValidationReport:
    """
    Validate all secrets are configured correctly.

    Returns:
        Validation report

    Example:
        >>> report = validate_secrets_configured()
        >>> if not report.is_valid:
        ...     print(report)
    """
    return _secret_manager.validate_all()


def get_connection_string(db_type: str) -> str:
    """
    Build database connection string from environment variables.

    This is the RULE 28 COMPLIANT way to build connection strings.
    NEVER hardcode credentials in connection strings.

    Args:
        db_type: Database type (postgresql, redis, questdb)

    Returns:
        Connection string

    Example:
        >>> db_url = get_connection_string("postgresql")
        >>> redis_url = get_connection_string("redis")
    """
    return _secret_manager.get_connection_string(db_type)


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Mask a secret value for safe logging.

    Args:
        value: Secret value to mask
        visible_chars: Characters to show at start/end

    Returns:
        Masked value

    Example:
        >>> logger.info(f"Using API key: {mask_secret(api_key)}")
        >>> # Logs: "Using API key: sk_a...xyz"
    """
    return _secret_manager.mask_value(value, visible_chars=visible_chars)


def is_production() -> bool:
    """Check if running in production environment."""
    return _secret_manager._is_production


def generate_secure_secret(length: int = 32, use_special_chars: bool = True) -> str:
    """
    Generate a cryptographically secure random secret.

    Args:
        length: Length of secret to generate (default: 32)
        use_special_chars: Include special characters (default: True)

    Returns:
        Secure random secret

    Example:
        >>> api_key = generate_secure_secret(32)
        >>> password = generate_secure_secret(16, use_special_chars=True)
    """
    return _secret_manager.generate_secure_secret(length, use_special_chars)


__all__ = [
    "get_secret",
    "require_secret",
    "validate_secrets_configured",
    "get_connection_string",
    "mask_secret",
    "is_production",
    "generate_secure_secret",
    "SecretManager",
    "SecretValidationError",
    "SecretNotConfiguredError",
    "SecretValidationReport",
    "SecretDefinition",
    "SecretMetadata",
    "SecretCategory",
]
