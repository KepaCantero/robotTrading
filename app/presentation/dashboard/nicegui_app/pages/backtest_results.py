"""Backtest Results page - view results and profitability verdict.

Displays metrics, charts, and the profitability pass/fail indicator.
"""

from nicegui import ui


def render() -> None:
    """Render the Backtest Results page content."""
    with ui.card().classes("w-full"):
        ui.label("Backtest Results").classes("text-h5")
        ui.label("View backtest results and profitability analysis.")
