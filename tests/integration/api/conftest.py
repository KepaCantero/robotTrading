"""Fixtures de autenticación para los tests de API de integración.

Los routers están protegidos por defecto (Fase 1): sin credencial devuelven
401 y sin rol suficiente 403. Los tests que validan lógica de negocio (no la
seguridad) deben ir autenticados; aquí key-1 actúa como clave operadora
(admin) y key-2 conserva los roles por defecto (viewer+trader). La matriz
completa de permisos vive en tests/api/test_auth_matrix.py.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_API_KEYS = "test-integration-key-1,test-integration-key-2"  # pragma: allowlist secret  (claves sintéticas de test)


@pytest.fixture(autouse=True)
def _api_keys_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garantiza claves de API y roles conocidos durante los tests."""
    # pragma: allowlist secret — nombres de variables de entorno, no secretos
    monkeypatch.setenv("API_ACCESS_KEYS", TEST_API_KEYS)  # pragma: allowlist secret
    monkeypatch.setenv(
        "API_KEY_ROLES",  # pragma: allowlist secret
        json.dumps({"test-integration-key-1": ["admin", "trader", "viewer"]}),
    )


@pytest.fixture
def client() -> TestClient:
    """Cliente de test autenticado con la clave operadora (admin)."""
    return TestClient(app, headers={"X-API-Key": "test-integration-key-1"})
