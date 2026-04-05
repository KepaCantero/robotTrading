"""Profitability badge component.

PASS/FAIL/INCONCLUSIVE indicator with color-coded styling.
"""

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import profitability_color


def profitability_badge(verdict: str) -> None:
    """Render a color-coded profitability verdict badge."""
    color = profitability_color(verdict)
    ui.badge(verdict.upper(), color=color).classes("text-h6")
