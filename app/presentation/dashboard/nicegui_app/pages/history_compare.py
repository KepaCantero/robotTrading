"""History & Compare page - historical runs and side-by-side comparison.

Shows past backtest runs in a table with diff comparison between runs.
"""

from nicegui import ui


def render() -> None:
    """Render the History & Compare page content."""
    with ui.card().classes("w-full"):
        ui.label("History & Compare").classes("text-h5")
        ui.label("Compare historical backtest runs side by side.")
