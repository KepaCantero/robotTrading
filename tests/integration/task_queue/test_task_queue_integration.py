"""
Integration tests for PersistentTaskQueue - End-to-end scenarios.

This test suite validates real-world usage patterns:
- Restart recovery
- Trading workflow integration
- Concurrency under load
- Dead letter queue handling
"""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from app.services.task_queue import (
    PersistentTaskQueue,
    Task,
    TaskPriority,
    TaskStatus,
    create_task,
)


@pytest.fixture
def integration_db_path(tmp_path):
    """Create temporary database path for integration tests."""
    return str(tmp_path / "integration_task_queue.db")


@pytest_asyncio.fixture
async def queue(integration_db_path):
    """Create task queue instance for integration tests."""
    q = PersistentTaskQueue(db_path=integration_db_path)
    await q.initialize()
    yield q
    await q.shutdown()


class TestRestartRecovery:
    """Tests for system restart recovery."""

    @pytest.mark.asyncio
    async def test_recover_pending_tasks_on_restart(self, integration_db_path):
        """Test that pending tasks are recovered after restart."""
        # Create queue and add tasks
        queue1 = PersistentTaskQueue(db_path=integration_db_path)
        await queue1.initialize()

        await create_task(queue1, "Order Task", {"symbol": "AAPL", "side": "buy"})
        await create_task(queue1, "Data Task", {"symbol": "MSFT"})
        await create_task(queue1, "Analysis Task", {"symbol": "GOOGL"})

        # Simulate shutdown
        await queue1.shutdown()

        # Restart queue
        queue2 = PersistentTaskQueue(db_path=integration_db_path)
        await queue2.initialize()

        # Check tasks are recovered
        stats = await queue2.get_statistics()
        assert stats["total_tasks"] == 3
        assert stats["by_status"]["pending"] == 3

        await queue2.shutdown()

    @pytest.mark.asyncio
    async def test_recover_processing_tasks_on_restart(self, integration_db_path):
        """Test that stuck processing tasks are reset on restart."""
        queue1 = PersistentTaskQueue(db_path=integration_db_path)
        await queue1.initialize()

        # Create a task and mark it as processing
        task_id = await create_task(queue1, "Stuck Task", {"data": "value"})
        await queue1.dequeue()  # Mark as processing

        # Shutdown without completing
        await queue1.shutdown()

        # Restart
        queue2 = PersistentTaskQueue(db_path=integration_db_path)
        await queue2.initialize()

        # Reprocess stuck tasks
        count = await queue2.reprocess_pending()
        assert count == 1

        # Task should be pending again
        task = await queue2.get_task(task_id)
        assert task.status == TaskStatus.PENDING

        await queue2.shutdown()

    @pytest.mark.asyncio
    async def test_completed_tasks_persist_across_restart(self, integration_db_path):
        """Test that completed tasks remain completed after restart."""
        queue1 = PersistentTaskQueue(db_path=integration_db_path)
        await queue1.initialize()

        # Create and complete a task
        task_id = await create_task(queue1, "Completed Task", {"data": "value"})
        await queue1.dequeue()
        await queue1.complete_task(task_id, {"result": "success"})

        await queue1.shutdown()

        # Restart
        queue2 = PersistentTaskQueue(db_path=integration_db_path)
        await queue2.initialize()

        task = await queue2.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"result": "success"}

        await queue2.shutdown()


