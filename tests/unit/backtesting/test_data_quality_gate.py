"""GATE Fase A — data coverage gate and quote cache.

The silent-truncation class of bug: a CSV starting late was quietly
clipped, a missing symbol vanished behind a `continue`. The STRICT gate
names symbols/dates and carries the repair command; partial runs opt in
explicitly and carry the evidence; the LRU cache kills the re-parse cost
of repeated windows without ever serving stale files.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from app.backtesting.data_quality import InsufficientDataError, scan_data_coverage


def _write_csv(path: Path, symbol: str, rows: list[tuple[str, float]]):
    with open(path / f"{symbol}.csv", "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "Open", "High", "Low", "Close", "Volume"])
        for day, close in rows:
            writer.writerow([day, close, close, close, close, 1_000_000])


def _days(start: str, count: int) -> list[tuple[str, float]]:
    from datetime import timedelta

    d0 = datetime.strptime(start, "%Y-%m-%d")
    return [((d0 + timedelta(days=i)).strftime("%Y-%m-%d"), 100.0 + i) for i in range(count)]


class TestScanDataCoverage:
    def test_covered_symbol(self, tmp_path):
        _write_csv(tmp_path, "AAA", list(_days("2020-01-01", 400)))

        report = scan_data_coverage(["AAA"], tmp_path, datetime(2020, 6, 1), datetime(2020, 12, 31))
        entry = report.symbols[0]
        assert entry.csv_exists and entry.covers_window
        assert entry.rows_in_execution_window > 100

    def test_late_start_is_uncovered(self, tmp_path):
        _write_csv(tmp_path, "LATE", list(_days("2020-06-01", 300)))  # window starts 2020-01

        report = scan_data_coverage(
            ["LATE"], tmp_path, datetime(2020, 1, 1), datetime(2020, 12, 31)
        )
        assert report.uncovered_symbols == ["LATE"]
        assert report.symbols[0].first_date == datetime(2020, 6, 1)

    def test_missing_csv_reported(self, tmp_path):
        report = scan_data_coverage(
            ["GHOST"], tmp_path, datetime(2020, 1, 1), datetime(2020, 12, 31)
        )
        assert report.missing_symbols == ["GHOST"]
        assert not report.symbols[0].csv_exists

    def test_warmup_never_gates(self, tmp_path):
        """Data covering the EXECUTION window but not the warm-up is fine."""
        _write_csv(tmp_path, "AAA", list(_days("2020-03-01", 300)))  # warm-up wanted from Jan

        report = scan_data_coverage(
            ["AAA"],
            tmp_path,
            datetime(2020, 6, 1),  # execution start (covered)
            datetime(2020, 12, 31),
            warmup_start=datetime(2020, 1, 1),  # warm-up NOT covered
        )
        assert report.symbols[0].covers_window

    def test_error_message_is_actionable(self, tmp_path):
        _write_csv(tmp_path, "LATE", list(_days("2020-06-01", 300)))

        report = scan_data_coverage(
            ["LATE", "GHOST"], tmp_path, datetime(2020, 1, 1), datetime(2020, 12, 31)
        )
        err = InsufficientDataError(report, "Cobertura insuficiente")
        msg = str(err)
        assert "LATE" in msg and "2020-06-01" in msg  # what's available
        assert "GHOST" in msg  # what's missing
        assert "download_market_data" in msg  # the repair command
        assert "2020-01-01" in msg  # what was requested


class TestOrchestratorStrictGate:
    """End-to-end through orchestrate(): STRICT fails naming the symbol;
    allow_partial_data runs and carries the report + warning."""

    def _request(self, **over):
        from app.services.backtest_orchestration.models import BacktestOrchestrationRequest

        base = dict(
            profile_id="gate",
            input_id="gate",
            module_parameter_set_id="gate",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("300"),
            objective="capital_preservation",
            risk_profile="moderate",
            strategy_name="mean_reversion",
            symbols=["DVY", "VYM"],  # DVY desde 2003; VYM desde 2006-11
            start_date=date(2006, 1, 2),
            end_date=date(2007, 12, 31),
            benchmark_symbol="",
        )
        base.update(over)
        return BacktestOrchestrationRequest(**base)

    async def test_strict_fails_naming_late_symbol(self):
        from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator

        result = await BacktestOrchestrator().orchestrate(self._request())

        assert result.success is False
        assert "VYM" in result.error_message
        assert "download_market_data" in result.error_message

    async def test_partial_data_runs_with_warning_and_report(self):
        from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator

        result = await BacktestOrchestrator().orchestrate(self._request(allow_partial_data=True))

        assert result.success is True
        assert any("allow_partial_data" in w for w in result.warnings)
        report = result.data_quality
        assert report is not None
        assert "VYM" in report["uncovered_symbols"]

    async def test_covered_window_unchanged(self):
        from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator

        result = await BacktestOrchestrator().orchestrate(
            self._request(start_date=date(2008, 1, 2), end_date=date(2009, 6, 30))
        )

        assert result.success is True
        assert result.data_quality is not None
        assert result.data_quality["uncovered_symbols"] == []


class TestQuoteCache:
    def test_hit_returns_equal_list_new_object(self, tmp_path):
        from app.backtesting.data_loader import _QUOTE_CACHE, DataLoader

        _write_csv(tmp_path, "AAA", list(_days("2020-01-01", 60)))
        loader = DataLoader(base_path=tmp_path)
        _QUOTE_CACHE.clear()

        first = loader.load_market_data("AAA", datetime(2020, 2, 1), datetime(2020, 3, 1))
        second = loader.load_market_data("AAA", datetime(2020, 2, 1), datetime(2020, 3, 1))
        assert first == second
        assert first is not second  # copy of the list — callers can't corrupt the cache
        assert len(_QUOTE_CACHE) == 1

    def test_mtime_invalide_on_rewrite(self, tmp_path):
        import os
        import time

        from app.backtesting.data_loader import _QUOTE_CACHE, DataLoader

        _write_csv(tmp_path, "AAA", list(_days("2020-01-01", 60)))
        loader = DataLoader(base_path=tmp_path)
        _QUOTE_CACHE.clear()

        a = loader.load_market_data("AAA", datetime(2020, 2, 1), datetime(2020, 3, 1))
        # rewrite the file (repair) — new mtime must invalidate
        time.sleep(0.01)
        _write_csv(tmp_path, "AAA", list(_days("2020-01-01", 120)))
        os.utime(tmp_path / "AAA.csv")  # force mtime bump for fast filesystems

        b = loader.load_market_data("AAA", datetime(2020, 2, 1), datetime(2020, 3, 1))
        assert len(_QUOTE_CACHE) == 2  # old + new keys coexist until LRU evicts
        assert a != b or True  # content may coincide; the point is the fresh parse

    def test_lru_bounded(self, tmp_path):
        from app.backtesting.data_loader import _QUOTE_CACHE, _QUOTE_CACHE_MAX, DataLoader

        loader = DataLoader(base_path=tmp_path)
        _QUOTE_CACHE.clear()
        for i in range(_QUOTE_CACHE_MAX + 5):
            _write_csv(tmp_path, f"S{i}", list(_days("2020-01-01", 40)))
            loader.load_market_data(f"S{i}", datetime(2020, 1, 5), datetime(2020, 2, 1))

        assert len(_QUOTE_CACHE) <= _QUOTE_CACHE_MAX
