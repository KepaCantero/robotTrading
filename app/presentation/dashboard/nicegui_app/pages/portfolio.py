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
from app.services.live_trading.broker_connector import BrokerConnector
from app.services.live_trading.order_manager import OrderManager
from app.services.portfolio_management import (
    OBJECTIVES,
    PlanContext,
    PortfolioManagementStore,
    ProfileAnswers,
    RebalanceTrigger,
    SpainRebalanceTax,
    adopt_target,
    cooldown_ends_at,
    plan_rebalance,
)
from app.services.portfolio_management.executor import RebalanceExecutor
from app.services.portfolio_management.winner_adoption import latest_winner

D = Decimal
_DB_PATH = Path("data/portfolio_management.db")  # legacy path of slug "main"
_CORPUS = Path("data/historical")

#: Requirement (user 2026-10-27): paper trading holds MORE THAN ONE
#: portfolio, each by NAME, each with its own account/lots/history.
#: Active selection is module-level (single-user local dashboard) and the
#: engines are cached per slug.
_ACTIVE_SLUG = "main"
_stores: dict[str, PortfolioManagementStore] = {}
_brokers: dict[str, BrokerConnector] = {}


async def _get_store() -> PortfolioManagementStore:
    slug = _ACTIVE_SLUG
    cached = _stores.get(slug)
    if cached is not None:
        return cached
    from app.services.portfolio_management.named_portfolios import open_store, prepare_store

    engine, store = open_store(slug)
    await prepare_store(engine)
    _stores[slug] = store
    return store


async def _get_broker() -> BrokerConnector:
    slug = _ACTIVE_SLUG
    cached = _brokers.get(slug)
    if cached is not None:
        return cached
    from app.services.portfolio_management.named_portfolios import open_broker

    connector = await open_broker(slug)
    _brokers[slug] = connector
    return connector


#: Requirement 1's questionnaire — plain answers, no jargon.
DRAWDOWN_CHOICES = {
    "10": "Up to 10% — small dips only",
    "20": "Up to 20% — I can wait out a bad year",
    "30": "30% or more — I am here for the long run",
}
PROVINCES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Otro"]


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


