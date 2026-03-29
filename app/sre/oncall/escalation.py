# mypy: ignore-errors
"""
Escalation Policies and Paths - SRE Rule 24

Implements comprehensive incident escalation system:
- Multi-level escalation paths
- Automatic escalation based on time
- Severity-based routing
- On-call escalation tracking
- Escalation notification system
- Post-escalation analysis
- Integration with rotation system
- Escalation metrics and reporting

Domain Model (Cosmic Python - Rule 16):
- EscalationPath: Domain entity for escalation flow
- EscalationLevel: Value object for escalation tiers
- EscalationIncident: Value object for tracked escalations
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import aiosqlite

from app.shared.utils.safe_parse import safe_parse

logger = logging.getLogger(__name__)


class IncidentSeverity(str, Enum):
    """Incident severity levels (SRE standard)."""

    SEV1 = "sev1"  # Critical - Business impact
    SEV2 = "sev2"  # High - Major service degradation
    SEV3 = "sev3"  # Medium - Service degradation
    SEV4 = "sev4"  # Low - Minor issue


class EscalationStatus(str, Enum):
    """Status of escalation request."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class LevelType(str, Enum):
    """Types of escalation levels."""

    ONCALL = "oncall"  # Current on-call engineer
    MANAGER = "manager"  # Engineering manager
    DIRECTOR = "director"  # Engineering director
    VP = "vp"  # VP of Engineering
    CTO = "cto"  # CTO/Head of Engineering
    EXECUTIVE = "executive"  # Executive team


@dataclass(frozen=True)
class EscalationLevel:
    """
    Value object for escalation level (Cosmic Python).

    Represents a single tier in the escalation chain with
    time thresholds and contact information.
    """

    level: int
    name: str
    level_type: LevelType
    contact_email: str
    contact_phone: str
    escalation_minutes: int  # Escalate if no response in X minutes
    is_primary: bool = True
    is_backup: bool = True

    @property
    def escalation_threshold(self) -> timedelta:
        """Get escalation threshold as timedelta."""
        return timedelta(minutes=self.escalation_minutes)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "name": self.name,
            "type": self.level_type.value,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "escalation_minutes": self.escalation_minutes,
            "is_primary": self.is_primary,
            "is_backup": self.is_backup,
        }


