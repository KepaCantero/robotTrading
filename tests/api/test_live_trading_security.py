"""
Security tests for the /live-trading router (app/presentation/api/live_trading.py).

Covers:
- Every write endpoint (POST/PATCH/DELETE) returns 401 without valid auth
- Absolute caps on PATCH /risk/limits: values above the cap are rejected
  with 422 (not clamped) and never applied
- Valid API key allows write operations
"""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.api.live_trading import (
    MAX_DAILY_LOSS_LIMIT,
    MAX_DRAWDOWN_LIMIT,
    MAX_LEVERAGE_LIMIT,
    MAX_POSITION_PCT_LIMIT,
    get_alert_to_trade_mapper,
    get_broker_connector,
    get_order_manager_for_api,
    get_risk_gates,
    get_trading_bridge_orchestrator,
    router,
)

VALID_KEY = "live-trading-test-key-7c1d4e9b25a84f06b3d8e7f2a6c5d901"  # pragma: allowlist secret  (clave sintética de test)

# Every write endpoint of the router: (method, path, request kwargs)
WRITE_ENDPOINTS = [
    ("post", "/live-trading/start", {}),
    ("post", "/live-trading/stop", {}),
    (
        "post",
        "/live-trading/orders",
        {"params": {"symbol": "AAPL", "side": "buy", "quantity": 1}},
    ),
    ("delete", "/live-trading/orders/ord-1", {}),
    ("post", "/live-trading/orders/cancel-all", {}),
    (
        "post",
        "/live-trading/risk/validate",
        {"params": {"symbol": "AAPL", "side": "buy", "quantity": 1}},
    ),
    ("patch", "/live-trading/risk/limits", {"params": {"max_daily_loss": 0.05}}),
    ("post", "/live-trading/rules", {"json": {"rule_id": "r1", "alert_rule_id": "a1"}}),
    ("delete", "/live-trading/rules/r1", {}),
]


@pytest.fixture
def risk_gates():
    """Mock RiskGates with synchronous setters."""
    gates = Mock()
    gates.max_position_size = Decimal("50000")
    gates.max_leverage = Decimal("2.0")
    gates.max_concentration = Decimal("0.30")
    gates.max_daily_loss = Decimal("0.05")
    gates.max_drawdown = Decimal("0.15")
    gates.min_cash_reserve = Decimal("0.20")
    return gates


@pytest.fixture
def client(monkeypatch, risk_gates):
    """TestClient for the /live-trading router with mocked dependencies.

    A valid API key is configured for authenticated requests.
    """
    monkeypatch.setenv("API_ACCESS_KEYS", VALID_KEY)

    app = FastAPI()
    app.include_router(router)

    orchestrator = Mock()
    orchestrator.start = AsyncMock(return_value=None)
    orchestrator.stop = AsyncMock(return_value=None)

    order_manager = Mock()
    placed = Mock()
    placed.order_id = "ord-1"
    order_manager.place_order = AsyncMock(return_value=placed)
    order_manager.cancel_order = AsyncMock(return_value=True)
    order_manager.cancel_all_orders = AsyncMock(return_value=0)

    broker = Mock()
    mapper = Mock()

    app.dependency_overrides[get_trading_bridge_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_order_manager_for_api] = lambda: order_manager
    app.dependency_overrides[get_risk_gates] = lambda: risk_gates
    app.dependency_overrides[get_broker_connector] = lambda: broker
    app.dependency_overrides[get_alert_to_trade_mapper] = lambda: mapper

    return TestClient(app)


class TestLiveTradingWriteEndpointsRequireAuth:
    """(e) Write endpoints without auth -> 401."""

    @pytest.mark.parametrize(("method", "path", "request_kwargs"), WRITE_ENDPOINTS)
    def test_write_endpoint_without_auth_returns_401(self, client, method, path, request_kwargs):
        response = getattr(client, method)(path, **request_kwargs)
        assert response.status_code == 401, f"{method.upper()} {path} must require auth"

    def test_write_endpoint_with_wrong_32_char_key_returns_401(self, client):
        response = client.post(
            "/live-trading/start",
            headers={"X-API-Key": "x" * 32},
        )
        assert response.status_code == 401

    def test_write_endpoint_with_valid_key_returns_200(self, client):
        response = client.post("/live-trading/start", headers={"X-API-Key": VALID_KEY})
        assert response.status_code == 200
        assert response.json()["status"] == "started"


class TestRiskLimitsAbsoluteCaps:
    """(d) PATCH /risk/limits rejects values above the absolute caps."""

    @pytest.mark.parametrize(
        ("field", "cap", "value"),
        [
            ("max_daily_loss", MAX_DAILY_LOSS_LIMIT, 0.5),
            ("max_drawdown", MAX_DRAWDOWN_LIMIT, 0.31),
            ("max_leverage", MAX_LEVERAGE_LIMIT, 10.0),
            ("max_concentration", MAX_POSITION_PCT_LIMIT, 0.9),
        ],
    )
    def test_value_above_cap_rejected_with_422(self, client, risk_gates, field, cap, value):
        response = client.patch(
            "/live-trading/risk/limits",
            params={field: value},
            headers={"X-API-Key": VALID_KEY},
        )
        assert response.status_code == 422
        assert field in response.json()["detail"]["message"]
        # The limit must not be applied (reject, never clamp)
        risk_gates.set_max_daily_loss.assert_not_called()
        risk_gates.set_max_leverage.assert_not_called()
        risk_gates.set_max_drawdown.assert_not_called()

    def test_rejection_is_atomic_when_other_fields_valid(self, client, risk_gates):
        """A capped field rejects the whole request even alongside valid fields."""
        response = client.patch(
            "/live-trading/risk/limits",
            params={"max_daily_loss": 0.05, "max_leverage": 99.0},
            headers={"X-API-Key": VALID_KEY},
        )
        assert response.status_code == 422
        risk_gates.set_max_daily_loss.assert_not_called()
        risk_gates.set_max_leverage.assert_not_called()

    def test_values_within_caps_are_applied(self, client, risk_gates):
        response = client.patch(
            "/live-trading/risk/limits",
            params={"max_daily_loss": 0.05, "max_leverage": 2.0},
            headers={"X-API-Key": VALID_KEY},
        )
        assert response.status_code == 200
        risk_gates.set_max_daily_loss.assert_called_once_with(Decimal("0.05"))
        risk_gates.set_max_leverage.assert_called_once_with(Decimal("2.0"))
