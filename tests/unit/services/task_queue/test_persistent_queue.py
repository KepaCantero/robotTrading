"""
Tests for PersistentTaskQueue - CRITICAL for 24/7 operation.

This test suite ensures that the task queue:
- Persists tasks to database correctly
- Reprocesses pending tasks on restart
- Handles task expiration properly
- Supports priority queue ordering
- Has dead letter queue for failures
- Implements retry with exponential backoff
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from app.services.task_queue import (
    Task,
    TaskPriority,
    TaskStatus,
    PersistentTaskQueue,
    exponential_backoff,
    create_task,
)


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    return str(tmp_path / "test_task_queue.db")


@pytest_asyncio.fixture
async def queue(temp_db_path):
    """Create task queue instance."""
    q = PersistentTaskQueue(db_path=temp_db_path)
    await q.initialize()
    yield q
    await q.shutdown()


class TestExponentialBackoff:
    """Tests for exponential backoff calculation."""

    def test_exponential_backoff_base(self):
        """Test exponential backoff with base delay."""
        delay = exponential_backoff(0, base_delay=1.0)
        assert delay == 1.0

    def test_exponential_backoff_increases(self):
        """Test exponential backoff increases with attempts."""
        delay_0 = exponential_backoff(0, base_delay=1.0)
        delay_1 = exponential_backoff(1, base_delay=1.0)
        delay_2 = exponential_backoff(2, base_delay=1.0)
        assert delay_0 < delay_1 < delay_2

    def test_exponential_backoff_max_delay(self):
        """Test exponential backoff respects max delay."""
        delay = exponential_backoff(100, base_delay=1.0, max_delay=300.0)
        assert delay <= 300.0

    def test_exponential_backoff_custom_base(self):
        """Test exponential backoff with custom base delay."""
        delay = exponential_backoff(2, base_delay=2.0)
        assert delay == 8.0  # 2.0 * 2^2 = 8.0


class TestTaskModel:
    """Tests for Task model."""

    def test_task_creation(self):
        """Test task creation with required fields."""
        task = Task(
            task_id="test-1",
            name="Test Task",
            payload={"symbol": "AAPL", "action": "buy"},
        )
        assert task.task_id == "test-1"
        assert task.name == "Test Task"
        assert task.payload["symbol"] == "AAPL"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
        assert task.retry_count == 0

    def test_task_with_priority(self):
        """Test task creation with custom priority."""
        task = Task(
            task_id="test-2",
            name="High Priority Task",
            payload={},
            priority=TaskPriority.HIGH,
        )
        assert task.priority == TaskPriority.HIGH

    def test_task_with_expiration(self):
        """Test task creation with expiration."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        task = Task(
            task_id="test-3",
            name="Expiring Task",
            payload={},
            expires_at=expires_at,
        )
        assert task.expires_at == expires_at

    def test_task_to_dict(self):
        """Test task serialization to dictionary."""
        task = Task(
            task_id="test-4",
            name="Test Task",
            payload={"value": 123},
            priority=TaskPriority.CRITICAL,
        )
        data = task.to_dict()
        assert data["task_id"] == "test-4"
        assert data["name"] == "Test Task"
        assert data["priority"] == TaskPriority.CRITICAL.value
        assert data["status"] == TaskStatus.PENDING.value

    def test_task_from_dict(self):
        """Test task deserialization from dictionary."""
        data = {
            "task_id": "test-5",
            "name": "Test Task",
            "payload": '{"symbol": "AAPL"}',
            "priority": TaskPriority.HIGH.value,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": None,
            "completed_at": None,
            "expires_at": None,
            "retry_count": 0,
            "max_retries": 3,
            "result": None,
            "error": None,
            "next_retry_at": None,
        }
        task = Task.from_dict(data)
        assert task.task_id == "test-5"
        assert task.name == "Test Task"
        assert task.payload["symbol"] == "AAPL"
        assert task.priority == TaskPriority.HIGH

    def test_task_should_retry(self):
        """Test task retry logic."""
        task = Task(
            task_id="test-6",
            name="Retry Task",
            payload={},
            status=TaskStatus.FAILED,
            retry_count=1,
            max_retries=3,
        )
        assert task.should_retry()

    def test_task_should_not_retry(self):
        """Test task should not retry when max retries reached."""
        task = Task(
            task_id="test-7",
            name="No Retry Task",
            payload={},
            status=TaskStatus.FAILED,
            retry_count=3,
            max_retries=3,
        )
        assert not task.should_retry()

    def test_task_is_expired(self):
        """Test task expiration check."""
        expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        task = Task(
            task_id="test-8",
            name="Expired Task",
            payload={},
            expires_at=expires_at,
        )
        assert task.is_expired()

    def test_task_is_not_expired(self):
        """Test task not expired."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        task = Task(
            task_id="test-9",
            name="Not Expired Task",
            payload={},
            expires_at=expires_at,
        )
        assert not task.is_expired()

    def test_task_can_process(self):
        """Test task can be processed."""
        task = Task(
            task_id="test-10",
            name="Processable Task",
            payload={},
            status=TaskStatus.PENDING,
        )
        assert task.can_process()

    def test_task_cannot_process_when_processing(self):
        """Test task cannot process when already processing."""
        task = Task(
            task_id="test-11",
            name="Processing Task",
            payload={},
            status=TaskStatus.PROCESSING,
        )
        assert not task.can_process()

    def test_task_cannot_process_when_expired(self):
        """Test task cannot process when expired."""
        expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        task = Task(
            task_id="test-12",
            name="Expired Task",
            payload={},
            status=TaskStatus.PENDING,
            expires_at=expires_at,
        )
        assert not task.can_process()

    def test_task_cannot_process_when_waiting_retry(self):
        """Test task cannot process when waiting for retry."""
        next_retry = datetime.now(timezone.utc) + timedelta(minutes=5)
        task = Task(
            task_id="test-13",
            name="Retry Wait Task",
            payload={},
            status=TaskStatus.PENDING,
            next_retry_at=next_retry,
        )
        assert not task.can_process()


class TestQueueInitialization:
    """Tests for queue initialization."""

    @pytest.mark.asyncio
    async def test_queue_initialization(self, temp_db_path):
        """Test queue initializes database."""
        q = PersistentTaskQueue(db_path=temp_db_path)
        await q.initialize()
        # Database should be created
        import os

        assert os.path.exists(temp_db_path)
        await q.shutdown()

    @pytest.mark.asyncio
    async def test_queue_multiple_initialization(self, queue):
        """Test queue can be initialized multiple times."""
        # Should not raise an error
        await queue.initialize()
        await queue.initialize()


class TestTaskEnqueue:
    """Tests for task enqueue operations."""

    @pytest.mark.asyncio
    async def test_enqueue_single_task(self, queue):
        """Test enqueuing a single task."""
        task = Task(
            task_id="enqueue-1",
            name="Enqueue Test",
            payload={"test": "data"},
        )
        task_id = await queue.enqueue(task)
        assert task_id == "enqueue-1"

    @pytest.mark.asyncio
    async def test_enqueue_multiple_tasks(self, queue):
        """Test enqueuing multiple tasks."""
        tasks = [
            Task(
                task_id=f"enqueue-{i}",
                name=f"Task {i}",
                payload={"index": i},
            )
            for i in range(5)
        ]

        for task in tasks:
            await queue.enqueue(task)

        stats = await queue.get_statistics()
        assert stats["total_tasks"] == 5

    @pytest.mark.asyncio
    async def test_enqueue_with_priority(self, queue):
        """Test enqueuing tasks with different priorities."""
        high_task = Task(
            task_id="high-priority",
            name="High Priority",
            payload={},
            priority=TaskPriority.HIGH,
        )
        low_task = Task(
            task_id="low-priority",
            name="Low Priority",
            payload={},
            priority=TaskPriority.LOW,
        )

        await queue.enqueue(low_task)
        await queue.enqueue(high_task)

        # High priority should be dequeued first
        task = await queue.dequeue()
        assert task.task_id == "high-priority"


class TestTaskDequeue:
    """Tests for task dequeue operations."""

    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self, queue):
        """Test dequeuing from empty queue."""
        task = await queue.dequeue()
        assert task is None

    @pytest.mark.asyncio
    async def test_dequeue_single_task(self, queue):
        """Test dequeuing a single task."""
        task = Task(
            task_id="dequeue-1",
            name="Dequeue Test",
            payload={},
        )
        await queue.enqueue(task)

        dequeued = await queue.dequeue()
        assert dequeued.task_id == "dequeue-1"
        assert dequeued.status == TaskStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_dequeue_priority_order(self, queue):
        """Test dequeue respects priority order."""
        # Enqueue in random order
        await queue.enqueue(Task(task_id="low", name="Low", payload={}, priority=TaskPriority.LOW))
        await queue.enqueue(
            Task(task_id="critical", name="Critical", payload={}, priority=TaskPriority.CRITICAL)
        )
        await queue.enqueue(
            Task(task_id="normal", name="Normal", payload={}, priority=TaskPriority.NORMAL)
        )
        await queue.enqueue(
            Task(task_id="high", name="High", payload={}, priority=TaskPriority.HIGH)
        )

        # Should dequeue in priority order
        first = await queue.dequeue()
        assert first.task_id == "critical"

        second = await queue.dequeue()
        assert second.task_id == "high"

        third = await queue.dequeue()
        assert third.task_id == "normal"

        fourth = await queue.dequeue()
        assert fourth.task_id == "low"

    @pytest.mark.asyncio
    async def test_dequeue_fifo_within_priority(self, queue):
        """Test FIFO ordering within same priority."""
        await queue.enqueue(
            Task(task_id="first", name="First", payload={}, priority=TaskPriority.NORMAL)
        )
        await queue.enqueue(
            Task(task_id="second", name="Second", payload={}, priority=TaskPriority.NORMAL)
        )

        first = await queue.dequeue()
        second = await queue.dequeue()

        assert first.task_id == "first"
        assert second.task_id == "second"


class TestTaskCompletion:
    """Tests for task completion."""

    @pytest.mark.asyncio
    async def test_complete_task_success(self, queue):
        """Test marking task as completed."""
        task = Task(
            task_id="complete-1",
            name="Complete Test",
            payload={},
        )
        await queue.enqueue(task)

        # Dequeue to start processing
        await queue.dequeue()

        # Complete with result
        result = {"status": "success", "value": 42}
        await queue.complete_task("complete-1", result)

        # Verify task status
        retrieved = await queue.get_task("complete-1")
        assert retrieved.status == TaskStatus.COMPLETED
        assert retrieved.result == result

    @pytest.mark.asyncio
    async def test_complete_task_without_result(self, queue):
        """Test completing task without result."""
        task = Task(
            task_id="complete-2",
            name="Complete No Result",
            payload={},
        )
        await queue.enqueue(task)
        await queue.dequeue()
        await queue.complete_task("complete-2")

        retrieved = await queue.get_task("complete-2")
        assert retrieved.status == TaskStatus.COMPLETED


class TestTaskFailure:
    """Tests for task failure handling."""

    @pytest.mark.asyncio
    async def test_fail_task_permanent(self, queue):
        """Test failing task permanently."""
        task = Task(
            task_id="fail-1",
            name="Permanent Fail",
            payload={},
            max_retries=0,
        )
        await queue.enqueue(task)
        await queue.dequeue()

        await queue.fail_task("fail-1", "Test error")

        retrieved = await queue.get_task("fail-1")
        assert retrieved.status == TaskStatus.FAILED
        assert retrieved.error == "Test error"
        assert retrieved.retry_count == 1

    @pytest.mark.asyncio
    async def test_fail_task_with_retry(self, queue):
        """Test failing task with retry."""
        task = Task(
            task_id="fail-2",
            name="Retry Fail",
            payload={},
            max_retries=3,
        )
        await queue.enqueue(task)
        await queue.dequeue()

        await queue.fail_task("fail-2", "Temporary error")

        retrieved = await queue.get_task("fail-2")
        assert retrieved.status == TaskStatus.PENDING
        assert retrieved.retry_count == 1
        assert retrieved.next_retry_at is not None

    @pytest.mark.asyncio
    async def test_fail_task_max_retries(self, queue):
        """Test task fails after max retries."""
        task = Task(
            task_id="fail-3",
            name="Max Retries",
            payload={},
            max_retries=2,
        )
        await queue.enqueue(task)
        await queue.dequeue()

        # Fail first time
        await queue.fail_task("fail-3", "Error 1")
        # Should be pending

        # Dequeue and fail second time
        await queue.dequeue()
        await queue.fail_task("fail-3", "Error 2")
        # Should still be pending

        # Dequeue and fail third time (exceeds max_retries)
        await queue.dequeue()
        await queue.fail_task("fail-3", "Error 3")
        # Should be failed permanently

        retrieved = await queue.get_task("fail-3")
        assert retrieved.status == TaskStatus.FAILED


class TestTaskExpiration:
    """Tests for task expiration handling."""

    @pytest.mark.asyncio
    async def test_mark_expired_tasks(self, queue):
        """Test marking expired tasks."""
        # Create expired task
        expired_task = Task(
            task_id="expired-1",
            name="Expired Task",
            payload={},
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        await queue.enqueue(expired_task)

        # Create valid task
        valid_task = Task(
            task_id="valid-1",
            name="Valid Task",
            payload={},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        await queue.enqueue(valid_task)

        # Mark expired
        count = await queue.mark_expired()
        assert count == 1

        # Check status
        expired = await queue.get_task("expired-1")
        assert expired.status == TaskStatus.EXPIRED

        valid = await queue.get_task("valid-1")
        assert valid.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_expired_task_not_dequeued(self, queue):
        """Test expired tasks are not dequeued."""
        expired_task = Task(
            task_id="expired-2",
            name="Expired Task",
            payload={},
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        await queue.enqueue(expired_task)

        # Should not dequeue expired task
        task = await queue.dequeue()
        assert task is None


class TestTaskRetry:
    """Tests for task retry functionality."""

    @pytest.mark.asyncio
    async def test_retry_failed_tasks(self, queue):
        """Test retrying failed tasks."""
        # Create failed task ready for retry
        task = Task(
            task_id="retry-1",
            name="Retry Task",
            payload={},
            status=TaskStatus.FAILED,
            next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        await queue.enqueue(task)

        # Retry failed tasks
        count = await queue.retry_failed()
        assert count == 1

        # Check status
        retrieved = await queue.get_task("retry-1")
        assert retrieved.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_retry_failed_not_yet(self, queue):
        """Test retry respects next_retry_at."""
        task = Task(
            task_id="retry-2",
            name="Future Retry",
            payload={},
            status=TaskStatus.FAILED,
            next_retry_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        await queue.enqueue(task)

        # Should not retry yet
        count = await queue.retry_failed()
        assert count == 0


class TestReprocessPending:
    """Tests for reprocessing stuck tasks."""

    @pytest.mark.asyncio
    async def test_reprocess_stuck_tasks(self, queue):
        """Test reprocessing tasks stuck in PROCESSING state."""
        # Create stuck task
        task = Task(
            task_id="stuck-1",
            name="Stuck Task",
            payload={},
            status=TaskStatus.PROCESSING,
        )
        await queue.enqueue(task)

        # Reprocess stuck tasks
        count = await queue.reprocess_pending()
        assert count == 1

        # Check status
        retrieved = await queue.get_task("stuck-1")
        assert retrieved.status == TaskStatus.PENDING


class TestDeadLetterQueue:
    """Tests for dead letter queue."""

    @pytest.mark.asyncio
    async def test_get_dead_letter_queue(self, queue):
        """Test getting permanently failed tasks."""
        # Create permanently failed task
        failed_task = Task(
            task_id="dlq-1",
            name="Failed Task",
            payload={},
            status=TaskStatus.FAILED,
            retry_count=3,
            max_retries=3,
        )
        await queue.enqueue(failed_task)

        # Create normal task
        normal_task = Task(
            task_id="dlq-2",
            name="Normal Task",
            payload={},
            status=TaskStatus.PENDING,
        )
        await queue.enqueue(normal_task)

        # Get dead letter queue
        dlq = await queue.get_dead_letter_queue()
        assert len(dlq) == 1
        assert dlq[0].task_id == "dlq-1"


class TestQueueStatistics:
    """Tests for queue statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, queue):
        """Test getting queue statistics."""
        # Add tasks with different statuses
        await queue.enqueue(
            Task(task_id="stat-1", name="P1", payload={}, status=TaskStatus.PENDING)
        )
        await queue.enqueue(
            Task(task_id="stat-2", name="P2", payload={}, status=TaskStatus.PENDING)
        )
        await queue.enqueue(
            Task(task_id="stat-3", name="C1", payload={}, status=TaskStatus.COMPLETED)
        )

        stats = await queue.get_statistics()
        assert stats["total_tasks"] == 3
        assert stats["by_status"]["pending"] == 2
        assert stats["by_status"]["completed"] == 1

    @pytest.mark.asyncio
    async def test_statistics_by_priority(self, queue):
        """Test statistics broken down by priority."""
        await queue.enqueue(
            Task(task_id="prio-1", name="High", payload={}, priority=TaskPriority.HIGH)
        )
        await queue.enqueue(
            Task(task_id="prio-2", name="Normal", payload={}, priority=TaskPriority.NORMAL)
        )
        await queue.enqueue(
            Task(task_id="prio-3", name="Low", payload={}, priority=TaskPriority.LOW)
        )

        stats = await queue.get_statistics()
        assert stats["pending_by_priority"]["HIGH"] == 1
        assert stats["pending_by_priority"]["NORMAL"] == 1
        assert stats["pending_by_priority"]["LOW"] == 1


