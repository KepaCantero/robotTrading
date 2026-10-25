"""Operational safety fixes for live trading (audit 2026-10-17, section 2).

Covers:
(a) Fail-closed broker factory: IBKR/unknown raise instead of silently
    falling back to PaperAdapter; get_broker_connector respects its argument.
(b) OrderManager.place_order serializes read-account -> validate -> send.
(c) Deterministic client_order_id derived from order_ref and propagated.
(d) Daily-loss circuit breaker fed from account equity.
(e) PaperAdapter rejects SELLs without a held position (no implicit shorts).
(f) IBAdapter no longer rejects legitimate resting limit orders.
"""

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import app.services.live_trading.broker_connector as broker_connector_module
from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter
from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerConnector,
    BrokerOrder,
    BrokerQuote,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
    get_broker_connector,
)
from app.services.live_trading.order_manager import OrderManager
from app.services.live_trading.risk_gates import RiskGates


@pytest.fixture
def connector_singleton_reset():
    """Isolate the BrokerConnector singleton for a test."""
    original = broker_connector_module._connector
    broker_connector_module._connector = None
    yield
    broker_connector_module._connector = original


class FakeEquityBroker:
    """Minimal broker double with mutable equity, tracing and send delay."""

    def __init__(self, equity=Decimal("100000")):
        self.equity = equity
        self.orders: dict[str, BrokerOrder] = {}
        self.trace: list[tuple[str, str]] = []
        self._seq = 0

    async def get_account_info(self):
        self.trace.append(("account-enter", ""))
        await asyncio.sleep(0.01)
        self.trace.append(("account-exit", ""))
        return BrokerAccount(
            account_id="fake",
            broker_type=BrokerType.PAPER,
            cash_available=self.equity,
            portfolio_value=self.equity,
            buying_power=self.equity,
            equity=self.equity,
            connected=True,
        )

    async def get_positions(self):
        return {}

    async def get_quote(self, symbol):
        # Fase 2 (A05): order managers validate MARKET orders against a real
        # quote; the double provides one so serialization/idempotency tests
        # exercise the full path.
        from datetime import datetime

        return BrokerQuote(
            symbol=symbol, price=Decimal("100"), timestamp=datetime.utcnow(), source="fake"
        )

    async def place_order(
        self,
        symbol,
        side,
        quantity,
        order_type=OrderType.MARKET,
        price=None,
        stop_price=None,
        client_order_id=None,
    ):
        self.trace.append(("send-enter", client_order_id))
        await asyncio.sleep(0.01)
        self.trace.append(("send-exit", client_order_id))
        self._seq += 1
        order = BrokerOrder(
            order_id=f"order_{self._seq}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            status=OrderStatus.SUBMITTED,
            client_order_id=client_order_id,
        )
        self.orders[order.order_id] = order
        return order

    async def cancel_order(self, order_id):
        return True

    async def get_order_status(self, order_id):
        return OrderStatus.SUBMITTED


def make_manager(broker):
    """OrderManager wired to a broker double (no singletons involved)."""
    return OrderManager(broker=broker, risk_gates=RiskGates(broker=broker))


# ============================================================================
# (a) Fail-closed broker factory
# ============================================================================


class TestFailClosedBrokerFactory:
    @pytest.mark.asyncio
    async def test_paper_connector_uses_paper_adapter(self):
        connector = BrokerConnector(BrokerType.PAPER)
        assert isinstance(connector.adapter, PaperAdapter)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("broker_type", [BrokerType.IBKR, BrokerType.INTERACTIVE_BROKERS])
    async def test_ibkr_wires_real_adapter_never_paper_fallback(self, broker_type):
        """Fase 3: the IBKR adapter exists and is wired. The rule that
        stays: a requested broker NEVER silently degrades to paper."""
        from app.services.live_trading.broker_adapters.ibkr_adapter import IbkrAdapter

        connector = BrokerConnector(broker_type)
        assert isinstance(connector.adapter, IbkrAdapter)
        assert not isinstance(connector.adapter, PaperAdapter)

    @pytest.mark.asyncio
    async def test_unsupported_broker_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported broker type"):
            BrokerConnector(BrokerType.TRADIER)

    @pytest.mark.asyncio
    async def test_get_broker_connector_respects_requested_type(self, connector_singleton_reset):
        connector = get_broker_connector(BrokerType.PAPER)
        assert connector.broker_type == BrokerType.PAPER
        assert isinstance(connector.adapter, PaperAdapter)

    @pytest.mark.asyncio
    async def test_get_broker_connector_refuses_mismatched_type(self, connector_singleton_reset):
        get_broker_connector(BrokerType.PAPER)
        with pytest.raises(ValueError, match="refusing to return it"):
            get_broker_connector(BrokerType.ALPACA)


# ============================================================================
# (b) place_order serialization (validate -> send atomic)
# ============================================================================


