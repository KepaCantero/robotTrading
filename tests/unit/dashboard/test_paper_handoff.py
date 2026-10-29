"""Mission Control → /portfolio hand-off (user report 2026-10-27).

Creating a named paper portfolio only WRITES the target; the user saw an
empty account and no copy of his portfolio. The hand-off must land him on
/portfolio with his portfolio SELECTED and the first-deployment preview
already open — one manual Confirm invests the cash (supervision rule).
"""

from __future__ import annotations

import asyncio
from decimal import Decimal as D

import pytest
from nicegui import ui
from nicegui.testing import User
from starlette.requests import Request

from app.presentation.dashboard.nicegui_app.pages import portfolio as page_mod
from app.services.portfolio_management.models import Holding, ProfileAnswers
from app.services.portfolio_management.named_portfolios import (
    create_portfolio,
    open_store,
    prepare_store,
)
from app.services.portfolio_management.winner_adoption import build_target

SLUG = "max-dividends-10y"


@pytest.fixture
def named_env(tmp_path, monkeypatch):
    """Isolated portfolio registry + per-slug engines, cached page state reset."""
    monkeypatch.setattr("app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path)
    page_mod._ACTIVE_SLUG = "main"
    page_mod._stores.clear()
    page_mod._brokers.clear()
    yield
    page_mod._ACTIVE_SLUG = "main"
    page_mod._stores.clear()
    page_mod._brokers.clear()


@pytest.fixture
async def made_portfolio(named_env):
    """A portfolio exactly as Mission Control creates it: meta, store, target."""
    create_portfolio(
        "Max dividends 10y",
        source_run_id="swarm_test",
        strategy_name="static_ew",
        decision_status="CONDITIONAL",
        initial_cash=D("100000"),
    )
    engine, store = open_store(SLUG)
    await prepare_store(engine)
    winner = {
        "run_id": "swarm_test",
        "strategy_name": "static_ew",
        "decision_status": "CONDITIONAL",
        "holdings": [
            Holding(symbol="SCHD", weight=D("0.40"), rationale="Core dividends"),
            Holding(symbol="VT", weight=D("0.60"), rationale="Whole world"),
        ],
    }
    target = build_target(
        ProfileAnswers(
            objective="MAXIMIZAR_DIVIDENDOS",
            risk_level="aggressive",
            horizon_months=120,
        ),
        winner,
    )
    await store.save_target(target)
    return SLUG


@pytest.fixture
def register_page():
    state: dict = {}

    @ui.page("/portfolio-handoff")
    def page():
        page_mod.render(
            None, None, focus_slug=state.get("slug", ""), autodeploy=state.get("autodeploy", False)
        )

    return state


async def _settle(user: User) -> None:
    """Let the 0.1s first-render timer (and the auto-opened preview) run."""
    for _ in range(20):
        await asyncio.sleep(0.1)


async def test_handoff_selects_the_new_portfolio(user: User, register_page, made_portfolio):
    register_page.update(slug=SLUG, autodeploy=False)
    await user.open("/portfolio-handoff")
    await _settle(user)

    await user.should_see("3 · On track?")
    # the selector landed on the created portfolio, not "main"
    select = next(iter(user.find(marker="portfolio_select").elements))
    assert select.value == SLUG
    # the empty state says what to do instead of leaving a dead end
    await user.should_see("Press “Apply to paper account” to deploy")


async def test_handoff_opens_first_deployment_preview(user: User, register_page, made_portfolio):
    register_page.update(slug=SLUG, autodeploy=True)
    await user.open("/portfolio-handoff")
    await _settle(user)

    # the preview opened by itself: the buy plan is on screen
    await user.should_see("Apply to your paper account")
    await user.should_see("Confirm and send orders")
    await user.should_see("Not now")
    # table cell text isn't matched by should_see — inspect the rows directly
    rows = [row for table in user.find(ui.table).elements for row in (table.rows or [])]
    buys = {row["symbol"] for row in rows if row.get("side") == "BUY"}
    assert {"SCHD", "VT"} <= buys


async def test_no_autodeploy_on_plain_visit(user: User, register_page, made_portfolio):
    """Without deploy=1 the preview must NOT pop — the page stays calm.
    (A plain visit without ?portfolio= falls back to "main", whose store is
    empty under the isolated registry — so visit WITH the portfolio selected
    but no deploy flag; same calm-page contract.)"""
    register_page.update(slug=SLUG, autodeploy=False)
    await user.open("/portfolio-handoff")
    await _settle(user)

    await user.should_see("3 · On track?")
    await user.should_see("Cash not invested yet")
    with pytest.raises(AssertionError):
        await user.should_see("Apply to your paper account")


async def test_request_query_params_reach_the_page_handler(user: User):
    """The /portfolio route relies on NiceGUI injecting ``request: Request``
    into the page handler (layout.py reads ?portfolio=&deploy=). This pins
    that mechanism at the routing level."""
    seen: dict = {}

    @ui.page("/handoff-route")
    def page(request: Request):
        seen["query"] = dict(request.query_params)

    await user.open("/handoff-route?portfolio=max-dividends-10y&deploy=1")
    assert seen["query"] == {"portfolio": "max-dividends-10y", "deploy": "1"}