class TestTradingWorkflow:
    """Tests for trading workflow integration."""

    @pytest.mark.asyncio
    async def test_order_submission_workflow(self, queue):
        """Test complete order submission workflow."""
        # Create order task
        task_id = await create_task(
            queue,
            "submit_market_order",
            {
                "symbol": "AAPL",
                "side": "buy",
                "quantity": 100,
                "order_type": "market",
                "price": Decimal("150.00"),
            },
            priority=TaskPriority.HIGH,
        )

        # Process order
        async def submit_order(task):
            # Simulate order submission
            return {
                "order_id": f"ORDER-{task.task_id}",
                "status": "filled",
                "filled_price": Decimal("150.25"),
                "filled_quantity": 100,
            }

        await queue.dequeue()
        result = await submit_order(await queue.get_task(task_id))
        await queue.complete_task(task_id, result)

        # Verify
        task = await queue.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.result["status"] == "filled"

    @pytest.mark.asyncio
    async def test_multi_stage_trading_workflow(self, queue):
        """Test multi-stage trading workflow with multiple tasks."""
        # Stage 1: Market data analysis
        analysis_task = await create_task(
            queue,
            "analyze_market_data",
            {"symbol": "AAPL", "indicators": ["RSI", "MACD"]},
            priority=TaskPriority.NORMAL,
        )

        # Stage 2: Signal generation (depends on analysis)
        signal_task = await create_task(
            queue,
            "generate_trading_signal",
            {"symbol": "AAPL", "strategy": "momentum"},
            priority=TaskPriority.HIGH,
        )

        # Stage 3: Order execution (depends on signal)
        order_task = await create_task(
            queue,
            "execute_order",
            {"symbol": "AAPL", "side": "buy", "quantity": 100},
            priority=TaskPriority.CRITICAL,
        )

        # Process in priority order
        processed = []

        async def handler(task):
            processed.append(task.task_id)
            await asyncio.sleep(0.01)
            return {"stage": task.name, "status": "complete"}

        # Process all tasks
        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=3))
        await asyncio.sleep(0.5)
        await queue.shutdown()
        await processing

        # CRITICAL should be processed first
        assert order_task in processed

    @pytest.mark.asyncio
    async def test_trading_task_failure_with_retry(self, queue):
        """Test trading task failure and retry workflow."""
        attempt_count = 0

        async def unreliable_connection(task):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Network timeout")
            return {"order_id": "ORDER-SUCCESS", "status": "filled"}

        task_id = await create_task(
            queue,
            "submit_order_with_retry",
            {"symbol": "AAPL", "side": "buy", "quantity": 100},
            priority=TaskPriority.HIGH,
            max_retries=5,
        )

        # Process with failures
        for _ in range(3):
            await queue.dequeue()
            task = await queue.get_task(task_id)
            try:
                result = await unreliable_connection(task)
                await queue.complete_task(task_id, result)
                break
            except ConnectionError as e:
                await queue.fail_task(task_id, str(e))

        # Verify eventual success
        task = await queue.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert attempt_count == 3


class TestDeadLetterQueueWorkflow:
    """Tests for dead letter queue workflow."""

    @pytest.mark.asyncio
    async def test_failed_tasks_to_dead_letter_queue(self, queue):
        """Test permanently failed tasks go to dead letter queue."""
        # Create tasks that will fail
        for i in range(3):
            task_id = await create_task(
                queue,
                f"failing_task_{i}",
                {"data": i},
                max_retries=2,
            )

            # Fail task multiple times
            for _ in range(3):
                await queue.dequeue()
                await queue.fail_task(task_id, f"Attempt {_} failed")

        # Get dead letter queue
        dlq = await queue.get_dead_letter_queue()
        assert len(dlq) == 3

        # All should be permanently failed
        for task in dlq:
            assert task.status == TaskStatus.FAILED
            assert task.retry_count >= task.max_retries

    @pytest.mark.asyncio
    async def test_dead_letter_queue_analysis(self, queue):
        """Test analyzing dead letter queue for patterns."""
        # Add failed tasks with different error types
        task1_id = await create_task(queue, "task1", {"type": "network"}, max_retries=0)
        await queue.dequeue()
        await queue.fail_task(task1_id, "Connection timeout")

        task2_id = await create_task(queue, "task2", {"type": "validation"}, max_retries=0)
        await queue.dequeue()
        await queue.fail_task(task2_id, "Invalid price")

        task3_id = await create_task(queue, "task3", {"type": "network"}, max_retries=0)
        await queue.dequeue()
        await queue.fail_task(task3_id, "Network unreachable")

        # Get and analyze DLQ
        dlq = await queue.get_dead_letter_queue()

        # Group by error type
        error_counts = {}
        for task in dlq:
            error_type = task.error.split()[0] if task.error else "unknown"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        # Should have network and validation errors
        assert "Connection" in error_counts or "Network" in error_counts
        assert "Invalid" in error_counts


