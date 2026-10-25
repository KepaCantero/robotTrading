"""Spain tax preview for rebalancing sells (requirements 8 and 11).

Built on the repo's own SpainTaxEngine — progressive savings rates
(19/21/23%), no long/short distinction, loss compensation — plus the two
things the engine does not model yet:

- FIFO lot matching against the persisted purchase lots (portfolio_lots),
  because "what did these shares cost" is a per-lot question.
- Spain's 2-month repurchase rule (Art. 33.5.c LIS): a loss is NOT
  computable if the same listed security is reacquired within two months
  before or after the sale. SpainTaxEngine.applies_wash_sale() answers
  False for the US-style rule, which is right — but the Spanish rule is
  real and this module enforces it before planning a loss-making sell.

The preview is an ESTIMATE: the progressive rate is applied on this sell's
gain positioned in the year's savings base (``ytd_net_gains``), not on the
final declared base. It is shown BEFORE any confirmation, never after.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.tax_efficiency.engines.spain_tax_engine import SpainTaxEngine

from .models import LotSnapshot, SellTaxImpact

logger = logging.getLogger(__name__)

#: Art. 33.5.c LIS — two months around the sale for listed securities.
REPURCHASE_WINDOW_DAYS = 62


class SpainRebalanceTax:
    """Tax-aware sell side for the rebalance planner."""

    def __init__(self, engine: SpainTaxEngine | None = None) -> None:
        self.engine = engine or SpainTaxEngine()

    def preview_sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        lots: list[LotSnapshot],
        now: datetime | None = None,
        ytd_net_gains: Decimal = Decimal("0"),
    ) -> SellTaxImpact:
        """Estimated € tax if ``quantity`` shares of ``symbol`` were sold
        at ``price`` now. FIFO over ``lots``; a missing lot history yields
        a zero-basis estimate with an explicit note (never a silent 100%
        gain)."""
        now = now or datetime.utcnow()
        proceeds = (quantity * price).quantize(Decimal("0.01"))
        matched = _match_fifo(quantity, lots)
        notes: list[str] = []

        if matched:
            cost_basis = sum(
                (qty * lot_price for lot_price, qty, _ in matched), Decimal("0")
            ).quantize(Decimal("0.01"))
        else:
            cost_basis = Decimal("0")
            notes.append(
                "no purchase lots recorded for this position — tax preview assumes "
                "full gain; record lots to refine it"
            )

        gain = proceeds - cost_basis
        loss_rule_hit = gain < 0 and self._recent_purchase(matched, lots, now)
        if loss_rule_hit:
            notes.append(
                "Spain 2-month rule: reacquiring this ETF within two months of this "
                "loss-making sale would make the loss non-computable"
            )
            tax = Decimal("0")
            rate = Decimal("0")
        else:
            # Position this sell's gain in the year's savings base so the
            # marginal bracket reflects where the user actually sits.
            taxable = max(gain + max(ytd_net_gains, Decimal("0")), Decimal("0"))
            rate = self.engine._get_progressive_rate(taxable) if gain > 0 else Decimal("0")
            tax = (gain * rate).quantize(Decimal("0.01")) if gain > 0 else Decimal("0")

        return SellTaxImpact(
            symbol=symbol,
            quantity=quantity,
            price=price,
            proceeds=proceeds,
            cost_basis=cost_basis,
            gain=gain.quantize(Decimal("0.01")),
            tax=tax,
            marginal_rate=rate,
            loss_not_computable=loss_rule_hit,
            notes=notes,
        )

    @staticmethod
    def _recent_purchase(
        matched: list[tuple[Decimal, Decimal, datetime]],
        lots: list[LotSnapshot],
        now: datetime,
    ) -> bool:
        """True when any lot being sold (or any open lot of the symbol) was
        bought inside the 2-month window — selling it at a loss now, or
        buying back soon after, trips the rule."""
        window_start = now - timedelta(days=REPURCHASE_WINDOW_DAYS)
        for _, _, purchased_at in matched:
            if purchased_at >= window_start:
                return True
        return any(lot.purchased_at >= window_start for lot in lots)

    def order_sells_by_tax(self, impacts: list[SellTaxImpact]) -> list[SellTaxImpact]:
        """Cheapest to realise first — the planner sells the low-tax names
        before touching the expensive ones."""
        return sorted(impacts, key=lambda i: (i.tax, -i.proceeds, i.symbol))


def _match_fifo(
    quantity: Decimal, lots: list[LotSnapshot]
) -> list[tuple[Decimal, Decimal, datetime]]:
    """Oldest lots first: (purchase_price, matched_quantity, purchased_at)."""
    matched: list[tuple[Decimal, Decimal, datetime]] = []
    outstanding = quantity
    for lot in sorted(lots, key=lambda lot_: lot_.purchased_at):
        if outstanding <= 0:
            break
        take = min(lot.quantity, outstanding)
        matched.append((lot.purchase_price, take, lot.purchased_at))
        outstanding -= take
    return matched
