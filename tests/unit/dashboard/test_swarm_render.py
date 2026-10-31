"""Headless render tests for the Agent Swarm pipeline-control page (light).

Uses NiceGUI's ``User`` simulation to build the page in a fake client and
assert the key UI blocks exist, a full pipeline run works end-to-end from
the UI, and the step details dialog opens on row click.
"""

from __future__ import annotations

import asyncio

import pytest
from nicegui import ui
from nicegui.testing import User

from app.presentation.dashboard.nicegui_app.pages import swarm
from app.services.agent_swarm import Capa2PipelineExecutor
from app.services.agent_swarm.executor import AGENT_SPECS


@pytest.fixture
def register_page(tmp_path):
    """Register a /swarm-test route rendering the page with a real executor.

    ``profiles_path`` MUST be isolated: with the default (repo-root) store
    the page would auto-apply the owner's real ACTIVE profile and run a
    'max' 20-year window — tests crawled for minutes and failed on the
    coverage gate (31-10).
    """

    @ui.page("/swarm-test")
    def page():
        swarm.render(Capa2PipelineExecutor(), None, str(tmp_path / "no-profiles.json"))


async def test_swarm_page_renders(user: User, register_page):
    client = await user.open("/swarm-test")

    assert client is not None
    await user.should_see("Mission Control")
    await user.should_see("Run my backtest")
    await user.should_see("1 · SET IT UP")
    await user.should_see("2 · WHAT IS HAPPENING")
    await user.should_see("Ready")


async def test_swarm_page_shows_step_track(user: User, register_page):
    """The visual rail replaces the old list: 10 clickable nodes + NOW panel."""
    await user.open("/swarm-test")

    nodes = [el for el in user.find(ui.element).elements if "pnode" in el.classes]
    connectors = [el for el in user.find(ui.element).elements if "t-connector" in el.classes]
    assert len(nodes) == 10
    assert len(connectors) == 9
    await user.should_see("Ready to start")
    await user.should_see("Press Run my backtest")


async def test_swarm_page_config_form_has_plain_helpers(user: User, register_page):
    await user.open("/swarm-test")

    await user.should_see("How much money you want to start with.")
    await user.should_see("What you want to achieve with this investment.")
    await user.should_see("Fine-tune — everything else is pre-set for you")


async def test_swarm_page_has_period_and_tax_inputs(user: User, register_page):
    """The investment period, investor age and tax province are configurable.

    The period IS the investment horizon (money stays invested for the whole
    window), so the old separate "Time frame (months)" field is gone.
    """
    await user.open("/swarm-test")

    await user.should_see("Investment period")
    # Default (user 2026-10-27): 10 years — the configuration that passes
    await user.should_see("Last 10 years")
    await user.should_see("Your age")
    await user.should_see("Province (tax residence)")
    await user.should_not_see("Time frame (months)")


async def test_swarm_page_has_no_docs_band(user: User, register_page):
    """The HELP & DOCS band was removed from the run page (owner 31-10:
    useless clutter under the mission); docs stay in the nav's
    Documentation entry."""
    await user.open("/swarm-test")

    await user.should_not_see("HELP & DOCS")
    await user.should_not_see("All documentation")
    doc_links: list[ui.link] = []
    try:
        doc_links = [
            link
            for link in user.find(ui.link).elements
            if (link.props.get("href") or "").startswith("/docs")
        ]
    except AssertionError:
        pass  # no links at all on the page — even better
    assert doc_links == []


async def test_swarm_pipeline_runs_end_to_end_from_ui(user: User, register_page):
    """Click Run in the simulated UI; the real pipeline must complete."""
    await user.open("/swarm-test")
    user.find(marker="run_pipeline").click()

    # The real T1.1→T10.1 chain includes a full backtest, the mandatory
    # walk-forward gate AND the in-backtest optimization (up to 6 extra
    # backtests — and a sequential fallback if the process pool breaks),
    # so the budget must cover minutes, not seconds.
    for _ in range(720):
        await asyncio.sleep(0.25)
        try:
            await user.should_see("Completed")
            break
        except AssertionError:
            continue
    else:
        pytest.fail("pipeline did not complete within 180s in the simulated UI")

    await user.should_see("Step 10 of 10")
    await user.should_see("3 · RESULT")
    await user.should_see("PORTFOLIO")
    await user.should_see("HOW YOUR CAPITAL IS SPREAD")


async def test_agent_step_click_opens_details_dialog(user: User, register_page):
    """Clicking a step opens the dialog with input/output sections."""
    await user.open("/swarm-test")

    user.find(marker="step_node_t11").trigger("click")

    await user.should_see("Step T1.1 Input Processor")
    await user.should_see("INPUT")
    await user.should_see("OUTPUT")


async def test_step_dialogs_show_visual_outputs(user: User, register_page):
    """After a run, each step dialog renders charts/tiles, not just JSON."""
    await user.open("/swarm-test")
    user.find(marker="run_pipeline").click()
    for _ in range(240):
        await asyncio.sleep(0.25)
        try:
            await user.should_see("Completed")
            break
        except AssertionError:
            continue

    user.find(marker="step_node_t41").trigger("click")
    await user.should_see("Win rate %")
    await user.should_see("Profit factor")

    user.find(marker="step_node_t71").trigger("click")
    await user.should_see("ALLOCATION")


async def test_accessibility_basics(user: User, register_page):
    """Keyboard operability, aria labels and the 1-click replay exist."""
    await user.open("/swarm-test")

    node = next(iter(user.find(marker="step_node_t11").elements))
    assert node.props.get("tabindex") is not None
    assert node.props.get("role") == "button"
    assert "Check your inputs" in str(node.props.get("aria-label", ""))

    # keyboard: Enter on a node opens the details dialog
    user.find(marker="step_node_t11").trigger("keyup.enter")
    await user.should_see("Step T1.1 Input Processor")

    await user.should_see("Replay last")

    desk = next(iter(user.find(marker="office_desk_t41").elements))
    assert "Simulate the strategy" in str(desk.props.get("aria-label", ""))


async def test_office_scene_has_ten_clickable_desks(user: User, register_page):
    """The animated office floor exposes one clickable hit-area per worker."""
    await user.open("/swarm-test")

    desks = [user.find(marker=f"office_desk_{spec.agent_id}").elements for spec in AGENT_SPECS]
    assert all(len(elements) == 1 for elements in desks)

    user.find(marker="office_desk_t41").click()
    await user.should_see("Step T4.1 Backtest Orchestrator")
