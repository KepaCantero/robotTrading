"""Dividend-specific metrics and charts panel.

DRIP return, yield on cost, dividend income vs capital gains,
payout ratio, dividend aristocrat/king detection.
"""

from nicegui import ui


def dividend_panel() -> None:
    """Render the dividend deep-dive panel."""
    with ui.card().classes("w-full"):
        ui.label("Dividend Analysis").classes("text-h6")
        ui.label("Dividend metrics will be displayed here.").classes("text-grey")
