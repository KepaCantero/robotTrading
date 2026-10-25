"""Drift monitoring: how far each holding is from its target weight.

Absolute-band drift (requirement 5): a holding breaches when its current
weight differs from the target by more than ``band`` weight points — the
2-3% absolute band that is easy to explain and avoids churn. Relative
bands exist in the industry but are harder for a novice to reason about;
the absolute band is the default here.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from .models import DriftStatus, Holding


def compute_drift(
    target_holdings: list[Holding],
    current_values: dict[str, Decimal],
    total_value: Decimal,
    band: Decimal,
) -> list[DriftStatus]:
    """Current vs target weight for every symbol that has a target or a
    position. ``total_value`` is the whole portfolio (positions + cash) —
    weights only mean something against the total."""
    statuses: list[DriftStatus] = []
    if total_value <= 0:
        return statuses
    band_weight = band / Decimal("100")
    symbols = {h.symbol for h in target_holdings} | set(current_values)
    targets = {h.symbol: h.weight for h in target_holdings}
    for symbol in sorted(symbols):
        target_weight = targets.get(symbol, Decimal("0"))
        current_weight = (current_values.get(symbol, Decimal("0")) / total_value).quantize(
            Decimal("0.0001")
        )
        drift = (current_weight - target_weight).quantize(Decimal("0.0001"))
        statuses.append(
            DriftStatus(
                symbol=symbol,
                target_weight=target_weight,
                current_weight=current_weight,
                drift=drift,
                breached=abs(drift) > band_weight,
            )
        )
    return statuses


def in_cooldown(
    last_rebalance: datetime | None,
    cooldown_days: int,
    now: datetime,
) -> bool:
    """Requirement 10: minimum time between rebalances, checked BEFORE any
    other condition so short-term noise never triggers a trade."""
    if last_rebalance is None or cooldown_days <= 0:
        return False
    return now < last_rebalance + timedelta(days=cooldown_days)


def cooldown_ends_at(
    last_rebalance: datetime | None,
    cooldown_days: int,
) -> datetime | None:
    if last_rebalance is None:
        return None
    return last_rebalance + timedelta(days=cooldown_days)
