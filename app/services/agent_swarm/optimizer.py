"""Strategy parameter optimizer for the Agent Swarm dashboard.

Runs small grid searches over a strategy's tunable parameters using the REAL
backtest path (same engine the pipeline uses), then reports the best combo
against the current baseline so the user can decide whether to adopt it.
Adopted parameter sets are persisted to SQLite (history, restorable).
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Tunable parameter grids per strategy (novice-safe: few knobs, sane ranges).
PARAM_GRIDS: dict[str, dict[str, list[Any]]] = {
    "mean_reversion": {
        "z_score_threshold": [0.75, 1.0, 1.25, 1.5],
        "lookback_period": [10, 20, 30],
    },
    "momentum_modular": {
        "lookback_period": [10, 20, 30],
    },
    # bracketing the 2016-2026 sweep winner (semiannual rebalance, hysteresis
    # ±2% on satellites, deep-bear-only core guard) so the grid search
    # explores its neighbourhood
    "dividend_tracking": {
        "rebalance_days": [63, 126, 189],
        "skip_recent_days": [21, 42, 63],
        "satellite_exit_momentum": [-0.05, -0.02, 0.0],
        "satellite_top_k": [1, 2, 3],
    },
    "low_volatility": {
        "lookback_days": [63, 126, 252],
        "rebalance_days": [21, 63, 126],
        "top_k": [3, 4, 5],
    },
    # el pasivo solo tiene UN grado de libertad honesto: la cadencia de
    # re-balance. En ventanas tendenciales con dispersión (SCHD +253%
    # 2016-2026) recortar al ganador cada año COSTÓ 30 pp — el extremo
    # "no tocarlo" (730/3650 días) debe estar en el menú, no solo cadencias
    # más frecuentes que la anual.
    "static_ew": {
        "rebalance_days": [252, 365, 730, 3650],
    },
    # dos-fondos: el reparto equity/bondo se BUSCA (owner 31-10: "debería
    # buscarme tú el mejor peso para mi edad"). El ejecutor recorta este
    # grid al cap del perfil de riesgo (BAJO 0.60 / MEDIO 0.75 / ALTO 0.90)
    # antes de llamar — la edad/riesgo acota la búsqueda, la historia elige.
    "static_weighted": {
        "equity_weight": [0.3, 0.45, 0.6, 0.75, 0.9],
    },
    # pares: la ventana del spread y cuán extremo debe ser el z-score
    "pairs_trading": {
        "lookback_period": [30, 60, 120],
        "min_spread_z_score": [1.5, 2.0, 2.5],
    },
}

# Parameters the strategies accept directly in their config dict (fallback
# branch of MeanReversionStrategy etc.). Anything outside the YAML file's
# `parameters` is fair game via config kwargs.
_STRATEGY_DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "mean_reversion": {
        "z_score_threshold": 1.0,
        "lookback_period": 20,
        "mean_reversion_speed": 0.1,
        "volatility_threshold": 0.02,
        "atr_floor": 0.002,
        "price_range_multiplier": 0.02,
    },
    "momentum_modular": {},
}


@dataclass
class OptimizationResult:
    """Outcome of one optimization run."""

    strategy: str
    symbols: list[str]
    start: str
    end: str
    baseline: dict  # metrics with current/default params
    trials: list[dict]  # [{params, trades, return_pct, sharpe}]
    best_params: dict
    best: dict  # metrics of best combo
    improved: bool


def default_params(strategy: str) -> dict[str, Any]:
    base = dict(_STRATEGY_DEFAULT_PARAMS.get(strategy, {}))
    try:
        import yaml

        yaml_path = Path("config/strategies") / f"{strategy.replace('_modular', '')}.yaml"
        if yaml_path.exists():
            loaded = yaml.safe_load(yaml_path.read_text()) or {}
            base.update(loaded.get("parameters") or {})
    except Exception:  # noqa: BLE001 - defaults are enough
        pass
    return base


def _run_one_backtest(
    strategy: str,
    params: dict[str, Any],
    symbols: list[str],
    start: date,
    end: date,
    capital: Decimal,
) -> dict:
    """One REAL backtest with the given strategy params (shared engine path)."""
    from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator
    from app.services.backtest_orchestration.models import BacktestOrchestrationRequest

    orchestrator = BacktestOrchestrator()
    # inject strategy params through the module-level patch point used by
    # _build_strategy: it merges our dict into the strategy config
    orchestrator._strategy_param_overrides = params  # noqa: SLF001

    request = BacktestOrchestrationRequest(
        profile_id="optimizer",
        input_id="optimizer",
        module_parameter_set_id="optimizer",
        initial_capital=capital,
        target_monthly_return_eur=(capital * Decimal("0.003")).quantize(Decimal("1")),
        objective="maximizar_capital",
        risk_profile="moderate",
        start_date=start,
        end_date=end,
        strategy_name=strategy,
        symbols=symbols,
    )
    result = asyncio_run(orchestrator.orchestrate(request))
    if not result.success or result.backtest_result is None:
        return {
            "trades": 0,
            "return_pct": Decimal("-999"),
            "sharpe": Decimal("-999"),
            "error": result.error_message,
        }
    metrics = result.backtest_result.metrics
    return {
        "trades": metrics.total_trades,
        "return_pct": metrics.total_return_pct,
        "sharpe": metrics.sharpe_ratio,
        "drawdown_pct": metrics.max_drawdown_pct,
        "win_rate_pct": metrics.win_rate_pct,
    }


def _stratified_combos(combos: list[tuple], max_trials: int) -> list[tuple]:
    """D11: evenly spaced combos across the product so EVERY axis value
    gets explored. The old ``combos[:max_trials]`` only ever saw the first
    value of the leading axis (12 trials never left rebalance_days=63)."""
    if len(combos) <= max_trials or max_trials <= 0:
        return combos
    span = len(combos) - 1
    step = span / (max_trials - 1) if max_trials > 1 else 0
    picked: list[tuple] = []
    for i in range(max_trials):
        combo = combos[round(i * step)]
        if combo not in picked:
            picked.append(combo)
    return picked


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


def _trial_worker(payload: tuple) -> tuple[int, dict]:
    """Process-pool worker: one REAL backtest trial.

    Module-level (picklable) with a flat payload — each worker builds its
    OWN orchestrator, so the ComplianceEngine/live-gate singletons stay
    isolated per process (the D05-era gate reset races disappear).
    """
    index, strategy, params, symbols, start_date, end_date, capital = payload
    metrics = _run_one_backtest(strategy, params, symbols, start_date, end_date, capital)
    return index, metrics


def optimize(
    strategy: str,
    symbols: list[str],
    start: str,
    end: str,
    capital: Decimal = Decimal("100000"),
    max_trials: int = 12,
    parallel: bool = True,
    baseline_params: dict[str, Any] | None = None,
    grid: dict[str, list[Any]] | None = None,
) -> OptimizationResult:
    """Grid-search the strategy's tunable params with the real engine.

    Trials run in a ProcessPoolExecutor (stdlib; workers=min(4, cpu-1,
    combos)) with a sequential fallback — one engine, same results, just
    less wall time. The engine is deterministic, so the best trial's RAW
    metrics are reused instead of re-running the best combo a 13th time.

    ``baseline_params`` (30-10): the params the run ACTUALLY used (T3.1
    overrides + the adopted default) — the baseline backtest runs with
    them so "current" is the truth, not the YAML defaults. Trials still
    explore the full grid on top of ``default_params``.
    ``grid`` (31-10): an explicit grid overriding PARAM_GRIDS — the
    executor uses it to cap static_weighted's equity_weight search at
    the run's risk profile.
    """
    grid = grid or PARAM_GRIDS.get(strategy)
    if not grid:
        raise ValueError(f"No tunable parameters defined for strategy '{strategy}'")

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    # baseline with the params the run really used (or YAML defaults)
    baseline_metrics = _run_one_backtest(
        strategy, dict(baseline_params or {}), symbols, start_date, end_date, capital
    )

    combos = list(itertools.product(*grid.values()))
    combos = _stratified_combos(combos, max_trials)
    keys = list(grid.keys())

    params_by_combo = [dict(zip(keys, combo, strict=False)) for combo in combos]
    raw_results: list[dict | None] = [None] * len(combos)

    if parallel and len(combos) > 1:
        try:
            import os
            from concurrent.futures import ProcessPoolExecutor

            workers = max(1, min(4, (os.cpu_count() or 2) - 1, len(combos)))
            payloads = [
                (i, strategy, params_by_combo[i], symbols, start_date, end_date, capital)
                for i in range(len(combos))
            ]
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for index, metrics in pool.map(_trial_worker, payloads):
                    raw_results[index] = metrics
        except Exception:  # noqa: BLE001 - pool unavailable → sequential, loudly
            logger.warning(
                "Parallel trials unavailable — falling back to sequential", exc_info=True
            )
            raw_results = [None] * len(combos)

    # sequential path: fills whatever the pool left (fallback or leftovers)
    for i in range(len(combos)):
        if raw_results[i] is None:
            logger.info("Optimizer trial %s: %s", strategy, params_by_combo[i])
            raw_results[i] = _run_one_backtest(
                strategy, params_by_combo[i], symbols, start_date, end_date, capital
            )

    trials: list[dict] = [
        {
            "params": params_by_combo[i],
            **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in raw_results[i].items()},
        }
        for i in range(len(combos))
    ]

    def score(metrics: dict) -> float:
        try:
            return float(metrics.get("sharpe") or -999)
        except (TypeError, ValueError):
            return -999.0

    # GATE Fase B: the engine is deterministic — the best trial's RAW
    # metrics ARE the best metrics; the 13th re-run was pure waste.
    best_index = max(range(len(combos)), key=lambda i: score(raw_results[i]))
    best_params = params_by_combo[best_index]
    best_metrics = raw_results[best_index]

    return OptimizationResult(
        strategy=strategy,
        symbols=symbols,
        start=start,
        end=end,
        baseline={
            k: (str(v) if isinstance(v, Decimal) else v) for k, v in baseline_metrics.items()
        },
        trials=trials,
        best_params=best_params,
        best={k: (str(v) if isinstance(v, Decimal) else v) for k, v in best_metrics.items()},
        improved=score(best_metrics) > score(baseline_metrics),
    )
