from __future__ import annotations

"""
Persistent Task Queue Implementation for AlgoTrading System.

This module implements a robust, persistent task queue that survives restarts
and provides comprehensive task lifecycle management for 24/7 trading operations.
"""

import asyncio
import contextlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 300.0) -> float:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds with exponential backoff
    """
    delay: float = base_delay * float(2**attempt)
    return min(delay, max_delay)


def serialize_datetime(dt: datetime | None) -> str | None:
    """Serialize datetime to ISO format string."""
    return dt.isoformat() if dt else None


def deserialize_datetime(dt_str: str | None) -> datetime | None:
    """Deserialize ISO format string to datetime."""
    return datetime.fromisoformat(dt_str) if dt_str else None


def serialize_value(
    value: str | int | float | bool | Decimal | datetime | date | Enum | dict | list | None,
) -> str | int | float | bool | list | dict | None:
    """Serialize complex types to JSON-compatible values."""
    if isinstance(value, datetime):
        return serialize_datetime(value)
    if isinstance(value, date):
        return serialize_datetime(datetime.combine(value, datetime.min.time()))
    if isinstance(value, Decimal):
        return str(value)  # Store as string to preserve precision
    if isinstance(value, Enum):
        enum_val: str | int = value.value
        return enum_val
    if hasattr(value, "__dict__"):
        return value.__dict__
    return value


def deserialize_payload(
    payload: dict[str, str | int | float | bool | None],
) -> dict[str, str | int | float | bool | datetime | Decimal | None]:
    """Deserialize payload values to their original types."""
    result: dict[str, str | int | float | bool | datetime | Decimal | None] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            # Try to parse as datetime
            try:
                result[key] = datetime.fromisoformat(value)
                continue
            except (ValueError, AttributeError):
                pass
            # Try to parse as Decimal (only if it looks like a number)
            with contextlib.suppress(ValueError, TypeError, AttributeError):
                # Check if string looks like a number first
                if value.replace(".", "", 1).replace("-", "", 1).isdigit() or (
                    value.startswith("-")
                    and value[1:].replace(".", "", 1).replace("+", "").isdigit()
                ):
                    result[key] = Decimal(str(value))
                    continue
        result[key] = value
    return result


@dataclass
class Task:
    """
    A persistent task that can be stored and recovered from the database.

    Attributes:
        task_id: Unique task identifier
        name: Human-readable task name
        payload: Task data/parameters (JSON-serializable)
        priority: Task priority level
        status: Current task status
        created_at: Task creation timestamp
        started_at: Task start timestamp
        completed_at: Task completion timestamp
        expires_at: Task expiration timestamp
        retry_count: Number of retry attempts
        max_retries: Maximum number of retry attempts
        result: Task execution result (JSON-serializable)
        error: Error message if task failed
        next_retry_at: Timestamp for next retry attempt
    """

    task_id: str
    name: str
    payload: dict[str, str | int | float | bool | Decimal | datetime | None]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    result: str | int | float | bool | dict | list | None | None = None
    error: str | None = None
    next_retry_at: datetime | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        """Convert task to dictionary for database storage."""
        data: dict[str, str | int | None] = {
            "task_id": self.task_id,
            "name": self.name,
            "payload": json.dumps({k: serialize_value(v) for k, v in self.payload.items()}),
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": serialize_datetime(self.created_at),
            "started_at": serialize_datetime(self.started_at),
            "completed_at": serialize_datetime(self.completed_at),
            "expires_at": serialize_datetime(self.expires_at),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": json.dumps(serialize_value(self.result)) if self.result is not None else None,
            "error": self.error,
            "next_retry_at": serialize_datetime(self.next_retry_at),
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, str | int | None]) -> Task:
        """Create task from database dictionary."""
        raw_payload = data.get("payload")
        payload: dict[str, str | int | float | bool | None]
        if isinstance(raw_payload, str):
            loaded = json.loads(raw_payload)
            payload = loaded if isinstance(loaded, dict) else {}
        else:
            payload = {}

        raw_result = data.get("result")
        task_result: str | int | float | bool | dict | list | None = None
        if isinstance(raw_result, str):
            loaded_result = json.loads(raw_result)
            if isinstance(loaded_result, dict):
                task_result = deserialize_payload(loaded_result)
            else:
                task_result = loaded_result

        # Extract required fields with proper types
        priority_val = data["priority"]
        if not isinstance(priority_val, int):
            priority_val = int(str(priority_val))
        retry_count_val = data["retry_count"]
        if not isinstance(retry_count_val, int):
            retry_count_val = int(str(retry_count_val))
        max_retries_val = data["max_retries"]
        if not isinstance(max_retries_val, int):
            max_retries_val = int(str(max_retries_val))
        created_at_val = data["created_at"]
        if not isinstance(created_at_val, str):
            created_at_val = str(created_at_val)

        created_at_dt = deserialize_datetime(created_at_val)
        if created_at_dt is None:
            created_at_dt = datetime.now(timezone.utc)

        return cls(
            task_id=str(data["task_id"]),
            name=str(data["name"]),
            payload=deserialize_payload(payload),
            priority=TaskPriority(priority_val),
            status=TaskStatus(str(data["status"])),
            created_at=created_at_dt,
            started_at=(
                deserialize_datetime(str(data.get("started_at")))
                if data.get("started_at") is not None
                else None
            ),
            completed_at=(
                deserialize_datetime(str(data.get("completed_at")))
                if data.get("completed_at") is not None
                else None
            ),
            expires_at=(
                deserialize_datetime(str(data.get("expires_at")))
                if data.get("expires_at") is not None
                else None
            ),
            retry_count=retry_count_val,
            max_retries=max_retries_val,
            result=task_result,
            error=str(data.get("error")) if data.get("error") is not None else None,
            next_retry_at=(
                deserialize_datetime(str(data.get("next_retry_at")))
                if data.get("next_retry_at") is not None
                else None
            ),
        )

    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def is_expired(self) -> bool:
        """Check if task has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def can_process(self) -> bool:
        """Check if task can be processed."""
        if self.status != TaskStatus.PENDING:
            return False
        if self.is_expired():
            return False
        return not (self.next_retry_at and datetime.now(timezone.utc) < self.next_retry_at)


