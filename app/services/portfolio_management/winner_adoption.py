"""Adopt the target portfolio from the latest winning swarm run.

User decision (2026-10-24): the default "do it for me" portfolio is the one
the winning backtest actually held — not a hand-written model portfolio.
The winner rule is deterministic:

1. Scan finished swarm runs newest-first (swarm_runs.db, read-only).
2. A run is a winner when its deployment decision is APPROVED or
   CONDITIONAL and the T5 validation report did not fail.
3. Holdings come from the run's own portfolio payload (time-weighted
   exposure of its real trades), rescaled to sum 100%.
4. Concentration caps still bind (requirement 3): a single holding above
   the profile cap is clamped and the excess redistributed — the winner
   explains the portfolio, it does not override risk limits.

When no winner exists yet (fresh database), a curated seed per objective is
used instead. The seed is documented as REPLACEABLE: the first winning run
supersedes it automatically.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

import aiosqlite

from app.services.agent_swarm.store import DEFAULT_SWARM_DB_PATH

from .models import ASSET_CLASS, Holding, ProfileAnswers, TargetPortfolio

logger = logging.getLogger(__name__)

WINNER_STATUSES = {"APPROVED", "CONDITIONAL"}

_WEIGHT = Decimal("0.000001")  # quantisation for rescaled weights

#: Curated seed portfolios per objective — the fallback while no winning
#: run exists. Symbols come from the repo's own curated universes
#: (swarm.py DIVIDEND_ETF_UNIVERSE / LOW_VOL_UNIVERSE). One plain sentence
#: per ETF: requirement 2 says the robot must show WHY each ETF is there.
SEED_PORTFOLIOS: dict[str, list[tuple[str, Decimal, str]]] = {
    "MAXIMIZAR_DIVIDENDOS": [
        ("SCHD", Decimal("35"), "US dividend growers — the core income engine."),
        ("VYM", Decimal("20"), "High-yield US stocks — boosts today's income."),
        ("VIG", Decimal("15"), "Dividend aristocrats — steadier, faster-growing payouts."),
        ("VYMI", Decimal("15"), "International dividends — spreads income across regions."),
        ("BND", Decimal("15"), "Total bond market — the cushion when stocks fall."),
    ],
    "MAXIMIZAR_CAPITAL": [
        ("VTI", Decimal("40"), "All US stocks — the growth engine, ultra-low cost."),
        ("VIG", Decimal("25"), "Dividend growers — quality tilt for the long run."),
        ("VYMI", Decimal("15"), "International stocks — growth beyond the US."),
        ("BND", Decimal("20"), "Total bond market — smooths the ride."),
    ],
    "CAPITAL_PRESERVATION": [
        ("BND", Decimal("35"), "Total bond market — keeps capital steady."),
        ("VDC", Decimal("15"), "Consumer staples — people buy food in every market."),
        ("VPU", Decimal("15"), "Utilities — steady demand, low swings."),
        ("VHT", Decimal("15"), "Healthcare — demand does not follow the cycle."),
        ("VIG", Decimal("20"), "Dividend growers — the defensive equity core."),
    ],
    "BALANCED_GROWTH": [
        ("VTI", Decimal("30"), "All US stocks — the growth side."),
        ("SCHD", Decimal("25"), "Dividend growers — pays you while it grows."),
        ("VYMI", Decimal("15"), "International stocks — diversifies growth."),
        ("BND", Decimal("30"), "Total bond market — the stabiliser."),
    ],
    "INCOME_GENERATION": [
        ("SCHD", Decimal("30"), "US dividend growers — reliable, growing income."),
        ("VYM", Decimal("20"), "High-yield US stocks — maximises current payouts."),
        ("DVY", Decimal("10"), "Selected dividend stocks — extra yield."),
        ("VIG", Decimal("15"), "Dividend aristocrats — income that keeps rising."),
        ("BND", Decimal("25"), "Total bond market — steady interest, low risk."),
    ],
}


def seed_target(profile: ProfileAnswers) -> TargetPortfolio:
    """Build the curated fallback target for an objective."""
    seed = SEED_PORTFOLIOS.get(profile.objective, SEED_PORTFOLIOS["BALANCED_GROWTH"])
    target = TargetPortfolio(
        source="seed",
        strategy_name=None,
        decision_status=None,
        holdings=[
            Holding(symbol=symbol, weight=pct / Decimal("100"), rationale=rationale)
            for symbol, pct, rationale in seed
        ],
        profile=profile,
    )
    target.settings_from_risk_level()
    return target


async def latest_winner(db_path: str | Path = DEFAULT_SWARM_DB_PATH) -> dict[str, Any] | None:
    """The newest finished run with an APPROVED/CONDITIONAL deployment
    decision and green validation gates. Read-only query on swarm_runs.db
    (deliberately NOT via SwarmRunStore: this package must not mutate the
    agent-swarm cluster, and list_runs does not return results_json)."""
    path = Path(db_path)
    if not path.exists():
        return None
    async with aiosqlite.connect(f"file:{path}?mode=ro", uri=True) as db:
        cursor = await db.execute(
            "SELECT workflow_id, started_at, results_json FROM swarm_runs "
            "WHERE status != 'running' AND results_json IS NOT NULL "
            "ORDER BY started_at DESC"
        )
        rows = await cursor.fetchall()

    for workflow_id, started_at, results_json in rows:
        try:
            results = json.loads(results_json)
        except ValueError:
            continue
        if not isinstance(results, dict):
            continue
        decision = results.get("deployment_decision") or {}
        if not isinstance(decision, dict):
            continue
        if decision.get("status") not in WINNER_STATUSES:
            continue
        validation = results.get("validation")
        if isinstance(validation, dict) and validation.get("passed") is False:
            continue
        portfolio = results.get("portfolio") or {}
        allocations = portfolio.get("allocations") or []
        holdings = _holdings_from_allocations(allocations)
        if not holdings:
            continue
        return {
            "run_id": workflow_id,
            "started_at": started_at,
            "decision_status": decision.get("status"),
            "strategy_name": decision.get("strategy_name"),
            "holdings": holdings,
            "metrics": {
                "annual_return_pct": portfolio.get("expected_portfolio_return_pct"),
                "sharpe": portfolio.get("expected_portfolio_sharpe"),
                "max_drawdown_pct": portfolio.get("expected_portfolio_drawdown_pct"),
                "diversification": portfolio.get("diversification_ratio"),
            },
        }
    return None


def winner_from_results(run_id: str, results: dict[str, Any]) -> dict[str, Any] | None:
    """Winner-shaped dict from ONE run's results (the swarm page holds it
    in memory after a run): same shape `latest_winner` returns, so
    `build_target` consumes either interchangeably. None when the run is
    not adoptable (REJECTED decision or failed validation)."""
    decision = results.get("deployment_decision") or {}
    if not isinstance(decision, dict) or decision.get("status") not in WINNER_STATUSES:
        return None
    validation = results.get("validation")
    if isinstance(validation, dict) and validation.get("passed") is False:
        return None
    portfolio = results.get("portfolio") or {}
    holdings = _holdings_from_allocations(portfolio.get("allocations") or [])
    if not holdings:
        return None
    return {
        "run_id": run_id,
        "started_at": None,
        "decision_status": decision.get("status"),
        "strategy_name": decision.get("strategy_name"),
        "holdings": holdings,
        "metrics": {
            "annual_return_pct": portfolio.get("expected_portfolio_return_pct"),
            "sharpe": portfolio.get("expected_portfolio_sharpe"),
            "max_drawdown_pct": portfolio.get("expected_portfolio_drawdown_pct"),
            "diversification": portfolio.get("diversification_ratio"),
        },
    }


def _holdings_from_allocations(allocations: list[Any]) -> list[Holding]:
    """AllocationWeight dicts (module_name=symbol, weight_pct) -> Holdings
    rescaled to sum exactly 1."""
    parsed: list[tuple[str, Decimal]] = []
    for allocation in allocations:
        if not isinstance(allocation, dict):
            continue
        symbol = str(allocation.get("module_name") or "").upper()
        try:
            weight_pct = Decimal(str(allocation.get("weight_pct") or 0))
        except ArithmeticError:
            continue
        if symbol and weight_pct > 0:
            parsed.append((symbol, weight_pct))
    total = sum((w for _, w in parsed), Decimal("0"))
    if total <= 0:
        return []
    return [
        Holding(
            symbol=symbol,
            weight=(w / total).quantize(_WEIGHT),
            rationale="Where the capital actually sat in the winning backtest run.",
        )
        for symbol, w in parsed
    ]


def build_target(
    profile: ProfileAnswers,
    winner: dict[str, Any] | None,
) -> TargetPortfolio:
    """Winner-derived target when a winner exists, curated seed otherwise.
    Either way the profile's band, cooldown and concentration caps bind."""
    if winner:
        target = TargetPortfolio(
            source="swarm_winner",
            source_run_id=str(winner["run_id"]),
            strategy_name=winner.get("strategy_name"),
            decision_status=winner.get("decision_status"),
            holdings=list(winner["holdings"]),
            profile=profile,
        )
    else:
        target = seed_target(profile)
    target.settings_from_risk_level()
    _apply_concentration_caps(target)
    return target