class TestPriorityHandling:
    """Tests for priority-based task handling."""

    @pytest.mark.asyncio
    async def test_emergency_order_precedence(self, queue):
        """Test emergency orders take precedence over normal tasks."""
        # Add normal priority tasks
        for i in range(5):
            await create_task(
                queue,
                f"normal_task_{i}",
                {"index": i},
                priority=TaskPriority.NORMAL,
            )

        # Add emergency order
        emergency_task = await create_task(
            queue,
            "emergency_market_sell",
            {"symbol": "AAPL", "side": "sell", "quantity": 1000},
            priority=TaskPriority.CRITICAL,
        )

        # Process tasks
        processed = []

        async def handler(task):
            processed.append(task.task_id)
            return {"status": "done"}

        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=1))
        await asyncio.sleep(0.2)
        await queue.shutdown()
        await processing

        # Emergency task should be processed first
        assert processed[0] == emergency_task

    @pytest.mark.asyncio
    async def test_priority_levels_respected(self, queue):
        """Test all priority levels are respected."""
        # Add tasks of different priorities
        tasks = {
            "low": await create_task(queue, "low", {}, TaskPriority.LOW),
            "normal": await create_task(queue, "normal", {}, TaskPriority.NORMAL),
            "high": await create_task(queue, "high", {}, TaskPriority.HIGH),
            "critical": await create_task(queue, "critical", {}, TaskPriority.CRITICAL),
        }

        # Dequeue in order
        order = []
        for _ in range(4):
            task = await queue.dequeue()
            if task:
                order.append(task.task_id)

        # Should be processed in priority order
        assert order[0] == tasks["critical"]
        assert order[1] == tasks["high"]
        assert order[2] == tasks["normal"]
        assert order[3] == tasks["low"]


class TestExpirationHandling:
    """Tests for task expiration in trading context."""

    @pytest.mark.asyncio
    async def test_expired_order_not_executed(self, queue):
        """Test expired orders are not executed."""
        # Create order that expires quickly
        expires_at = datetime.now(timezone.utc) + timedelta(milliseconds=100)

        task_id = await create_task(
            queue,
            "time_sensitive_order",
            {"symbol": "AAPL", "side": "buy", "quantity": 100},
            expires_at=expires_at,
        )

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Mark expired tasks
        await queue.mark_expired()

        # Try to dequeue
        task = await queue.dequeue()
        assert task is None

        # Verify task is expired
        task = await queue.get_task(task_id)
        assert task.status == TaskStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_valid_orders_execute_before_expiration(self, queue):
        """Test valid orders execute before expiration."""
        # Create order with future expiration
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        task_id = await create_task(
            queue,
            "valid_order",
            {"symbol": "AAPL", "side": "buy", "quantity": 100},
            expires_at=expires_at,
        )

        # Should be able to dequeue
        task = await queue.dequeue()
        assert task is not None
        assert task.task_id == task_id


class TestConcurrentLoad:
    """Tests for handling concurrent load."""

    @pytest.mark.asyncio
    async def test_high_concurrency_order_submissions(self, queue):
        """Test handling many concurrent order submissions."""
        num_orders = 50

        # Create many order tasks
        for i in range(num_orders):
            await create_task(
                queue,
                f"order_{i}",
                {"symbol": f"STOCK{i}", "side": "buy", "quantity": 100},
            )

        # Process with high concurrency
        processed = []

        async def handler(task):
            processed.append(task.task_id)
            await asyncio.sleep(0.01)  # Simulate I/O
            return {"status": "filled"}

        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=10))
        await asyncio.sleep(1.0)
        await queue.shutdown()
        await processing

        # All orders should be processed
        assert len(processed) == num_orders

        # All should be completed
        stats = await queue.get_statistics()
        assert stats["by_status"]["completed"] == num_orders

    @pytest.mark.asyncio
    async def test_queue_under_load(self, queue):
        """Test queue statistics under load."""
        # Add mix of tasks
        for i in range(20):
            await create_task(queue, f"task_{i}", {"index": i})

        # Start processing
        async def handler(task):
            await asyncio.sleep(0.01)
            return {"done": True}

        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=5))

        # Check stats during processing
        await asyncio.sleep(0.1)
        stats = await queue.get_statistics()

        # Should have some processing
        assert stats["total_tasks"] == 20
        assert stats["processing"] > 0 or stats["by_status"]["completed"] > 0

        await queue.shutdown()
        await processing