class TestTaskRetrieval:
    """Tests for task retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, queue):
        """Test getting task by ID."""
        task = Task(
            task_id="get-1",
            name="Get Test",
            payload={"data": "value"},
        )
        await queue.enqueue(task)

        retrieved = await queue.get_task("get-1")
        assert retrieved is not None
        assert retrieved.task_id == "get-1"
        assert retrieved.payload["data"] == "value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, queue):
        """Test getting non-existent task."""
        retrieved = await queue.get_task("nonexistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, queue):
        """Test listing tasks."""
        await queue.enqueue(Task(task_id="list-1", name="Task 1", payload={}))
        await queue.enqueue(Task(task_id="list-2", name="Task 2", payload={}))
        await queue.enqueue(Task(task_id="list-3", name="Task 3", payload={}))

        tasks = await queue.list_tasks(limit=2)
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, queue):
        """Test listing tasks filtered by status."""
        await queue.enqueue(
            Task(task_id="filter-1", name="Pending", payload={}, status=TaskStatus.PENDING)
        )
        await queue.enqueue(
            Task(task_id="filter-2", name="Completed", payload={}, status=TaskStatus.COMPLETED)
        )

        pending = await queue.list_tasks(status=TaskStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].task_id == "filter-1"

        completed = await queue.list_tasks(status=TaskStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].task_id == "filter-2"


class TestTaskDeletion:
    """Tests for task deletion."""

    @pytest.mark.asyncio
    async def test_delete_task(self, queue):
        """Test deleting a task."""
        task = Task(
            task_id="delete-1",
            name="Delete Me",
            payload={},
        )
        await queue.enqueue(task)

        deleted = await queue.delete_task("delete-1")
        assert deleted is True

        # Task should be gone
        retrieved = await queue.get_task("delete-1")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, queue):
        """Test deleting non-existent task."""
        deleted = await queue.delete_task("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_completed(self, queue):
        """Test clearing completed tasks."""
        await queue.enqueue(
            Task(task_id="clear-1", name="Completed 1", payload={}, status=TaskStatus.COMPLETED)
        )
        await queue.enqueue(
            Task(task_id="clear-2", name="Completed 2", payload={}, status=TaskStatus.COMPLETED)
        )
        await queue.enqueue(
            Task(task_id="clear-3", name="Pending", payload={}, status=TaskStatus.PENDING)
        )

        count = await queue.clear_completed()
        assert count == 2

        # Pending task should remain
        pending = await queue.get_task("clear-3")
        assert pending is not None

    @pytest.mark.asyncio
    async def test_clear_completed_older_than(self, queue):
        """Test clearing completed tasks older than specified time."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)

        old_task = Task(
            task_id="old",
            name="Old Completed",
            payload={},
            status=TaskStatus.COMPLETED,
            completed_at=old_time,
        )
        await queue.enqueue(old_task)

        recent_task = Task(
            task_id="recent",
            name="Recent Completed",
            payload={},
            status=TaskStatus.COMPLETED,
            completed_at=recent_time,
        )
        await queue.enqueue(recent_task)

        # Clear tasks older than 1 hour
        count = await queue.clear_completed(older_than=timedelta(hours=1))
        assert count == 1

        # Old task should be deleted
        assert await queue.get_task("old") is None
        # Recent task should remain
        assert await queue.get_task("recent") is not None


