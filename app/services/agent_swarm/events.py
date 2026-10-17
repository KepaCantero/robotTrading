"""Event model and in-process pub/sub bus for agent-swarm executions.

Every stage transition in a swarm run (start, completion, failure, skip,
achievement) is published as an :class:`AgentEvent`. Subscribers get an
``asyncio.Queue`` each; publishing never blocks the pipeline — a full queue
drops its oldest item to make room.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

# ── Event types ────────────────────────────────────────────────────────────────

RUN_STARTED = "run_started"
STAGE_STARTED = "stage_started"
STAGE_COMPLETED = "stage_completed"
STAGE_FAILED = "stage_failed"
STAGE_SKIPPED = "stage_skipped"
ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
RUN_COMPLETED = "run_completed"
RUN_FAILED = "run_failed"

EVENT_TYPES = (
    RUN_STARTED,
    STAGE_STARTED,
    STAGE_COMPLETED,
    STAGE_FAILED,
    STAGE_SKIPPED,
    ACHIEVEMENT_UNLOCKED,
    RUN_COMPLETED,
    RUN_FAILED,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentEvent:
    """A single execution event emitted by the swarm executor."""

    type: str
    run_id: str
    agent_id: str | None = None
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentEvent:
        return cls(
            type=data["type"],
            run_id=data["run_id"],
            agent_id=data.get("agent_id"),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", _utcnow_iso()),
        )


class AgentEventBus:
    """Minimal in-process pub/sub for agent events.

    ``subscribe()`` returns a queue the caller owns; ``unsubscribe(q)`` stops
    delivery. ``publish`` is synchronous and non-blocking.
    """

    def __init__(self, queue_size: int = 500, history_size: int = 200) -> None:
        self._queue_size = queue_size
        self._subscribers: list[asyncio.Queue] = []
        self._recent: deque[AgentEvent] = deque(maxlen=history_size)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @property
    def recent_events(self) -> list[AgentEvent]:
        return list(self._recent)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def publish(self, event: AgentEvent) -> None:
        self._recent.append(event)
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop the oldest item: the dashboard lags, the pipeline must not.
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:  # pragma: no cover - race with consumer
                    pass
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:  # pragma: no cover - extremely unlikely
                    pass
