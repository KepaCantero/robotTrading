"""Backtest Runner page - select parameters and run backtests.

Provides strategy/profile selection, time window picker, and execution controls.
"""

from nicegui import ui


def render() -> None:
    """Render the Backtest Runner page content."""
    with ui.card().classes("w-full"):
        ui.label("Backtest Runner").classes("text-h5")
        ui.label("Configure and run backtests from this page.")
