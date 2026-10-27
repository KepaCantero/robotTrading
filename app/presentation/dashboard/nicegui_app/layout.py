"""Application shell layout for the NiceGUI backtesting dashboard.

Provides the main layout structure: left drawer navigation, top header
with dark mode toggle, and a main content area with page routing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import PAGES

if TYPE_CHECKING:
    from app.infrastructure.persistence.backtest_result_store import BacktestResultStore
    from app.presentation.dashboard.profitability_engine import ProfitabilityEngine
    from app.services.agent_swarm.executor import Capa2PipelineExecutor
    from app.services.agent_swarm.store import SwarmRunStore
    from app.services.backtest_runner import BacktestRunner


def _toggle_mode(dark: ui.dark_mode, label: ui.label) -> None:
    """Toggle dark/light mode and update the label text."""
    dark.toggle()
    # dark.value is the *new* state after toggle
    is_dark = dark.value
    label.text = "Dark" if is_dark else "Light"


class AppShell:
    """Main application shell with drawer, header, and routed content area."""

    _store: BacktestResultStore | None = None
    _runner: BacktestRunner | None = None
    _profitability: ProfitabilityEngine | None = None
    _swarm_executor: Capa2PipelineExecutor | None = None
    _swarm_store: SwarmRunStore | None = None

    @classmethod
    def configure(
        cls,
        store: BacktestResultStore,
        runner: BacktestRunner,
        profitability: ProfitabilityEngine,
        swarm_executor: Capa2PipelineExecutor | None = None,
        swarm_store: SwarmRunStore | None = None,
    ) -> None:
        """Inject shared service instances before calling setup()."""
        cls._store = store
        cls._runner = runner
        cls._profitability = profitability
        cls._swarm_executor = swarm_executor
        cls._swarm_store = swarm_store

    @classmethod
    def _build_shell(cls) -> None:
        """Drawer + header, built inside each page so the menu shows everywhere."""
        dark = ui.dark_mode(True)

        with ui.left_drawer(bordered=True).classes("bg-[#1a1a2e]"):
            ui.label("AlgoTrading").classes("text-h5 font-bold text-white q-pa-md")
            ui.separator().classes("q-mb-md")
            with ui.column().classes("w-full gap-0"):
                for page in PAGES:
                    ui.button(
                        page["name"],
                        icon=page["icon"],
                        on_click=lambda _, r=page["route"]: ui.navigate.to(r),
                    ).props("flat align=left").classes("w-full text-white text-body1")

        with ui.header().classes("items-center justify-between bg-[#0f3460]"):
            ui.label("Backtesting Dashboard").classes("text-h6")
            with ui.row().classes("items-center gap-sm"):
                mode_label = ui.label("Dark").classes("text-caption")
                ui.button(
                    icon="dark_mode",
                    on_click=lambda: _toggle_mode(dark, mode_label),
                ).props("flat round").tooltip("Toggle dark/light mode")

    @classmethod
    def build_home(cls) -> None:
        """Render the home page (shell + Agent Swarm) for root mode."""
        cls._build_shell()
        from app.presentation.dashboard.nicegui_app.pages.swarm import render

        render(cls._swarm_executor, cls._swarm_store)

    @classmethod
    def setup(cls) -> None:
        """Register every page, each with its own shell (menu on all routes)."""

        # ── Page Routes ────────────────────────────────────────────────────
        def _render_swarm() -> None:
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.swarm import render

            render(cls._swarm_executor, cls._swarm_store)

        @ui.page("/")
        def page_agent_swarm():
            _render_swarm()

        @ui.page("/swarm")
        def page_agent_swarm_alias():
            _render_swarm()

        @ui.page("/portfolio")
        def page_portfolio():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.portfolio import render

            render(cls._swarm_executor, cls._swarm_store)

        @ui.page("/optimize")
        def page_optimize():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.optimize import render

            render(cls._swarm_executor, cls._swarm_store)

        @ui.page("/results")
        def page_results():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.backtest_results import render

            render(cls._store, cls._profitability)

        @ui.page("/start")
        def page_start():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.start import render

            render()

        @ui.page("/trust")
        def page_trust():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.trust import render

            render(cls._swarm_executor, cls._swarm_store)

        @ui.page("/design")
        def page_design():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.design import render

            render()

        @ui.page("/history")
        def page_history():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.history_compare import render

            render(cls._store, cls._profitability)

        @ui.page("/objectives")
        def page_objectives():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.objectives import render

            render(cls._store)

        @ui.page("/config")
        def page_config():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.config_viewer import render

            render()

        @ui.page("/profitability")
        def page_profitability():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.profitability import render

            render(cls._store, cls._profitability)