class TestPlaceOrderSerialized:
    @pytest.mark.asyncio
    async def test_concurrent_place_orders_do_not_interleave(self):
        broker = FakeEquityBroker()
        manager = make_manager(broker)

        await asyncio.gather(
            manager.place_order("AAPL", OrderSide.BUY, Decimal("1"), order_ref="sig-a"),
            manager.place_order("MSFT", OrderSide.BUY, Decimal("1"), order_ref="sig-b"),
        )

        assert len(broker.orders) == 2

        # Strict serialization: at no prefix may a section open while another
        # is still open (account reads and sends must never interleave).
        open_sections = 0
        for event, _ref in broker.trace:
            if event.endswith("enter"):
                open_sections += 1
                assert open_sections <= 1, f"sections interleaved: {broker.trace}"
            else:
                open_sections -= 1
                assert open_sections >= 0, f"unbalanced trace: {broker.trace}"

        assert len(broker.orders) == 2


# ============================================================================
# (c) Deterministic client_order_id
# ============================================================================


class TestDeterministicClientOrderId:
    @pytest.mark.asyncio
    async def test_client_order_id_derived_from_order_ref(self):
        broker = FakeEquityBroker()
        manager = make_manager(broker)

        order = await manager.place_order(
            "AAPL", OrderSide.BUY, Decimal("10"), order_ref="signal-123"
        )

        assert order is not None
        assert order.client_order_id == "signal-123:AAPL:buy:10"

    @pytest.mark.asyncio
    async def test_same_order_ref_dedups_at_paper_adapter(self):
        connector = BrokerConnector(BrokerType.PAPER)
        await connector.adapter.connect()
        manager = make_manager(connector)

        # Explicit price: this test is about idempotency, not quote
        # resolution (MARKET validation would fail closed on a stale CSV).
        first = await manager.place_order(
            "AAPL",
            OrderSide.BUY,
            Decimal("10"),
            price=Decimal("150"),
            order_ref="signal-123",
        )
        second = await manager.place_order(
            "AAPL",
            OrderSide.BUY,
            Decimal("10"),
            price=Decimal("150"),
            order_ref="signal-123",
        )

        assert first is not None and second is not None
        assert first.order_id == second.order_id
        assert len(connector.adapter.orders) == 1

    @pytest.mark.asyncio
    async def test_without_order_ref_ids_are_unique_per_call(self):
        broker = FakeEquityBroker()
        manager = make_manager(broker)

        await manager.place_order("AAPL", OrderSide.BUY, Decimal("10"))
        await manager.place_order("AAPL", OrderSide.BUY, Decimal("10"))

        ids = [o.client_order_id for o in broker.orders.values()]
        assert len(ids) == 2
        assert len(set(ids)) == 2


# ============================================================================
# (d) Daily-loss circuit breaker fed from equity
# ============================================================================


class TestDailyLossBreakerFed:
    @pytest.mark.asyncio
    async def test_equity_drop_over_limit_blocks_next_order(self):
        broker = FakeEquityBroker(equity=Decimal("100000"))
        manager = make_manager(broker)

        first = await manager.place_order("AAPL", OrderSide.BUY, Decimal("1"))
        assert first is not None
        assert manager.risk_gates.start_of_day_capital == Decimal("100000")

        broker.equity = Decimal("90000")  # -10% intraday
        second = await manager.place_order("MSFT", OrderSide.BUY, Decimal("1"))
        assert second is None
        assert manager.risk_gates.daily_pnl == Decimal("-10000")
        assert manager.risk_gates.circuit_breaker_active is True

        # Breaker stays active even if equity recovers
        broker.equity = Decimal("100000")
        third = await manager.place_order("GOOGL", OrderSide.BUY, Decimal("1"))
        assert third is None

    @pytest.mark.asyncio
    async def test_validate_order_rejects_after_negative_pnl_over_limit(self):
        broker = FakeEquityBroker(equity=Decimal("100000"))
        gates = RiskGates(broker=broker)
        gates.set_start_of_day_capital(Decimal("100000"))
        gates.update_daily_pnl(Decimal("-6000"))

        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("1"), Decimal("100"))

        assert result.passed is False
        assert any("Daily loss" in v for v in result.violations)
        assert gates.circuit_breaker_active is True

    @pytest.mark.asyncio
    async def test_missing_equity_does_not_break_order_flow(self):
        broker = FakeEquityBroker(equity=None)
        manager = make_manager(broker)

        # Missing equity: breaker feeding is skipped (no crash, no baseline),
        # and risk gates fail closed on their own daily-loss check.
        order = await manager.place_order("AAPL", OrderSide.BUY, Decimal("1"))

        assert order is None
        assert manager.risk_gates.start_of_day_capital == Decimal("0")

        # Once equity is available again, orders flow normally
        broker.equity = Decimal("100000")
        recovered = await manager.place_order("AAPL", OrderSide.BUY, Decimal("1"))
        assert recovered is not None
        assert manager.risk_gates.start_of_day_capital == Decimal("100000")


