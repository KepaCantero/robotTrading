"""Reusable metric card components.

Provides styled cards for displaying key performance metrics
(total return, Sharpe ratio, max drawdown, etc.).
"""

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import COLORS


def metric_card(
    title: str,
    value: str,
    subtitle: str = "",
    color: str = "",
) -> None:
    """Render a single metric card with title, value, and optional subtitle."""
    bg = color or COLORS["primary"]
    with ui.card().classes("q-pa-sm").style(f"border-left: 4px solid {bg}; min-width: 150px"):
        ui.label(title).classes("text-caption text-grey")
        ui.label(value).classes("text-h5 font-bold")
        if subtitle:
            ui.label(subtitle).classes("text-caption")
