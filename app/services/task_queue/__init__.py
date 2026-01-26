"""
Async Task Queue Service for AlgoTrading System.

This module provides a persistent task queue system for 24/7 operation that:
- Persists tasks to database
- Reprocesses pending tasks on restart
- Handles task expiration
- Supports priority queue
- Has dead letter queue for failures
- Implements retry with exponential backoff

The task queue is designed to replace direct asyncio.create_task() usage with
a more robust, persistent solution that survives system restarts.
"""

from .persistent_queue import (
    Task,
    TaskPriority,
    TaskStatus,
    PersistentTaskQueue,
    exponential_backoff,
    create_task,
)

__all__ = [
    "Task",
    "TaskPriority",
    "TaskStatus",
    "PersistentTaskQueue",
    "exponential_backoff",
    "create_task",
]
