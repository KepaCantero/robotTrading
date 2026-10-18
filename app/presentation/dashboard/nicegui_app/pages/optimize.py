"""Optimize page: strategy parameter tuning + tax optimization.

Two panels:
1 · TUNE PARAMETERS — grid-search the strategy's params with the real
   engine, compare baseline vs best, adopt with one click, full history.
2 · TAX OPTIMIZER — the repo's real TaxOptimizedPortfolioBuilder: shows
   harvesting opportunities, estimated tax benefit, after-tax return, and
   the adjustments it recommends for your current positions.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.swarm_fx import install as install_fx
from app.services.agent_swarm.serialization import pretty  # noqa: F401

if TYPE_CHECKING:
    from app.services.agent_swarm.executor import Capa2PipelineExecutor
    from app.services.agent_swarm.store import SwarmRunStore

STRATEGIES = {
    "mean_reversion": "Mean reversion",
    "momentum_modular": "Momentum (modular)",
}

PERIOD_PRESETS = {
    "6m": "Last 6 months",
    "1y": "Last year",
    "2y": "Last 2 years",
    "5y": "Last 5 years",
}


def render(
    executor: Capa2PipelineExecutor | None,
    store: SwarmRunStore | None,
) -> None:
    """Render the Optimize page."""
    install_fx()
    ui.dark_mode(False)

    with ui.element("div").classes("light-sheet w-full"):
        for blob in ("blob-a", "blob-b", "blob-c"):
            ui.element("div").classes(f"blob {blob}").props("aria-hidden=true")

        with ui.row().classes("w-full items-center no-wrap gap-md"):
            with ui.column().classes("gap-0 q-mr-md"):
                ui.label("Optimize").classes("hud-title")
                ui.label(
                    "Tune strategy parameters with the real engine, and check "
                    "if your portfolio can save on taxes."
                ).classes("hud-sub")

        with ui.row().classes("w-full items-start gap-lg q-mt-md no-wrap"):
            # ── Left: config ────────────────────────────────────────────
            with ui.element("div").classes("panel q-pa-md").style("width: 380px; flex-shrink: 0"):
                ui.label("1 · CONFIGURE").classes("lbl q-mb-sm")

                estrategia = ui.select(
                    STRATEGIES, value="mean_reversion", label="Strategy"
                ).classes("w-full")
                ui.label("The real strategy whose parameters will be tuned.").classes(
                    "help q-mb-sm"
                )

                periodo = ui.select(PERIOD_PRESETS, value="1y", label="Test period").classes(
                    "w-full"
                )
                ui.label("Longer periods give more reliable results but take longer.").classes(
                    "help q-mb-sm"
                )

                from app.presentation.dashboard.nicegui_app.pages.swarm import available_universe

                universe_options = available_universe()
                universo = ui.select(
                    universe_options,
                    multiple=True,
                    value=["AAPL", "MSFT", "GOOGL"],
                    label="Universe",
                ).classes("w-full")
                ui.label("3-5 symbols keeps optimization fast.").classes("help")

                # ── Optimize button ─────────────────────────────────────
                optimize_button = (
                    ui.button("Optimize parameters", icon="tune")
                    .props("color=teal unelevated dense")
                    .classes("w-full q-mt-md run-btn")
                    .mark("optimize_run")
                )

                optimize_status = ui.label("").classes("help")

            # ── Right: results + tax ────────────────────────────────────
            with ui.column().classes("flex-1 gap-md").style("min-width: 0"):
                optimize_results = ui.column().classes("w-full gap-md")
                param_history = ui.column().classes("w-full gap-xs")

                # ── Tax optimizer panel ─────────────────────────────────
                with ui.element("div").classes("panel q-pa-md w-full"):
                    ui.label("2 · TAX OPTIMIZER").classes("lbl q-mb-xs")
                    ui.label(
                        "Uses the repo's TaxOptimizedPortfolioBuilder with the "
                        "SpainTaxEngine (19/21/23% progressive). Enter your "
                        "current positions to see harvesting opportunities."
                    ).classes("help q-mb-sm")

                    with ui.row().classes("w-full gap-sm no-wrap"):
                        taxa_symbol = ui.input("Symbol (e.g. AAPL)", value="AAPL").classes("flex-1")
                        taxa_value = ui.number(
                            "Position value (€)", value=50000, min=0, step=1000
                        ).classes("flex-1")
                        taxa_cost = ui.number(
                            "Cost basis (€)", value=55000, min=0, step=1000
                        ).classes("flex-1")

                    add_position_btn = ui.button("Add position", icon="add").props(
                        "flat dense color=teal"
                    )
                    positions_list = ui.column().classes("w-full gap-xs q-mt-xs")
                    positions: list[dict[str, Decimal]] = []

                    def refresh_positions() -> None:
                        positions_list.clear()
                        with positions_list:
                            if not positions:
                                ui.label("No positions yet.").classes("help")
                            for i, pos in enumerate(positions):
                                with ui.row().classes("w-full items-center no-wrap gap-sm"):
                                    ui.label(
                                        f"{pos['symbol']}: €{pos['value']:,.0f} "
                                        f"(cost €{pos['cost']:,.0f})"
                                    ).classes("help").style("flex: 1")
                                    loss = pos["cost"] - pos["value"]
                                    if loss > 0:
                                        ui.label(f"−€{loss:,.0f} loss").classes("pstep-meta bad")
                                    rm = ui.button(icon="close").props(
                                        "flat round dense size=xs color=grey-6"
                                    )
                                    rm.on_click(lambda _, idx=i: remove_position(idx))

                    def remove_position(idx: int) -> None:
                        if 0 <= idx < len(positions):
                            positions.pop(idx)
                            refresh_positions()

                    def add_position() -> None:
                        symbol = (taxa_symbol.value or "").strip().upper()
                        if not symbol:
                            ui.notify("Enter a symbol.", type="warning")
                            return
                        positions.append(
                            {
                                "symbol": symbol,
                                "value": Decimal(str(taxa_value.value or 0)),
                                "cost": Decimal(str(taxa_cost.value or 0)),
                            }
                        )
                        refresh_positions()

                    add_position_btn.on_click(add_position)
                    refresh_positions()

                    tax_button = (
                        ui.button("Analyze taxes", icon="account_balance")
                        .props("color=teal outline dense")
                        .classes("q-mt-sm")
                        .mark("tax_analyze")
                    )
                    tax_results = ui.column().classes("w-full gap-sm q-mt-sm")

                    async def run_tax_analysis() -> None:
                        if not positions:
                            ui.notify("Add at least one position.", type="warning")
                            return
                        tax_button.disable()
                        try:
                            from app.services.tax_efficiency.tax_optimized_builder import (
                                TaxOptimizedPortfolioBuilder,
                            )

                            builder = TaxOptimizedPortfolioBuilder()
                            symbols = [p["symbol"] for p in positions]
                            total_value = sum(p["value"] for p in positions)
                            # equal-weight target for demonstration
                            target = {s: Decimal(1) / Decimal(len(symbols)) for s in symbols}
                            result = await builder.optimize_for_taxes(
                                base_allocation=target,
                                current_positions={p["symbol"]: p["value"] for p in positions},
                                cost_basis={p["symbol"]: p["cost"] for p in positions},
                                quantities={p["symbol"]: Decimal("1") for p in positions},
                                current_prices={p["symbol"]: Decimal("1") for p in positions},
                                marginal_tax_rate=Decimal("0.21"),
                                capital=total_value,
                            )
                        except Exception as exc:
                            tax_button.enable()
                            ui.notify(f"Tax analysis failed: {exc}", type="negative")
                            return
                        tax_button.enable()

                        tax_results.clear()
                        with tax_results:
                            if result.harvesting_opportunities:
                                with ui.row().classes("w-full gap-sm wrap"):
                                    _tax_tile(
                                        "Tax benefit", f"€{result.tax_benefit_estimated:,.0f}"
                                    )
                                    _tax_tile(
                                        "After-tax return",
                                        f"{result.after_tax_return_pct:.2f}%",
                                    )
                                    _tax_tile("Harvest", ", ".join(result.harvesting_opportunities))
                                ui.label("RECOMMENDED ADJUSTMENTS").classes("lbl q-mt-md q-mb-xs")
                                for adj in result.adjustments_made:
                                    ui.label(f"→ {adj}").classes("help")
                            else:
                                ui.label(
                                    "No tax harvesting opportunities found — "
                                    "your positions have no unrealized losses."
                                ).classes("help")

                    tax_button.on_click(run_tax_analysis)

        # ── Wire the optimizer ───────────────────────────────────────────
        async def run_optimize() -> None:
            from app.presentation.dashboard.nicegui_app.pages.swarm import (
                data_window,
                resolve_period,
            )
            from app.services.agent_swarm.optimizer import optimize as run_grid

            optimize_button.disable()
            optimize_status.text = "Searching… (uses the real engine, 1-2 min)"
            symbols = [str(s).upper() for s in (universo.value or [])] or ["AAPL", "MSFT", "GOOGL"]
            start_iso, end_iso = resolve_period(periodo.value, None, None, data_window(symbols))
            try:
                result = await asyncio.to_thread(
                    run_grid,
                    estrategia.value,
                    symbols,
                    start_iso,
                    end_iso,
                    Decimal("100000"),
                    12,
                )
            except Exception as exc:
                optimize_button.enable()
                optimize_status.text = f"Failed: {exc}"
                return
            optimize_button.enable()
            optimize_status.text = ""

            optimize_results.clear()
            with optimize_results:
                with ui.element("div").classes("panel q-pa-md w-full"):
                    ui.label("RESULTS").classes("lbl q-mb-sm")
                    with ui.row().classes("w-full gap-sm wrap"):
                        _tax_tile("Current return", f"{result.baseline.get('return_pct', '?')}%")
                        _tax_tile("Current Sharpe", str(result.baseline.get("sharpe", "?")))
                        _tax_tile("Best return", f"{result.best.get('return_pct', '?')}%")
                        _tax_tile("Best Sharpe", str(result.best.get("sharpe", "?")))
                    ui.label(f"Best parameters: {result.best_params}").classes("help q-mt-sm")
                    if result.improved:
                        adopt_btn = (
                            ui.button("Adopt best parameters", icon="check_circle")
                            .props("color=teal dense")
                            .classes("q-mt-sm")
                        )
                        adopt_btn.on_click(lambda: adopt_params(result))
                    else:
                        ui.label("Current parameters are already optimal in this grid.").classes(
                            "help q-mt-sm"
                        )

                    # trials table
                    if result.trials:
                        ui.label("ALL TRIALS").classes("lbl q-mt-md q-mb-xs")
                        for trial in result.trials:
                            with ui.row().classes("w-full items-center no-wrap gap-sm"):
                                ui.label(str(trial["params"])).classes("help").style(
                                    "flex: 1; min-width: 0"
                                )
                                ui.label(f"ret {trial.get('return_pct', '?')}%").classes(
                                    "pstep-meta"
                                )
                                ui.label(f"sharpe {trial.get('sharpe', '?')}").classes("pstep-meta")

            await refresh_param_history()

        async def adopt_params(result: Any) -> None:
            if store is None:
                ui.notify("Store not available.", type="warning")
                return
            await store.save_param_set(
                strategy=result.strategy,
                params=result.best_params,
                metrics={
                    "return_pct": str(result.best.get("return_pct", "")),
                    "sharpe": str(result.best.get("sharpe", "")),
                },
                source="optimizer",
                activate=True,
            )
            ui.notify("Parameters adopted — future runs will use them", type="positive")
            await refresh_param_history()

        async def refresh_param_history() -> None:
            if store is None:
                return
            try:
                sets = await store.list_param_sets()
            except Exception:
                return
            param_history.clear()
            if not sets:
                return
            with param_history:
                with ui.element("div").classes("panel q-pa-md w-full"):
                    ui.label("PARAMETER HISTORY").classes("lbl q-mb-xs")
                    for entry in sets[:8]:
                        with ui.row().classes("w-full items-center no-wrap gap-sm"):
                            ui.label("●" if entry["is_active"] else "○").classes(
                                "term-good" if entry["is_active"] else "help"
                            )
                            ui.label(f"{entry['strategy']} · {entry['params']}").classes(
                                "help"
                            ).style("flex: 1; min-width: 0")
                            ui.label(entry["created_at"][:16]).classes("help")
                            if not entry["is_active"]:
                                btn = ui.button("Restore", icon="history").props(
                                    "flat dense color=teal size=xs"
                                )
                                btn.on_click(lambda _, pid=entry["id"]: restore_params(pid))

        async def restore_params(param_set_id: int) -> None:
            if store is None:
                return
            await store.activate_param_set(param_set_id)
            ui.notify("Parameter set restored", type="positive")
            await refresh_param_history()

        optimize_button.on_click(run_optimize)
        ui.timer(0.1, refresh_param_history, once=True)


def _tax_tile(label: str, value: str) -> None:
    with ui.element("div").classes("metric-tile"):
        ui.label(label).classes("k")
        ui.label(value).classes("v")
