"""NiceGUI application factory for the backtesting dashboard.

Creates and configures the NiceGUI app with layout, pages, and dark mode.
"""

from nicegui import ui

from app.presentation.dashboard.nicegui_app.layout import AppShell


def create_app() -> None:
    """Initialize the NiceGUI backtesting dashboard application."""
    AppShell.setup()


def run(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> None:
    """Run the NiceGUI dashboard server."""
    create_app()
    ui.run(host=host, port=port, reload=reload, title="AlgoTrading Dashboard", dark=True)


if __name__ == "__main__":
    run()
