"""UI-1 — the /start wizard's logic: horizon→window and preset reuse."""

from __future__ import annotations

from app.presentation.dashboard.nicegui_app.pages.start import GOAL_OPTIONS, HORIZON_WINDOWS
from app.presentation.dashboard.nicegui_app.pages.swarm import preset_for_goal


class TestHorizonWindows:
    def test_every_horizon_has_window_and_months(self):
        for label, (period, months) in HORIZON_WINDOWS.items():
            assert period in ("5y", "10y", "max"), label
            assert months >= 60, label

    def test_long_horizon_uses_deep_dividend_universe(self):
        """10+ years + dividends → the deep-history universe (the preset
        rule the wizard reuses instead of its own logic)."""
        strategy, universe = preset_for_goal("MAXIMIZAR_DIVIDENDOS", 240)
        assert strategy == "dividend_tracking"
        assert "SDY" in universe  # deep corpus


class TestGoals:
    def test_goals_map_to_pipeline_values(self):
        assert set(GOAL_OPTIONS.values()) <= {
            "MAXIMIZAR_DIVIDENDOS",
            "CAPITAL_PRESERVATION",
            "BALANCED_GROWTH",
        }


class TestWizardRunsPersist:
    """The wizard must run on the SHARED executor (with the store) — a
    throwaway executor meant every /start run vanished from history
    ("las ejecuciones no se guardan")."""

    async def test_validate_uses_injected_executor(self, user):
        from types import SimpleNamespace

        from nicegui import ui

        from app.presentation.dashboard.nicegui_app.pages import start

        class SpyExecutor:
            def __init__(self) -> None:
                self.calls: list = []

            async def run(self, request, run_id=None, on_event=None):
                self.calls.append(request)
                return SimpleNamespace(
                    status="completed",
                    agents={
                        "t41": SimpleNamespace(
                            output_payload={
                                "backtest_result": {
                                    "metrics": {
                                        "total_return_pct": 5.0,
                                        "max_drawdown_pct": -2.0,
                                    },
                                    "walk_forward_passed": True,
                                }
                            }
                        )
                    },
                )

        spy = SpyExecutor()

        @ui.page("/start-wiring-test")
        def page():
            start.render(spy, None)  # type: ignore[arg-type]

        await user.open("/start-wiring-test")
        user.find(marker="opt_age_Under35").click()
        user.find(marker="opt_horizon_35years").click()
        user.find(marker="opt_risk_Balanced").click()
        user.find(marker="goal_MAXIMIZAR_DIVIDENDOS").click()
        user.find(marker="propose").click()
        await user.should_see("Validate it")
        user.find(marker="validate_it").click()
        await user.should_see("The honest numbers")

        assert len(spy.calls) == 1
        req = spy.calls[0]
        assert req.objetivo_inversion == "MAXIMIZAR_DIVIDENDOS"
        assert req.risk_tolerance == "MEDIO"
        assert req.investor_age == 30
        assert req.tax_province == "Madrid"
