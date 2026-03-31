"""
Test suite for Secret Manager (Rule 28 Compliance)

Tests:
- Secret strength validation
- Secret rotation detection
- Secret masking
- Compliance scoring
"""

import os
import time

import pytest

from app.security.secrets.secret_manager import (
    SecretCategory,
    SecretDefinition,
    SecretManager,
    SecretMetadata,
    SecretValidationError,
    SecretValidationReport,
    generate_secure_secret,
)


class TestSecretStrengthValidation:
    """Tests for secret strength validation."""

    def test_calculate_strength_score_strong_secret(self):
        """Test strength score calculation for strong secret."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_SECRET",
            category=SecretCategory.SECURITY,
            description="Test secret",
            min_length=32,
        )

        strong_secret = "Abc123!@#Xyz789$%^Def456&*()Ghi012"
        score = manager.calculate_strength_score(strong_secret, definition)

        assert score >= 80, f"Strong secret should score >= 80, got {score}"

    def test_calculate_strength_score_weak_secret(self):
        """Test strength score calculation for weak secret."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_SECRET",
            category=SecretCategory.SECURITY,
            description="Test secret",
            min_length=8,
        )

        weak_secret = "password"
        score = manager.calculate_strength_score(weak_secret, definition)

        assert score < 40, f"Weak secret should score < 40, got {score}"

    def test_calculate_strength_score_short_secret(self):
        """Test strength score calculation for short secret."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_SECRET",
            category=SecretCategory.SECURITY,
            description="Test secret",
            min_length=8,
        )

        short_secret = "Ab1!"
        score = manager.calculate_strength_score(short_secret, definition)

        assert score < 50, f"Short secret should score < 50, got {score}"

    def test_calculate_strength_score_no_variety(self):
        """Test strength score for secret without character variety."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_SECRET",
            category=SecretCategory.SECURITY,
            description="Test secret",
            min_length=16,
        )

        no_variety = "abcdefghijk123456789"
        score = manager.calculate_strength_score(no_variety, definition)

        assert score < 60, f"Secret without variety should score < 60, got {score}"