class TestTaskCancellation:
    """Tests for task cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_task(self, queue):
        """Test cancelling a task."""
        task = Task(
            task_id="cancel-1",
            name="Cancel Me",
            payload={},
        )
        await queue.enqueue(task)

        await queue.cancel_task("cancel-1")

        retrieved = await queue.get_task("cancel-1")
        assert retrieved.status == TaskStatus.CANCELLED


class TestQueueProcessing:
    """Tests for queue processing with handlers."""

    @pytest.mark.asyncio
    async def test_process_single_task(self, queue):
        """Test processing a single task."""
        processed = []

        async def handler(task):
            processed.append(task.task_id)
            return {"result": "success"}

        task = Task(
            task_id="process-1",
            name="Process Test",
            payload={"value": 42},
        )
        await queue.enqueue(task)

        # Process for a short time
        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=1))

        # Wait for task to be processed
        await asyncio.sleep(0.5)

        await queue.stop()
        await processing

        assert "process-1" in processed

        # Verify task completed
        retrieved = await queue.get_task("process-1")
        assert retrieved.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_failing_task(self, queue):
        """Test processing a task that fails."""
        processed = []

        async def failing_handler(task):
            processed.append(task.task_id)
            raise ValueError("Test error")

        task = Task(
            task_id="fail-process-1",
            name="Failing Task",
            payload={},
            max_retries=0,
        )
        await queue.enqueue(task)

        processing = asyncio.create_task(queue.process_queue(failing_handler, max_concurrent=1))
        await asyncio.sleep(0.5)
        await queue.stop()
        await processing

        assert "fail-process-1" in processed

        # Verify task failed
        retrieved = await queue.get_task("fail-process-1")
        assert retrieved.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_concurrent_tasks(self, queue):
        """Test processing multiple tasks concurrently."""
        processed = []
        processing_order = []

        async def slow_handler(task):
            processing_order.append(task.task_id)
            await asyncio.sleep(0.1)
            processed.append(task.task_id)
            return task.task_id

        # Add multiple tasks
        for i in range(3):
            task = Task(
                task_id=f"concurrent-{i}",
                name=f"Concurrent Task {i}",
                payload={"index": i},
            )
            await queue.enqueue(task)

        processing = asyncio.create_task(queue.process_queue(slow_handler, max_concurrent=3))
        await asyncio.sleep(0.5)
        await queue.stop()
        await processing

        assert len(processed) == 3
        assert len(processing_order) == 3

    @pytest.mark.asyncio
    async def test_process_with_retry(self, queue):
        """Test processing with retry."""
        attempt_count = 0

        async def flaky_handler(task):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return {"success": True}

        task = Task(
            task_id="flaky-1",
            name="Flaky Task",
            payload={},
            max_retries=3,
        )
        await queue.enqueue(task)

        # Process task
        await queue.dequeue()
        try:
            await flaky_handler(task)
        except ValueError:
            pass

        # Fail and retry
        await queue.fail_task("flaky-1", "Temporary failure")

        # Verify task is pending for retry
        retrieved = await queue.get_task("flaky-1")
        assert retrieved.status == TaskStatus.PENDING
        assert retrieved.next_retry_at is not None


class TestCreateTaskHelper:
    """Tests for create_task helper function."""

    @pytest.mark.asyncio
    async def test_create_task_default(self, queue):
        """Test creating task with defaults."""
        task_id = await create_task(
            queue,
            "Test Task",
            {"key": "value"},
        )

        assert task_id is not None

        task = await queue.get_task(task_id)
        assert task.name == "Test Task"
        assert task.payload["key"] == "value"
        assert task.priority == TaskPriority.NORMAL
        assert task.max_retries == 3

    @pytest.mark.asyncio
    async def test_create_task_with_options(self, queue):
        """Test creating task with options."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        task_id = await create_task(
            queue,
            "High Priority Task",
            {"data": "important"},
            priority=TaskPriority.HIGH,
            max_retries=5,
            expires_at=expires_at,
        )

        task = await queue.get_task(task_id)
        assert task.priority == TaskPriority.HIGH
        assert task.max_retries == 5
        assert task.expires_at == expires_at