class PersistentTaskQueue:
    """
    Persistent task queue that survives restarts.

    This queue provides robust task management for 24/7 trading operations
    with features like priority handling, expiration, retries, and dead letter queue.
    """

    def __init__(
        self,
        db_path: str = "data/task_queue.db",
        logger: logging.Logger | None = None,
    ):
        """
        Initialize task queue with database path.

        Args:
            db_path: Path to SQLite database file
            logger: Optional logger instance
        """
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        self._running = False
        self._processing_tasks: dict[str, asyncio.Task] = {}

    async def initialize(self) -> None:
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    expires_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    result TEXT,
                    error TEXT,
                    next_retry_at TEXT
                )
            """)
            # Create indexes for common queries
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_status_priority ON tasks(status, priority DESC)"
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_next_retry ON tasks(next_retry_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON tasks(expires_at)")
            await db.commit()

    async def enqueue(self, task: Task) -> str:
        """
        Add task to persistent queue.

        Args:
            task: Task to enqueue

        Returns:
            Task ID
        """
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            data = task.to_dict()
            await db.execute(
                """
                    INSERT INTO tasks (
                        task_id, name, payload, priority, status,
                        created_at, started_at, completed_at, expires_at,
                        retry_count, max_retries, result, error, next_retry_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["task_id"],
                    data["name"],
                    data["payload"],
                    data["priority"],
                    data["status"],
                    data["created_at"],
                    data["started_at"],
                    data["completed_at"],
                    data["expires_at"],
                    data["retry_count"],
                    data["max_retries"],
                    data["result"],
                    data["error"],
                    data["next_retry_at"],
                ),
            )
            await db.commit()

        self.logger.info(
            f"Task {task.task_id} ({task.name}) enqueued with priority {task.priority.name}"
        )
        return task.task_id

    async def dequeue(self) -> Task | None:
        """
        Get next task to process (priority-ordered).

        Returns:
            Next task or None if queue is empty
        """
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            # Get highest priority pending task that can be processed
            cursor = await db.execute(
                """
                    SELECT * FROM tasks
                    WHERE status = ?
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                """,
                (TaskStatus.PENDING.value,),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            # Convert row to dict
            columns = [
                "task_id",
                "name",
                "payload",
                "priority",
                "status",
                "created_at",
                "started_at",
                "completed_at",
                "expires_at",
                "retry_count",
                "max_retries",
                "result",
                "error",
                "next_retry_at",
            ]
            data = dict(zip(columns, row))
            task = Task.from_dict(data)

            # Check if task can be processed
            if not task.can_process():
                return None

            # Mark as processing
            now = datetime.now(timezone.utc)
            await self._update_status_started(
                db,
                task.task_id,
                TaskStatus.PROCESSING,
                started_at=now,
            )
            await db.commit()

            # Update task object to reflect new status
            task.status = TaskStatus.PROCESSING
            task.started_at = now

        self.logger.debug(f"Dequeued task {task.task_id} ({task.name})")
        return task

    async def _update_status_started(
        self,
        db: aiosqlite.Connection,
        task_id: str,
        status: TaskStatus,
        started_at: datetime,
    ) -> None:
        """Update task status to processing with started_at timestamp."""
        await db.execute(
            "UPDATE tasks SET status = ?, started_at = ? WHERE task_id = ?",
            (status.value, serialize_datetime(started_at), task_id),
        )

    async def _update_status_completed(
        self,
        db: aiosqlite.Connection,
        task_id: str,
        status: TaskStatus,
        completed_at: datetime,
        result: str | None = None,
    ) -> None:
        """Update task status to completed with completed_at and optional result."""
        await db.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, result = ? WHERE task_id = ?",
            (status.value, serialize_datetime(completed_at), result, task_id),
        )

    async def _update_status_simple(
        self,
        db: aiosqlite.Connection,
        task_id: str,
        status: TaskStatus,
        completed_at: datetime,
    ) -> None:
        """Update task status with completed_at timestamp (for expired/cancelled)."""
        await db.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE task_id = ?",
            (status.value, serialize_datetime(completed_at), task_id),
        )

    async def complete_task(
        self, task_id: str, result: str | int | float | bool | dict | list | None = None
    ) -> None:
        """
        Mark task as completed.

        Args:
            task_id: Task ID
            result: Task execution result
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Serialize result to JSON string
            result_str: str | None = None
            if result is not None:
                if isinstance(result, dict):
                    # For dict, serialize values then JSON encode
                    serialized_dict = {k: serialize_value(v) for k, v in result.items()}
                    result_str = json.dumps(serialized_dict)
                elif isinstance(result, list):
                    # For list, serialize values then JSON encode
                    serialized_list = [serialize_value(v) for v in result]
                    result_str = json.dumps(serialized_list)
                else:
                    # For simple types, serialize and JSON encode
                    result_str = json.dumps(serialize_value(result))

            await self._update_status_completed(
                db,
                task_id,
                TaskStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                result=result_str,
            )
            await db.commit()

        self.logger.info(f"Task {task_id} completed successfully")

    async def fail_task(
        self,
        task_id: str,
        error: str,
        retry_count: int | None = None,
    ) -> None:
        """
        Mark task as failed.

        Args:
            task_id: Task ID
            error: Error message
            retry_count: Updated retry count
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Get current task data
            cursor = await db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = await cursor.fetchone()

            if not row:
                self.logger.warning(f"Task {task_id} not found")
                return

            columns = [
                "task_id",
                "name",
                "payload",
                "priority",
                "status",
                "created_at",
                "started_at",
                "completed_at",
                "expires_at",
                "retry_count",
                "max_retries",
                "result",
                "error",
                "next_retry_at",
            ]
            data = dict(zip(columns, row))
            task = Task.from_dict(data)

            # Update retry count if provided
            if retry_count is not None:
                task.retry_count = retry_count
            else:
                task.retry_count += 1

            # Determine if task should be retried
            # A task can retry if retry_count < max_retries
            can_retry = task.retry_count < task.max_retries

            if can_retry:
                next_delay = exponential_backoff(task.retry_count - 1)
                task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=next_delay)
                task.status = TaskStatus.PENDING
                self.logger.info(
                    f"Task {task_id} will retry in {next_delay:.1f}s "
                    f"(attempt {task.retry_count}/{task.max_retries})"
                )
            else:
                task.status = TaskStatus.FAILED
                self.logger.error(
                    f"Task {task_id} failed permanently: {error} "
                    f"(attempts: {task.retry_count}/{task.max_retries})"
                )

            # Update task
            task_data = task.to_dict()
            await db.execute(
                """
                UPDATE tasks SET
                    status = ?, retry_count = ?, error = ?, next_retry_at = ?
                WHERE task_id = ?
            """,
                (
                    task_data["status"],
                    task_data["retry_count"],
                    error,
                    task_data["next_retry_at"],
                    task_id,
                ),
            )
            await db.commit()

    async def process_queue(
        self,
        handler: Callable[[Task], Awaitable[str | int | float | bool | dict | list | None]],
        max_concurrent: int = 5,
    ) -> None:
        """
        Process pending tasks with concurrent workers.

        Args:
            handler: Async function to handle tasks
            max_concurrent: Maximum number of concurrent workers
        """
        self._running = True
        self.logger.info(f"Starting queue processing with {max_concurrent} workers")

        while self._running:
            # Clean up completed tasks first
            done_tasks = [tid for tid, t in self._processing_tasks.items() if t.done()]
            for tid in done_tasks:
                del self._processing_tasks[tid]

            # Get task
            task = await self.dequeue()

            if task is None:
                # No tasks available, wait before checking again
                await asyncio.sleep(0.1)
                continue

            # Check if we've reached max concurrent tasks
            if len(self._processing_tasks) >= max_concurrent:
                await asyncio.sleep(0.05)
                # Re-queue the task for later processing
                await self._requeue_task(task.task_id)
                continue

            # Process task asynchronously
            processing_task = asyncio.create_task(self._process_single_task(handler, task))
            self._processing_tasks[task.task_id] = processing_task

        # Wait for remaining tasks to complete
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks.values(), return_exceptions=True)

    async def _process_single_task(
        self,
        handler: Callable[[Task], Awaitable[str | int | float | bool | dict | list | None]],
        task: Task,
    ) -> None:
        """
        Process a single task with error handling.

        Args:
            handler: Async function to handle tasks
            task: Task to process
        """
        self.logger.info(f"Processing task {task.task_id} ({task.name})")

        try:
            # Check if task is expired
            if task.is_expired():
                await self._mark_as_expired(task.task_id)
                return

            # Execute handler
            result = await handler(task)

            # Mark as completed
            await self.complete_task(task.task_id, result)

        except asyncio.CancelledError:
            self.logger.warning(f"Task {task.task_id} was cancelled")
            await self.cancel_task(task.task_id)
        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)
            await self.fail_task(task.task_id, str(e))

    async def _mark_as_expired(self, task_id: str) -> None:
        """Mark task as expired."""
        async with aiosqlite.connect(self.db_path) as db:
            await self._update_status_simple(
                db,
                task_id,
                TaskStatus.EXPIRED,
                completed_at=datetime.now(timezone.utc),
            )
            await db.commit()

        self.logger.warning(f"Task {task_id} marked as expired")

    async def cancel_task(self, task_id: str) -> None:
        """
        Cancel a task.

        Args:
            task_id: Task ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            await self._update_status_simple(
                db,
                task_id,
                TaskStatus.CANCELLED,
                completed_at=datetime.now(timezone.utc),
            )
            await db.commit()

        self.logger.info(f"Task {task_id} cancelled")

    async def _requeue_task(self, task_id: str) -> None:
        """Requeue a task by resetting its status to PENDING."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET status = ? WHERE task_id = ?",
                (TaskStatus.PENDING.value, task_id),
            )
            await db.commit()

    async def reprocess_pending(self) -> int:
        """
        Reprocess tasks stuck in PROCESSING state.

        This is useful on startup to handle tasks that were processing
        when the system shut down.

        Returns:
            Number of tasks reprocessed
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT task_id FROM tasks
                WHERE status = ?
            """,
                (TaskStatus.PROCESSING.value,),
            )
            rows = await cursor.fetchall()

            for row in rows:
                task_id = row[0]
                await db.execute(
                    "UPDATE tasks SET status = ? WHERE task_id = ?",
                    (TaskStatus.PENDING.value, task_id),
                )

            await db.commit()

        count = len(rows)
        if count > 0:
            self.logger.info(f"Reprocessed {count} stuck tasks")

        return count

    async def mark_expired(self) -> int:
        """
        Mark expired tasks as EXPIRED.

        Returns:
            Number of tasks marked as expired
        """
        now = serialize_datetime(datetime.now(timezone.utc))

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?
                WHERE status = ? AND expires_at IS NOT NULL AND expires_at < ?
            """,
                (TaskStatus.EXPIRED.value, now, TaskStatus.PENDING.value, now),
            )
            await db.commit()
            count: int = cursor.rowcount

        if count > 0:
            self.logger.info(f"Marked {count} tasks as expired")

        return count

    async def retry_failed(self) -> int:
        """
        Retry failed tasks that are ready for retry.

        Returns:
            Number of tasks queued for retry
        """
        now = serialize_datetime(datetime.now(timezone.utc))

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE tasks
                SET status = ?
                WHERE status = ?
                AND next_retry_at IS NOT NULL
                AND next_retry_at <= ?
            """,
                (TaskStatus.PENDING.value, TaskStatus.FAILED.value, now),
            )
            await db.commit()
            count: int = cursor.rowcount

        if count > 0:
            self.logger.info(f"Queued {count} failed tasks for retry")

        return count

    async def get_dead_letter_queue(self) -> list[Task]:
        """
        Get permanently failed tasks.

        Returns:
            List of permanently failed tasks
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
            """,
                (TaskStatus.FAILED.value,),
            )
            rows = await cursor.fetchall()

            tasks = []
            columns = [
                "task_id",
                "name",
                "payload",
                "priority",
                "status",
                "created_at",
                "started_at",
                "completed_at",
                "expires_at",
                "retry_count",
                "max_retries",
                "result",
                "error",
                "next_retry_at",
            ]
            for row in rows:
                data = dict(zip(columns, row))
                tasks.append(Task.from_dict(data))

            return tasks

    async def get_statistics(self) -> dict[str, int | dict[str, int]]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Get count by status
            cursor = await db.execute("""
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
            """)
            rows = await cursor.fetchall()

            status_counts = {status.value: 0 for status in TaskStatus}
            for row in rows:
                status_counts[row[0]] = row[1]

            # Get count by priority for pending tasks
            cursor = await db.execute(
                """
                SELECT priority, COUNT(*) as count
                FROM tasks
                WHERE status = ?
                GROUP BY priority
            """,
                (TaskStatus.PENDING.value,),
            )
            rows = await cursor.fetchall()

            priority_counts = {priority.name: 0 for priority in TaskPriority}
            for row in rows:
                priority_name = TaskPriority(row[0]).name
                priority_counts[priority_name] = row[1]

            # Get total tasks
            cursor = await db.execute("SELECT COUNT(*) FROM tasks")
            total = (await cursor.fetchone())[0]

            return {
                "total_tasks": total,
                "by_status": status_counts,
                "pending_by_priority": priority_counts,
                "processing": len(self._processing_tasks),
            }

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = await cursor.fetchone()

            if not row:
                return None

            columns = [
                "task_id",
                "name",
                "payload",
                "priority",
                "status",
                "created_at",
                "started_at",
                "completed_at",
                "expires_at",
                "retry_count",
                "max_retries",
                "result",
                "error",
                "next_retry_at",
            ]
            data = dict(zip(columns, row))
            return Task.from_dict(data)

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """
        List tasks with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of tasks
        """
        async with aiosqlite.connect(self.db_path) as db:
            if status:
                cursor = await db.execute(
                    """
                    SELECT * FROM tasks
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """,
                    (status.value, limit, offset),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM tasks
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """,
                    (limit, offset),
                )

            rows = await cursor.fetchall()

            tasks = []
            columns = [
                "task_id",
                "name",
                "payload",
                "priority",
                "status",
                "created_at",
                "started_at",
                "completed_at",
                "expires_at",
                "retry_count",
                "max_retries",
                "result",
                "error",
                "next_retry_at",
            ]
            for row in rows:
                data = dict(zip(columns, row))
                tasks.append(Task.from_dict(data))

            return tasks

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from the queue.

        Args:
            task_id: Task ID

        Returns:
            True if task was deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            await db.commit()
            deleted: bool = cursor.rowcount > 0

        if deleted:
            self.logger.info(f"Task {task_id} deleted")

        return deleted

    async def clear_completed(self, older_than: timedelta | None = None) -> int:
        """
        Clear completed tasks from the queue.

        Args:
            older_than: Only clear tasks older than this duration

        Returns:
            Number of tasks cleared
        """
        async with aiosqlite.connect(self.db_path) as db:
            if older_than:
                cutoff = datetime.now(timezone.utc) - older_than
                cutoff_str = serialize_datetime(cutoff)
                cursor = await db.execute(
                    """
                    DELETE FROM tasks
                    WHERE status = ? AND completed_at < ?
                """,
                    (TaskStatus.COMPLETED.value, cutoff_str),
                )
            else:
                cursor = await db.execute(
                    "DELETE FROM tasks WHERE status = ?",
                    (TaskStatus.COMPLETED.value,),
                )

            await db.commit()
            count: int = cursor.rowcount

        if count > 0:
            self.logger.info(f"Cleared {count} completed tasks")

        return count

    async def stop(self) -> None:
        """Stop queue processing gracefully."""
        self._running = False
        self.logger.info("Queue processing stopped")

    async def shutdown(self) -> None:
        """
        Shutdown queue and wait for current tasks to complete.

        This should be called when shutting down the application.
        """
        await self.stop()

        # Wait for remaining tasks
        if self._processing_tasks:
            self.logger.info(f"Waiting for {len(self._processing_tasks)} tasks to complete...")
            await asyncio.gather(*self._processing_tasks.values(), return_exceptions=True)

        self.logger.info("Queue shutdown complete")


async def create_task(
    queue: PersistentTaskQueue,
    name: str,
    payload: dict[str, str | int | float | bool | Decimal | datetime | None],
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    expires_at: datetime | None = None,
) -> str:
    """
    Create and enqueue a new task.

    Args:
        queue: Task queue instance
        name: Task name
        payload: Task payload
        priority: Task priority
        max_retries: Maximum number of retries
        expires_at: Task expiration time

    Returns:
        Task ID
    """
    task = Task(
        task_id=str(uuid.uuid4()),
        name=name,
        payload=payload,
        priority=priority,
        max_retries=max_retries,
        expires_at=expires_at,
    )
    return await queue.enqueue(task)
