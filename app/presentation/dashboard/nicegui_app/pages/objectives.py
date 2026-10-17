"""Objectives & compliance page for the NiceGUI dashboard.

Evaluates every saved backtest run against the integration-test targets.
Ported from the retired Streamlit advanced dashboard (2026-10-17 migration);
the target values are unchanged so historical comparisons still match.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.infrastructure.persistence.backtest_result_store import BacktestResultStore

logger = logging.getLogger(__name__)

# Integration-test objectives per metric.
OBJECTIVES: dict[str, dict[str, Any]] = {
    "max_drawdown": {
        "label": "Max Drawdown",
        "target": 20.0,
        "operator": "<",
        "unit": "%",
        "description": "Protect capital in losing streaks",
    },
    "sharpe_ratio": {
        "label": "Sharpe Ratio",
        "target": 1.2,
        "operator": ">",
        "unit": "",
        "description": "Good return per unit of risk",
    },
    "sortino_ratio": {
        "label": "Sortino Ratio",
        "target": 1.5,
        "operator": ">",
        "unit": "",
        "description": "Penalizes downside only",
    },
    "profit_factor": {
        "label": "Profit Factor",
        "target": 1.4,
        "operator": ">",
        "unit": "",
        "description": "Profit per unit of loss",
    },
    "win_rate": {
        "label": "Win Rate",
        "target_min": 45.0,
        "target_max": 60.0,
        "operator": "range",
        "unit": "%",
        "description": "Healthy when avg win > avg loss",
    },
}


def _metric_value(run: Any, metric: str) -> float | None:
    """Extract a comparable value for a metric, or None if missing."""
    value = getattr(run, metric, None)
    if value is None:
        return None
    value = float(value)
    if metric == "max_drawdown":
        return abs(value)
    if metric == "win_rate" and value <= 1.0:
        return value * 100.0
    return value


def _passes(metric: str, value: float) -> bool:
    obj = OBJECTIVES[metric]
    if obj["operator"] == ">":
        return value > obj["target"]
    if obj["operator"] == "<":
        return value < obj["target"]
    return obj["target_min"] <= value <= obj["target_max"]


def _target_text(metric: str) -> str:
    obj = OBJECTIVES[metric]
    if obj["operator"] == "range":
        return f"{obj['target_min']}–{obj['target_max']}{obj['unit']}"
    arrow = ">" if obj["operator"] == ">" else "<"
    return f"{arrow} {obj['target']}{obj['unit']}"


def _format_value(metric: str, value: float) -> str:
    obj = OBJECTIVES[metric]
    if obj["unit"] == "%":
        return f"{value:.1f}%"
    return f"{value:.2f}"


def render(store: BacktestResultStore | None) -> None:
    """Render the objectives compliance page."""
    ui.label("Objectives & Compliance").classes("text-h4 q-mb-md")
    ui.label("Every saved run, checked against the integration-test targets.").classes(
        "text-grey q-mb-lg"
    )

    container = ui.column().classes("w-full")

    async def load() -> None:
        if store is None:
            with container:
                ui.label("BacktestResultStore is not initialized.").classes("text-warning")
            return
        try:
            runs = await store.list_runs(limit=100)
        except Exception:
            logger.exception("Failed to load runs for the objectives page")
            container.clear()
            with container:
                ui.label("Could not load runs from the store.").classes("text-negative")
            return

        container.clear()
        with container:
            if not runs:
                ui.label("No saved runs yet — run a backtest first.").classes("text-grey")
                return

            per_objective_pass: dict[str, int] = {m: 0 for m in OBJECTIVES}
            runs_passing_all = 0

            for run in runs:
                results: dict[str, tuple[bool, float | None]] = {}
                for metric in OBJECTIVES:
                    value = _metric_value(run, metric)
                    results[metric] = (
                        (_passes(metric, value), value) if value is not None else (False, None)
                    )
                if all(passed for passed, _ in results.values()):
                    runs_passing_all += 1
                for metric, (passed, _) in results.items():
                    if passed:
                        per_objective_pass[metric] += 1

            # ── Summary ────────────────────────────────────────────────────
            total = len(runs)
            with ui.row().classes("w-full items-stretch"):
                with ui.card().classes("flex-1"):
                    ui.label("Runs evaluated").classes("text-caption text-grey")
                    ui.label(str(total)).classes("text-h3")
                with ui.card().classes("flex-1"):
                    ui.label("Pass ALL objectives").classes("text-caption text-grey")
                    ui.label(str(runs_passing_all)).classes(
                        "text-h3",
                    ).style(f"color: {COLORS['profit'] if runs_passing_all else COLORS['loss']}")
                for metric, passed in per_objective_pass.items():
                    with ui.card().classes("flex-1"):
                        ui.label(OBJECTIVES[metric]["label"]).classes("text-caption text-grey")
                        ui.label(f"{passed}/{total}").classes("text-h5")
                        ui.linear_progress(
                            value=passed / total if total else 0,
                            show_value=False,
                        ).props(
                            f"color={COLORS['profit'] if passed == total else COLORS['warning']}"
                        ).classes("q-mt-xs")

            # ── Per-run detail ─────────────────────────────────────────────
            ui.label("Runs").classes("text-h6 q-mt-lg")
            for run in runs:
                all_pass = True
                chips: list[str] = []
                for metric in OBJECTIVES:
                    value = _metric_value(run, metric)
                    if value is None:
                        all_pass = False
                        chips.append(f"{OBJECTIVES[metric]['label']}: n/a")
                        continue
                    passed = _passes(metric, value)
                    all_pass = all_pass and passed
                    mark = "✓" if passed else "✗"
                    chips.append(
                        f"{mark} {OBJECTIVES[metric]['label']} {_format_value(metric, value)}"
                    )
                title = (
                    f"{'🟢' if all_pass else '🔴'} "
                    f"{run.timestamp.strftime('%Y-%m-%d %H:%M')} · {run.strategy_name}"
                )
                with ui.expansion(title).classes("w-full"):
                    target_summary = " · ".join(
                        f"{OBJECTIVES[m]['label']} {_target_text(m)}" for m in OBJECTIVES
                    )
                    ui.label(f"Targets: {target_summary}").classes("text-caption text-grey q-mb-sm")
                    for metric, chip in zip(OBJECTIVES, chips):
                        ui.chip(
                            chip,
                            icon=(
                                "check_circle"
                                if chip.startswith("✓")
                                else "cancel"
                                if chip.startswith("✗")
                                else "help"
                            ),
                        ).props("outline").style(
                            "color: #4CAF50" if chip.startswith("✓") else "color: #F44336"
                        )

    ui.button("Refresh", icon="refresh", on_click=load).props("color=primary q-mb-md")
    ui.timer(0.05, load, once=True)
