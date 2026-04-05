"""Profitability page - trends, heatmaps, and verdicts.

Aggregated profitability analysis across strategies, profiles, and time windows.
"""

from nicegui import ui


def render() -> None:
    """Render the Profitability page content."""
    with ui.card().classes("w-full"):
        ui.label("Profitability").classes("text-h5")
        ui.label("Profitability trends, heatmaps, and verdicts.")
