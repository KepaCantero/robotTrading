"""History & Compare — the REAL run memory (swarm_runs.db).

Every mission the executor persisted, with the passing ones pinnable (★)
and any two comparable side by side. This page used to read
backtest_results.db — orphaned since 2026-10-18, when its only writer
lost its route — which is why history and comparison looked frozen at
two stale rows. Click a passing run to pin/unpin it as a saved backtest.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.pages.swarm import extract_result_metrics
from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.services.agent_swarm.store import SwarmRunStore

logger = logging.getLogger(__name__)

#: FIX 3 (31-10): binary verdicts — CONDITIONAL is retired. Historical
#: CONDITIONAL runs render but no longer count as passing.
_PASSING = ("APPROVED",)


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
        # Quasar emite rowClick como (row, index) → NiceGUI entrega e.args
        # como LISTA; también toleramos el dict {"row": ...} de versiones
        # previas. Antes: e.args.get sobre una lista → AttributeError en
        # cada click (el "no funciona" reportado 31-10).
        args = e.args
        row: dict = {}
        if isinstance(args, dict):
            row = dict(args.get("row") or {})
        elif isinstance(args, list) and args and isinstance(args[0], dict):
            row = dict(args[0].get("row") or args[0])
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


def _build_portfolio_lab() -> None:
    """Backtest ANY portfolio (31-10, user: 'se tiene que poder cargar el
    portfolio que quieras y darle backtesting'): paste one SYMBOL WEIGHT
    line per position (or load a saved portfolio), pick a window, and get
    the same honest machinery as any run — weighted buy&hold over real
    local data, bootstrap fan, 4% withdrawals and stress replays."""
    from datetime import date, timedelta

    import numpy as np
    import pandas as pd

    from app.presentation.dashboard.nicegui_app.pages.swarm import build_fan_chart_option
    from app.services.backtest_orchestration.reliability import (
        DEFAULT_DATA_DIR,
        bootstrap_portfolio,
        stress_windows,
        withdrawal_sequences,
    )

    ui.label("Backtest any portfolio").classes("text-h6 q-mt-lg q-mb-md")
    ui.label(
        "Paste any portfolio — one position per line as SYMBOL WEIGHT (%) — or "
        "load one of your saved portfolios, choose a window, and simulate it: "
        "buy & hold with real local data, 1,000 alternative orderings, "
        "withdrawal survival and real-crash replays."
    ).classes("text-grey q-mb-md")

    periods = {"6m": 183, "1y": 365, "2y": 730, "5y": 1825, "10y": 3650}
    presets: dict[str, str] = {}
    try:
        from app.services.portfolio_management.named_portfolios import list_portfolios

        for portfolio in list_portfolios() or []:
            slug = str(portfolio.get("slug") or "")
            if slug:
                presets[slug] = str(portfolio.get("name") or slug)
    except Exception:  # noqa: BLE001 - presets are a convenience, not a requirement
        logger.warning("portfolio lab: no named portfolios", exc_info=True)

    with ui.row().classes("w-full items-center gap-md no-wrap"):
        period = ui.select(periods, value="10y", label="Window").classes("min-w-[110px]")
        if presets:
            preset_select = (
                ui.select(presets, value=next(iter(presets)), label="Load a saved portfolio")
                .classes("min-w-[260px]")
                .mark("lab_preset")
            )
        else:
            preset_select = None

    text = (
        ui.textarea(
            "Portfolio — one position per line: SYMBOL WEIGHT (%)", value="VWCE 75\nAGGH.AS 25"
        )
        .classes("w-full")
        .style("min-height: 110px")
        .mark("lab_portfolio")
    )

    async def _fill_from_preset() -> None:
        if preset_select is None:
            return
        slug = str(preset_select.value or "")
        if not slug:
            return
        try:
            from app.services.portfolio_management.named_portfolios import open_store

            engine, portfolio_store = open_store(slug)
            try:
                target = await portfolio_store.get_active_target()
            finally:
                await engine.dispose()
            if target and target.holdings:
                text.value = "\n".join(
                    f"{h.symbol} {float(h.weight) * 100:g}" for h in target.holdings if h.weight > 0
                )
                ui.notify(f"Loaded {slug}", type="positive")
        except Exception:  # noqa: BLE001 - a failed preset load must not break the lab
            logger.warning("portfolio lab: preset load failed", exc_info=True)
            ui.notify("Could not load that portfolio's target.", type="warning")

    if preset_select is not None:
        preset_select.on_value_change(lambda _e: _fill_from_preset())

    result_box = ui.column().classes("w-full")

    def _weighted_series(weights: dict[str, float], start: str, end: str):
        parts: list[pd.Series] = []
        used: list[str] = []
        for sym, weight in weights.items():
            path = DEFAULT_DATA_DIR / f"{sym}.csv"
            if not path.exists():
                continue
            try:
                frame = pd.read_csv(
                    path, usecols=["date", "Close"], parse_dates=["date"], index_col="date"
                )
                window = frame.loc[start:end, "Close"].dropna()
            except Exception:  # noqa: BLE001 - one bad CSV never kills the lab
                continue
            if len(window) < 5:
                continue
            parts.append(float(weight) * (window / float(window.iloc[0])))
            used.append(sym)
        if not parts:
            return None, used
        covered = sum(weights[s] for s in used)
        return (sum(parts) / covered).dropna(), used

    async def _run_lab() -> None:
        weights: dict[str, float] = {}
        unparsed: list[str] = []
        for line in (text.value or "").splitlines():
            line = line.strip().replace(",", " ")
            if not line or line.startswith("#"):
                continue
            bits = line.split()
            if len(bits) < 2:
                unparsed.append(line)
                continue
            try:
                weight = float(bits[1])
            except ValueError:
                unparsed.append(line)
                continue
            if weight <= 0:
                continue
            # "75" = por ciento; "0.75" = fracción
            weight = weight / 100.0 if weight > 1.5 else weight
            symbol = bits[0].upper()
            weights[symbol] = weights.get(symbol, 0.0) + weight
        if unparsed:
            ui.notify(f"Ignored unparseable lines: {unparsed[:3]}", type="warning")
        if not weights:
            ui.notify("Write at least one SYMBOL WEIGHT line.", type="warning")
            return

        days = periods.get(str(period.value), 3650)
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days)).isoformat()
        series, used = await asyncio.to_thread(_weighted_series, weights, start, end)

        result_box.clear()
        with result_box:
            if series is None or len(series) < 30:
                ui.label(
                    "No local data covers that window for any of those symbols — "
                    "check the tickers or use a shorter window."
                ).classes("help q-mt-md")
                return
            returns = series.pct_change().dropna().values
            years = (series.index[-1] - series.index[0]).days / 365.25
            total = float(series.iloc[-1] / series.iloc[0] - 1)
            cagr = (1.0 + total) ** (1.0 / years) - 1.0 if total > -1 else -1.0
            max_dd = float((series / series.cummax() - 1.0).min())
            sharpe = (
                float(np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(252))
                if len(returns) > 2
                else 0.0
            )
            missing = [s for s in weights if s not in used]

            with ui.row().classes("w-full gap-lg wrap q-mt-md"):
                for tile_label, tile_value in (
                    ("Total return", f"{total * 100:+.1f}%"),
                    ("CAGR", f"{cagr * 100:+.1f}%"),
                    ("Max drawdown", f"{max_dd * 100:.1f}%"),
                    ("Sharpe", f"{sharpe:.2f}"),
                    ("Years", f"{years:.1f}"),
                    ("Positions with data", f"{len(used)}/{len(weights)}"),
                ):
                    with ui.column().classes("gap-xs"):
                        ui.label(tile_value).classes("help").style(
                            "font-size:1.25rem;font-weight:600"
                        )
                        ui.label(tile_label).classes("help")
            if missing:
                ui.label(
                    f"No local data for: {', '.join(missing)} — excluded, weights "
                    "renormalized over the rest."
                ).classes("help q-mt-xs")

            boot = bootstrap_portfolio(returns)
            if boot:
                ui.echart(build_fan_chart_option(boot)).props(
                    "role=img aria-label='Portfolio lab bootstrap fan chart'"
                ).classes("w-full").style("height: 240px")
                ui.label(
                    f"1,000 alternative orderings: worst 5% ends at "
                    f"{boot['final_p05']:.2f}×, median {boot['final_p50']:.2f}×, "
                    f"chance of loss {boot['prob_loss'] * 100:.0f}%."
                ).classes("help q-mt-xs")
            withdrawal = withdrawal_sequences(returns)
            if withdrawal:
                ui.label(
                    f"Living off it at 4%/yr for {withdrawal['horizon_years']}y: the money "
                    f"runs out in {withdrawal['prob_exhausted'] * 100:.0f}% of sequences "
                    f"(median ends at {withdrawal['final_p50']:.2f}×)."
                ).classes("help")
            stress = stress_windows(used)
            stress_bits = [
                f"{label}: {info['max_drawdown'] * 100:+.1f}% worst fall"
                for label, info in (stress or {}).items()
                if info
            ]
            if stress_bits:
                ui.label("Stress: " + " · ".join(stress_bits)).classes("help")

    ui.button("Backtest this portfolio", icon="science").props("unelevated no-caps").classes(
        "run-btn"
    ).mark("lab_run").on_click(lambda: _run_lab())


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

        ui.separator().classes("q-mt-lg q-mb-lg")

        with ui.element("div").classes("panel q-pa-md w-full"):
            _build_portfolio_lab()
