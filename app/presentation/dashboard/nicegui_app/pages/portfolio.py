"""Portfolio page: the robo-advisor surface (requirements 1-14).

One page for someone who does not know how to invest:

1 · A five-question profile (objective, drawdown tolerance, risk, age,
    province) becomes a concrete portfolio — adopted from the latest
    winning swarm run, curated seed as fallback — with a one-sentence
    "why" per ETF (requirement 2's visible criteria included).
2 · The portfolio view shows target vs current weights, the drift band,
    the cooldown countdown, and the reactive-only switch.
3 · "Rebalance now" PREVIEWS the plan with its tax impact in € before
    anything is confirmed (requirement 11); confirmation sends diff-orders
    through the risk gates.
4 · The history explains every past rebalance in plain English.
"""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.swarm_fx import install as install_fx
from app.services.agent_swarm.store import DEFAULT_SWARM_DB_PATH
from app.services.live_trading.broker_connector import BrokerConnector, BrokerPosition, BrokerType
from app.services.live_trading.order_manager import OrderManager
from app.services.portfolio_management import (
    OBJECTIVES,
    PlanContext,
    PortfolioManagementStore,
    ProfileAnswers,
    SpainRebalanceTax,
    adopt_target,
    cooldown_ends_at,
    plan_rebalance,
)
from app.services.portfolio_management.executor import RebalanceExecutor
from app.services.portfolio_management.paper_state import DEFAULT_PAPER_STATE_PATH, load_paper_state
from app.services.portfolio_management.winner_adoption import latest_winner

D = Decimal
_DB_PATH = Path("data/portfolio_management.db")
_CORPUS = Path("data/historical")

#: Requirement 1's questionnaire — plain answers, no jargon.
DRAWDOWN_CHOICES = {
    "10": "Up to 10% — small dips only",
    "20": "Up to 20% — I can wait out a bad year",
    "30": "30% or more — I am here for the long run",
}
PROVINCES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Otro"]

_store: PortfolioManagementStore | None = None
_broker: BrokerConnector | None = None


async def _get_store() -> PortfolioManagementStore:
    global _store
    if _store is None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.infrastructure.persistence.database import Base
        from app.services.portfolio_management import store as store_module

        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_PATH}")
        async with engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all,
                tables=[
                    store_module.TargetPortfolioRecord.__table__,
                    store_module.PortfolioLotRecord.__table__,
                    store_module.RebalanceEventRecord.__table__,
                ],
            )
        _store = PortfolioManagementStore(async_sessionmaker(engine, expire_on_commit=False))
    return _store


async def _get_broker() -> BrokerConnector:
    global _broker
    if _broker is None:
        connector = BrokerConnector(BrokerType.PAPER)
        connector.adapter.auto_fill_orders = True
        await connector.connect()
        state = load_paper_state(DEFAULT_PAPER_STATE_PATH)
        if state is not None and connector.adapter.account is not None:
            cash, positions = state
            connector.adapter.account.cash_available = cash
            for symbol, data in positions.items():
                quote = await connector.get_quote(symbol)
                price = quote.price if quote else data["avg_price"]
                quantity = data["quantity"]
                connector.adapter.positions[symbol] = BrokerPosition(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=data["avg_price"],
                    current_price=price,
                    market_value=quantity * price,
                    unrealized_pl=(price - data["avg_price"]) * quantity,
                    unrealized_pl_pct=D("0"),
                )
        _broker = connector
    return _broker


def _corpus_facts(symbol: str) -> dict[str, Any] | None:
    """Real selection facts from the repo's own data: history depth, last
    real price date, average daily money traded. These are the objective
    criteria requirement 2 asks the robot to show."""
    path = _CORPUS / f"{symbol.upper()}.csv"
    if not path.exists():
        return None
    rows: list[tuple[str, float, float]] = []
    try:
        with path.open() as handle:
            reader = csv.reader(handle)
            next(reader, None)  # header
            for row in reader:
                if len(row) >= 6:
                    rows.append((row[0], float(row[4]), float(row[5])))
    except (OSError, ValueError):
        return None
    if not rows:
        return None
    tail = rows[-252:]
    avg_dollar_volume = sum(close * volume for _, close, volume in tail) / len(tail)
    return {
        "first": rows[0][0],
        "last": rows[-1][0],
        "days": len(rows),
        "avg_volume_m": avg_dollar_volume / 1_000_000,
    }


