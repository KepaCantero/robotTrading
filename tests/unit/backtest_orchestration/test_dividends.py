"""Fase 4 — dividend income ledger (hallazgos D01/D04).

Acceptance from docs/audits/2026-10-24/auditoria_dividendos_D01-D12.md:

- D01: "dos carteras con igual Sharpe pero distinto efectivo distribuido
  deben distinguirse en el objetivo de renta" — the ledger derives income
  from real distribution events against the EXECUTED book, separate from
  total return.
- D04: missing distribution data is a NAMED gap ("qué métricas no son
  calculables"), never a constant-yield placeholder.
- Entitlements respect buy/sell execution times (ex-date accounting).
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.backtesting.dividends import (
    DEFAULT_WITHHOLDING_RATE,
    DistributionEvent,
    DividendLedger,
    coverage,
    load_distributions,
    units_held_at,
)


def make_trade(symbol, side, qty, entry_time, exit_time=None):
    """Minimal canonical-Trade double with the fields the ledger reads."""
    from types import SimpleNamespace

    return SimpleNamespace(
        symbol=symbol,
        side=side,
        quantity=Decimal(str(qty)),
        entry_time=entry_time,
        exit_time=exit_time,
    )


def write_events(tmp_path, symbol: str, events: list[tuple[str, str]]) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    with (tmp_path / f"{symbol}.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["date", "amount", "currency", "source"])
        writer.writeheader()
        writer.writerows(
            {"date": d, "amount": a, "currency": "USD", "source": "test"} for d, a in events
        )


JAN1 = datetime(2026, 1, 1)
DEC31 = datetime(2026, 12, 31)


class TestUnitsHeldAt:
    def test_buy_then_ex_date_entitled(self):
        trade = make_trade("SCHD", "buy", 10, datetime(2026, 1, 15))
        assert units_held_at([trade], "SCHD", datetime(2026, 3, 25)) == Decimal("10")

    def test_buy_after_ex_date_not_entitled(self):
        trade = make_trade("SCHD", "buy", 10, datetime(2026, 4, 2))
        assert units_held_at([trade], "SCHD", datetime(2026, 3, 25)) == Decimal("0")

    def test_position_window_entry_to_exit(self):
        # Engine trade shape: ONE buy record with entry/exit window. Held
        # strictly between entry and exit.
        trades = [
            make_trade("SCHD", "buy", 10, datetime(2026, 1, 15), exit_time=datetime(2026, 6, 30)),
        ]
        assert units_held_at(trades, "SCHD", datetime(2026, 3, 25)) == Decimal("10")
        assert units_held_at(trades, "SCHD", datetime(2026, 7, 10)) == Decimal("0")

    def test_paired_sell_row_does_not_double_subtract(self):
        # The engine repeats the interval as a sell row: it must not open a
        # short nor cancel the buy.
        trades = [
            make_trade("SCHD", "buy", 10, datetime(2026, 1, 15), exit_time=datetime(2026, 9, 1)),
            make_trade("SCHD", "sell", 10, datetime(2026, 1, 15), exit_time=datetime(2026, 9, 1)),
        ]
        assert units_held_at(trades, "SCHD", datetime(2026, 3, 25)) == Decimal("10")

    def test_closed_position_via_exit_time(self):
        trades = [
            make_trade("SCHD", "buy", 10, datetime(2026, 1, 15), exit_time=datetime(2026, 3, 20)),
        ]
        assert units_held_at(trades, "SCHD", datetime(2026, 3, 25)) == Decimal("0")


class TestLedger:
    def test_net_income_with_withholding(self, tmp_path):
        write_events(tmp_path, "SCHD", [("2026-03-25", "0.25")])
        trades = [make_trade("SCHD", "buy", 100, datetime(2026, 1, 15))]

        entries, metrics = DividendLedger(withholding_rate=Decimal("0.15")).record(
            trades, ["SCHD"], JAN1, DEC31, data_dir=tmp_path
        )

        assert len(entries) == 1
        assert entries[0].units_entitled == Decimal("100")
        assert entries[0].gross == Decimal("25.00")
        assert entries[0].withholding == Decimal("3.75")
        assert entries[0].net == Decimal("21.25")
        assert metrics.net_total == Decimal("21.25")
        assert metrics.computable
        assert metrics.net_by_year[2026] == Decimal("21.25")
        assert metrics.income_on_initial_capital(Decimal("10000")) == Decimal("0.002125")

    def test_same_return_different_dividends_distinguish(self, tmp_path):
        """D01 acceptance: identical trades (identical return), different
        distribution events -> different income metrics."""
        write_events(tmp_path, "AAA", [("2026-06-01", "1.00")])
        write_events(tmp_path, "BBB", [("2026-06-01", "0.10")])
        trades_a = [make_trade("AAA", "buy", 10, datetime(2026, 1, 5))]
        trades_b = [make_trade("BBB", "buy", 10, datetime(2026, 1, 5))]

        ledger = DividendLedger()
        _, metrics_a = ledger.record(trades_a, ["AAA"], JAN1, DEC31, data_dir=tmp_path)
        _, metrics_b = ledger.record(trades_b, ["BBB"], JAN1, DEC31, data_dir=tmp_path)

        # Same exposure, same trade shape — income differs 10x
        assert metrics_a.net_total == 10 * (1 - DEFAULT_WITHHOLDING_RATE) * 10 / 10
        assert metrics_a.net_total > metrics_b.net_total * 5

    def test_missing_data_is_a_named_gap_never_a_yield(self, tmp_path):
        trades = [make_trade("NOEVENTS", "buy", 10, datetime(2026, 1, 5))]
        entries, metrics = DividendLedger().record(
            trades, ["NOEVENTS"], JAN1, DEC31, data_dir=tmp_path
        )
        assert entries == []
        assert not metrics.computable
        assert any("NOEVENTS" in gap for gap in metrics.coverage_gaps)
        assert "no computable" in metrics.coverage_gaps[0].lower()

    def test_assumptions_are_recorded(self, tmp_path):
        write_events(tmp_path, "SCHD", [("2026-03-25", "0.25")])
        trades = [make_trade("SCHD", "buy", 10, datetime(2026, 1, 5))]
        _, metrics = DividendLedger().record(trades, ["SCHD"], JAN1, DEC31, data_dir=tmp_path)
        assert any("ex-date" in a for a in metrics.assumptions)
        assert any("withholding" in a for a in metrics.assumptions)

    def test_events_outside_window_ignored(self, tmp_path):
        write_events(tmp_path, "SCHD", [("2025-12-31", "0.25"), ("2026-06-01", "0.25")])
        trades = [make_trade("SCHD", "buy", 10, datetime(2025, 1, 5))]
        entries, _ = DividendLedger().record(trades, ["SCHD"], JAN1, DEC31, data_dir=tmp_path)
        assert len(entries) == 1
        assert entries[0].ex_date == date(2026, 6, 1)


class TestEventModel:
    def test_non_positive_amount_rejected(self):
        with pytest.raises(ValueError):
            DistributionEvent(symbol="X", ex_date=date(2026, 1, 1), amount_per_share=Decimal("0"))

    def test_load_returns_sorted_events(self, tmp_path):
        write_events(tmp_path, "SCHD", [("2026-06-01", "0.25"), ("2026-03-25", "0.24")])
        events = load_distributions("SCHD", tmp_path)
        assert [e.ex_date for e in events] == [date(2026, 3, 25), date(2026, 6, 1)]

    def test_coverage_of_missing_symbol(self, tmp_path):
        cov = coverage("MISSING", tmp_path)
        assert not cov.has_data and cov.events == 0

    def test_real_corpus_has_schd(self):
        """The downloaded corpus is present and non-trivial (SCHD ~60 quarterly)."""
        events = load_distributions("SCHD")
        assert len(events) > 40
        assert events[0].ex_date < events[-1].ex_date
