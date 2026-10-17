"""
Tests for API key authentication in app/presentation/api/security.py.

Covers the replacement of the placeholder behavior (any 32+ char key was
accepted) with real validation against configured keys:
- Valid configured key authenticates (200)
- Arbitrary 32+ char key is rejected (401) - length alone never authenticates
- AUTH_ENABLED with no keys configured fails closed (401) and logs ONE
  critical error, not one per request
- Single-key fallback via API_KEY
- Bearer tokens are rejected while JWT support is unimplemented
"""

import logging

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.presentation.api import security
from app.presentation.api.security import require_auth

VALID_KEY = "test-api-key-3f9a2c8e11d04b76a5e0c2f19d83b447"
OTHER_KEY_32_CHARS = "x" * 32


@pytest.fixture(autouse=True)
def reset_missing_keys_flag():
    """Reset the one-shot 'no API keys configured' log flag around each test."""
    security._api_keys_missing_logged = False
    yield
    security._api_keys_missing_logged = False


@pytest.fixture
def client():
    """TestClient for a minimal app with one require_auth-protected endpoint."""
    app = FastAPI()

    @app.post("/secure")
    @require_auth()
    async def secure_endpoint(request: Request) -> dict:
        return {"ok": True}

    return TestClient(app)


class TestApiKeyAuthentication:
    """require_auth + get_user_from_request behavior."""

    def test_valid_api_key_authenticates(self, client, monkeypatch):
        """(a) A key matching API_ACCESS_KEYS authenticates -> 200."""
        monkeypatch.setenv("API_ACCESS_KEYS", VALID_KEY)
        response = client.post("/secure", headers={"X-API-Key": VALID_KEY})
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_invalid_32_char_api_key_rejected(self, client, monkeypatch):
        """(b) A 32+ char key that is not configured is rejected -> 401."""
        monkeypatch.setenv("API_ACCESS_KEYS", VALID_KEY)
        response = client.post("/secure", headers={"X-API-Key": OTHER_KEY_32_CHARS})
        assert response.status_code == 401

    def test_any_32_char_key_rejected_when_other_keys_configured(self, client, monkeypatch):
        """Length alone never authenticates, even with several keys configured."""
        monkeypatch.setenv("API_ACCESS_KEYS", f"{VALID_KEY},another-valid-key-4b8c1e0a9d23")
        response = client.post("/secure", headers={"X-API-Key": "a" * 64})
        assert response.status_code == 401

    def test_no_configured_keys_fails_closed(self, client, monkeypatch, caplog):
        """(c) AUTH_ENABLED + no keys configured -> 401 and ONE critical log."""
        monkeypatch.delenv("API_ACCESS_KEYS", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)

        with caplog.at_level(logging.CRITICAL, logger=security.logger.name):
            first = client.post("/secure", headers={"X-API-Key": VALID_KEY})
            second = client.post("/secure", headers={"X-API-Key": VALID_KEY})

        assert first.status_code == 401
        assert second.status_code == 401

        critical_logs = [
            record
            for record in caplog.records
            if record.levelno == logging.CRITICAL and "API_ACCESS_KEYS" in record.message
        ]
        assert len(critical_logs) == 1, "missing-keys error must be logged once, not per request"

    def test_single_api_key_env_fallback(self, client, monkeypatch):
        """API_KEY (single key) is used when API_ACCESS_KEYS is not set."""
        monkeypatch.delenv("API_ACCESS_KEYS", raising=False)
        monkeypatch.setenv("API_KEY", VALID_KEY)
        response = client.post("/secure", headers={"X-API-Key": VALID_KEY})
        assert response.status_code == 200

    def test_missing_api_key_header_rejected(self, client, monkeypatch):
        """No credentials at all -> 401."""
        monkeypatch.setenv("API_ACCESS_KEYS", VALID_KEY)
        response = client.post("/secure")
        assert response.status_code == 401

    def test_bearer_token_rejected_until_jwt_implemented(self, client, monkeypatch):
        """Bearer tokens fail closed while JWT validation is unimplemented."""
        monkeypatch.setenv("API_ACCESS_KEYS", VALID_KEY)
        response = client.post(
            "/secure",
            headers={"Authorization": f"Bearer {VALID_KEY}"},
        )
        assert response.status_code == 401
