"""History & Compare: readable run selectors and a working comparison.

The compare selects received options as a list of {label, value} dicts,
which Quasar rendered as '[object Object]' for every run (31-10) — and
the page never injected the Mission Control skin it borrows classes
from ('la visualización es penosa'). Options are a value→label dict now
and the two most recent runs arrive preselected.
"""

from __future__ import annotations

import asyncio
import json

from nicegui import ui
from nicegui.testing import User

from app.presentation.dashboard.nicegui_app.pages import history_compare
from app.services.agent_swarm.store import SwarmRunStore


def _results(verdict: str, total: float) -> dict:
    return {
        "backtest_result": {
            "metrics": {"total_return_pct": total, "max_drawdown_pct": -20.0, "sharpe": 0.5},
            "verdict": {"overall": verdict},
            "strategy_name": "static_ew",
            "symbols": ["VWCE", "AGGH.AS"],
        }
    }


async def _seed(store: SwarmRunStore) -> None:
    await store.initialize()
    for i, (verdict, total) in enumerate((("APPROVED", 112.0), ("APPROVED", 148.0))):
        run_id = f"run_{i}"
        await store.create_run(
            run_id,
            {"objetivo_inversion": "ACUMULAR", "strategy": "static_ew"},
            started_at=f"2026-10-31T11:2{i}:00",
        )
        await store.finish_run(
            run_id,
            "completed",
            finished_at=f"2026-10-31T11:2{i}:09",
            results=json.loads(json.dumps(_results(verdict, total))),
        )


async def _open(user: User, store: SwarmRunStore, route: str) -> None:
    await _seed(store)

    @ui.page(route)
    def page():
        history_compare.render(store)

    await user.open(route)
    await asyncio.sleep(0.5)  # let the table/selector loaders (timers) fire


class TestCompareSelectors:
    async def test_options_are_plain_dict_labels(self, user: User, tmp_path):
        """'[object Object]' came from list-of-dicts options; the guard is
        the options SHAPE: a value→label dict of plain strings."""
        store = SwarmRunStore(str(tmp_path / "swarm_runs.db"))
        try:
            await _open(user, store, "/history-labels-test")
            await user.should_see("Run A")

            select_a = next(iter(user.find(marker="compare_run_a").elements))
            assert isinstance(select_a.options, dict) and select_a.options
            assert all(isinstance(label, str) for label in select_a.options.values())
            assert any("ACUMULAR" in label for label in select_a.options.values())

            table = next(iter(user.find(ui.table).elements))
            assert any("ACUMULAR" in str(row.get("goal", "")) for row in table.rows)
        finally:
            await store.close()

    async def test_two_latest_runs_preselected_and_comparable(self, user: User, tmp_path):
        store = SwarmRunStore(str(tmp_path / "swarm_runs.db"))
        try:
            await _open(user, store, "/history-compare-test")

            a = next(iter(user.find(marker="compare_run_a").elements))
            assert a.value  # a run is preselected

            user.find(marker="compare_button").click()
            await user.should_see("Comparison Results")

            tables = list(user.find(ui.table).elements)
            compare_rows = [row for t in tables for row in t.rows if "metric" in row]
            assert compare_rows, "comparison table has no rows"
            assert any(row["metric"] == "Return %" for row in compare_rows)
        finally:
            await store.close()
