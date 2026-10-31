"""History & Compare — the REAL run memory (swarm_runs.db).

Every mission the executor persisted, with the passing ones pinnable (★)
and any two comparable side by side. This page used to read
backtest_results.db — orphaned since 2026-10-18, when its only writer
lost its route — which is why history and comparison looked frozen at
two stale rows. Click a passing run to pin/unpin it as a saved backtest.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.pages.swarm import extract_result_metrics
from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.services.agent_swarm.store import SwarmRunStore

logger = logging.getLogger(__name__)

_PASSING = ("APPROVED", "CONDITIONAL")


def _fmt(value: Any, suffix: str = "") -> str:
    """Numeric display with sign; anything unknown is an em dash."""
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):+,.2f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def _summarize(run: dict[str, Any]) -> dict[str, Any]:
    """One display row from a stored run (request + results)."""
    request = run.get("request") or {}
    metrics = extract_result_metrics(run.get("results") or {})
    verdict = str(metrics.get("verdict") or "")
    if not verdict:
        verdict = "RUNNING" if run.get("status") == "running" else "FAILED"
    symbols = metrics.get("symbols") or request.get("symbols") or []
    return {
        "run_id": run.get("workflow_id", ""),
        "date": str(run.get("started_at") or "")[:16].replace("T", " "),
        "goal": str(request.get("objetivo_inversion") or "—"),
        "strategy": metrics.get("strategy") or request.get("strategy") or "—",
        "universe": f"{len(symbols)} symbols" if symbols else "—",
        "return": _fmt(metrics.get("total_return"), "%"),
        "sharpe": _fmt(metrics.get("sharpe")),
        "drawdown": _fmt(metrics.get("drawdown"), "%"),
        "verdict": verdict,
        "saved": "★" if run.get("saved") else "☆",
        "_passing": verdict in _PASSING,
        "_saved": bool(run.get("saved")),
    }


async def _load_runs(store: SwarmRunStore, limit: int = 100) -> list[dict[str, Any]]:
    """Detailed runs (request + results) for the table and the selectors."""
    listed = await store.list_runs(limit=limit)
    detailed: list[dict[str, Any]] = []
    for entry in listed:
        run = await store.get_run(entry["workflow_id"])
        detailed.append(run or {**entry, "results": {}})
    return detailed


def _compare_rows(run_a: dict[str, Any], run_b: dict[str, Any]) -> list[dict[str, str]]:
    """Metric/delta rows for two stored runs (text + numeric)."""
    m_a = extract_result_metrics(run_a.get("results") or {})
    m_b = extract_result_metrics(run_b.get("results") or {})
    r_a, r_b = run_a.get("request") or {}, run_b.get("request") or {}

    rows: list[dict[str, str]] = []

    def _row(name: str, a: Any, b: Any, numeric: bool = False) -> None:
        a_str = _fmt(a) if numeric else (str(a) if a not in (None, "") else "—")
        b_str = _fmt(b) if numeric else (str(b) if b not in (None, "") else "—")
        delta: str | None = None
        color = str(COLORS.get("neutral", ""))
        if numeric:
            try:
                diff = float(b) - float(a)
                delta = f"{diff:+,.2f}"
                color = str(COLORS.get("profit" if diff > 0 else "loss", ""))
            except (TypeError, ValueError):
                pass
        rows.append(
            {"metric": name, "run_a": a_str, "run_b": b_str, "delta": delta or "—", "color": color}
        )

    _row("Date", run_a.get("started_at", "")[:16], run_b.get("started_at", "")[:16])
    _row("Goal", r_a.get("objetivo_inversion"), r_b.get("objetivo_inversion"))
    _row("Strategy", m_a.get("strategy"), m_b.get("strategy"))
    _row(
        "Universe",
        ", ".join(m_a.get("symbols") or r_a.get("symbols") or []),
        ", ".join(m_b.get("symbols") or r_b.get("symbols") or []),
    )
    _row(
        "Period",
        f"{r_a.get('backtest_start', '?')} → {r_a.get('backtest_end', '?')}",
        f"{r_b.get('backtest_start', '?')} → {r_b.get('backtest_end', '?')}",
    )
    _row("Return %", m_a.get("total_return"), m_b.get("total_return"), numeric=True)
    _row("Sharpe", m_a.get("sharpe"), m_b.get("sharpe"), numeric=True)
    _row("Max drawdown %", m_a.get("drawdown"), m_b.get("drawdown"), numeric=True)
    _row(
        "Feasibility",
        m_a.get("feasibility"),
        m_b.get("feasibility"),
        numeric=True,
    )
    _row("Verdict", m_a.get("verdict"), m_b.get("verdict"))
    return rows


def _build_runs_table(store: SwarmRunStore | None) -> tuple[ui.table, ui.switch, ui.switch]:
    """History table + its filters. Click a passing row to pin (★) it."""
    columns = [
        {"name": "saved", "label": "", "field": "saved", "align": "center"},
        {"name": "date", "label": "Date", "field": "date", "align": "left"},
        {"name": "goal", "label": "Goal", "field": "goal", "align": "left"},
        {"name": "strategy", "label": "Strategy", "field": "strategy", "align": "left"},
        {"name": "universe", "label": "Universe", "field": "universe", "align": "left"},
        {"name": "return", "label": "Return", "field": "return", "align": "right"},
        {"name": "sharpe", "label": "Sharpe", "field": "sharpe", "align": "right"},
        {"name": "drawdown", "label": "Max DD", "field": "drawdown", "align": "right"},
        {"name": "verdict", "label": "Verdict", "field": "verdict", "align": "center"},
    ]
    only_passing = ui.switch("Only passing (APPROVED / CONDITIONAL)", value=False)
    saved_only = ui.switch("Saved only", value=False)

    table = ui.table(
        columns=columns,
        rows=[],
        row_key="run_id",
        pagination={"rowsPerPage": 15},
    ).classes("w-full")

    async def _refresh() -> None:
        if store is None or not store.is_initialized:
            return
        try:
            runs = await _load_runs(store)
        except Exception:
            logger.exception("Failed to load swarm runs")
            return
        summaries = [_summarize(r) for r in runs]
        if only_passing.value:
            summaries = [s for s in summaries if s["_passing"]]
        if saved_only.value:
            summaries = [s for s in summaries if s["_saved"]]
        table.rows = summaries
        table.update()

    async def _on_row_click(e: Any) -> None:
        row = dict(e.args.get("row") or {})
        run_id = str(row.get("run_id") or "")
        if not run_id or store is None:
            return
        if not row.get("_passing"):
            ui.notify("Only passing runs (APPROVED/CONDITIONAL) can be saved.", type="warning")
            return
        new_saved = not bool(row.get("_saved"))
        await store.set_saved(run_id, new_saved)
        ui.notify("Backtest saved ★" if new_saved else "Backtest unpinned", type="positive")
        await _refresh()

    table.on("rowClick", lambda e: _on_row_click(e))
    only_passing.on_value_change(lambda _e: _refresh())
    saved_only.on_value_change(lambda _e: _refresh())
    ui.timer(0.1, _refresh, once=True)
    return table, only_passing, saved_only


def _build_comparison_section(store: SwarmRunStore | None) -> None:
    """Two-run comparison over the same real runs the table shows."""
    ui.label("Compare Runs").classes("text-h6 q-mt-lg q-mb-md")

    diff_container: ui.column = ui.column().classes("w-full q-mt-md")
    select_a = ui.select(options=[], with_input=True, label="Run A").classes("min-w-[300px]")
    select_b = ui.select(options=[], with_input=True, label="Run B").classes("min-w-[300px]")

    async def _load_options() -> None:
        if store is None or not store.is_initialized:
            return
        try:
            runs = await _load_runs(store, limit=100)
        except Exception:
            logger.exception("Failed to load runs for comparison")
            return
        options = []
        for run in runs:
            s = _summarize(run)
            options.append(
                {
                    "label": f"{s['date']} · {s['goal']} · {s['strategy']} · {s['verdict']}",
                    "value": s["run_id"],
                }
            )
        select_a.options = options
        select_b.options = options
        select_a.update()
        select_b.update()

    async def _run_compare() -> None:
        if store is None:
            ui.notify("Store not initialized.", type="warning")
            return
        if not select_a.value or not select_b.value:
            ui.notify("Please select two runs to compare.", type="warning")
            return
        if select_a.value == select_b.value:
            ui.notify("Please select two different runs.", type="warning")
            return
        run_a = await store.get_run(str(select_a.value))
        run_b = await store.get_run(str(select_b.value))
        if not run_a or not run_b:
            ui.notify("One or both runs not found.", type="negative")
            return
        diff_container.clear()
        with diff_container:
            with ui.element("div").classes("panel q-pa-md w-full"):
                ui.label("Comparison Results").classes("text-h6 q-mb-md")
                ui.table(
                    columns=[
                        {"name": "metric", "label": "Metric", "field": "metric", "align": "left"},
                        {"name": "run_a", "label": "Run A", "field": "run_a", "align": "right"},
                        {"name": "run_b", "label": "Run B", "field": "run_b", "align": "right"},
                        {
                            "name": "delta",
                            "label": "Delta (B−A)",
                            "field": "delta",
                            "align": "right",
                        },
                    ],
                    rows=_compare_rows(run_a, run_b),
                ).classes("w-full")

    with ui.row().classes("w-full items-center gap-lg"):
        ui.button("Compare", icon="compare").props("unelevated no-caps").classes("run-btn").mark(
            "compare_button"
        ).on_click(lambda: _run_compare())

    ui.timer(0.2, _load_options, once=True)


# ── Page Render ───────────────────────────────────────────────────────────────


def render(store: SwarmRunStore | None) -> None:
    """Render the History & Compare page over the swarm run store."""
    with ui.column().classes("w-full q-pa-lg"):
        ds.section_heading(
            "History & Compare", "Every past run, side by side — the honest memory of the robot."
        )
        ui.label(
            "Every run you make lands here automatically. Click a passing run to "
            "pin it ★ as a saved backtest; compare any two below."
        ).classes("text-grey q-mb-lg")

        if store is None:
            ui.label(
                "Run storage is not available in this session — restart the dashboard."
            ).classes("help")
            return

        with ui.element("div").classes("panel q-pa-md w-full"):
            _build_runs_table(store)

        ui.separator().classes("q-mt-lg q-mb-lg")

        with ui.element("div").classes("panel q-pa-md w-full"):
            _build_comparison_section(store)
