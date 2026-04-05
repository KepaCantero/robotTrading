"""Side-by-side run comparison component.

Displays two backtest runs with parameter diff and results diff.
Used by the History & Compare page to render metric-by-metric
comparison between two BacktestRunRecord instances.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import COLORS


def run_comparison(
    run_a_label: str,
    run_b_label: str,
    diff: dict[str, Any],
) -> None:
    """Render a side-by-side comparison of two backtest runs.

    Parameters
    ----------
    run_a_label:
        Display label for run A (e.g. timestamp + strategy).
    run_b_label:
        Display label for run B.
    diff:
        Dict mapping metric names to ``{a, b, delta}`` dicts as
        returned by ``BacktestResultStore.compare()``.
    """
    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(run_a_label).classes("text-subtitle1 font-bold").style(
                f"color: {COLORS['primary']}"
            )
            ui.icon("arrow_forward").classes("text-grey")
            ui.label(run_b_label).classes("text-subtitle1 font-bold").style(
                f"color: {COLORS['accent']}"
            )

        ui.separator().classes("q-mt-sm q-mb-md")

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

            val_a_str = _format_value(val_a)
            val_b_str = _format_value(val_b)

            delta_str = f"{delta:+.4f}" if delta is not None else "N/A"

            rows.append(
                {
                    "metric": key,
                    "run_a": val_a_str,
                    "run_b": val_b_str,
                    "delta": delta_str,
                }
            )

        ui.table(
            columns=columns,
            rows=rows,
        ).classes("w-full")


def _format_value(value: Any) -> str:
    """Format a comparison value for display."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
