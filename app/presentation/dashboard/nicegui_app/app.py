"""NiceGUI application factory for the backtesting dashboard.

Creates and configures the NiceGUI app with layout, pages, and dark mode.
Initializes shared services (BacktestResultStore, BacktestRunner,
ProfitabilityEngine, and the agent-swarm executor + store for the
Mission Control page) and injects them into the application shell.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from nicegui import ui

from app.infrastructure.persistence.backtest_result_store import BacktestResultStore
from app.presentation.dashboard.nicegui_app.layout import AppShell
from app.presentation.dashboard.profitability_engine import ProfitabilityEngine
from app.services.agent_swarm.executor import Capa2PipelineExecutor
from app.services.agent_swarm.store import DEFAULT_SWARM_DB_PATH, SwarmRunStore
from app.services.backtest_runner import BacktestRunner

logger = logging.getLogger(__name__)

_DB_PATH = "backtest_results.db"

_DOCS_SITE = Path(__file__).resolve().parents[4] / "site"


def _mount_pwa() -> None:
    """UI-5: manifest + icons so the dashboard installs as a PWA
    (phone home-screen, no store)."""
    from nicegui import app as nicegui_app
    from starlette.staticfiles import StaticFiles

    pwa_dir = Path(__file__).resolve().parent / "static" / "pwa"
    nicegui_app.mount("/pwa", StaticFiles(directory=str(pwa_dir)), name="pwa")


def _mount_documentation() -> None:
    """Serve the built MkDocs site at /docs so docs live inside the dashboard."""
    from nicegui import app as nicegui_app
    from starlette.staticfiles import StaticFiles

    if (_DOCS_SITE / "index.html").is_file():
        # html=True so /docs/ resolves to the site's index.html.
        nicegui_app.mount(
            "/docs",
            StaticFiles(directory=str(_DOCS_SITE), html=True),
            name="docs-site",
        )
        return

    logger.warning("Docs site not built at %s — run 'make docs-build'.", _DOCS_SITE)

    @ui.page("/docs")
    def _docs_not_built() -> None:
        ui.label("Documentation site is not built yet.").classes("text-h6")
        ui.label(
            "Run  make docs-build  (or  make dashboard, which builds it) and restart."
        ).classes("text-body1")


async def _init_services() -> tuple[
    BacktestResultStore,
    BacktestRunner,
    ProfitabilityEngine,
    Capa2PipelineExecutor,
    SwarmRunStore,
]:
    """Create and initialize all dashboard services."""
    store = BacktestResultStore(_DB_PATH)
    await store.initialize()
    runner = BacktestRunner(store)
    profitability = ProfitabilityEngine()

    swarm_store = SwarmRunStore(DEFAULT_SWARM_DB_PATH)
    await swarm_store.initialize()
    swarm_executor = Capa2PipelineExecutor(store=swarm_store)
    return store, runner, profitability, swarm_executor, swarm_store


def create_app() -> None:
    """Initialize the NiceGUI backtesting dashboard application."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If already inside an async context (e.g. NiceGUI event loop),
        # schedule initialization and use defaults.
        store = BacktestResultStore(_DB_PATH)
        runner = BacktestRunner(store)
        profitability = ProfitabilityEngine()
        swarm_store = SwarmRunStore(DEFAULT_SWARM_DB_PATH)
        swarm_executor = Capa2PipelineExecutor(store=swarm_store)

        async def _init() -> None:
            await store.initialize()
            await swarm_store.initialize()

        _task = loop.create_task(_init())  # noqa: RUF006
    else:
        store, runner, profitability, swarm_executor, swarm_store = loop.run_until_complete(
            _init_services()
        )

    AppShell.configure(store, runner, profitability, swarm_executor, swarm_store)
    _mount_pwa()
    _mount_documentation()
    AppShell.setup()
