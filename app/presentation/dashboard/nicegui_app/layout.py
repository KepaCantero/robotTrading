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

    MOBILE_NAV = [
        {"name": "Start", "icon": "play_circle", "route": "/start"},
        {"name": "Mission", "icon": "hub", "route": "/"},
        {"name": "Portfolio", "icon": "donut_small", "route": "/portfolio"},
        {"name": "Optimize", "icon": "tune", "route": "/optimize"},
        {"name": "Trust", "icon": "verified_user", "route": "/trust"},
    ]

    @classmethod
    def _build_mobile_nav(cls) -> None:
        """Bottom navigation for phones (UI-5): 44px targets, safe-area
        padding for notched phones, hidden on desktop."""
        ui.add_head_html(
            '<link rel="manifest" href="/pwa/manifest.webmanifest">'
            '<meta name="theme-color" content="#3f8f85">'
            '<link rel="apple-touch-icon" href="/pwa/icon-192.png">'
            "<style>"
            ".ds-mobile-nav { display: none; }"
            "@media (max-width: 900px) {"
            "  .ds-mobile-nav { display: flex; position: fixed; bottom: 0; left: 0;"
            "    right: 0; z-index: 50; background: #16213e; border-top: 1px solid #2a3b5c;"
            "    padding-bottom: env(safe-area-inset-bottom); }"
            "  .ds-mobile-nav button { flex: 1; min-height: 56px; color: #cfd8e6; }"
            "  body { padding-bottom: 64px; }"
            "}"
            "</style>"
        )
        with ui.row().classes("ds-mobile-nav w-full no-wrap items-stretch"):
            for page in cls.MOBILE_NAV:
                ui.button(
                    page["name"],
                    icon=page["icon"],
                    on_click=lambda _, r=page["route"]: ui.navigate.to(r),
                ).props("flat no-caps stack").classes("text-caption")

    @classmethod
    def _build_shell(cls) -> None:
        """Drawer + header, built inside each page so the menu shows everywhere.

        UI beauty pass: ONE visual language — the chrome speaks the same
        warm cream/teal design system as the pages (the old dark-blue
        chrome around light pages read as two apps glued together).
        """
        from app.presentation.dashboard.nicegui_app import design_system as ds

        ds.inject()
        dark = ui.dark_mode(False)

        ui.add_head_html(
            "<style>"
            ".q-drawer { background: #f9f5ec !important; }"
            ".q-drawer .text-h5, .q-drawer .q-btn { color: #3e3a31 !important; }"
            ".q-drawer .q-btn:hover { background: rgba(63,143,133,0.10) !important; }"
            ".q-header { background: #fffdf6 !important; border-bottom: 1px solid #e2d9c8; }"
            ".q-header .text-h6, .q-header .q-btn, .q-header .text-caption "
            "{ color: #3e3a31 !important; }"
            "body { background: #fffdf6; }"
            "</style>"
        )

        with ui.left_drawer(bordered=True).classes("bg-[#f9f5ec]"):
            ui.html(
                '<div style="font-weight:800;font-size:19px;color:#2e6b63;'
                'padding:14px 16px 4px;letter-spacing:-0.3px">robotTrading</div>'
                '<div style="font-size:11.5px;color:#6f6858;padding:0 16px 10px">'
                "a portfolio you can understand</div>"
            )
            ui.separator().classes("q-mb-sm")
            with ui.column().classes("w-full gap-0"):
                for page in PAGES:
                    ui.button(
                        page["name"],
                        icon=page["icon"],
                        on_click=lambda _, r=page["route"]: ui.navigate.to(r),
                    ).props("flat align=left no-caps").classes("w-full text-body1").style(
                        "color:#3e3a31;justify-content:flex-start;min-height:42px"
                    )

        with ui.header().classes("items-center justify-between"):
            ui.label("Backtesting Dashboard").classes("text-h6").style(
                "font-weight:700;color:#3e3a31"
            )
            with ui.row().classes("items-center gap-sm"):
                mode_label = ui.label("Dark").classes("text-caption")
                ui.button(
                    icon="dark_mode",
                    on_click=lambda: _toggle_mode(dark, mode_label),
                ).props("flat round").tooltip("Toggle dark/light mode")

        # UI-5 — mobile bottom nav: the thumb-reachable loop on small
        # screens (drawer stays for desktop). Hidden ≥900px via CSS.
        cls._build_mobile_nav()

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

        @ui.page("/glossary")
        def page_glossary():
            cls._build_shell()
            from app.presentation.dashboard.nicegui_app.pages.glossary import render

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
