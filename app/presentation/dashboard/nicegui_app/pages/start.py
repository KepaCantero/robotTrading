"""UI-1 — /start: the 5-question wizard behind NAMED investor profiles.

The owner answers five plain questions once per profile and names it
("Conservative", "Retirement", …) — several can coexist (product rule:
anything account-like is plural and user-named). Mission Control (/swarm)
lists the saved profiles and applies the chosen one as the run
configuration; /start is only where profiles are created and edited.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.pages.swarm import OBJECTIVES, SPANISH_PROVINCES
from app.services.agent_swarm.investor_profile import (
    InvestorProfile,
    delete_profile,
    get_profile,
    list_profiles,
    save_profile,
    set_active,
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
RISK_OPTIONS = {"Low": "BAJO", "Medium": "MEDIO", "High": "ALTO"}
#: FIX 5 (owner 31-10): PERFIL 45 — la edad por defecto del wizard. La banda
#: 35–50 lleva 45 como representante y viene PRESELECCIONADA: quien no toca
#: nada guarda el perfil del owner (45 años).
AGE_OPTIONS = {"Under 35": 30, "35–50": 45, "50–65": 57, "Over 65": 70}
DEFAULT_AGE = 45

#: the SAME objectives Mission Control runs, same labels (no drift), with
#: the owner-decreed default first (31-10). The wizard must never offer
#: less than /swarm ("faltan opciones", 31-10).
_GOAL_ORDER = (
    "ACUMULAR",
    "VIVIR_DE_LA_CARTERA",
    "BALANCED_GROWTH",
    "MAXIMIZAR_CAPITAL",
    "MAXIMIZAR_DIVIDENDOS",
    "INCOME_GENERATION",
    "CAPITAL_PRESERVATION",
)
GOAL_OPTIONS = {key: OBJECTIVES[key] for key in _GOAL_ORDER}

#: value → label, so a SAVED profile redisplays as the answers the user
#: picked (the wizard writes values, humans read labels).
_AGE_LABEL = {v: k for k, v in AGE_OPTIONS.items()}
_HORIZON_LABEL = {months: label for label, (_, months) in HORIZON_WINDOWS.items()}


def _profile_summary(profile: InvestorProfile) -> str:
    """One sober line per profile: what Mission Control would run."""
    return " · ".join(
        (
            GOAL_OPTIONS.get(profile.objetivo_inversion, profile.objetivo_inversion),
            _HORIZON_LABEL.get(profile.investment_horizon, f"{profile.investment_horizon // 12}y"),
            {v: k for k, v in RISK_OPTIONS.items()}.get(
                profile.risk_tolerance, profile.risk_tolerance
            ),
            profile.tax_province,
            f"age {profile.investor_age}",
        )
    )


def render(profiles_path: str | Path | None = None) -> None:
    """Render the profile manager + wizard.

    The five answers are persisted under a NAME — Mission Control lists
    the saved profiles and applies the chosen one. Before 31-10 the page
    also ran the pipeline itself ("Show my portfolio"); that lives in
    /swarm now, one single place that shows portfolios.
    """
    ds.inject()
    ui.add_head_html(
        "<style>body { background: var(--ds-bg); font-family: var(--ds-font); "
        "color: var(--ds-text); }</style>"
    )
    answers: dict[str, Any] = {
        "age": DEFAULT_AGE,  # PERFIL 45: preselected, changeable in one click
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
            "Investor profiles",
            "Answer five questions, name the profile, save. Keep as many as "
            "you need — Mission Control runs any of them.",
        )

        # ── saved profiles ───────────────────────────────────────────
        with ds.card(title="Saved profiles").classes("w-full"):
            profiles_holder = ui.column().classes("w-full gap-2")

        def _refresh_profiles() -> None:
            profiles_holder.clear()
            with profiles_holder:
                profiles = list_profiles(profiles_path)
                if not profiles:
                    ds.empty_state(
                        "No profiles yet — answer the questions below and save your first one.",
                        icon="🗂",
                    )
                    return
                for p in profiles:
                    with ui.row().classes("w-full items-center gap-4 no-wrap"):
                        with ui.column().classes("gap-1 flex-1").style("min-width:0"):
                            ui.label(p.name).style(
                                "font-size:15px;font-weight:600;color:var(--ds-text)"
                            )
                            ui.label(_profile_summary(p)).style(
                                "color:var(--ds-text_soft);font-size:var(--ds-small-size)"
                            )
                        ui.button(
                            "Load",
                            on_click=lambda name=p.name: _load(name),
                        ).props("flat dense no-caps").mark(f"load_{p.name}")
                        ui.button(
                            icon="delete",
                            on_click=lambda name=p.name: _confirm_delete(name),
                        ).props("flat dense round").mark(f"delete_{p.name}").tooltip(
                            "Delete this profile"
                        )

        pending_delete: dict[str, str | None] = {"name": None}
        delete_dialog = ui.dialog()
        with delete_dialog:
            with ui.card().classes("p-6"):
                delete_label = ui.label("Delete this profile?")
                with ui.row().classes("gap-4"):
                    ui.button("Cancel", on_click=delete_dialog.close).props("flat no-caps")
                    ui.button("Delete", on_click=lambda: _do_delete()).mark("confirm_delete")

        def _confirm_delete(name: str) -> None:
            pending_delete["name"] = name
            delete_label.text = f"Delete profile “{name}”?"
            delete_dialog.open()

        def _do_delete() -> None:
            delete_dialog.close()
            name = pending_delete.get("name")
            pending_delete["name"] = None
            if not name:
                return
            delete_profile(name, profiles_path)
            status.text = f"Profile “{name}” deleted."
            _refresh_profiles()

        # ── the wizard: five questions + name + save ─────────────────
        with ds.card(title="Your answers").classes("w-full"):
            name_input = (
                ui.input("Profile name", validation={"Too long": lambda v: len(v) <= 40})
                .props("dense outlined clearable")
                .mark("profile_name")
            )
            ui.label("A name you will recognise in Mission Control.").style(
                "color:var(--ds-text_soft);font-size:var(--ds-small-size)"
            )
            with ui.grid(columns=2).classes("gap-4 w-full q-mt-md"):
                with ds.card(title="1 · Age", alt=True):
                    for label, age in AGE_OPTIONS.items():
                        b = _option("age", age, label)
                        if age == DEFAULT_AGE:
                            b.classes(add="ds-option--selected")
                with ds.card(title="2 · Time horizon", alt=True):
                    for label in HORIZON_WINDOWS:
                        _option("horizon", label, label)
                with ds.card(title="3 · Risk tolerance", alt=True):
                    t3 = ds.eli5_tooltip(
                        ui.label(
                            "A fall means the portfolio temporarily loses value before it recovers."
                        ).style("font-size:var(--ds-small-size);color:var(--ds-text_soft)"),
                        "Market fall",
                        "Prices go down sometimes. Low-risk portfolios fall less "
                        "but grow slower; high-risk ones fall harder but usually "
                        "grow more.",
                    )
                    del t3
                    for label, value in RISK_OPTIONS.items():
                        _option("risk", value, label)
                with ds.card(title="4 · Tax residence", alt=True):
                    ui.select(
                        {p: p for p in SPANISH_PROVINCES},
                        value="Madrid",
                        label="Province",
                        on_change=lambda e: _pick("province", e.value, e.value),
                    ).classes("w-full")
                with ds.card(title="5 · Objective", alt=True).classes("col-span-2"):
                    with ui.row().classes("gap-4 flex-wrap"):
                        for value, label in GOAL_OPTIONS.items():
                            _option("goal", value, label)

        status = ui.label("").style("color:var(--ds-teal_deep);font-weight:600")
        ds.button("Save profile", on_click=lambda: _save()).mark("save_profile")

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
                f"{filled}/4 key questions answered" if filled < 4 else "All questions answered."
            )

        def _load(name: str) -> None:
            profile = get_profile(name, profiles_path)
            if profile is None:
                status.text = f"Profile “{name}” no longer exists."
                _refresh_profiles()
                return
            answers.update(
                {
                    "age": profile.investor_age,
                    "horizon": _HORIZON_LABEL.get(profile.investment_horizon),
                    "risk": profile.risk_tolerance,
                    "province": profile.tax_province,
                    "goal": profile.objetivo_inversion,
                }
            )
            for key, pairs in option_buttons.items():
                for value, b in pairs:
                    if answers[key] is not None and value == answers[key]:
                        b.classes(add="ds-option--selected")
                    else:
                        b.classes(remove="ds-option--selected")
            name_input.value = profile.name
            status.text = f"Editing “{profile.name}” — all questions pre-filled."

        def _save() -> None:
            missing = [k for k in ("age", "horizon", "risk", "goal") if not answers[k]]
            if missing:
                status.text = "Answer the four key questions first (province defaults to Madrid)."
                return
            name = (name_input.value or "").strip()
            if not name:
                status.text = "Give the profile a name before saving."
                return
            profile = InvestorProfile(
                name=name,
                investor_age=int(answers["age"]),
                investment_horizon=HORIZON_WINDOWS[answers["horizon"]][1],
                risk_tolerance=str(answers["risk"]),
                tax_province=str(answers["province"]),
                objetivo_inversion=str(answers["goal"]),
            )
            save_profile(profile, profiles_path)
            set_active(profile.name, profiles_path)  # newest intent wins in /swarm
            status.text = f"Profile “{name}” saved."
            _refresh_profiles()

        _refresh_profiles()
        _refresh_status()
