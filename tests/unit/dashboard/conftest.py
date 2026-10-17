"""NiceGUI simulated-user fixture for dashboard render tests.

Builds the ``user`` fixture on top of NiceGUI's public testing helpers
(``nicegui.testing.general``), without importing the full
``nicegui.testing.plugin`` (whose screen part requires selenium, not
installed in this project's dev environment).
"""

from __future__ import annotations

from typing import AsyncGenerator

import httpx
import pytest
from nicegui.testing.general_fixtures import nicegui_reset_globals  # noqa: F401
from nicegui.testing.user import User


@pytest.fixture
async def user(nicegui_reset_globals) -> AsyncGenerator[User, None]:
    """Create a simulated NiceGUI user able to open pages headlessly."""
    from nicegui import core
    from nicegui.testing.general import prepare_simulation

    prepare_simulation()
    async with core.app.router.lifespan_context(core.app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(core.app), base_url="http://test"
        ) as client:
            yield User(client)
    # NOTE: unlike the upstream plugin, we do not fail the test on ERROR-level
    # logs — the CAPA 2 components log genuine ERRORs while still succeeding
    # (e.g. ValidationEngine's degraded sub-validators).
