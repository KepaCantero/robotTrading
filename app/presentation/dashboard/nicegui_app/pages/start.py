"""UI-1 — /start: the 5-question wizard (the master move).

A complete novice goes from zero to a VALIDATED portfolio in under five
minutes: 5 plain-English cards → proposed pie → "Validate it" runs the
REAL pipeline (same executor as Mission Control) behind a plain-language
narration → honest numbers with trust badges. The optimizer stays
INVISIBLE — presets, never sliders (novice rule from the plan).
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.pages.swarm import SPANISH_PROVINCES, preset_for_goal

#: plain-English narration per pipeline stage (Mission Control vocabulary)
STAGE_LINES: dict[str, str] = {
    "t11": "Reading your answers…",
    "t21": "Shaping a profile that fits you…",
    "t31": "Choosing sensible settings — no knobs for you to worry about…",
    "t41": "Checking years of market history with real fees included…",
    "t51": "Making sure the tax rules of your province are respected…",
    "t61": "Scoring how solid this portfolio really is…",
    "t71": "Drawing your portfolio…",
    "t81": "Auditing the whole run…",
    "t91": "Writing the report…",
    "t101": "Wrapping up…",
}

HORIZON_WINDOWS = {
    "3–5 years": ("5y", 60),
    "5–10 years": ("10y", 120),
    "10+ years": ("max", 240),
}
RISK_OPTIONS = {"Cautious": "BAJO", "Balanced": "MEDIO", "Adventurous": "ALTO"}
AGE_OPTIONS = {"Under 35": 30, "35–50": 42, "50–65": 57, "Over 65": 70}
GOAL_OPTIONS = {
    "Monthly income (dividends)": "MAXIMIZAR_DIVIDENDOS",
    "Keep my money safe": "CAPITAL_PRESERVATION",
    "Grow it over time": "BALANCED_GROWTH",
}
DEFAULT_CAPITAL = Decimal("10000")


def _horizon_window(label: str) -> tuple[str, int]:
    """('10y', months) — the backtest window IS the horizon (period=horizon)."""
    return HORIZON_WINDOWS[label]


def _narration_for(stage_id: str) -> str:
    return STAGE_LINES.get(stage_id, "Working…")


def render() -> None:
    ds.inject()
    ui.add_head_html(
        "<style>body { background: var(--ds-bg); font-family: var(--ds-font); "
        "color: var(--ds-text); } .opt-btn { width: 100%; justify-content: flex-start; "
        "text-align: left; }</style>"
    )
    answers = {
        "age": None,
        "horizon": None,
        "risk": None,
        "province": "Madrid",
        "goal": None,
    }
    option_buttons: dict[str, list] = {}

    def _option(key: str, value, label: str) -> ui.button:
        """One answer choice — the selected state glows, siblings un-glow."""
        b = (
            ui.button(label, on_click=lambda: _pick(key, value, label, b))
            .classes("ds-option")
            .props("no-caps unelevated")
        )
        option_buttons.setdefault(key, []).append(b)
        return b

    with ui.column().classes("w-full max-w-[1040px] mx-auto p-8 gap-6"):
        ds.section_heading(
            "Let's build your portfolio",
            "Five simple questions — no jargon, nothing to install. "
            "You'll see exactly how it would have done, fees included.",
        )

        # ── the 5 question cards ─────────────────────────────────────
        with ui.grid(columns=2).classes("gap-4 w-full"):
            with ds.card(title="1 · How old are you?").classes("ds-card--hover ds-enter"):
                for label, age in AGE_OPTIONS.items():
                    _option("age", age, label)
            with ds.card(title="2 · How long until you need it?").classes(
                "ds-card--hover ds-enter"
            ):
                for label in HORIZON_WINDOWS:
                    _option("horizon", label, label)
            with ds.card(title="3 · How do you feel about falls?"):
                t3 = ds.eli5_tooltip(
                    ui.label(
                        "A fall means your portfolio temporarily loses value before it recovers."
                    ).style("font-size:var(--ds-small-size);color:var(--ds-text_soft)"),
                    "Market fall",
                    "Prices go down sometimes. Cautious portfolios fall less but "
                    "grow slower; adventurous ones fall harder but usually grow more.",
                )
                del t3
                for label, value in RISK_OPTIONS.items():
                    _option("risk", value, label)
            with ds.card(title="4 · Where do you pay taxes?"):
                ui.select(
                    {p: p for p in SPANISH_PROVINCES},
                    value="Madrid",
                    label="Province",
                    on_change=lambda e: _pick("province", e.value, e.value),
                ).classes("w-full")
            with ds.card(title="5 · What is the money for?").classes("col-span-2"):
                with ui.row().classes("gap-4 flex-wrap"):
                    for label, goal in GOAL_OPTIONS.items():
                        ui.button(
                            label, on_click=lambda g=goal, t=label: _pick("goal", g, t)
                        ).classes("ds-btn ds-btn--secondary").props("no-caps unelevated outline")

        status = ui.label("").style("color:var(--ds-teal_deep);font-weight:600")
        go = ds.button("Show my portfolio →", on_click=lambda: _propose())

        # ── proposal + validation area ───────────────────────────────
        proposal = ui.column().classes("w-full gap-6")

        def _pick(key: str, value, _label: str, _btn=None) -> None:
            answers[key] = value
            for b in option_buttons.get(key, []):
                b.classes(remove="ds-option--selected")
            if _btn is not None:
                _btn.classes(add="ds-option--selected")
            filled = sum(1 for k in ("age", "horizon", "risk", "goal") if answers[k])
            status.text = (
                f"{filled}/4 key questions answered"
                if filled < 4
                else "Ready — see what we'd build for you."
            )

        def _propose() -> None:
            missing = [k for k in ("age", "horizon", "risk", "goal") if not answers[k]]
            if missing:
                status.text = "Answer the four key questions first (province defaults to Madrid)."
                return
            go.set_text("Update my portfolio →")
            with proposal:
                proposal.clear()
                _render_proposal()

        def _render_proposal() -> None:
            preset = preset_for_goal(answers["goal"], HORIZON_WINDOWS[answers["horizon"]][1])
            if preset is None:
                # no curated preset for this goal → the executor derives it (D02)
                strategy, universe = None, None
                note = "The engine picks the strategy from your goal automatically."
            else:
                strategy, universe = preset
                note = None
            with ds.card(title="Your proposed portfolio").classes("w-full"):
                if universe:
                    _pie(universe)
                    ui.label(
                        note or "Built for your goal; validated next with real market history."
                    ).style("color:var(--ds-text_soft);font-size:var(--ds-small-size)")
                else:
                    ds.empty_state(
                        "A general-growth mix — the engine will pick it when validating.",
                        icon="🌱",
                    )
            with ui.row().classes("gap-4"):
                ds.button("Validate it", on_click=_validate)
                ds.button("Customize", on_click=lambda: ui.navigate.to("/swarm"), primary=False)

        def _pie(universe: list[str]) -> None:
            n = len(universe)
            colors = ds.CHART_CATEGORICAL
            data = [
                {
                    "value": round(100 / n, 1),
                    "name": s,
                    "itemStyle": {"color": colors[i % len(colors)]},
                }
                for i, s in enumerate(universe)
            ]
            chart = ui.echart(
                {
                    "tooltip": {"trigger": "item", "formatter": "{b}: {c}%"},
                    "series": [
                        {
                            "type": "pie",
                            "radius": ["48%", "74%"],
                            "itemStyle": {
                                "borderRadius": 8,
                                "borderColor": "#fffdf6",
                                "borderWidth": 3,
                                "shadowBlur": 12,
                                "shadowColor": "rgba(62,58,49,0.12)",
                            },
                            "label": {"formatter": "{b}", "color": "#3e3a31"},
                            "emphasis": {"scaleSize": 8},
                            "animationType": "scale",
                            "animationEasing": "elasticOut",
                            "data": data,
                        }
                    ],
                }
            ).classes("w-full h-72 ds-enter")
            del chart

        # ── validation: the REAL pipeline, narrated ──────────────────
        async def _run_pipeline() -> dict:
            from datetime import date, timedelta

            from app.services.agent_swarm.executor import Capa2PipelineExecutor, SwarmRunRequest

            period, months = _horizon_window(answers["horizon"])
            days = {"5y": 1825, "10y": 3650, "max": 7300}[period]
            end = date.today() - timedelta(days=1)
            start = end - timedelta(days=days)
            request = SwarmRunRequest(
                capital_initial=DEFAULT_CAPITAL,
                objetivo_inversion=answers["goal"],
                risk_tolerance=answers["risk"],
                investment_horizon=months,
                investor_age=answers["age"],
                tax_province=answers["province"],
                backtest_start=start.isoformat(),
                backtest_end=end.isoformat(),
            )
            state = await Capa2PipelineExecutor().run(request)
            return {
                "status": state.status,
                "years": round(days / 365.25),
                "payload": state.agents["t41"].output_payload
                if state.status == "completed"
                else None,
            }

        def _validate() -> None:
            with proposal:
                narration_card = ds.card(title="Checking your portfolio…").classes("w-full")
                with narration_card:
                    line = ui.label("Starting the engine…").classes("ds-skeleton")
                    line.style("color:var(--ds-text_soft)")

                async def _task() -> None:
                    try:
                        result = await _run_pipeline()
                        line.classes(remove="ds-skeleton").style("color:var(--ds-text)")
                        narration_card.clear()
                        with narration_card:
                            if result["status"] != "completed" or not result["payload"]:
                                ds.error_state(
                                    "The engine could not validate this portfolio",
                                    "Try a shorter horizon or Customize for more options.",
                                )
                                return
                            _render_honest_numbers(result["payload"], result["years"])
                    except Exception as exc:  # noqa: BLE001 - novice sees a plain error
                        narration_card.clear()
                        with narration_card:
                            ds.error_state("Something went wrong", str(exc)[:120])

                asyncio.get_event_loop().create_task(_task())

        def _render_honest_numbers(payload: dict, years: int) -> None:
            backtest = payload.get("backtest_result") or {}
            metrics = backtest.get("metrics") or {}
            total = metrics.get("total_return_pct")
            dd = metrics.get("max_drawdown_pct")
            with ds.card(title="The honest numbers").classes("w-full"):
                with ui.row().classes("gap-8 flex-wrap items-end"):
                    if total is not None:
                        ds.honest_number(f"{total}%", "total return, fees included")
                    if dd is not None:
                        ds.honest_number(f"{dd}%", "worst fall on the way")
                    if years:
                        ds.honest_number(f"{years:g}", "years of history checked")
                with ui.row().classes("gap-2 mt-4"):
                    ds.validation_badge("fees")
                    if backtest.get("walk_forward_passed"):
                        ds.validation_badge("walk_forward")
                    ds.validation_badge("taxes")
                ui.label(
                    "Past performance never guarantees the future — that's why every "
                    "number here comes from the same engine, with costs, that will "
                    "manage the real thing."
                ).style("color:var(--ds-text_soft);font-size:var(--ds-small-size);margin-top:12px")
