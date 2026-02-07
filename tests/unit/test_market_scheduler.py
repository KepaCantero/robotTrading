"""
Unit tests for MarketScheduler - Phase 3.1

Tests the market scheduling functionality for multi-market operations.
"""

import asyncio
from datetime import date, time
from unittest.mock import AsyncMock

import pytest

from app.services.scheduling import (
    MarketSchedule,
    MarketScheduler,
    MarketStatus,
    MarketType,
)


class TestMarketType:
    """Test MarketType enum."""

    def test_market_types(self):
        """Test all market types are defined."""
        assert MarketType.CRYPTO.value == "crypto"
        assert MarketType.FOREX.value == "forex"
        assert MarketType.STOCKS_US.value == "stocks_us"
        assert MarketType.STOCKS_EU.value == "stocks_eu"
        assert MarketType.STOCKS_ASIA.value == "stocks_asia"


class TestMarketSchedule:
    """Test MarketSchedule dataclass."""

    def test_24_7_market(self):
        """Test 24/7 market detection."""
        schedule = MarketSchedule(
            market_type=MarketType.CRYPTO,
            timezone_str="UTC",
            open_time=None,
            close_time=None,
            weekends=True,
        )
        assert schedule.is_24_7() is True

    def test_scheduled_market(self):
        """Test scheduled market detection."""
        schedule = MarketSchedule(
            market_type=MarketType.STOCKS_US,
            timezone_str="America/New_York",
            open_time=time(9, 30),
            close_time=time(16, 0),
            weekends=False,
        )
        assert schedule.is_24_7() is False


