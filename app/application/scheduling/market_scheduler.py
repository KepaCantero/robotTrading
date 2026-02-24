"""
Market Scheduler - Schedule tasks based on market hours.

Handles:
- 24/7 markets (crypto, forex) - continuous operation
- Stock markets (6.5h/day) - US: 9:30-16:00 ET, EU: 9:00-17:30 CET, Asia: 9:00-15:00 JST
- Market holidays
- Timezone differences (US, EU, Asia)
- Graceful startup/shutdown

Phase 3.1: 24/7 Market Scheduler
Critical for multi-market support where crypto/forex run 24/7 but stocks
have limited trading hours. Efficiently manages CPU usage by only running
tasks when markets are open.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pytz

from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class MarketType(Enum):
    """Types of markets with different hours."""

    CRYPTO = "crypto"  # 24/7
    FOREX = "forex"  # 24/5
    STOCKS_US = "stocks_us"  # 9:30-16:00 ET
    STOCKS_EU = "stocks_eu"  # 9:00-17:30 CET
    STOCKS_ASIA = "stocks_asia"  # 9:00-15:00 JST


class MarketStatus(Enum):
    """Current status of a market."""

    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"


@dataclass
class MarketSchedule:
    """Schedule information for a market."""

    market_type: MarketType
    timezone_str: str
    open_time: Optional[time] = None  # None for 24/7
    close_time: Optional[time] = None  # None for 24/7
    lunch_start: Optional[time] = None
    lunch_end: Optional[time] = None
    weekends: bool = False  # Trades on weekends
    holidays: List[date] = field(default_factory=list)

    def is_24_7(self) -> bool:
        """Check if market is 24/7."""
        return self.open_time is None


# Default market schedules with proper timezone support
MARKET_SCHEDULES = {
    MarketType.CRYPTO: MarketSchedule(
        market_type=MarketType.CRYPTO,
        timezone_str="UTC",
        open_time=None,  # 24/7
        close_time=None,
        weekends=True,
    ),
    MarketType.FOREX: MarketSchedule(
        market_type=MarketType.FOREX,
        timezone_str="UTC",
        open_time=None,  # 24/5 (effectively 24/7 for trading)
        close_time=None,
        weekends=False,  # Closed weekends
    ),
    MarketType.STOCKS_US: MarketSchedule(
        market_type=MarketType.STOCKS_US,
        timezone_str="America/New_York",
        open_time=time(9, 30),
        close_time=time(16, 0),
        weekends=False,
    ),
    MarketType.STOCKS_EU: MarketSchedule(
        market_type=MarketType.STOCKS_EU,
        timezone_str="Europe/Madrid",
        open_time=time(9, 0),
        close_time=time(17, 30),
        lunch_start=None,  # Most EU exchanges don't have lunch breaks
        lunch_end=None,
        weekends=False,
    ),
    MarketType.STOCKS_ASIA: MarketSchedule(
        market_type=MarketType.STOCKS_ASIA,
        timezone_str="Asia/Tokyo",
        open_time=time(9, 0),
        close_time=time(15, 0),
        lunch_start=time(11, 30),  # Tokyo Stock Exchange has lunch break
        lunch_end=time(12, 30),
        weekends=False,
    ),
}


@dataclass
class ScheduledTask:
    """A task scheduled for specific market conditions."""

    task_id: str
    name: str
    market_types: List[MarketType]
    handler: Callable
    run_when_closed: bool = False
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class MarketScheduler:
    """
    Schedule tasks based on market hours.

    Efficiently manages CPU usage by:
    - Running 24/7 tasks continuously with appropriate intervals
    - Scheduling 6.5h market tasks during open hours only
    - Respecting market holidays and weekends
    - Handling timezone differences across markets
    - Providing graceful startup and shutdown

    Attributes:
        schedules: Dictionary of market schedules by MarketType
        tasks: Dictionary of scheduled tasks by task_id
        _task_loops: Background asyncio tasks for each market type
        _is_running: Whether the scheduler is currently running
    """

    def __init__(
        self,
        schedules: Optional[Dict[MarketType, MarketSchedule]] = None,
        check_interval_24_7: float = 60.0,
        check_interval_scheduled: float = 60.0,
    ):
        """
        Initialize market scheduler.

        Args:
            schedules: Custom market schedules (defaults to MARKET_SCHEDULES)
            check_interval_24_7: Seconds between checks for 24/7 markets (default: 60)
            check_interval_scheduled: Seconds between checks for scheduled markets (default: 60)
        """
        self.schedules = schedules or MARKET_SCHEDULES.copy()
        self.tasks: Dict[str, ScheduledTask] = {}
        self._task_loops: Dict[str, asyncio.Task] = {}
        self._is_running = False
        self._check_interval_24_7 = check_interval_24_7
        self._check_interval_scheduled = check_interval_scheduled

        logger.info("MarketScheduler initialized")

    async def start(self) -> bool:
        """
        Start all scheduled tasks.

        Creates background asyncio tasks for each market type.
        Each task loop monitors its market and runs scheduled tasks
        when the market is open.

        Returns:
            True if started successfully, False if already running

        Example:
            >>> scheduler = MarketScheduler()
            >>> await scheduler.start()
            True
        """
        if self._is_running:
            logger.warning("MarketScheduler already running")
            return False

        self._is_running = True

        # Start task loops for all market types
        for market_type in MarketType:
            task = asyncio.create_task(self._run_market_tasks(market_type))
            self._task_loops[market_type.value] = task

        logger.info(f"MarketScheduler started with {len(self._task_loops)} market loops")
        return True

    async def stop(self) -> bool:
        """
        Stop all scheduled tasks.

        Cancels all background task loops and waits for them to complete.

        Returns:
            True if stopped successfully, False if not running

        Example:
            >>> await scheduler.stop()
            True
        """
        if not self._is_running:
            logger.warning("MarketScheduler not running")
            return False

        self._is_running = False

        # Cancel all task loops
        for task in self._task_loops.values():
            task.cancel()

        # Wait for tasks to complete cancellation
        if self._task_loops:
            await asyncio.gather(*self._task_loops.values(), return_exceptions=True)

        self._task_loops.clear()

        logger.info("MarketScheduler stopped")
        return True

    def schedule_task(
        self,
        task_id: str,
        name: str,
        market_types: List[MarketType],
        handler: Callable,
        run_when_closed: bool = False,
        enabled: bool = True,
    ) -> None:
        """
        Schedule a task for specific market types.

        Args:
            task_id: Unique task identifier
            name: Human-readable task name
            market_types: List of market types to run on
            handler: Async callable to execute
            run_when_closed: If True, runs even when market is closed
            enabled: If False, task is registered but not executed

        Raises:
            ValueError: If task_id already exists

        Example:
            >>> async def my_handler():
            ...     print("Running task...")
            >>>
            >>> scheduler.schedule_task(
            ...     task_id="monitor_1",
            ...     name="Market Monitor",
            ...     market_types=[MarketType.CRYPTO],
            ...     handler=my_handler
            ... )
        """
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id} already exists")

        task = ScheduledTask(
            task_id=task_id,
            name=name,
            market_types=market_types,
            handler=handler,
            run_when_closed=run_when_closed,
            enabled=enabled,
        )
        self.tasks[task_id] = task
        logger.info(f"Scheduled task: {name} ({task_id}) for " f"{[m.value for m in market_types]}")

    def unschedule_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.

        Args:
            task_id: Task identifier to remove

        Returns:
            True if task was removed, False if not found

        Example:
            >>> scheduler.unschedule_task("monitor_1")
            True
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Unscheduled task: {task_id}")
            return True
        return False

    def enable_task(self, task_id: str) -> bool:
        """
        Enable a scheduled task.

        Args:
            task_id: Task identifier to enable

        Returns:
            True if task was enabled, False if not found

        Example:
            >>> scheduler.enable_task("monitor_1")
            True
        """
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            logger.info(f"Enabled task: {task_id}")
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """
        Disable a scheduled task.

        Args:
            task_id: Task identifier to disable

        Returns:
            True if task was disabled, False if not found

        Example:
            >>> scheduler.disable_task("monitor_1")
            True
        """
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            logger.info(f"Disabled task: {task_id}")
            return True
        return False

    async def _run_market_tasks(self, market_type: MarketType) -> None:
        """
        Run tasks for a specific market type.

        This is the main loop for a market type. It continuously:
        1. Checks if the market is open
        2. Gets all tasks scheduled for this market
        3. Runs enabled tasks if market is open (or if task allows closed execution)
        4. Waits for the appropriate interval before next check

        Args:
            market_type: Market type to run tasks for
        """
        schedule = self.schedules.get(market_type)

        if not schedule:
            logger.warning(f"No schedule for {market_type.value}")
            return

        logger.info(f"Starting task loop for {market_type.value}")

        while self._is_running:
            try:
                # Check if market is open
                status = await self.get_market_status(market_type)

                # Get tasks for this market
                tasks = [
                    t for t in self.tasks.values() if market_type in t.market_types and t.enabled
                ]

                # Determine if we should run tasks
                should_run = status == MarketStatus.OPEN

                for task in tasks:
                    # Run if market is open or task allows closed execution
                    if should_run or task.run_when_closed:
                        try:
                            await task.handler()
                            task.last_run = utc_now()
                            task.run_count += 1
                        except asyncio.CancelledError:  # pylint: disable=try-except-raise
                            raise
                        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                            task.error_count += 1
                            logger.error(
                                f"Error in task {task.name} ({task.task_id}): {e}",
                                exc_info=True,
                            )

                # Calculate wait time based on market type
                if schedule.is_24_7():
                    # 24/7 markets: run frequently
                    wait_time = self._check_interval_24_7
                else:
                    # Scheduled markets: wait until next check
                    wait_time = self._check_interval_scheduled

                await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                logger.info(f"Task loop for {market_type.value} cancelled")
                break
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(
                    f"Error in task loop for {market_type.value}: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(60.0)

        logger.info(f"Task loop for {market_type.value} ended")

    async def get_market_status(self, market_type: MarketType) -> MarketStatus:
        """
        Get current status of a market.

        Args:
            market_type: Market type to check

        Returns:
            Current market status

        Example:
            >>> status = await scheduler.get_market_status(MarketType.CRYPTO)
            >>> status
            <MarketStatus.OPEN: 'open'>
        """
        schedule = self.schedules.get(market_type)

        if not schedule:
            logger.warning(f"No schedule found for {market_type.value}")
            return MarketStatus.CLOSED

        # 24/7 markets are always open
        if schedule.is_24_7():
            return MarketStatus.OPEN

        # Check weekend
        now_utc = utc_now()

        # Get market timezone
        tz = pytz.timezone(schedule.timezone_str)
        now_local = now_utc.astimezone(tz)

        # Check weekend (Saturday=5, Sunday=6)
        if now_local.weekday() >= 5:
            return MarketStatus.WEEKEND

        # Check holiday
        local_date = now_local.date()
        if local_date in schedule.holidays:
            return MarketStatus.HOLIDAY

        # Check hours
        current_time = now_local.time()

        # Before market open
        if current_time < schedule.open_time:
            return MarketStatus.CLOSED

        # After market close
        if current_time > schedule.close_time:
            return MarketStatus.AFTER_HOURS

        # Check lunch break (if applicable)
        if schedule.lunch_start and schedule.lunch_end:
            if schedule.lunch_start <= current_time <= schedule.lunch_end:
                return MarketStatus.CLOSED

        # Market is open
        return MarketStatus.OPEN

    async def wait_until_market_open(self, market_type: MarketType) -> None:
        """
        Wait until market opens.

        Blocks until the specified market opens. Useful for initialization
        tasks that need to run only when markets are open.

        Args:
            market_type: Market type to wait for

        Example:
            >>> await scheduler.wait_until_market_open(MarketType.STOCKS_US)
        """
        schedule = self.schedules.get(market_type)

        if schedule.is_24_7():
            logger.info(f"{market_type.value} is 24/7, not waiting")
            return  # Already open

        logger.info(f"Waiting for {market_type.value} to open...")

        while self._is_running:
            status = await self.get_market_status(market_type)

            if status == MarketStatus.OPEN:
                logger.info(f"{market_type.value} is now open")
                return

            # Wait 1 minute before checking again
            await asyncio.sleep(60.0)

    def is_market_open(self, market_type: MarketType) -> bool:
        """
        Synchronous check if market is open.

        This is a simplified synchronous version for quick checks.
        For accurate results, use get_market_status() instead.

        Args:
            market_type: Market type to check

        Returns:
            True if market is open (simplified check)

        Example:
            >>> if scheduler.is_market_open(MarketType.CRYPTO):
            ...     print("Crypto market is open")
        """
        schedule = self.schedules.get(market_type)
        if not schedule:
            return False

        # 24/7 markets are always open
        return schedule.is_24_7()

    def add_holiday(self, market_type: MarketType, holiday_date: date) -> None:
        """
        Add a holiday for a market.

        Args:
            market_type: Market type to add holiday for
            holiday_date: Date of the holiday

        Example:
            >>> from datetime import date
            >>> scheduler.add_holiday(
            ...     MarketType.STOCKS_US,
            ...     date(2024, 12, 25)  # Christmas
            ... )
        """
        schedule = self.schedules.get(market_type)
        if schedule:
            if holiday_date not in schedule.holidays:
                schedule.holidays.append(holiday_date)
                logger.info(f"Added holiday {holiday_date} for {market_type.value}")

    def remove_holiday(self, market_type: MarketType, holiday_date: date) -> bool:
        """
        Remove a holiday for a market.

        Args:
            market_type: Market type to remove holiday from
            holiday_date: Date of the holiday to remove

        Returns:
            True if holiday was removed, False if not found

        Example:
            >>> from datetime import date
            >>> scheduler.remove_holiday(
            ...     MarketType.STOCKS_US,
            ...     date(2024, 12, 25)
            ... )
        """
        schedule = self.schedules.get(market_type)
        if schedule and holiday_date in schedule.holidays:
            schedule.holidays.remove(holiday_date)
            logger.info(f"Removed holiday {holiday_date} for {market_type.value}")
            return True
        return False

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a scheduled task.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with task information or None if not found

        Example:
            >>> info = scheduler.get_task_info("monitor_1")
            >>> print(info['name'], info['run_count'])
        """
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "name": task.name,
            "market_types": [m.value for m in task.market_types],
            "enabled": task.enabled,
            "run_when_closed": task.run_when_closed,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "run_count": task.run_count,
            "error_count": task.error_count,
        }

    def list_tasks(self, market_type: Optional[MarketType] = None) -> List[Dict[str, Any]]:
        """
        List all scheduled tasks, optionally filtered by market type.

        Args:
            market_type: Optional market type filter

        Returns:
            List of task information dictionaries

        Example:
            >>> crypto_tasks = scheduler.list_tasks(MarketType.CRYPTO)
            >>> all_tasks = scheduler.list_tasks()
        """
        tasks = list(self.tasks.values())

        if market_type:
            tasks = [t for t in tasks if market_type in t.market_types]

        return [self.get_task_info(t.task_id) for t in tasks]

    async def run_task_once(self, task_id: str) -> bool:
        """
        Run a task immediately, regardless of market status.

        Useful for manual task execution or testing.

        Args:
            task_id: Task identifier to run

        Returns:
            True if task was run successfully, False otherwise

        Example:
            >>> await scheduler.run_task_once("monitor_1")
            True
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return False

        try:
            await task.handler()
            task.last_run = utc_now()
            task.run_count += 1
            logger.info(f"Ran task {task.name} ({task_id}) once")
            return True
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            task.error_count += 1
            logger.error(f"Error running task {task_id}: {e}", exc_info=True)
            return False

    def get_market_schedule(self, market_type: MarketType) -> Optional[MarketSchedule]:
        """
        Get the schedule for a market type.

        Args:
            market_type: Market type to get schedule for

        Returns:
            MarketSchedule or None if not found

        Example:
            >>> schedule = scheduler.get_market_schedule(MarketType.STOCKS_US)
            >>> print(schedule.open_time, schedule.close_time)
        """
        return self.schedules.get(market_type)

    def is_running(self) -> bool:
        """
        Check if the scheduler is currently running.

        Returns:
            True if scheduler is running
        """
        return self._is_running

    def get_task_count(self) -> int:
        """
        Get the total number of scheduled tasks.

        Returns:
            Number of tasks
        """
        return len(self.tasks)

    def get_enabled_task_count(self) -> int:
        """
        Get the number of enabled tasks.

        Returns:
            Number of enabled tasks
        """
        return sum(1 for t in self.tasks.values() if t.enabled)
