"""
BacktestRunner - Service that validates, runs, and persists backtest results.

Runs the repo's REAL backtest engine (CSV candles → strategy signals →
BacktestEngine with commissions, slippage and t+1 execution) and persists
genuine metrics per run. Shares the same execution path as the Agent Swarm
pipeline (BacktestOrchestrator).
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from app.infrastructure.persistence.backtest_result_store import (
    BacktestResultStore,
    BacktestRunRecord,
)

logger = logging.getLogger(__name__)

# Allowed time-window values.
_VALID_TIME_WINDOWS = frozenset({"1mo", "3mo", "6mo", "1y", "2y", "5y"})
_WINDOW_DAYS = {"1mo": 31, "3mo": 92, "6mo": 183, "1y": 365, "2y": 730, "5y": 1825}

# Home-page strategy names map onto the orchestrator's real strategies.
_STRATEGY_MAP = {
    "mean_reversion": "mean_reversion",
    "momentum": "momentum_modular",
    "momentum_modular": "momentum_modular",
}


@dataclass
class BacktestParams:
    """Input parameters for a backtest run."""

    strategy_name: str
    investor_profile: str | None = None
    time_window: str = "1y"  # "1mo", "3mo", "6mo", "1y", "2y", "5y"
    symbols: list[str] | None = None
    initial_capital: float = 100000.0


class BacktestRunner:
    """Runs the real backtest engine and persists results."""

    def __init__(self, store: BacktestResultStore) -> None:
        self.store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, params: BacktestParams) -> BacktestRunRecord:
        """Run a REAL backtest with given parameters and persist results.

        1. Validates params
        2. Executes the real engine via BacktestOrchestrator
        3. Persists the genuine metrics
        """
        errors = self.validate_params(params)
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        engine_metrics = await self._execute_real_backtest(params)

        git_hash = self._capture_git_hash()
        config_snapshot = json.dumps(asdict(params))

        record = BacktestRunRecord(
            strategy_name=params.strategy_name,
            investor_profile=params.investor_profile,
            time_window=params.time_window,
            git_commit_hash=git_hash,
            config_snapshot=config_snapshot,
            total_return=engine_metrics.get("total_return"),
            sharpe_ratio=engine_metrics.get("sharpe_ratio"),
            sortino_ratio=engine_metrics.get("sortino_ratio"),
            max_drawdown=engine_metrics.get("max_drawdown"),
            win_rate=engine_metrics.get("win_rate"),
            profit_factor=engine_metrics.get("profit_factor"),
            total_trades=engine_metrics.get("total_trades"),
            full_results_json=json.dumps(engine_metrics, default=str),
        )

        await self.store.save(record)
        logger.info(
            "Backtest run created: run_id=%s strategy=%s trades=%s",
            record.run_id,
            record.strategy_name,
            record.total_trades,
        )
        return record

    def validate_params(self, params: BacktestParams) -> list[str]:
        """Validate params and return list of error messages (empty = valid)."""
        errors: list[str] = []

        # strategy_name must be non-empty (after stripping whitespace)
        if not params.strategy_name or not params.strategy_name.strip():
            errors.append("strategy_name must be a non-empty string")

        # time_window must be one of the allowed values
        if params.time_window not in _VALID_TIME_WINDOWS:
            errors.append(
                f"time_window must be one of {sorted(_VALID_TIME_WINDOWS)}, "
                f"got '{params.time_window}'"
            )

        # initial_capital must be positive
        if params.initial_capital <= 0:
            errors.append(f"initial_capital must be greater than 0, got {params.initial_capital}")

        # If symbols is provided, it must be a non-empty list
        if params.symbols is not None and len(params.symbols) == 0:
            errors.append("symbols list must not be empty when provided")

        return errors

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _execute_real_backtest(self, params: BacktestParams) -> dict:
        """Run the real engine through BacktestOrchestrator (shared with /swarm)."""
        from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator
        from app.services.backtest_orchestration.models import BacktestOrchestrationRequest

        end = date.today()
        start = end - timedelta(days=_WINDOW_DAYS.get(params.time_window, 365))
        request_symbols = params.symbols or ["AAPL", "MSFT", "GOOGL"]
        start, end = self._clamp_to_available_data(start, end, request_symbols)
        request = BacktestOrchestrationRequest(
            profile_id=f"home-{params.strategy_name}",
            input_id="home-runner",
            module_parameter_set_id="home",
            initial_capital=Decimal(str(params.initial_capital)),
            target_monthly_return_eur=(
                Decimal(str(params.initial_capital)) * Decimal("0.003")
            ).quantize(Decimal("1")),
            objective=(params.investor_profile or "maximizar_capital").lower(),
            risk_profile="moderate",
            start_date=start,
            end_date=end,
            strategy_name=_STRATEGY_MAP.get(params.strategy_name, "mean_reversion"),
            symbols=request_symbols,
        )

        result = await BacktestOrchestrator().orchestrate(request)

        if not result.success or result.backtest_result is None:
            raise RuntimeError(f"Real backtest failed: {result.error_message or 'unknown error'}")

        metrics = result.backtest_result.metrics
        if metrics is None:
            raise RuntimeError("Real backtest failed: no metrics available")
        return {
            "total_return": float(metrics.total_return_pct) / 100,
            "sharpe_ratio": float(metrics.sharpe_ratio),
            "sortino_ratio": float(metrics.sortino_ratio),
            "max_drawdown": float(metrics.max_drawdown_pct) / 100,
            "win_rate": float(metrics.win_rate_pct) / 100,
            "profit_factor": float(metrics.profit_factor),
            "total_trades": metrics.total_trades,
            "feasibility_ratio": str(result.feasibility_ratio),
            "feasibility_status": result.feasibility_status,
            "ending_capital": str(result.backtest_result.ending_capital),
        }

    @staticmethod
    def _clamp_to_available_data(start: date, end: date, symbols: list[str]) -> tuple[date, date]:
        """Clamp the requested window to the CSV data actually on disk."""
        earliest = latest = None
        for symbol in symbols:
            csv_path = Path("data/historical") / f"{symbol}.csv"
            if not csv_path.is_file():
                continue
            try:
                with csv_path.open() as handle:
                    handle.readline()  # header
                    first = handle.readline().split(",")[0]
                    last = ""
                    for line in handle:
                        if line.strip():
                            last = line
                day_first = date.fromisoformat(first.strip())
                day_last = date.fromisoformat(last.split(",")[0].strip())
            except (ValueError, OSError, IndexError):
                continue
            earliest = day_first if earliest is None else min(earliest, day_first)
            latest = day_last if latest is None else max(latest, day_last)
        if latest:
            end = min(end, latest)
        if earliest:
            start = max(min(start, end), earliest)
        if start >= end:
            start = end - timedelta(days=30)
        return start, end

    @staticmethod
    def _capture_git_hash() -> str | None:
        """Capture the short git commit hash with a fallback to None."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            return None
