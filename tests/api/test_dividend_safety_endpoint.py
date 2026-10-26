"""Bloque 2 (T2.3) — /dividends/safety: the report the backtest uses,
served over the API with the F1 auth matrix intact (401 without a key).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.presentation.api import security

VIEWER_KEY = "safety-viewer-key-4c1d8e9b25a84f06b3d8e7f2a6c5d901"  # pragma: allowlist secret  (clave sintética de test)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("API_ACCESS_KEYS", VIEWER_KEY)
    monkeypatch.delenv("API_KEY", raising=False)
    security._api_keys_missing_logged = False
    yield


def _h():
    return {"X-API-Key": VIEWER_KEY}


def test_anonymous_gets_401():
    assert client.get("/dividends/safety?tickers=KO").status_code == 401


def test_report_carries_formula_factors_and_verdict():
    r = client.get(
        "/dividends/safety",
        params={"tickers": "MSFT,LUMN", "as_of": "2023-12-31", "min_score": "60"},
        headers=_h(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["formula"]["cobertura"] == 35  # public formula
    assert "MSFT" in body["passes_filter"]
    reports = {rep["ticker"]: rep for rep in body["reports"]}
    assert reports["MSFT"]["computable"] is True
    assert reports["MSFT"]["formula"]  # per-symbol factors
    assert "limitation" in body


def test_too_many_tickers_rejected():
    many = ",".join(f"T{i}" for i in range(51))
    assert client.get(f"/dividends/safety?tickers={many}", headers=_h()).status_code == 422
