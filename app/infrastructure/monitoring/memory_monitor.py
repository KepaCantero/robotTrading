"""
Memory Monitor - Monitor memory usage and auto-restart.

Protects against memory leaks in 24/7 operation:
- Monitors memory usage every 5 minutes
- Auto-restart if memory > limit
- State persistence before restart
- Configurable restart behavior
- Alert on restart
"""

from __future__ import annotations

import asyncio
import gc
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

import psutil

from app.shared.utils.timezone_utils import utc_now

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryAction(Enum):
    """Action to take when memory limit exceeded."""

    RESTART = "restart"
    ALERT_ONLY = "alert_only"
    GARBAGE_COLLECT = "garbage_collect"
    CLOSE_POSITIONS = "close_positions"


@dataclass
class MemoryConfig:
    """Configuration for memory monitoring."""

    memory_limit_mb: int = 4096  # 4GB default
    warning_threshold_mb: int = 3072  # 3GB
    check_interval_seconds: float = 300.0  # 5 minutes
    action: MemoryAction = MemoryAction.ALERT_ONLY
    close_positions_on_restart: bool = False
    save_state_before_restart: bool = True
    alert_callback: Callable[[str], None] | None = None


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage."""

    timestamp: datetime
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    gc_objects: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "rss_mb": round(self.rss_mb, 2),
            "vms_mb": round(self.vms_mb, 2),
            "percent": round(self.percent, 2),
            "available_mb": round(self.available_mb, 2),
            "gc_objects": self.gc_objects,
        }


class MemoryMonitor:
    """
    Monitor memory usage and auto-restart if needed.

    This is CRITICAL for 24/7 operation where memory leaks
    can accumulate over days.
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        state_saver: Callable[[], Awaitable[None]] | None = None,
        position_closer: Callable[[], Awaitable[None]] | None = None,
    ):
        """
        Initialize memory monitor.

        Args:
            config: Memory monitoring configuration
            state_saver: Async callback to save state before restart
            position_closer: Async callback to close positions before restart
        """
        self.config = config or MemoryConfig()
        self.state_saver = state_saver
        self.position_closer = position_closer

        # State
        self._is_monitoring = False
        self._monitor_task: asyncio.Task | None = None
        self._snapshots: list[MemorySnapshot] = []
        self._restart_count = 0
        self._last_restart: datetime | None = None

        # Get process
        self.process = psutil.Process(os.getpid())

        logger.info(
            f"MemoryMonitor initialized: limit={self.config.memory_limit_mb}MB, "
            f"action={self.config.action.value}",
            extra={
                "memory_limit_mb": self.config.memory_limit_mb,
                "warning_threshold_mb": self.config.warning_threshold_mb,
                "action": self.config.action.value,
                "check_interval_seconds": self.config.check_interval_seconds,
            },
        )

    async def start(self) -> bool:
        """Start memory monitoring."""
        if self._is_monitoring:
            logger.warning("MemoryMonitor already running", extra={"action": "start_skipped"})
            return False

        self._is_monitoring = True

        # Start monitoring loop
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info(
            "MemoryMonitor started",
            extra={"check_interval_seconds": self.config.check_interval_seconds},
        )
        return True

    async def stop(self) -> bool:
        """Stop memory monitoring."""
        if not self._is_monitoring:
            logger.warning("MemoryMonitor not running", extra={"action": "stop_skipped"})
            return False

        self._is_monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

        logger.info("MemoryMonitor stopped", extra={"restart_count": self._restart_count})
        return True

    async def _monitor_loop(self) -> None:
        """Check memory usage every 5 minutes."""
        while self._is_monitoring:
            try:
                memory_mb = self.get_memory_usage()

                if memory_mb > self.config.memory_limit_mb:
                    logger.critical(
                        f"Memory limit exceeded: {memory_mb:.2f}MB > "
                        f"{self.config.memory_limit_mb}MB",
                        extra={
                            "current_memory_mb": memory_mb,
                            "limit_mb": self.config.memory_limit_mb,
                            "action": self.config.action.value,
                        },
                    )
                    await self.trigger_action(memory_mb)
                elif memory_mb > self.config.warning_threshold_mb:
                    logger.warning(
                        f"Memory usage high: {memory_mb:.2f}MB "
                        f"(warning: {self.config.warning_threshold_mb}MB)",
                        extra={
                            "current_memory_mb": memory_mb,
                            "warning_threshold_mb": self.config.warning_threshold_mb,
                            "limit_mb": self.config.memory_limit_mb,
                        },
                    )

                    if self.config.alert_callback:
                        self.config.alert_callback(f"Memory usage high: {memory_mb:.2f}MB")

                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, OSError) as e:
                logger.error("Error in memory monitor loop", extra={"error_type": type(e).__name__})
                await asyncio.sleep(self.config.check_interval_seconds)

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        logger.debug("Getting current memory usage")
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / (1024 * 1024)
        except (asyncio.TimeoutError, OSError):
            return 0.0

    def get_detailed_stats(self) -> dict[str, Any]:
        """Get detailed memory statistics."""
        logger.debug("Getting detailed memory statistics")
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            return {
                "rss_mb": round(memory_info.rss / (1024 * 1024), 2),
                "vms_mb": round(memory_info.vms / (1024 * 1024), 2),
                "percent": round(memory_percent, 2),
                "available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
                "gc_objects": len(gc.get_objects()),
                "limit_mb": self.config.memory_limit_mb,
                "warning_mb": self.config.warning_threshold_mb,
            }
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error("Error getting memory stats", extra={"error_type": type(e).__name__})
            return {}

    async def trigger_action(self, current_memory_mb: float) -> None:
        """Trigger configured action when memory limit exceeded."""
        action = self.config.action

        logger.critical(
            f"Triggering memory action: {action.value}",
            extra={
                "action": action.value,
                "current_memory_mb": current_memory_mb,
                "limit_mb": self.config.memory_limit_mb,
            },
        )

        if action == MemoryAction.GARBAGE_COLLECT:
            # Try garbage collection first
            collected = gc.collect()
            logger.info(
                f"Garbage collected {collected} objects",
                extra={
                    "collected_objects": collected,
                    "action": "garbage_collect",
                },
            )

            # Check if memory freed
            new_memory = self.get_memory_usage()
            if new_memory < self.config.memory_limit_mb:
                logger.info(
                    f"Memory freed: {current_memory_mb:.2f}MB -> {new_memory:.2f}MB",
                    extra={
                        "before_mb": current_memory_mb,
                        "after_mb": new_memory,
                        "freed_mb": current_memory_mb - new_memory,
                    },
                )
                return

        elif action == MemoryAction.CLOSE_POSITIONS and self.position_closer:
            # Close positions before restart
            try:
                logger.info("Closing positions before restart", extra={"action": "close_positions"})
                await self.position_closer()
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(
                    "Error closing positions",
                    extra={"error_type": type(e).__name__},
                    exc_info=True,
                )

        # Save state if configured
        if self.config.save_state_before_restart and self.state_saver:
            try:
                logger.info("Saving state before restart", extra={"action": "save_state"})
                await self.state_saver()
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(
                    "Error saving state", extra={"error_type": type(e).__name__}, exc_info=True
                )

        # Send alert
        if self.config.alert_callback:
            try:
                logger.debug(
                    "Sending memory alert",
                    extra={"action": action.value, "memory_mb": current_memory_mb},
                )
                self.config.alert_callback(
                    f"Memory action: {action.value} ({current_memory_mb:.2f}MB)"
                )
            except (asyncio.TimeoutError, OSError) as e:
                logger.error("Error in alert callback", extra={"error_type": type(e).__name__})

        # Restart if configured
        if action == MemoryAction.RESTART:
            await self.trigger_graceful_restart()

    async def trigger_graceful_restart(self) -> None:
        """Close positions and restart process."""
        logger.critical(
            "Initiating graceful restart",
            extra={
                "restart_count": self._restart_count + 1,
                "last_restart": self._last_restart.isoformat() if self._last_restart else None,
            },
        )

        # Update restart stats
        self._restart_count += 1
        self._last_restart = utc_now()

        # Flush logs
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Restart process
        try:
            logger.info(
                "Executing process restart", extra={"executable": sys.executable, "argv": sys.argv}
            )
            os.execv(sys.executable, [sys.executable, *sys.argv])
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(
                "Error restarting process", extra={"error_type": type(e).__name__}, exc_info=True
            )

    def take_snapshot(self) -> MemorySnapshot:
        """Take a snapshot of current memory usage."""
        logger.debug("Taking memory snapshot")
        try:
            memory_info = self.process.memory_info()
            virtual_mem = psutil.virtual_memory()

            snapshot = MemorySnapshot(
                timestamp=utc_now(),
                rss_mb=memory_info.rss / (1024 * 1024),
                vms_mb=memory_info.vms / (1024 * 1024),
                percent=self.process.memory_percent(),
                available_mb=virtual_mem.available / (1024 * 1024),
                gc_objects=len(gc.get_objects()),
            )

            self._snapshots.append(snapshot)

            # Keep only last 100 snapshots
            if len(self._snapshots) > 100:
                self._snapshots = self._snapshots[-100:]

            return snapshot

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error("Error taking snapshot", extra={"error_type": type(e).__name__})
            return MemorySnapshot(
                timestamp=utc_now(),
                rss_mb=0,
                vms_mb=0,
                percent=0,
                available_mb=0,
                gc_objects=0,
            )

    def get_snapshots(self, limit: int = 10) -> list[MemorySnapshot]:
        """Get recent memory snapshots."""
        return self._snapshots[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        """Get monitor statistics."""
        current_snapshot = self.take_snapshot()

        return {
            "is_monitoring": self._is_monitoring,
            "current_memory": current_snapshot.to_dict(),
            "restart_count": self._restart_count,
            "last_restart": (self._last_restart.isoformat() if self._last_restart else None),
            "config": {
                "limit_mb": self.config.memory_limit_mb,
                "warning_mb": self.config.warning_threshold_mb,
                "check_interval_seconds": self.config.check_interval_seconds,
                "action": self.config.action.value,
            },
            "snapshots_count": len(self._snapshots),
        }


# Global instance
_memory_monitor: MemoryMonitor | None = None


def get_memory_monitor(
    config: MemoryConfig | None = None,
    state_saver: Callable[[], None] | None = None,
    position_closer: Callable[[], None] | None = None,
) -> MemoryMonitor:
    """
    Get or create the global MemoryMonitor instance.

    Args:
        config: Memory monitoring configuration
        state_saver: Callback to save state before restart
        position_closer: Callback to close positions before restart

    Returns:
        MemoryMonitor instance
    """
    global _memory_monitor

    logger.debug("Getting memory monitor instance", extra={"exists": _memory_monitor is not None})

    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor(
            config=config,
            state_saver=state_saver,
            position_closer=position_closer,
        )

    return _memory_monitor


def reset_memory_monitor() -> None:
    """Reset the global MemoryMonitor instance (for testing)."""
    global _memory_monitor
    logger.debug("Resetting memory monitor instance", extra={"action": "reset"})
    _memory_monitor = None
