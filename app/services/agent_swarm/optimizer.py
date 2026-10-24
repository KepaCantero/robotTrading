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
    # re-balance (más frecuente = más coste sin señal que lo justifique)
    "static_ew": {
        "rebalance_days": [126, 252, 365],
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


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


def optimize(
    strategy: str,
    symbols: list[str],
    start: str,
    end: str,
    capital: Decimal = Decimal("100000"),
    max_trials: int = 12,
) -> OptimizationResult:
    """Grid-search the strategy's tunable params with the real engine."""
    grid = PARAM_GRIDS.get(strategy)
    if not grid:
        raise ValueError(f"No tunable parameters defined for strategy '{strategy}'")

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    _base = default_params(strategy)

    # baseline with current/default params
    baseline_metrics = _run_one_backtest(strategy, {}, symbols, start_date, end_date, capital)

    combos = list(itertools.product(*grid.values()))
    combos = combos[:max_trials]
    keys = list(grid.keys())

    trials: list[dict] = []
    for combo in combos:
        params = dict(zip(keys, combo, strict=False))
        logger.info("Optimizer trial %s: %s", strategy, params)
        metrics = _run_one_backtest(strategy, params, symbols, start_date, end_date, capital)
        trials.append(
            {
                "params": params,
                **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in metrics.items()},
            }
        )

    def score(metrics: dict) -> float:
        try:
            return float(metrics.get("sharpe") or -999)
        except (TypeError, ValueError):
            return -999.0

    best_trial = max(trials, key=score) if trials else None
    best_metrics = None  # se recalcula abajo con los mejores parámetros
    # rerun best params to get clean metrics dict (trials store strings)
    if best_trial:
        best_params = dict(best_trial["params"])
        best_metrics = _run_one_backtest(
            strategy, best_params, symbols, start_date, end_date, capital
        )
    else:
        best_params, best_metrics = {}, baseline_metrics

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
