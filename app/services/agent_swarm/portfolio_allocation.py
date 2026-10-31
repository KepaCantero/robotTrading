"""Real portfolio allocation derived from the backtest's own trades.

The pipeline runs ONE strategy over real data; "how the capital is spread"
must answer with where that capital actually sat during the run — not with
a generic three-module "efficient frontier" built from guessed module
characteristics (that fabrication showed equal 33% weights and an invented
Sharpe of 92).

Metric: time-weighted average exposure per symbol. Every closed trade
contributes ``quantity × entry_price`` over its holding period
``[entry, exit]``; a symbol's weight is its exposure-days share of the
total. The engine closes all positions at the end of the window (realised
P&L accounting), so weights describe the run, not a live book — the
allocation notes say so.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.portfolio_constructor.models import AllocationWeight, PortfolioAllocation


def _days(entry: str | None, exit_: str | None) -> Decimal:
    try:
        start = date.fromisoformat(str(entry)[:10])
        end = date.fromisoformat(str(exit_)[:10]) if exit_ else date.today()
    except ValueError:
        return Decimal("1")
    return Decimal(max(1, (end - start).days))


def allocation_from_backtest(
    profile_id: str,
    capital_eur: Decimal,
    trades_summary: list[dict],
    annual_return_pct: Decimal,
    sharpe_ratio: Decimal,
    max_drawdown_pct: Decimal,
    window_days: int | None = None,
) -> PortfolioAllocation:
    """Build the run's real allocation from its closed trades.

    ``window_days`` (the backtest window length) unlocks the honesty
    metrics: average cash fraction = 1 − Σ(exposure×days)/(capital×days)
    — the number FIX 4 compares against the <1% passive bar.
    """
    exposure_days: dict[str, Decimal] = {}
    total_exposure_days = Decimal("0")
    for trade in trades_summary:
        symbol = str(trade.get("symbol") or "").upper()
        if not symbol:
            continue
        try:
            notional = abs(Decimal(str(trade.get("entry_price") or 0))) * abs(
                Decimal(str(trade.get("quantity") or 0))
            )
        except ArithmeticError:
            continue
        held = _days(trade.get("entry_time"), trade.get("exit_time"))
        exposure_days[symbol] = exposure_days.get(symbol, Decimal("0")) + notional * held
        total_exposure_days += notional * held

    total = total_exposure_days
    if total <= 0 or not exposure_days:
        raise ValueError("no trade exposure to allocate from")

    allocations = [
        AllocationWeight(
            module_name=symbol,
            weight_pct=(weight / total * Decimal("100")).quantize(Decimal("0.01")),
            capital_allocation_eur=(capital_eur * weight / total).quantize(Decimal("0.01")),
            rationale="Time-weighted average exposure in the real backtest",
        )
        for symbol, weight in sorted(exposure_days.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    weights = [a.weight_pct / Decimal("100") for a in allocations]
    hhi = sum((w * w for w in weights), Decimal("0"))
    effective_names = Decimal("1") / hhi if hhi > 0 else Decimal("1")
    diversification = (effective_names / Decimal(len(weights))).quantize(Decimal("0.01"))

    #: FIX 4: ¿fue ESTE run el pasivo 1/N? desviación máxima de manga vs
    #: 1/N (en pp) y % medio de caja (lo que no estuvo invertido)
    unit = Decimal("100") / Decimal(len(allocations))
    max_deviation = max(abs(a.weight_pct - unit) for a in allocations)
    avg_cash_pct: Decimal | None = None
    if window_days and window_days > 0:
        deployed_fraction = total_exposure_days / (capital_eur * Decimal(window_days))
        avg_cash_pct = (Decimal("1") - min(Decimal("1"), deployed_fraction)) * Decimal("100")

    return PortfolioAllocation(
        success=True,
        profile_id=profile_id,
        total_capital_eur=capital_eur,
        allocations=allocations,
        allocation_method="backtest_positions",
        expected_portfolio_return_pct=annual_return_pct,
        expected_portfolio_sharpe=sharpe_ratio,
        expected_portfolio_drawdown_pct=max_drawdown_pct,
        diversification_ratio=diversification,
        optimization_notes=(
            f"Average exposure over {len(trades_summary)} real trades; all positions "
            "were closed at the end of the window (realised-P&L accounting)."
        ),
        max_weight_deviation_pct=max_deviation.quantize(Decimal("0.01")),
        avg_cash_pct=avg_cash_pct.quantize(Decimal("0.01")) if avg_cash_pct is not None else None,
    )
