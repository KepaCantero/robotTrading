"""Fase 1 acceptance: full HTTP authentication matrix against the REAL app.

Plan `docs/plans/PLAN_PRODUCCION_PAPER_IBKR.md` (Fase 1) — hallazgos A01,
A02, A13, A14 y A15:

- Anonymous or invalid key on a protected router -> 401 (never 500).
- Valid key without the required role -> 403 (roles now travel with the
  principal; API keys are no longer roleless).
- Valid key with the role -> passes authorization (any business status
  except 401/403).
- /health stays public for readiness probes.
- The old hard-coded development key never authenticates, and with no keys
  configured the app fails closed.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.main import app
from app.presentation.api import security
from app.presentation.api.portfolio import get_portfolio_service
from app.presentation.api.security import require_auth
from app.presentation.api.signals import get_signal_scorer_service
from app.services.live_trading.order_manager import get_order_manager_for_api

VIEWER_KEY = "matrix-viewer-key-4c1d8e9b25a84f06b3d8e7f2a6c5d901"  # pragma: allowlist secret  (clave sintética de test)
TRADER_KEY = "matrix-trader-key-7f2a4c8e11d04b76a5e0c2f19d83b447"  # pragma: allowlist secret  (clave sintética de test; roles por defecto)
ADMIN_KEY = "matrix-admin-key-9d234b8c1e0a7d23f5a2c8e4b1d09f63"  # pragma: allowlist secret  (clave sintética de test)
ALL_KEYS = f"{VIEWER_KEY},{TRADER_KEY},{ADMIN_KEY}"
KEY_ROLES = json.dumps(
    {
        VIEWER_KEY: ["viewer"],
        ADMIN_KEY: ["admin", "trader"],
    }
)

HEADERS = {
    "anon": {},
    "invalid": {"X-API-Key": "totally-wrong-key"},
    "viewer": {"X-API-Key": VIEWER_KEY},
    "trader": {"X-API-Key": TRADER_KEY},
    "admin": {"X-API-Key": ADMIN_KEY},
}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch):
    """Known keys + role mapping for every test; no stray env leaks."""
    monkeypatch.setenv("API_ACCESS_KEYS", ALL_KEYS)
    monkeypatch.setenv("API_KEY_ROLES", KEY_ROLES)
    monkeypatch.delenv("API_KEY", raising=False)
    security._api_keys_missing_logged = False
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    """TestClient on the real app with business dependencies stubbed.

    Authorization outcomes (401/403 vs pass) are what this module asserts;
    authorized requests only need to REACH the endpoint, so stubs return
    minimal valid shapes. raise_server_exceptions=False keeps an unexpected
    business 500 distinguishable from 401/403 instead of raising in-test.
    """
    portfolio_service = Mock()
    portfolio_service.reset_circuit_breaker.return_value = None
    portfolio_service.get_circuit_breaker_status.return_value = {}

    scorer = Mock()
    scorer.get_signals_by_symbol = AsyncMock(return_value=[])

    order_manager = Mock()
    placed = Mock()
    placed.order_id = "ord-matrix-1"
    order_manager.place_order = AsyncMock(return_value=placed)

    app.dependency_overrides[get_portfolio_service] = lambda: portfolio_service
    app.dependency_overrides[get_signal_scorer_service] = lambda: scorer
    app.dependency_overrides[get_order_manager_for_api] = lambda: order_manager

    return TestClient(app, raise_server_exceptions=False)


def _authorized(response) -> bool:
    """The request passed authentication AND authorization."""
    return response.status_code not in (401, 403)


# ---------------------------------------------------------------------------
# The matrix: route x credential -> expected outcome
# ---------------------------------------------------------------------------

MATRIX = [
    # (method, path, kwargs, per-credential expectation or None for uniform)
    (
        "get",
        "/health",
        {},
        {"anon": 200, "invalid": 200, "viewer": 200, "trader": 200, "admin": 200},
    ),
    # Router-level gate (any principal may read)
    (
        "get",
        "/live-trading/status",
        {},
        {"anon": 401, "invalid": 401, "viewer": "pass", "trader": "pass", "admin": "pass"},
    ),
    (
        "get",
        "/live-trading/risk/limits",
        {},
        {"anon": 401, "invalid": 401, "viewer": "pass", "trader": "pass", "admin": "pass"},
    ),
    # Trader gate (execution)
    (
        "post",
        "/live-trading/orders",
        {"params": {"symbol": "AAPL", "side": "buy", "quantity": 1}},
        {"anon": 401, "invalid": 401, "viewer": 403, "trader": "pass", "admin": "pass"},
    ),
    (
        "post",
        "/signals/execute/AAPL",
        {},
        {"anon": 401, "invalid": 401, "viewer": 403, "trader": "pass", "admin": "pass"},
    ),
    # Admin gate (resets, thresholds, limits)
    (
        "post",
        "/portfolio/circuit-breakers/portfolio/reset",
        {},
        {"anon": 401, "invalid": 401, "viewer": 403, "trader": 403, "admin": "pass"},
    ),
    (
        "post",
        "/signals/thresholds",
        {"params": {"confidence_threshold": 50.0, "liquidity_threshold": 40.0}},
        {"anon": 401, "invalid": 401, "viewer": 403, "trader": 403, "admin": "pass"},
    ),
]


@pytest.mark.parametrize("method,path,kwargs,expectations", MATRIX)
@pytest.mark.parametrize("credential", list(HEADERS))
def test_auth_matrix(client: TestClient, method, path, kwargs, expectations, credential):
    """Every route x credential combination matches the expected outcome."""
    response = getattr(client, method)(path, headers=HEADERS[credential], **kwargs)
    expected = expectations[credential]
    if expected == "pass":
        assert _authorized(response), (
            f"{method.upper()} {path} with {credential} got {response.status_code}: "
            f"{response.text[:200]} — should pass authz"
        )
    else:
        assert response.status_code == expected, (
            f"{method.upper()} {path} with {credential} got {response.status_code}: "
            f"{response.text[:200]}"
        )


# ---------------------------------------------------------------------------
# Regressions for the specific audited defects
# ---------------------------------------------------------------------------


class TestRegressions:
    def test_anonymous_gets_401_not_500(self, client: TestClient):
        """A15: missing credentials answer 401, never an internal error."""
        response = client.get("/live-trading/status")
        assert response.status_code == 401
        assert response.headers.get("www-authenticate")

    def test_dev_key_never_authenticates(self, monkeypatch, client: TestClient):
        """A02: the hard-coded development key is dead, with or without
        other keys configured."""
        monkeypatch.setenv("API_ACCESS_KEYS", "")
        response = client.get("/live-trading/status", headers={"X-API-Key": "dev-api-key-12345"})
        assert response.status_code == 401

    def test_no_keys_configured_fails_closed(self, monkeypatch, client: TestClient):
        """Operational config without credentials rejects everything."""
        monkeypatch.setenv("API_ACCESS_KEYS", "")
        monkeypatch.delenv("API_KEY", raising=False)
        response = client.get("/live-trading/status")
        assert response.status_code == 401

    def test_unknown_path_still_404(self, client: TestClient):
        """Protect-by-default must not turn 404s into auth errors."""
        assert client.get("/nonexistent_endpoint").status_code == 404

    def test_http_request_named_parameter_authenticates(self, monkeypatch):
        """A14: require_auth finds Request even when declared as http_request."""

        mini = FastAPI()

        @mini.post("/secure")
        @require_auth()
        async def secure(http_request: Request) -> dict:
            del http_request
            return {"ok": True}

        monkeypatch.setenv("API_ACCESS_KEYS", TRADER_KEY)
        c = TestClient(mini)
        assert c.post("/secure", headers=HEADERS["trader"]).status_code == 200
        assert c.post("/secure", headers=HEADERS["invalid"]).status_code == 401
        assert c.post("/secure").status_code == 401

    def test_api_key_roles_reach_decorator(self, monkeypatch):
        """A13: a principal from an API key carries roles, so role-gated
        decorators no longer reject every valid key."""
        mini = FastAPI()

        @mini.post("/trade")
        @require_auth(roles=["trader", "admin"])
        async def trade(request: Request) -> dict:
            del request
            return {"ok": True}

        monkeypatch.setenv("API_ACCESS_KEYS", ALL_KEYS)
        monkeypatch.setenv("API_KEY_ROLES", KEY_ROLES)
        c = TestClient(mini)
        assert c.post("/trade", headers=HEADERS["trader"]).status_code == 200
        assert c.post("/trade", headers=HEADERS["viewer"]).status_code == 403
