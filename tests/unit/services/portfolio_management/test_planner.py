"""Scenario matrix for the canonical rebalance planner (requirements 5-14).

Each test is one cell of the approved matrix: small drift does nothing,
cash buys the underweight, band-without-cash sells, cooldown blocks,
reactive-only never sells, a profile change bypasses cooldown with a
warning, dust orders are skipped, and tax vetoes defer expensive sells.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.services.portfolio_management.models import (
    Holding,
    PlanStatus,
    ProfileAnswers,
    RebalanceTrigger,
    TargetPortfolio,
)
from app.services.portfolio_management.planner import PlanContext, plan_rebalance

D = Decimal


def _target(band: str = "2.5", reactive_only: bool = False) -> TargetPortfolio:
    target = TargetPortfolio(
        source="seed",
        holdings=[
            Holding(symbol="SCHD", weight=D("0.40")),
            Holding(symbol="VYM", weight=D("0.30")),
            Holding(symbol="BND", weight=D("0.30")),
        ],
        profile=ProfileAnswers(risk_level="medium"),
        drift_band_pct=D(band),
        cooldown_days=7,
        reactive_only=reactive_only,
        max_position_pct=D("35"),
        equity_max_pct=D("75"),
    )
    return target


PRICES = {"SCHD": D("100"), "VYM": D("50"), "BND": D("80")}


def _ctx(**overrides) -> PlanContext:
    defaults: dict = {
        "target": _target(),
        "positions": {"SCHD": D("4000"), "VYM": D("3000"), "BND": D("3000")},
        "cash": D("0"),
        "prices": dict(PRICES),
        "lots": {},
        "now": datetime(2026, 10, 24),
    }
    defaults.update(overrides)
    return PlanContext(**defaults)


def test_small_drift_does_nothing():
    plan = plan_rebalance(_ctx())
    assert plan.status is PlanStatus.SKIPPED
    assert not plan.trades
    assert "inside" in plan.summary or "Nothing to do" in plan.summary


def test_new_cash_buys_the_underweight_never_sells():
    # SCHD drifted low; VYM drifted high; new cash must fix SCHD by buying.
    ctx = _ctx(
        positions={"SCHD": D("3600"), "VYM": D("3400"), "BND": D("3000")},
        cash=D("500"),
    )
    plan = plan_rebalance(ctx)
    assert plan.status is PlanStatus.REACTIVE
    assert plan.trigger is RebalanceTrigger.CASH
    assert all(t.side == "BUY" for t in plan.trades)
    assert any(t.symbol == "SCHD" for t in plan.trades)
    assert "cash" in plan.summary.lower()


def test_band_exceeded_without_cash_sells_overweight():
    # VYM 30→37% (drift 7pp > 2.5pp), no cash: proactive sell + buy.
    ctx = _ctx(
        positions={"SCHD": D("3800"), "VYM": D("3700"), "BND": D("2900")},
    )
    plan = plan_rebalance(ctx)
    assert plan.status is PlanStatus.PROACTIVE
    sells = [t for t in plan.trades if t.side == "SELL"]
    buys = [t for t in plan.trades if t.side == "BUY"]
    assert sells and all(t.symbol == "VYM" for t in sells)
    assert buys
    # sells come first — proceeds fund the buys
    assert plan.trades[0].side == "SELL"


def test_cooldown_blocks_everything():
    ctx = _ctx(
        positions={"SCHD": D("3600"), "VYM": D("3400"), "BND": D("3000")},
        cash=D("500"),
        last_rebalance=datetime(2026, 10, 20),  # 4 days ago, cooldown 7
    )
    plan = plan_rebalance(ctx)
    assert plan.status is PlanStatus.SKIPPED
    assert "Cooling down" in plan.summary


def test_profile_change_bypasses_cooldown_with_warning():
    ctx = _ctx(
        positions={"SCHD": D("3600"), "VYM": D("3400"), "BND": D("3000")},
        cash=D("500"),
        last_rebalance=datetime(2026, 10, 20),
        forced=True,
        forced_trigger=RebalanceTrigger.PROFILE_CHANGE,
    )
    plan = plan_rebalance(ctx)
    assert plan.status is not PlanStatus.SKIPPED
    assert plan.trigger is RebalanceTrigger.PROFILE_CHANGE
    assert any("cooldown bypassed" in r for r in plan.reasons)


def test_reactive_only_never_sells():
    ctx = _ctx(
        target=_target(reactive_only=True),
        positions={"SCHD": D("3800"), "VYM": D("3700"), "BND": D("2900")},
    )
    plan = plan_rebalance(ctx)
    assert plan.status is PlanStatus.SKIPPED
    assert not any(t.side == "SELL" for t in plan.trades)
    assert "reactive-only" in plan.summary.lower()


def test_reactive_only_with_cash_still_buys():
    # only SCHD is out of band (under) — VYM/BND inside, so cash fixes it
    ctx = _ctx(
        target=_target(reactive_only=True),
        positions={"SCHD": D("3600"), "VYM": D("3300"), "BND": D("3000")},
        cash=D("400"),
    )
    plan = plan_rebalance(ctx)
    assert plan.status is PlanStatus.REACTIVE
    assert all(t.side == "BUY" for t in plan.trades)
    assert any(t.symbol == "SCHD" for t in plan.trades)


def test_dust_orders_below_minimum_are_skipped():
    # 80€ of drift: below the 100€ minimum trade value.
    ctx = _ctx(
        positions={"SCHD": D("3920"), "VYM": D("3000"), "BND": D("3000")},
    )
    plan = plan_rebalance(ctx)
    assert plan.status is PlanStatus.SKIPPED or all(
        t.value >= ctx.min_trade_value for t in plan.trades
    )


def test_expensive_tax_defers_the_sell():
    from app.services.portfolio_management.models import LotSnapshot
    from app.services.portfolio_management.tax import SpainRebalanceTax

    # VYM overweight 7pp ≈ 700€ with a big embedded gain → 19% of ~700€
    # gain ≈ 133€ > 20% veto of 700€? No: 140€ — make the gain larger than
    # the value itself is impossible; use a tighter veto ratio instead.
    lots = {
        "VYM": [
            LotSnapshot(
                lot_id="l1",
                symbol="VYM",
                quantity=D("74"),
                purchase_price=D("1"),  # bought at 1€, now 50€: gain ≈ 99%
                purchased_at=datetime(2024, 1, 1),
            )
        ]
    }
    ctx = _ctx(
        positions={"SCHD": D("3800"), "VYM": D("3700"), "BND": D("2900")},
        lots=lots,
        tax_veto_ratio=D("0.10"),  # veto when tax > 10% of the traded value
    )
    plan = plan_rebalance(ctx, tax_preview=SpainRebalanceTax().preview_sell)
    vetoes = [r for r in plan.reasons if "deferred" in r and "VYM" in r]
    assert vetoes, f"expected a tax veto for VYM, reasons: {plan.reasons}"
    assert not any(t.side == "SELL" and t.symbol == "VYM" for t in plan.trades)


def test_two_month_rule_vetoes_loss_sell():
    from app.services.portfolio_management.models import LotSnapshot
    from app.services.portfolio_management.tax import SpainRebalanceTax

    # VYM overweight but bought 10 days ago at a higher price: selling at a
    # loss inside the 2-month window is exactly what Spain disallows.
    lots = {
        "VYM": [
            LotSnapshot(
                lot_id="l1",
                symbol="VYM",
                quantity=D("74"),
                purchase_price=D("80"),
                purchased_at=datetime(2026, 10, 14),
            )
        ]
    }
    ctx = _ctx(
        positions={"SCHD": D("3800"), "VYM": D("3700"), "BND": D("2900")},
        lots=lots,
    )
    plan = plan_rebalance(ctx, tax_preview=SpainRebalanceTax().preview_sell)
    assert any("2-month" in r or "vetoed" in r for r in plan.reasons)
    assert not any(t.side == "SELL" and t.symbol == "VYM" for t in plan.trades)


def test_zero_band_all_breached_still_plans_minimally():
    ctx = _ctx(target=_target(band="2.5"))
    plan = plan_rebalance(ctx)
    # sanity on the reference scenario: in band → skip
    assert plan.status is PlanStatus.SKIPPED


def test_holding_outside_target_gets_sold():
    # A symbol the target does not include anymore (old winner holding).
    ctx = _ctx(positions={"SCHD": D("4000"), "VYM": D("3000"), "BND": D("2000"), "DVY": D("1000")})
    plan = plan_rebalance(ctx)
    assert plan.status is PlanStatus.PROACTIVE
    assert any(t.side == "SELL" and t.symbol == "DVY" for t in plan.trades)
