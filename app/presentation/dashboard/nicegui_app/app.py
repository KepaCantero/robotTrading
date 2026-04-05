"""NiceGUI application factory for the backtesting dashboard.

Creates and configures the NiceGUI app with layout, pages, and dark mode.
Initializes shared services (BacktestResultStore, BacktestRunner,
ProfitabilityEngine) and injects them into the application shell.
"""

from __future__ import annotations

import asyncio

from nicegui import ui

from app.infrastructure.persistence.backtest_result_store import BacktestResultStore
from app.presentation.dashboard.nicegui_app.layout import AppShell
from app.presentation.dashboard.profitability_engine import ProfitabilityEngine
from app.services.backtest_runner import BacktestRunner

_DB_PATH = "backtest_results.db"


async def _init_services() -> tuple[BacktestResultStore, BacktestRunner, ProfitabilityEngine]:
    """Create and initialize all dashboard services."""
    store = BacktestResultStore(_DB_PATH)
    await store.initialize()
    runner = BacktestRunner(store)
    profitability = ProfitabilityEngine()
    return store, runner, profitability


def create_app() -> None:
    """Initialize the NiceGUI backtesting dashboard application."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If already inside an async context (e.g. NiceGUI event loop),
        # schedule initialization and use defaults.
        store = BacktestResultStore(_DB_PATH)
        runner = BacktestRunner(store)
        profitability = ProfitabilityEngine()

        async def _init() -> None:
            await store.initialize()

        _task = loop.create_task(_init())  # noqa: RUF006
    else:
        store, runner, profitability = loop.run_until_complete(_init_services())

    AppShell.configure(store, runner, profitability)
    AppShell.setup()


def run(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> None:
    """Run the NiceGUI dashboard server."""
    create_app()
    ui.run(host=host, port=port, reload=reload, title="AlgoTrading Dashboard", dark=True)


if __name__ == "__main__":
    run()
