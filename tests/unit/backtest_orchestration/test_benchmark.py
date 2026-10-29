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
        """SPY local empieza en 2006-10 (tras el empalme de CSVs): un run de
        2001-2007 compararía 6 años de estrategia contra 9 meses de mercado.
        IVV (mismo índice, desde 2000) cubre la ventana y debe ganar."""
        bench = BacktestOrchestrator()._load_benchmark(
            _request(start_date=date(2001, 1, 2), end_date=date(2007, 6, 29)),
            DataLoader(base_path=REPO / "data" / "historical"),
            datetime(2001, 1, 2),
            datetime(2007, 6, 29),
        )
        assert bench is not None
        assert bench["symbol"] == "IVV"
        assert bench["curve"][0][0].startswith("2001-01")

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
            max_drawdown_percentage=D("-10"),
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
        bench = {
            "symbol": "SPY",
            "return_pct": D("16.00"),
            "curve": [("t", "1.16")],
            "universe_ew_return_pct": D("12.00"),
            "universe_ew_sharpe": D("0.8"),
            "universe_ew_max_dd_pct": D("15.00"),
            "universe_ew_symbols_used": ["BND", "SCHD"],
            "excess_vs_universe_ew": 10.0,
        }
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
        # Post-2026-10-27: universe_ew_return_pct IS the achievable
        # buy&hold twin (single score benchmark); max_dd rides along for
        # the relative-DD score.
        assert result.universe_ew_return_pct == D("12.00")
        assert result.universe_ew_max_dd_pct == D("15.00")
        assert result.universe_ew_symbols_used == ["BND", "SCHD"]
        assert result.excess_vs_universe_ew_pct == D("10.00")
        payload = result.to_dict()
        assert payload["benchmark_symbol"] == "SPY"
        assert payload["benchmark_curve"] == [{"ts": "t", "value": "1.16"}]
        assert payload["universe_ew_max_dd_pct"] == "15.00"
        assert payload["universe_ew_symbols_used"] == ["BND", "SCHD"]

    def test_no_benchmark_leaves_neutral_fields(self):
        result = BacktestOrchestrator()._map_engine_result(  # noqa: SLF001
            _request(), self._engine_result(), datetime(2020, 1, 2), datetime(2020, 12, 31, 23, 59)
        )
        assert result.benchmark_symbol == ""
        assert result.benchmark_return_pct is None
        assert result.excess_return_pct is None
        assert result.universe_ew_max_dd_pct is None
        assert result.universe_ew_symbols_used == []
        assert result.to_dict()["benchmark_curve"] == []


class TestUniverseEqualWeightBenchmark:
    """D12: benchmark EW del propio universo — TODOS los activos declarados,
    invariante al orden de entrada, y buy&hold separado del rebalanceo diario."""

    DIVIDEND_PRESET = ["VIG", "DGRO", "DGRW", "SCHD", "VYM", "DVY", "BND"]

    def _ew(self, symbols, start=date(2020, 1, 2), end=date(2022, 12, 30)):
        return BacktestOrchestrator()._load_dividend_benchmark(  # noqa: SLF001
            _request(symbols=symbols, start_date=start, end_date=end),
            DataLoader(base_path=REPO / "data" / "historical"),
            datetime(start.year, start.month, start.day),
            datetime(end.year, end.month, end.day, 23, 59),
        )

    def test_all_declared_assets_included(self):
        """BND cae séptimo y debe estar: el recorte a 6 lo excluía."""
        bench = self._ew(self.DIVIDEND_PRESET)
        assert bench is not None
        assert bench["symbols_used"] == sorted(self.DIVIDEND_PRESET)

    def test_invariant_to_symbol_order(self):
        """Reordenar la entrada no cambia composición ni resultados."""
        forward = self._ew(self.DIVIDEND_PRESET)
        shuffled = self._ew(list(reversed(self.DIVIDEND_PRESET)))
        assert forward is not None and shuffled is not None
        assert forward["symbols_used"] == shuffled["symbols_used"]
        for key in (
            "return_pct",
            "sharpe",
            "buy_hold_return_pct",
            "buy_hold_sharpe",
            "curve",
            "buy_hold_curve",
        ):
            assert forward[key] == shuffled[key], key

    def test_both_policies_present_on_real_data(self):
        """Las DOS curvas viajan: rebalance diario y buy&hold puro (el
        rebalanceo arranca una sesión después — necesita retorno, no solo
        precio)."""
        bench = self._ew(["SCHD", "VYM", "BND"])
        assert bench is not None
        assert bench["return_pct"] != bench["buy_hold_return_pct"]
        assert len(bench["curve"]) >= 2 and len(bench["buy_hold_curve"]) >= 2

    def test_synthetic_hand_computed_split(self, tmp_path):
        """Rebalance diario vs buy&hold con matemática cerrada (D12)."""
        import csv

        days = [f"2024-01-{d:02d}" for d in range(1, 13)]

        def write(symbol, closes):
            with open(tmp_path / f"{symbol}.csv", "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["date", "Open", "High", "Low", "Close", "Volume"])
                for day, close in zip(days, closes):
                    writer.writerow([day, close, close, close, close, 1_000_000])

        # 10 días planos + doble y vuelta: A 100×10, 200, 100 · B 100×12
        write("AAA", [100.0] * 10 + [200.0, 100.0])
        write("BBB", [100.0] * 12)

        bench = BacktestOrchestrator()._load_dividend_benchmark(  # noqa: SLF001
            _request(
                symbols=["AAA", "BBB"], start_date=date(2024, 1, 1), end_date=date(2024, 1, 12)
            ),
            DataLoader(base_path=tmp_path),
            datetime(2024, 1, 1),
            datetime(2024, 1, 12, 23, 59),
        )
        assert bench is not None
        assert bench["return_pct"] == pytest.approx(12.5)
        assert bench["buy_hold_return_pct"] == pytest.approx(0.0)
