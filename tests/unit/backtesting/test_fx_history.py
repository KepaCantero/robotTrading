"""Bloque 3 — PIT FX history: real data or None, never constants."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.backtesting.fx_history import FxHistory


def _write(path: Path, rows: list[tuple], header: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _corpus(tmp_path: Path) -> FxHistory:
    # USDJPY fixes: Fri 5th, Mon 8th; EURUSD daily
    _write(
        tmp_path / "fx" / "USDJPY.csv",
        [("2024-01-05", "140.00"), ("2024-01-08", "141.00"), ("2024-01-09", "142.00")],
        ["date", "close"],
    )
    _write(
        tmp_path / "rates" / "USD.csv",
        [("2024-01-01", "5.50"), ("2024-06-01", "5.25")],
        ["date", "rate_pct"],
    )
    _write(
        tmp_path / "rates" / "JPY.csv",
        [("2024-01-01", "0.10"), ("2024-06-01", "0.10")],
        ["date", "rate_pct"],
    )
    return FxHistory(data_dir=tmp_path)


class TestPitSemantics:
    def test_exact_date(self, tmp_path):
        p = _corpus(tmp_path).rate("USDJPY", date(2024, 1, 8))
        assert p is not None and p.rate == Decimal("141.00")
        assert p.observed == date(2024, 1, 8)

    def test_weekend_falls_back_to_friday_labelled(self, tmp_path):
        """Sunday Jan 7 → Friday's fix, and the OBSERVATION date says so."""
        p = _corpus(tmp_path).rate("USDJPY", date(2024, 1, 7))
        assert p is not None and p.rate == Decimal("140.00")
        assert p.observed == date(2024, 1, 5)

    def test_before_first_fix_is_none(self, tmp_path):
        assert _corpus(tmp_path).rate("USDJPY", date(2024, 1, 4)) is None

    def test_unknown_pair_is_none_never_constant(self, tmp_path):
        assert _corpus(tmp_path).rate("USDMXN", date(2024, 1, 8)) is None

    def test_corpus_hole_is_none(self, tmp_path):
        """A gap bigger than the FX staleness limit is a HOLE, not 'last known'."""
        _write(
            tmp_path / "fx" / "EURUSD.csv",
            [("2024-01-02", "1.10")],
            ["date", "close"],
        )
        fx = _corpus(tmp_path)
        # 20 days after the only fix → hole (fresh corpus, stale answer)
        assert fx.rate("EURUSD", date(2024, 1, 22)) is None

    def test_pair_format_slash_normalized(self, tmp_path):
        assert _corpus(tmp_path).rate("USD/JPY", date(2024, 1, 8)) is not None


class TestRatesAndCarry:
    def test_policy_rate_pit(self, tmp_path):
        p = _corpus(tmp_path).policy_rate("USD", date(2024, 3, 15))
        assert p is not None and p.rate == Decimal("5.50")  # before the June cut
        p2 = _corpus(tmp_path).policy_rate("USD", date(2024, 7, 1))
        assert p2 is not None and p2.rate == Decimal("5.25")

    def test_missing_currency_is_none(self, tmp_path):
        assert _corpus(tmp_path).policy_rate("BRL", date(2024, 1, 1)) is None

    def test_carry_differential_base_minus_quote(self, tmp_path):
        """BASE − QUOTE in percentage points: long the PAIR earns it
        (2024 USDJPY long = long USD/short JPY = positive carry)."""
        diff = _corpus(tmp_path).carry_differential("USDJPY", date(2024, 7, 1))
        assert diff is not None
        # USD 5.25 − JPY 0.10 = +5.15 → long USDJPY EARNED carry ✓
        assert diff.rate == Decimal("5.15")

    def test_differential_with_missing_leg_is_none(self, tmp_path):
        assert _corpus(tmp_path).carry_differential("USDBRL", date(2024, 1, 1)) is None


class TestRealCorpus:
    """Smoke against the downloaded corpus (real ECB-derived numbers)."""

    def test_usdjpy_from_real_data(self):
        fx = FxHistory()
        p = fx.rate("USDJPY", date(2024, 1, 16))
        assert p is not None
        # early 2024 USDJPY traded ~143-148; a derived ECB cross must land there
        assert Decimal("140") < p.rate < Decimal("152")
        assert p.observed <= date(2024, 1, 16)

    def test_eurusd_from_real_data(self):
        """ECB quotes USD-per-EUR directly — EURUSD must be ~1.09 in early
        2024, NOT the inverted ~0.91 (a regression the tests must pin)."""
        p = FxHistory().rate("EURUSD", date(2024, 1, 16))
        assert p is not None
        assert Decimal("1.05") < p.rate < Decimal("1.15")

    def test_real_carry_2024(self):
        fx = FxHistory()
        diff = fx.carry_differential("USDJPY", date(2024, 6, 28))
        # 2024: USD ~5.3-5.5 vs JPY ~0.1 → carry strongly positive for USD
        assert diff is not None
        assert Decimal("4.5") < diff.rate < Decimal("6.0")

    def test_service_fetcher_uses_corpus(self):
        from app.services.forex_data_service import ForexDataFetcher

        rate = ForexDataFetcher()._fetch_rate_from_api("EUR/USD")
        assert rate is not None
        assert Decimal("0.8") < rate < Decimal("1.6")  # a real fix, not 1.08 exact
        assert rate != Decimal("1.08")  # the old constant must be gone from the path