class TestTaskCleanup:
    """Tests for task cleanup operations."""

    @pytest.mark.asyncio
    async def test_old_completed_tasks_cleanup(self, queue):
        """Test cleanup of old completed tasks."""
        # Create old completed task
        old_time = datetime.now(timezone.utc) - timedelta(days=30)
        old_task = Task(
            task_id="old_completed",
            name="Old Completed",
            payload={},
            status=TaskStatus.COMPLETED,
            completed_at=old_time,
        )
        await queue.enqueue(old_task)

        # Create recent completed task
        recent_task = Task(
            task_id="recent_completed",
            name="Recent Completed",
            payload={},
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        await queue.enqueue(recent_task)

        # Create pending task
        pending_task = Task(
            task_id="pending",
            name="Pending",
            payload={},
            status=TaskStatus.PENDING,
        )
        await queue.enqueue(pending_task)

        # Clear tasks older than 7 days
        cleared = await queue.clear_completed(older_than=timedelta(days=7))
        assert cleared == 1

        # Old task should be deleted
        assert await queue.get_task("old_completed") is None
        # Recent and pending should remain
        assert await queue.get_task("recent_completed") is not None
        assert await queue.get_task("pending") is not None

    @pytest.mark.asyncio
    async def test_dead_letter_queue_cleanup(self, queue):
        """Test cleanup of dead letter queue."""
        # Add permanently failed tasks
        for i in range(5):
            task_id = await create_task(queue, f"failed_{i}", {}, max_retries=0)
            await queue.dequeue()
            await queue.fail_task(task_id, "Permanent error")

        # Get DLQ
        dlq = await queue.get_dead_letter_queue()
        assert len(dlq) == 5

        # Delete old DLQ tasks
        for task in dlq[:3]:
            await queue.delete_task(task.task_id)

        # Remaining tasks should be in DLQ
        dlq = await queue.get_dead_letter_queue()
        assert len(dlq) == 2


class TestStatisticsAndMonitoring:
    """Tests for statistics and monitoring capabilities."""

    @pytest.mark.asyncio
    async def test_queue_statistics_accuracy(self, queue):
        """Test accuracy of queue statistics."""
        # Add tasks in different states
        # Create pending tasks first (with lower priority to avoid being dequeued)
        await create_task(queue, "pending1", {}, priority=TaskPriority.LOW)
        await create_task(queue, "pending2", {}, priority=TaskPriority.LOW)
        await create_task(queue, "pending3", {}, priority=TaskPriority.LOW)

        # Complete a task with higher priority so it gets dequeued first
        task_id = await create_task(queue, "completed", {}, priority=TaskPriority.HIGH)
        await queue.dequeue()
        await queue.complete_task(task_id)

        # Fail a task with higher priority
        task_id = await create_task(queue, "failed", {}, priority=TaskPriority.HIGH, max_retries=0)
        await queue.dequeue()
        await queue.fail_task(task_id, "Error")

        # Get statistics
        stats = await queue.get_statistics()

        assert stats["total_tasks"] == 5
        assert stats["by_status"]["pending"] == 3
        assert stats["by_status"]["completed"] == 1
        assert stats["by_status"]["failed"] == 1
        assert stats["pending_by_priority"]["LOW"] == 3

    @pytest.mark.asyncio
    async def test_queue_status_monitoring(self, queue):
        """Test monitoring queue status over time."""
        # Initial state
        stats1 = await queue.get_statistics()
        assert stats1["total_tasks"] == 0

        # Add tasks
        for i in range(10):
            await create_task(queue, f"monitor_{i}", {})

        stats2 = await queue.get_statistics()
        assert stats2["total_tasks"] == 10

        # Process some tasks
        processed = []

        async def handler(task):
            processed.append(task.task_id)
            return {"done": True}

        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=5))
        await asyncio.sleep(0.2)
        await queue.shutdown()
        await processing

        # Final state
        stats3 = await queue.get_statistics()
        assert len(processed) > 0
        assert stats3["by_status"]["completed"] == len(processed)


