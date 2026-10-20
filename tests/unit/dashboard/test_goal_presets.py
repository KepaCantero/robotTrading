"""Los presets por objetivo del dashboard deben disparar con las claves reales.

Las claves de OBJECTIVES son MAYÚSCULAS; el preset antiguo comparaba en
minúsculas y nunca se activaba desde la UI. `preset_for_goal` es
insensible a mayúsculas y conoce ambos objetivos con estrategia propia.
"""

from __future__ import annotations

from decimal import Decimal as D

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


class TestStrategyQualityInVerdict:
    """Los baremos de calidad (Chan 2013) del StrategyValidator entran al T5."""

    def test_deep_drawdown_downgrades_approve_to_conditional(self):
        import asyncio

        from app.services.validation_engine.models import ValidationRequest
        from app.services.validation_engine.validation_engine import ValidationEngine

        req = ValidationRequest(
            profile_id="q",
            input_id="q",
            initial_capital=D("100000"),
            target_monthly_return_eur=D("150"),
            backtest_feasibility_ratio=D("1.5"),
            backtest_sharpe_ratio=D("1.2"),
            backtest_max_drawdown_pct=D("30"),
            walk_forward_passed=True,
        )
        res = asyncio.run(ValidationEngine().validate(req))
        assert res.overall_recommendation == "CONDITIONAL"
        assert any("25%" in w for w in res.warnings)

    def test_low_sharpe_warns_but_does_not_block(self):
        import asyncio

        from app.services.validation_engine.models import ValidationRequest
        from app.services.validation_engine.validation_engine import ValidationEngine

        req = ValidationRequest(
            profile_id="q",
            input_id="q",
            initial_capital=D("100000"),
            target_monthly_return_eur=D("150"),
            backtest_feasibility_ratio=D("1.4"),
            backtest_sharpe_ratio=D("0.21"),
            backtest_max_drawdown_pct=D("13"),
            walk_forward_passed=True,
        )
        res = asyncio.run(ValidationEngine().validate(req))
        assert res.passed is True
        assert any("Sharpe" in w for w in res.warnings)
