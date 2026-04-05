"""History & Compare page - historical runs and side-by-side comparison.

Shows past backtest runs in a table with diff comparison between runs.
Loads data from BacktestResultStore and provides two-dropdown comparison
with metric deltas.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.infrastructure.persistence.backtest_result_store import (
        BacktestResultStore,
        BacktestRunRecord,
    )
    from app.presentation.dashboard.profitability_engine import ProfitabilityEngine

logger = logging.getLogger(__name__)


def _fmt_ts(record: BacktestRunRecord) -> str:
    """Format the timestamp for display."""
    return record.timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_val(value: float | None, suffix: str = "") -> str:
    """Format a numeric value for display."""
    if value is None:
        return "N/A"
    return f"{value:.4f}{suffix}"


def _fmt_pct(value: float | None) -> str:
    """Format a value as percentage."""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _build_runs_table(
    store: BacktestResultStore | None,
    profitability: ProfitabilityEngine | None,
) -> ui.table:
    """Build and return the runs history table."""
    columns = [
        {"name": "timestamp", "label": "Timestamp", "field": "timestamp", "align": "left"},
        {"name": "strategy", "label": "Strategy", "field": "strategy", "align": "left"},
        {"name": "profile", "label": "Profile", "field": "profile", "align": "left"},
        {"name": "window", "label": "Time Window", "field": "window", "align": "left"},
        {"name": "return", "label": "Return", "field": "return", "align": "right"},
        {"name": "sharpe", "label": "Sharpe", "field": "sharpe", "align": "right"},
        {"name": "verdict", "label": "Verdict", "field": "verdict", "align": "center"},
    ]

    table = ui.table(
        columns=columns,
        rows=[],
        row_key="run_id",
        pagination={"rowsPerPage": 15},
    ).classes("w-full")

    async def _load_data() -> None:
        if store is None:
            return
        try:
            runs = await store.list_runs(limit=100)
        except Exception:
            logger.exception("Failed to load runs")
            return

        rows: list[dict[str, Any]] = []
        for run in runs:
            verdict = "INCONCLUSIVE"
            if profitability is not None:
                result = profitability.evaluate(run)
                verdict = result.verdict

            rows.append(
                {
                    "run_id": run.run_id,
                    "timestamp": _fmt_ts(run),
                    "strategy": run.strategy_name,
                    "profile": run.investor_profile or "N/A",
                    "window": run.time_window,
                    "return": _fmt_pct(run.total_return),
                    "sharpe": _fmt_val(run.sharpe_ratio),
                    "verdict": verdict,
                }
            )
        table.rows = rows
        table.update()

    ui.timer(0.1, _load_data, once=True)
    return table


def _build_comparison_section(
    store: BacktestResultStore | None,
) -> None:
    """Build the comparison dropdowns and diff view."""
    ui.label("Compare Runs").classes("text-h6 q-mt-lg q-mb-md")

    with ui.row().classes("w-full items-center gap-lg"):
        with ui.column().classes("min-w-[300px]"):
            ui.label("Run A").classes("text-caption")
            select_a = ui.select(
                options=[],
                with_input=True,
                label="Select first run",
            ).classes("min-w-[300px]")

        with ui.column().classes("min-w-[300px]"):
            ui.label("Run B").classes("text-caption")
            select_b = ui.select(
                options=[],
                with_input=True,
                label="Select second run",
            ).classes("min-w-[300px]")

        ui.button(
            "Compare",
            icon="compare",
        ).props(
            "color=primary"
        ).on_click(lambda: _run_compare(store, select_a, select_b, diff_container))

    diff_container = ui.column().classes("w-full q-mt-md")

    async def _load_options() -> None:
        if store is None:
            return
        try:
            runs = await store.list_runs(limit=100)
        except Exception:
            logger.exception("Failed to load runs for comparison")
            return

        options = [
            {
                "label": f"{r.timestamp.strftime('%Y-%m-%d %H:%M')} | {r.strategy_name} ({r.run_id[:8]})",
                "value": r.run_id,
            }
            for r in runs
        ]
        select_a.options = options
        select_b.options = options
        select_a.update()
        select_b.update()

    ui.timer(0.2, _load_options, once=True)


async def _run_compare(
    store: BacktestResultStore | None,
    select_a: ui.select,
    select_b: ui.select,
    container: ui.column,
) -> None:
    """Execute the comparison and render the diff view."""
    if store is None:
        ui.notify("Store not initialized.", type="warning")
        return

    id_a = select_a.value
    id_b = select_b.value

    if not id_a or not id_b:
        ui.notify("Please select two runs to compare.", type="warning")
        return

    if id_a == id_b:
        ui.notify("Please select two different runs.", type="warning")
        return

    try:
        diff = await store.compare(id_a, id_b)
    except Exception:
        logger.exception("Comparison failed")
        ui.notify("Comparison failed.", type="negative")
        return

    if diff is None:
        ui.notify("One or both runs not found.", type="negative")
        return

    container.clear()
    with container:
        _render_diff(diff)


def _render_diff(diff: dict[str, Any]) -> None:
    """Render the comparison diff as a table."""
    with ui.card().classes("w-full"):
        ui.label("Comparison Results").classes("text-h6 q-mb-md")

        columns = [
            {"name": "metric", "label": "Metric", "field": "metric", "align": "left"},
            {"name": "run_a", "label": "Run A", "field": "run_a", "align": "right"},
            {"name": "run_b", "label": "Run B", "field": "run_b", "align": "right"},
            {"name": "delta", "label": "Delta", "field": "delta", "align": "right"},
        ]

        rows: list[dict[str, str]] = []
        for key, values in diff.items():
            val_a = values.get("a")
            val_b = values.get("b")
            delta = values.get("delta")

            if isinstance(val_a, float):
                val_a_str = f"{val_a:.4f}"
            elif val_a is not None:
                val_a_str = str(val_a)
            else:
                val_a_str = "N/A"

            if isinstance(val_b, float):
                val_b_str = f"{val_b:.4f}"
            elif val_b is not None:
                val_b_str = str(val_b)
            else:
                val_b_str = "N/A"

            if delta is not None:
                delta_str = f"{delta:+.4f}"
                delta_color = COLORS["profit"] if delta > 0 else COLORS["loss"]
            else:
                delta_str = "N/A"
                delta_color = COLORS["neutral"]

            rows.append(
                {
                    "metric": key,
                    "run_a": val_a_str,
                    "run_b": val_b_str,
                    "delta": delta_str,
                    "delta_color": delta_color,
                }
            )

        ui.table(
            columns=columns,
            rows=rows,
        ).classes("w-full")


# ── Page Render ───────────────────────────────────────────────────────────────


def render(
    store: BacktestResultStore | None,
    profitability: ProfitabilityEngine | None,
) -> None:
    """Render the History & Compare page content."""
    with ui.column().classes("w-full q-pa-lg"):
        ui.label("History & Compare").classes("text-h4 q-mb-md")
        ui.label("View past backtest runs and compare results side by side.").classes(
            "text-grey q-mb-lg"
        )

        with ui.card().classes("w-full q-pa-lg"):
            ui.label("Run History").classes("text-h6 q-mb-md")
            _build_runs_table(store, profitability)

        ui.separator().classes("q-mt-lg q-mb-lg")

        with ui.card().classes("w-full q-pa-lg"):
            _build_comparison_section(store)