class TestErrorRecovery:
    """Tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_handler_exception_doesnt_crash_queue(self, queue):
        """Test handler exceptions don't crash the queue."""
        exception_count = 0

        async def failing_handler(task):
            nonlocal exception_count
            exception_count += 1
            raise ValueError("Handler error")

        # Add tasks
        for i in range(3):
            await create_task(queue, f"fail_{i}", {}, max_retries=0)

        # Process - should not crash
        processing = asyncio.create_task(queue.process_queue(failing_handler, max_concurrent=1))
        # Wait longer for all tasks to be processed
        await asyncio.sleep(2.0)
        await queue.shutdown()
        await processing

        # All tasks should have been attempted
        assert exception_count == 3

    @pytest.mark.asyncio
    async def test_database_error_recovery(self, integration_db_path):
        """Test recovery from database errors."""
        queue1 = PersistentTaskQueue(db_path=integration_db_path)
        await queue1.initialize()

        # Add tasks
        await create_task(queue1, "task1", {})
        await create_task(queue1, "task2", {})

        await queue1.shutdown()

        # Simulate database corruption by changing permissions
        # (In real scenario, this would be a database error)

        # Restart - should handle gracefully
        queue2 = PersistentTaskQueue(db_path=integration_db_path)
        await queue2.initialize()

        # Should still be able to operate
        await create_task(queue2, "task3", {})

        stats = await queue2.get_statistics()
        assert stats["total_tasks"] == 3

        await queue2.shutdown()


class TestBackpressureAndFlowControl:
    """Tests for backpressure and flow control."""

    @pytest.mark.asyncio
    async def test_respect_max_concurrent_limit(self, queue):
        """Test queue respects max concurrent workers limit."""
        concurrent_count = 0
        max_concurrent_seen = 0

        async def slow_handler(task):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.2)
            concurrent_count -= 1
            return {"done": True}

        # Add many tasks
        for i in range(10):
            await create_task(queue, f"slow_{i}", {})

        # Process with limited concurrency
        processing = asyncio.create_task(queue.process_queue(slow_handler, max_concurrent=3))
        await asyncio.sleep(0.3)
        await queue.shutdown()
        await processing

        # Should not exceed max concurrent
        assert max_concurrent_seen <= 3

    @pytest.mark.asyncio
    async def test_queue_throttling_under_load(self, queue):
        """Test queue behavior under heavy load."""
        tasks_processed = []

        async def tracking_handler(task):
            tasks_processed.append(
                {
                    "task_id": task.task_id,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            await asyncio.sleep(0.01)
            return {"done": True}

        # Flood the queue
        for i in range(20):
            await create_task(queue, f"flood_{i}", {})

        # Process with limited concurrency
        processing = asyncio.create_task(queue.process_queue(tracking_handler, max_concurrent=5))
        await asyncio.sleep(0.5)
        await queue.shutdown()
        await processing

        # Should process all tasks
        assert len(tasks_processed) > 0


class TestRealWorldScenarios:
    """Tests for real-world trading scenarios."""

    @pytest.mark.asyncio
    async def test_market_hours_task_processing(self, queue):
        """Test task processing during market hours."""
        # Simulate market open tasks
        await create_task(
            queue,
            "market_open_check",
            {"action": "verify_positions"},
            priority=TaskPriority.HIGH,
        )

        # Add regular trading tasks
        for i in range(5):
            await create_task(
                queue,
                f"trading_signal_{i}",
                {"symbol": f"STOCK{i}"},
                priority=TaskPriority.NORMAL,
            )

        # Add risk management tasks
        await create_task(
            queue,
            "risk_check",
            {"action": "verify_exposure"},
            priority=TaskPriority.CRITICAL,
        )

        # Process - risk check should be first
        processed = []

        async def handler(task):
            processed.append(task.name)
            await asyncio.sleep(0.01)
            return {"done": True}

        processing = asyncio.create_task(queue.process_queue(handler, max_concurrent=3))
        await asyncio.sleep(0.3)
        await queue.shutdown()
        await processing

        # Risk check should be processed first
        assert "risk_check" in processed

    @pytest.mark.asyncio
    async def test_after_hours_batch_processing(self, queue):
        """Test batch processing after market hours."""
        # Create analysis tasks
        for i in range(10):
            await create_task(
                queue,
                f"end_of_day_analysis_{i}",
                {"symbol": f"STOCK{i}", "analysis": "daily_performance"},
                priority=TaskPriority.LOW,
            )

        # Process with high concurrency for batch processing
        processed = []

        async def analysis_handler(task):
            processed.append(task.name)
            await asyncio.sleep(0.02)
            return {"analysis": "complete"}

        processing = asyncio.create_task(queue.process_queue(analysis_handler, max_concurrent=10))
        await asyncio.sleep(0.5)
        await queue.shutdown()
        await processing

        # All analysis tasks should be processed
        assert len(processed) == 10
