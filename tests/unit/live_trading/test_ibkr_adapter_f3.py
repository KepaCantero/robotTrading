"""Fase 3 — IBKR adapter rules, tested without a running TWS.

Every plan rule gets a deterministic proof via a fake ib_insync client:
- paper is verified by the ACCOUNT (DU prefix), never the port or a flag
- live/mixed accounts are refused and disconnected
- instruments resolve to exactly one contract — never silently substituted
- re-sent intents (same client_order_id) never place a second order
- reconciliation reports divergences instead of absorbing them
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.live_trading.broker_adapters.ibkr_adapter import (
    AccountNotPaperError,
    IbkrAdapter,
    IBKRConnectionError,
    InstrumentResolutionError,
)
from app.services.live_trading.broker_connector import BrokerType, OrderSide, OrderType


class FakeIB:
    """Deterministic stand-in for ib_insync.IB covering the adapter surface."""

    def __init__(self, accounts="DU1234567", contracts=None, positions=None, executions=None):
        self._accounts = accounts
        self._contracts = contracts or {}
        self._positions = positions or []
        self._executions = executions or []
        self.connected = False
        self.disconnected = False
        self.placed: list[tuple] = []

    def connect(self, host, port, clientId=1, timeout=8):
        if self._accounts is None:  # simulate unreachable socket
            raise OSError("connection refused")
        self.connected = True
        return self

    def disconnect(self):
        self.disconnected = True
        self.connected = False

    def isConnected(self):
        return self.connected

    def managedAccounts(self):
        return self._accounts

    def accountSummary(self):
        return [
            SimpleNamespace(tag="TotalCashValue", value="100000.00", currency="USD"),
            SimpleNamespace(tag="NetLiquidationValue", value="110000.00", currency="USD"),
            SimpleNamespace(tag="BuyingPower", value="200000.00", currency="USD"),
            SimpleNamespace(tag="SomeOtherTag", value="1", currency="USD"),
            SimpleNamespace(tag="TotalCashValue", value="99.00", currency="EUR"),  # ignored
        ]

    def reqContractDetails(self, contract):
        return self._contracts.get(contract.symbol, [])

    def reqMktData(self, contract, what, snapshot=False, regulatorySnapshot=False):
        return SimpleNamespace(marketPrice=lambda: float("nan"))

    def positions(self):
        return self._positions

    def reqExecutions(self):
        return self._executions

    def placeOrder(self, contract, order):
        trade = SimpleNamespace(order=order, orderStatus="Submitted")
        order.orderId = len(self.placed) + 1
        self.placed.append((contract, order))
        return trade

    @property
    def trades(self):
        return ()


def _adapter(fake: FakeIB) -> IbkrAdapter:
    return IbkrAdapter(ib_factory=lambda: fake)


class TestPaperVerification:
    async def test_du_account_connects_and_reports_paper(self):
        fake = FakeIB(accounts="DU1234567")
        adapter = _adapter(fake)

        assert await adapter.connect() is True
        assert adapter.is_connected
        assert adapter.is_paper_trading() is True
        assert adapter.account.account_id == "DU1234567"
        assert adapter.account.cash_available == Decimal("100000.00")
        assert adapter.account.equity == Decimal("110000.00")

    async def test_live_account_refused_and_disconnected(self):
        """Plan: the port proves nothing — a U-account must never operate."""
        fake = FakeIB(accounts="U9876543")
        adapter = _adapter(fake)

        with pytest.raises(AccountNotPaperError, match="NOT paper"):
            await adapter.connect()
        assert adapter.is_connected is False
        assert fake.disconnected is True

    async def test_mixed_accounts_refused(self):
        fake = FakeIB(accounts="DU1234567,U9876543")
        adapter = _adapter(fake)

        with pytest.raises(AccountNotPaperError):
            await adapter.connect()
        assert fake.disconnected is True

    async def test_no_managed_accounts_refused(self):
        fake = FakeIB(accounts="")
        adapter = _adapter(fake)

        with pytest.raises(AccountNotPaperError, match="no managed accounts"):
            await adapter.connect()

    async def test_unreachable_socket_raises_connection_error(self):
        adapter = _adapter(FakeIB(accounts=None))

        with pytest.raises(IBKRConnectionError, match="Cannot reach IBKR"):
            await adapter.connect()


class TestInstrumentResolution:
    async def test_exactly_one_contract_resolves_and_caches(self):
        detail = SimpleNamespace(
            contract=SimpleNamespace(symbol="SCHD", conId=123, exchange="SMART")
        )
        fake = FakeIB(contracts={"SCHD": [detail]})
        adapter = _adapter(fake)
        await adapter.connect()

        contract = adapter.resolve_contract("SCHD")
        assert contract.conId == 123
        # second resolution is served from cache (no re-qualification)
        assert adapter.resolve_contract("schd") is contract

    async def test_zero_matches_raises_never_substitutes(self):
        adapter = _adapter(FakeIB())
        await adapter.connect()

        with pytest.raises(InstrumentResolutionError, match="no IBKR contract"):
            adapter.resolve_contract("NOSUCH")

    async def test_ambiguous_matches_raise(self):
        fake = FakeIB(
            contracts={
                "TEF": [SimpleNamespace(contract=object()), SimpleNamespace(contract=object())]
            }
        )
        adapter = _adapter(fake)
        await adapter.connect()

        with pytest.raises(InstrumentResolutionError, match="ambiguous"):
            adapter.resolve_contract("TEF")


def _schd_contract():
    return {"SCHD": [SimpleNamespace(contract=SimpleNamespace(symbol="SCHD", conId=123))]}


class TestOrders:
    async def test_market_order_maps_and_places(self):
        fake = FakeIB(contracts=_schd_contract())
        adapter = _adapter(fake)
        await adapter.connect()

        order_id = await adapter.place_order(
            "SCHD", OrderSide.BUY, Decimal("10"), client_order_id="trade_abc"
        )
        assert order_id in adapter.orders
        order = adapter.orders[order_id]
        assert order.symbol == "SCHD"
        assert order.client_order_id == "trade_abc"
        contract, ib_order = fake.placed[0]
        assert ib_order.action == "BUY"
        assert ib_order.totalQuantity == 10.0
        assert ib_order.orderRef == "trade_abc"

    async def test_resend_same_intent_returns_original_never_duplicates(self):
        """SEC-005: ambiguous-outcome retry must not double the order."""
        fake = FakeIB(contracts=_schd_contract())
        adapter = _adapter(fake)
        await adapter.connect()

        first = await adapter.place_order(
            "SCHD", OrderSide.BUY, Decimal("10"), client_order_id="trade_same"
        )
        second = await adapter.place_order(
            "SCHD", OrderSide.BUY, Decimal("10"), client_order_id="trade_same"
        )
        assert first == second
        assert len(fake.placed) == 1

    async def test_limit_order_requires_price(self):
        adapter = _adapter(FakeIB(contracts=_schd_contract()))
        await adapter.connect()

        with pytest.raises(ValueError, match="needs a price"):
            await adapter.place_order("SCHD", OrderSide.BUY, Decimal("1"), OrderType.LIMIT)

    async def test_not_connected_refuses_to_trade(self):
        adapter = _adapter(FakeIB())

        with pytest.raises(IBKRConnectionError, match="not connected"):
            await adapter.place_order("SCHD", OrderSide.BUY, Decimal("1"))


class TestReconciliation:
    async def test_broker_position_missing_locally_is_reported(self):
        """Connect reconciles an empty book; a position appearing at the
        broker afterwards must surface as a divergence, not be absorbed."""
        fake = FakeIB()
        adapter = _adapter(fake)
        await adapter.connect()

        fake._positions.append(
            SimpleNamespace(
                contract=SimpleNamespace(symbol="SCHD"),
                position=10.0,
                avgCost=75.0,
            )
        )

        div = await adapter.reconcile()
        assert div["positions"] == ["SCHD: broker 10.0 vs local none"]
        # and the broker-confirmed book is what the adapter now exposes
        assert adapter.positions["SCHD"].quantity == Decimal("10")

    async def test_local_position_gone_at_broker_is_reported(self):
        fake = FakeIB()
        adapter = _adapter(fake)
        await adapter.connect()
        adapter.positions = {
            "VYM": SimpleNamespace(quantity=Decimal("5")),
        }

        div = await adapter.reconcile()
        assert div["positions"] == ["VYM: broker none vs local held"]

    async def test_execution_without_local_intent_is_reported(self):
        fake = FakeIB(
            executions=[
                SimpleNamespace(
                    execution=SimpleNamespace(execId="e1", symbol="SCHD"),
                    order=SimpleNamespace(orderRef="unknown_ref"),
                )
            ]
        )
        adapter = _adapter(fake)
        await adapter.connect()

        div = await adapter.reconcile()
        assert any("no local intent" in d for d in div["orders"])

    async def test_clean_state_reports_no_divergences(self):
        adapter = _adapter(FakeIB())
        await adapter.connect()

        div = await adapter.reconcile()
        assert div == {"positions": [], "orders": [], "balances": []}


class TestQuoteFailsClosed:
    async def test_nan_price_returns_none(self):
        adapter = _adapter(FakeIB())
        await adapter.connect()

        assert await adapter.get_quote("SCHD") is None


class TestConnectorWiring:
    def test_broker_connector_instantiates_ibkr_adapter(self):
        import app.services.live_trading.broker_connector as bc
        from app.services.live_trading.broker_connector import BrokerConnector, get_broker_connector

        connector = BrokerConnector(BrokerType.IBKR)
        assert isinstance(connector.adapter, IbkrAdapter)
        # singleton hygiene: drop it so other tests get a fresh connector
        bc._connector = None
        del get_broker_connector
