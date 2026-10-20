"""Los presets por objetivo del dashboard deben disparar con las claves reales.

Las claves de OBJECTIVES son MAYÚSCULAS; el preset antiguo comparaba en
minúsculas y nunca se activaba desde la UI. `preset_for_goal` es
insensible a mayúsculas y conoce ambos objetivos con estrategia propia.
"""

from __future__ import annotations

from app.presentation.dashboard.nicegui_app.pages.swarm import (
    DIVIDEND_ETF_UNIVERSE,
    LOW_VOL_UNIVERSE,
    OBJECTIVES,
    preset_for_goal,
)


def test_dividend_goal_uses_real_objective_key():
    assert "MAXIMIZAR_DIVIDENDOS" in OBJECTIVES
    assert preset_for_goal("MAXIMIZAR_DIVIDENDOS") == ("dividend_tracking", DIVIDEND_ETF_UNIVERSE)


def test_preset_is_case_insensitive():
    assert preset_for_goal("maximizar_dividendos") == ("dividend_tracking", DIVIDEND_ETF_UNIVERSE)
    assert preset_for_goal("Capital_Preservation") == ("low_volatility", LOW_VOL_UNIVERSE)


def test_capital_preservation_maps_to_low_volatility():
    assert "CAPITAL_PRESERVATION" in OBJECTIVES
    assert preset_for_goal("CAPITAL_PRESERVATION") == ("low_volatility", LOW_VOL_UNIVERSE)


def test_goals_without_preset_return_none():
    assert preset_for_goal("MAXIMIZAR_CAPITAL") is None
    assert preset_for_goal(None) is None
    assert preset_for_goal("") is None