def _stat_tile(label: str, value: str, color: str = "var(--ds-text)") -> None:
    """Small paper-account stat: label + big number, design-system skin."""
    with ui.element("div").style(
        "min-width:150px;padding:12px 16px;background:var(--ds-surface_alt);"
        "border:1px solid var(--ds-line);border-radius:12px"
    ):
        ui.label(label).style("font-size:11px;font-weight:600;color:var(--ds-text_soft)")
        ui.label(value).style(f"font-size:20px;font-weight:700;color:{color};margin-top:3px")


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
    focus_slug: str = "",
    autodeploy: bool = False,
) -> None:
    """Render the Portfolio page (signature matches the page registry).

    ``focus_slug``/``autodeploy`` come from the Mission Control hand-off
    (``/portfolio?portfolio=<slug>&deploy=1``): after creating a named paper
    portfolio the owner lands HERE with it selected and the first-deployment
    preview already open — one Confirm deploys the cash.
    """
    install_fx()
    _inject_ds()  # UI-2: the interactive pie + symbol cards speak the design system
    ui.dark_mode(False)

    with ui.element("div").classes("light-sheet w-full"):
        for blob in ("blob-a", "blob-b", "blob-c"):
            ui.element("div").classes(f"blob {blob}").props("aria-hidden=true")

        with ui.row().classes("w-full items-center no-wrap gap-md"):
            with ui.column().classes("gap-0 q-mr-md flex-1"):
                ui.label("Portfolio").classes("page-title")
                ui.label(
                    "Your investments on autopilot: answer five questions, get a "
                    "portfolio you can understand, and let the robot keep it on track."
                ).classes("page-sub")
            from app.services.portfolio_management.named_portfolios import list_portfolios

            portfolios = list_portfolios()
            options = {p["slug"]: p["name"] for p in portfolios}
            if focus_slug and focus_slug in options:
                global _ACTIVE_SLUG
                _ACTIVE_SLUG = focus_slug

            def _switch_portfolio(e) -> None:
                global _ACTIVE_SLUG
                _ACTIVE_SLUG = str(e.value or "main")
                render_state.refresh()

            ui.select(
                options,
                value=_ACTIVE_SLUG if _ACTIVE_SLUG in options else "main",
                label="Paper portfolio",
                on_change=_switch_portfolio,
            ).classes("min-w-[220px]").mark("portfolio_select").tooltip(
                "Each portfolio keeps its own paper account. Send a validated run "
                "from Mission Control to create a new one."
            )

        target_state: dict[str, Any] = {}

        @ui.refreshable
        async def render_state() -> None:
            pm_store = await _get_store()
            target = await pm_store.get_active_target()
            target_state["target"] = target
            if target is None or target_state.get("editing"):
                _render_questionnaire(first_time=target is None)
                return
            _render_digest_card(target)
            _render_target_card(target)
            await _render_live_card(target)
            await _render_drift_card(target, pm_store)
            await _render_history_card(pm_store)

        def _render_questionnaire(first_time: bool = False) -> None:
            with ui.element("div").classes("panel q-pa-md w-full q-mt-md"):
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
                with ui.row().classes("items-center gap-sm"):
                    ui.button(
                        "Build my portfolio",
                        icon="auto_awesome",
                        on_click=lambda: _build(objective, drawdown, age, province),
                    ).props("unelevated no-caps").classes("run-btn")
                    if not first_time:
                        ui.button(
                            "Keep current portfolio",
                            on_click=lambda: (
                                target_state.__setitem__("editing", False),
                                render_state.refresh(),
                            ),
                        ).props("flat no-caps").tooltip("Go back without changing anything")

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
            target_state["editing"] = False
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
            with ui.element("div").classes("panel q-pa-md w-full q-mt-md"):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    ui.label("2 · Your portfolio").classes("text-h6")
                    with ui.row().classes("gap-sm"):
                        ui.button(
                            "Change profile",
                            on_click=lambda: (
                                target_state.__setitem__("editing", True),
                                render_state.refresh(),
                            ),
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

        async def _gather_account_state(target, pm_store) -> dict:
            """One snapshot of the paper account shared by the drift card and
            the auto-opened first-deployment preview (same numbers, no drift
            between the two views)."""
            broker = await _get_broker()
            account = await broker.get_account_info()
            positions_map = await broker.get_positions()
            positions = {p.symbol: p.market_value for p in positions_map.values()}
            prices: dict[str, Decimal] = {}
            for symbol in {h.symbol for h in target.holdings} | set(positions):
                quote = await broker.get_quote(symbol)
                if quote is not None:
                    prices[symbol] = quote.price
            lots = await pm_store.get_lots()
            lots_by_symbol: dict[str, list] = {}
            for lot in lots:
                lots_by_symbol.setdefault(lot.symbol, []).append(lot)
            return {
                "target": target,
                "positions": positions,
                "cash": account.cash_available if account else D("0"),
                "prices": prices,
                "lots_by_symbol": lots_by_symbol,
                "last_rebalance": await pm_store.last_rebalance_at(),
                # _preview doesn't take this; the drift card P&L columns do.
                "positions_map": positions_map,
            }

        async def _render_live_card(target) -> None:
            """Real broker account vs the adopted target (read-only).

            The owner holds a live IBKR account tracked in his own
            portfolio project. Pasting its holdings here connects the two
            worlds: corpus-priced gap per sleeve, a buy-only path for new
            money (dilution — the robot never proposes selling the real
            account), and an estimated tax cost should HE choose to trim.
            """
            from app.services.portfolio_management import real_gap

            snapshot = real_gap.load_real_holdings(_ACTIVE_SLUG)
            with ui.element("div").classes("panel q-pa-md w-full q-mt-md"):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    ui.label("3 · Your live account vs this target").classes("text-h6")
                    if snapshot is not None:
                        ui.button(
                            "Re-import",
                            icon="upload_file",
                            on_click=lambda: (
                                target_state.__setitem__("editing", "live"),
                                render_state.refresh(),
                            ),
                        ).props("flat dense").tooltip(
                            "Paste the broker holdings again (replaces the stored ones)."
                        )
                ui.label(
                    "Real money, read-only: the robot prices your actual holdings "
                    "from its own data and shows the gap to the target above. "
                    "Nothing here touches your broker."
                ).classes("text-caption")
                if snapshot is None or target_state.get("editing") == "live":
                    paste = ui.textarea(
                        label="Paste holdings — ticker, quantity, avg cost € (one per line)",
                        placeholder=(
                            "VWCE,224.88,148.71\nVHYL,494.04,69.09\nO,138.73,51.33\n"
                            "CASH,560.36,1.00"
                        ),
                    ).classes("w-full").props("autogrow")
                    fx_input = ui.number(
                        "USD→EUR rate (leave empty to use the ECB reference)",
                        value=None,
                        step="0.0001",
                        min=0.5,
                        max=1.5,
                    )

                    async def _import_live() -> None:
                        positions, cash, skipped = real_gap.parse_holdings_paste(
                            paste.value or ""
                        )
                        if not positions and cash <= 0:
                            ui.notify(
                                "Nothing readable in the paste — one 'ticker,quantity,cost' "
                                "line per holding.",
                                type="negative",
                            )
                            return
                        snap = real_gap.RealSnapshot(
                            cash_eur=cash,
                            fx_usd_eur=(
                                D(str(fx_input.value)) if fx_input.value else None
                            ),
                            positions=positions,
                        )
                        real_gap.save_real_holdings(_ACTIVE_SLUG, snap)
                        target_state.pop("editing", None)
                        ui.notify(
                            f"Imported {len(positions)} live positions"
                            + (f" (+€{cash:,.0f} cash)" if cash else "")
                            + (
                                f" — {len(skipped)} line(s) skipped"
                                if skipped
                                else ""
                            ),
                            type="positive",
                        )
                        render_state.refresh()

                    with ui.row().classes("items-center gap-sm"):
                        ui.button(
                            "Import live holdings",
                            icon="download",
                            on_click=_import_live,
                        ).props("unelevated no-caps").classes("run-btn")
                        if snapshot is not None:
                            ui.button(
                                "Keep stored holdings",
                                on_click=lambda: (
                                    target_state.pop("editing", None),
                                    render_state.refresh(),
                                ),
                            ).props("flat no-caps")
                    return

                report = real_gap.compute_gap(target.holdings, snapshot)
                if report.total_eur <= 0:
                    ui.label(
                        "No imported position could be priced from the local corpus "
                        f"({', '.join(report.unpriced) or 'none found'}). Import at "
                        "least one symbol the robot has data for."
                    ).classes("text-caption text-warning")
                    return
                outside_pct = (
                    sum((v for _, v in report.outside_target), D("0"))
                    / report.total_eur
                )
                with ui.row().classes("w-full gap-sm wrap q-mb-md"):
                    _stat_tile("Live account", f"€{report.total_eur:,.0f}")
                    _stat_tile(
                        "Positions", f"€{report.total_eur - report.cash_eur:,.0f}"
                    )
                    _stat_tile("Cash", f"€{report.cash_eur:,.0f}")
                    _stat_tile(
                        "USD→EUR fx",
                        f"{report.fx_usd_eur:.4f}" if report.fx_usd_eur else "n/a",
                    )
                columns = [
                    {"name": "symbol", "label": "ETF", "field": "symbol", "align": "left"},
                    {"name": "target", "label": "Target", "field": "target", "align": "right"},
                    {"name": "now", "label": "Live", "field": "now", "align": "right"},
                    {"name": "gap", "label": "Gap", "field": "gap", "align": "right"},
                ]
                rows = []
                for row in report.rows:
                    rows.append(
                        {
                            "symbol": row.symbol,
                            "target": _fmt_pct(row.target_weight),
                            "now": (
                                _fmt_pct(row.live_weight)
                                if row.live_weight is not None
                                else "held — no local price"
                            ),
                            "gap": (
                                f"buy €{row.gap_eur:,.0f}"
                                if row.gap_eur is not None and row.gap_eur > 0
                                else (
                                    f"excess €{-row.gap_eur:,.0f}"
                                    if row.gap_eur is not None
                                    else "—"
                                )
                            ),
                        }
                    )
                if report.outside_target:
                    rows.append(
                        {
                            "symbol": f"Outside target ({len(report.outside_target)} more)",
                            "target": "—",
                            "now": _fmt_pct(outside_pct),
                            "gap": "yours, untouched",
                        }
                    )
                ui.table(columns=columns, rows=rows, row_key="symbol").classes("w-full").props(
                    "flat bordered dense"
                )
                if report.unpriced:
                    ui.label(
                        "Not priced locally (excluded from the gap): "
                        + ", ".join(report.unpriced)
                    ).classes("text-caption text-warning")
                if report.outside_target:
                    outside = ", ".join(
                        f"{sym} €{val:,.0f}" for sym, val in report.outside_target[:6]
                    )
                    ui.label(
                        f"Held but outside this target: {outside}"
                        + (
                            " …"
                            if len(report.outside_target) > 6
                            else ""
                        )
                        + " — the plan below only funds the target sleeves."
                    ).classes("text-caption")

                # Buy-only path: new money closes the underweights, the
                # dilution philosophy — the robot never sells the real
                # account (selling is the owner's call, priced below).
                with ui.row().classes("w-full items-end gap-sm no-wrap q-mt-md"):
                    monthly = ui.number(
                        "New money to invest (€)", value=3000, min=0, step=100
                    ).style("max-width:220px")

                    def _plan_buys() -> None:
                        buys_box.clear()
                        plan = real_gap.plan_buys(report, D(str(monthly.value or 0)))
                        with buys_box:
                            if not plan:
                                ui.label(
                                    "No underweights to fund — the live account already "
                                    "covers every sleeve."
                                ).classes("text-caption")
                                return
                            ui.label(
                                "Buy only, no sells — new money closes the gaps:"
                            ).classes("text-body2")
                            for sym, amount in plan:
                                ui.label(f"· {sym}: €{amount:,.0f}").classes(
                                    "text-body2"
                                ).style("padding-left:12px")

                    ui.button(
                        "Plan these buys",
                        icon="shopping_cart",
                        on_click=_plan_buys,
                    ).props("unelevated no-caps").classes("run-btn")
                buys_box = ui.column().classes("w-full gap-xs")

                trims = real_gap.trim_costs(report, snapshot)
                if trims:
                    with ui.expansion(
                        "If you sold the excess today (tax estimate)", icon="sell"
                    ).classes("w-full q-mt-sm"):
                        ui.label(
                            "You said you would rather not sell — this is only what "
                            "trimming back to target would cost in estimated tax "
                            "(average-cost basis, Spain savings rates)."
                        ).classes("text-caption")
                        trim_rows = [
                            {
                                "symbol": t.symbol,
                                "excess": f"€{t.excess_value_eur:,.0f}",
                                "qty": f"{t.quantity:.2f} sh",
                                "tax": (
                                    f"€{t.est_tax_eur:,.0f} ({t.marginal_rate * 100:.0f}%)"
                                    if t.est_tax_eur > 0
                                    else "€0 (loss or within allowance)"
                                ),
                            }
                            for t in trims
                        ]
                        ui.table(
                            columns=[
                                {
                                    "name": "symbol",
                                    "label": "ETF",
                                    "field": "symbol",
                                    "align": "left",
                                },
                                {
                                    "name": "excess",
                                    "label": "Excess",
                                    "field": "excess",
                                    "align": "right",
                                },
                                {
                                    "name": "qty",
                                    "label": "Shares",
                                    "field": "qty",
                                    "align": "right",
                                },
                                {
                                    "name": "tax",
                                    "label": "Est. tax",
                                    "field": "tax",
                                    "align": "right",
                                },
                            ],
                            rows=trim_rows,
                            row_key="symbol",
                        ).props("flat bordered dense")

        async def _render_drift_card(target, pm_store) -> None:
            state = await _gather_account_state(target, pm_store)
            positions_map = state.pop("positions_map")
            positions = state["positions"]
            cash = state["cash"]
            prices = state["prices"]
            lots_by_symbol = state["lots_by_symbol"]
            last_rebalance = state["last_rebalance"]

            from app.services.portfolio_management.drift import compute_drift

            total = sum(positions.values(), D("0")) + cash
            drifts = compute_drift(target.holdings, positions, total, target.drift_band_pct)

            with ui.element("div").classes("panel q-pa-md w-full q-mt-md"):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    ui.label("4 · On track?").classes("text-h6")
                    cooldown_left = cooldown_ends_at(last_rebalance, target.cooldown_days)
                    if cooldown_left and cooldown_left > datetime.utcnow():
                        ui.badge(
                            f"cooling down until {cooldown_left:%d %b %H:%M}", color="grey"
                        ).props("outline")
                invested = sum(positions.values(), D("0"))
                # "Empty" = the cash is not INVESTED yet (a fresh portfolio is
                # 100% cash, so total>0 — the deploy step is still pending).
                if invested <= 0:
                    ui.label(
                        "Cash not invested yet — the portfolio is saved but not "
                        "bought. Press “Apply to paper account” to deploy it "
                        "(you confirm the exact orders first)."
                    ).classes("text-caption")
                else:
                    unrealized = sum((p.unrealized_pl for p in positions_map.values()), D("0"))
                    pl_color = "var(--ds-good)" if unrealized >= 0 else "var(--ds-bad)"
                    with ui.row().classes("w-full gap-sm wrap q-mb-md"):
                        _stat_tile("Paper account", f"€{total:,.0f}")
                        _stat_tile("Invested", f"€{invested:,.0f}")
                        _stat_tile("Cash", f"€{cash:,.0f}")
                        _stat_tile("Unrealized P&L", f"€{unrealized:+,.0f}", pl_color)
                    columns = [
                        {"name": "symbol", "label": "ETF", "field": "symbol", "align": "left"},
                        {"name": "target", "label": "Target", "field": "target", "align": "right"},
                        {"name": "current", "label": "Now", "field": "current", "align": "right"},
                        {"name": "drift", "label": "Drift", "field": "drift", "align": "right"},
                        {"name": "pl", "label": "P&L", "field": "pl", "align": "right"},
                        {"name": "status", "label": "Status", "field": "status", "align": "left"},
                    ]
                    rows = []
                    for drift in drifts:
                        pl_pos = positions_map.get(drift.symbol)
                        rows.append(
                            {
                                "symbol": drift.symbol,
                                "target": _fmt_pct(drift.target_weight),
                                "current": _fmt_pct(drift.current_weight),
                                "drift": f"{(drift.drift * D('100')):+.1f} pp",
                                "pl": (
                                    f"€{pl_pos.unrealized_pl:+,.0f}" if pl_pos is not None else "—"
                                ),
                                "status": "⚠ outside band" if drift.breached else "✓ in band",
                            }
                        )
                    ui.table(columns=columns, rows=rows, row_key="symbol").classes("w-full").props(
                        "flat bordered dense"
                    )
                with (
                    ui.row().classes("w-full items-center gap-sm no-wrap").style("margin-top:12px")
                ):
                    ui.button(
                        "Apply to paper account",
                        icon="science",
                        on_click=lambda: _preview(
                            target, positions, cash, prices, lots_by_symbol, last_rebalance
                        ),
                    ).props("unelevated no-caps").classes("run-btn").tooltip(
                        "Preview first: the exact trades and their tax impact in € — "
                        "nothing is sent until you confirm."
                    )
                    ui.button(
                        "Refresh",
                        icon="refresh",
                        on_click=lambda: render_state.refresh(),
                    ).props("flat no-caps dense").tooltip(
                        "Re-read the paper account and current prices."
                    )
                    ui.button(
                        "Fresh start",
                        icon="restart_alt",
                        on_click=lambda: _fresh_start_dialog(pm_store),
                    ).props("flat no-caps dense").style("color:var(--ds-bad)").tooltip(
                        "Empty the paper account back to its starting cash and clear "
                        "the tax lots (history stays for audit)."
                    )

        def _fresh_start_dialog(pm_store) -> None:
            with ui.dialog() as dialog, ui.card().classes("min-w-[480px]"):
                ui.label("Fresh paper start?").classes("text-h6")
                ui.label(
                    "This empties the paper account (positions and cash reset to the "
                    "starting amount) and clears the tax lots. The event history stays "
                    "as an audit trail. Nothing touches your real broker."
                ).classes("text-body2")
                with ui.row().classes("w-full justify-end gap-sm"):
                    ui.button("Cancel", on_click=dialog.close).props("flat")

                    async def _do_reset() -> None:
                        await _reset_paper_account(pm_store)
                        dialog.close()
                        ui.notify("Paper account reset to its starting cash.", type="positive")
                        render_state.refresh()

                    ui.button(
                        "Reset the paper account", icon="restart_alt", on_click=_do_reset
                    ).props("unelevated no-caps").classes("run-btn")
            dialog.open()

        async def _reset_paper_account(pm_store) -> None:
            """Supervised fresh start: broker account back to initial cash,
            lots cleared, persisted paper state removed. Events are kept."""
            from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter
            from app.services.portfolio_management.named_portfolios import paper_state_path

            broker = await _get_broker()
            adapter = broker.adapter
            if isinstance(adapter, PaperAdapter):
                adapter.positions.clear()
                if adapter.account is not None:
                    adapter.account.cash_available = adapter.initial_cash
                    adapter.account.portfolio_value = adapter.initial_cash
                    adapter.account.buying_power = adapter.initial_cash
                    adapter.account.equity = adapter.initial_cash
                    adapter.account.margin_used = D("0")
            Path(paper_state_path(_ACTIVE_SLUG)).unlink(missing_ok=True)
            cleared = await pm_store.clear_lots()
            await pm_store.append_event(
                trigger="manual",
                action="reset",
                reason=(
                    "Fresh paper start: account emptied back to starting cash, "
                    "tax lots cleared (this event is the audit trail)."
                ),
                details={"cleared_lots": cleared},
            )

        async def _preview(target, positions, cash, prices, lots_by_symbol, last_rebalance) -> None:
            cooling_until = cooldown_ends_at(last_rebalance, target.cooldown_days)
            was_cooling = bool(cooling_until and cooling_until > datetime.utcnow())
            ctx = PlanContext(
                target=target,
                positions=positions,
                cash=cash,
                prices=prices,
                lots=lots_by_symbol,
                last_rebalance=last_rebalance,
                # The cooldown stops the ROBOT from churning — it must never
                # lock out the owner: a manual click plans through it, with
                # the bypass said out loud (supervision rule).
                forced=True,
                forced_trigger=RebalanceTrigger.MANUAL,
            )
            plan = plan_rebalance(ctx, tax_preview=SpainRebalanceTax().preview_sell)

            with ui.dialog() as dialog, ui.card().classes("min-w-[720px]"):
                ui.label("Apply to your paper account").classes("text-h6")
                ui.label(
                    "Real rules, imaginary money — every trade below goes through the "
                    "same risk gates as live trading."
                ).classes("text-caption")
                if was_cooling:
                    ui.label(
                        f"Supervised action: bypassing the robot's rest period "
                        f"(until {cooling_until:%d %b %H:%M}) — you pressed the button, "
                        f"this trades now."
                    ).classes("text-caption text-warning")
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
                        ).props("unelevated no-caps").classes("run-btn")
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
            with ui.element("div").classes("panel q-pa-md w-full q-mt-md"):
                ui.label("5 · What the robot did, and why").classes("text-h6")
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
                                "reset": "warning",
                            }.get(event["action"], "grey")
                            ui.badge(event["action"], color=color).props("outline").classes(
                                "q-mt-xs"
                            )
                            with ui.column().classes("gap-0 flex-1"):
                                ui.label(event["reason"]).classes("text-body2")
                                ui.label(
                                    f"{event['ts'][:16].replace('T', ' ')} · trigger {event['trigger']}"
                                ).classes("text-caption")
                                # Order-level detail: every fill/rejection the
                                # supervisor is accountable for, not just the summary.
                                details = event.get("details") or {}
                                for order in details.get("executed") or []:
                                    ui.label(
                                        f"↳ {order.get('side')} {order.get('symbol')} · "
                                        f"{D(str(order.get('quantity', '0'))).normalize():f} shares "
                                        f"@ €{D(str(order.get('price', '0'))):,.2f} · "
                                        f"order {str(order.get('order_id', ''))[:12]}"
                                    ).classes("text-caption").style(
                                        "color:var(--ds-good);padding-left:18px"
                                    )
                                for failed in details.get("failed") or []:
                                    ui.label(
                                        f"↳ ✗ {failed.get('symbol', '?')}: {failed.get('error', '?')}"
                                    ).classes("text-caption").style(
                                        "color:var(--ds-bad);padding-left:18px"
                                    )

        async def _first_render() -> None:
            await render_state()
            # Mission Control hand-off: the freshly created portfolio is
            # selected; if its account is still empty, open the deployment
            # preview so one Confirm invests the cash. The Confirm button
            # stays manual — nothing trades without the owner's click.
            if not autodeploy:
                return
            target = target_state.get("target")
            if target is None or target_state.get("editing"):
                return
            pm_store = await _get_store()
            state = await _gather_account_state(target, pm_store)
            state.pop("positions_map")
            invested = sum(state["positions"].values(), D("0"))
            cash = state["cash"]
            # deploy=1 only auto-OPENS the preview when there is cash sitting
            # uninvested; if positions exist it stays closed (no nagging).
            if invested <= 0 and cash > 0:
                await _preview(**state)

        ui.timer(0.1, _first_render, once=True)

        ui.label(
            "Paper mode: orders go to the deterministic paper broker through the same "
            "risk gates as live trading. The account is saved after every execution "
            "and restored on restart, so the dashboard and the daily runner share one "
            "paper portfolio."
        ).classes("text-caption q-mt-md text-grey-7")