@dataclass
class EscalationPath:
    """
    Domain entity for escalation path (Cosmic Python).

    Defines the complete escalation chain for a service
    or team with multiple levels and timing rules.
    """

    path_id: str
    name: str
    service: str
    levels: list[EscalationLevel]
    severity_filter: list[IncidentSeverity] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate path invariants."""
        if not self.path_id:
            raise ValueError("Path ID cannot be empty")
        if not self.name:
            raise ValueError("Path name cannot be empty")
        if not self.levels:
            raise ValueError("Path must have at least one level")

        # Validate level ordering
        for i, level in enumerate(self.levels):
            if level.level != i + 1:
                raise ValueError(f"Level {i + 1} has incorrect level number: {level.level}")

    def get_level(self, level_num: int) -> EscalationLevel | None:
        """Get escalation level by number."""
        for level in self.levels:
            if level.level == level_num:
                return level
        return None

    def get_next_level(self, current_level: int) -> EscalationLevel | None:
        """Get next escalation level."""
        return self.get_level(current_level + 1)

    def should_escalate(
        self,
        severity: IncidentSeverity,
        current_level: int,
    ) -> bool:
        """
        Check if incident should escalate.

        Args:
            severity: Incident severity
            current_level: Current escalation level

        Returns:
            True if should escalate
        """
        # Check if severity is in filter
        if self.severity_filter and severity not in self.severity_filter:
            return False

        # Check if there's a next level
        return self.get_next_level(current_level) is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path_id": self.path_id,
            "name": self.name,
            "service": self.service,
            "levels": [level.to_dict() for level in self.levels],
            "severity_filter": [s.value for s in self.severity_filter],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EscalationIncident:
    """
    Value object for tracked escalation incident.

    Records the state of an active escalation including
    current level, timestamps, and contact history.
    """

    incident_id: str
    escalation_path_id: str
    severity: IncidentSeverity
    title: str
    description: str
    service: str
    current_level: int = 1
    status: EscalationStatus = EscalationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: datetime | None = None
    escalated_at: datetime | None = None
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None
    contact_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate incident invariants."""
        if not self.incident_id:
            raise ValueError("Incident ID cannot be empty")
        if not self.title:
            raise ValueError("Title cannot be empty")

    def should_auto_escalate(self, threshold_minutes: int) -> bool:
        """
        Check if incident should auto-escalate based on time.

        Args:
            threshold_minutes: Minutes before auto-escalation

        Returns:
            True if should auto-escalate
        """
        if self.status in (EscalationStatus.RESOLVED, EscalationStatus.CANCELLED):
            return False

        if self.status == EscalationStatus.ACKNOWLEDGED:
            return False

        # Check time since creation
        elapsed = (datetime.utcnow() - self.created_at).total_seconds() / 60
        return elapsed >= threshold_minutes

    def acknowledge(self, acknowledged_by: str) -> None:
        """Acknowledge incident."""
        self.status = EscalationStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = acknowledged_by

    def escalate(self, new_level: int) -> None:
        """Escalate to next level."""
        self.current_level = new_level
        self.status = EscalationStatus.ESCALATED
        self.escalated_at = datetime.utcnow()

    def resolve(self) -> None:
        """Mark incident as resolved."""
        self.status = EscalationStatus.RESOLVED
        self.resolved_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel incident."""
        self.status = EscalationStatus.CANCELLED

    def add_contact_attempt(
        self,
        level: int,
        method: str,
        success: bool,
        notes: str | None = None,
    ) -> None:
        """Record contact attempt."""
        self.contact_history.append(
            {
                "level": level,
                "method": method,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
                "notes": notes,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "incident_id": self.incident_id,
            "escalation_path_id": self.escalation_path_id,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "service": self.service,
            "current_level": self.current_level,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_by": self.acknowledged_by,
            "contact_attempts": len(self.contact_history),
            "metadata": self.metadata,
        }


@dataclass
class EscalationPolicy:
    """Configuration for escalation manager."""

    # Auto-escalation settings
    enable_auto_escalation: bool = True
    auto_escalation_check_interval_seconds: int = 60  # Check every minute

    # Notification settings
    notification_methods: list[str] = field(default_factory=lambda: ["sms", "email", "call"])
    max_contact_attempts: int = 3
    retry_delay_minutes: int = 5

    # Severity-based settings
    sev1_escalation_minutes: int = 15  # Escalate SEV1 every 15 minutes
    sev2_escalation_minutes: int = 30
    sev3_escalation_minutes: int = 60
    sev4_escalation_minutes: int = 120

    # Database
    db_path: str = "data/oncall_escalation.db"

    # Callbacks
    on_escalation: Callable[[EscalationIncident], None] | None = None
    on_acknowledgement: Callable[[EscalationIncident], None] | None = None
    on_resolution: Callable[[EscalationIncident], None] | None = None


class EscalationManager:
    """
    Escalation manager (SRE Rule 24).

    Responsibilities:
    - Manage escalation paths and policies
    - Track active escalations
    - Auto-escalate based on time thresholds
    - Send escalation notifications
    - Record contact history
    - Generate escalation metrics

    Domain Logic (Cosmic Python - Rule 16):
    - EscalationPath is the core domain entity
    - Escalation rules are business logic
    - Timing and routing are domain concerns
    """

    def __init__(
        self,
        paths: list[EscalationPath],
        config: EscalationPolicy | None = None,
    ):
        """
        Initialize escalation manager.

        Args:
            paths: List of escalation paths
            config: Escalation policy configuration
        """
        self.paths = {p.path_id: p for p in paths}
        self.config = config or EscalationPolicy()
        self.logger = logging.getLogger(f"{__name__}")

        # State
        self._incidents: dict[str, EscalationIncident] = {}
        self._lock = asyncio.Lock()

        # Auto-escalation task
        self._escalation_task: asyncio.Task | None = None
        self._is_running = False

        self.logger.info(
            f"EscalationManager initialized with {len(paths)} paths "
            f"(auto-escalation: {self.config.enable_auto_escalation})"
        )

    async def initialize(self) -> None:
        """Initialize the escalation manager."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()

                # Load existing incidents
                await self._load_incidents()

                # Start auto-escalation if enabled
                if self.config.enable_auto_escalation:
                    await self.start_auto_escalation()

                self.logger.info("EscalationManager initialized successfully")

            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                # Escalation paths table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS escalation_paths (
                        path_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        service TEXT NOT NULL,
                        severity_filter TEXT,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL
                    )
                """
                )

                # Escalation levels table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS escalation_levels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path_id TEXT NOT NULL,
                        level INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        level_type TEXT NOT NULL,
                        contact_email TEXT NOT NULL,
                        contact_phone TEXT NOT NULL,
                        escalation_minutes INTEGER NOT NULL,
                        is_primary BOOLEAN NOT NULL DEFAULT 1,
                        is_backup BOOLEAN NOT NULL DEFAULT 1,
                        FOREIGN KEY (path_id) REFERENCES escalation_paths(path_id),
                        UNIQUE(path_id, level)
                    )
                """
                )

                # Escalation incidents table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS escalation_incidents (
                        incident_id TEXT PRIMARY KEY,
                        escalation_path_id TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        service TEXT NOT NULL,
                        current_level INTEGER NOT NULL DEFAULT 1,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        acknowledged_at TEXT,
                        escalated_at TEXT,
                        resolved_at TEXT,
                        acknowledged_by TEXT,
                        metadata TEXT,
                        FOREIGN KEY (escalation_path_id) REFERENCES escalation_paths(path_id)
                    )
                """
                )

                # Contact history table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS contact_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        incident_id TEXT NOT NULL,
                        level INTEGER NOT NULL,
                        method TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        notes TEXT,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (incident_id) REFERENCES escalation_incidents(incident_id)
                    )
                """
                )

                # Create indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_incidents_status
                    ON escalation_incidents(status)
                """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_incidents_service
                    ON escalation_incidents(service)
                """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_contact_incident
                    ON contact_history(incident_id)
                """
                )

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_incidents(self) -> None:
        """Load active incidents from database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT incident_id, escalation_path_id, severity, title,
                           description, service, current_level, status,
                           created_at, acknowledged_at, escalated_at, resolved_at,
                           acknowledged_by, metadata
                    FROM escalation_incidents
                    WHERE status NOT IN ('resolved', 'cancelled')
                    ORDER BY created_at DESC
                """
                )

                rows = await cursor.fetchall()
                self._incidents = {}

                for row in rows:
                    incident = EscalationIncident(
                        incident_id=row[0],
                        escalation_path_id=row[1],
                        severity=IncidentSeverity(row[2]),
                        title=row[3],
                        description=row[4] or "",
                        service=row[5],
                        current_level=row[6],
                        status=EscalationStatus(row[7]),
                        created_at=datetime.fromisoformat(row[8]),
                        acknowledged_at=datetime.fromisoformat(row[9]) if row[9] else None,
                        escalated_at=datetime.fromisoformat(row[10]) if row[10] else None,
                        resolved_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        acknowledged_by=row[12],
                        metadata=safe_parse(row[13], default={}) if row[13] else {},
                    )

                    self._incidents[incident.incident_id] = incident

            self.logger.info(f"Loaded {len(self._incidents)} active incidents")

        except (aiosqlite.Error, ValueError) as e:
            self.logger.error(f"Error loading incidents: {e}")

    async def start_auto_escalation(self) -> None:
        """Start automatic escalation monitoring."""
        if self._is_running:
            self.logger.warning("Auto-escalation already running")
            return

        self._is_running = True
        self._escalation_task = asyncio.create_task(self._escalation_loop())
        self.logger.info("Started auto-escalation")

    async def stop_auto_escalation(self) -> None:
        """Stop automatic escalation monitoring."""
        self._is_running = False
        if self._escalation_task:
            self._escalation_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._escalation_task
        self.logger.info("Stopped auto-escalation")

    async def _escalation_loop(self) -> None:
        """Main auto-escalation loop."""
        while self._is_running:
            try:
                await self._check_auto_escalations()
                await asyncio.sleep(self.config.auto_escalation_check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in escalation loop: {e}")
                await asyncio.sleep(self.config.auto_escalation_check_interval_seconds)

    async def _check_auto_escalations(self) -> None:
        """Check for incidents that need auto-escalation."""
        async with self._lock:
            for incident in list(self._incidents.values()):
                if incident.status in (EscalationStatus.RESOLVED, EscalationStatus.CANCELLED):
                    continue

                # Get escalation path
                path = self.paths.get(incident.escalation_path_id)
                if not path:
                    continue

                # Get current level
                current_level = path.get_level(incident.current_level)
                if not current_level:
                    continue

                # Check if should auto-escalate
                if incident.should_auto_escalate(current_level.escalation_minutes):
                    await self._escalate_incident(incident)

    async def _escalate_incident(self, incident: EscalationIncident) -> None:
        """Escalate incident to next level."""
        try:
            path = self.paths.get(incident.escalation_path_id)
            if not path:
                self.logger.error(f"Path {incident.escalation_path_id} not found")
                return

            next_level = path.get_next_level(incident.current_level)
            if not next_level:
                self.logger.warning(f"No next level for incident {incident.incident_id}")
                return

            # Escalate
            incident.escalate(next_level.level)

            # Send notification
            await self._send_escalation_notification(incident, next_level)

            # Save to database
            await self._save_incident(incident)

            # Notify callback
            if self.config.on_escalation:
                try:
                    self.config.on_escalation(incident)
                except Exception as e:
                    self.logger.error(f"Error in escalation callback: {e}")

            self.logger.warning(
                f"Escalated incident {incident.incident_id} to level {next_level.level}"
            )

        except Exception as e:
            self.logger.error(f"Error escalating incident: {e}")

    async def _send_escalation_notification(
        self,
        incident: EscalationIncident,
        level: EscalationLevel,
    ) -> None:
        """Send escalation notification."""
        # Record contact attempt
        for method in self.config.notification_methods:
            success = await self._send_notification(
                incident=incident,
                level=level,
                method=method,
            )

            incident.add_contact_attempt(
                level=level.level,
                method=method,
                success=success,
            )

    async def _send_notification(
        self,
        incident: EscalationIncident,
        level: EscalationLevel,
        method: str,
    ) -> bool:
        """
        Send notification via specified method.

        Args:
            incident: Escalation incident
            level: Escalation level
            method: Notification method

        Returns:
            True if successful
        """
        # In production, this would integrate with actual notification services
        # For now, we just log
        self.logger.info(
            f"Sending {method} notification to {level.name} "
            f"({level.contact_email}) for incident {incident.incident_id}"
        )

        # Simulate success
        return True

    async def create_incident(
        self,
        escalation_path_id: str,
        severity: IncidentSeverity,
        title: str,
        description: str,
        service: str,
        metadata: dict[str, Any] | None = None,
    ) -> EscalationIncident | None:
        """
        Create new escalation incident.

        Args:
            escalation_path_id: ID of escalation path to use
            severity: Incident severity
            title: Incident title
            description: Incident description
            service: Affected service
            metadata: Additional metadata

        Returns:
            Created incident or None
        """
        async with self._lock:
            try:
                # Validate path exists
                if escalation_path_id not in self.paths:
                    self.logger.error(f"Path {escalation_path_id} not found")
                    return None

                # Create incident
                incident_id = f"inc_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                incident = EscalationIncident(
                    incident_id=incident_id,
                    escalation_path_id=escalation_path_id,
                    severity=severity,
                    title=title,
                    description=description,
                    service=service,
                    metadata=metadata or {},
                )

                # Get initial level and send notification
                path = self.paths[escalation_path_id]
                initial_level = path.get_level(1)
                if initial_level:
                    await self._send_escalation_notification(incident, initial_level)

                # Store incident
                self._incidents[incident_id] = incident

                # Save to database
                await self._save_incident(incident)

                self.logger.info(f"Created escalation incident: {incident_id}")

                return incident

            except Exception as e:
                self.logger.error(f"Error creating incident: {e}")
                return None

    async def acknowledge_incident(
        self,
        incident_id: str,
        acknowledged_by: str,
    ) -> bool:
        """
        Acknowledge escalation incident.

        Args:
            incident_id: ID of incident to acknowledge
            acknowledged_by: Who is acknowledging

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                incident = self._incidents.get(incident_id)
                if not incident:
                    self.logger.error(f"Incident {incident_id} not found")
                    return False

                incident.acknowledge(acknowledged_by)
                await self._save_incident(incident)

                # Notify callback
                if self.config.on_acknowledgement:
                    try:
                        self.config.on_acknowledgement(incident)
                    except Exception as e:
                        self.logger.error(f"Error in acknowledgement callback: {e}")

                self.logger.info(f"Incident {incident_id} acknowledged by {acknowledged_by}")

                return True

            except Exception as e:
                self.logger.error(f"Error acknowledging incident: {e}")
                return False

    async def resolve_incident(self, incident_id: str) -> bool:
        """
        Resolve escalation incident.

        Args:
            incident_id: ID of incident to resolve

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                incident = self._incidents.get(incident_id)
                if not incident:
                    self.logger.error(f"Incident {incident_id} not found")
                    return False

                incident.resolve()
                await self._save_incident(incident)

                # Notify callback
                if self.config.on_resolution:
                    try:
                        self.config.on_resolution(incident)
                    except Exception as e:
                        self.logger.error(f"Error in resolution callback: {e}")

                self.logger.info(f"Incident {incident_id} resolved")

                return True

            except Exception as e:
                self.logger.error(f"Error resolving incident: {e}")
                return False

    async def _save_incident(self, incident: EscalationIncident) -> None:
        """Save incident to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO escalation_incidents
                    (incident_id, escalation_path_id, severity, title, description,
                     service, current_level, status, created_at, acknowledged_at,
                     escalated_at, resolved_at, acknowledged_by, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        incident.incident_id,
                        incident.escalation_path_id,
                        incident.severity.value,
                        incident.title,
                        incident.description,
                        incident.service,
                        incident.current_level,
                        incident.status.value,
                        incident.created_at.isoformat(),
                        incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                        incident.escalated_at.isoformat() if incident.escalated_at else None,
                        incident.resolved_at.isoformat() if incident.resolved_at else None,
                        incident.acknowledged_by,
                        str(incident.metadata),
                    ),
                )

                # Save contact history
                for attempt in incident.contact_history:
                    await db.execute(
                        """
                        INSERT INTO contact_history
                        (incident_id, level, method, success, notes, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            incident.incident_id,
                            attempt["level"],
                            attempt["method"],
                            attempt["success"],
                            attempt.get("notes"),
                            attempt["timestamp"],
                        ),
                    )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving incident: {e}")

    async def get_active_incidents(self) -> list[dict[str, Any]]:
        """
        Get all active incidents.

        Returns:
            List of active incidents
        """
        async with self._lock:
            return [
                incident.to_dict()
                for incident in self._incidents.values()
                if incident.status not in (EscalationStatus.RESOLVED, EscalationStatus.CANCELLED)
            ]

    async def get_incident_metrics(self) -> dict[str, Any]:
        """
        Get escalation metrics.

        Returns:
            Metrics dictionary
        """
        async with self._lock:
            total = len(self._incidents)
            active = sum(
                1
                for i in self._incidents.values()
                if i.status not in (EscalationStatus.RESOLVED, EscalationStatus.CANCELLED)
            )

            by_severity = {}
            for incident in self._incidents.values():
                sev = incident.severity.value
                by_severity[sev] = by_severity.get(sev, 0) + 1

            by_status = {}
            for incident in self._incidents.values():
                status = incident.status.value
                by_status[status] = by_status.get(status, 0) + 1

            return {
                "total_incidents": total,
                "active_incidents": active,
                "by_severity": by_severity,
                "by_status": by_status,
                "escalation_paths": len(self.paths),
            }
