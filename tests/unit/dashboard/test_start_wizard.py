"""UI-1 — the /start wizard: it SAVES the investor profile (owner 31-10).

The wizard no longer builds or validates portfolios (that moved to
Mission Control); its one job is persisting the five answers so /swarm
can use them as the default.
"""

from __future__ import annotations

import json

from app.presentation.dashboard.nicegui_app.pages.start import GOAL_OPTIONS, HORIZON_WINDOWS


class TestHorizonWindows:
    def test_every_horizon_has_window_and_months(self):
        for label, (period, months) in HORIZON_WINDOWS.items():
            assert period in ("5y", "10y", "max"), label
            assert months >= 60, label


class TestGoals:
    def test_goals_map_to_pipeline_values(self):
        assert set(GOAL_OPTIONS.values()) <= {
            "MAXIMIZAR_DIVIDENDOS",
            "CAPITAL_PRESERVATION",
            "BALANCED_GROWTH",
        }


class TestProfileSave:
    """The 5 answers must land in investor_profile.json — before 31-10
    they lived only in the page and vanished on refresh."""

    async def test_save_writes_profile_and_shows_summary(self, user, tmp_path):
        from nicegui import ui

        from app.presentation.dashboard.nicegui_app.pages import start

        path = tmp_path / "investor_profile.json"

        @ui.page("/start-save-test")
        def page():
            start.render(str(path))

        await user.open("/start-save-test")
        user.find(marker="opt_age_Under35").click()
        user.find(marker="opt_horizon_510years").click()
        user.find(marker="opt_risk_Balanced").click()
        user.find(marker="opt_goal_Growitovertime").click()
        user.find(marker="save_profile").click()
        await user.should_see("Your saved investor profile")

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["investor_age"] == 30
        assert data["investment_horizon"] == 120  # '5–10 years'
        assert data["risk_tolerance"] == "MEDIO"
        assert data["tax_province"] == "Madrid"
        assert data["objetivo_inversion"] == "BALANCED_GROWTH"

    async def test_incomplete_answers_write_nothing(self, user, tmp_path):
        from nicegui import ui

        from app.presentation.dashboard.nicegui_app.pages import start

        path = tmp_path / "investor_profile.json"

        @ui.page("/start-incomplete-test")
        def page():
            start.render(str(path))

        await user.open("/start-incomplete-test")
        user.find(marker="save_profile").click()
        await user.should_see("Answer the four key questions")
        assert not path.exists()

    async def test_saved_profile_is_preselected_and_resavable(self, user, tmp_path):
        """Reopening /start shows the saved profile and one click re-saves
        it — the user never answers the same question twice."""
        from nicegui import ui

        from app.presentation.dashboard.nicegui_app.pages import start
        from app.services.agent_swarm.investor_profile import InvestorProfile, save_investor_profile

        path = tmp_path / "investor_profile.json"
        save_investor_profile(
            InvestorProfile(
                investor_age=42,
                investment_horizon=240,
                risk_tolerance="ALTO",
                tax_province="Bizkaia",
                objetivo_inversion="MAXIMIZAR_DIVIDENDOS",
            ),
            path,
        )

        @ui.page("/start-preselect-test")
        def page():
            start.render(str(path))

        await user.open("/start-preselect-test")
        await user.should_see("Profile loaded")
        await user.should_see("Your saved investor profile")

        user.find(marker="save_profile").click()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["investor_age"] == 42
        assert data["investment_horizon"] == 240
        assert data["risk_tolerance"] == "ALTO"
        assert data["tax_province"] == "Bizkaia"
        assert data["objetivo_inversion"] == "MAXIMIZAR_DIVIDENDOS"
