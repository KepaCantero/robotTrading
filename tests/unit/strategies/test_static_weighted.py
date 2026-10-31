"""static_weighted — the two-fund passive whose equity/bond split the
optimizer SEARCHES (owner 31-10: 'debería buscarme tú el mejor peso')."""

from __future__ import annotations

from app.domain.strategies.static_weighted import StaticWeightedStrategy


def _strategy(universe: list[str], equity_weight: float = 0.75) -> StaticWeightedStrategy:
    return StaticWeightedStrategy({"symbols": universe, "equity_weight": equity_weight})


class TestWeights:
    def test_two_fund_split(self):
        s = _strategy(["VWCE", "AGGH.AS"], 0.75)
        assert s._position_weight("VWCE") == 0.7425  # 0.75 × 0.99 exposure
        assert s._position_weight("AGGH.AS") == 0.2475

    def test_bond_seat_detected_by_table(self):
        s = _strategy(["EUNL.DE", "IBGS.AS"], 0.6)
        assert s._position_weight("EUNL.DE") > s._position_weight("IBGS.AS")

    def test_unclassifiable_universe_degrades_to_equal_weight(self):
        s = _strategy(["VWCE", "EUNL.DE"], 0.9)  # two equity funds, no bond
        assert s._split() is None
        assert s._position_weight("VWCE") == s._position_weight("EUNL.DE") == 0.495

    def test_setattr_after_init_changes_the_portfolio(self):
        """The orchestrator applies overrides with setattr AFTER __init__ —
        a frozen weights table made every optimizer trial run the DEFAULT
        mix while the twin read the override (a fabricated 12.8 pp gap,
        31-10). Weights must follow the live attribute."""
        s = _strategy(["VWCE", "AGGH.AS"], 0.75)
        s.equity_weight = 0.90
        assert s._position_weight("VWCE") == round(0.90 * 0.99, 4)
        assert s._position_weight("AGGH.AS") == round(0.10 * 0.99, 4)
        assert s.suggested_max_position_size == 0.9

    def test_max_position_size_covers_the_heaviest_sleeve(self):
        assert _strategy(["VWCE", "AGGH.AS"], 0.9).suggested_max_position_size == 0.9

    def test_equity_weight_clamped(self):
        s = _strategy(["VWCE", "AGGH.AS"], 5.0)
        assert s._position_weight("VWCE") <= 0.95


class TestOrchestratorWiring:
    def test_build_strategy_passes_the_run_universe(self):
        """Without its branch the strategy fell to the else path with NO
        symbols: universe defaulted to SCHD/VYM…, nothing quoted, and every
        trial ended at 0 trades (the trap this test pins)."""
        from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator

        strategy = BacktestOrchestrator()._build_strategy("static_weighted", ["VWCE", "AGGH.AS"])
        assert strategy.universe == ["VWCE", "AGGH.AS"]
        assert isinstance(strategy, StaticWeightedStrategy)
