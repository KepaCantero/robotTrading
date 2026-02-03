#!/usr/bin/env python
"""
Market Scheduler Usage Examples

This file demonstrates how to use the MarketScheduler for multi-market
algorithmic trading operations.
"""

import asyncio
import logging
from datetime import date

from app.services.scheduling import (
    MarketScheduler,
    MarketType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Basic 24/7 Crypto Monitoring
# ============================================================================


async def example_1_crypto_monitoring():
    """
    Example 1: Basic 24/7 crypto monitoring.

    Crypto markets run 24/7, so monitoring tasks should run continuously.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 1: 24/7 Crypto Monitoring")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler(check_interval_24_7=5.0)

    # Define monitoring task
    async def monitor_crypto_prices():
        """
        Monitor crypto prices and generate signals.

        This runs continuously since crypto is 24/7.
        """
        logger.info("Checking crypto prices...")
        # Your price monitoring logic here
        # - Fetch prices from exchange API
        # - Calculate indicators
        # - Generate trading signals

    # Schedule the monitoring task
    scheduler.schedule_task(
        task_id="crypto_price_monitor",
        name="Crypto Price Monitor",
        market_types=[MarketType.CRYPTO],
        handler=monitor_crypto_prices,
    )

    # Start the scheduler
    await scheduler.start()

    # Run for 30 seconds (in production, run indefinitely)
    logger.debug("Running crypto monitoring for 30 seconds...")
    await asyncio.sleep(30)

    # Stop the scheduler
    await scheduler.stop()
    logger.debug("Crypto monitoring stopped\n")


# ============================================================================
# EXAMPLE 2: Multi-Market Strategy
# ============================================================================


async def example_2_multi_market_strategy():
    """
    Example 2: Multi-market strategy trading both crypto and stocks.

    Demonstrates how to schedule different tasks for different markets.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 2: Multi-Market Strategy")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler(
        check_interval_24_7=5.0,
        check_interval_scheduled=5.0,
    )

    # Crypto strategy (runs 24/7)
    async def crypto_momentum_strategy():
        logger.info("Executing crypto momentum strategy...")
        # Your crypto trading logic here

    # US Stock strategy (runs 9:30-16:00 ET only)
    async def us_stock_momentum_strategy():
        logger.info("Executing US stock momentum strategy...")
        # Your stock trading logic here

    # EU Stock strategy (runs 9:00-17:30 CET only)
    async def eu_stock_momentum_strategy():
        logger.info("Executing EU stock momentum strategy...")
        # Your EU stock trading logic here

    # Schedule all strategies
    scheduler.schedule_task(
        task_id="crypto_momentum",
        name="Crypto Momentum Strategy",
        market_types=[MarketType.CRYPTO],
        handler=crypto_momentum_strategy,
    )

    scheduler.schedule_task(
        task_id="us_stock_momentum",
        name="US Stock Momentum Strategy",
        market_types=[MarketType.STOCKS_US],
        handler=us_stock_momentum_strategy,
    )

    scheduler.schedule_task(
        task_id="eu_stock_momentum",
        name="EU Stock Momentum Strategy",
        market_types=[MarketType.STOCKS_EU],
        handler=eu_stock_momentum_strategy,
    )

    # Start scheduler
    await scheduler.start()

    # Run for 30 seconds
    logger.debug("Running multi-market strategy for 30 seconds...")
    await asyncio.sleep(30)

    # Stop scheduler
    await scheduler.stop()
    logger.debug("Multi-market strategy stopped\n")


# ============================================================================
# EXAMPLE 3: Maintenance Tasks (Run Even When Closed)
# ============================================================================


