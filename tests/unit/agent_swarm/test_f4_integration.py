"""Fase 4 integration fixes (hallazgos D02/D11).

- D02: a dividend request without an explicit strategy runs
  dividend_tracking — never the old mean_reversion default; an explicit
  strategy still wins (backend and frontend resolve identically).
- D11: the optimizer budget covers every axis value (the first-12 slice
  never left rebalance_days=63).
"""

from __future__ import annotations

import itertools

from app.services.agent_swarm.executor import Capa2PipelineExecutor
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
