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
