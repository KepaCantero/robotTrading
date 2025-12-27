"""
TASK-MET-RUNTIME-1: Runtime Performance Tracking Service.

Tracks performance metrics per cycle to monitor system efficiency and identify bottlenecks.
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CycleMetrics:
    """Metrics for a single cycle."""

    def __init__(self):
        self.cycle_id: int = 0
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.signals_generated: int = 0
        self.trades_executed: int = 0
        self.cpu_usage: Optional[float] = None
        self.memory_usage_mb: Optional[float] = None
        self.errors_count: int = 0
        self.warnings_count: int = 0

    def finish(self) -> None:
        """Mark cycle as finished and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000


class PerformanceTracker:
    """
    TASK-MET-RUNTIME-1: Tracks runtime performance metrics per cycle.

    Monitors:
    - Cycle duration
    - Signals generated per cycle
    - Trades executed per cycle
    - Resource usage (CPU, memory)
    - Error rates
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.cycle_metrics: List[CycleMetrics] = []
        self.total_cycles: int = 0
        self.current_cycle: Optional[CycleMetrics] = None

    def start_cycle(self) -> int:
        """
        Start a new performance tracking cycle.

        Returns:
            Cycle ID
        """
        cycle_metrics = CycleMetrics()
        cycle_metrics.cycle_id = self.total_cycles
        self.current_cycle = cycle_metrics
        self.total_cycles += 1
        return cycle_metrics.cycle_id

    def end_cycle(self) -> Optional[Dict[str, Any]]:
        """
        End the current cycle and return metrics.

        Returns:
            Dictionary with cycle metrics or None
        """
        if self.current_cycle is None:
            return None

        self.current_cycle.finish()
        metrics_dict = self._cycle_to_dict(self.current_cycle)

        # Add to history
        self.cycle_metrics.append(self.current_cycle)
        if len(self.cycle_metrics) > self.max_history:
            self.cycle_metrics = self.cycle_metrics[-self.max_history :]

        self.current_cycle = None
        return metrics_dict

    def track_signal_generated(self) -> None:
        """Track signal generation."""
        if self.current_cycle:
            self.current_cycle.signals_generated += 1

    def track_trade_executed(self) -> None:
        """Track trade execution."""
        if self.current_cycle:
            self.current_cycle.trades_executed += 1

    def track_error(self) -> None:
        """Track error occurrence."""
        if self.current_cycle:
            self.current_cycle.errors_count += 1

    def track_warning(self) -> None:
        """Track warning occurrence."""
        if self.current_cycle:
            self.current_cycle.warnings_count += 1

    def get_performance_summary(self, last_n_cycles: int = 100) -> Dict[str, Any]:
        """
        Get performance summary for the last N cycles.

        Args:
            last_n_cycles: Number of recent cycles to analyze

        Returns:
            Dictionary with performance summary
        """
        recent_cycles = self.cycle_metrics[-last_n_cycles:] if self.cycle_metrics else []

        if not recent_cycles:
            return {
                "total_cycles": 0,
                "avg_duration_ms": 0.0,
                "avg_signals_per_cycle": 0.0,
                "avg_trades_per_cycle": 0.0,
                "total_errors": 0,
                "total_warnings": 0,
                "error_rate": 0.0,
            }

        return {
            "total_cycles": len(recent_cycles),
            "avg_duration_ms": sum(c.duration_ms for c in recent_cycles) / len(recent_cycles),
            "avg_signals_per_cycle": sum(c.signals_generated for c in recent_cycles)
            / len(recent_cycles),
            "avg_trades_per_cycle": sum(c.trades_executed for c in recent_cycles)
            / len(recent_cycles),
            "total_errors": sum(c.errors_count for c in recent_cycles),
            "total_warnings": sum(c.warnings_count for c in recent_cycles),
            "error_rate": sum(c.errors_count for c in recent_cycles) / len(recent_cycles),
            "max_duration_ms": max(c.duration_ms for c in recent_cycles),
            "min_duration_ms": min(c.duration_ms for c in recent_cycles),
        }

    def _cycle_to_dict(self, cycle: CycleMetrics) -> Dict[str, Any]:
        """Convert CycleMetrics to dictionary."""
        return {
            "cycle_id": cycle.cycle_id,
            "duration_ms": round(cycle.duration_ms, 2),
            "signals_generated": cycle.signals_generated,
            "trades_executed": cycle.trades_executed,
            "errors_count": cycle.errors_count,
            "warnings_count": cycle.warnings_count,
        }


# Global tracker instance
_performance_tracker: Optional[PerformanceTracker] = None


def get_performance_tracker() -> PerformanceTracker:
    """Get global performance tracker instance."""
    global _performance_tracker
    if _performance_tracker is None:
        pass

    return _performance_tracker
