"""Tests for the corpus-derived automatic universe (selector + executor wiring)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

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
            "out-of-goal": 0,
            "short-history": 1,
            "stale": 1,
            "illiquid": 1,
            "uncovered-window": 0,
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
        monkeypatch.setattr(executor_module, "auto_universe", lambda **kw: fake)

        state = await Capa2PipelineExecutor().run(make_request())

        assert state.status == "completed"
        assert state.agents["t41"].input_payload["symbols"] == ["AAPL", "MSFT"]
        assert state.agents["t41"].warnings[0].startswith("auto universe")

    async def test_goal_is_passed_to_auto_universe(self, monkeypatch):
        seen = {}

        def _capture(**kwargs):
            seen.update(kwargs)
            return AutoUniverseResult(
                symbols=["SCHD"], scanned=1, kept=1, dropped={}, fallback_used=False
            )

        monkeypatch.setattr(executor_module, "auto_universe", _capture)

        state = await Capa2PipelineExecutor().run(
            make_request(objetivo_inversion="MAXIMIZAR_DIVIDENDOS")
        )

        assert state.status == "completed"
        assert seen.get("goal") == "MAXIMIZAR_DIVIDENDOS"
        assert seen.get("window_start") is None  # request sin backtest_start

    async def test_explicit_symbols_skip_auto_universe(self, monkeypatch):
        def _boom() -> None:
            raise AssertionError("auto_universe must not run for explicit symbols")

        monkeypatch.setattr(executor_module, "auto_universe", _boom)

        state = await Capa2PipelineExecutor().run(make_request(symbols=["AAPL"]))

        assert state.status == "completed"
        assert state.agents["t41"].input_payload["symbols"] == ["AAPL"]
        assert not state.agents["t41"].warnings


class TestGoalAwareUniverse:
    def test_dividend_goal_restricts_to_curated_dividend_etfs(self, tmp_path):
        for sym in ("SCHD", "VIG", "VYM", "DGRO", "DVY", "SDY", "NOBL", "PEY", "FDVV", "DLN"):
            write_csv(tmp_path, sym, 700)
        write_csv(tmp_path, "SPY", 700, volume=9_000_000)  # mucho más líquido
        write_csv(tmp_path, "NVDA", 700, volume=9_000_000)

        result = auto_universe(tmp_path, today=TODAY, goal="maximizar_dividendos")

        assert set(result.symbols) <= {
            "SCHD",
            "VIG",
            "VYM",
            "DGRO",
            "DVY",
            "SDY",
            "NOBL",
            "PEY",
            "FDVV",
            "DLN",
        }
        assert result.goal_filter == "MAXIMIZAR_DIVIDENDOS"
        assert "SPY" not in result.symbols
        assert "out-of-goal" in result.dropped

    def test_capital_preservation_goal_picks_defensive_names(self, tmp_path):
        for sym in ("BND", "TLT", "LQD", "AGG", "IEF", "GLD", "JNJ", "XLU", "VPU", "KO"):
            write_csv(tmp_path, sym, 700)
        write_csv(tmp_path, "TSLA", 700, volume=9_000_000)

        result = auto_universe(tmp_path, today=TODAY, goal="CAPITAL_PRESERVATION")

        assert "TSLA" not in result.symbols
        # BND/AGG y TLT/IEF son familias: con liquidez igual gana el
        # alfabético (AGG, IEF); GLD no tiene rival en este corpus
        assert {"AGG", "IEF", "GLD"} <= set(result.symbols)

    def test_goal_with_too_few_survivors_keeps_curated_set(self, tmp_path):
        # 30-10: los objetivos curados NUNCA recaen en la pantalla
        # genérica — una petición ACUMULAR llegó a testear IBEX/Toyota/SPY
        # porque el floor de liquidez (Yahoo subestima el volumen de los
        # ETF listados en EUR) dejó el conjunto bajo el mínimo. El objetivo
        # manda: se relaja el floor y se queda con sus nombres curados.
        write_csv(tmp_path, "SCHD", 700, volume=1_000)  # curado, volumen bajo
        write_csv(tmp_path, "SPY", 700, volume=5_000_000)
        write_csv(tmp_path, "QQQ", 700, volume=4_000_000)

        result = auto_universe(tmp_path, k=2, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS")

        assert result.goal_filter == "MAXIMIZAR_DIVIDENDOS"
        assert result.symbols == ["SCHD"]
        assert "SPY" not in result.symbols  # jamás un cambio silencioso de universo

    def test_goal_without_any_viable_candidate_fails_loudly(self, tmp_path):
        # sin un solo candidato viable del objetivo, la run FALLE con una
        # razón clara — nunca prueba en silencio un universo ajeno
        write_csv(tmp_path, "SPY", 700, volume=5_000_000)

        with pytest.raises(ValueError, match="MAXIMIZAR_DIVIDENDOS"):
            auto_universe(tmp_path, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS")

    def test_acumular_drops_uncovered_acc_on_long_windows(self, tmp_path):
        # VWCE nació 2019 y AGGH cotiza desde 2021: en una ventana de 10
        # años no pueden entrar — uncovered (avisado), no rompen la run.
        # VHYL/IDVY ya NO son del objetivo (distribuyen — critique 30-10).
        for sym, bars in (
            ("EUNL.DE", 3900),
            ("IUSQ.DE", 3900),
            ("EIMI.MI", 3900),
            ("VWCE", 2000),
            ("AGGH.AS", 1000),
            ("IBGS.AS", 3900),
        ):
            write_csv(tmp_path, sym, bars)

        result = auto_universe(
            tmp_path,
            today=TODAY,
            goal="ACUMULAR",
            window_start=TODAY - timedelta(days=3650),
        )

        assert result.dropped["uncovered-window"] == 2
        assert "VWCE" not in result.symbols and "AGGH.AS" not in result.symbols
        assert {"EUNL.DE", "IUSQ.DE", "EIMI.MI", "IBGS.AS"} == set(result.symbols)

    def test_unknown_goal_is_generic(self, tmp_path):
        write_csv(tmp_path, "SPY", 700)

        result = auto_universe(tmp_path, today=TODAY, goal="MAXIMIZAR_CAPITAL")

        assert result.goal_filter == ""
        assert result.symbols == ["SPY"]


class TestFamilyDiversification:
    def test_generic_screen_caps_us_index_copies(self, tmp_path):
        # 5 ETFs del mismo índice, más líquidos que el resto
        for i, sym in enumerate(("SPY", "IVV", "VOO", "DIA", "IWM")):
            write_csv(tmp_path, sym, 700, volume=9_000_000 - i)
        # suficientes singletons (sin familia) para llenar k sin relleno diferido
        for sym, vol in {
            "GLD": 1_000_000,
            "JPM": 900_000,
            "KO": 800_000,
            "CAT": 700_000,
            "BA": 600_000,
        }.items():
            write_csv(tmp_path, sym, 700, volume=vol)

        result = auto_universe(tmp_path, k=8, today=TODAY)

        assert sum(1 for s in result.symbols if s in {"SPY", "IVV", "VOO", "DIA", "IWM"}) == 3
        assert {"GLD", "JPM", "KO", "CAT", "BA"} <= set(result.symbols)
        assert result.diversified is True

    def test_deferred_over_cap_symbols_fill_remaining_slots(self, tmp_path):
        for i, sym in enumerate(("SPY", "IVV", "VOO", "DIA", "IWM")):
            write_csv(tmp_path, sym, 700, volume=9_000_000 - i)

        result = auto_universe(tmp_path, k=5, today=TODAY)

        assert len(result.symbols) == 5  # 3 capped + 2 deferred rellenan

    def test_goal_filtered_screen_dedupes_but_no_generic_cap(self, tmp_path):
        # 10 símbolos en 4 familias de solapamiento -> 4 elegidos (uno por
        # familia); el tope genérico de familia NO aplica en el goal screen
        for i, sym in enumerate(
            ("SCHD", "VIG", "VYM", "DGRO", "DVY", "SDY", "NOBL", "PEY", "FDVV", "DLN")
        ):
            write_csv(tmp_path, sym, 700, volume=5_000_000 - i)

        result = auto_universe(tmp_path, k=10, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS")

        assert len(result.symbols) == 4
        assert result.overlap_dropped == 6
        assert result.diversified is False

    def test_long_window_prefers_family_member_that_covers_it(self, tmp_path):
        # VYMI (más líquido, historia corta) vs PID (menos líquido, historia
        # larga): un run desde 2008 debe elegir PID; uno desde 2020, VYMI
        write_csv(tmp_path, "VYMI", 2500, volume=9_000_000)  # ~2019 -> hoy
        write_csv(tmp_path, "PID", 7000, volume=2_000_000)  # ~2007 -> hoy
        for sym, vol in (
            ("SCHD", 5_000_000),
            ("VYM", 4_500_000),
            ("NOBL", 3_000_000),
            ("SDY", 2_500_000),
            ("DVY", 2_000_000),
            ("PEY", 1_500_000),
        ):
            write_csv(tmp_path, sym, 700, volume=vol)

        short = auto_universe(
            tmp_path, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS", window_start=date(2020, 1, 1)
        )
        assert "VYMI" in short.symbols and "PID" not in short.symbols

        long_run = auto_universe(
            tmp_path, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS", window_start=date(2008, 1, 2)
        )
        assert "PID" in long_run.symbols and "VYMI" not in long_run.symbols

    def test_family_of_known_shapes(self):
        from app.services.agent_swarm.universe_selector import family_of

        assert family_of("SPY") == "us-index"
        assert family_of("7203.T") == "japan"
        assert family_of("ITX.MC") == "europe"
        assert family_of("WEIRDTOCKER") == "WEIRDTOCKER"


class TestOverlapFamilyDedupe:
    """DGRO/VIG comparten ~80-95% de posiciones: pagar dos comisiones por
    la misma exposición. El cribado por objetivo mantiene UNO por familia
    (el más líquido) — incluida la familia internacional si el corpus la
    tiene."""

    def _corpus(self, tmp_path, vols: dict[str, float]):
        for sym, vol in vols.items():
            write_csv(tmp_path, sym, 700, volume=vol)

    def test_dividend_goal_keeps_one_per_family(self, tmp_path):
        self._corpus(
            tmp_path,
            {
                "VIG": 9_000_000,
                "DGRO": 8_000_000,  # misma familia → solo VIG
                "SCHD": 7_000_000,
                "VYM": 6_500_000,  # misma familia → solo SCHD
                "NOBL": 5_000_000,
                "SDY": 4_500_000,  # aristócratas → solo NOBL
                "DVY": 4_000_000,
                "PEY": 3_500_000,  # high-yield → solo DVY
                "VYMI": 3_000_000,  # internacional, única
            },
        )
        result = auto_universe(tmp_path, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS")
        assert set(result.symbols) == {"VIG", "SCHD", "NOBL", "DVY", "VYMI"}
        assert "DGRO" not in result.symbols and "VYM" not in result.symbols
        assert result.overlap_dropped == 4  # DGRO, VYM, SDY, PEY

    def test_most_liquid_wins_within_family(self, tmp_path):
        self._corpus(
            tmp_path,
            {
                "DGRO": 9_000_000,
                "VIG": 8_000_000,
                "SCHD": 5_000_000,
                "VYM": 4_000_000,
                "NOBL": 3_000_000,
                "SDY": 2_000_000,
                "DVY": 1_500_000,
                "PEY": 1_200_000,
                "VYMI": 1_000_000,
                "DGRW": 6_000_000,
                "FDVV": 3_000_000,
                "DLN": 2_500_000,
            },
        )
        result = auto_universe(tmp_path, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS")
        assert "DGRO" in result.symbols and "VIG" not in result.symbols

    def test_preservation_goal_dedupes_bond_and_gold_twins(self, tmp_path):
        self._corpus(
            tmp_path,
            {
                "BND": 9_000_000,
                "AGG": 8_500_000,
                "SCHZ": 8_000_000,
                "GLD": 7_000_000,
                "IAU": 6_500_000,
                "TLT": 6_000_000,
                "IEF": 5_500_000,
                "JNJ": 5_000_000,
                "XLV": 4_500_000,
                "VHT": 4_000_000,
            },
        )
        result = auto_universe(tmp_path, today=TODAY, goal="CAPITAL_PRESERVATION")
        assert "BND" in result.symbols and "AGG" not in result.symbols
        assert "GLD" in result.symbols and "IAU" not in result.symbols
        assert "XLV" in result.symbols and "VHT" not in result.symbols

    def test_unaffiliated_symbols_pass_through(self, tmp_path):
        # 8+ supervivientes para no disparar el fallback genérico
        self._corpus(
            tmp_path,
            {
                "SCHD": 9_000_000,
                "VYM": 8_000_000,
                "NOBL": 3_000_000,
                "SDY": 2_000_000,
                "DVY": 1_500_000,
                "PEY": 1_200_000,
                "VYMI": 1_000_000,
                "DES": 900_000,
                "DON": 800_000,
            },
        )
        result = auto_universe(tmp_path, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS")
        assert {"SCHD", "NOBL", "DVY", "VYMI"} <= set(result.symbols)
        assert "VYM" not in result.symbols and "DES" in result.symbols


class TestExhaustiveUniverse:
    """User (2026-10-27): 'automatic y todos los símbolos' — exhaustive
    mode keeps EVERY screened symbol (no goal filter, no family caps, no
    top-k) but drops symbols that cannot cover the window start (the
    strict coverage gate would fail the whole run otherwise)."""

    def test_exhaustive_keeps_all_screened_symbols(self, tmp_path):
        write_csv(tmp_path, "LIQ", 700, close=100.0, volume=2_000_000)
        write_csv(tmp_path, "AAA", 700, close=100.0, volume=1_000_000)
        write_csv(tmp_path, "THIN", 700, volume=100.0)  # still illiquid: out
        result = auto_universe(tmp_path, today=TODAY, goal="MAXIMIZAR_DIVIDENDOS", exhaustive=True)
        assert result.symbols == ["LIQ", "AAA"]  # no goal filter, no caps

    def test_exhaustive_drops_symbols_missing_the_window(self, tmp_path):
        write_csv(tmp_path, "OLD", 900, close=100.0, volume=2_000_000)
        # 600 bars ending yesterday: enough history, but only starts ~600
        # days back — a 800-day window needs more
        write_csv(tmp_path, "NEW", 600, close=100.0, volume=2_000_000)
        result = auto_universe(
            tmp_path, today=TODAY, window_start=TODAY - timedelta(days=800), exhaustive=True
        )
        assert result.symbols == ["OLD"]
        assert result.dropped["uncovered-window"] == 1
