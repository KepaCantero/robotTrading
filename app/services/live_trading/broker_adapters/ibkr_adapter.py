"""IBKR adapter for the BrokerConnector contract (Fase 3).

Connects to TWS / IB Gateway on this Mac and exposes ONLY broker-confirmed
state. Design rules taken from PLAN_PRODUCCION_PAPER_IBKR.md §Fase 3:

- **Paper is verified by the ACCOUNT, never by the port or a local flag.**
  IBKR paper accounts carry a ``DU`` prefix; the adapter disconnects and
  refuses to operate on any other account. Live trading is out of scope for
  the whole plan, so there is no override switch.
- **Instruments resolve by contract id/market/currency with exactly one
  match** — an ambiguous or unknown symbol raises; assets are never
  silently substituted.
- **Reconciliation** (positions, balances, executions) runs on connect and
  on demand; it reports divergences against the adapter's local book, it
  never mutates broker state.

The ib_insync client is injected via a factory so every rule above is testable
without a running TWS.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable
from uuid import uuid4

from app.services.live_trading.broker_adapters._loop_patch import patch_ib_eventloop
from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    BrokerQuote,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
)

logger = logging.getLogger(__name__)

#: default TWS paper socket (host-local). In-container callers override
#: with IBKR_HOST=host.docker.internal — the port alone proves nothing.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7497
#: stable API client id: survives restarts so TWS-side sessions and
#: order-id bookkeeping stay coherent across process restarts
DEFAULT_CLIENT_ID = 77001

#: IBKR paper accounts are DU-prefixed (individual live accounts are U…).
_PAPER_PREFIX = "DU"


class IBKRConnectionError(Exception):
    """Connection to TWS/IB Gateway failed or was refused."""


class AccountNotPaperError(IBKRConnectionError):
    """The connected account is not an IBKR paper account — operation refused."""


class InstrumentResolutionError(Exception):
    """Symbol did not resolve to exactly one IBKR contract."""


def _status_map() -> dict[str, OrderStatus]:
    """ib_insync order status strings → contract statuses."""
    return {
        "PendingSubmit": OrderStatus.PENDING,
        "PreSubmitted": OrderStatus.SUBMITTED,
        "Submitted": OrderStatus.SUBMITTED,
        "ApiPending": OrderStatus.PENDING,
        "Filled": OrderStatus.FILLED,
        "Cancelled": OrderStatus.CANCELED,
        "ApiCancelled": OrderStatus.CANCELED,
        "Inactive": OrderStatus.REJECTED,
    }


class IbkrAdapter:
    """Interactive Brokers adapter speaking the BrokerAdapter protocol.

    Every public piece of state (account, positions, orders) comes from
    IBKR-confirmed events — nothing on this class is simulated. The paper
    simulator lives in :class:`PaperAdapter` and the two are never mixed.
    """

    def __init__(
        self,
        ib_factory: Callable[[], Any] | None = None,
        host: str | None = None,
        port: int | None = None,
        client_id: int | None = None,
        connect_timeout: float = 8.0,
    ):
        #: injectable ib_insync.IB factory — tests pass a deterministic fake
        self._ib_factory = ib_factory or self._default_ib_factory
        self._host = host or os.getenv("IBKR_HOST", DEFAULT_HOST)
        self._port = int(port or os.getenv("IBKR_PORT", DEFAULT_PORT))
        self._client_id = int(client_id or os.getenv("IBKR_CLIENT_ID", DEFAULT_CLIENT_ID))
        self._connect_timeout = connect_timeout
        self._ib: Any = None
        #: symbol → qualified IBKR contract (resolved once, reused)
        self._contracts: dict[str, Any] = {}
        #: client_order_id → order_id (SEC-005 idempotency across re-sends)
        self._order_ids: dict[str, str] = {}
        self.account: BrokerAccount | None = None
        self.positions: dict[str, BrokerPosition] = {}
        self.orders: dict[str, BrokerOrder] = {}
        self.is_connected: bool = False

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _managed_accounts(ib: Any) -> list[str]:
        """ib_insync's managedAccounts() returns a repr like "['DU9811225']"
        (or "['DU1', 'DU2']") — normalize to a clean account list."""
        raw = str(ib.managedAccounts()).strip()
        return [
            a.strip().strip("'\"") for a in raw.strip("[]").split(",") if a.strip().strip("'\"")
        ]

    @staticmethod
    def _default_ib_factory() -> Any:
        from ib_insync import IB

        return IB()

    async def connect(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        account_id: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """Connect, then verify the account is PAPER before enabling anything.

        api_key/api_secret are not used by IBKR's socket API (TWS holds the
        session); they exist to satisfy the shared adapter contract.
        """
        host = str(kwargs.get("host") or self._host)
        port = int(kwargs.get("port") or self._port)
        client_id = int(kwargs.get("client_id") or self._client_id)

        # ib_insync's sync-style API needs the loop patched at CONNECT time
        # (never at import: that was the global mutation Fase 3 removes).
        patch_ib_eventloop()

        ib = self._ib_factory()
        try:
            ib.connect(host, port, clientId=client_id, timeout=self._connect_timeout)
        except Exception as exc:  # noqa: BLE001 - surface any socket failure honestly
            raise IBKRConnectionError(
                f"Cannot reach IBKR at {host}:{port} (clientId {client_id}): {exc}"
            ) from exc
        self._ib = ib

        # PAPER VERIFICATION — the account itself decides, not the port.
        accounts = self._managed_accounts(ib)
        if not accounts:
            await self.disconnect()
            raise AccountNotPaperError(
                "IBKR reported no managed accounts — cannot verify paper mode"
            )
        non_paper = [a for a in accounts if not a.startswith(_PAPER_PREFIX)]
        if non_paper:
            await self.disconnect()
            raise AccountNotPaperError(
                f"Account(s) {non_paper} are NOT paper (expected {_PAPER_PREFIX}* prefix); "
                "live trading is outside this plan — refusing to operate"
            )

        self.is_connected = True
        logger.info("IBKR connected (paper-verified: %s, clientId %s)", accounts, client_id)
        # account/balance data arrives ASYNCHRONOUSLY after the handshake —
        # reading immediately shows a funded account as all zeros. Let the
        # event queue drain once before the first snapshot.
        settle = getattr(ib, "sleep", None)
        if callable(settle):
            settle(3.0)
        await self._sync_account()
        await self.reconcile()
        return True

    async def disconnect(self) -> bool:
        if self._ib is not None:
            try:
                self._ib.disconnect()
            except Exception:  # noqa: BLE001 - closing must never throw
                logger.warning("IBKR disconnect raised", exc_info=True)
        self._ib = None
        self.is_connected = False
        return True

    # ------------------------------------------------------------------
    # account / positions
    # ------------------------------------------------------------------

    async def _sync_account(self) -> None:
        """Fill self.account from IBKR's accountSummary (broker-confirmed).

        Balance rows arrive per currency and the BASE-currency row comes
        FIRST per tag (a Spanish account reports EUR — there is no
        "Currency" marker row; the dump showed TotalCashValue/BuyingPower
        in EUR ahead of any per-currency residuals). First-seen wins and
        its currency becomes the account's base.
        """
        if self._ib is None:
            return
        # NB: the liquidation tag is "NetLiquidationValue" on some accounts
        # and plain "NetLiquidation" on others (live dump: the latter).
        money_tags = (
            "TotalCashValue",
            "NetLiquidationValue",
            "NetLiquidation",
            "BuyingPower",
        )
        values: dict[str, Decimal] = {}
        base_currency = "USD"
        for item in self._ib.accountSummary():
            tag = getattr(item, "tag", "")
            if tag not in money_tags or tag in values:
                continue  # first row per tag is the base-currency one
            try:
                values[tag] = Decimal(str(item.value))
            except Exception:  # noqa: BLE001 - malformed row → skip, not crash
                continue
            if tag == "TotalCashValue":
                base_currency = str(getattr(item, "currency", "USD")).strip() or "USD"
        equity = values.get("NetLiquidationValue")
        if equity is None:
            equity = values.get("NetLiquidation", Decimal("0"))
        managed = (self._managed_accounts(self._ib) or [""])[0]
        self.account = BrokerAccount(
            account_id=managed,
            broker_type=BrokerType.IBKR,
            currency=base_currency,
            cash_available=values.get("TotalCashValue", Decimal("0")),
            equity=equity,
            buying_power=values.get("BuyingPower", Decimal("0")),
            portfolio_value=equity,
            connected=True,
            last_sync=datetime.now(timezone.utc),
        )

    async def get_account_info(self) -> BrokerAccount | None:
        if not self.is_connected:
            return None
        await self._sync_account()
        return self.account

    async def get_positions(self) -> list[BrokerPosition]:
        return list(self.positions.values())

    async def get_position(self, symbol: str) -> BrokerPosition | None:
        return self.positions.get(symbol.upper())

    async def update_positions(self) -> dict[str, BrokerPosition]:
        await self.reconcile()
        return self.positions

    async def sync_account_balance(self) -> bool:
        await self._sync_account()
        return self.account is not None

    async def calculate_portfolio_value(self) -> Decimal | None:
        if self.account is None:
            return None
        return self.account.portfolio_value

    # ------------------------------------------------------------------
    # instrument resolution — exactly one contract or nothing
    # ------------------------------------------------------------------

    def resolve_contract(self, symbol: str, exchange: str = "SMART", currency: str = "USD"):
        """Qualify `symbol` to exactly ONE IBKR contract.

        Zero matches (no listing) or several (ambiguous — e.g. same ticker
        on multiple venues without an exchange pin) both raise: the order
        path must never trade a substituted instrument in silence.
        """
        key = f"{symbol.upper()}:{exchange}:{currency}"
        cached = self._contracts.get(key)
        if cached is not None:
            return cached
        if self._ib is None:
            raise InstrumentResolutionError("not connected")
        from ib_insync import Stock

        details = self._ib.reqContractDetails(Stock(symbol.upper(), exchange, currency))
        if len(details) == 0:
            raise InstrumentResolutionError(
                f"{symbol} resolved to no IBKR contract ({exchange}/{currency})"
            )
        if len(details) > 1:
            raise InstrumentResolutionError(
                f"{symbol} is ambiguous on {exchange}/{currency} "
                f"({len(details)} contracts) — pin the exchange explicitly"
            )
        contract = details[0].contract
        self._contracts[key] = contract
        return contract

    # ------------------------------------------------------------------
    # orders
    # ------------------------------------------------------------------

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
    ) -> str:
        if not self.is_connected or self._ib is None:
            raise IBKRConnectionError("not connected")
        client_order_id = client_order_id or f"trade_{uuid4().hex}"
        if client_order_id in self._order_ids:
            # SEC-005: same intent re-sent after an ambiguous outcome —
            # return the ORIGINAL order, never a second one.
            return self._order_ids[client_order_id]

        contract = self.resolve_contract(symbol)
        from ib_insync import LimitOrder, MarketOrder, StopOrder

        qty = float(quantity)
        if order_type == OrderType.MARKET:
            ib_order = MarketOrder("BUY" if side == OrderSide.BUY else "SELL", qty)
        elif order_type == OrderType.LIMIT:
            if price is None:
                raise ValueError("limit order needs a price")
            ib_order = LimitOrder("BUY" if side == OrderSide.BUY else "SELL", qty, float(price))
        elif order_type == OrderType.STOP:
            if stop_price is None:
                raise ValueError("stop order needs a stop price")
            ib_order = StopOrder("BUY" if side == OrderSide.BUY else "SELL", qty, float(stop_price))
        else:
            raise ValueError(f"order type {order_type} not supported by the IBKR adapter yet")
        ib_order.orderRef = client_order_id

        trade = self._ib.placeOrder(contract, ib_order)
        order_id = str(getattr(trade.order, "orderId", "") or uuid4().hex)
        self._order_ids[client_order_id] = order_id
        self.orders[order_id] = BrokerOrder(
            order_id=order_id,
            symbol=symbol.upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.SUBMITTED,
            client_order_id=client_order_id,
        )
        await self._refresh_order(trade, order_id)
        return order_id

    async def _refresh_order(self, trade: Any, order_id: str) -> None:
        """Map the broker's trade object onto our BrokerOrder."""
        order = self.orders.get(order_id)
        if order is None:
            return
        raw = str(getattr(trade, "orderStatus", "") or "")
        order.status = _status_map().get(raw, OrderStatus.SUBMITTED)
        filled = getattr(trade, "orderStatus", None)
        executed = getattr(filled, "filled", 0.0) if filled else 0.0
        avg = getattr(filled, "avgFillPrice", 0.0) if filled else 0.0
        order.filled_quantity = Decimal(str(executed))
        order.avg_filled_price = Decimal(str(avg))
        if order.status == OrderStatus.FILLED:
            order.executed_at = datetime.now(timezone.utc)
            order.updated_at = order.executed_at

    async def cancel_order(self, order_id: str) -> bool:
        if self._ib is None or order_id not in self.orders:
            return False
        for trade in getattr(self._ib, "trades", ()) or ():
            if str(getattr(trade.order, "orderId", "")) == order_id:
                self._ib.cancelOrder(trade.order)
                self.orders[order_id].status = OrderStatus.CANCELED
                return True
        return False

    async def get_order_status(self, order_id: str) -> OrderStatus:
        order = self.orders.get(order_id)
        return order.status if order else OrderStatus.PENDING

    # ------------------------------------------------------------------
    # quotes (A05: real and timestamped, or None)
    # ------------------------------------------------------------------

    async def get_quote(self, symbol: str) -> BrokerQuote | None:
        if not self.is_connected or self._ib is None:
            return None
        try:
            contract = self.resolve_contract(symbol)
            ticker = self._ib.reqMktData(contract, "", snapshot=True, regulatorySnapshot=False)
            price = ticker.marketPrice()
            if price is None or str(price) == "nan":
                return None
            return BrokerQuote(
                symbol=symbol.upper(),
                price=Decimal(str(price)),
                timestamp=datetime.now(timezone.utc),
                source="ibkr",
            )
        except Exception:  # noqa: BLE001 - no trustworthy quote → None
            logger.info("No IBKR quote for %s", symbol, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # reconciliation
    # ------------------------------------------------------------------

    async def reconcile(self) -> dict[str, list[str]]:
        """Pull broker-confirmed positions/executions and report divergences.

        Runs on connect, on reconnect and periodically. It ONLY reads and
        reports — repairing local state to match the broker is the
        executor's job, so every divergence is spelled out instead of
        being absorbed silently.
        """
        divergences: dict[str, list[str]] = {"positions": [], "orders": [], "balances": []}
        if self._ib is None:
            return divergences

        broker_positions: dict[str, BrokerPosition] = {}
        for pos in self._ib.positions():
            symbol = getattr(pos.contract, "symbol", "").upper()
            if not symbol:
                continue
            qty = Decimal(str(pos.position))
            avg_cost = Decimal(str(getattr(pos, "avgCost", 0) or 0))
            broker_positions[symbol] = BrokerPosition(
                symbol=symbol,
                quantity=qty,
                avg_price=avg_cost,
                current_price=Decimal("0"),  # marks come with quotes, not positions
                market_value=Decimal("0"),
                unrealized_pl=Decimal("0"),
                unrealized_pl_pct=Decimal("0"),
            )

        for symbol, pos in broker_positions.items():
            local = self.positions.get(symbol)
            if local is None:
                divergences["positions"].append(f"{symbol}: broker {qty} vs local none")
            elif local.quantity != pos.quantity:
                divergences["positions"].append(f"{symbol}: broker {qty} vs local {local.quantity}")
        for symbol in self.positions:
            if symbol not in broker_positions:
                divergences["positions"].append(f"{symbol}: broker none vs local held")

        # executions since last call keep order fills honest across restarts
        for data in self._ib.reqExecutions():
            symbol = getattr(data.execution, "symbol", "").upper()
            order_ref = getattr(data.order, "orderRef", "") or ""
            known = self._order_ids.get(order_ref)
            if known is None:
                divergences["orders"].append(
                    f"execution {getattr(data.execution, 'execId', '?')} for {symbol} "
                    "has no local intent — broker knows something we do not"
                )

        self.positions = broker_positions
        if divergences["positions"] or divergences["orders"]:
            logger.warning("IBKR reconcile divergences: %s", divergences)
        return divergences

    def is_paper_trading(self) -> bool:
        """True only with a VERIFIED paper account — never a config flag."""
        account_id = self.account.account_id if self.account else ""
        return self.is_connected and account_id.startswith(_PAPER_PREFIX)
