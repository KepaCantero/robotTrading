"""Profitability page - verdicts, trends, and summary statistics.

Aggregated profitability analysis across all runs. Shows a verdict table,
color-coded badges, and summary counts of PASS/FAIL/INCONCLUSIVE.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.metric_cards import skeleton_card
from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.infrastructure.persistence.backtest_result_store import BacktestResultStore
    from app.presentation.dashboard.profitability_engine import (
        ProfitabilityEngine,
        ProfitabilityResult,
    )

logger = logging.getLogger(__name__)


def _fmt_pct(value: float | None) -> str:
    """Format a value as a percentage string."""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _build_summary_cards(results: list[ProfitabilityResult]) -> None:
    """Render summary statistics cards."""
    pass_count = sum(1 for r in results if r.verdict == "PASS")
    fail_count = sum(1 for r in results if r.verdict == "FAIL")
    inconclusive_count = sum(1 for r in results if r.verdict == "INCONCLUSIVE")
    total = len(results)

    if total > 0:
        avg_score = sum(r.score for r in results) / total
        pass_rate = pass_count / total * 100
    else:
        avg_score = 0.0
        pass_rate = 0.0

    with ui.row().classes("w-full wrap gap-md q-mb-lg"):
        with (
            ui.card()
            .classes("q-pa-md")
            .style(f"border-left: 4px solid {COLORS['primary']}; min-width: 150px")
        ):
            ui.label("Total Runs").classes("text-caption text-grey")
            ui.label(str(total)).classes("text-h5 font-bold")

        with (
            ui.card()
            .classes("q-pa-md")
            .style(f"border-left: 4px solid {COLORS['pass_']}; min-width: 150px")
        ):
            ui.label("PASS").classes("text-caption text-grey")
            ui.label(str(pass_count)).classes("text-h5 font-bold").style(
                f"color: {COLORS['pass_']}"
            )

        with (
            ui.card()
            .classes("q-pa-md")
            .style(f"border-left: 4px solid {COLORS['fail']}; min-width: 150px")
        ):
            ui.label("FAIL").classes("text-caption text-grey")
            ui.label(str(fail_count)).classes("text-h5 font-bold").style(f"color: {COLORS['fail']}")

        with (
            ui.card()
            .classes("q-pa-md")
            .style(f"border-left: 4px solid {COLORS['inconclusive']}; min-width: 150px")
        ):
            ui.label("INCONCLUSIVE").classes("text-caption text-grey")
            ui.label(str(inconclusive_count)).classes("text-h5 font-bold").style(
                f"color: {COLORS['inconclusive']}"
            )

        with (
            ui.card()
            .classes("q-pa-md")
            .style(f"border-left: 4px solid {COLORS['accent']}; min-width: 150px")
        ):
            ui.label("Pass Rate").classes("text-caption text-grey")
            ui.label(f"{pass_rate:.1f}%").classes("text-h5 font-bold").style(
                f"color: {COLORS['accent']}"
            )

        with (
            ui.card()
            .classes("q-pa-md")
            .style(f"border-left: 4px solid {COLORS['secondary']}; min-width: 150px")
        ):
            ui.label("Avg Score").classes("text-caption text-grey")
            ui.label(f"{avg_score:.1f}").classes("text-h5 font-bold")


def _build_verdict_table(
    store: BacktestResultStore | None,
    profitability: ProfitabilityEngine | None,
    summary_container: ui.column,
) -> ui.table:
    """Build and return the profitability verdicts table."""
    columns = [
        {"name": "run_id", "label": "Run ID", "field": "run_id", "align": "left"},
        {"name": "timestamp", "label": "Timestamp", "field": "timestamp", "align": "left"},
        {"name": "strategy", "label": "Strategy", "field": "strategy", "align": "left"},
        {"name": "profile", "label": "Profile", "field": "profile", "align": "left"},
        {"name": "score", "label": "Score", "field": "score", "align": "right"},
        {"name": "verdict", "label": "Verdict", "field": "verdict", "align": "center"},
    ]

    table = ui.table(
        columns=columns,
        rows=[],
        row_key="run_id",
        pagination={"rowsPerPage": 25},
    ).classes("w-full")

    async def _load_data() -> None:
        if store is None or profitability is None:
            return
        try:
            runs = await store.list_runs(limit=200)
        except Exception:
            logger.exception("Failed to load runs for profitability")
            return

        results = profitability.batch_evaluate(runs)

        rows: list[dict[str, Any]] = []
        for run, result in zip(runs, results):
            rows.append(
                {
                    "run_id": run.run_id[:12],
                    "timestamp": run.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "strategy": run.strategy_name,
                    "profile": run.investor_profile or "N/A",
                    "score": f"{result.score:.1f}",
                    "verdict": result.verdict,
                }
            )

        table.rows = rows
        table.update()

        # Update summary cards
        summary_container.clear()
        with summary_container:
            _build_summary_cards(results)

    ui.timer(0.1, _load_data, once=True)
    return table


# ── Page Render ───────────────────────────────────────────────────────────────


def render(
    store: BacktestResultStore | None,
    profitability: ProfitabilityEngine | None,
) -> None:
    """Render the Profitability page content."""
    with ui.column().classes("w-full q-pa-lg"):
        ui.label("Profitability Analysis").classes("text-h4 q-mb-md")
        ui.label(
            "Aggregated profitability verdicts and summary statistics across all runs."
        ).classes("text-grey q-mb-lg")

        # Summary stats (populated asynchronously)
        summary_container = ui.column().classes("w-full q-mb-lg")
        with summary_container:  # noqa: SIM117
            with ui.row().classes("w-full wrap gap-md"):
                for _ in range(6):
                    skeleton_card()

        with ui.card().classes("w-full q-pa-lg"):
            ui.label("Verdict Table").classes("text-h6 q-mb-md")
            _build_verdict_table(store, profitability, summary_container)
