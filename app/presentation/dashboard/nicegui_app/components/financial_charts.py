"""Financial chart components.

Candlestick, equity curve, and drawdown chart components using ECharts.
"""

from nicegui import ui


def equity_curve_chart() -> None:
    """Render a placeholder equity curve chart."""
    with ui.card().classes("w-full"):
        ui.label("Equity Curve").classes("text-h6")
        ui.label("Chart will be rendered here.").classes("text-grey")