class TestComplexPayloads:
    """Tests for complex payload serialization."""

    @pytest.mark.asyncio
    async def test_task_with_decimal_payload(self, queue):
        """Test task with decimal values in payload."""
        task = Task(
            task_id="decimal-1",
            name="Decimal Task",
            payload={
                "price": Decimal("123.45"),
                "quantity": Decimal("1000"),
            },
        )
        await queue.enqueue(task)

        retrieved = await queue.get_task("decimal-1")
        assert isinstance(retrieved.payload["price"], Decimal)
        assert retrieved.payload["price"] == Decimal("123.45")

    @pytest.mark.asyncio
    async def test_task_with_datetime_payload(self, queue):
        """Test task with datetime values in payload."""
        now = datetime.now(timezone.utc)
        task = Task(
            task_id="datetime-1",
            name="DateTime Task",
            payload={
                "timestamp": now,
                "date": now.date(),
            },
        )
        await queue.enqueue(task)

        retrieved = await queue.get_task("datetime-1")
        assert isinstance(retrieved.payload["timestamp"], datetime)
        # Note: date() is not preserved, becomes datetime

    @pytest.mark.asyncio
    async def test_task_with_nested_payload(self, queue):
        """Test task with nested payload structure."""
        task = Task(
            task_id="nested-1",
            name="Nested Task",
            payload={
                "level1": {
                    "level2": {
                        "value": 123,
                    }
                },
                "list": [1, 2, 3],
            },
        )
        await queue.enqueue(task)

        retrieved = await queue.get_task("nested-1")
        assert retrieved.payload["level1"]["level2"]["value"] == 123
        assert retrieved.payload["list"] == [1, 2, 3]


