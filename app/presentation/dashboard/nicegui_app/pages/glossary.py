"""UI-6 — /glossary: every term, in plain English, one breath each."""

from __future__ import annotations

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds


def render() -> None:
    ds.inject()
    ui.add_head_html(
        "<style>body { background: var(--ds-bg); font-family: var(--ds-font); "
        "color: var(--ds-text); }</style>"
    )
    with ui.column().classes("w-full max-w-[900px] mx-auto p-8 gap-4"):
        ds.section_heading(
            "Plain-English glossary",
            "Every word this app uses, explained the way a friend would — "
            "one breath each. The same texts appear as tooltips where the "
            "words show up.",
        )
        with ui.grid(columns=2).classes("gap-4 w-full"):
            for name, plain in ds.GLOSSARY.items():
                with ds.card():
                    ui.label(name).style("font-weight:600;color:var(--ds-teal_deep)")
                    ui.label(plain).style(
                        "color:var(--ds-text_soft);font-size:var(--ds-small-size)"
                    )