class TestSecretRotationDetection:
    """Tests for secret rotation detection."""

    def test_detect_secret_rotation(self):
        """Test detection of secret rotation."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_ROTATION",
            category=SecretCategory.SECURITY,
            description="Test rotation",
            min_length=16,
        )

        # Set initial secret
        os.environ["TEST_ROTATION"] = "InitialSecret123!@#"
        manager._load_metadata()

        # Get initial metadata
        initial_metadata = manager.get_secret_metadata("TEST_ROTATION")
        initial_rotation_count = initial_metadata.rotation_count if initial_metadata else 0

        # Rotate secret
        os.environ["TEST_ROTATION"] = "RotatedSecret456$%^"
        manager._detect_secret_rotation("TEST_ROTATION", os.environ["TEST_ROTATION"])

        # Check rotation detected
        new_metadata = manager.get_secret_metadata("TEST_ROTATION")
        assert new_metadata is not None
        assert new_metadata.rotation_count == initial_rotation_count + 1

        # Cleanup
        del os.environ["TEST_ROTATION"]

    def test_check_rotation_needed(self):
        """Test checking if rotation is needed."""
        manager = SecretManager()

        # Create old metadata
        metadata = SecretMetadata(
            name="OLD_SECRET",
            created_at=time.time() - (100 * 86400),  # 100 days ago
            last_rotated=time.time() - (100 * 86400),
            rotation_count=0,
        )
        manager._metadata["OLD_SECRET"] = metadata

        # Check rotation needed
        assert manager.check_rotation_needed("OLD_SECRET", rotation_days=90)

        # Check rotation not needed
        assert not manager.check_rotation_needed("OLD_SECRET", rotation_days=120)


class TestSecretValidation:
    """Tests for secret validation."""

    def test_validate_secret_strong(self):
        """Test validation of strong secret."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_STRONG",
            category=SecretCategory.SECURITY,
            description="Test strong",
            min_length=32,
            requires_uppercase=True,
            requires_lowercase=True,
            requires_digit=True,
            requires_special=True,
        )

        os.environ["TEST_STRONG"] = "StrongSecret123!@#WithSpecialChars456$%^"
        assert manager.validate_secret(definition)

        del os.environ["TEST_STRONG"]

    def test_validate_secret_too_short(self):
        """Test validation rejects too short secret."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_SHORT",
            category=SecretCategory.SECURITY,
            description="Test short",
            min_length=32,
        )

        os.environ["TEST_SHORT"] = "Short"

        with pytest.raises(SecretValidationError):
            manager.validate_secret(definition)

        del os.environ["TEST_SHORT"]

    def test_validate_secret_missing_uppercase(self):
        """Test validation rejects secret without uppercase."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_NO_UPPER",
            category=SecretCategory.SECURITY,
            description="Test no upper",
            requires_uppercase=True,
        )

        os.environ["TEST_NO_UPPER"] = "lowercase123!@#"

        with pytest.raises(SecretValidationError):
            manager.validate_secret(definition)

        del os.environ["TEST_NO_UPPER"]

    def test_validate_secret_missing_digit(self):
        """Test validation rejects secret without digit."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_NO_DIGIT",
            category=SecretCategory.SECURITY,
            description="Test no digit",
            requires_digit=True,
        )

        os.environ["TEST_NO_DIGIT"] = "NoDigitsHere!@#"

        with pytest.raises(SecretValidationError):
            manager.validate_secret(definition)

        del os.environ["TEST_NO_DIGIT"]

    def test_validate_secret_weak_pattern(self):
        """Test validation detects weak patterns."""
        manager = SecretManager()
        definition = SecretDefinition(
            name="TEST_WEAK",
            category=SecretCategory.SECURITY,
            description="Test weak",
            min_length=16,
        )

        os.environ["TEST_WEAK"] = "mypassword123456"

        assert not manager.validate_secret(definition)

        del os.environ["TEST_WEAK"]


class TestSecretMasking:
    """Tests for secret masking in logs."""

    def test_mask_value_short(self):
        """Test masking of short value."""
        manager = SecretManager()

        masked = manager.mask_value("abcd", visible_chars=2)
        assert masked == "ab**"

    def test_mask_value_long(self):
        """Test masking of long value."""
        manager = SecretManager()

        masked = manager.mask_value("VeryLongSecretValue123456789", visible_chars=4)
        assert masked == "Very...6789"

    def test_mask_value_very_short(self):
        """Test masking of very short value."""
        manager = SecretManager()

        masked = manager.mask_value("ab", visible_chars=4)
        assert masked == "**"

    def test_is_masked(self):
        """Test checking if value is masked."""
        manager = SecretManager()

        manager.get("MASK_TEST", default="secret_value", mask=True)

        assert manager.is_masked("secret_value")
        assert not manager.is_masked("other_value")


class TestSecretGeneration:
    """Tests for secure secret generation."""

    def test_generate_secure_secret_default(self):
        """Test generating secret with default settings."""
        secret = generate_secure_secret()

        assert len(secret) == 32
        assert any(c.isupper() for c in secret)
        assert any(c.islower() for c in secret)
        assert any(c.isdigit() for c in secret)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)

    def test_generate_secure_secret_custom_length(self):
        """Test generating secret with custom length."""
        secret = generate_secure_secret(length=64)

        assert len(secret) == 64

    def test_generate_secure_secret_no_special(self):
        """Test generating secret without special characters."""
        secret = generate_secure_secret(length=32, include_special=False)

        assert not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)

    def test_generate_secure_secret_no_lowercase(self):
        """Test generating secret without lowercase letters."""
        secret = generate_secure_secret(length=32, include_lowercase=False)

        assert not any(c.islower() for c in secret)

    def test_generate_secure_secret_uppercase_only(self):
        """Test generating secret with uppercase only."""
        secret = generate_secure_secret(
            length=32,
            include_uppercase=True,
            include_lowercase=False,
            include_digits=False,
            include_special=False,
        )

        assert secret.isupper()
        assert secret.isalpha()

    def test_generate_secure_secret_raises_on_no_types(self):
        """Test generation raises when no character types selected."""
        with pytest.raises(ValueError):
            generate_secure_secret(
                include_uppercase=False,
                include_lowercase=False,
                include_digits=False,
                include_special=False,
            )


class TestSecretValidationReport:
    """Tests for secret validation report."""

    def test_validation_report_compliance_calculation(self):
        """Test compliance score calculation."""
        # This test requires environment setup
        # For now, test the report structure
        report = SecretValidationReport(
            is_valid=True, compliance_score=95.0, strength_scores={"SECRET1": 85, "SECRET2": 90}
        )

        assert report.is_valid
        assert report.compliance_score == 95.0
        assert len(report.strength_scores) == 2

    def test_validation_report_formatting(self):
        """Test validation report string formatting."""
        report = SecretValidationReport(
            is_valid=False,
            missing_secrets=["SECRET1: Required"],
            weak_secrets=["SECRET2: Too short"],
            rotation_required=["SECRET3: 100 days ago"],
            strength_scores={"SECRET4": 45},
            compliance_score=65.0,
        )

        report_str = str(report)

        assert "Secret Validation Report" in report_str
        assert "Valid: False" in report_str
        assert "65.0%" in report_str
        assert "SECRET1: Required" in report_str
        assert "SECRET2: Too short" in report_str
        assert "SECRET3: 100 days ago" in report_str
        assert "Weak" in report_str


class TestProductionReadiness:
    """Tests for production readiness checks."""

    def test_production_detection(self):
        """Test production environment detection."""
        # Should not be production by default
        manager = SecretManager()
        assert not manager._is_production

    def test_validate_all_in_development(self):
        """Test validation in development (non-production)."""
        manager = SecretManager()
        report = manager.validate_all()

        # In development, should have high compliance even without secrets
        assert report.compliance_score >= 80

    @pytest.mark.skipif(
        os.getenv("ENVIRONMENT", "").lower() not in ["production", "prod"],
        reason="Only runs in production",
    )
    def test_validate_all_in_production(self):
        """Test validation in production."""
        manager = SecretManager()
        report = manager.validate_all()

        # In production, should require all secrets
        if report.missing_secrets:
            pytest.fail(f"Missing required secrets in production: {report.missing_secrets}")

        assert report.compliance_score >= 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
