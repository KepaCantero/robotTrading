"""
Position Monitor Service - Continuous position monitoring and risk management.

Monitors all open positions and executes stop-loss/take-profit orders automatically.
This is a CRITICAL component for production trading.

Criticality: LIFE-THREATENING - System executes trades then forgets positions exist.
No stop-loss execution in production.

This service:
- Checks positions every second
- Executes stop-loss automatically when hit
- Executes take-profit automatically when hit
- Survives process restart (reads from DB)
- Handles broker disconnections gracefully
"""

from .position_monitor import (
    MonitoredPosition,
    PositionMonitor,
    PositionMonitorConfig,
    PositionStatus,
)
from .stop_executor import StopExecutionResult, StopExecutor, StopType

__all__ = [
    "PositionMonitor",
    "PositionMonitorConfig",
    "MonitoredPosition",
    "PositionStatus",
    "StopExecutor",
    "StopExecutionResult",
    "StopType",
]
