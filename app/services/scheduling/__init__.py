"""
Market Scheduler Module - Phase 3.1: 24/7 Market Scheduler

This module provides intelligent task scheduling for multi-market trading operations:
- 24/7 markets (crypto): continuous operation
- 24/5 markets (forex): continuous weekday operation
- Scheduled markets (stocks US/EU/Asia): specific hours with proper timezone handling

The scheduler efficiently manages CPU resources by:
- Running 24/7 tasks continuously with appropriate intervals
- Scheduling 6.5h stock market tasks only during open hours
- Respecting market holidays and weekends
- Handling timezone differences across US, EU, and Asian markets
- Providing graceful startup and shutdown

Example:
    >>> from app.services.scheduling import MarketScheduler, MarketType
    >>>
    >>> scheduler = MarketScheduler()
    >>> await scheduler.start()
    >>>
    >>> # Schedule a task for crypto (24/7)
    >>> scheduler.schedule_task(
    ...     task_id="crypto_monitor",
    ...     name="Crypto Market Monitor",
    ...     market_types=[MarketType.CRYPTO],
    ...     handler=crypto_monitoring_handler
    ... )
    >>>
    >>> # Schedule a task for US stocks (9:30-16:00 ET)
    >>> scheduler.schedule_task(
    ...     task_id="us_stock_scanner",
    ...     name="US Stock Scanner",
    ...     market_types=[MarketType.STOCKS_US],
    ...     handler=us_stock_scanner_handler
    ... )
"""

from app.services.scheduling.market_scheduler import (
    MARKET_SCHEDULES,
    MarketSchedule,
    MarketScheduler,
    MarketStatus,
    MarketType,
    ScheduledTask,
)

__all__ = [
    "MarketScheduler",
    "MarketType",
    "MarketStatus",
    "MarketSchedule",
    "ScheduledTask",
    "MARKET_SCHEDULES",
]