async def example_3_maintenance_tasks():
    """
    Example 3: Maintenance tasks that run regardless of market status.

    Useful for data synchronization, health checks, etc.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 3: Maintenance Tasks")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler(
        check_interval_scheduled=5.0,
    )

    # Data synchronization task
    async def sync_market_data():
        logger.info("Synchronizing market data...")
        # Your data sync logic here

    # Health check task
    async def health_check():
        logger.info("Performing system health check...")
        # Your health check logic here

    # Schedule maintenance tasks
    # Note: run_when_closed=True allows execution even when market is closed
    scheduler.schedule_task(
        task_id="data_sync",
        name="Market Data Synchronization",
        market_types=[MarketType.STOCKS_US],
        handler=sync_market_data,
        run_when_closed=True,
    )

    scheduler.schedule_task(
        task_id="health_check",
        name="System Health Check",
        market_types=[MarketType.CRYPTO],
        handler=health_check,
        run_when_closed=True,
    )

    await scheduler.start()

    logger.debug("Running maintenance tasks for 20 seconds...")
    await asyncio.sleep(20)

    await scheduler.stop()
    logger.debug("Maintenance tasks stopped\n")


# ============================================================================
# EXAMPLE 4: Dynamic Task Management
# ============================================================================


async def example_4_dynamic_task_management():
    """
    Example 4: Dynamic task management (enable/disable/add/remove).

    Demonstrates how to manage tasks while the scheduler is running.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 4: Dynamic Task Management")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler(check_interval_24_7=3.0)

    async def task_handler():
        logger.info("Task executed")

    # Start with one task
    scheduler.schedule_task(
        task_id="task_1",
        name="Task 1",
        market_types=[MarketType.CRYPTO],
        handler=task_handler,
    )

    await scheduler.start()

    logger.debug("Running with Task 1 for 10 seconds...")
    await asyncio.sleep(10)

    # Add another task while running
    logger.debug("Adding Task 2...")
    scheduler.schedule_task(
        task_id="task_2",
        name="Task 2",
        market_types=[MarketType.CRYPTO],
        handler=task_handler,
    )

    logger.debug("Running with Task 1 and Task 2 for 10 seconds...")
    await asyncio.sleep(10)

    # Disable Task 1
    logger.debug("Disabling Task 1...")
    scheduler.disable_task("task_1")

    logger.debug("Running with only Task 2 for 10 seconds...")
    await asyncio.sleep(10)

    # Re-enable Task 1
    logger.debug("Re-enabling Task 1...")
    scheduler.enable_task("task_1")

    logger.debug("Running with both tasks again for 10 seconds...")
    await asyncio.sleep(10)

    await scheduler.stop()
    logger.debug("Dynamic task management demo stopped\n")


# ============================================================================
# EXAMPLE 5: Market Status Monitoring
# ============================================================================


async def example_5_market_status_monitoring():
    """
    Example 5: Monitor market status for different markets.

    Demonstrates how to check if markets are open, closed, on holiday, etc.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 5: Market Status Monitoring")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler()

    # Check status of all markets
    markets = [
        MarketType.CRYPTO,
        MarketType.FOREX,
        MarketType.STOCKS_US,
        MarketType.STOCKS_EU,
        MarketType.STOCKS_ASIA,
    ]

    logger.debug("Current market statuses:")
    for market in markets:
        status = await scheduler.get_market_status(market)
        schedule = scheduler.get_market_schedule(market)

        logger.debug(f"\n{market.value.upper()}:")
        logger.debug(f"  Status: {status.value}")

        if schedule.open_time:
            logger.debug(f"  Hours: {schedule.open_time} - {schedule.close_time}")
            logger.debug(f"  Timezone: {schedule.timezone_str}")
        else:
            logger.debug("  Hours: 24/7")

        if schedule.holidays:
            logger.debug(f"  Holidays: {len(schedule.holidays)} configured")

    logger.debug("\n")


# ============================================================================
# EXAMPLE 6: Holiday Management
# ============================================================================


async def example_6_holiday_management():
    """
    Example 6: Managing market holidays.

    Demonstrates how to add and remove holidays for markets.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 6: Holiday Management")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler()

    # Add some holidays
    independence_day = date(2024, 7, 4)
    christmas = date(2024, 12, 25)
    new_year = date(2025, 1, 1)

    logger.debug("Adding holidays for US market...")
    scheduler.add_holiday(MarketType.STOCKS_US, independence_day)
    scheduler.add_holiday(MarketType.STOCKS_US, christmas)
    scheduler.add_holiday(MarketType.STOCKS_US, new_year)

    # Check added holidays
    us_schedule = scheduler.get_market_schedule(MarketType.STOCKS_US)
    logger.debug(f"\nUS Market holidays configured: {len(us_schedule.holidays)}")
    for holiday in sorted(us_schedule.holidays):
        logger.debug(f"  - {holiday}")

    # Remove a holiday
    logger.debug(f"\nRemoving {new_year} from holidays...")
    scheduler.remove_holiday(MarketType.STOCKS_US, new_year)

    logger.debug(f"Remaining holidays: {len(us_schedule.holidays)}")
    for holiday in sorted(us_schedule.holidays):
        logger.debug(f"  - {holiday}")

    logger.debug("\n")


