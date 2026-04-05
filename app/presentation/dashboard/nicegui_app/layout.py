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

    @classmethod
    def configure(
        cls,
        store: BacktestResultStore,
        runner: BacktestRunner,
        profitability: ProfitabilityEngine,
    ) -> None:
        """Inject shared service instances before calling setup()."""
        cls._store = store
        cls._runner = runner
        cls._profitability = profitability

    @classmethod
    def setup(cls) -> None:
        """Set up the full application shell with all pages."""
        dark = ui.dark_mode(True)

        # ── Left Drawer ────────────────────────────────────────────────────
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

        # ── Header ─────────────────────────────────────────────────────────
        with ui.header().classes("items-center justify-between bg-[#0f3460]"):
            ui.label("Backtesting Dashboard").classes("text-h6")
            with ui.row().classes("items-center gap-sm"):
                mode_label = ui.label("Dark").classes("text-caption")
                ui.button(
                    icon="dark_mode",
                    on_click=lambda: _toggle_mode(dark, mode_label),
                ).props("flat round").tooltip("Toggle dark/light mode")

        # ── Page Routes ────────────────────────────────────────────────────
        @ui.page("/")
        def page_backtest_runner():
            from app.presentation.dashboard.nicegui_app.pages.backtest_runner import render

            render(cls._store, cls._runner, cls._profitability)

        @ui.page("/results")
        def page_results():
            from app.presentation.dashboard.nicegui_app.pages.backtest_results import render

            render(cls._store, cls._profitability)

        @ui.page("/history")
        def page_history():
            from app.presentation.dashboard.nicegui_app.pages.history_compare import render

            render(cls._store, cls._profitability)

        @ui.page("/config")
        def page_config():
            from app.presentation.dashboard.nicegui_app.pages.config_viewer import render

            render()

        @ui.page("/profitability")
        def page_profitability():
            from app.presentation.dashboard.nicegui_app.pages.profitability import render

            render(cls._store, cls._profitability)
