"""UI-0 — /design: the design-system showcase (acceptance demo).

Every component the system ships, rendered on one warm page. This page
IS the acceptance criterion: "any new page builds only from these".
"""

from __future__ import annotations

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds


def render() -> None:
    ds.inject()
    ui.add_head_html(
        "<style>body { background: var(--ds-bg); font-family: var(--ds-font); "
        "color: var(--ds-text); }</style>"
    )

    with ui.column().classes("w-full max-w-[980px] mx-auto p-8 gap-6"):
        ds.section_heading(
            "Design system",
            "One visual language for every page — cream shell, warm ink, "
            "AA contrast measured by test, not by eye.",
        )

        # ── trust badges + honest numbers ────────────────────────────
        with ds.card(title="Trust layer"):
            with ui.row().classes("gap-2 flex-wrap"):
                ds.validation_badge("fees")
                ds.validation_badge("walk_forward")
                ds.validation_badge("paper")
                ds.validation_badge("taxes")
                ds.validation_badge("partial")
            ui.space()
            with ui.row().classes("gap-8 mt-4"):
                ds.honest_number("+114.9%", "18-year total return")
                ds.honest_number("−17.5%", "worst fall on the way")
                ds.honest_number("0%", "our fee — forever")

        # ── buttons + ELI5 tooltip ───────────────────────────────────
        with ds.card(title="Actions & plain English"):
            with ui.row().classes("items-center gap-4"):
                ds.button("Validate it", on_click=lambda: ui.notify("Backtest launched"))
                ds.button("Customize", on_click=lambda: None, primary=False)
                term = (
                    ui.label("Drawdown")
                    .classes("underline decoration-dotted cursor-help")
                    .style("color:var(--ds-teal_deep)")
                )
                ds.eli5_tooltip(
                    term,
                    "Drawdown",
                    "How far it fell from its highest point before recovering. "
                    "Bigger (more negative) means a scarier ride.",
                )

        # ── states ───────────────────────────────────────────────────
        with ui.row().classes("gap-4 w-full"):
            with ds.card(title="Loading").classes("flex-1"):
                ds.skeleton("70%", "22px")
                ds.skeleton("100%", "14px")
                ds.skeleton("92%", "14px")
            with ds.card(title="Empty").classes("flex-1"):
                ds.empty_state("No portfolio yet — your first one is 5 questions away.")
            with ds.card(title="Error").classes("flex-1"):
                ds.error_state(
                    "Backtest could not run",
                    "SPY history starts in 2016 — pick a window after that.",
                )

        # ── tokens table (the source of truth, visible) ──────────────
        with ds.card(title="Tokens", alt=True):
            with ui.row().classes("gap-3 flex-wrap"):
                for name, value in ds.TOKENS["color"].items():
                    with ui.element("div").classes("text-center"):
                        ui.element("div").style(
                            f"background:{value};width:74px;height:44px;"
                            "border-radius:8px;border:1px solid var(--ds-line)"
                        )
                        ui.label(name).style(
                            "font-size:var(--ds-caption-size);color:var(--ds-text_soft)"
                        )
