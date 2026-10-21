"""El orquestador debe pasar el universo del run a las estrategias
cross-sectional; sin wiring, dividend/low_vol miran sus capas por defecto
(VIG…/VDC…) que pueden no existir en los datos → cero señales.
"""

from __future__ import annotations

from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator


def test_dividend_strategy_receives_run_universe():
    strategy = BacktestOrchestrator()._build_strategy(
        "dividend_tracking", ["SDY", "DLN", "DVY", "PEY", "BIV"]
    )
    assert strategy.core_symbols == ["SDY", "DLN"]
    assert strategy.satellite_symbols == ["DVY", "PEY"]
    assert strategy.defensive_symbol == "BIV"


def test_low_volatility_strategy_receives_run_universe():
    strategy = BacktestOrchestrator()._build_strategy("low_volatility", ["SPY", "QQQ", "TLT"])
    assert strategy.universe == ["SPY", "QQQ", "TLT"]


def test_per_symbol_strategy_unaffected_by_symbols():
    strategy = BacktestOrchestrator()._build_strategy("mean_reversion", ["SPY", "QQQ"])
    assert strategy is not None  # construye igual; las per-símbolo ignoran el universo


def test_without_symbols_defaults_are_kept():
    strategy = BacktestOrchestrator()._build_strategy("dividend_tracking")
    assert "VIG" in strategy.core_symbols
