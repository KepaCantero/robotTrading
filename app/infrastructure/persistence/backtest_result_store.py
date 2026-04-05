"""
BacktestResultStore - SQLite persistence for backtest run records.

Provides async CRUD operations and comparison for BacktestRunRecord objects.
Uses sqlite3 via aiosqlite for non-blocking database access.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path  # noqa: TC003 - used at runtime in __init__
from typing import Any
from uuid import uuid4

import aiosqlite
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id              TEXT PRIMARY KEY,
    timestamp           TEXT NOT NULL,
    strategy_name       TEXT NOT NULL,
    investor_profile    TEXT,
    time_window         TEXT NOT NULL DEFAULT '1y',
    git_commit_hash     TEXT,
    config_snapshot     TEXT,
    total_return        REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    max_drawdown        REAL,
    win_rate            REAL,
    profit_factor       REAL,
    total_trades        INTEGER,
    full_results_json   TEXT
)
"""

_INSERT_SQL = """
INSERT INTO backtest_runs (
    run_id, timestamp, strategy_name, investor_profile, time_window,
    git_commit_hash, config_snapshot,
    total_return, sharpe_ratio, sortino_ratio, max_drawdown,
    win_rate, profit_factor, total_trades,
    full_results_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_SELECT_BY_ID_SQL = """
SELECT
    run_id, timestamp, strategy_name, investor_profile, time_window,
    git_commit_hash, config_snapshot,
    total_return, sharpe_ratio, sortino_ratio, max_drawdown,
    win_rate, profit_factor, total_trades,
    full_results_json
FROM backtest_runs
WHERE run_id = ?
"""

_LIST_SQL = """
SELECT
    run_id, timestamp, strategy_name, investor_profile, time_window,
    git_commit_hash, config_snapshot,
    total_return, sharpe_ratio, sortino_ratio, max_drawdown,
    win_rate, profit_factor, total_trades,
    full_results_json
FROM backtest_runs
{where_clause}
ORDER BY timestamp DESC
LIMIT ?
"""

_DELETE_SQL = "DELETE FROM backtest_runs WHERE run_id = ?"

# Metric columns used for comparison.
_METRIC_COLUMNS = [
    "total_return",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "win_rate",
    "profit_factor",
    "total_trades",
]

_METADATA_COLUMNS = [
    "strategy_name",
    "time_window",
]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class BacktestRunRecord(BaseModel):
    """Persistence record for a single backtest run."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    strategy_name: str
    investor_profile: str | None = None
    time_window: str = "1y"
    git_commit_hash: str | None = None
    config_snapshot: str | None = None  # JSON string
    # Key metrics (nullable for incomplete runs)
    total_return: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown: float | None = None
    win_rate: float | None = None
    profit_factor: float | None = None
    total_trades: int | None = None
    # Full results blob
    full_results_json: str | None = None  # Serialized BacktestResult


# ---------------------------------------------------------------------------
# Row <-> Model helpers
# ---------------------------------------------------------------------------

_ROW_COLUMNS = [
    "run_id",
    "timestamp",
    "strategy_name",
    "investor_profile",
    "time_window",
    "git_commit_hash",
    "config_snapshot",
    "total_return",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "win_rate",
    "profit_factor",
    "total_trades",
    "full_results_json",
]


def _row_to_record(row: aiosqlite.Row) -> BacktestRunRecord:
    """Convert a database row to a BacktestRunRecord."""
    values = dict(zip(_ROW_COLUMNS, row))
    # Parse the ISO-format timestamp string back to datetime.
    ts = values["timestamp"]
    if isinstance(ts, str):
        values["timestamp"] = datetime.fromisoformat(ts)
    return BacktestRunRecord(**values)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class BacktestResultStore:
    """Async SQLite-backed store for BacktestRunRecord objects."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    # -- lifecycle -----------------------------------------------------------

    async def initialize(self) -> None:
        """Create the backtest_runs table if it does not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute(_CREATE_TABLE_SQL)
            await db.commit()
        logger.debug("BacktestResultStore initialized at %s", self.db_path)

    # -- CRUD ----------------------------------------------------------------

    async def save(self, run: BacktestRunRecord) -> str:
        """Persist a BacktestRunRecord. Returns the run_id."""
        run_id = run.run_id
        ts_iso = run.timestamp.isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                _INSERT_SQL,
                (
                    run_id,
                    ts_iso,
                    run.strategy_name,
                    run.investor_profile,
                    run.time_window,
                    run.git_commit_hash,
                    run.config_snapshot,
                    run.total_return,
                    run.sharpe_ratio,
                    run.sortino_ratio,
                    run.max_drawdown,
                    run.win_rate,
                    run.profit_factor,
                    run.total_trades,
                    run.full_results_json,
                ),
            )
            await db.commit()
        logger.debug("Saved backtest run %s", run_id)
        return run_id

    async def get(self, run_id: str) -> BacktestRunRecord | None:
        """Retrieve a single run by run_id, or None if not found."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(_SELECT_BY_ID_SQL, (run_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_record(tuple(row))

    async def list_runs(
        self,
        limit: int = 50,
        strategy: str | None = None,
    ) -> list[BacktestRunRecord]:
        """Return runs sorted by timestamp descending.

        Parameters
        ----------
        limit:
            Maximum number of records to return (default 50).
        strategy:
            If provided, filter to runs matching this strategy name.
        """
        where_clause = ""
        params: list[Any] = []

        if strategy is not None:
            where_clause = "WHERE strategy_name = ?"
            params.append(strategy)

        params.append(limit)

        sql = _LIST_SQL.format(where_clause=where_clause)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            return [_row_to_record(tuple(r)) for r in rows]

    async def delete(self, run_id: str) -> bool:
        """Delete a run by run_id. Returns True if a row was deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(_DELETE_SQL, (run_id,))
            await db.commit()
            return cursor.rowcount > 0

    # -- comparison ----------------------------------------------------------

    async def compare(self, run_id_a: str, run_id_b: str) -> dict | None:
        """Compare key metrics between two runs.

        Returns a dict mapping metric names to ``{a, b, delta}`` dicts,
        or None if either run does not exist.
        """
        record_a = await self.get(run_id_a)
        record_b = await self.get(run_id_b)

        if record_a is None or record_b is None:
            return None

        diff: dict[str, Any] = {}

        for col in _METRIC_COLUMNS:
            val_a = getattr(record_a, col, None)
            val_b = getattr(record_b, col, None)

            if val_a is not None and val_b is not None:
                delta: Any = val_b - val_a
            else:
                delta = None

            diff[col] = {"a": val_a, "b": val_b, "delta": delta}

        for col in _METADATA_COLUMNS:
            val_a = getattr(record_a, col, None)
            val_b = getattr(record_b, col, None)
            diff[col] = {"a": val_a, "b": val_b}

        return diff
