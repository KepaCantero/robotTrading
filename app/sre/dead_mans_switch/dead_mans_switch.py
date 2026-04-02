from __future__ import annotations

# mypy: ignore-errors
"""
Dead Man's Switch - Health Check Monitoring

Implements a dead man's switch that requires periodic health check pings.
If pings are missed, triggers alerts and automatic recovery actions.
"""


import asyncio
import contextlib
import logging
import os
import signal
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import aiosqlite

from app.shared.utils.safe_parse import safe_parse

logger = logging.getLogger(__name__)


class SwitchStatus(str, Enum):
    """Status of dead man's switch."""

    ACTIVE = "active"  # Switch is armed and monitoring
    TRIGGERED = "triggered"  # Switch has been triggered (missed pings)
    DISABLED = "disabled"  # Switch is disabled
    RECOVERING = "recovering"  # Recovery in progress


@dataclass
class HealthCheckConfig:
    """Configuration for dead man's switch."""

    # Timing
    ping_interval_seconds: int = 60  # How often to ping
    timeout_seconds: int = 90  # Timeout before triggering
    grace_period_seconds: int = 30  # Grace period on startup

    # Health check endpoint
    health_check_url: str | None = None  # External health check URL
    health_check_method: str = "GET"
    health_check_timeout: int = 10

    # Alerting
    alert_on_trigger: bool = True
    alert_channels: list[str] = field(default_factory=lambda: ["email", "slack"])

    # Auto-recovery
    auto_restart: bool = True
    restart_command: str | None = None
    max_restart_attempts: int = 3

    # Degraded mode
    enable_degraded_mode: bool = True
    degraded_mode_actions: list[str] = field(default_factory=list)

    # Database
    db_path: str = "data/dead_mans_switch.db"

    # Verification
    require_consecutive_failures: int = 3  # Require N consecutive failures

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ping_interval_seconds": self.ping_interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "grace_period_seconds": self.grace_period_seconds,
            "health_check_url": self.health_check_url,
            "health_check_method": self.health_check_method,
            "health_check_timeout": self.health_check_timeout,
            "alert_on_trigger": self.alert_on_trigger,
            "alert_channels": self.alert_channels,
            "auto_restart": self.auto_restart,
            "restart_command": self.restart_command,
            "max_restart_attempts": self.max_restart_attempts,
            "enable_degraded_mode": self.enable_degraded_mode,
            "degraded_mode_actions": self.degraded_mode_actions,
            "require_consecutive_failures": self.require_consecutive_failures,
        }


@dataclass
class HeartbeatRecord:
    """Record of a heartbeat/ping."""

    timestamp: datetime
    success: bool
    response_time_ms: float | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class IncidentRecord:
    """Record of a dead man's switch incident."""

    incident_id: str
    triggered_at: datetime
    resolved_at: datetime | None
    missed_pings: int
    last_ping_at: datetime | None
    recovery_actions: list[str]
    status: SwitchStatus
    root_cause: str | None = None

    @property
    def duration_minutes(self) -> int | None:
        """Calculate incident duration."""
        if not self.resolved_at:
            return None
        return int((self.resolved_at - self.triggered_at).total_seconds() / 60)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "incident_id": self.incident_id,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "duration_minutes": self.duration_minutes,
            "missed_pings": self.missed_pings,
            "last_ping_at": self.last_ping_at.isoformat() if self.last_ping_at else None,
            "recovery_actions": self.recovery_actions,
            "status": self.status.value,
            "root_cause": self.root_cause,
        }


