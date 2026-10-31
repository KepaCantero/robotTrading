"""Profitability page - verdicts, trends, and summary statistics.

Aggregated profitability analysis across ALL REAL runs (swarm_runs.db —
the same store Mission Control persists to). Until 31-10 this page read
the orphaned backtest_results.db and showed two frozen rows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.components.metric_cards import skeleton_card
from app.presentation.dashboard.nicegui_app.pages.swarm import extract_result_metrics
from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.services.agent_swarm.store import SwarmRunStore

logger = logging.getLogger(__name__)

_VERDICT_COLORS = {
    "APPROVED": COLORS["pass_"],
    "CONDITIONAL": COLORS["inconclusive"],
    "REJECTED": COLORS["fail"],
    "FAILED": COLORS["fail"],
    "RUNNING": COLORS["inconclusive"],
}


def _verdict_color(verdict: str) -> str:
    return _VERDICT_COLORS.get(verdict, COLORS["inconclusive"])


def _build_summary_cards(runs: list[dict[str, Any]]) -> None:
    """Render summary statistics cards over real run verdicts."""
    verdicts = [str(r.get("verdict") or "—") for r in runs]
    total = len(runs)
    approved = verdicts.count("APPROVED")
    conditional = verdicts.count("CONDITIONAL")
    rejected = verdicts.count("REJECTED")
    scores = [r.get("score") for r in runs if isinstance(r.get("score"), (int, float))]
    approval_rate = (approved + conditional) / total * 100 if total else 0.0
    avg_score = sum(scores) / len(scores) if scores else 0.0

    def _card(label: str, value: str, color: str) -> None:
        with (
            ui.element("div")
            .classes("panel q-pa-md flex-1")
            .style(f"border-left: 4px solid {color}; min-width: 150px")
        ):
            ui.label(label).classes("text-caption text-grey")
            ui.label(value).classes("text-h5 font-bold").style(f"color: {color}")

    with ui.row().classes("w-full wrap gap-md q-mb-lg"):
        _card("Total Runs", str(total), COLORS["primary"])
        _card("APPROVED", str(approved), COLORS["pass_"])
        _card("CONDITIONAL", str(conditional), COLORS["inconclusive"])
        _card("REJECTED", str(rejected), COLORS["fail"])
        _card("Approval Rate", f"{approval_rate:.1f}%", COLORS["accent"])
        _card("Avg Score", f"{avg_score:.1f}", COLORS["secondary"])


def _build_verdict_table(store: SwarmRunStore | None, summary_container: ui.column) -> ui.table:
    """Verdict table over the runs the executor actually persisted."""
    columns = [
        {"name": "run_id", "label": "Run ID", "field": "run_id", "align": "left"},
        {"name": "timestamp", "label": "Date", "field": "timestamp", "align": "left"},
        {"name": "goal", "label": "Goal", "field": "goal", "align": "left"},
        {"name": "strategy", "label": "Strategy", "field": "strategy", "align": "left"},
        {"name": "return", "label": "Return", "field": "return", "align": "right"},
        {"name": "sharpe", "label": "Sharpe", "field": "sharpe", "align": "right"},
        {"name": "score", "label": "Score", "field": "score", "align": "right"},
        {"name": "verdict", "label": "Verdict", "field": "verdict", "align": "center"},
    ]
    table = ui.table(
        columns=columns, rows=[], row_key="run_id", pagination={"rowsPerPage": 25}
    ).classes("w-full")

    async def _load_data() -> None:
        if store is None or not store.is_initialized:
            return
        try:
            listed = await store.list_runs(limit=200)
        except Exception:
            logger.exception("Failed to load runs for profitability")
            return
        rows: list[dict[str, Any]] = []
        for entry in listed:
            detail = await store.get_run(entry["workflow_id"]) or {}
            results = detail.get("results") or {}
            metrics = extract_result_metrics(results)
            decision = results.get("deployment_decision") or {}
            verdict = str(
                metrics.get("verdict")
                or decision.get("status")
                or ("RUNNING" if entry.get("status") == "running" else "FAILED")
            )
            request = entry.get("request") or {}
            score = decision.get("recommendation_score")
            rows.append(
                {
                    "run_id": str(entry.get("workflow_id") or "")[:12],
                    "timestamp": str(entry.get("started_at") or "")[:16].replace("T", " "),
                    "goal": str(request.get("objetivo_inversion") or "—"),
                    "strategy": metrics.get("strategy") or request.get("strategy") or "—",
                    "return": _fmt(metrics.get("total_return"), "%"),
                    "sharpe": _fmt(metrics.get("sharpe")),
                    "score": f"{float(score):.1f}" if isinstance(score, (int, float)) else "—",
                    "verdict": verdict,
                    "verdict_color": _verdict_color(verdict),
                }
            )
        table.rows = rows
        table.update()

        summary_container.clear()
        with summary_container:
            _build_summary_cards(rows)

    ui.timer(0.1, _load_data, once=True)
    return table


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):+,.2f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


# ── Page Render ───────────────────────────────────────────────────────────────


def render(store: SwarmRunStore | None) -> None:
    """Render the Profitability page over the real swarm run store."""
    ds.inject()
    with ui.column().classes("w-full q-pa-lg"):
        ds.section_heading(
            "Profitability Analysis",
            "Aggregated profitability verdicts and summary statistics across all runs.",
        )

        summary_container = ui.column().classes("w-full q-mb-lg")
        with summary_container:  # noqa: SIM117
            with ui.row().classes("w-full wrap gap-md"):
                for _ in range(6):
                    skeleton_card()

        with ui.card().classes("w-full q-pa-lg"):
            ui.label("Verdict Table").classes("text-h6 q-mb-md")
            _build_verdict_table(store, summary_container)
