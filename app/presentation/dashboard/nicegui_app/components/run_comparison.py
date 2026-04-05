"""Side-by-side run comparison component.

Displays two backtest runs with parameter diff and results diff.
"""

from nicegui import ui


def run_comparison() -> None:
    """Render the run comparison component."""
    with ui.card().classes("w-full"):
        ui.label("Run Comparison").classes("text-h6")
        ui.label("Side-by-side comparison will be displayed here.").classes("text-grey")
