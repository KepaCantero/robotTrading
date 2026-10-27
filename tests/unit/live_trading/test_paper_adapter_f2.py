"""Fase 2/3 — PaperAdapter accounting invariants (hallazgo A10).

Acceptance from docs/audits/2026-10-24/auditoria_general_A01-A24.md (A10):
"saldo inicial 1.000, compra 1 a 100 y venta 1 a 100, saldo final 1.000".
The full-close early return used to skip the cash credit; these tests pin
cash conservation for full and partial closes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter
from app.services.live_trading.broker_connector import OrderSide


@pytest.fixture
async def paper():
    adapter = PaperAdapter(initial_cash=Decimal("1000"), auto_fill_orders=True)
    await adapter.connect()
    return adapter


@pytest.mark.asyncio
async def test_full_close_conserves_cash(paper):
    await paper.place_order("AAPL", OrderSide.BUY, Decimal("1"), price=Decimal("100"))
    await paper.place_order("AAPL", OrderSide.SELL, Decimal("1"), price=Decimal("100"))
    assert paper.account.cash_available == Decimal("1000")
    assert "AAPL" not in paper.positions


@pytest.mark.asyncio
async def test_partial_close_keeps_quantity_and_average(paper):
    await paper.place_order("AAPL", OrderSide.BUY, Decimal("2"), price=Decimal("100"))
    await paper.place_order("AAPL", OrderSide.SELL, Decimal("1"), price=Decimal("100"))
    pos = paper.positions["AAPL"]
    assert pos.quantity == Decimal("1")
    assert pos.avg_price == Decimal("100")
    # 1000 - 200 (buy) + 100 (partial sell) = 900
    assert paper.account.cash_available == Decimal("900")


@pytest.mark.asyncio
async def test_cash_never_increases_without_position(paper):
    """Selling more than held is rejected before any cash movement (no
    implicit short credit)."""
    await paper.place_order("AAPL", OrderSide.BUY, Decimal("1"), price=Decimal("100"))
    with pytest.raises(ValueError, match="insufficient position"):
        await paper.place_order("AAPL", OrderSide.SELL, Decimal("5"), price=Decimal("100"))
    assert paper.account.cash_available == Decimal("900")


@pytest.mark.asyncio
async def test_account_is_eur(paper):
    """The user's IBKR paper account is EUR-based: every € the dashboard
    prints must be the account's own currency (was USD until 2026-10-27)."""
    assert paper.account.currency == "EUR"
