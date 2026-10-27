"""Fase 4 integration fixes (hallazgos D02/D11).

- D02: a dividend request without an explicit strategy runs
  dividend_tracking — never the old mean_reversion default; an explicit
  strategy still wins (backend and frontend resolve identically).
- D11: the optimizer budget covers every axis value (the first-12 slice
  never left rebalance_days=63).
"""

from __future__ import annotations

import itertools
from types import SimpleNamespace

from app.services.agent_swarm.executor import Capa2PipelineExecutor, _strategy_overrides_from
from app.services.agent_swarm.optimizer import _stratified_combos


def _ctx(objective: str, strategy=None, modules=None):
    from types import SimpleNamespace

    return SimpleNamespace(
        request=SimpleNamespace(objetivo_inversion=objective, strategy=strategy),
        param_result=(
            SimpleNamespace(
                parameter_set=SimpleNamespace(module_parameters={m: {} for m in modules})
            )
            if modules
            else None
        ),
    )


class TestResolveStrategy:
    def test_dividend_goal_without_strategy_runs_dividend_tracking(self):
        executor = Capa2PipelineExecutor.__new__(Capa2PipelineExecutor)  # no __init__ wiring
        assert executor._resolve_strategy(_ctx("MAXIMIZAR_DIVIDENDOS")) == "dividend_tracking"

    def test_capital_preservation_maps_to_low_volatility(self):
        executor = Capa2PipelineExecutor.__new__(Capa2PipelineExecutor)
        assert executor._resolve_strategy(_ctx("CAPITAL_PRESERVATION")) == "low_volatility"

    def test_explicit_strategy_overrides_everything(self):
        executor = Capa2PipelineExecutor.__new__(Capa2PipelineExecutor)
        resolved = executor._resolve_strategy(
            _ctx("MAXIMIZAR_DIVIDENDOS", strategy="static_ew", modules=["low_volatility"])
        )
        assert resolved == "static_ew"

    def test_t31_module_beats_goal_fallback(self):
        executor = Capa2PipelineExecutor.__new__(Capa2PipelineExecutor)
        resolved = executor._resolve_strategy(
            _ctx("MAXIMIZAR_DIVIDENDOS", modules=["pairs_trading"])
        )
        assert resolved == "pairs_trading"

    def test_unknown_goal_falls_back_to_momentum(self):
        executor = Capa2PipelineExecutor.__new__(Capa2PipelineExecutor)
        assert executor._resolve_strategy(_ctx("OTRA_COSA")) == "momentum_modular"


class TestStrategyOverrides:
    """D03: T3.1 module parameters reach the engine as strategy overrides."""

    def test_module_specific_passthrough_and_position_cap_mapped(self):
        # max_position_size es FRACCIÓN 0-1 (contrato de module_parameters.yaml
        # y trading_config: "Maximum position size (0-1)") — nunca un porcentaje.
        cfg = SimpleNamespace(
            max_position_size=0.10,  # 10% per position
            module_specific={"rebalance_days": 60, "satellite_top_k": 3},
        )
        overrides = _strategy_overrides_from({"dividend_tracking": cfg}, "dividend_tracking")
        assert overrides["rebalance_days"] == 60
        assert overrides["satellite_top_k"] == 3
        assert overrides["weight_cap"] == 0.10  # el límite del perfil CAPA los pesos

    def test_weight_cap_never_lands_below_engine_position_floor(self):
        # Regresión del bug /100: 0.10 (10%) se convertía en 0.001, la
        # estrategia lo setattr-eaba tras su clamp, suggested_max_position_size
        # hacía ceil(0.1)/100=1% y el validador del motor (piso 5%) rechazaba
        # TODAS las compras → runs REJECTED con 0 trades.
        from decimal import Decimal

        from app.domain.strategies.dividend_core_satellite import DividendCoreSatelliteStrategy

        cfg = SimpleNamespace(max_position_size=Decimal("0.10"), module_specific={})
        overrides = _strategy_overrides_from({"dividend_tracking": cfg}, "dividend_tracking")
        strategy = DividendCoreSatelliteStrategy(
            {"name": "d", "enabled": True, "symbols": ["SCHD", "VIG", "VYMI"]}
        )
        for key, value in overrides.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        floor = 0.05  # validator_min_position_pct del motor
        assert strategy.suggested_max_position_size >= floor

    def test_falls_back_to_first_module_when_strategy_absent(self):
        cfg = SimpleNamespace(max_position_size=0.05, module_specific={"lookback_days": 126})
        overrides = _strategy_overrides_from({"other_module": cfg}, "dividend_tracking")
        assert overrides["lookback_days"] == 126

    def test_empty_when_no_modules(self):
        assert _strategy_overrides_from({}, "dividend_tracking") == {}
        assert _strategy_overrides_from(None, "dividend_tracking") == {}

    def test_weight_cap_honored_by_strategy(self):
        from datetime import datetime

        from app.domain.strategies.dividend_core_satellite import DividendCoreSatelliteStrategy

        s = DividendCoreSatelliteStrategy(
            {"name": "d", "enabled": True, "symbols": ["SCHD", "VIG"], "weight_cap": 0.10}
        )
        weights = s._compute_weights({"SCHD", "VIG"}, datetime.utcnow())
        assert max(weights.values()) <= 0.1001  # el tope del perfil manda
        assert sum(weights.values()) > 0.15  # la redistribución no evapora manga


class TestStratifiedCombos:
    GRID = {
        "rebalance_days": [63, 126, 189],
        "satellite_top_k": [2, 3],
        "skip_recent_days": [10, 20, 30],
        "core_share": [0.4, 0.5],
        "entry": [0.0, 0.02],
        "exit": [-0.01, -0.02],
    }

    def test_every_first_axis_value_explored(self):
        combos = list(itertools.product(*self.GRID.values()))
        picked = _stratified_combos(combos, 12)
        rebalance_values = {combo[0] for combo in picked}
        assert rebalance_values == {63, 126, 189}  # the old slice saw only 63

    def test_budget_respected_and_order_preserved(self):
        combos = list(itertools.product(*self.GRID.values()))
        picked = _stratified_combos(combos, 12)
        assert len(picked) <= 12
        assert picked == sorted(picked, key=combos.index)  # stable order

    def test_no_cap_needed_when_under_budget(self):
        combos = [(1,), (2,), (3,)]
        assert _stratified_combos(combos, 10) == combos
