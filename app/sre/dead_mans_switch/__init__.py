"""
Dead Man's Switch - External Health Check with Auto-Response (SRE Rule 20.10)

Implements Google SRE dead man's switch practices:
- External health check monitoring
- Periodic pings with timeout detection
- Automatic alerts on missed pings
- Auto-restart on failure
- Degraded mode activation

Usage:
    switch = DeadMansSwitch(
        service_name="trading_engine",
        ping_interval_seconds=60,
        timeout_seconds=90
    )
    await switch.start()
"""

from .dead_mans_switch import (
    DeadMansSwitch,
    HealthCheckConfig,
    HeartbeatRecord,
    IncidentRecord,
    SwitchStatus,
)
from .external_monitor import (
    AlertChannel,
    ExternalMonitor,
    MonitorConfig,
)

__all__ = [
    "DeadMansSwitch",
    "SwitchStatus",
    "HealthCheckConfig",
    "HeartbeatRecord",
    "IncidentRecord",
    "ExternalMonitor",
    "MonitorConfig",
    "AlertChannel",
]
