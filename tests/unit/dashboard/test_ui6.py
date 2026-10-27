"""UI-6 — digest honesty + glossary completeness."""

from __future__ import annotations

from app.presentation.dashboard.nicegui_app.components.weekly_digest import weekly_digest
from app.presentation.dashboard.nicegui_app.design_system import GLOSSARY


class TestDigest:
    def test_the_most_common_digest_is_no_action(self):
        d = weekly_digest(
            last_run_status="completed",
            last_run_return_pct="8.3",
            drift_status="skipped",
            next_rebalance_days=41,
        )
        assert "none" in d["action"].lower()
        assert "in 41 days" in d["when"]

    def test_proactive_drift_tells_to_preview_with_tax(self):
        d = weekly_digest(
            last_run_status="completed",
            last_run_return_pct=None,
            drift_status="proactive",
        )
        assert "preview" in d["action"].lower()

    def test_failed_run_is_said_aloud(self):
        d = weekly_digest(last_run_status="failed", drift_status=None)
        assert "didn't complete" in d["headline"]

    def test_no_runs_points_to_start(self):
        d = weekly_digest(last_run_status=None, drift_status=None)
        assert "/start" in d["headline"]


class TestGlossary:
    def test_every_entry_is_one_breath(self):
        for term_name, plain in GLOSSARY.items():
            assert 10 < len(plain) < 140, term_name  # plain, not a lecture

    def test_the_core_journey_words_exist(self):
        for needed in (
            "Drawdown",
            "Rebalance",
            "Paper trading",
            "Fees",
            "Walk-forward",
            "Tax preview",
        ):
            assert needed in GLOSSARY
