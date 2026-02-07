"""
Aggressive Memory Manager for Backtesting Operations.

This module provides memory management utilities to prevent memory leaks
and excessive memory usage during long-running backtesting operations.

FIXES (Phase 4):
- Proper deep cleanup of nested references
- Single GC pass instead of multiple
- Automatic monitoring in add methods
- Weak references for BacktestResult objects
"""

from __future__ import annotations

import gc
import logging
import threading
import weakref
from collections import deque
from typing import TypedDict

import psutil

from app.backtesting.models import BacktestResult

logger = logging.getLogger(__name__)


class BacktestResultDict(TypedDict, total=False):
    """TypedDict for backtest result dictionaries."""

    test_type: str
    test_name: str
    strategy_name: str
    total_pnl: float
    return_pct: float
    final_capital: float
    total_trades: int
    win_rate: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    avg_trade_pnl: float


class MemoryPressureError(Exception):
    """Raised when memory pressure exceeds threshold."""



class AggressiveMemoryManager:
    """
    Aggressive memory management for backtesting operations.

    Features:
    - Automatic cleanup of results when thresholds are exceeded
    - Memory pressure monitoring with psutil
    - Emergency cleanup when memory limits are reached
    - Thread-safe operations with locks

    Example:
        >>> manager = AggressiveMemoryManager(max_results=500, memory_threshold_mb=4096)
        >>> manager.add_result({'strategy_name': 'test', 'return': 0.05})
        >>> if manager.check_memory_pressure():
        ...     logger.warning("Memory pressure detected")
    """

    def __init__(
        self,
        max_results: int = 500,
        max_backtest_objects: int = 100,
        memory_threshold_mb: int = 4096,
        auto_monitor: bool = True,
    ) -> None:
        """
        Initialize memory manager.

        Args:
            max_results: Maximum number of lightweight results to keep
            max_backtest_objects: Maximum number of BacktestResult objects (heavy)
            memory_threshold_mb: Memory threshold in MB for triggering cleanup
            auto_monitor: Enable automatic memory monitoring on each add
        """
        self.max_results = max_results
        self.max_backtest_objects = max_backtest_objects
        self.memory_threshold = memory_threshold_mb
        self.auto_monitor = auto_monitor

        # Use deque with maxlen for automatic bounded size
        self._results: deque[BacktestResultDict] = deque(maxlen=max_results)
        # Use weak references for BacktestResult to prevent circular references
        self._backtest_refs: dict[str, weakref.ref] = {}
        self._backtest_objects: deque[tuple[str, BacktestResult]] = deque(
            maxlen=max_backtest_objects
        )

        # Thread-safe lock for cleanup operations
        self._lock = threading.RLock()

        # Statistics
        self._cleanup_count = 0
        self._emergency_cleanup_count = 0

    def add_result(self, result: BacktestResultDict) -> None:
        """
        Add a lightweight result dictionary.

        Args:
            result: Dictionary containing backtest results
        """
        with self._lock:
            self._results.append(result)
            self._cleanup_if_needed()

            # Automatic memory monitoring
            if self.auto_monitor:
                self._auto_check_memory()

    def add_backtest_object(self, key: str, obj: BacktestResult) -> None:
        """
        Add a heavy BacktestResult object with strict control.

        Args:
            key: Identifier for the backtest result
            obj: BacktestResult object (heavyweight)
        """
        with self._lock:
            self._backtest_objects.append((key, obj))

            # Create weak reference to prevent circular references
            def cleanup_callback(ref: weakref.ref) -> None:
                """Callback when weak reference is deleted."""
                with self._lock:
                    if key in self._backtest_refs:
                        del self._backtest_refs[key]

            self._backtest_refs[key] = weakref.ref(obj, cleanup_callback)
            self._cleanup_backtest_objects_if_needed()

            # Automatic memory monitoring
            if self.auto_monitor:
                self._auto_check_memory()

    def get_results(self) -> list[BacktestResultDict]:
        """
        Get all current results as a list.

        Returns:
            List of result dictionaries
        """
        with self._lock:
            return list(self._results)

    def get_backtest_objects(self) -> list[tuple[str, BacktestResult]]:
        """
        Get all current BacktestResult objects.

        Returns:
            List of (key, BacktestResult) tuples
        """
        with self._lock:
            return list(self._backtest_objects)

    def clear_all(self) -> None:
        """Clear all stored results and objects with proper cleanup."""
        with self._lock:
            # Clear results
            self._results.clear()

            # Clear backtest objects with proper deep cleanup (FIX)
            for key, obj in self._backtest_objects:
                self._deep_cleanup_object(obj)
                if key in self._backtest_refs:
                    del self._backtest_refs[key]

            self._backtest_objects.clear()
            self._backtest_refs.clear()

            # Single GC pass (FIX: was 3 passes)
            gc.collect()
            logger.debug("Cleared all memory-managed objects")

    def _cleanup_if_needed(self) -> None:
        """
        Perform cleanup when result threshold is approached.
        """
        # Trigger cleanup when approaching 80% capacity
        if len(self._results) > self.max_results * 0.8:
            self._perform_cleanup()

    def _cleanup_backtest_objects_if_needed(self) -> None:
        """
        Perform aggressive cleanup of BacktestResult objects with deep cleanup (FIX).
        """
        # Keep only 50 most recent
        while len(self._backtest_objects) > 50:
            key, obj = self._backtest_objects.popleft()
            # Proper deep cleanup instead of just del old (FIX)
            self._deep_cleanup_object(obj)
            if key in self._backtest_refs:
                del self._backtest_refs[key]
            self._cleanup_count += 1

        # Force garbage collection if we have many objects
        if len(self._backtest_objects) > 30:
            gc.collect()

    def _deep_cleanup_object(self, obj) -> None:
        """
        Perform deep cleanup of an object to remove circular references.

        Args:
            obj: Object to clean up
        """
        try:
            # Clear any dict/list attributes that might hold references
            if hasattr(obj, '__dict__'):
                for attr_name, attr_value in list(obj.__dict__.items()):
                    if isinstance(attr_value, (dict, list, set)):
                        # Clear the container
                        if hasattr(attr_value, 'clear'):
                            attr_value.clear()
                    elif attr_value is not obj:
                        # Set to None to break references
                        setattr(obj, attr_name, None)
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.debug(
                "Error during deep cleanup",
                extra={
                    'object_type': type(obj).__name__,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                },
                exc_info=True,
            )

    def _perform_cleanup(self) -> None:
        """
        Perform standard cleanup operation.
        """
        # Keep results at 50% capacity
        target_size = self.max_results // 2
        while len(self._results) > target_size:
            result = self._results.popleft()
            # Clean up result dict to remove nested references (FIX)
            if isinstance(result, dict):
                result.clear()
            self._cleanup_count += 1

        # Single garbage collection pass (FIX: was implicit multiple calls)
        gc.collect()

    def _emergency_cleanup(self) -> None:
        """
        Emergency cleanup - free as much memory as possible.
        """
        logger.critical(
            "Emergency cleanup triggered",
            extra={
                'action': 'emergency_cleanup',
                'results_before': len(self._results),
                'backtest_objects_before': len(self._backtest_objects),
                'memory_threshold_mb': self.memory_threshold,
            },
        )

        with self._lock:
            # Keep only 10 most recent results
            while len(self._results) > 10:
                result = self._results.popleft()
                if isinstance(result, dict):
                    result.clear()

            # Keep only 5 most recent BacktestResult objects
            while len(self._backtest_objects) > 5:
                key, obj = self._backtest_objects.popleft()
                self._deep_cleanup_object(obj)
                if key in self._backtest_refs:
                    del self._backtest_refs[key]

            # Clear weak refs
            self._backtest_refs.clear()

            # Single GC pass
            gc.collect()

            self._emergency_cleanup_count += 1
            logger.critical(
                "Emergency cleanup completed",
                extra={
                    'results_after': len(self._results),
                    'backtest_objects_after': len(self._backtest_objects),
                    'emergency_cleanup_count': self._emergency_cleanup_count,
                },
            )

    def check_memory_pressure(self) -> bool:
        """
        Check if the process is under memory pressure.

        Returns:
            True if memory usage exceeds threshold, False otherwise
        """
        return self._auto_check_memory()

    def _auto_check_memory(self) -> bool:
        """
        Internal automatic memory check.

        Returns:
            True if memory usage exceeds threshold, False otherwise
        """
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.memory_threshold:
                logger.warning(
                    "Memory pressure detected",
                    extra={
                        'memory_mb': round(memory_mb, 2),
                        'threshold_mb': self.memory_threshold,
                        'results_count': len(self._results),
                        'backtest_objects_count': len(self._backtest_objects),
                    },
                )
                self._emergency_cleanup()
                return True

            # Log memory usage at regular intervals for monitoring
            if len(self._results) % 100 == 0 or len(self._backtest_objects) % 20 == 0:
                logger.debug(
                    "Memory status check",
                    extra={
                        'memory_mb': round(memory_mb, 2),
                        'results_count': len(self._results),
                        'backtest_objects_count': len(self._backtest_objects),
                        'weak_refs_count': len(self._backtest_refs),
                        'threshold_mb': self.memory_threshold,
                    },
                )

            return False

        except psutil.Error as e:
            logger.error(
                "Error checking memory pressure",
                extra={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                },
                exc_info=True,
            )
            return False

    def get_memory_usage_mb(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in megabytes
        """
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except (psutil.Error, Exception):
            return 0.0

    def get_stats(self) -> dict[str, int | float | bool]:
        """
        Get memory manager statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'results_count': len(self._results),
            'backtest_objects_count': len(self._backtest_objects),
            'weak_refs_count': len(self._backtest_refs),  # FIX: Added tracking
            'cleanup_count': self._cleanup_count,
            'emergency_cleanup_count': self._emergency_cleanup_count,
            'memory_usage_mb': self.get_memory_usage_mb(),
            'memory_threshold_mb': self.memory_threshold,
            'auto_monitor_enabled': self.auto_monitor,  # FIX: Added tracking
        }

    def __repr__(self) -> str:
        """String representation of memory manager state."""
        return (
            f"AggressiveMemoryManager("
            f"results={len(self._results)}/{self.max_results}, "
            f"backtest_objects={len(self._backtest_objects)}/{self.max_backtest_objects}, "
            f"weak_refs={len(self._backtest_refs)}, "  # FIX: Added to repr
            f"memory={self.get_memory_usage_mb():.0f}MB"
            f")"
        )
