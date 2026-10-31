"""UI-1 — the /start wizard behind NAMED investor profiles (owner 31-10).

The page manages profiles: create with a name, list, load/edit, delete.
Mission Control (/swarm) lists the same profiles and applies the chosen
one — covered by test_swarm_profile_picker.py.
"""

from __future__ import annotations

import json

from app.presentation.dashboard.nicegui_app.pages.start import GOAL_OPTIONS, HORIZON_WINDOWS
from app.services.agent_swarm.investor_profile import InvestorProfile, save_profile


class TestHorizonWindows:
    def test_every_horizon_has_window_and_months(self):
        for label, (period, months) in HORIZON_WINDOWS.items():
            assert period in ("5y", "10y", "max"), label
            assert months >= 60, label


class TestGoals:
    def test_wizard_offers_every_mission_control_objective(self):
        """The wizard can never offer LESS than /swarm — 'faltan opciones
        como el acumulado' (31-10) was exactly this drift."""
        from app.presentation.dashboard.nicegui_app.pages.swarm import OBJECTIVES

        assert set(GOAL_OPTIONS) == set(OBJECTIVES)

    def test_owner_decree_default_goal_comes_first(self):
        assert next(iter(GOAL_OPTIONS)) == "ACUMULAR"


def _open_wizard(user, path, route: str):  # noqa: ANN001 — nicegui test types
    from nicegui import ui

    from app.presentation.dashboard.nicegui_app.pages import start

    @ui.page(route)
    def page():
        start.render(str(path))


class TestProfileSave:
    """The 5 answers must land in the named-profiles store — before 31-10
    they lived only in the page and vanished on refresh."""

    async def test_save_named_profile_and_set_it_active(self, user, tmp_path):
        path = tmp_path / "investor_profiles.json"
        _open_wizard(user, path, "/start-save-test")

        await user.open("/start-save-test")
        user.find(marker="opt_age_Under35").click()
        user.find(marker="opt_horizon_510years").click()
        user.find(marker="opt_risk_Medium").click()
        user.find(marker="opt_goal_Growcapital").click()
        user.find(marker="profile_name").type("Growth plan")
        user.find(marker="save_profile").click()
        await user.should_see("Profile “Growth plan” saved.")

        data = json.loads(path.read_text(encoding="utf-8"))
        profiles = {p["name"]: p for p in data["profiles"]}
        assert profiles["Growth plan"]["investor_age"] == 30
        assert profiles["Growth plan"]["investment_horizon"] == 120  # '5–10 years'
        assert profiles["Growth plan"]["risk_tolerance"] == "MEDIO"
        assert profiles["Growth plan"]["tax_province"] == "Madrid"
        assert profiles["Growth plan"]["objetivo_inversion"] == "MAXIMIZAR_CAPITAL"
        assert data["active"] == "Growth plan"  # newest intent wins in /swarm

    async def test_incomplete_answers_write_nothing(self, user, tmp_path):
        path = tmp_path / "investor_profiles.json"
        _open_wizard(user, path, "/start-incomplete-test")

        await user.open("/start-incomplete-test")
        user.find(marker="save_profile").click()
        await user.should_see("Answer the four key questions")
        assert not path.exists()

    async def test_name_is_required(self, user, tmp_path):
        path = tmp_path / "investor_profiles.json"
        _open_wizard(user, path, "/start-noname-test")

        await user.open("/start-noname-test")
        user.find(marker="opt_age_Under35").click()
        user.find(marker="opt_horizon_510years").click()
        user.find(marker="opt_risk_Medium").click()
        user.find(marker="opt_goal_Growcapital").click()
        user.find(marker="save_profile").click()
        await user.should_see("Give the profile a name")
        assert not path.exists()


class TestProfileManagement:
    async def test_saved_profiles_are_listed_and_loadable(self, user, tmp_path):
        path = tmp_path / "investor_profiles.json"
        save_profile(
            InvestorProfile(
                name="Retirement",
                investor_age=57,
                investment_horizon=240,
                risk_tolerance="BAJO",
                tax_province="Bizkaia",
                objetivo_inversion="MAXIMIZAR_DIVIDENDOS",
            ),
            path,
        )
        _open_wizard(user, path, "/start-list-test")

        await user.open("/start-list-test")
        await user.should_see("Retirement")
        await user.should_see("Maximise dividends")  # the summary line

        user.find(marker="load_Retirement").click()
        await user.should_see("Editing “Retirement” — all questions pre-filled.")

    async def test_age_saved_under_old_representative_still_loads(self, user, tmp_path):
        """'la edad no se guarda' (31-10): a profile stored as 42 (the old
        '35–50' representative, pre-PERFIL-45) matched NO button after the
        band moved to 45 — the age looked unsaved. Loading must snap to the
        band and saving must persist the band's current representative."""
        from app.presentation.dashboard.nicegui_app.pages.start import _band_value_for_age

        assert _band_value_for_age(42) == 45
        assert _band_value_for_age(34) == 30
        assert _band_value_for_age(66) == 70

        path = tmp_path / "investor_profiles.json"
        save_profile(
            InvestorProfile(
                name="Legacy 42",
                investor_age=42,
                investment_horizon=120,
                risk_tolerance="MEDIO",
                objetivo_inversion="ACUMULAR",
            ),
            path,
        )
        _open_wizard(user, path, "/start-age42-test")

        await user.open("/start-age42-test")
        user.find(marker="load_Legacy 42").click()
        await user.should_see("Editing “Legacy 42” — all questions pre-filled.")

        user.find(marker="save_profile").click()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["profiles"][0]["investor_age"] == 45  # band representative

    async def test_delete_asks_first_then_removes(self, user, tmp_path):
        path = tmp_path / "investor_profiles.json"
        save_profile(
            InvestorProfile(
                name="Old plan",
                investor_age=30,
                investment_horizon=60,
                risk_tolerance="ALTO",
                objetivo_inversion="ACUMULAR",
            ),
            path,
        )
        _open_wizard(user, path, "/start-delete-test")

        await user.open("/start-delete-test")
        user.find(marker="delete_Old plan").click()
        await user.should_see("Delete profile “Old plan”?")
        user.find(marker="confirm_delete").click()
        await user.should_see("Profile “Old plan” deleted.")
        assert store_names(path) == []


def store_names(path) -> list[str]:  # noqa: ANN001
    data = json.loads(path.read_text(encoding="utf-8"))
    return [p["name"] for p in data["profiles"]]