def _fmt_pct(weight: Decimal) -> str:
    return f"{(weight * D('100')):.1f}%"


def _role_chip(rationale: str) -> tuple[str, str]:
    """Plain-English role from the SAME rationale the engine wrote —
    the chip never invents a role the portfolio didn't state."""
    r = (rationale or "").lower()
    if any(k in r for k in ("dividend", "income", "renta", "yield")):
        return "Income engine", "info"
    if any(k in r for k in ("bond", "defensive", "cash", "stability", "staples", "low vol")):
        return "Safety cushion", "good"
    if any(k in r for k in ("growth", "appreciation", "momentum")):
        return "Growth booster", "warn"
    return "Diversifier", "good"


def _render_interactive_pie(holdings, weight_fmt=_fmt_pct) -> None:
    """UI-2: every slice is clickable → the symbol's plain-language card."""
    from app.presentation.dashboard.nicegui_app import design_system as ds

    data = [
        {"value": float(h.weight) * 100, "name": h.symbol, "rationale": h.rationale}
        for h in holdings
    ]
    with ui.row().classes("w-full items-start no-wrap gap-md"):
        chart = ui.echart(
            {
                "tooltip": {"trigger": "item", "formatter": "{b}: {c}%"},
                "series": [
                    {
                        "type": "pie",
                        "radius": ["45%", "72%"],
                        "itemStyle": {
                            "borderRadius": 6,
                            "borderColor": "#fffdf6",
                            "borderWidth": 2,
                        },
                        "label": {"formatter": "{b}"},
                        "data": data,
                    }
                ],
            }
        ).classes("h-64 w-72 shrink-0")

        detail = ui.column().classes("flex-1 gap-sm")

        def _show(name: str) -> None:
            detail.clear()
            with detail:
                holding = next((h for h in holdings if h.symbol == name), None)
                if holding is None:
                    return
                chip, tone = _role_chip(holding.rationale)
                with ds.card(title=holding.symbol):
                    ds.validation_badge("partial" if tone == "warn" else "fees", text=chip)
                    ui.label(holding.rationale or "Part of your mix.").classes("q-mt-sm")
                    facts = _corpus_facts(holding.symbol)
                    ui.label(
                        f"{weight_fmt(holding.weight)} of your portfolio · "
                        + (
                            f"{facts['days']:,} days of history, "
                            f"€{facts['avg_volume_m']:.1f}M/day traded"
                            if facts
                            else "no local history"
                        )
                    ).classes("text-caption")

        chart.on("click", lambda e: _show(e.args["name"]))
        ui.label("Tap a slice to see what it does for you.").classes("text-caption")


def _inject_ds() -> None:
    from app.presentation.dashboard.nicegui_app import design_system as ds

    ds.inject()


def _render_digest_card(target) -> None:
    """UI-6: the weekly digest — what happened, what to do (usually nothing)."""
    from app.presentation.dashboard.nicegui_app import design_system as ds
    from app.presentation.dashboard.nicegui_app.components.weekly_digest import weekly_digest

    with ds.card(title="This week, in plain English").classes("w-full q-mb-md"):
        lines = weekly_digest(
            last_run_status="completed" if getattr(target, "source_run_id", None) else None,
            last_run_return_pct=None,
            drift_status=None,
        )
        ui.label(lines["headline"]).style("color:var(--ds-text)")
        ui.label(lines["action"]).style(
            "color:var(--ds-text_soft);font-size:var(--ds-small-size);margin-top:6px"
        )


