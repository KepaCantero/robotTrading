"""Backtest Runner page - select parameters and run backtests.

Provides strategy/profile selection, time window picker, initial capital
input, and execution controls. Displays results with metric cards and
profitability verdict badge.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.metric_cards import metric_card
from app.presentation.dashboard.nicegui_app.components.profitability_badge import (
    profitability_badge,
)
from app.presentation.dashboard.nicegui_app.theme import COLORS

if TYPE_CHECKING:
    from app.infrastructure.persistence.backtest_result_store import BacktestResultStore
    from app.presentation.dashboard.profitability_engine import ProfitabilityEngine
    from app.services.backtest_runner import BacktestRunner

logger = logging.getLogger(__name__)

# ── Selector Options ──────────────────────────────────────────────────────────

_STRATEGY_OPTIONS = [
    "momentum",
    "mean_reversion",
    "pairs_trading",
    "multi_strategy",
]

_PROFILE_OPTIONS = [
    "maximizar_capital",
    "maximizar_dividendos",
    "capital_preservation",
    "balanced_growth",
    "income_generation",
]

_TIME_WINDOW_OPTIONS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

# ── Helpers ───────────────────────────────────────────────────────────────────


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


def _build_results_area(
    verdict_text: str,
    score: float,
    total_return: float | None,
    sharpe: float | None,
    max_dd: float | None,
    win_rate: float | None,
    profit_factor: float | None,
    total_trades: int | None,
    run_id: str,
) -> None:
    """Render the results area with badge, score, and metric cards."""
    ui.label("Backtest Results").classes("text-h6 q-mt-md")
    ui.label(f"Run ID: {run_id}").classes("text-caption text-grey")

    with ui.row().classes("items-center q-mt-sm q-mb-sm gap-md"):
        ui.label("Verdict:").classes("text-subtitle1")
        profitability_badge(verdict_text)
        ui.label(f"Score: {score:.1f} / 100").classes("text-subtitle1 font-bold").style(
            f"color: {COLORS['accent']}"
        )

    ui.separator().classes("q-mb-md")

    with ui.row().classes("w-full wrap gap-md"):
        metric_card(
            title="Total Return",
            value=_fmt_pct(total_return),
            subtitle="Net performance",
            color=COLORS["profit"] if total_return and total_return > 0 else COLORS["loss"],
        )
        metric_card(
            title="Sharpe Ratio",
            value=_fmt_float(sharpe),
            subtitle="Risk-adjusted return",
            color=COLORS["primary"],
        )
        metric_card(
            title="Max Drawdown",
            value=_fmt_pct(max_dd),
            subtitle="Worst peak-to-trough",
            color=COLORS["loss"],
        )
        metric_card(
            title="Win Rate",
            value=_fmt_pct(win_rate),
            subtitle="Winning trades / total",
            color=COLORS["primary"],
        )
        metric_card(
            title="Profit Factor",
            value=_fmt_float(profit_factor),
            subtitle="Gross profit / gross loss",
            color=COLORS["primary"],
        )
        metric_card(
            title="Total Trades",
            value=_fmt_int(total_trades),
            subtitle="Executed trades",
            color=COLORS["secondary"],
        )


# ── Page Render ───────────────────────────────────────────────────────────────


def render(
    store: BacktestResultStore | None,
    runner: BacktestRunner | None,
    profitability: ProfitabilityEngine | None,
) -> None:
    """Render the Backtest Runner page content."""
    with ui.column().classes("w-full q-pa-lg"):
        ui.label("Backtest Runner").classes("text-h4 q-mb-md")
        ui.label("Configure parameters and run a backtest.").classes("text-grey q-mb-lg")

        # ── Parameter Card ──────────────────────────────────────────────────
        with ui.card().classes("w-full q-pa-lg"):
            ui.label("Parameters").classes("text-h6 q-mb-md")

            with ui.row().classes("w-full wrap gap-lg"):
                with ui.column().classes("min-w-[200px]"):
                    ui.label("Strategy").classes("text-caption")
                    strategy_select = ui.select(
                        options=_STRATEGY_OPTIONS,
                        value=_STRATEGY_OPTIONS[0],
                        with_input=True,
                    ).classes("min-w-[220px]")

                with ui.column().classes("min-w-[200px]"):
                    ui.label("Investor Profile").classes("text-caption")
                    profile_select = ui.select(
                        options=_PROFILE_OPTIONS,
                        value=_PROFILE_OPTIONS[0],
                        with_input=True,
                    ).classes("min-w-[220px]")

                with ui.column().classes("min-w-[200px]"):
                    ui.label("Time Window").classes("text-caption")
                    time_window_select = ui.select(
                        options=_TIME_WINDOW_OPTIONS,
                        value="1y",
                    ).classes("min-w-[120px]")

                with ui.column().classes("min-w-[150px]"):
                    ui.label("Initial Capital").classes("text-caption")
                    capital_input = ui.number(
                        value=100000.0,
                        min=1000.0,
                        step=1000.0,
                        format="%.2f",
                    ).classes("min-w-[150px]")

            ui.separator().classes("q-mt-lg q-mb-md")

            run_button = (
                ui.button(
                    "Run Backtest",
                    icon="play_arrow",
                )
                .props("color=primary")
                .classes("q-mt-sm")
            )

        # ── Results Container (refreshable) ─────────────────────────────────
        results_container = ui.column().classes("w-full")

        async def _on_run() -> None:
            """Handle the Run Backtest button click."""
            if runner is None:
                ui.notify("BacktestRunner is not initialized.", type="warning")
                return

            strategy = strategy_select.value
            profile = profile_select.value
            window = time_window_select.value
            capital = capital_input.value

            if not strategy:
                ui.notify("Please select a strategy.", type="warning")
                return

            # Show spinner, disable button
            run_button.disable()
            results_container.clear()

            with results_container:
                ui.spinner("dots", size="xl").classes("q-mt-lg")
                ui.label("Running backtest...").classes("text-grey q-mt-sm")

            try:
                from app.services.backtest_runner import BacktestParams

                params = BacktestParams(
                    strategy_name=strategy,
                    investor_profile=profile,
                    time_window=window,
                    initial_capital=capital,
                )

                record = await runner.run(params)

                # Evaluate profitability
                verdict_text = "INCONCLUSIVE"
                score = 0.0
                if profitability is not None:
                    result = profitability.evaluate(record)
                    verdict_text = result.verdict
                    score = result.score

                # Replace spinner with results
                results_container.clear()
                with results_container:
                    _build_results_area(
                        verdict_text=verdict_text,
                        score=score,
                        total_return=record.total_return,
                        sharpe=record.sharpe_ratio,
                        max_dd=record.max_drawdown,
                        win_rate=record.win_rate,
                        profit_factor=record.profit_factor,
                        total_trades=record.total_trades,
                        run_id=record.run_id,
                    )

                ui.notify("Backtest completed!", type="positive")

            except ValueError as exc:
                results_container.clear()
                with results_container:
                    ui.label(f"Validation error: {exc}").classes("text-negative")
                ui.notify(str(exc), type="negative")
            except Exception as exc:
                logger.exception("Backtest run failed")
                results_container.clear()
                with results_container:
                    ui.label(f"Error: {exc}").classes("text-negative")
                ui.notify(f"Backtest failed: {exc}", type="negative")
            finally:
                run_button.enable()

        run_button.on_click(_on_run)
