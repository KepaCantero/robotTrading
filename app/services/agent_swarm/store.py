"""SQLite persistence for agent-swarm runs.

Stores one row per run plus every emitted event, so past missions can be
listed and replayed in the Mission Control dashboard even when it was not
open while they ran. Shared by the API process and the dashboard process
(same file, WAL journaling).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from app.services.agent_swarm.events import AgentEvent

logger = logging.getLogger(__name__)

DEFAULT_SWARM_DB_PATH = str(Path(__file__).resolve().parents[3] / "swarm_runs.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS swarm_runs (
    workflow_id     TEXT PRIMARY KEY,
    status          TEXT NOT NULL,
    request_json    TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    total_xp        INTEGER NOT NULL DEFAULT 0,
    achievements_json TEXT NOT NULL DEFAULT '[]',
    results_json    TEXT
);
CREATE TABLE IF NOT EXISTS swarm_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id  TEXT NOT NULL,
    ts           TEXT NOT NULL,
    type         TEXT NOT NULL,
    agent_id     TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_swarm_events_run ON swarm_events(workflow_id);
"""


class SwarmRunStore:
    """Async SQLite store for swarm runs and their events."""

    def __init__(self, db_path: str = DEFAULT_SWARM_DB_PATH) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    @property
    def is_initialized(self) -> bool:
        return self._db is not None

    async def initialize(self) -> None:
        if self._db is not None:
            return
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        logger.info("SwarmRunStore initialized at %s", self.db_path)

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    def _require_db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("SwarmRunStore not initialized; call initialize() first")
        return self._db

    # ── Runs ─────────────────────────────────────────────────────────────────

    async def create_run(self, workflow_id: str, request: dict, started_at: str) -> None:
        db = self._require_db()
        await db.execute(
            "INSERT OR REPLACE INTO swarm_runs "
            "(workflow_id, status, request_json, started_at) VALUES (?, ?, ?, ?)",
            (workflow_id, "running", json.dumps(request, default=str), started_at),
        )
        await db.commit()

    async def finish_run(
        self,
        workflow_id: str,
        status: str,
        finished_at: str,
        total_xp: int = 0,
        achievements: list[dict] | None = None,
        results: dict | None = None,
    ) -> None:
        db = self._require_db()
        await db.execute(
            "UPDATE swarm_runs SET status = ?, finished_at = ?, total_xp = ?, "
            "achievements_json = ?, results_json = ? WHERE workflow_id = ?",
            (
                status,
                finished_at,
                total_xp,
                json.dumps(achievements or [], default=str),
                json.dumps(results or {}, default=str),
                workflow_id,
            ),
        )
        await db.commit()

    async def count_runs(self) -> int:
        db = self._require_db()
        cursor = await db.execute("SELECT COUNT(*) FROM swarm_runs")
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        db = self._require_db()
        cursor = await db.execute(
            "SELECT workflow_id, status, request_json, started_at, finished_at, "
            "total_xp, achievements_json FROM swarm_runs "
            "ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        runs = []
        for row in rows:
            runs.append(
                {
                    "workflow_id": row[0],
                    "status": row[1],
                    "request": _load_json(row[2]),
                    "started_at": row[3],
                    "finished_at": row[4],
                    "total_xp": row[5],
                    "achievements": _load_json(row[6]),
                }
            )
        return runs

    # ── Events ───────────────────────────────────────────────────────────────

    async def append_event(self, event: AgentEvent) -> None:
        db = self._require_db()
        await db.execute(
            "INSERT INTO swarm_events (workflow_id, ts, type, agent_id, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                event.run_id,
                event.timestamp,
                event.type,
                event.agent_id,
                json.dumps(event.payload, default=str, ensure_ascii=False),
            ),
        )
        await db.commit()

    async def get_run_events(self, workflow_id: str) -> list[dict[str, Any]]:
        db = self._require_db()
        cursor = await db.execute(
            "SELECT ts, type, agent_id, payload_json FROM swarm_events "
            "WHERE workflow_id = ? ORDER BY id ASC",
            (workflow_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": row[0],
                "type": row[1],
                "agent_id": row[2],
                "payload": _load_json(row[3]),
            }
            for row in rows
        ]


def _load_json(text: str | None) -> Any:
    if not text:
        return {}
    try:
        return json.loads(text)
    except ValueError:
        return {"__raw__": str(text)[:500]}
