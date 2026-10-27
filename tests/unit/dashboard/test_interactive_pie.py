"""UI-2 — the role chip derives from the ENGINE's own rationale."""

from __future__ import annotations

from app.presentation.dashboard.nicegui_app.pages.portfolio import _role_chip


def test_income_engine():
    chip, tone = _role_chip("High-dividend ETF: pays you cash every quarter")
    assert chip == "Income engine"


def test_safety_cushion():
    chip, _ = _role_chip("Bonds keep the ride calm when stocks fall")
    assert chip == "Safety cushion"


def test_growth_booster():
    chip, _ = _role_chip("Captures growth when the market rises")
    assert chip == "Growth booster"


def test_diversifier_fallback():
    chip, _ = _role_chip("Adds a different region to the mix")
    assert chip == "Diversifier"


def test_never_invents_on_empty():
    assert _role_chip("")[0] == "Diversifier"