def _apply_concentration_caps(target: TargetPortfolio) -> None:
    """Requirement 3: clamp any holding above the per-asset cap and any
    equity total above the per-type ceiling.

    Caps must be SATISFIABLE before they can bind: a 2-ETF winner under a
    35% cap can never sum to 100%, and a portfolio whose only bond must
    hold 40% cannot respect a 30% per-asset cap. When the mix makes a cap
    infeasible, the effective cap rises to the minimum share that class
    needs (and the relaxation is logged) — an impossible constraint that
    silently rejects every portfolio is worse protection than a visible,
    slightly higher cap.
    """
    holdings = target.holdings
    if not holdings:
        return
    cap = target.max_position_pct / Decimal("100")
    equity_cap = target.equity_max_pct / Decimal("100")

    def klass(holding: Holding) -> str:
        return ASSET_CLASS.get(holding.symbol, "equity")

    equities = [h for h in holdings if klass(h) == "equity"]
    bonds = [h for h in holdings if klass(h) == "bond"]

    # 1 ── equity ceiling: trim equities proportionally, move the excess
    #      into bonds. A winner that never held bonds (defensive shelter
    #      outside its universe) gets a BND cushion added — the risk
    #      profile binds harder than the backtest's universe.
    equity_total = sum((h.weight for h in equities), Decimal("0"))
    if equity_total > equity_cap:
        if bonds:
            scale = equity_cap / equity_total
            excess = equity_total - equity_cap
            for holding in equities:
                holding.weight *= scale
            share = excess / Decimal(len(bonds))
            for holding in bonds:
                holding.weight += share
        elif equity_cap < Decimal("1"):
            scale = equity_cap / equity_total
            for holding in equities:
                holding.weight *= scale
            holdings.append(
                Holding(
                    symbol="BND",
                    weight=Decimal("1") - equity_cap,
                    rationale="Bond cushion required by your risk profile "
                    "(the winning run held none).",
                )
            )
            logger.info(
                "Winner was 100%% equity — added a %.0f%% BND cushion to honor the %s equity cap",
                (1 - equity_cap) * 100,
                equity_cap,
            )

    # 2 ── feasible per-asset caps: at least 1/N each, and each bond at
    #      least its class share / k (a lone bond holding 40% is legitimate).
    n = Decimal(len(holdings))
    floor = Decimal("1") / n
    bond_total = sum((h.weight for h in bonds), Decimal("0"))
    bond_floor = bond_total / Decimal(len(bonds)) if bonds else Decimal("0")

    def effective_cap(holding: Holding) -> Decimal:
        if klass(holding) == "bond":
            return max(cap, floor, bond_floor)
        return max(cap, floor)

    # 3 ── iterative clamp: redistribution can push a receiver over its own
    #      cap, so repeat until stable.
    relaxed = False
    for _ in range(len(holdings) + 1):
        over = [h for h in holdings if h.weight > effective_cap(h) + Decimal("0.001")]
        if not over:
            break
        for holding in over:
            limit = effective_cap(holding)
            if limit > cap:
                relaxed = True
            excess = holding.weight - limit
            holding.weight = limit
            _redistribute(holdings, holding.symbol, excess)
    if relaxed:
        logger.info(
            "Per-asset cap %s relaxed to the minimum feasible share for this mix "
            "(N=%s holdings, bond class needs %s)",
            cap,
            len(holdings),
            bond_floor.quantize(Decimal("0.001")),
        )
    _normalise(holdings)


def _redistribute(
    holdings: list[Holding],
    skip_symbol: str,
    excess: Decimal,
    asset_class: str | None = None,
) -> None:
    """Spread ``excess`` weight over the other holdings (largest first),
    optionally only over holdings of one asset class."""
    receivers = [
        h
        for h in holdings
        if h.symbol != skip_symbol
        and (asset_class is None or ASSET_CLASS.get(h.symbol, "equity") == asset_class)
    ]
    if not receivers:
        return
    receivers.sort(key=lambda h: (-h.weight, h.symbol))
    share = excess / Decimal(len(receivers))
    for holding in receivers:
        holding.weight += share


def _normalise(holdings: list[Holding]) -> None:
    total = sum((h.weight for h in holdings), Decimal("0"))
    if total > 0:
        for holding in holdings:
            holding.weight = (holding.weight / total).quantize(_WEIGHT)


async def adopt_target(
    store: Any,
    profile: ProfileAnswers,
    swarm_db_path: str | Path = DEFAULT_SWARM_DB_PATH,
) -> TargetPortfolio:
    """One-click "do it for me": build from the latest winner (or seed) and
    persist it as the new active target version."""
    winner = await latest_winner(swarm_db_path)
    target = build_target(profile, winner)
    return await store.save_target(target)