class TestMarketScheduler:
    """Test MarketScheduler class."""

    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = MarketScheduler()
        assert scheduler.is_running() is False
        assert scheduler.get_task_count() == 0
        assert len(scheduler._task_loops) == 0

    def test_initialization_custom_intervals(self):
        """Test scheduler with custom check intervals."""
        scheduler = MarketScheduler(
            check_interval_24_7=30.0,
            check_interval_scheduled=120.0,
        )
        assert scheduler._check_interval_24_7 == 30.0
        assert scheduler._check_interval_scheduled == 120.0

    def test_schedule_task(self):
        """Test scheduling a task."""
        scheduler = MarketScheduler()

        async def dummy_handler():
            pass

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=dummy_handler,
        )

        assert scheduler.get_task_count() == 1
        task = scheduler.tasks["test_task"]
        assert task.name == "Test Task"
        assert task.enabled is True
        assert task.run_count == 0

    def test_schedule_duplicate_task(self):
        """Test scheduling duplicate task raises error."""
        scheduler = MarketScheduler()

        async def dummy_handler():
            pass

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=dummy_handler,
        )

        with pytest.raises(ValueError, match="already exists"):
            scheduler.schedule_task(
                task_id="test_task",
                name="Test Task 2",
                market_types=[MarketType.CRYPTO],
                handler=dummy_handler,
            )

    def test_unschedule_task(self):
        """Test unscheduling a task."""
        scheduler = MarketScheduler()

        async def dummy_handler():
            pass

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=dummy_handler,
        )

        assert scheduler.unschedule_task("test_task") is True
        assert scheduler.get_task_count() == 0
        assert scheduler.unschedule_task("test_task") is False

    def test_enable_disable_task(self):
        """Test enabling and disabling tasks."""
        scheduler = MarketScheduler()

        async def dummy_handler():
            pass

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=dummy_handler,
            enabled=False,
        )

        assert scheduler.tasks["test_task"].enabled is False
        assert scheduler.enable_task("test_task") is True
        assert scheduler.tasks["test_task"].enabled is True
        assert scheduler.disable_task("test_task") is True
        assert scheduler.tasks["test_task"].enabled is False

    def test_add_holiday(self):
        """Test adding holidays."""
        scheduler = MarketScheduler()
        holiday_date = date(2024, 12, 25)

        scheduler.add_holiday(MarketType.STOCKS_US, holiday_date)

        schedule = scheduler.get_market_schedule(MarketType.STOCKS_US)
        assert holiday_date in schedule.holidays

    def test_remove_holiday(self):
        """Test removing holidays."""
        scheduler = MarketScheduler()
        holiday_date = date(2024, 12, 25)

        scheduler.add_holiday(MarketType.STOCKS_US, holiday_date)
        assert scheduler.remove_holiday(MarketType.STOCKS_US, holiday_date) is True
        assert scheduler.remove_holiday(MarketType.STOCKS_US, holiday_date) is False

    def test_get_task_info(self):
        """Test getting task information."""
        scheduler = MarketScheduler()

        async def dummy_handler():
            pass

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO, MarketType.FOREX],
            handler=dummy_handler,
        )

        info = scheduler.get_task_info("test_task")
        assert info is not None
        assert info["task_id"] == "test_task"
        assert info["name"] == "Test Task"
        assert "crypto" in info["market_types"]
        assert "forex" in info["market_types"]
        assert info["enabled"] is True
        assert info["run_count"] == 0

    def test_list_tasks(self):
        """Test listing tasks."""
        scheduler = MarketScheduler()

        async def dummy_handler():
            pass

        scheduler.schedule_task(
            task_id="crypto_task",
            name="Crypto Task",
            market_types=[MarketType.CRYPTO],
            handler=dummy_handler,
        )

        scheduler.schedule_task(
            task_id="stock_task",
            name="Stock Task",
            market_types=[MarketType.STOCKS_US],
            handler=dummy_handler,
        )

        all_tasks = scheduler.list_tasks()
        assert len(all_tasks) == 2

        crypto_tasks = scheduler.list_tasks(MarketType.CRYPTO)
        assert len(crypto_tasks) == 1
        assert crypto_tasks[0]["task_id"] == "crypto_task"

    def test_is_market_open_24_7(self):
        """Test synchronous check for 24/7 markets."""
        scheduler = MarketScheduler()
        assert scheduler.is_market_open(MarketType.CRYPTO) is True
        assert scheduler.is_market_open(MarketType.FOREX) is True

    def test_is_market_open_scheduled(self):
        """Test synchronous check for scheduled markets."""
        scheduler = MarketScheduler()
        # This is a simplified check - should return False for scheduled markets
        assert scheduler.is_market_open(MarketType.STOCKS_US) is False

    def test_get_market_schedule(self):
        """Test getting market schedule."""
        scheduler = MarketScheduler()
        schedule = scheduler.get_market_schedule(MarketType.STOCKS_US)

        assert schedule is not None
        assert schedule.market_type == MarketType.STOCKS_US
        assert schedule.open_time == time(9, 30)
        assert schedule.close_time == time(16, 0)
        assert schedule.timezone_str == "America/New_York"

    @pytest.mark.asyncio
    async def test_get_market_status_crypto(self):
        """Test market status for crypto (always open)."""
        scheduler = MarketScheduler()
        status = await scheduler.get_market_status(MarketType.CRYPTO)
        assert status == MarketStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_market_status_forex(self):
        """Test market status for forex (always open for trading)."""
        scheduler = MarketScheduler()
        status = await scheduler.get_market_status(MarketType.FOREX)
        assert status == MarketStatus.OPEN

    @pytest.mark.asyncio
    async def test_run_task_once(self):
        """Test running a task once manually."""
        scheduler = MarketScheduler()
        handler_mock = AsyncMock()

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=handler_mock,
        )

        result = await scheduler.run_task_once("test_task")
        assert result is True
        handler_mock.assert_called_once()

        task = scheduler.tasks["test_task"]
        assert task.run_count == 1
        assert task.last_run is not None

    @pytest.mark.asyncio
    async def test_run_task_once_not_found(self):
        """Test running non-existent task."""
        scheduler = MarketScheduler()
        result = await scheduler.run_task_once("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_run_task_once_error(self):
        """Test running a task that raises an error."""
        scheduler = MarketScheduler()

        async def failing_handler():
            raise ValueError("Test error")

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=failing_handler,
        )

        result = await scheduler.run_task_once("test_task")
        assert result is False

        task = scheduler.tasks["test_task"]
        assert task.error_count == 1

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping scheduler."""
        scheduler = MarketScheduler()

        assert await scheduler.start() is True
        assert scheduler.is_running() is True
        assert await scheduler.start() is False  # Already running

        await asyncio.sleep(0.1)  # Give loops time to start

        assert await scheduler.stop() is True
        assert scheduler.is_running() is False
        assert await scheduler.stop() is False  # Already stopped

    @pytest.mark.asyncio
    async def test_wait_until_market_open_24_7(self):
        """Test waiting for 24/7 market (should return immediately)."""
        scheduler = MarketScheduler()

        # Should return immediately for 24/7 markets
        await scheduler.wait_until_market_open(MarketType.CRYPTO)

    @pytest.mark.asyncio
    async def test_task_execution_in_loop(self):
        """Test that tasks are executed in the loop."""
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,  # Fast checks for testing
        )
        handler_mock = AsyncMock()

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=handler_mock,
        )

        await scheduler.start()

        # Wait a bit for task to run
        await asyncio.sleep(0.3)

        await scheduler.stop()

        # Task should have been executed at least once
        assert handler_mock.call_count > 0

    @pytest.mark.asyncio
    async def test_disabled_task_not_executed(self):
        """Test that disabled tasks are not executed."""
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
        )
        handler_mock = AsyncMock()

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=handler_mock,
            enabled=False,
        )

        await scheduler.start()
        await asyncio.sleep(0.3)
        await scheduler.stop()

        # Task should not have been executed
        assert handler_mock.call_count == 0

    @pytest.mark.asyncio
    async def test_task_error_handling(self):
        """Test that errors in tasks don't stop the loop."""
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
        )

        async def failing_handler():
            raise ValueError("Test error")

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=failing_handler,
        )

        await scheduler.start()
        await asyncio.sleep(0.3)
        await scheduler.stop()

        # Task should have been attempted multiple times despite errors
        task = scheduler.tasks["test_task"]
        assert task.error_count > 0
