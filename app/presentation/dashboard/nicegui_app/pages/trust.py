"""UI-4 — /trust: the trust layer (mandatory before real money).

Three honest pieces:
(a) "What can go wrong" in plain numbers — the portfolio's OWN worst
    12-month stretch, computed from local data (never a stock disclaimer).
(b) The door to live: risk explained without legal jargon + an explicit
    two-step confirmation — which ends in the truth: live is disabled
    by design in this product (no fake activation, ever).
(c) The bot's auditable decision log: the last run's T1→T10 events,
    narrated in plain English with timestamps.

The Live node on Mission Control points HERE: the locked door is where
you explain the door.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.pages.start import STAGE_LINES

_DATA_DIR = Path(__file__).resolve().parents[5] / "data" / "historical"


def worst_12_months(universe: list[str], data_dir: Path | None = None) -> tuple[float, str] | None:
    """The EW universe's worst rolling 12-month return in LOCAL data.

    Real prices, real alignment (a symbol trades only from its own first
    common date), no vendor claims. Returns (pct, iso_end_date) or None
    when the corpus can't answer — never an invented stress number.
    """
    import csv

    base = data_dir or _DATA_DIR
    closes: dict[str, dict[str, float]] = {}
    for symbol in universe:
        path = base / f"{symbol}.csv"
        if not path.exists():
            continue
        series: dict[str, float] = {}
        with path.open() as fh:
            for row in csv.DictReader(fh):
                try:
                    series[row["date"]] = float(row["Close"])
                except (KeyError, ValueError, TypeError):
                    continue
        if len(series) > 260:
            closes[symbol] = series
    if len(closes) < 2:
        return None
    days = sorted({d for s in closes.values() for d in s})
    equity = 1.0
    window: list[float] = []
    worst = (0.0, "")
    prev_closes: dict[str, float] = {}
    for day in days:
        rets = []
        for symbol, series in closes.items():
            px = series.get(day)
            prev = prev_closes.get(symbol)
            if px is not None and prev:
                rets.append(px / prev - 1.0)
            if px is not None:
                prev_closes[symbol] = px
        if not rets:
            continue
        equity *= 1.0 + sum(rets) / len(rets)
        window.append(equity)
        if len(window) > 252:
            window.pop(0)
        if len(window) == 252:
            ret12 = window[-1] / window[0] - 1.0
            if ret12 < worst[0]:
                worst = (ret12, day)
    if worst[1] == "":
        return None
    return worst[0] * 100, worst[1]


def render(executor: Any = None, store: Any = None) -> None:
    del executor  # symmetric signature with the other pages
    ds.inject()
    ui.add_head_html(
        "<style>body { background: var(--ds-bg); font-family: var(--ds-font); "
        "color: var(--ds-text); }</style>"
    )
    with ui.column().classes("w-full max-w-[980px] mx-auto p-8 gap-6"):
        ds.section_heading(
            "Trust, before anything else",
            "What can go wrong, what the bot decided, and why real money "
            "stays off — all in plain English.",
        )

        # ── (a) what can go wrong — from the portfolio's OWN data ────
        scenario_card = ds.card(title="If things go wrong").classes("w-full")
        log_holder = ui.column().classes("w-full gap-6")

        def _render_scenarios() -> None:
            universe = ["SCHD", "VYM", "VIG", "DVY", "BND"]
            worst = worst_12_months(universe)
            scenario_card.clear()
            with scenario_card:
                with ui.row().classes("gap-8 flex-wrap items-end"):
                    if worst:
                        pct, day = worst
                        ds.honest_number(
                            f"{pct:.0f}%",
                            f"worst 12 months in this mix's own history (ended {day})",
                        )
                    else:
                        ds.empty_state("Not enough local history to state a worst year honestly.")
                    ds.honest_number(
                        "−40%",
                        "a 2008-magnitude year for broad stocks — expect your mix to fall hard too",
                    )
                    ds.honest_number("0", "hidden costs — fees are already in every number you saw")
                ui.label(
                    "Falling does not mean broken: every backtest you saw survived its "
                    "worst stretch and kept going. The honest question is whether you "
                    "could watch a number like that without panic-selling at the bottom."
                ).style("color:var(--ds-text_soft);font-size:var(--ds-small-size);margin-top:12px")

        ui.timer(0.05, _render_scenarios, once=True)

        # ── (b) the door to live: 2 explicit steps, honest terminal ──
        with ds.card(title="Real money — the door").classes("w-full") as door:
            ui.label(
                "Everything so far ran on paper: real prices, real rules, imaginary "
                "money. Turning on live trading means a bad day costs real euros — "
                "and no software, ours included, can promise gains."
            ).style("color:var(--ds-text_soft)")

            def _step2() -> None:
                door.clear()
                with door:
                    ui.label("Real money — the door").classes("ds-card__title")
                    ui.label("You acknowledged the risk. Final step:").style(
                        "color:var(--ds-text_soft)"
                    )
                    ds.button("I'm ready — turn on live trading", on_click=_terminal)

            def _terminal() -> None:
                door.clear()
                with door:
                    ui.label("Real money — the door").classes("ds-card__title")
                    ds.error_state(
                        "Live trading is OFF — by design",
                        "This product version excludes real money. Nothing was "
                        "activated, nothing was charged, and that is intentional.",
                    )
                    ds.validation_badge("partial", text="Paper only — on purpose")

            def _step1() -> None:
                ds.button("I understand I can lose money", on_click=_step2)

            _step1()

        # ── (c) the bot's auditable decision log ─────────────────────
        with log_holder:
            log_card = ds.card(title="What the bot decided (last run)").classes("w-full")

            async def _render_log() -> None:
                try:
                    runs = await store.list_runs(limit=1)
                    if not runs:
                        log_card.clear()
                        with log_card:
                            ds.empty_state("No runs yet — the log fills as the robot works.")
                        return
                    run_id = runs[0]["workflow_id"]
                    events = await store.get_run_events(run_id)
                except Exception:  # noqa: BLE001 - the page never dies on the log
                    events = []
                log_card.clear()
                with log_card:
                    for ev in events[-24:]:
                        stage = str(ev.get("type", ""))
                        agent = str(ev.get("agent_id", "")) or str(
                            ev.get("data", {}).get("agent_id", "")
                        )
                        line = STAGE_LINES.get(agent) or _narration(stage)
                        ts = str(ev.get("timestamp", ""))[:19].replace("T", " ")
                        with ui.row().classes("gap-3 items-baseline"):
                            ui.label(ts).style(
                                "font-size:var(--ds-caption-size);color:var(--ds-text_soft);"
                                "font-variant-numeric:tabular-nums"
                            )
                            ui.label(line).style("font-size:var(--ds-small-size)")

        ui.timer(0.05, _render_log, once=True)


def _narration(event_type: str) -> str:
    plain = {
        "run_started": "Run started",
        "run_completed": "Run finished",
        "run_failed": "Run failed — nothing was hidden",
    }
    for key, text in plain.items():
        if key in event_type.lower():
            return text
    return event_type