class DeadMansSwitch:
    """
    Dead man's switch implementation.

    Responsibilities:
    - Monitor periodic health check pings
    - Detect missed pings/timeouts
    - Trigger alerts on failure
    - Execute auto-recovery actions
    - Track incidents

    Usage:
        switch = DeadMansSwitch(
            service_name="trading_engine",
            config=HealthCheckConfig()
        )
        await switch.initialize()
        await switch.start()

        # In your application loop:
        await switch.ping()

        # Or use health check endpoint:
        # GET /health/ping?token=SECRET_TOKEN
    """

    def __init__(
        self,
        service_name: str,
        config: HealthCheckConfig | None = None,
    ):
        """
        Initialize dead man's switch.

        Args:
            service_name: Name of the service
            config: Health check configuration
        """
        self.service_name = service_name
        self.config = config or HealthCheckConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._status = SwitchStatus.ACTIVE
        self._last_ping: datetime | None = None
        self._last_successful_ping: datetime | None = None
        self._consecutive_failures = 0
        self._restart_attempts = 0
        self._current_incident: IncidentRecord | None = None

        # Heartbeat history
        self._heartbeat_history: list[HeartbeatRecord] = []
        self._incident_history: list[IncidentRecord] = []

        # Monitoring task
        self._monitor_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None

        # Callbacks
        self._on_trigger: Callable[[IncidentRecord], None] | None = None
        self._on_recover: Callable[[IncidentRecord], None] | None = None
        self._on_degraded: Callable[[], None] | None = None

        # Lock
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize dead man's switch."""
        async with self._lock:
            try:
                await self._init_database()
                await self._load_active_incident()
                self.logger.info("DeadMansSwitch initialized")
            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS heartbeats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        success INTEGER NOT NULL,
                        response_time_ms REAL,
                        error_message TEXT,
                        metadata TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS incidents (
                        incident_id TEXT PRIMARY KEY,
                        service_name TEXT NOT NULL,
                        triggered_at TEXT NOT NULL,
                        resolved_at TEXT,
                        missed_pings INTEGER NOT NULL,
                        last_ping_at TEXT,
                        recovery_actions TEXT NOT NULL,
                        status TEXT NOT NULL,
                        root_cause TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_heartbeats_service_timestamp
                    ON heartbeats(service_name, timestamp)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_incidents_service_status
                    ON incidents(service_name, status)
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_active_incident(self) -> None:
        """Load active incident from database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT incident_id, triggered_at, missed_pings, last_ping_at,
                           recovery_actions, status, root_cause
                    FROM incidents
                    WHERE service_name = ? AND status IN ('triggered', 'recovering')
                    ORDER BY triggered_at DESC
                    LIMIT 1
                """,
                    (self.service_name,),
                )

                row = await cursor.fetchone()

                if row:
                    self._current_incident = IncidentRecord(
                        incident_id=row[0],
                        triggered_at=datetime.fromisoformat(row[1]),
                        resolved_at=None,
                        missed_pings=row[2],
                        last_ping_at=datetime.fromisoformat(row[3]) if row[3] else None,
                        recovery_actions=safe_parse(row[4], default=[]),
                        status=SwitchStatus(row[5]),
                        root_cause=row[6],
                    )
                    self._status = SwitchStatus.RECOVERING

                    self.logger.warning(f"Loaded active incident: {row[0]}")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error loading incident: {e}")

    async def start(self) -> None:
        """Start dead man's switch monitoring."""
        if self._monitor_task and not self._monitor_task.done():
            self.logger.warning("Monitor already running")
            return

        self.logger.info("Starting dead man's switch monitor")

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        # Start auto-ping task if health check URL configured
        if self.config.health_check_url:
            self._ping_task = asyncio.create_task(self._auto_ping_loop())

    async def stop(self) -> None:
        """Stop dead man's switch monitoring."""
        self.logger.info("Stopping dead man's switch monitor")

        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

        if self._ping_task:
            self._ping_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ping_task

    async def ping(
        self,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send a heartbeat/ping to the dead man's switch.

        Args:
            metadata: Optional metadata to attach to ping

        Returns:
            True if ping successful
        """
        async with self._lock:
            try:
                start_time = datetime.utcnow()

                # Perform health check if configured
                if self.config.health_check_url:
                    await self._perform_health_check()

                # Record heartbeat
                heartbeat = HeartbeatRecord(
                    timestamp=start_time,
                    success=True,
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    metadata=metadata or {},
                )

                self._heartbeat_history.append(heartbeat)
                self._last_ping = start_time
                self._last_successful_ping = start_time
                self._consecutive_failures = 0

                # Save to database
                await self._save_heartbeat(heartbeat)

                # Trim history
                if len(self._heartbeat_history) > 1000:
                    self._heartbeat_history = self._heartbeat_history[-500:]

                return True

            except Exception as e:
                self.logger.error(f"Ping failed: {e}")

                # Record failed heartbeat
                heartbeat = HeartbeatRecord(
                    timestamp=datetime.utcnow(),
                    success=False,
                    error_message=str(e),
                )

                self._heartbeat_history.append(heartbeat)
                self._consecutive_failures += 1

                await self._save_heartbeat(heartbeat)

                return False

    async def _perform_health_check(self) -> None:
        """Perform external health check."""
        try:
            import aiohttp

            async with (
                aiohttp.ClientSession() as session,
                session.request(
                    self.config.health_check_method,
                    self.config.health_check_url,
                    timeout=self.config.health_check_timeout,
                ) as response,
            ):
                if response.status >= 400:
                    raise ConnectionError(f"Health check failed: HTTP {response.status}")

                await response.read()

        except asyncio.TimeoutError as exc:
            raise TimeoutError("Health check timeout") from exc
        except Exception as e:
            raise ConnectionError(f"Health check error: {e}") from e

    async def _monitor_loop(self) -> None:
        """Monitor for missed pings."""
        grace_period_end = datetime.utcnow() + timedelta(seconds=self.config.grace_period_seconds)

        while True:
            try:
                await asyncio.sleep(self.config.ping_interval_seconds)

                now = datetime.utcnow()

                # Check if still in grace period
                if now < grace_period_end:
                    continue

                # Check for timeout
                if self._last_successful_ping:
                    time_since_last_ping = (now - self._last_successful_ping).total_seconds()

                    if time_since_last_ping > self.config.timeout_seconds:
                        # Timeout detected
                        await self._handle_timeout()

                # Check consecutive failures
                if self._consecutive_failures >= self.config.require_consecutive_failures:
                    await self._handle_timeout()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")

    async def _auto_ping_loop(self) -> None:
        """Automatically ping health check endpoint."""
        while True:
            try:
                await asyncio.sleep(self.config.ping_interval_seconds)
                await self.ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in auto ping loop: {e}")

    async def _handle_timeout(self) -> None:
        """Handle timeout/missed pings."""
        if self._status in [SwitchStatus.DISABLED, SwitchStatus.RECOVERING]:
            return

        self.logger.critical("Dead man's switch triggered!")

        # Calculate missed pings
        if self._last_successful_ping:
            time_since = (datetime.utcnow() - self._last_successful_ping).total_seconds()
            missed_pings = int(time_since / self.config.ping_interval_seconds)
        else:
            missed_pings = 1

        # Create incident
        import uuid

        incident = IncidentRecord(
            incident_id=str(uuid.uuid4()),
            triggered_at=datetime.utcnow(),
            resolved_at=None,
            missed_pings=missed_pings,
            last_ping_at=self._last_successful_ping,
            recovery_actions=[],
            status=SwitchStatus.TRIGGERED,
        )

        self._current_incident = incident
        self._status = SwitchStatus.TRIGGERED

        # Save incident
        await self._save_incident(incident)

        # Trigger callback
        if self._on_trigger:
            try:
                await self._on_trigger(incident)
            except Exception as e:
                self.logger.error(f"Error in trigger callback: {e}")

        # Send alerts
        if self.config.alert_on_trigger:
            await self._send_alerts(incident)

        # Auto-recovery
        if self.config.auto_restart:
            await self._attempt_recovery(incident)

        # Degraded mode
        if self.config.enable_degraded_mode:
            await self._enter_degraded_mode()

    async def _attempt_recovery(self, incident: IncidentRecord) -> None:
        """Attempt automatic recovery."""
        if self._restart_attempts >= self.config.max_restart_attempts:
            self.logger.error("Max restart attempts reached")
            return

        self._restart_attempts += 1
        self._status = SwitchStatus.RECOVERING

        recovery_actions = []

        # Execute restart command
        if self.config.restart_command:
            try:
                self.logger.info(f"Executing restart command: {self.config.restart_command}")

                import shlex
                import subprocess

                # SECURITY: Parse command safely to avoid shell injection
                # shlex.split() properly handles quoted arguments
                if isinstance(self.config.restart_command, str):
                    cmd_args = shlex.split(self.config.restart_command)
                else:
                    cmd_args = list(self.config.restart_command)

                result = subprocess.run(
                    cmd_args,
                    shell=False,
                    timeout=60,
                    capture_output=True,
                    check=False,
                )

                if result.returncode == 0:
                    recovery_actions.append("Restart command executed successfully")
                else:
                    recovery_actions.append(f"Restart command failed: {result.stderr}")

            except Exception as e:
                recovery_actions.append(f"Restart command error: {e}")

        # Send signal to restart
        try:
            os.kill(os.getpid(), signal.SIGTERM)
            recovery_actions.append("Sent SIGTERM to process")
        except Exception as e:
            recovery_actions.append(f"Signal error: {e}")

        incident.recovery_actions = recovery_actions
        await self._update_incident(incident)

        self.logger.info(
            f"Recovery attempt {self._restart_attempts}/{self.config.max_restart_attempts}"
        )

    async def _enter_degraded_mode(self) -> None:
        """Enter degraded mode."""
        self.logger.warning("Entering degraded mode")

        # Trigger callback
        if self._on_degraded:
            try:
                await self._on_degraded()
            except Exception as e:
                self.logger.error(f"Error in degraded callback: {e}")

        # Execute degraded mode actions
        for action in self.config.degraded_mode_actions:
            try:
                self.logger.info(f"Executing degraded action: {action}")
                # Implementation depends on action type
            except Exception as e:
                self.logger.error(f"Error executing degraded action {action}: {e}")

    async def resolve_incident(self, incident_id: str) -> bool:
        """
        Manually resolve an incident.

        Args:
            incident_id: Incident ID to resolve

        Returns:
            True if resolved
        """
        if not self._current_incident or self._current_incident.incident_id != incident_id:
            return False

        self._current_incident.resolved_at = datetime.utcnow()
        self._current_incident.status = SwitchStatus.ACTIVE

        await self._update_incident(self._current_incident)

        self._incident_history.append(self._current_incident)
        self._current_incident = None
        self._status = SwitchStatus.ACTIVE
        self._restart_attempts = 0
        self._consecutive_failures = 0

        # Trigger recovery callback
        if self._on_recover:
            try:
                await self._on_recover(self._incident_history[-1])
            except Exception as e:
                self.logger.error(f"Error in recover callback: {e}")

        self.logger.info(f"Incident {incident_id} resolved")

        return True

    async def _send_alerts(self, incident: IncidentRecord) -> None:
        """Send alerts for incident."""
        # Implementation depends on alert channels
        # This is a placeholder for actual alert sending
        self.logger.critical(
            f"DEAD MAN'S SWITCH TRIGGERED: {self.service_name} "
            f"(missed {incident.missed_pings} pings)"
        )

    async def _save_heartbeat(self, heartbeat: HeartbeatRecord) -> None:
        """Save heartbeat to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO heartbeats
                    (service_name, timestamp, success, response_time_ms, error_message, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.service_name,
                        heartbeat.timestamp.isoformat(),
                        1 if heartbeat.success else 0,
                        heartbeat.response_time_ms,
                        heartbeat.error_message,
                        str(heartbeat.metadata),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving heartbeat: {e}")

    async def _save_incident(self, incident: IncidentRecord) -> None:
        """Save incident to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO incidents
                    (incident_id, service_name, triggered_at, resolved_at, missed_pings,
                     last_ping_at, recovery_actions, status, root_cause)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        incident.incident_id,
                        self.service_name,
                        incident.triggered_at.isoformat(),
                        incident.resolved_at.isoformat() if incident.resolved_at else None,
                        incident.missed_pings,
                        incident.last_ping_at.isoformat() if incident.last_ping_at else None,
                        str(incident.recovery_actions),
                        incident.status.value,
                        incident.root_cause,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving incident: {e}")

    async def _update_incident(self, incident: IncidentRecord) -> None:
        """Update incident in database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    UPDATE incidents
                    SET resolved_at = ?, recovery_actions = ?, status = ?, root_cause = ?
                    WHERE incident_id = ?
                """,
                    (
                        incident.resolved_at.isoformat() if incident.resolved_at else None,
                        str(incident.recovery_actions),
                        incident.status.value,
                        incident.root_cause,
                        incident.incident_id,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error updating incident: {e}")

    def set_trigger_callback(self, callback: Callable) -> None:
        """Set callback for when switch is triggered."""
        self._on_trigger = callback

    def set_recover_callback(self, callback: Callable) -> None:
        """Set callback for when incident is resolved."""
        self._on_recover = callback

    def set_degraded_callback(self, callback: Callable) -> None:
        """Set callback for entering degraded mode."""
        self._on_degraded = callback

    @property
    def status(self) -> SwitchStatus:
        """Get current status."""
        return self._status

    @property
    def last_ping(self) -> datetime | None:
        """Get last successful ping time."""
        return self._last_successful_ping

    @property
    def current_incident(self) -> IncidentRecord | None:
        """Get current incident."""
        return self._current_incident

    def get_summary(self) -> dict[str, Any]:
        """Get dead man's switch summary."""
        return {
            "service": self.service_name,
            "status": self._status.value,
            "last_ping": (
                self._last_successful_ping.isoformat() if self._last_successful_ping else None
            ),
            "consecutive_failures": self._consecutive_failures,
            "restart_attempts": self._restart_attempts,
            "current_incident": (
                self._current_incident.to_dict() if self._current_incident else None
            ),
            "total_incidents": len(self._incident_history),
            "uptime_seconds": (
                (datetime.utcnow() - self._last_successful_ping).total_seconds()
                if self._last_successful_ping
                else 0
            ),
        }
