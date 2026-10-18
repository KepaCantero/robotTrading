"""Fixtures de autenticación para los tests de API de integración.

Los endpoints usan `require_auth`; sin credencial devuelven 401 y los tests
que validan lógica de negocio (no la seguridad) deben ir autenticados.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_API_KEYS = "test-integration-key-1,test-integration-key-2"


@pytest.fixture(autouse=True)
def _api_keys_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garantiza claves de API conocidas durante los tests de integración."""
    monkeypatch.setenv("API_ACCESS_KEYS", TEST_API_KEYS)


@pytest.fixture
def client() -> TestClient:
    """Cliente de test autenticado con la clave primaria de test."""
    return TestClient(app, headers={"X-API-Key": "test-integration-key-1"})
