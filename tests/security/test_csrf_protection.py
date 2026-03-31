"""
Tests for app/security/csrf_protection.py
"""

import time

import pytest
from fastapi import HTTPException

from app.security.web_security.csrf_protection import (
    CSRFTokenManager,
    DoubleSubmitCookieCSRF,
    generate_csrf_token,
    get_csrf_token_manager,
    validate_csrf_token,
)


class TestCSRFTokenManager:
    """Test CSRF token generation and validation."""

    def test_generate_token(self):
        """Test token generation."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        token = manager.generate_token()

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_with_user_id(self):
        """Test token generation with user ID."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        token = manager.generate_token(user_id="user123")

        assert token is not None
        assert isinstance(token, str)

    def test_validate_valid_token(self):
        """Test validating a valid token."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        token = manager.generate_token()

        result = manager.validate_token(token)
        assert result is True

    def test_validate_token_with_user_id(self):
        """Test validating token with user ID."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        token = manager.generate_token(user_id="user123")

        result = manager.validate_token(token, user_id="user123")
        assert result is True

    def test_validate_token_user_mismatch(self):
        """Test token validation with user mismatch."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        token = manager.generate_token(user_id="user123")

        with pytest.raises(HTTPException) as exc_info:
            manager.validate_token(token, user_id="user456")

        assert exc_info.value.status_code == 403

    def test_validate_invalid_token(self):
        """Test validating an invalid token."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")

        with pytest.raises(HTTPException) as exc_info:
            manager.validate_token("invalid_token")

        assert exc_info.value.status_code == 403

    def test_validate_empty_token(self):
        """Test validating an empty token."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")

        with pytest.raises(HTTPException) as exc_info:
            manager.validate_token("")

        assert exc_info.value.status_code == 403

    def test_validate_none_token(self):
        """Test validating None token."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")

        with pytest.raises(HTTPException) as exc_info:
            manager.validate_token(None)

        assert exc_info.value.status_code == 403

    def test_token_expiration(self):
        """Test token expiration."""
        manager = CSRFTokenManager(
            secret_key="test_secret_key_32_characters_long", token_expiry=1  # 1 second
        )
        token = manager.generate_token()

        # Wait for token to expire
        time.sleep(2)

        with pytest.raises(HTTPException) as exc_info:
            manager.validate_token(token)

        assert exc_info.value.status_code == 403
        assert "expired" in str(exc_info.value.detail).lower()

    def test_rotate_token(self):
        """Test token rotation."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        old_token = manager.generate_token()
        new_token = manager.rotate_token(old_token)

        assert new_token != old_token
        assert isinstance(new_token, str)

    def test_token_uniqueness(self):
        """Test that tokens are unique."""
        manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        tokens = [manager.generate_token() for _ in range(100)]

        # All tokens should be unique
        assert len(set(tokens)) == 100


class TestDoubleSubmitCookieCSRF:
    """Test double-submit cookie CSRF protection."""

    def test_generate_token_for_request(self):
        """Test generating token for request."""
        token_manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        csrf = DoubleSubmitCookieCSRF(token_manager)

        token = csrf.generate_token_for_request()
        assert token is not None
        assert isinstance(token, str)

    def test_validate_request_safe_methods(self):
        """Test that safe methods skip validation."""
        from unittest.mock import Mock

        token_manager = CSRFTokenManager(secret_key="test_secret_key_32_characters_long")
        csrf = DoubleSubmitCookieCSRF(token_manager)

        for method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
            request = Mock()
            request.method = method
            result = csrf.validate_request(request)
            assert result is True


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_csrf_token_manager(self):
        """Test getting global token manager."""
        manager = get_csrf_token_manager()
        assert manager is not None
        assert isinstance(manager, CSRFTokenManager)

    def test_generate_csrf_token(self):
        """Test generating CSRF token."""
        token = generate_csrf_token()
        assert token is not None
        assert isinstance(token, str)

    def test_validate_csrf_token_valid(self):
        """Test validating valid CSRF token."""
        token = generate_csrf_token()
        result = validate_csrf_token(token)
        assert result is True

    def test_validate_csrf_token_invalid(self):
        """Test validating invalid CSRF token."""
        with pytest.raises(HTTPException):
            validate_csrf_token("invalid_token")