# ============================================================================
# (e) PaperAdapter: SELL without position rejected
# ============================================================================


class TestPaperSellWithoutPosition:
    @pytest.mark.asyncio
    async def test_sell_without_position_rejected(self):
        adapter = PaperAdapter()
        await adapter.connect()

        with pytest.raises(
            ValueError, match="insufficient position: cannot sell 10 of AAPL, held 0"
        ):
            await adapter.place_order("AAPL", OrderSide.SELL, Decimal("10"))

        assert len(adapter.orders) == 0
        assert adapter.account.cash_available == Decimal("100000")

    @pytest.mark.asyncio
    async def test_sell_more_than_held_rejected(self):
        adapter = PaperAdapter(auto_fill_orders=True)
        await adapter.connect()
        await adapter.place_order("AAPL", OrderSide.BUY, Decimal("10"), price=Decimal("100"))

        with pytest.raises(ValueError, match="held 10"):
            await adapter.place_order("AAPL", OrderSide.SELL, Decimal("15"), price=Decimal("100"))

        # No phantom cash from the rejected sell
        assert adapter.account.cash_available == Decimal("99000")

    @pytest.mark.asyncio
    async def test_sell_within_position_succeeds(self):
        adapter = PaperAdapter(auto_fill_orders=True)
        await adapter.connect()
        await adapter.place_order("AAPL", OrderSide.BUY, Decimal("10"), price=Decimal("100"))

        order_id = await adapter.place_order(
            "AAPL", OrderSide.SELL, Decimal("4"), price=Decimal("100")
        )

        assert order_id in adapter.orders
        assert adapter.positions["AAPL"].quantity == Decimal("6")
        # Buy 10@100 then sell 4@100: cash must reflect both legs
        assert adapter.account.cash_available == Decimal("99400")

    @pytest.mark.asyncio
    async def test_order_manager_rejects_sell_without_position(self):
        connector = BrokerConnector(BrokerType.PAPER)
        await connector.adapter.connect()
        manager = make_manager(connector)

        order = await manager.place_order("MSFT", OrderSide.SELL, Decimal("50"))

        assert order is None
        assert manager.pending_orders == {}
        assert connector.adapter.account.cash_available == Decimal("100000")

    @pytest.mark.asyncio
    async def test_allow_shorting_flag_permits_bare_sell(self):
        adapter = PaperAdapter(allow_shorting=True)
        await adapter.connect()

        order_id = await adapter.place_order("AAPL", OrderSide.SELL, Decimal("10"))

        assert order_id in adapter.orders


# ============================================================================
# (f) IBAdapter: legitimate resting limit orders no longer rejected
# ============================================================================


class TestIBLimitOrderValidation:
    def _make_connection(self, monkeypatch):
        import app.services.live_trading.broker_adapters.ib_adapter as ib_adapter_module
        from app.services.live_trading.broker_adapters.ib_adapter import IBConnection

        conn = IBConnection(
            config={"host": "127.0.0.1", "port": 7497, "client_id": 999, "paper_trading": True}
        )
        conn.connected = True

        async def fake_summary():
            return {"NetLiquidation": {"value": 100000}}

        async def fake_market_data(symbol, **kwargs):
            return {"bid": 139.5, "ask": 140.2, "last": 140.0, "volume": 1000}

        async def no_sleep(_seconds):
            return None

        monkeypatch.setattr(conn, "get_account_summary", fake_summary)
        monkeypatch.setattr(conn, "get_market_data", fake_market_data)
        monkeypatch.setattr(conn, "_get_contract", lambda symbol, **kw: MagicMock())
        monkeypatch.setattr(ib_adapter_module.asyncio, "sleep", no_sleep)

        trade = MagicMock()
        trade.fills = []
        trade.order.orderId = 42
        conn.ib = MagicMock()
        conn.ib.placeOrder.return_value = trade
        return conn

    @pytest.mark.asyncio
    async def test_buy_limit_below_ask_not_rejected(self, monkeypatch):
        conn = self._make_connection(monkeypatch)

        result = await conn.place_order(
            symbol="AAPL", side="BUY", quantity=10, order_type="LMT", price=140.0
        )

        assert "error" not in result, result
        assert result["status"] == "SUBMITTED"
        conn.ib.placeOrder.assert_called_once()

    @pytest.mark.asyncio
    async def test_sell_limit_above_bid_not_rejected(self, monkeypatch):
        conn = self._make_connection(monkeypatch)

        result = await conn.place_order(
            symbol="AAPL", side="SELL", quantity=10, order_type="LMT", price=141.0
        )

        assert "error" not in result, result
        conn.ib.placeOrder.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_positive_limit_price_rejected(self, monkeypatch):
        conn = self._make_connection(monkeypatch)

        result = await conn.place_order(
            symbol="AAPL", side="BUY", quantity=10, order_type="LMT", price=-5
        )

        assert result.get("error") == "Invalid limit price: -5"
        conn.ib.placeOrder.assert_not_called()
