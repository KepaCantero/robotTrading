"""
BacktestRunner - Service that validates, runs, and persists backtest results.

Phase 2: Creates placeholder records with nil metrics.
Phase 3 (future): Integrates with the actual backtest engine to produce real results.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass

from app.infrastructure.persistence.backtest_result_store import (
    BacktestResultStore,
    BacktestRunRecord,
)

logger = logging.getLogger(__name__)

# Allowed time-window values.
_VALID_TIME_WINDOWS = frozenset({"1mo", "3mo", "6mo", "1y", "2y", "5y"})


@dataclass
class BacktestParams:
    """Input parameters for a backtest run."""

    strategy_name: str
    investor_profile: str | None = None
    time_window: str = "1y"  # "1mo", "3mo", "6mo", "1y", "2y", "5y"
    symbols: list[str] | None = None
    initial_capital: float = 100000.0


class BacktestRunner:
    """Wraps existing backtest engine and persists results."""

    def __init__(self, store: BacktestResultStore) -> None:
        self.store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, params: BacktestParams) -> BacktestRunRecord:
        """Run a backtest with given parameters and persist results.

        This is the main entry point. It:
        1. Validates params
        2. Creates a BacktestRunRecord with placeholder metrics
        3. Saves to store
        4. Returns the record

        Note: For Phase 2, the actual engine execution is a placeholder.
        The real engine integration happens in Phase 3 when we connect
        to the existing backtest engines.
        """
        errors = self.validate_params(params)
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        git_hash = self._capture_git_hash()
        config_snapshot = json.dumps(asdict(params))

        record = BacktestRunRecord(
            strategy_name=params.strategy_name,
            investor_profile=params.investor_profile,
            time_window=params.time_window,
            git_commit_hash=git_hash,
            config_snapshot=config_snapshot,
            # Phase 2 placeholder: all metrics are None
            total_return=None,
            sharpe_ratio=None,
            sortino_ratio=None,
            max_drawdown=None,
            win_rate=None,
            profit_factor=None,
            total_trades=None,
            full_results_json=None,
        )

        await self.store.save(record)
        logger.info(
            "Backtest run created: run_id=%s strategy=%s",
            record.run_id,
            record.strategy_name,
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
