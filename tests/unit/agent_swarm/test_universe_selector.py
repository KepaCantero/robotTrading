"""Tests for the corpus-derived automatic universe (selector + executor wiring)."""

from datetime import date, timedelta
from decimal import Decimal

from app.services.agent_swarm import executor as executor_module
from app.services.agent_swarm.executor import Capa2PipelineExecutor, SwarmRunRequest
from app.services.agent_swarm.universe_selector import (
    DEFAULT_UNIVERSE,
    AutoUniverseResult,
    auto_universe,
    corpus_symbol_names,
)

TODAY = date(2026, 10, 20)


def write_csv(
    folder,
    symbol: str,
    bars: int,
    *,
    end: date = TODAY - timedelta(days=1),
    close: float = 100.0,
    volume: float = 1_000_000.0,
) -> None:
    """Write a synthetic OHLCV CSV ending at ``end`` with ``bars`` rows."""
    rows = ["date,Open,High,Low,Close,Volume"]
    for i in range(bars):
        day = end - timedelta(days=bars - 1 - i)
        rows.append(f"{day.isoformat()},{close},{close},{close},{close},{volume:.0f}")
    (folder / f"{symbol}.csv").write_text("\n".join(rows) + "\n")


def make_request(**overrides) -> SwarmRunRequest:
    defaults = {
        "capital_initial": Decimal("100000"),
        "objetivo_inversion": "MAXIMIZAR_CAPITAL",
        "risk_tolerance": "MEDIO",
        "investment_horizon": 24,
    }
    defaults.update(overrides)
    return SwarmRunRequest(**defaults)


class TestAutoUniverse:
    def test_screen_filters_and_ranks_by_liquidity(self, tmp_path):
        write_csv(tmp_path, "LIQ", 700, close=100.0, volume=2_000_000)  # 200M/day
        write_csv(tmp_path, "AAA", 700, close=100.0, volume=1_000_000)  # 100M/day
        write_csv(tmp_path, "SHORTY", 100)  # not enough history
        write_csv(tmp_path, "STALE", 700, end=TODAY - timedelta(days=300))  # too old
        write_csv(tmp_path, "THIN", 700, volume=100.0)  # below liquidity floor

        result = auto_universe(tmp_path, today=TODAY)

        assert result.symbols == ["LIQ", "AAA"]
        assert result.scanned == 5
        assert result.kept == 2
        assert result.dropped == {
            "unreadable": 0,
            "short-history": 1,
            "stale": 1,
            "illiquid": 1,
        }
        assert not result.fallback_used

    def test_k_truncates_to_top_symbols(self, tmp_path):
        for i in range(4):
            write_csv(tmp_path, f"S{i}", 700, volume=float(1_000_000 * (i + 1)))

        result = auto_universe(tmp_path, k=2, today=TODAY)

        assert result.symbols == ["S3", "S2"]
        assert result.kept == 4

    def test_equal_liquidity_breaks_ties_alphabetically(self, tmp_path):
        write_csv(tmp_path, "ZEBRA", 700)
        write_csv(tmp_path, "APPLE", 700)

        result = auto_universe(tmp_path, today=TODAY)

        assert result.symbols == ["APPLE", "ZEBRA"]

    def test_empty_corpus_falls_back_to_default_universe(self, tmp_path):
        result = auto_universe(tmp_path, today=TODAY)

        assert result.symbols == list(DEFAULT_UNIVERSE)
        assert result.fallback_used
        assert "fallback DEFAULT_UNIVERSE" in result.summary()

    def test_unreadable_files_are_counted_not_fatal(self, tmp_path):
        write_csv(tmp_path, "GOOD", 700)
        (tmp_path / "GARBAGE.csv").write_text("this,is,not,ohlcv\n1,2,3\n")

        result = auto_universe(tmp_path, today=TODAY)

        assert result.symbols == ["GOOD"]
        assert result.dropped["unreadable"] == 1
        assert result.scanned == 2

    def test_summary_reports_the_screen_story(self, tmp_path):
        write_csv(tmp_path, "LIQ", 700)
        write_csv(tmp_path, "STALE", 700, end=TODAY - timedelta(days=300))

        summary = auto_universe(tmp_path, today=TODAY).summary()

        assert "2 CSVs scanned" in summary
        assert "1 valid" in summary
        assert "1 stale" in summary
        assert "top 1 by liquidity" in summary

    def test_corpus_symbol_names_lists_every_csv(self, tmp_path):
        write_csv(tmp_path, "b", 10)
        write_csv(tmp_path, "a", 10)

        assert corpus_symbol_names(tmp_path) == ["A", "B"]

    def test_missing_folder_yields_no_names(self, tmp_path):
        assert corpus_symbol_names(tmp_path / "nope") == []


class TestExecutorWiring:
    async def test_run_without_symbols_uses_auto_universe(self, monkeypatch):
        fake = AutoUniverseResult(
            symbols=["AAPL", "MSFT"],
            scanned=713,
            kept=566,
            dropped={"stale": 147},
            fallback_used=False,
        )
        monkeypatch.setattr(executor_module, "auto_universe", lambda: fake)

        state = await Capa2PipelineExecutor().run(make_request())

        assert state.status == "completed"
        assert state.agents["t41"].input_payload["symbols"] == ["AAPL", "MSFT"]
        assert state.agents["t41"].warnings[0].startswith("auto universe")

    async def test_explicit_symbols_skip_auto_universe(self, monkeypatch):
        def _boom() -> None:
            raise AssertionError("auto_universe must not run for explicit symbols")

        monkeypatch.setattr(executor_module, "auto_universe", _boom)

        state = await Capa2PipelineExecutor().run(make_request(symbols=["AAPL"]))

        assert state.status == "completed"
        assert state.agents["t41"].input_payload["symbols"] == ["AAPL"]
        assert not state.agents["t41"].warnings
