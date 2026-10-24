"""Fase 2 order path (hallazgos A04/A05/A06/A16).

Acceptance from docs/audits/2026-10-24/auditoria_general_A01-A24.md:

- A04: a STOP with stop_price but no price GOES THROUGH the risk validator
  (0 risk calls before, 1 broker call); validation is unconditional.
- A05: MARKET orders validate and execute at a REAL quote — the
  Decimal("100") placeholder is gone; missing/stale quotes reject the order.
- A06: reservations held while an order is in flight are released on
  terminal states (fill, cancel).
- A16: the API answers REJECTED with the real reason (HTTP 422) when the
  order never reached the broker — never a fake SUBMITTED.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.api.live_trading import router
from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerOrder,
    BrokerQuote,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
)
from app.services.live_trading.order_manager import OrderManager, get_order_manager_for_api
from app.services.live_trading.risk_gates import RiskGates


class OrderPathBroker:
    """Async double: 100k account, no positions, configurable quotes."""

    def __init__(self, quotes: dict[str, BrokerQuote] | None = None):
        self.quotes = quotes or {}
        self.sent: list[dict] = []
        self.orders: dict[str, BrokerOrder] = {}
        self._seq = 0
        self.terminal_on_placement = False

    async def get_account_info(self):
        return BrokerAccount(
            account_id="op",
            broker_type=BrokerType.PAPER,
            cash_available=Decimal("100000"),
            portfolio_value=Decimal("100000"),
            buying_power=Decimal("100000"),
            equity=Decimal("100000"),
            connected=True,
        )

    async def get_positions(self):
        return {}

    async def get_quote(self, symbol):
        return self.quotes.get(symbol)

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
        self.sent.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "price": price,
                "stop_price": stop_price,
                "client_order_id": client_order_id,
            }
        )
        self._seq += 1
        status = OrderStatus.FILLED if self.terminal_on_placement else OrderStatus.SUBMITTED
        order = BrokerOrder(
            order_id=f"op_{self._seq}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=status,
            client_order_id=client_order_id,
        )
        self.orders[order.order_id] = order
        return order

    async def cancel_order(self, order_id):
        self.orders[order_id].status = OrderStatus.CANCELED
        return True


def fresh_quote(symbol: str, price: str) -> BrokerQuote:
    return BrokerQuote(
        symbol=symbol, price=Decimal(price), timestamp=datetime.utcnow(), source="test"
    )


def make_manager(broker: OrderPathBroker) -> OrderManager:
    return OrderManager(broker=broker, risk_gates=RiskGates(broker=broker))


class TestAlwaysValidateWithRealPrice:
    """A04 + A05."""

    @pytest.mark.asyncio
    async def test_stop_order_validates_with_stop_price(self):
        broker = OrderPathBroker(quotes={"SPY": fresh_quote("SPY", "400")})
        manager = make_manager(broker)
        captured: list[Decimal] = []
        original = manager.risk_gates.validate_order

        async def spy(**kwargs):
            captured.append(kwargs["price"])
            return await original(**kwargs)

        manager.risk_gates.validate_order = spy  # type: ignore[method-assign]

        order = await manager.place_order(
            "SPY",
            OrderSide.BUY,
            Decimal("1"),
            order_type=OrderType.STOP,
            stop_price=Decimal("410"),
        )
        assert order is not None
        assert captured == [Decimal("410")]  # the STOP trigger validated, not 100
        assert broker.sent[0]["stop_price"] == Decimal("410")

    @pytest.mark.asyncio
    async def test_market_order_validates_and_executes_at_quote(self):
        broker = OrderPathBroker(quotes={"SPY": fresh_quote("SPY", "400")})
        manager = make_manager(broker)

        order = await manager.place_order("SPY", OrderSide.BUY, Decimal("1"))

        assert order is not None
        assert order.price == Decimal("400")  # executed at the real quote
        assert broker.sent[0]["price"] == Decimal("400")

    @pytest.mark.asyncio
    async def test_market_without_quote_rejected_fail_closed(self):
        broker = OrderPathBroker(quotes={})  # no quote for SPY
        manager = make_manager(broker)

        order = await manager.place_order("SPY", OrderSide.BUY, Decimal("1"))

        assert order is None
        assert broker.sent == []  # never reached the broker
        assert "No valid quote" in (manager.last_rejection or "")

    @pytest.mark.asyncio
    async def test_placeholder_price_100_is_gone(self):
        # A validator price of exactly 100 must come from a REAL quote, not
        # from the deleted default. A quote of 100 is honored; no quote at
        # all never validates at 100.
        broker = OrderPathBroker(quotes={"XYZ": fresh_quote("XYZ", "100")})
        manager = make_manager(broker)
        order = await manager.place_order("XYZ", OrderSide.BUY, Decimal("1"))
        assert order is not None
        assert order.price == Decimal("100")


class TestReservationLifecycle:
    """A06: reserve in flight, release on terminal."""

    @pytest.mark.asyncio
    async def test_in_flight_order_reserves_capacity(self):
        from decimal import Decimal as D

        broker = OrderPathBroker(
            quotes={"A": fresh_quote("A", "100"), "B": fresh_quote("B", "100")}
        )
        manager = make_manager(broker)
        manager.risk_gates.set_max_position_size(D("200000"))  # isolate the bp check
        # 100k buying power: a pending 60k buy leaves 40k — a second 60k
        # buy must fail while the reservation lives (60+60 > 100).
        first = await manager.place_order("A", OrderSide.BUY, D("600"))
        assert first is not None
        assert manager.risk_gates.reservations  # reservation held

        second = await manager.place_order("B", OrderSide.BUY, D("600"))
        assert second is None  # reserved capacity blocks it
        assert "pending buys" in (manager.last_rejection or "")

    @pytest.mark.asyncio
    async def test_filled_order_releases_reservation(self):
        broker = OrderPathBroker(quotes={"A": fresh_quote("A", "100")})
        broker.terminal_on_placement = True  # fills immediately
        manager = make_manager(broker)

        order = await manager.place_order("A", OrderSide.BUY, Decimal("50"))
        assert order is not None
        assert not manager.risk_gates.reservations  # released on FILLED

    @pytest.mark.asyncio
    async def test_canceled_order_releases_reservation(self):
        broker = OrderPathBroker(quotes={"A": fresh_quote("A", "100")})
        manager = make_manager(broker)

        order = await manager.place_order("A", OrderSide.BUY, Decimal("50"))
        assert manager.risk_gates.reservations
        await manager.cancel_order(order.order_id)
        assert not manager.risk_gates.reservations


class TestPaperQuoteSource:
    """PaperAdapter quote semantics (A05)."""

    @pytest.mark.asyncio
    async def test_abandoned_quote_rejected(self):
        from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter

        adapter = PaperAdapter()
        abandoned = datetime.utcnow() - timedelta(days=120)
        adapter.set_price_source(lambda sym: (Decimal("100"), abandoned))
        assert await adapter.get_quote("AAPL") is None

    @pytest.mark.asyncio
    async def test_moderately_stale_quote_marked_not_hidden(self):
        from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter

        adapter = PaperAdapter()
        stale = datetime.utcnow() - timedelta(days=30)
        adapter.set_price_source(lambda sym: (Decimal("100"), stale))
        quote = await adapter.get_quote("AAPL")
        assert quote is not None
        assert quote.source == "paper-source-STALE"  # surfaced, never silent

    @pytest.mark.asyncio
    async def test_fresh_quote_returned(self):
        from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter

        adapter = PaperAdapter()
        adapter.set_price_source(lambda sym: (Decimal("100"), datetime.utcnow()))
        quote = await adapter.get_quote("AAPL")
        assert quote is not None and quote.price == Decimal("100")

    @pytest.mark.asyncio
    async def test_market_fill_uses_quote_not_100(self):
        from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter

        adapter = PaperAdapter(initial_cash=Decimal("10000"), auto_fill_orders=True)
        adapter.set_price_source(lambda sym: (Decimal("431.25"), datetime.utcnow()))
        await adapter.connect()
        await adapter.place_order("SPY", OrderSide.BUY, Decimal("2"))  # MARKET, no price
        pos = adapter.positions["SPY"]
        assert pos.avg_price == Decimal("431.25")
        assert adapter.account.cash_available == Decimal("10000") - Decimal("862.50")

    @pytest.mark.asyncio
    async def test_market_fill_without_quote_raises(self):
        from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter

        adapter = PaperAdapter(initial_cash=Decimal("10000"), auto_fill_orders=True)
        adapter.set_price_source(lambda sym: None)
        await adapter.connect()
        with pytest.raises(ValueError, match="No valid quote"):
            await adapter.place_order("SPY", OrderSide.BUY, Decimal("1"))


class TestHonestApiResponse:
    """A16: REJECTED with reason, never a fake SUBMITTED."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv(
            "API_ACCESS_KEYS", "order-path-key-1c2d3e4f5a6b7c8d9e0f"
        )  # pragma: allowlist secret
        app = FastAPI()
        app.include_router(router)
        headers = {"X-API-Key": "order-path-key-1c2d3e4f5a6b7c8d9e0f"}

        rejected_manager = Mock()
        rejected_manager.place_order = AsyncMock(return_value=None)
        rejected_manager.last_rejection = "Daily loss 6.0% exceeds limit 5.0%"
        app.dependency_overrides[get_order_manager_for_api] = lambda: rejected_manager

        return TestClient(app), headers

    def test_rejected_order_returns_422_with_reason(self, client):
        c, headers = client
        response = c.post(
            "/live-trading/orders",
            params={"symbol": "SPY", "side": "buy", "quantity": 1},
            headers=headers,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["detail"]["status"] == "REJECTED"
        assert "Daily loss" in body["detail"]["reason"]

    def test_success_reports_real_status(self, client):
        c, headers = client
        manager = c.app.dependency_overrides[get_order_manager_for_api]()
        placed = Mock()
        placed.order_id = "ord-1"
        placed.status = OrderStatus.SUBMITTED
        manager.place_order = AsyncMock(return_value=placed)

        response = c.post(
            "/live-trading/orders",
            params={"symbol": "SPY", "side": "buy", "quantity": 1},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"
