"""Tests for the live-account gap service (real_gap).

Covers the paste parser (the portfolio project's holdings.csv shape),
the corpus pricing + ECB fx path, the buy-only dilution plan and the
trim tax estimate — with a tiny synthetic corpus so the numbers are
assertable, not eyeballed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.portfolio_management import real_gap
from app.services.portfolio_management.models import Holding

D = Decimal


def _write_csv(path, rows):
    lines = ["date,open,high,low,close,volume"]
    lines += [f"{d},1,1,1,{close},1000" for d, close in rows]
    path.write_text("\n".join(lines) + "\n")


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    hist = tmp_path / "historical"
    hist.mkdir()
    fx = tmp_path / "fx"
    fx.mkdir()
    # EUR-listed UCITS core at €100; the US stock at $50
    _write_csv(hist / "VWCE.csv", [("2026-10-28", "100.00")])
    _write_csv(hist / "VHYL.csv", [("2026-10-28", "50.00")])
    _write_csv(hist / "O.csv", [("2026-10-28", "50.00")])
    (fx / "ecb_exr.csv").write_text("date,currency,rate\n2026-10-23,USD,1.1200\n")
    monkeypatch.setattr(real_gap, "_CORPUS", hist)
    monkeypatch.setattr(real_gap, "_FX_CSV", fx / "ecb_exr.csv")
    monkeypatch.setattr(real_gap, "_DATA_DIR", tmp_path)
    return hist


PASTE = """ticker,quantity,avg_cost_eur,account,notes
VWCE,100.0,80.00,IBKR,base
VHYL,200.0,40.00,IBKR,renta
O,10.0,30.00,IBKR,REIT
CASH,500.0,1.00,IBKR,cash
BADLINE,not-a-number
"""


class TestParsePaste:
    def test_parses_positions_cash_and_skips_noise(self):
        positions, cash, skipped = real_gap.parse_holdings_paste(PASTE)
        assert [p.symbol for p in positions] == ["VWCE", "VHYL", "O"]
        assert cash == D("500.0")
        assert skipped == ["BADLINE,not-a-number"]

    def test_header_and_blanks_ignored(self):
        positions, cash, _ = real_gap.parse_holdings_paste(
            "\n\nticker,quantity,cost\n\n"
        )
        assert positions == [] and cash == 0


class TestPricing:
    def test_prices_eur_native_and_usd_via_ecb(self, corpus):
        snap = real_gap.RealSnapshot(
            positions=[
                real_gap.RealPosition("VWCE", D("100"), D("80")),
                real_gap.RealPosition("O", D("10"), D("30")),
            ]
        )
        values, total, unpriced, price_date = real_gap.price_snapshot(snap)
        # ECB 1.12 USD per EUR → USD→EUR = 1/1.12, quantised to 4 dp
        usd_eur = (D("1") / D("1.1200")).quantize(D("0.0001"))
        assert values["VWCE"] == D("10000.00")
        assert values["O"] == (D("10") * D("50.00") * usd_eur).quantize(D("0.01"))
        assert unpriced == []
        assert price_date == "2026-10-28"

    def test_unpriced_symbol_reported_never_guessed(self, corpus):
        snap = real_gap.RealSnapshot(
            positions=[real_gap.RealPosition("ZZZZ", D("1"), D("1"))]
        )
        values, _total, unpriced, _ = real_gap.price_snapshot(snap)
        assert values == {} and unpriced == ["ZZZZ"]


class TestGapAndPlans:
    def _snapshot(self):
        return real_gap.RealSnapshot(
            cash_eur=D("500"),
            positions=[
                real_gap.RealPosition("VWCE", D("100"), D("80")),  # €10,000
                real_gap.RealPosition("VHYL", D("200"), D("40")),  # €10,000
                real_gap.RealPosition("O", D("10"), D("30")),  # USD, ~€446
            ],
        )

    def test_gap_rows_and_outside_target(self, corpus):
        holdings = [
            Holding(symbol="VWCE", weight=D("0.50")),
            Holding(symbol="VHYL", weight=D("0.25")),
            Holding(symbol="IBTS", weight=D("0.25")),
        ]
        report = real_gap.compute_gap(holdings, self._snapshot())
        # total ≈ 10000 + 10000 + ~446 + 500 cash ≈ 20946
        assert report.total_eur > D("20000")
        by_symbol = {r.symbol: r for r in report.rows}
        assert by_symbol["VWCE"].gap_eur > 0  # target 50% > live ~47.7%
        # a sleeve not held yet is a FULL buy gap, never an unknown
        assert by_symbol["IBTS"].live_value_eur == 0
        assert by_symbol["IBTS"].gap_eur == (D("0.25") * report.total_eur).quantize(
            D("0.01")
        )
        assert [sym for sym, _ in report.outside_target] == ["O"]

    def test_buys_are_underweights_only_and_sum_to_money(self, corpus):
        holdings = [
            Holding(symbol="VWCE", weight=D("0.50")),
            Holding(symbol="VHYL", weight=D("0.25")),
            Holding(symbol="IBTS", weight=D("0.25")),
        ]
        report = real_gap.compute_gap(holdings, self._snapshot())
        plan = real_gap.plan_buys(report, D("3000"))
        assert plan, "there are underweights to fund"
        assert sum((amount for _, amount in plan), D("0")) == D("3000.00")
        symbols = [sym for sym, _ in plan]
        assert "VWCE" in symbols and "IBTS" in symbols
        # a sleeve at/over target never receives new money
        over = [r.symbol for r in report.rows if r.gap_eur is not None and r.gap_eur <= 0]
        assert all(sym not in symbols for sym in over)

    def test_trim_costs_estimate_tax_on_excess(self, corpus):
        holdings = [Holding(symbol="VHYL", weight=D("0.10"))]  # target far below live
        report = real_gap.compute_gap(holdings, self._snapshot())
        trims = real_gap.trim_costs(report, self._snapshot())
        assert len(trims) == 1 and trims[0].symbol == "VHYL"
        # avg cost 40 vs price 50 → gain 25% of the excess proceeds, taxed
        # at the marginal savings rate and quantised to cents
        trim = trims[0]
        qty_value = trim.quantity * D("50.00")
        expected_gain = (qty_value - trim.quantity * D("40")).quantize(D("0.01"))
        assert trim.est_tax_eur == (expected_gain * trim.marginal_rate).quantize(D("0.01"))


class TestPersistence:
    def test_roundtrip_per_slug(self, corpus, tmp_path):
        snap = real_gap.RealSnapshot(
            captured_at="2026-10-29T12:00",
            cash_eur=D("560.36"),
            fx_usd_eur=D("0.89"),
            positions=[real_gap.RealPosition("VWCE", D("224.882"), D("148.71"))],
        )
        real_gap.save_real_holdings("pytest-slug", snap)
        back = real_gap.load_real_holdings("pytest-slug")
        assert back is not None
        assert back.cash_eur == D("560.36")
        assert back.fx_usd_eur == D("0.89")
        assert back.positions[0].symbol == "VWCE"
        assert real_gap.load_real_holdings("no-such-slug") is None