def render(
    executor: Any = None,
    store: Any = None,
) -> None:
    """Render the Portfolio page (signature matches the page registry)."""
    install_fx()
    _inject_ds()  # UI-2: the interactive pie + symbol cards speak the design system
    ui.dark_mode(False)

    with ui.element("div").classes("light-sheet w-full"):
        for blob in ("blob-a", "blob-b", "blob-c"):
            ui.element("div").classes(f"blob {blob}").props("aria-hidden=true")

        with ui.row().classes("w-full items-center no-wrap gap-md"):
            with ui.column().classes("gap-0 q-mr-md"):
                ui.label("Portfolio").classes("hud-title")
                ui.label(
                    "Your investments on autopilot: answer five questions, get a "
                    "portfolio you can understand, and let the robot keep it on track."
                ).classes("hud-sub")

        target_state: dict[str, Any] = {}

        @ui.refreshable
        async def render_state() -> None:
            pm_store = await _get_store()
            target = await pm_store.get_active_target()
            target_state["target"] = target
            if target is None:
                _render_questionnaire(first_time=True)
                return
            _render_digest_card(target)
            _render_target_card(target)
            await _render_drift_card(target, pm_store)
            await _render_history_card(pm_store)

        def _render_questionnaire(first_time: bool = False) -> None:
            with ui.card().classes("w-full q-mt-md card-soft"):
                ui.label("1 · Tell us about you").classes("text-h6")
                ui.label(
                    "Five questions — the robot turns them into a concrete portfolio "
                    "(you never pick ETFs yourself)."
                ).classes("text-caption")
                with ui.row().classes("w-full items-end gap-md wrap"):
                    objective = ui.select(
                        OBJECTIVES, value="BALANCED_GROWTH", label="Your goal"
                    ).classes("min-w-[220px]")
                    drawdown = ui.select(
                        DRAWDOWN_CHOICES, value="20", label="How much can your portfolio fall?"
                    ).classes("min-w-[260px]")
                    age = ui.number("Your age", value=40, min=18, max=100).classes("w-32")
                    province = ui.select(
                        {p: p for p in PROVINCES}, value="Madrid", label="Province (taxes)"
                    ).classes("min-w-[160px]")
                ui.button(
                    "Build my portfolio",
                    icon="auto_awesome",
                    on_click=lambda: _build(objective, drawdown, age, province),
                ).props("unelevated").classes("btn-primary")

        async def _build(objective, drawdown, age, province) -> None:
            pm_store = await _get_store()
            profile = ProfileAnswers(
                objective=str(objective.value),
                risk_level="medium",
                drawdown_tolerance_pct=D(str(drawdown.value)),
                investor_age=int(age.value or 40),
                tax_province=str(province.value),
            )
            # The drawdown answer IS the risk level: 10% conservative,
            # 20% medium, 30%+ aggressive.
            tolerance = profile.drawdown_tolerance_pct
            profile.risk_level = (
                "conservative"
                if tolerance <= 10
                else ("medium" if tolerance <= 20 else "aggressive")
            )
            target = await adopt_target(pm_store, profile, DEFAULT_SWARM_DB_PATH)
            winner = await latest_winner(DEFAULT_SWARM_DB_PATH)
            source = (
                f"your latest winning backtest ({winner['decision_status']})"
                if winner
                else "a curated starter portfolio"
            )
            ui.notify(
                f"Portfolio v{target.version} built from {source}: "
                + ", ".join(f"{h.symbol} {_fmt_pct(h.weight)}" for h in target.holdings),
                type="positive",
            )
            render_state.refresh()

        def _render_target_card(target) -> None:
            with ui.card().classes("w-full q-mt-md card-soft"):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    ui.label("2 · Your portfolio").classes("text-h6")
                    with ui.row().classes("gap-sm"):
                        ui.button(
                            "Change profile",
                            on_click=lambda: render_state.refresh(),
                        ).props("flat dense").tooltip("Re-answer the questionnaire")
                provenance = (
                    f"Adopted from winning run {target.source_run_id} "
                    f"({target.decision_status}, strategy {target.strategy_name})."
                    if target.source == "swarm_winner"
                    else "Curated starter portfolio — the first winning backtest replaces it."
                )
                ui.label(provenance).classes("text-caption")
                _render_interactive_pie(target.holdings)
                columns = [
                    {"name": "symbol", "label": "ETF", "field": "symbol", "align": "left"},
                    {"name": "weight", "label": "Target", "field": "weight", "align": "right"},
                    {"name": "why", "label": "Why it is here", "field": "why", "align": "left"},
                    {"name": "facts", "label": "Data check", "field": "facts", "align": "left"},
                ]
                rows = []
                for holding in target.holdings:
                    facts = _corpus_facts(holding.symbol)
                    facts_text = (
                        f"{facts['days']:,} days of history, €{facts['avg_volume_m']:.1f}M/day traded"
                        if facts
                        else "no local history"
                    )
                    rows.append(
                        {
                            "symbol": holding.symbol,
                            "weight": _fmt_pct(holding.weight),
                            "why": holding.rationale or "—",
                            "facts": facts_text,
                        }
                    )
                ui.table(columns=columns, rows=rows, row_key="symbol").classes("w-full").props(
                    "flat bordered dense"
                )
                with ui.row().classes("q-mt-sm gap-lg text-caption"):
                    ui.label(
                        f"Drift band ±{target.drift_band_pct}% · cooldown {target.cooldown_days} days"
                    )
                    ui.label(
                        f"Max per ETF {target.max_position_pct}% · max equity {target.equity_max_pct}%"
                    )
                    reactive_switch = ui.switch(
                        "Reactive only (never sell)",
                        value=target.reactive_only,
                        on_change=lambda e: _toggle_reactive(e.value),
                    )
                    reactive_switch.props("dense")

        async def _toggle_reactive(value: bool) -> None:
            pm_store = await _get_store()
            target = target_state.get("target")
            if target is None:
                return
            await pm_store.update_target_flags(target.version, reactive_only=value)
            ui.notify(
                "Reactive-only ON: the robot will only buy with new money, never sell."
                if value
                else "Reactive-only OFF: the robot may sell to correct drift.",
                type="info",
            )

        async def _render_drift_card(target, pm_store) -> None:
            broker = await _get_broker()
            account = await broker.get_account_info()
            positions_map = await broker.get_positions()
            positions = {p.symbol: p.market_value for p in positions_map.values()}
            prices: dict[str, Decimal] = {}
            for symbol in {h.symbol for h in target.holdings} | set(positions):
                quote = await broker.get_quote(symbol)
                if quote is not None:
                    prices[symbol] = quote.price
            cash = account.cash_available if account else D("0")
            lots = await pm_store.get_lots()
            lots_by_symbol: dict[str, list] = {}
            for lot in lots:
                lots_by_symbol.setdefault(lot.symbol, []).append(lot)
            last_rebalance = await pm_store.last_rebalance_at()

            from app.services.portfolio_management.drift import compute_drift

            total = sum(positions.values(), D("0")) + cash
            drifts = compute_drift(target.holdings, positions, total, target.drift_band_pct)

            with ui.card().classes("w-full q-mt-md card-soft"):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    ui.label("3 · On track?").classes("text-h6")
                    cooldown_left = cooldown_ends_at(last_rebalance, target.cooldown_days)
                    if cooldown_left and cooldown_left > datetime.utcnow():
                        ui.badge(
                            f"cooling down until {cooldown_left:%d %b %H:%M}", color="grey"
                        ).props("outline")
                if total <= 0:
                    ui.label(
                        "Paper account is empty — the first rebalance will deploy the cash."
                    ).classes("text-caption")
                else:
                    columns = [
                        {"name": "symbol", "label": "ETF", "field": "symbol", "align": "left"},
                        {"name": "target", "label": "Target", "field": "target", "align": "right"},
                        {"name": "current", "label": "Now", "field": "current", "align": "right"},
                        {"name": "drift", "label": "Drift", "field": "drift", "align": "right"},
                        {"name": "status", "label": "Status", "field": "status", "align": "left"},
                    ]
                    rows = []
                    for drift in drifts:
                        rows.append(
                            {
                                "symbol": drift.symbol,
                                "target": _fmt_pct(drift.target_weight),
                                "current": _fmt_pct(drift.current_weight),
                                "drift": f"{(drift.drift * D('100')):+.1f} pp",
                                "status": "⚠ outside band" if drift.breached else "✓ in band",
                            }
                        )
                    ui.table(columns=columns, rows=rows, row_key="symbol").classes("w-full").props(
                        "flat bordered dense"
                    )
                    ui.label(f"Cash €{cash:,.0f} · total €{total:,.0f}").classes("text-caption")
                ui.button(
                    "Preview rebalance",
                    icon="balance",
                    on_click=lambda: _preview(
                        target, positions, cash, prices, lots_by_symbol, last_rebalance
                    ),
                ).props("unelevated").classes("btn-primary")

        async def _preview(target, positions, cash, prices, lots_by_symbol, last_rebalance) -> None:
            ctx = PlanContext(
                target=target,
                positions=positions,
                cash=cash,
                prices=prices,
                lots=lots_by_symbol,
                last_rebalance=last_rebalance,
            )
            plan = plan_rebalance(ctx, tax_preview=SpainRebalanceTax().preview_sell)

            with ui.dialog() as dialog, ui.card().classes("min-w-[720px]"):
                ui.label("Rebalance preview").classes("text-h6")
                ui.label(plan.summary).classes("text-body1")
                if plan.trades:
                    columns = [
                        {"name": "side", "label": "", "field": "side", "align": "left"},
                        {"name": "symbol", "label": "ETF", "field": "symbol", "align": "left"},
                        {"name": "qty", "label": "Shares", "field": "qty", "align": "right"},
                        {"name": "value", "label": "Value", "field": "value", "align": "right"},
                        {"name": "tax", "label": "Tax", "field": "tax", "align": "right"},
                    ]
                    rows = [
                        {
                            "side": trade.side,
                            "symbol": trade.symbol,
                            "qty": f"{trade.quantity:.4f}",
                            "value": f"€{trade.value:,.0f}",
                            "tax": f"€{trade.tax_impact.tax:,.0f}" if trade.tax_impact else "—",
                        }
                        for trade in plan.trades
                    ]
                    ui.table(columns=columns, rows=rows, row_key="symbol").props(
                        "flat bordered dense"
                    )
                    if plan.tax_total > 0:
                        ui.label(
                            f"Estimated tax if confirmed: €{plan.tax_total:,.0f} "
                            "(shown BEFORE you confirm — no surprises in your tax return)."
                        ).classes("text-caption text-warning")
                else:
                    ui.label("Nothing to do — the plan above explains why.").classes("text-caption")
                for reason in plan.reasons[:6]:
                    if reason not in {t.reason for t in plan.trades}:
                        ui.label(f"· {reason}").classes("text-caption")
                with ui.row().classes("w-full justify-end gap-sm"):
                    ui.button("Not now", on_click=dialog.close).props("flat")
                    if plan.trades:
                        ui.button(
                            "Confirm and send orders",
                            icon="send",
                            on_click=lambda: _confirm(plan, dialog),
                        ).props("unelevated").classes("btn-primary")
            dialog.open()

        async def _confirm(plan, dialog) -> None:
            pm_store = await _get_store()
            broker = await _get_broker()
            manager = OrderManager(broker=broker)
            executor_ = RebalanceExecutor(pm_store, broker, order_manager=manager)
            outcome = await executor_.execute(plan)
            dialog.close()
            if outcome.ok and outcome.executed:
                ui.notify(
                    f"Done: {len(outcome.executed)} order(s) sent to the paper broker.",
                    type="positive",
                )
            elif outcome.failed:
                ui.notify(
                    f"{len(outcome.failed)} order(s) rejected: "
                    + "; ".join(f["error"] for f in outcome.failed[:3]),
                    type="negative",
                )
            else:
                ui.notify("Plan recorded, nothing was traded.", type="info")
            render_state.refresh()

        async def _render_history_card(pm_store) -> None:
            events = await pm_store.list_events(limit=20)
            with ui.card().classes("w-full q-mt-md card-soft"):
                ui.label("4 · What the robot did, and why").classes("text-h6")
                if not events:
                    ui.label("No rebalances yet — history will explain each one here.").classes(
                        "text-caption"
                    )
                    return
                with ui.element("div").classes("w-full column gap-xs"):
                    for event in events:
                        with ui.row().classes("w-full items-start no-wrap gap-sm"):
                            color = {
                                "executed": "positive",
                                "skipped": "grey",
                                "planned": "info",
                                "rejected": "negative",
                            }.get(event["action"], "grey")
                            ui.badge(event["action"], color=color).props("outline").classes(
                                "q-mt-xs"
                            )
                            with ui.column().classes("gap-0"):
                                ui.label(event["reason"]).classes("text-body2")
                                ui.label(
                                    f"{event['ts'][:16].replace('T', ' ')} · trigger {event['trigger']}"
                                ).classes("text-caption")

        ui.timer(0.1, render_state, once=True)

        ui.label(
            "Paper mode: orders go to the deterministic paper broker through the same "
            "risk gates as live trading. The account is saved after every execution "
            "and restored on restart, so the dashboard and the daily runner share one "
            "paper portfolio."
        ).classes("text-caption q-mt-md text-grey-7")