# ============================================================================
# EXAMPLE 7: Task Information and Metrics
# ============================================================================


async def example_7_task_metrics():
    """
    Example 7: Tracking task execution metrics.

    Demonstrates how to monitor task performance and execution counts.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 7: Task Execution Metrics")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler(check_interval_24_7=2.0)

    execution_count = 0

    async def monitored_task():
        nonlocal execution_count
        execution_count += 1
        logger.info(f"Task execution #{execution_count}")

    scheduler.schedule_task(
        task_id="monitored_task",
        name="Monitored Task",
        market_types=[MarketType.CRYPTO],
        handler=monitored_task,
    )

    await scheduler.start()

    logger.debug("Running task for 10 seconds...")
    await asyncio.sleep(10)

    # Get task information
    task_info = scheduler.get_task_info("monitored_task")

    logger.debug("\nTask Metrics:")
    logger.debug(f"  Task ID: {task_info['task_id']}")
    logger.debug(f"  Name: {task_info['name']}")
    logger.debug(f"  Executions: {task_info['run_count']}")
    logger.debug(f"  Errors: {task_info['error_count']}")
    logger.debug(f"  Last Run: {task_info['last_run']}")
    logger.debug(f"  Enabled: {task_info['enabled']}")

    # List all tasks
    logger.debug(f"\nTotal Tasks: {scheduler.get_task_count()}")
    logger.debug(f"Enabled Tasks: {scheduler.get_enabled_task_count()}")

    await scheduler.stop()
    logger.debug("\n")


# ============================================================================
# EXAMPLE 8: Waiting for Market Open
# ============================================================================


async def example_8_wait_for_market_open():
    """
    Example 8: Waiting for market to open.

    Demonstrates how to wait until a market opens before executing logic.
    """

    logger.debug("\n" + "=" * 70)
    logger.debug("EXAMPLE 8: Waiting for Market Open")
    logger.debug("=" * 70 + "\n")

    scheduler = MarketScheduler()

    # For 24/7 markets, this returns immediately
    logger.debug("Waiting for crypto market to open...")
    await scheduler.wait_until_market_open(MarketType.CRYPTO)
    logger.debug("Crypto market is open (24/7)")

    # For scheduled markets, this would wait until opening time
    # (commented out to avoid long wait in demo)
    # print("\nWaiting for US stock market to open...")
    # await scheduler.wait_until_market_open(MarketType.STOCKS_US)
    # print("US stock market is now open")

    logger.debug("\n")


# ============================================================================
# MAIN DEMO
# ============================================================================


async def main():
    """Run all examples."""

    logger.debug("\n" + "=" * 70)
    logger.debug("MARKET SCHEDULER USAGE EXAMPLES")
    logger.debug("=" * 70)

    # Run examples
    await example_1_crypto_monitoring()
    await example_2_multi_market_strategy()
    await example_3_maintenance_tasks()
    await example_4_dynamic_task_management()
    await example_5_market_status_monitoring()
    await example_6_holiday_management()
    await example_7_task_metrics()
    await example_8_wait_for_market_open()

    logger.debug("=" * 70)
    logger.debug("ALL EXAMPLES COMPLETED")
    logger.debug("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