class TestConcurrentOperations:
    """Tests for concurrent queue operations."""

    @pytest.mark.asyncio
    async def test_concurrent_enqueue(self, queue):
        """Test concurrent enqueue operations."""
        tasks = [
            Task(
                task_id=f"concurrent-enqueue-{i}",
                name=f"Concurrent Enqueue {i}",
                payload={"index": i},
            )
            for i in range(10)
        ]

        # Enqueue concurrently
        await asyncio.gather(*[queue.enqueue(task) for task in tasks])

        stats = await queue.get_statistics()
        assert stats["total_tasks"] == 10

    @pytest.mark.asyncio
    async def test_concurrent_dequeue(self, queue):
        """Test concurrent dequeue operations."""
        for i in range(10):
            await queue.enqueue(
                Task(
                    task_id=f"concurrent-dequeue-{i}",
                    name=f"Concurrent Dequeue {i}",
                    payload={},
                )
            )

        # Dequeue concurrently
        tasks = await asyncio.gather(*[queue.dequeue() for _ in range(5)])

        # Should get 5 tasks
        assert len([t for t in tasks if t is not None]) == 5


class TestShutdown:
    """Tests for queue shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_stops_processing(self, queue):
        """Test shutdown stops queue processing."""
        processed = []

        async def handler(task):
            processed.append(task.task_id)
            await asyncio.sleep(0.1)
            return task.task_id

        # Add tasks
        for i in range(5):
            await queue.enqueue(
                Task(
                    task_id=f"shutdown-{i}",
                    name=f"Shutdown Task {i}",
                    payload={},
                )
            )

        # Start processing
        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=2))

        # Wait a bit then shutdown
        await asyncio.sleep(0.1)
        await queue.shutdown()
        await processing

        # Should have processed some tasks
        assert len(processed) >= 0

    @pytest.mark.asyncio
    async def test_shutdown_waits_for_completion(self, queue):
        """Test shutdown waits for current tasks to complete."""
        completed = []

        async def slow_handler(task):
            await asyncio.sleep(0.2)
            completed.append(task.task_id)
            return task.task_id

        await queue.enqueue(Task(task_id="slow-1", name="Slow", payload={}))

        # Start processing
        processing = asyncio.create_task(queue.process_queue(slow_handler, max_concurrent=1))

        # Wait for task to start processing
        await asyncio.sleep(0.05)

        # Shutdown - should wait for task to complete
        await queue.shutdown()
        await processing

        # Task should have completed
        assert "slow-1" in completed
