"""Spain tax preview: progressive brackets, FIFO lots, 2-month rule."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.services.portfolio_management.models import LotSnapshot
from app.services.portfolio_management.tax import SpainRebalanceTax

D = Decimal


def _lot(qty: str, price: str, when: datetime, lot_id: str = "l1") -> LotSnapshot:
    return LotSnapshot(
        lot_id=lot_id,
        symbol="SCHD",
        quantity=D(qty),
        purchase_price=D(price),
        purchased_at=when,
    )


def test_fifo_gain_across_two_lots():
    tax = SpainRebalanceTax()
    lots = [
        _lot("10", "80", datetime(2024, 1, 1), "a"),
        _lot("10", "90", datetime(2024, 6, 1), "b"),
    ]
    impact = tax.preview_sell("SCHD", D("15"), D("100"), lots, now=datetime(2026, 10, 24))
    # FIFO: 10 shares @80 (gain 200) + 5 @90 (gain 50) = 250 total gain
    assert impact.cost_basis == D("1250.00")
    assert impact.gain == D("250.00")
    # 250 € gain sits in the 19% bracket
    assert impact.marginal_rate == D("0.19")
    assert impact.tax == D("47.50")


def test_bracket_position_with_ytd_gains():
    tax = SpainRebalanceTax()
    lots = [_lot("10", "1", datetime(2020, 1, 1))]
    # 20,000 € gain on top of 20,000 € already realised this year puts the
    # savings base (40,000 €) in the second bracket — the engine's rate for
    # the whole base, so the preview matches the canonical SpainTaxEngine.
    impact = tax.preview_sell(
        "SCHD",
        D("10"),
        D("2001"),
        lots,
        now=datetime(2026, 10, 24),
        ytd_net_gains=D("20000"),
    )
    assert impact.marginal_rate == D("0.21")
    # and a small gain with no YTD history stays in the 19% bracket
    small = tax.preview_sell("SCHD", D("1"), D("2001"), lots, now=datetime(2026, 10, 24))
    assert small.marginal_rate == D("0.19")


def test_no_loss_no_tax_even_without_lots():
    tax = SpainRebalanceTax()
    impact = tax.preview_sell("SCHD", D("10"), D("100"), [], now=datetime(2026, 10, 24))
    assert impact.gain == D("1000.00")
    assert impact.tax == D("190.00")
    assert any("no purchase lots" in note for note in impact.notes)


def test_loss_is_zero_tax():
    tax = SpainRebalanceTax()
    lots = [_lot("10", "120", datetime(2024, 1, 1))]
    impact = tax.preview_sell("SCHD", D("10"), D("100"), lots, now=datetime(2026, 10, 24))
    assert impact.gain == D("-200.00")
    assert impact.tax == 0
    assert impact.loss_not_computable is False  # old lot: rule does not apply


def test_two_month_rule_flags_recent_purchase():
    tax = SpainRebalanceTax()
    now = datetime(2026, 10, 24)
    lots = [_lot("10", "120", now - timedelta(days=10))]
    impact = tax.preview_sell("SCHD", D("10"), D("100"), lots, now=now)
    assert impact.gain < 0
    assert impact.loss_not_computable is True
    assert impact.tax == 0
    assert any("2-month" in note for note in impact.notes)


def test_order_sells_by_tax_cheapest_first():
    tax = SpainRebalanceTax()
    now = datetime(2026, 10, 24)
    cheap = tax.preview_sell(
        "SCHD", D("1"), D("100"), [_lot("1", "99", datetime(2020, 1, 1))], now=now
    )
    expensive = tax.preview_sell(
        "VYM", D("1"), D("100"), [_lot("1", "10", datetime(2020, 1, 1))], now=now
    )
    ordered = tax.order_sells_by_tax([expensive, cheap])
    assert [i.symbol for i in ordered] == ["SCHD", "VYM"]
