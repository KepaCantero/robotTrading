"""The canonical rebalance planner.

One decision chain (requirements 5-14), in this exact order:

1. COOLDOWN first (requirement 10) — a profile change bypasses it with a
   warning (requirement 14); nothing else does.
2. NEW CASH → reactive rebalancing (requirement 6): buy the underweight,
   never sell. Cash is always the first line of defence.
3. Still out of band → proactive (requirement 7): sell the overweight and
   buy the underweight — but only if not in reactive-only mode
   (requirement 13) and only when the tax cost of a sell does not eat the
   benefit of the correction (requirement 8).
4. Every planned order is a DIFF order (quantity delta), fractional by
   default (requirement 9); sells below the minimum trade value are dust
   and are skipped.

The plan is preview-shaped: it is what the UI shows (with its tax impact,
requirement 11) BEFORE anything is executed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from .drift import compute_drift, in_cooldown
from .models import (
    DriftStatus,
    LotSnapshot,
    PlannedTrade,
    PlanStatus,
    RebalancePlan,
    RebalanceTrigger,
    SellTaxImpact,
    TargetPortfolio,
)

logger = logging.getLogger(__name__)

#: Orders below this value cost more than they fix (commissions, spread).
DEFAULT_MIN_TRADE_VALUE = Decimal("100")
#: A sell is vetoed when its estimated tax exceeds this share of the value
#: being rebalanced (requirement 8: know when NOT to rebalance).
DEFAULT_TAX_VETO_RATIO = Decimal("0.20")
#: Spain: a loss is not computable if the same security is repurchased
#: within two months (Art. 33.5.c LIS) — window in days.
TWO_MONTH_RULE_DAYS = 62
_QTY = Decimal("0.000001")


@dataclass
class PlanContext:
    """Everything the planner needs to decide. Values, not quantities —
    quantities are derived with reference prices at planning time."""

    target: TargetPortfolio
    #: symbol -> current market value of the position
    positions: dict[str, Decimal] = field(default_factory=dict)
    #: cash available for buying (deposits, collected dividends)
    cash: Decimal = Decimal("0")
    #: reference prices (symbol -> price) used to turn values into quantities
    prices: dict[str, Decimal] = field(default_factory=dict)
    #: open purchase lots per symbol (for the tax-aware sell side)
    lots: dict[str, list[LotSnapshot]] = field(default_factory=dict)
    last_rebalance: datetime | None = None
    now: datetime = field(default_factory=datetime.utcnow)
    #: profile change / manual button: bypasses cooldown, with a warning
    forced: bool = False
    forced_trigger: RebalanceTrigger = RebalanceTrigger.PROFILE_CHANGE
    min_trade_value: Decimal = DEFAULT_MIN_TRADE_VALUE
    tax_veto_ratio: Decimal = DEFAULT_TAX_VETO_RATIO
    #: realised savings-base gains so far this year (bracket positioning)
    ytd_net_gains: Decimal = Decimal("0")


def plan_rebalance(
    ctx: PlanContext,
    tax_preview=None,  # SpainRebalanceTax.preview_sell, injected to avoid cycles
) -> RebalancePlan:
    """Produce the plan. Pure function of the context — safe to call for a
    preview (requirement 11) and again for execution."""
    plan = RebalancePlan(event_id=str(uuid4()), planned_at=ctx.now)
    band = ctx.target.drift_band_pct

    # 1 ── cooldown gates everything except an explicit profile change.
    if not ctx.forced and in_cooldown(ctx.last_rebalance, ctx.target.cooldown_days, ctx.now):
        from .drift import cooldown_ends_at

        ends = cooldown_ends_at(ctx.last_rebalance, ctx.target.cooldown_days)
        plan.status = PlanStatus.SKIPPED
        plan.trigger = RebalanceTrigger.DRIFT
        plan.summary = (
            f"Cooling down until {ends:%Y-%m-%d %H:%M} — the portfolio rested "
            f"{ctx.target.cooldown_days} days between rebalances so it does not chase noise."
        )
        plan.reasons.append("cooldown active")
        return plan

    total_value = sum(ctx.positions.values(), Decimal("0")) + ctx.cash
    plan.drifts = compute_drift(ctx.target.holdings, ctx.positions, total_value, band)
    plan.max_abs_drift = max((abs(d.drift) for d in plan.drifts), default=Decimal("0"))
    band_weight = band / Decimal("100")

    drifted = {d.symbol: d for d in plan.drifts if d.breached}
    if not drifted and ctx.cash <= 0:
        plan.status = PlanStatus.SKIPPED
        plan.trigger = RebalanceTrigger.DRIFT
        plan.summary = _all_in_band_summary(plan.drifts, band)
        plan.reasons.append("all holdings inside the drift band")
        return plan

    target_weights = {h.symbol: h.weight for h in ctx.target.holdings}

    # 2 ── reactive: spend new cash on the underweight first (never sell).
    buys, cash_left = _reactive_buys(ctx, target_weights, total_value, band_weight)

    # Recompute drift as if the reactive buys had filled.
    projected = _projected_positions(ctx.positions, buys)
    projected_total = sum(projected.values(), Decimal("0")) + cash_left
    still_breached = [
        d
        for d in compute_drift(ctx.target.holdings, projected, projected_total, band)
        if d.breached
    ]

    if not still_breached:
        plan.status = PlanStatus.REACTIVE
        plan.trigger = ctx.forced_trigger if ctx.forced else RebalanceTrigger.CASH
        plan.trades = _to_trades(buys, ctx, side="BUY")
        plan.summary, reasons = _reactive_summary(plan.trades, cash_left)
        plan.reasons = reasons
        if ctx.forced:
            plan.reasons.append("forced: cooldown bypassed by a target/profile change")
        return plan

    # 3 ── proactive: sell the overweight (and exit anything the target no
    # longer holds), tax-aware, then buy the underweight with the proceeds.
    sells, vetoes = _tax_aware_sells(
        ctx, target_weights, projected, projected_total, band_weight, tax_preview
    )
    if ctx.target.reactive_only and sells:
        plan.status = PlanStatus.SKIPPED
        plan.trigger = RebalanceTrigger.DRIFT
        plan.summary = (
            "Reactive-only mode is on, so nothing is sold: the portfolio waits for "
            "new money to buy the underweight. "
            f"{len(still_breached)} holding(s) remain outside the ±{band}% band."
        )
        plan.reasons.append("reactive-only mode: sells suppressed")
        return plan

    proceeds = sum((value for _, value in sells), Decimal("0"))
    buys2, cash_left = _rebalance_buys(
        ctx, target_weights, projected, projected_total, cash_left + proceeds, band_weight
    )
    plan.status = PlanStatus.PROACTIVE
    plan.trigger = ctx.forced_trigger if ctx.forced else RebalanceTrigger.DRIFT
    plan.trades = _to_trades(sells, ctx, side="SELL") + _to_trades(buys2, ctx, side="BUY")
    plan.tax_total = sum((t.tax_impact.tax for t in plan.trades if t.tax_impact), Decimal("0"))
    plan.summary, reasons = _proactive_summary(plan, sells, buys2, vetoes, band)
    plan.reasons = reasons
    if ctx.forced:
        plan.reasons.append("forced: cooldown bypassed by a target/profile change")
    return plan


# ── Step 2: cash first ───────────────────────────────────────────────────


def _reactive_buys(
    ctx: PlanContext,
    target_weights: dict[str, Decimal],
    total_value: Decimal,
    band_weight: Decimal,
) -> tuple[list[tuple[str, Decimal]], Decimal]:
    """Allocate available cash to underweight holdings, most underweight
    first, until each is back inside the band. Buys only (requirement 6)."""
    cash = ctx.cash
    if cash <= 0 or total_value <= 0:
        return [], cash
    gaps: list[tuple[str, Decimal]] = []
    for symbol, weight in target_weights.items():
        current = ctx.positions.get(symbol, Decimal("0")) / total_value
        gap = (weight - current).quantize(Decimal("0.0001"))
        if gap > band_weight:
            gaps.append((symbol, gap * total_value))
    gaps.sort(key=lambda item: (-item[1], item[0]))
    buys: list[tuple[str, Decimal]] = []
    for symbol, needed in gaps:
        if cash <= 0:
            break
        spend = min(needed, cash)
        if spend >= ctx.min_trade_value:
            buys.append((symbol, spend))
            cash -= spend
    return buys, cash


# ── Step 3: tax-aware sell side ──────────────────────────────────────────


def _tax_aware_sells(
    ctx: PlanContext,
    target_weights: dict[str, Decimal],
    positions: dict[str, Decimal],
    total_value: Decimal,
    band_weight: Decimal,
    tax_preview=None,
) -> tuple[list[tuple[str, Decimal]], list[str]]:
    """Diff-sells that bring the overweight back inside the band — or exit
    a symbol the target no longer holds — ordered by ascending tax cost
    (cheapest to realise first) and vetoed when the tax exceeds the
    benefit of the correction or the 2-month Spain rule would make a loss
    non-computable."""
    candidates: list[tuple[str, Decimal]] = []
    for symbol in sorted(set(target_weights) | set(positions)):
        value = positions.get(symbol, Decimal("0"))
        if value <= 0:
            continue
        weight = target_weights.get(symbol)
        if weight is None:
            # not in the target anymore: full exit
            candidates.append((symbol, value))
            continue
        current = value / total_value if total_value > 0 else Decimal("0")
        excess_weight = (current - weight).quantize(Decimal("0.0001"))
        # sell only down to the band edge, not to the exact target
        over_band = excess_weight - band_weight
        if over_band > 0:
            candidates.append((symbol, min(over_band * total_value, value)))

    scored: list[tuple[Decimal, str, Decimal, SellTaxImpact | None]] = []
    vetoes: list[str] = []
    for symbol, value in candidates:
        if value < ctx.min_trade_value:
            continue
        price = ctx.prices.get(symbol)
        quantity = (value / price).quantize(_QTY) if price else Decimal("0")
        impact = None
        if tax_preview is not None and price and quantity > 0:
            impact = tax_preview(
                symbol,
                quantity,
                price,
                ctx.lots.get(symbol, []),
                ctx.now,
                ytd_net_gains=ctx.ytd_net_gains,
            )
        if impact is not None:
            if impact.loss_not_computable:
                vetoes.append(
                    f"{symbol}: sell vetoed — a loss within {TWO_MONTH_RULE_DAYS} days of "
                    "buying back is not computable in Spain"
                )
                continue
            if impact.tax > value * ctx.tax_veto_ratio:
                vetoes.append(
                    f"{symbol}: sell deferred — estimated tax €{impact.tax:.0f} is more than "
                    f"{ctx.tax_veto_ratio:.0%} of the €{value:.0f} being rebalanced"
                )
                continue
        scored.append((impact.tax if impact else Decimal("0"), symbol, value, impact))

    scored.sort(key=lambda item: (item[0], -item[2], item[1]))
    sells = [(symbol, value) for _, symbol, value, _ in scored]
    return sells, vetoes


# ── Step 3b: buys with proceeds ──────────────────────────────────────────


def _rebalance_buys(
    ctx: PlanContext,
    target_weights: dict[str, Decimal],
    positions: dict[str, Decimal],
    total_value: Decimal,
    budget: Decimal,
    band_weight: Decimal,
) -> tuple[list[tuple[str, Decimal]], Decimal]:
    """Buy the underweight back toward the band edge, funded by sale
    proceeds plus remaining cash. ``total_value`` is the WHOLE portfolio —
    buys just move value from cash to positions, so the denominator does
    not change."""
    buys: list[tuple[str, Decimal]] = []
    gaps: list[tuple[str, Decimal]] = []
    for symbol, weight in target_weights.items():
        target_value = weight * total_value
        gap = target_value - positions.get(symbol, Decimal("0")) - band_weight * total_value
        if gap > 0:
            gaps.append((symbol, gap))
    gaps.sort(key=lambda item: (-item[1], item[0]))
    for symbol, needed in gaps:
        if budget <= 0:
            break
        spend = min(needed, budget)
        if spend >= ctx.min_trade_value:
            buys.append((symbol, spend))
            budget -= spend
    return buys, budget


def _projected_positions(
    positions: dict[str, Decimal], buys: list[tuple[str, Decimal]]
) -> dict[str, Decimal]:
    projected = dict(positions)
    for symbol, value in buys:
        projected[symbol] = projected.get(symbol, Decimal("0")) + value
    return projected


def _to_trades(pairs: list[tuple[str, Decimal]], ctx: PlanContext, side: str) -> list[PlannedTrade]:
    trades: list[PlannedTrade] = []
    target_weights = {h.symbol: h.weight for h in ctx.target.holdings}
    for symbol, value in pairs:
        price = ctx.prices.get(symbol, Decimal("0"))
        quantity = (value / price).quantize(_QTY) if price > 0 else Decimal("0")
        weight = target_weights.get(symbol, Decimal("0"))
        trades.append(
            PlannedTrade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                value=quantity * price if price else value,
                reason=_trade_reason(symbol, side, value, weight, ctx.target.drift_band_pct),
            )
        )
    return trades


# ── Plain-language summaries (requirement 12) ───────────────────────────


def _pct(weight: Decimal) -> str:
    return f"{(weight * Decimal('100')):.1f}%"


def _trade_reason(symbol: str, side: str, value: Decimal, weight: Decimal, band: Decimal) -> str:
    if side == "BUY":
        return f"Buying €{value:.0f} of {symbol} to move it back toward its {_pct(weight)} target."
    return f"Selling €{value:.0f} of {symbol} to bring it back inside its ±{band}% band."


def _all_in_band_summary(drifts: list[DriftStatus], band: Decimal) -> str:
    worst = max(drifts, key=lambda d: abs(d.drift), default=None)
    if worst is None:
        return "Portfolio not started yet — nothing to rebalance."
    return (
        f"Nothing to do: every holding is inside its ±{band}% band "
        f"(largest drift {worst.symbol} at {_pct(abs(worst.drift))})."
    )


def _reactive_summary(trades: list[PlannedTrade], cash_left: Decimal) -> tuple[str, list[str]]:
    if not trades:
        return (
            "New cash arrived but every holding is already inside its band — "
            f"€{cash_left:.0f} stays in cash until the next deposit or drift."
        ), ["no underweight large enough to buy"]
    parts = [f"Buying €{t.value:.0f} of {t.symbol} with new cash" for t in trades]
    summary = "New money bought the underweight (no selling needed): " + "; ".join(parts) + "."
    if cash_left > 0:
        summary += f" €{cash_left:.0f} of dust stays in cash."
    return summary, [t.reason for t in trades]


def _proactive_summary(
    plan: RebalancePlan,
    sells: list[tuple[str, Decimal]],
    buys: list[tuple[str, Decimal]],
    vetoes: list[str],
    band: Decimal,
) -> tuple[str, list[str]]:
    reasons = [t.reason for t in plan.trades]
    reasons.extend(vetoes)
    sell_text = ", ".join(f"€{v:.0f} of {s}" for s, v in sells) or "nothing"
    buy_text = ", ".join(f"€{v:.0f} of {s}" for s, v in buys) or "nothing"
    tax_text = f" Estimated tax: €{plan.tax_total:.0f}." if plan.tax_total > 0 else ""
    summary = (
        f"Some holdings moved more than ±{band}% from their target, so the robot "
        f"rebalances: selling {sell_text} and buying {buy_text} back to target.{tax_text}"
    )
    if vetoes:
        summary += " Some sells were deferred to protect you from avoidable taxes."
    return summary, reasons
