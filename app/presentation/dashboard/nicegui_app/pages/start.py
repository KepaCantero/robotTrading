"""UI-1 — /start: the 5-question wizard that SAVES your investor profile.

A complete novice answers five plain-English questions ONCE; the profile
is persisted (investor_profile.json) and becomes the default everywhere.
Portfolio building, validation and the honest numbers live in Mission
Control (/swarm) — owner decision 31-10: /start captures the profile,
the swarm agents use it as their default and show the portfolio. There
is exactly one place that shows portfolios.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.pages.swarm import SPANISH_PROVINCES
from app.services.agent_swarm.investor_profile import (
    InvestorProfile,
    load_investor_profile,
    save_investor_profile,
)

#: plain-English narration per pipeline stage. /start itself no longer
#: narrates (the pipeline moved to /swarm) but /trust imports this — it
#: is the app's shared Mission Control vocabulary.
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

#: value → label, so a SAVED profile redisplays as the answers the user
#: picked (the wizard writes values, humans read labels).
_AGE_LABEL = {v: k for k, v in AGE_OPTIONS.items()}
_RISK_LABEL = {v: k for k, v in RISK_OPTIONS.items()}
_GOAL_LABEL = {v: k for k, v in GOAL_OPTIONS.items()}
_HORIZON_LABEL = {months: label for label, (_, months) in HORIZON_WINDOWS.items()}


def render(profile_path: str | Path | None = None) -> None:
    """Render the wizard.

    The five answers are PERSISTED — the saved profile is the default
    config for Mission Control (/swarm), where portfolios are now built
    and validated. Before 31-10 the wizard also ran the pipeline itself
    ("Show my portfolio"); that moved to the swarm agents.
    """
    ds.inject()
    ui.add_head_html(
        "<style>body { background: var(--ds-bg); font-family: var(--ds-font); "
        "color: var(--ds-text); }</style>"
    )
    saved = load_investor_profile(profile_path)
    answers: dict[str, Any] = {
        "age": None,
        "horizon": None,
        "risk": None,
        "province": "Madrid",
        "goal": None,
    }
    option_buttons: dict[str, list[tuple[Any, ui.button]]] = {}

    def _option(key: str, value, label: str) -> ui.button:
        """One answer choice — the selected state glows, siblings un-glow."""
        b = (
            ui.button(label, on_click=lambda: _pick(key, value, label, b))
            .classes("ds-option")
            .props("no-caps unelevated")
            .mark("opt_" + key + "_" + "".join(c for c in label if c.isalnum()))
        )
        option_buttons.setdefault(key, []).append((value, b))
        return b

    with ui.column().classes("w-full max-w-[1040px] mx-auto p-8 gap-6"):
        ds.section_heading(
            "Your investor profile",
            "Five simple questions — no jargon, nothing to install. "
            "Save once: Mission Control builds and tests your portfolio "
            "from this profile, fees included.",
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
                    value=(
                        saved.tax_province
                        if saved and saved.tax_province in SPANISH_PROVINCES
                        else "Madrid"
                    ),
                    label="Province",
                    on_change=lambda e: _pick("province", e.value, e.value),
                ).classes("w-full")
            with ds.card(title="5 · What is the money for?").classes("col-span-2"):
                with ui.row().classes("gap-4 flex-wrap"):
                    for label, goal in GOAL_OPTIONS.items():
                        _option("goal", goal, label)

        status = ui.label("").style("color:var(--ds-teal_deep);font-weight:600")
        go = ds.button("Save my profile →", on_click=lambda: _save()).mark("save_profile")

        # ── the saved profile, always visible once it exists ─────────
        summary = ui.column().classes("w-full gap-6")

        def _pick(key: str, value, _label: str, _btn=None) -> None:
            answers[key] = value
            for _, b in option_buttons.get(key, []):
                b.classes(remove="ds-option--selected")
            if _btn is not None:
                _btn.classes(add="ds-option--selected")
            _refresh_status()

        def _refresh_status() -> None:
            filled = sum(1 for k in ("age", "horizon", "risk", "goal") if answers[k])
            status.text = (
                f"{filled}/4 key questions answered"
                if filled < 4
                else "Ready — saving takes one click."
            )

        def _save() -> None:
            missing = [k for k in ("age", "horizon", "risk", "goal") if not answers[k]]
            if missing:
                status.text = "Answer the four key questions first (province defaults to Madrid)."
                return
            profile = InvestorProfile(
                investor_age=int(answers["age"]),
                investment_horizon=HORIZON_WINDOWS[answers["horizon"]][1],
                risk_tolerance=str(answers["risk"]),
                tax_province=str(answers["province"]),
                objetivo_inversion=str(answers["goal"]),
            )
            save_investor_profile(profile, profile_path)
            status.text = "Saved — Mission Control will use this as your default."
            go.set_text("Update my profile →")
            summary.clear()
            with summary:
                _summary_card(profile)

        def _summary_card(profile: InvestorProfile) -> None:
            with ds.card(title="Your saved investor profile").classes("w-full ds-enter"):
                rows = [
                    ("Age", _AGE_LABEL.get(profile.investor_age, f"{profile.investor_age} years")),
                    (
                        "Horizon",
                        _HORIZON_LABEL.get(
                            profile.investment_horizon,
                            f"{profile.investment_horizon // 12} years",
                        ),
                    ),
                    (
                        "Stomach for falls",
                        _RISK_LABEL.get(profile.risk_tolerance, profile.risk_tolerance),
                    ),
                    ("Taxes in", profile.tax_province),
                    (
                        "Goal",
                        _GOAL_LABEL.get(profile.objetivo_inversion, profile.objetivo_inversion),
                    ),
                ]
                with ui.row().classes("gap-8 flex-wrap items-end"):
                    for label, value_ in rows:
                        with ui.column().classes("gap-1"):
                            ui.label(value_).style(
                                "font-size:20px;font-weight:700;color:var(--ds-teal_deep)"
                            )
                            ui.label(label).style(
                                "color:var(--ds-text_soft);font-size:var(--ds-small-size)"
                            )
                ui.label(
                    f"Saved {profile.updated_at:%d %b %Y, %H:%M}. Mission Control (/swarm) "
                    "builds and validates your portfolio from this profile — "
                    "nothing to answer again."
                ).style("color:var(--ds-text_soft);font-size:var(--ds-small-size);margin-top:12px")
                ds.button(
                    "Build my portfolio in Mission Control →",
                    on_click=lambda: ui.navigate.to("/swarm"),
                ).mark("go_swarm")

        # ── first paint: a saved profile preselects its answers ──────
        if saved is not None:
            answers.update(
                {
                    "age": saved.investor_age,
                    "horizon": _HORIZON_LABEL.get(saved.investment_horizon),
                    "risk": saved.risk_tolerance,
                    "province": saved.tax_province,
                    "goal": saved.objetivo_inversion,
                }
            )
            for key, pairs in option_buttons.items():
                for value, b in pairs:
                    if answers[key] is not None and value == answers[key]:
                        b.classes(add="ds-option--selected")
            if all(answers[k] for k in ("age", "horizon", "risk", "goal")):
                status.text = "Profile loaded — change anything and save again."
                go.set_text("Update my profile →")
                with summary:
                    _summary_card(saved)
            else:  # saved outside the wizard's options → answer what's missing
                _refresh_status()
        else:
            _refresh_status()
