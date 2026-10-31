"""A crashed run must surface in the theater — no eternal 'Running… Step 1'.

The coverage gate raises BEFORE any run row exists (e.g. ACUMULAR's equity
seat cannot cover the 'max' 20-year window). The page used to fire one
fleeting toast from the background task — where even ui.notify raises
RuntimeError (no UI slot), killing the task with the button disabled and
the theater stuck on 'running' ('le doy a backtest y no termina', 31-10).
"""

from __future__ import annotations

import asyncio

import pytest
from nicegui import ui
from nicegui.testing import User

from app.presentation.dashboard.nicegui_app.pages import swarm


class CrashingExecutor:
    """Stands in for Capa2PipelineExecutor: run() raises like the gate."""

    def get_run(self, run_id):  # noqa: ANN001, ANN202 - page calls it in poll()
        return None

    async def run(self, request, run_id=None, on_event=None):  # noqa: ANN001, ANN202
        raise ValueError("Auto universe: ACUMULAR no tiene un fondo viable que cubra la ventana")


@pytest.fixture
def crashing_page(tmp_path):
    @ui.page("/swarm-crash-test")
    def page():
        swarm.render(CrashingExecutor(), None, str(tmp_path / "no-profiles.json"))  # type: ignore[arg-type]


async def test_crashed_run_shows_failure_theater_and_reenables(user: User, crashing_page):
    await user.open("/swarm-crash-test")
    await user.should_see("Run my backtest")

    user.find(marker="run_pipeline").click()

    # the failure renders from poll()'s 0.25s timer — give it ticks
    # (same waiting idiom as the end-to-end test in test_swarm_render.py)
    for _ in range(20):
        await asyncio.sleep(0.25)
        try:
            await user.should_see("The run failed")
            break
        except AssertionError:
            continue
    else:
        pytest.fail("theater never showed the failure")

    await user.should_see("no tiene un fondo viable")  # the gate's own message

    button = next(iter(user.find(marker="run_pipeline").elements))
    assert not button.props.get("disabled")
