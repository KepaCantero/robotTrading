"""Run the NiceGUI dashboard: python -m app.presentation.dashboard.nicegui_app.

Also available via  make dashboard  (which rebuilds the docs site first).
The dashboard serves the documentation at http://localhost:<port>/docs/.

NiceGUI 3.x requires the whole app (layout + page routes) to be built
inside a root function passed to ``ui.run``; building UI at module scope
would activate single-page script mode and reject ``@ui.page`` routes.
"""

from __future__ import annotations

import os

from nicegui import ui

from app.presentation.dashboard.nicegui_app.app import create_app


def root() -> None:
    """Build layout, register all dashboard pages and render home."""
    create_app()
    from app.presentation.dashboard.nicegui_app.layout import AppShell

    AppShell.build_home()


ui.run(
    root=root,
    title="AlgoTrading Dashboard",
    port=int(os.environ.get("DASHBOARD_PORT", "8503")),
    reload=False,
    show=False,
)
