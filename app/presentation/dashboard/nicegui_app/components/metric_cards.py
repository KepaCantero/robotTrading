"""Reusable metric card components.

Provides styled cards for displaying key performance metrics
(total return, Sharpe ratio, max drawdown, etc.) with tooltips
explaining each metric.
"""

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import COLORS, METRIC_DESCRIPTIONS


def metric_card(
    title: str,
    value: str,
    subtitle: str = "",
    color: str = "",
    tooltip: str = "",
) -> None:
    """Render a single metric card with title, value, and optional subtitle."""
    bg = color or COLORS["primary"]
    description = tooltip or METRIC_DESCRIPTIONS.get(title, "")
    with ui.card().classes("q-pa-sm").style(f"border-left: 4px solid {bg}; min-width: 150px"):
        header = ui.label(title).classes("text-caption text-grey")
        if description:
            header.tooltip(description)
        ui.label(value).classes("text-h5 font-bold")
        if subtitle:
            ui.label(subtitle).classes("text-caption")


def skeleton_card() -> None:
    """Render a placeholder skeleton card for loading state."""
    with ui.card().classes("q-pa-sm").style("min-width: 150px; min-height: 80px"):
        ui.skeleton(type="text", height="14px").classes("q-mb-sm")
        ui.skeleton(type="text", height="24px", width="60%").classes("q-mb-xs")
        ui.skeleton(type="text", height="12px", width="40%")
