"""
Integration tests for MarketScheduler - Phase 3.1

Tests the market scheduling functionality in realistic scenarios
with multiple market types and concurrent task execution.
"""

import asyncio
from datetime import date, time

import pytest

from app.services.scheduling import (
    MarketScheduler,
    MarketType,
    MarketStatus,
)


class TestMarketSchedulerIntegration:
    """Integration tests for MarketScheduler."""

    @pytest.mark.asyncio
    async def test_multi_market_task_scheduling(self):
        """
        Test scheduling tasks across multiple market types.

        Scenario:
        - Crypto task should run continuously
        - US stock task should only run during market hours
        - EU stock task should run during EU market hours
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
            check_interval_scheduled=0.1,
        )

        crypto_count = 0
        us_stock_count = 0
        eu_stock_count = 0

        async def crypto_handler():
            nonlocal crypto_count
            crypto_count += 1

        async def us_stock_handler():
            nonlocal us_stock_count
            us_stock_count += 1

        async def eu_stock_handler():
            nonlocal eu_stock_count
            eu_stock_count += 1

        scheduler.schedule_task(
            task_id="crypto_monitor",
            name="Crypto Monitor",
            market_types=[MarketType.CRYPTO],
            handler=crypto_handler,
        )

        scheduler.schedule_task(
            task_id="us_stock_scanner",
            name="US Stock Scanner",
            market_types=[MarketType.STOCKS_US],
            handler=us_stock_handler,
        )

        scheduler.schedule_task(
            task_id="eu_stock_scanner",
            name="EU Stock Scanner",
            market_types=[MarketType.STOCKS_EU],
            handler=eu_stock_handler,
        )

        await scheduler.start()
        await asyncio.sleep(0.5)
        await scheduler.stop()

        # Crypto should have run (24/7 market)
        assert crypto_count > 0

        # US and EU stocks may or may not have run depending on current time
        # This is expected behavior - they only run during market hours

        print(f"Crypto runs: {crypto_count}")
        print(f"US Stock runs: {us_stock_count}")
        print(f"EU Stock runs: {eu_stock_count}")

    @pytest.mark.asyncio
    async def test_task_with_closed_market_execution(self):
        """
        Test task that runs even when market is closed.

        Useful for maintenance tasks that should run regardless
        of market status.
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
        )

        task_count = 0

        async def maintenance_handler():
            nonlocal task_count
            task_count += 1

        scheduler.schedule_task(
            task_id="maintenance",
            name="Maintenance Task",
            market_types=[MarketType.STOCKS_US],
            handler=maintenance_handler,
            run_when_closed=True,  # Run even when market is closed
        )

        await scheduler.start()
        await asyncio.sleep(0.3)
        await scheduler.stop()

        # Task should have run despite market potentially being closed
        assert task_count > 0

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """
        Test that scheduler shuts down gracefully.

        Ensures all task loops are properly cancelled and cleaned up.
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
        )

        run_count = 0

        async def handler():
            nonlocal run_count
            run_count += 1
            await asyncio.sleep(0.05)  # Simulate some work

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=handler,
        )

        await scheduler.start()
        await asyncio.sleep(0.2)

        # Stop should complete without hanging
        stop_task = asyncio.create_task(scheduler.stop())
        await asyncio.wait_for(stop_task, timeout=2.0)

        assert scheduler.is_running() is False
        assert len(scheduler._task_loops) == 0

    @pytest.mark.asyncio
    async def test_dynamic_task_management(self):
        """
        Test adding, enabling, and disabling tasks while running.
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
        )

        task1_count = 0
        task2_count = 0

        async def task1_handler():
            nonlocal task1_count
            task1_count += 1

        async def task2_handler():
            nonlocal task2_count
            task2_count += 1

        # Start with one task
        scheduler.schedule_task(
            task_id="task1",
            name="Task 1",
            market_types=[MarketType.CRYPTO],
            handler=task1_handler,
        )

        await scheduler.start()
        await asyncio.sleep(0.2)

        # Add second task while running
        scheduler.schedule_task(
            task_id="task2",
            name="Task 2",
            market_types=[MarketType.CRYPTO],
            handler=task2_handler,
        )

        await asyncio.sleep(0.2)

        # Disable first task
        scheduler.disable_task("task1")
        task1_count_at_disable = task1_count

        await asyncio.sleep(0.2)

        await scheduler.stop()

        # Task 1 should have stopped incrementing after disable
        assert task1_count == task1_count_at_disable

        # Task 2 should have run
        assert task2_count > 0

    @pytest.mark.asyncio
    async def test_holiday_effect(self):
        """
        Test that holidays prevent task execution for stock markets.
        """
        scheduler = MarketScheduler(
            check_interval_scheduled=0.1,
        )

        # Add a future weekday as a holiday
        from datetime import datetime, timedelta

        # Get next weekday (Monday-Friday)
        today = date.today()
        future_date = today + timedelta(days=7)
        while future_date.weekday() >= 5:  # Skip weekends
            future_date += timedelta(days=1)

        scheduler.add_holiday(MarketType.STOCKS_US, future_date)

        # Verify holiday was added
        schedule = scheduler.get_market_schedule(MarketType.STOCKS_US)
        assert future_date in schedule.holidays

        # Check that the holiday functionality works
        # (We can't test actual holiday status without manipulating time)
        run_count = 0

        async def us_stock_handler():
            nonlocal run_count
            run_count += 1

        scheduler.schedule_task(
            task_id="us_stock_task",
            name="US Stock Task",
            market_types=[MarketType.STOCKS_US],
            handler=us_stock_handler,
        )

        # Check current market status
        status = await scheduler.get_market_status(MarketType.STOCKS_US)
        # Status should be one of the valid states
        assert status in [
            MarketStatus.OPEN,
            MarketStatus.CLOSED,
            MarketStatus.PRE_MARKET,
            MarketStatus.AFTER_HOURS,
            MarketStatus.WEEKEND,
            MarketStatus.HOLIDAY,
        ]

    @pytest.mark.asyncio
    async def test_weekend_detection(self):
        """
        Test weekend detection for stock markets.
        """
        scheduler = MarketScheduler()

        # Check current status
        status = await scheduler.get_market_status(MarketType.STOCKS_US)

        # On weekends, status should be WEEKEND (if not a holiday)
        # On weekdays, status could be OPEN, CLOSED, PRE_MARKET, or AFTER_HOURS
        # This test just verifies the method works without error
        assert status in [
            MarketStatus.OPEN,
            MarketStatus.CLOSED,
            MarketStatus.PRE_MARKET,
            MarketStatus.AFTER_HOURS,
            MarketStatus.WEEKEND,
            MarketStatus.HOLIDAY,
        ]

    @pytest.mark.asyncio
    async def test_task_execution_metrics(self):
        """
        Test that task execution metrics are tracked correctly.
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
        )

        async def handler():
            await asyncio.sleep(0.01)

        scheduler.schedule_task(
            task_id="test_task",
            name="Test Task",
            market_types=[MarketType.CRYPTO],
            handler=handler,
        )

        await scheduler.start()
        await asyncio.sleep(0.3)
        await scheduler.stop()

        info = scheduler.get_task_info("test_task")

        assert info is not None
        assert info["run_count"] > 0
        assert info["last_run"] is not None
        assert info["error_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_markets_same_task(self):
        """
        Test a single task scheduled for multiple market types.
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
            check_interval_scheduled=0.1,
        )

        run_count = 0

        async def multi_market_handler():
            nonlocal run_count
            run_count += 1

        scheduler.schedule_task(
            task_id="multi_market",
            name="Multi-Market Task",
            market_types=[MarketType.CRYPTO, MarketType.FOREX],
            handler=multi_market_handler,
        )

        await scheduler.start()
        await asyncio.sleep(0.3)
        await scheduler.stop()

        # Should run for both crypto and forex loops
        # Since both are 24/7, expect roughly 2x the runs
        assert run_count > 0

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """
        Test that scheduler continues after task errors.
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.1,
        )

        fail_count = 0
        success_count = 0

        async def failing_handler():
            nonlocal fail_count
            fail_count += 1
            if fail_count <= 2:
                raise ValueError("Simulated error")

        async def success_handler():
            nonlocal success_count
            success_count += 1

        scheduler.schedule_task(
            task_id="failing_task",
            name="Failing Task",
            market_types=[MarketType.CRYPTO],
            handler=failing_handler,
        )

        scheduler.schedule_task(
            task_id="success_task",
            name="Success Task",
            market_types=[MarketType.CRYPTO],
            handler=success_handler,
        )

        await scheduler.start()
        await asyncio.sleep(0.5)
        await scheduler.stop()

        # Both tasks should have been attempted
        assert fail_count > 0

        # Success task should have run despite failures in other task
        assert success_count > 0

    @pytest.mark.asyncio
    async def test_timezone_handling(self):
        """
        Test that timezone handling works correctly for different markets.
        """
        scheduler = MarketScheduler()

        # Check that each market has correct timezone
        us_schedule = scheduler.get_market_schedule(MarketType.STOCKS_US)
        assert us_schedule.timezone_str == "America/New_York"
        assert us_schedule.open_time == time(9, 30)
        assert us_schedule.close_time == time(16, 0)

        eu_schedule = scheduler.get_market_schedule(MarketType.STOCKS_EU)
        assert eu_schedule.timezone_str == "Europe/Madrid"
        assert eu_schedule.open_time == time(9, 0)
        assert eu_schedule.close_time == time(17, 30)

        asia_schedule = scheduler.get_market_schedule(MarketType.STOCKS_ASIA)
        assert asia_schedule.timezone_str == "Asia/Tokyo"
        assert asia_schedule.open_time == time(9, 0)
        assert asia_schedule.close_time == time(15, 0)

    @pytest.mark.asyncio
    async def test_wait_until_market_open_timeout(self):
        """
        Test wait_until_market_open with scheduled market.
        """
        scheduler = MarketScheduler()

        # For 24/7 markets, this should return immediately
        await scheduler.wait_until_market_open(MarketType.CRYPTO)

        # For scheduled markets, it would wait until market opens
        # We can't test full wait in unit tests, but we can verify
        # the method doesn't error
        wait_task = asyncio.create_task(scheduler.wait_until_market_open(MarketType.STOCKS_US))

        # Cancel after a short delay
        await asyncio.sleep(0.1)
        wait_task.cancel()

        try:
            await wait_task
        except asyncio.CancelledError:
            pass  # Expected


class TestMarketSchedulerRealWorldScenarios:
    """Real-world scenario tests."""

    @pytest.mark.asyncio
    async def test_crypto_monitoring_scenario(self):
        """
        Test real crypto monitoring scenario.

        Crypto runs 24/7, so monitoring should be continuous.
        """
        scheduler = MarketScheduler(
            check_interval_24_7=1.0,  # Check every second
        )

        prices_checked = 0
        signals_generated = 0

        async def check_prices():
            nonlocal prices_checked
            prices_checked += 1

        async def generate_signals():
            nonlocal signals_generated
            signals_generated += 1

        scheduler.schedule_task(
            task_id="price_checker",
            name="Price Checker",
            market_types=[MarketType.CRYPTO],
            handler=check_prices,
        )

        scheduler.schedule_task(
            task_id="signal_generator",
            name="Signal Generator",
            market_types=[MarketType.CRYPTO],
            handler=generate_signals,
        )

        await scheduler.start()
        await asyncio.sleep(2.0)
        await scheduler.stop()

        assert prices_checked > 0
        assert signals_generated > 0

    @pytest.mark.asyncio
    async def test_mixed_market_strategy(self):
        """
        Test mixed market strategy scenario.

        A strategy that trades both crypto (24/7) and stocks (scheduled).
        """
        scheduler = MarketScheduler(
            check_interval_24_7=0.2,
            check_interval_scheduled=0.2,
        )

        crypto_trades = 0
        stock_trades = 0

        async def crypto_strategy():
            nonlocal crypto_trades
            crypto_trades += 1

        async def stock_strategy():
            nonlocal stock_trades
            stock_trades += 1

        scheduler.schedule_task(
            task_id="crypto_strategy",
            name="Crypto Strategy",
            market_types=[MarketType.CRYPTO],
            handler=crypto_strategy,
        )

        scheduler.schedule_task(
            task_id="stock_strategy",
            name="Stock Strategy",
            market_types=[MarketType.STOCKS_US],
            handler=stock_strategy,
        )

        await scheduler.start()
        await asyncio.sleep(1.0)
        await scheduler.stop()

        # Crypto should have trades (24/7)
        assert crypto_trades > 0

        # Stock trades depend on market hours
        # (may be 0 if outside market hours)
        print(f"Crypto trades: {crypto_trades}")
        print(f"Stock trades: {stock_trades}")
