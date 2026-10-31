"""Los presets por objetivo del dashboard deben disparar con las claves reales.

Las claves de OBJECTIVES son MAYÚSCULAS; el preset antiguo comparaba en
minúsculas y nunca se activaba desde la UI. `preset_for_goal` es
insensible a mayúsculas y conoce ambos objetivos con estrategia propia.
"""

from __future__ import annotations

from decimal import Decimal as D

from app.presentation.dashboard.nicegui_app.pages.swarm import (
    LONG_HORIZON_MONTHS,
    LOW_VOL_UNIVERSE,
    OBJECTIVES,
    horizon_months,
    period_months,
    preset_for_goal,
)


def test_dividend_goal_defaults_to_the_passing_passive():
    """User (2026-10-27): 'dejalo por default la que pasa' — the dividend
    preset is the static passive with the AUTOMATIC universe (None), the
    configuration the system's own verdict recommends every run."""
    assert "MAXIMIZAR_DIVIDENDOS" in OBJECTIVES
    assert preset_for_goal("MAXIMIZAR_DIVIDENDOS") == ("static_ew", None)


def test_preset_is_case_insensitive():
    assert preset_for_goal("maximizar_dividendos") == ("static_ew", None)
    assert preset_for_goal("Capital_Preservation") == ("low_volatility", LOW_VOL_UNIVERSE)


def test_capital_preservation_maps_to_low_volatility():
    assert "CAPITAL_PRESERVATION" in OBJECTIVES
    assert preset_for_goal("CAPITAL_PRESERVATION") == ("low_volatility", LOW_VOL_UNIVERSE)


def test_goals_without_preset_return_none():
    assert preset_for_goal("MAXIMIZAR_CAPITAL") is None
    assert preset_for_goal(None) is None
    assert preset_for_goal("") is None


def test_acumular_preset_is_automatic_whole_goal_universe():
    """ACUMULAR (30-10): regla del dueño — por defecto TODO el universo
    del objetivo vía pantalla AUTOMÁTICA (None), como dividends. La
    pantalla del corpus decide por ventana: en 10y entran los UCITS que
    cubren (EUNL/IUSQ/EIMI/VHYL/IDVY + IBGS), en ventanas cortas también
    VWCE/QDIV. Nada de listas clavadas por defecto."""
    assert "ACUMULAR" in OBJECTIVES
    assert preset_for_goal("ACUMULAR") == ("static_ew", None)
    assert preset_for_goal("acumular") == preset_for_goal("ACUMULAR")


def test_vivir_preset_is_automatic_too():
    """Mismo principio para VIVIR_DE_LA_CARTERA: el conjunto UCITS lo
    decide la pantalla del objetivo por ventana, no una lista fija."""
    assert preset_for_goal("VIVIR_DE_LA_CARTERA") == ("static_ew", None)


class TestLongHorizonUniverse:
    """Un run de 20 años sobre VIG/SCHD (10 años de histórico) se trunca en
    silencio a la década disponible; con horizonte largo el preset de
    dividendos cambia al universo con histórico desde 2003-2007."""

    def test_passive_preset_stays_automatic_at_any_horizon(self):
        # static_ew + universo AUTOMÁTICO: la pantalla del corpus decide
        # por ventana (miembros que cubren), no una lista curada.
        assert preset_for_goal("MAXIMIZAR_DIVIDENDOS", 120) == ("static_ew", None)
        assert preset_for_goal("MAXIMIZAR_DIVIDENDOS", LONG_HORIZON_MONTHS) == (
            "static_ew",
            None,
        )

    def test_goal_without_deep_universe_is_unchanged(self):
        assert preset_for_goal("CAPITAL_PRESERVATION", 240) == ("low_volatility", LOW_VOL_UNIVERSE)


class TestHorizonIsThePeriod:
    """El horizonte de inversión ES la ventana del backtest (sin campo aparte)."""

    def test_horizon_months_from_window(self):
        assert horizon_months("2016-10-17", "2026-10-17") == 120
        assert horizon_months("2024-01-01", "2024-07-01") == 6
        assert horizon_months("2024-01-01", "2024-01-05") == 1

    def test_period_months_for_presets(self):
        assert period_months("6m", None, None) == 6
        assert period_months("1y", None, None) == 12
        assert period_months("10y", None, None) == 120
        assert period_months("unknown", None, None) is None

    def test_all_available_data_counts_as_long_horizon(self):
        assert period_months("max", None, None) >= LONG_HORIZON_MONTHS

    def test_custom_dates_measured_directly(self):
        assert period_months("custom", "2008-01-02", "2026-01-02") == 216
        assert period_months("custom", "2026-01-02", "2008-01-02") is None
        assert period_months("custom", None, "2026-01-02") is None


class TestStrategyQualityInVerdict:
    """Los baremos de calidad (Chan 2013) del StrategyValidator entran al T5."""

    def test_deep_drawdown_downgrades_approve_to_conditional(self):
        """DD por ENCIMA de la tolerancia declarada degrada; dentro, no.

        Sin perfil (tolerancia 30%): -30% está DENTRO → sigue APPROVE con
        aviso informativo del baremo Chan; -35% la supera → CONDITIONAL.
        """
        import asyncio

        from app.services.validation_engine.models import ValidationRequest
        from app.services.validation_engine.validation_engine import ValidationEngine

        base = dict(
            profile_id="q",
            input_id="q",
            initial_capital=D("100000"),
            target_monthly_return_eur=D("150"),
            backtest_feasibility_ratio=D("1.5"),
            backtest_sharpe_ratio=D("1.2"),
            walk_forward_passed=True,
        )
        dentro = asyncio.run(
            ValidationEngine().validate(
                ValidationRequest(**base, backtest_max_drawdown_pct=D("30"))
            )
        )
        assert dentro.overall_recommendation == "APPROVE", "30% dentro de tolerancia 30%"
        fuera = asyncio.run(
            ValidationEngine().validate(
                ValidationRequest(**base, backtest_max_drawdown_pct=D("35"))
            )
        )
        assert fuera.overall_recommendation == "CONDITIONAL", "35% supera tolerancia 30%"
        assert any("25%" in w for w in fuera.warnings), "aviso informativo del baremo Chan"

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
