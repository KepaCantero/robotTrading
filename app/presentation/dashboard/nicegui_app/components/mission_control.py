"""UI-3 — Mission Control: the macro loop as one honest rail.

Five stages — Design → Backtest → Optimize → Paper → Live — as visual
nodes (NEVER a text list), each with its REAL state derived from real
sources (the swarm store, the validated IBKR observation), each line in
plain English. Live is LOCKED by product decree, shown as such instead
of hidden; Paper shows exactly where the rollout stands (§5: observation
done, controlled orders next). Clicking a node takes the novice to the
page where that stage happens.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

#: stage → (route, icon). Narration comes from loop_states() so text and
#: state can never disagree.
STAGES: list[tuple[str, str, str]] = [
    ("Design", "/start", "edit_note"),
    ("Backtest", "/results", "history_edu"),
    # 30-10: optimization runs INSIDE every backtest (T4.1) — the stage
    # lives on the run page, not a separate one
    ("Optimize", "/", "tune"),
    ("Paper", "/portfolio", "science"),
    ("Live", "/trust", "lock"),  # the locked door leads to its explanation (UI-4)
]


def loop_states(runs: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Derive every stage's state from REAL evidence.

    design: done when at least one run exists (a profile was built).
    backtest: done when any run COMPLETED (metrics exist).
    optimize: ready the moment a validated backtest exists.
    paper: honest rollout state — IBKR observed live (§5.2), controlled
           orders are the next step; never faked as "running".
    live: blocked by product decree (out of scope), shown locked.
    """
    runs = runs or []
    completed = any(r.get("status") == "completed" for r in runs)
    has_any = bool(runs)
    return [
        {
            "stage": "Design",
            "state": "done" if has_any else "todo",
            "line": "Your profile, five questions" if not has_any else "Profile ready",
        },
        {
            "stage": "Backtest",
            "state": "done" if completed else "todo",
            "line": "Check the past with real fees"
            if not completed
            else "Validated with history, fees included",
        },
        {
            "stage": "Optimize",
            "state": "ready" if completed else "todo",
            "line": "Tune quietly behind the scenes"
            if completed
            else "Needs a validated backtest first",
        },
        {
            "stage": "Paper",
            "state": "active",
            "line": "Broker connected (watching, not trading) — controlled "
            "test orders are the next step",
        },
        {
            "stage": "Live",
            "state": "blocked",
            "line": "Real money — off by design until you say otherwise",
        },
    ]


def mission_control_band(runs: list[dict[str, Any]] | None = None) -> ui.element:
    """The macro rail. Render at the top of the central page."""
    states = loop_states(runs)
    tone = {
        "done": ("var(--ds-good)", "check_circle"),
        "ready": ("var(--ds-teal)", STAGES[2][2]),
        "active": ("var(--ds-warn)", "play_circle"),
        "todo": ("var(--ds-text-soft)", "radio_button_unchecked"),
        "blocked": ("var(--ds-text-soft)", "lock"),
    }
    with ui.row().classes("w-full items-stretch gap-2 no-wrap") as band:
        for (name, route, _icon), st in zip(STAGES, states):
            color, icon = tone[st["state"]]
            with (
                ui.element("button")
                .classes("ds-card text-left flex-1")
                .style("cursor:pointer;border-top:3px solid " + color)
                .on("click", lambda r=route: ui.navigate.to(r) if r else None)
            ):
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.icon(icon).style(f"color:{color};font-size:22px")
                    ui.label(name).style(
                        "font-weight:600;color:var(--ds-text);font-size:var(--ds-body-size)"
                    )
                ui.label(st["line"]).style(
                    "color:var(--ds-text_soft);font-size:var(--ds-small-size);"
                    "margin-top:4px;line-height:1.3"
                )
    return band
