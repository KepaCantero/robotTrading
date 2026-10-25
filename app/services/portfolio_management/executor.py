"""Execute a rebalance plan as diff-orders through the ONE live order path.

Requirements wired here:

- Diff orders (plan line 66): each trade is a quantity DELTA against the
  current position — never close-and-reopen.
- Fraccionado (requirement 9): quantities stay fractional on PaperAdapter
  (and Alpaca notional later); ``whole_shares`` is the fallback for brokers
  without fractions, sweeping the residual into cash.
- Intent-first (Fase 2 semantics): the plan is persisted as an event
  BEFORE the first order goes out, so a crash mid-rebalance leaves an
  auditable "what was intended", not just "what filled".
- Lot accounting: every BUY fill opens a lot; every SELL fill consumes
  lots FIFO, so the tax preview and the 2-month rule always see reality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from app.services.live_trading.broker_connector import BrokerConnector, OrderSide, OrderType
from app.services.live_trading.order_manager import OrderManager

from .models import RebalancePlan
from .paper_state import DEFAULT_PAPER_STATE_PATH, save_paper_state
from .store import PortfolioManagementStore

logger = logging.getLogger(__name__)

_QTY = Decimal("0.000001")


@dataclass
class ExecutionOutcome:
    """What actually happened when the plan hit the order path."""

    plan_id: str
    executed: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    total_traded: Decimal = Decimal("0")

    @property
    def ok(self) -> bool:
        return not self.failed


class RebalanceExecutor:
    """Sends a plan's trades through OrderManager (risk gates included)."""

    def __init__(
        self,
        store: PortfolioManagementStore,
        broker: BrokerConnector,
        order_manager: OrderManager | None = None,
        whole_shares: bool = False,
        paper_state_path: str = DEFAULT_PAPER_STATE_PATH,
    ) -> None:
        self.store = store
        self.broker = broker
        self.order_manager = order_manager or OrderManager(broker=broker)
        self.whole_shares = whole_shares
        self.paper_state_path = paper_state_path

    async def execute(self, plan: RebalancePlan, dry_run: bool = False) -> ExecutionOutcome:
        """Persist the intent, then place the diff-orders in plan order
        (sells before buys — proceeds fund the buys)."""
        outcome = ExecutionOutcome(plan_id=plan.event_id)

        if not plan.trades:
            await self.store.record_plan(plan, action="skipped")
            return outcome

        if dry_run:
            await self.store.record_plan(plan, action="planned")
            return outcome

        # Intent persisted BEFORE the first order goes out.
        await self.store.record_plan(plan, action="planned")

        for index, trade in enumerate(plan.trades):
            quantity = self._quantity(trade.quantity)
            if quantity <= 0:
                outcome.failed.append(
                    {
                        "symbol": trade.symbol,
                        "error": f"quantity {quantity} rounds to zero "
                        f"({'whole-share' if self.whole_shares else 'fractional'} mode)",
                    }
                )
                continue
            side = OrderSide.BUY if trade.side == "BUY" else OrderSide.SELL
            # Deterministic order_ref: a retried execution of the same plan
            # deduplicates at the broker instead of double-trading.
            order_ref = f"rebalance:{plan.event_id}:{index}"
            try:
                order = await self.order_manager.place_order(
                    symbol=trade.symbol,
                    side=side,
                    quantity=quantity,
                    order_type=OrderType.MARKET,
                    order_ref=order_ref,
                )
            except Exception as exc:  # noqa: BLE001 - one bad order must not abort the rest
                logger.exception("Rebalance order failed for %s", trade.symbol)
                outcome.failed.append({"symbol": trade.symbol, "error": str(exc)})
                continue

            if order is None:
                rejection = getattr(self.order_manager, "last_rejection", "") or "rejected"
                outcome.failed.append({"symbol": trade.symbol, "error": rejection})
                continue

            fill_price = (
                order.avg_filled_price
                if order.avg_filled_price > 0
                else (order.price or trade.price)
            )
            await self._account_lots(trade.symbol, side, quantity, fill_price)
            outcome.executed.append(
                {
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": str(quantity),
                    "price": str(fill_price),
                    "order_id": order.order_id,
                }
            )
            outcome.total_traded += quantity * fill_price

        action = "executed" if outcome.ok else "rejected"
        await self.store.append_event(
            trigger=plan.trigger.value,
            action=action,
            reason=plan.summary,
            details={
                "plan_id": plan.event_id,
                "executed": outcome.executed,
                "failed": outcome.failed,
                "tax_total": str(plan.tax_total),
            },
        )
        if outcome.executed:
            self._persist_paper_state()
        if not outcome.ok:
            logger.warning(
                "Rebalance %s finished with %s failed order(s)", plan.event_id, len(outcome.failed)
            )
        return outcome

    def _persist_paper_state(self) -> None:
        """Snapshot the paper account so the next session (dashboard or
        runner, same or other process) continues from the same portfolio."""
        from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter

        adapter = self.broker.adapter
        if isinstance(adapter, PaperAdapter) and adapter.account is not None:
            save_paper_state(
                self.paper_state_path,
                adapter.account.cash_available,
                adapter.positions,
            )

    def _quantity(self, quantity: Decimal) -> Decimal:
        if self.whole_shares:
            return quantity.quantize(Decimal("1"))
        return quantity.quantize(_QTY)

    async def _account_lots(
        self, symbol: str, side: OrderSide, quantity: Decimal, price: Decimal
    ) -> None:
        """Keep the lot store in sync with fills — the tax side depends on it."""
        if price <= 0:
            return
        if side == OrderSide.BUY:
            await self.store.add_lot(symbol=symbol, quantity=quantity, purchase_price=price)
        else:
            await self.store.consume_lots_fifo(symbol=symbol, quantity=quantity)
