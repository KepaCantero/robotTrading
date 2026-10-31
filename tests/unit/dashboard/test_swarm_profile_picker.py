"""Mission Control's investor-profile picker (owner 31-10).

Saved profiles (created in /start) must be selectable here, and the
ACTIVE one is applied as the default configuration on page load.
"""

from __future__ import annotations

import pytest
from nicegui import ui
from nicegui.testing import User

from app.presentation.dashboard.nicegui_app.pages import swarm
from app.services.agent_swarm import Capa2PipelineExecutor
from app.services.agent_swarm.investor_profile import InvestorProfile, save_profile, set_active


@pytest.fixture
def profile_store(tmp_path):
    return str(tmp_path / "investor_profiles.json")


def _register(route: str, store_path: str) -> None:
    @ui.page(route)
    def page():
        swarm.render(Capa2PipelineExecutor(), None, store_path)


async def test_active_profile_is_applied_on_load(user: User, profile_store):
    save_profile(
        InvestorProfile(
            name="Dividends",
            investor_age=57,
            investment_horizon=240,
            risk_tolerance="BAJO",
            tax_province="Bizkaia",
            objetivo_inversion="MAXIMIZAR_DIVIDENDOS",
        ),
        profile_store,
    )
    set_active("Dividends", profile_store)
    _register("/swarm-picker-active", profile_store)

    await user.open("/swarm-picker-active")
    await user.should_see("Dividends")  # the picker carries the profile
    await user.should_see("Maximise dividends")  # its goal is now selected


async def test_without_active_profile_the_decree_defaults_stay(user: User, profile_store):
    save_profile(
        InvestorProfile(
            name="Unused",
            investor_age=30,
            investment_horizon=60,
            risk_tolerance="ALTO",
            objetivo_inversion="CAPITAL_PRESERVATION",
        ),
        profile_store,
    )
    _register("/swarm-picker-inactive", profile_store)

    await user.open("/swarm-picker-inactive")
    await user.should_see("None — manual settings")
    await user.should_see("Accumulate — total return (UCITS ACC)")  # default goal intact


def test_period_for_horizon_maps_wizard_windows():
    assert swarm.period_for_horizon(60) == "5y"
    assert swarm.period_for_horizon(120) == "10y"
    assert swarm.period_for_horizon(240) == "max"
    assert swarm.period_for_horizon(999) == "max"
