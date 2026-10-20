"""Benchmark (buy&hold de referencia) en el resultado del backtest de producto.

El benchmark es CONTEXTO de mercado, nunca parte del veredicto: el mismo
motor, misma ventana, misma capitalización inicial que la equity de la
estrategia para poder compararlas visual y numéricamente.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.backtesting.data_loader import DataLoader
from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator
from app.services.backtest_orchestration.models import BacktestOrchestrationRequest, BacktestResult

REPO = Path(__file__).resolve().parents[3]


def _request(**over) -> BacktestOrchestrationRequest:
    base = dict(
        profile_id="t",
        input_id="t",
        module_parameter_set_id="t",
        initial_capital=D("100000"),
        target_monthly_return_eur=D("300"),
        objective="capital_preservation",
        risk_profile="conservative",
        start_date=date(2020, 1, 2),
        end_date=date(2020, 12, 31),
    )
    base.update(over)
    return BacktestOrchestrationRequest(**base)


class TestLoadBenchmark:
    def test_spy_buy_and_hold_matches_close_ratio(self):
        bench = BacktestOrchestrator()._load_benchmark(
            _request(),
            DataLoader(base_path=REPO / "data" / "historical"),
            datetime(2020, 1, 2),
            datetime(2020, 12, 31, 23, 59),
        )
        assert bench is not None
        assert bench["symbol"] == "SPY"
        first = float(bench["curve"][0][1])
        last = float(bench["curve"][-1][1])
        assert first == pytest.approx(1.0)
        assert float(D(str(last - 1.0)) * 100) == pytest.approx(
            float(bench["return_pct"]), abs=0.02
        )

    def test_disabled_returns_none(self):
        bench = BacktestOrchestrator()._load_benchmark(
            _request(benchmark_symbol=""),
            DataLoader(base_path=REPO / "data" / "historical"),
            datetime(2020, 1, 2),
            datetime(2020, 12, 31, 23, 59),
        )
        assert bench is None

    def test_missing_symbol_returns_none_not_raise(self):
        bench = BacktestOrchestrator()._load_benchmark(
            _request(benchmark_symbol="NOSUCH"),
            DataLoader(base_path=REPO / "data" / "historical"),
            datetime(2020, 1, 2),
            datetime(2020, 12, 31, 23, 59),
        )
        assert bench is None

    def test_long_window_falls_back_to_deeper_same_index_series(self):
        """SPY local empieza en 2016: un run de 2008-2026 compararía 18 años
        de estrategia contra 10 de mercado. IVV (mismo índice, desde 2000)
        cubre la ventana y debe ganar."""
        bench = BacktestOrchestrator()._load_benchmark(
            _request(start_date=date(2008, 1, 2), end_date=date(2026, 1, 2)),
            DataLoader(base_path=REPO / "data" / "historical"),
            datetime(2008, 1, 2),
            datetime(2026, 1, 2),
        )
        assert bench is not None
        assert bench["symbol"] == "IVV"
        assert bench["curve"][0][0].startswith("2008-01")

    def test_short_window_keeps_requested_symbol(self):
        bench = BacktestOrchestrator()._load_benchmark(
            _request(start_date=date(2019, 1, 2), end_date=date(2021, 1, 2)),
            DataLoader(base_path=REPO / "data" / "historical"),
            datetime(2019, 1, 2),
            datetime(2021, 1, 2),
        )
        assert bench is not None
        assert bench["symbol"] == "SPY"


class TestMapperAttachesBenchmark:
    def _engine_result(self):
        perf = SimpleNamespace(
            sharpe_ratio=D("0.5"),
            sortino_ratio=D("0.5"),
            calmar_ratio=D("0"),
            max_drawdown=D("-0.10"),
            total_trades=2,
            win_rate=D("50"),
        )
        ts = datetime(2020, 6, 1)
        return SimpleNamespace(
            performance=perf,
            trades=[],
            equity_curve=[(ts, D("100000")), (ts, D("110000"))],
            final_capital=D("110000"),
        )

    def test_fields_and_excess(self):
        orch = BacktestOrchestrator()
        bench = {"symbol": "SPY", "return_pct": D("16.00"), "curve": [("t", "1.16")]}
        result = orch._map_engine_result(  # noqa: SLF001 - unit under test
            _request(),
            self._engine_result(),
            datetime(2020, 1, 2),
            datetime(2020, 12, 31, 23, 59),
            gate={"passed": True, "windows": 5, "summary": "ok"},
            benchmark=bench,
        )
        assert isinstance(result, BacktestResult)
        assert result.benchmark_symbol == "SPY"
        assert result.benchmark_return_pct == D("16.00")
        # total_return 10% vs SPY 16% → excess -6%
        assert result.excess_return_pct == D("-6.00")
        payload = result.to_dict()
        assert payload["benchmark_symbol"] == "SPY"
        assert payload["benchmark_curve"] == [{"ts": "t", "value": "1.16"}]

    def test_no_benchmark_leaves_neutral_fields(self):
        result = BacktestOrchestrator()._map_engine_result(  # noqa: SLF001
            _request(), self._engine_result(), datetime(2020, 1, 2), datetime(2020, 12, 31, 23, 59)
        )
        assert result.benchmark_symbol == ""
        assert result.benchmark_return_pct is None
        assert result.excess_return_pct is None
        assert result.to_dict()["benchmark_curve"] == []
