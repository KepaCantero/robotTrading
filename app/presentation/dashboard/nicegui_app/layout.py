"""Application shell layout for the NiceGUI backtesting dashboard.

Provides the main layout structure: left drawer navigation, top header
with dark mode toggle, and a main content area with page routing.
"""

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import PAGES


class AppShell:
    """Main application shell with drawer, header, and routed content area."""

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
            ui.button(icon="dark_mode", on_click=lambda: dark.toggle()).props("flat round").tooltip(
                "Toggle dark/light mode"
            )

        # ── Page Routes ────────────────────────────────────────────────────
        @ui.page("/")
        def page_backtest_runner():
            cls._page_wrapper("Backtest Runner")

        @ui.page("/results")
        def page_results():
            cls._page_wrapper("Results")

        @ui.page("/history")
        def page_history():
            cls._page_wrapper("History & Compare")

        @ui.page("/config")
        def page_config():
            cls._page_wrapper("Config Viewer")

        @ui.page("/profitability")
        def page_profitability():
            cls._page_wrapper("Profitability")

    @staticmethod
    def _page_wrapper(title: str) -> None:
        """Wrap page content with standard padding and a title."""
        with ui.column().classes("w-full q-pa-lg"):
            ui.label(title).classes("text-h4 q-mb-md")
            ui.label(f"Welcome to {title}. Content coming soon.").classes("text-grey")
