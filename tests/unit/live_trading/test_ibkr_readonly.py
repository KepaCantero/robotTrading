"""Read-only live viewing — the sanctioned exception to the DU-only rule.

Proves the exact contract promised for viewing a live account:
- the DEFAULT adapter still refuses non-DU accounts (no silent scope creep)
- read_only=True connects to a live/mixed account and reports it honestly
  (``is_paper_trading()`` is False — never a config flag)
- place_order and cancel_order raise ReadOnlyModeError BEFORE touching the
  socket, connected or not — the block is at the root, not a runtime check
- a DU account remains viewable in read-only mode too
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.live_trading.broker_adapters.ibkr_adapter import (
    AccountNotPaperError,
    IbkrAdapter,
    ReadOnlyModeError,
)
from app.services.live_trading.broker_connector import OrderSide


class FakeIB:
    """Trimmed stand-in for ib_insync.IB (same surface as test_ibkr_adapter_f3)."""

    def __init__(self, accounts="U9876543", positions=None, executions=None, portfolio=None):
        self._accounts = accounts
        self._positions = positions or []
        self._executions = executions or []
        self._portfolio = portfolio  # None → attribute absent (legacy fakes)
        self.connected = False
        self.disconnected = False
        self.placed: list[tuple] = []
        self.cancelled: list = []

    def connect(self, host, port, clientId=1, timeout=8):
        self.connected = True
        return self

    def disconnect(self):
        self.disconnected = True
        self.connected = False

    def managedAccounts(self):
        return self._accounts

    def accountSummary(self):
        # Spanish-style live account: EUR base, NetLiquidation variant
        return [
            SimpleNamespace(tag="TotalCashValue", value="25000.00", currency="EUR"),
            SimpleNamespace(tag="NetLiquidation", value="125000.00", currency="EUR"),
            SimpleNamespace(tag="BuyingPower", value="50000.00", currency="EUR"),
        ]

    def sleep(self, seconds):
        pass

    def positions(self):
        return self._positions

    def portfolio(self):
        """PortfolioItem stand-ins with broker marks, when requested."""
        if self._portfolio is None:
            return ()  # marks not arrived yet → adapter falls back
        return self._portfolio

    def reqExecutions(self):
        return self._executions

    def placeOrder(self, contract, order):
        order.orderId = len(self.placed) + 1
        self.placed.append((contract, order))
        return SimpleNamespace(order=order, orderStatus="Submitted")

    def cancelOrder(self, order):
        self.cancelled.append(order)

    @property
    def trades(self):
        return ()


def _adapter(fake: FakeIB, **kwargs) -> IbkrAdapter:
    return IbkrAdapter(ib_factory=lambda: fake, **kwargs)


class TestReadOnlyConnections:
    async def test_live_account_still_refused_without_read_only(self):
        """The exception must be explicit — default adapters never widen."""
        fake = FakeIB(accounts="U9876543")
        adapter = _adapter(fake)

        with pytest.raises(AccountNotPaperError, match="read-only viewing requires"):
            await adapter.connect()
        assert adapter.is_connected is False
        assert fake.disconnected is True

    async def test_live_account_connects_read_only(self):
        fake = FakeIB(accounts="U9876543")
        adapter = _adapter(fake, read_only=True)

        assert await adapter.connect() is True
        assert adapter.is_connected is True
        assert adapter.account.account_id == "U9876543"
        assert adapter.account.currency == "EUR"
        assert adapter.account.equity == Decimal("125000.00")
        assert adapter.is_paper_trading() is False  # honest, not a flag

    async def test_mixed_accounts_connect_read_only(self):
        fake = FakeIB(accounts="DU1234567,U9876543")
        adapter = _adapter(fake, read_only=True)

        assert await adapter.connect() is True
        assert adapter.is_connected is True

    async def test_paper_account_viewable_read_only(self):
        fake = FakeIB(accounts="DU1234567")
        adapter = _adapter(fake, read_only=True)

        assert await adapter.connect() is True
        assert adapter.is_paper_trading() is True

    async def test_read_only_reconcile_pulls_broker_positions(self):
        fake = FakeIB(
            accounts="U9876543",
            positions=[
                SimpleNamespace(contract=SimpleNamespace(symbol="SCHD"), position=10, avgCost=50.25)
            ],
        )
        adapter = _adapter(fake, read_only=True)
        await adapter.connect()

        positions = await adapter.get_positions()
        assert [p.symbol for p in positions] == ["SCHD"]
        assert positions[0].quantity == Decimal("10")
        assert positions[0].avg_price == Decimal("50.25")
        # bare positions carry no marks — zeros, never guesses
        assert positions[0].market_value == Decimal("0")

    async def test_reconcile_captures_broker_marks_when_available(self):
        """ib.portfolio() marks (marketValue/markPrice/PnL) reach BrokerPosition."""
        fake = FakeIB(
            accounts="U9876543",
            portfolio=[
                SimpleNamespace(
                    contract=SimpleNamespace(symbol="SCHD"),
                    position=10,
                    averageCost=50.25,
                    marketPrice=61.40,
                    marketValue=614.00,
                    unrealizedPNL=111.50,
                )
            ],
        )
        adapter = _adapter(fake, read_only=True)
        await adapter.connect()

        (pos,) = await adapter.get_positions()
        assert pos.market_value == Decimal("614.00")
        assert pos.current_price == Decimal("61.40")
        assert pos.unrealized_pl == Decimal("111.50")
        assert pos.unrealized_pl_pct == Decimal("111.50") / Decimal("614.00")

    async def test_marks_with_none_values_keep_zero_not_guesses(self):
        fake = FakeIB(
            accounts="U9876543",
            portfolio=[
                SimpleNamespace(
                    contract=SimpleNamespace(symbol="SCHD"),
                    position=10,
                    averageCost=50.0,
                    marketPrice=None,
                    marketValue=None,
                    unrealizedPNL=None,
                )
            ],
        )
        adapter = _adapter(fake, read_only=True)
        await adapter.connect()

        (pos,) = await adapter.get_positions()
        assert pos.market_value == Decimal("0")
        assert pos.current_price == Decimal("0")


class TestReadOnlyOrderBlock:
    async def test_place_order_blocked_at_root(self):
        fake = FakeIB(accounts="U9876543")
        adapter = _adapter(fake, read_only=True)
        await adapter.connect()

        with pytest.raises(ReadOnlyModeError, match="read-only session"):
            await adapter.place_order("SCHD", OrderSide.BUY, Decimal("1"))
        assert fake.placed == []  # nothing reached the socket

    async def test_place_order_blocked_even_before_connect(self):
        """The block is structural, not a connected-state runtime check."""
        adapter = _adapter(FakeIB(accounts="U9876543"), read_only=True)

        with pytest.raises(ReadOnlyModeError, match="read-only session"):
            await adapter.place_order("SCHD", OrderSide.BUY, Decimal("1"))

    async def test_cancel_order_blocked_at_root(self):
        fake = FakeIB(accounts="U9876543")
        adapter = _adapter(fake, read_only=True)
        await adapter.connect()

        with pytest.raises(ReadOnlyModeError, match="read-only session"):
            await adapter.cancel_order("1")
        assert fake.cancelled == []

    async def test_read_only_cannot_be_flipped_after_construction(self):
        """The mode is fixed at construction — no runtime widening path."""
        adapter = _adapter(FakeIB(accounts="U9876543"), read_only=True)
        adapter._read_only = False  # pylint: disable=protected-access

        # even direct attribute poking cannot smuggle an order past the
        # account guard: the default (non-read-only) path refuses U-accounts
        with pytest.raises(AccountNotPaperError):
            await adapter.connect()
