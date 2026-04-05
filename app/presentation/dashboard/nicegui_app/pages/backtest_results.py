"""Backtest Results page - view results and profitability verdict.

Displays metrics, profitability badge, and detailed metrics for a
specific run. The run is selected via a dropdown loaded from
BacktestResultStore.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.metric_cards import metric_card
from app.presentation.dashboard.nicegui_app.components.profitability_badge import (
    profitability_badge,
)
from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.infrastructure.persistence.backtest_result_store import (
        BacktestResultStore,
        BacktestRunRecord,
    )
    from app.presentation.dashboard.profitability_engine import ProfitabilityEngine

logger = logging.getLogger(__name__)


def _fmt_pct(value: float | None) -> str:
    """Format a value as a percentage string."""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _fmt_float(value: float | None) -> str:
    """Format a value as a decimal string."""
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def _fmt_int(value: int | None) -> str:
    """Format an integer value."""
    if value is None:
        return "N/A"
    return str(value)


def _render_run_details(
    run: BacktestRunRecord,
    verdict_text: str,
    score: float,
) -> None:
    """Render the full run details card."""
    # ── Header ────────────────────────────────────────────────────────────
    with ui.card().classes("w-full q-pa-lg"):
        ui.label(f"Run: {run.run_id}").classes("text-h6")
        with ui.row().classes("q-mt-sm q-mb-md gap-md"):
            ui.label(f"Strategy: {run.strategy_name}").classes("text-body2")
            ui.label(f"Profile: {run.investor_profile or 'N/A'}").classes("text-body2")
            ui.label(f"Window: {run.time_window}").classes("text-body2")
            ui.label(f"Timestamp: {run.timestamp.strftime('%Y-%m-%d %H:%M:%S')}").classes(
                "text-body2"
            )

        ui.separator().classes("q-mb-md")

        # ── Verdict ───────────────────────────────────────────────────────
        with ui.row().classes("items-center q-mb-md gap-md"):
            ui.label("Profitability Verdict:").classes("text-subtitle1")
            profitability_badge(verdict_text)
            ui.label(f"Score: {score:.1f} / 100").classes("text-subtitle1 font-bold").style(
                f"color: {COLORS['accent']}"
            )

        ui.separator().classes("q-mb-md")

        # ── Key Metrics ───────────────────────────────────────────────────
        ui.label("Key Metrics").classes("text-h6 q-mb-sm")
        with ui.row().classes("w-full wrap gap-md"):
            metric_card(
                title="Total Return",
                value=_fmt_pct(run.total_return),
                subtitle="Net performance",
                color=(
                    COLORS["profit"]
                    if run.total_return and run.total_return > 0
                    else COLORS["loss"]
                ),
            )
            metric_card(
                title="Sharpe Ratio",
                value=_fmt_float(run.sharpe_ratio),
                subtitle="Risk-adjusted return",
                color=COLORS["primary"],
            )
            metric_card(
                title="Sortino Ratio",
                value=_fmt_float(run.sortino_ratio),
                subtitle="Downside risk-adjusted",
                color=COLORS["primary"],
            )
            metric_card(
                title="Max Drawdown",
                value=_fmt_pct(run.max_drawdown),
                subtitle="Worst peak-to-trough",
                color=COLORS["loss"],
            )
            metric_card(
                title="Win Rate",
                value=_fmt_pct(run.win_rate),
                subtitle="Winning trades / total",
                color=COLORS["primary"],
            )
            metric_card(
                title="Profit Factor",
                value=_fmt_float(run.profit_factor),
                subtitle="Gross profit / gross loss",
                color=COLORS["primary"],
            )
            metric_card(
                title="Total Trades",
                value=_fmt_int(run.total_trades),
                subtitle="Executed trades",
                color=COLORS["secondary"],
            )

    # ── Config Snapshot ───────────────────────────────────────────────────
    if run.config_snapshot:
        with ui.card().classes("w-full q-pa-lg q-mt-md"):
            ui.label("Configuration Snapshot").classes("text-h6 q-mb-sm")
            ui.separator().classes("q-mb-sm")
            try:
                config = json.loads(run.config_snapshot)
                with ui.row().classes("w-full wrap gap-lg"):
                    for key, value in config.items():
                        with ui.column().classes("min-w-[150px]"):
                            ui.label(key).classes("text-caption text-grey")
                            ui.label(str(value)).classes("text-body2")
            except json.JSONDecodeError:
                ui.label(run.config_snapshot).classes("text-caption text-grey")

    # ── Metadata ──────────────────────────────────────────────────────────
    with ui.card().classes("w-full q-pa-lg q-mt-md"):
        ui.label("Metadata").classes("text-h6 q-mb-sm")
        ui.separator().classes("q-mb-sm")
        with ui.row().classes("w-full wrap gap-lg"):
            with ui.column().classes("min-w-[150px]"):
                ui.label("Run ID").classes("text-caption text-grey")
                ui.label(run.run_id).classes("text-body2")
            with ui.column().classes("min-w-[150px]"):
                ui.label("Git Commit").classes("text-caption text-grey")
                ui.label(run.git_commit_hash or "N/A").classes("text-body2")
            with ui.column().classes("min-w-[150px]"):
                ui.label("Timestamp").classes("text-caption text-grey")
                ui.label(run.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")).classes("text-body2")


# ── Page Render ───────────────────────────────────────────────────────────────


def render(
    store: BacktestResultStore | None,
    profitability: ProfitabilityEngine | None,
) -> None:
    """Render the Backtest Results page content."""
    with ui.column().classes("w-full q-pa-lg"):
        ui.label("Backtest Results").classes("text-h4 q-mb-md")
        ui.label("Select a run to view detailed results.").classes("text-grey q-mb-lg")

        # ── Run Selector ──────────────────────────────────────────────────
        with ui.card().classes("w-full q-pa-lg"):
            ui.label("Select Run").classes("text-h6 q-mb-md")

            with ui.row().classes("w-full items-center gap-lg"):
                select = ui.select(
                    options=[],
                    with_input=True,
                    label="Choose a backtest run",
                ).classes("min-w-[400px]")

                async def _load_options() -> None:
                    if store is None:
                        return
                    try:
                        runs = await store.list_runs(limit=100)
                    except Exception:
                        logger.exception("Failed to load run options")
                        return

                    options = [
                        {
                            "label": (
                                f"{r.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                                f"{r.strategy_name} | "
                                f"{r.investor_profile or 'N/A'} "
                                f"({r.run_id[:8]})"
                            ),
                            "value": r.run_id,
                        }
                        for r in runs
                    ]
                    select.options = options
                    select.update()

                ui.button(
                    "View Results",
                    icon="search",
                ).props("color=primary").on_click(
                    lambda: _load_run(store, profitability, select, results_container)
                )

            ui.timer(0.1, _load_options, once=True)

        # ── Results Container ─────────────────────────────────────────────
        results_container: ui.column = ui.column().classes("w-full q-mt-md")


async def _load_run(
    store: BacktestResultStore | None,
    profitability: ProfitabilityEngine | None,
    select: ui.select,
    container: ui.column,
) -> None:
    """Load and display a specific run's results."""
    if store is None:
        ui.notify("Store not initialized.", type="warning")
        return

    run_id = select.value
    if not run_id:
        ui.notify("Please select a run.", type="warning")
        return

    try:
        run = await store.get(run_id)
    except Exception:
        logger.exception("Failed to load run %s", run_id)
        ui.notify("Failed to load run.", type="negative")
        return

    if run is None:
        ui.notify("Run not found.", type="negative")
        return

    # Evaluate profitability
    verdict_text = "INCONCLUSIVE"
    score = 0.0
    if profitability is not None:
        result = profitability.evaluate(run)
        verdict_text = result.verdict
        score = result.score

    container.clear()
    with container:
        _render_run_details(run, verdict_text, score)
