"""UI-3 — Mission Control states: derived from evidence, never faked."""

from __future__ import annotations

from app.presentation.dashboard.nicegui_app.components.mission_control import STAGES, loop_states


def _stages(states):
    return {s["stage"]: s["state"] for s in states}


def test_empty_store_design_todo():
    s = _stages(loop_states([]))
    assert s["Design"] == "todo"
    assert s["Backtest"] == "todo"
    assert s["Optimize"] == "todo"


def test_completed_run_unlocks_the_chain():
    s = _stages(loop_states([{"status": "completed"}]))
    assert s["Design"] == "done"
    assert s["Backtest"] == "done"
    assert s["Optimize"] == "ready"


def test_failed_run_counts_as_design_only():
    """A crashed run built a profile but validated nothing — honest."""
    s = _stages(loop_states([{"status": "failed"}]))
    assert s["Design"] == "done"
    assert s["Backtest"] == "todo"


def test_paper_is_active_observation_and_live_is_locked():
    s = _stages(loop_states([{"status": "completed"}]))
    assert s["Paper"] == "active"  # §5.2 observation done, orders next
    assert s["Live"] == "blocked"  # real money off by decree


def test_every_stage_has_a_plain_line_and_a_route():
    states = loop_states([])
    for (name, route, _icon), st in zip(STAGES, states):
        assert st["stage"] == name
        assert st["line"], name  # no empty narration
    routes = [r for _, r, _ in STAGES]
    assert routes[-1] == "/trust"  # UI-4: the locked door leads to its explanation
    assert all(r for r in routes)
