# pylint: disable=eval-used
# mypy: ignore-errors
"""
Shift Handoff Procedures - SRE Rule 24

Implements comprehensive shift handoff system:
- Structured handoff checklists
- Knowledge transfer documentation
- Context sharing procedures
- Incident handoff tracking
- Outstanding tasks tracking
- System status summary
- Handoff quality metrics
- Automated handoff reminders

Domain Model (Cosmic Python - Rule 16):
- HandoffSession: Domain entity for handoff events
- HandoffChecklist: Value object for required items
- HandoffContext: Value object for shared context
"""

from __future__ import annotations
import numpy as np

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class HandoffStatus(str, Enum):
    """Status of handoff session."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChecklistItemType(str, Enum):
    """Types of checklist items."""

    INCIDENT_REVIEW = "incident_review"
    SYSTEM_STATUS = "system_status"
    OUTSTANDING_TASKS = "outstanding_tasks"
    KNOWLEDGE_TRANSFER = "knowledge_transfer"
    DOCUMENTATION = "documentation"
    RUNBOOK_REVIEW = "runbook_review"
    METRICS_REVIEW = "metrics_review"


@dataclass(frozen=True)
class ChecklistItem:
    """
    Value object for checklist item (Cosmic Python).

    Represents a single item in the handoff checklist with
    validation criteria and completion status.
    """

    item_id: str
    title: str
    description: str
    item_type: ChecklistItemType
    is_required: bool = True
    estimated_minutes: int = 5
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "title": self.title,
            "description": self.description,
            "type": self.item_type.value,
            "is_required": self.is_required,
            "estimated_minutes": self.estimated_minutes,
            "depends_on": self.depends_on,
        }


@dataclass
class ChecklistCompletion:
    """Record of checklist item completion."""

    item_id: str
    is_completed: bool = False
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)  # Links to docs, etc.


@dataclass
class HandoffContext:
    """
    Value object for handoff context (Cosmic Python).

    Contains all context information that needs to be
    transferred during handoff.
    """

    # System status
    system_health: Dict[str, str] = field(default_factory=dict)
    active_incidents: List[Dict[str, Any]] = field(default_factory=list)
    recent_incidents: List[Dict[str, Any]] = field(default_factory=list)

    # Outstanding work
    outstanding_tasks: List[Dict[str, Any]] = field(default_factory=list)
    in_progress_changes: List[Dict[str, Any]] = field(default_factory=list)
    pending_deployments: List[Dict[str, Any]] = field(default_factory=list)

    # Knowledge artifacts
    documentation_links: List[str] = field(default_factory=list)
    runbook_references: List[str] = field(default_factory=list)
    important_contacts: Dict[str, str] = field(default_factory=dict)

    # Metrics and trends
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    recent_alerts: List[Dict[str, Any]] = field(default_factory=list)

    # Special considerations
    known_issues: List[Dict[str, Any]] = field(default_factory=list)
    upcoming_maintenance: List[Dict[str, Any]] = field(default_factory=list)
    special_instructions: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "system_health": self.system_health,
            "active_incidents_count": len(self.active_incidents),
            "recent_incidents_count": len(self.recent_incidents),
            "outstanding_tasks_count": len(self.outstanding_tasks),
            "in_progress_changes_count": len(self.in_progress_changes),
            "pending_deployments_count": len(self.pending_deployments),
            "documentation_links": self.documentation_links,
            "runbook_references": self.runbook_references,
            "important_contacts": self.important_contacts,
            "key_metrics": self.key_metrics,
            "recent_alerts_count": len(self.recent_alerts),
            "known_issues_count": len(self.known_issues),
            "upcoming_maintenance_count": len(self.upcoming_maintenance),
            "special_instructions": self.special_instructions,
        }


@dataclass
class HandoffSession:
    """
    Domain entity for handoff session (Cosmic Python).

    Represents a complete handoff session between on-call
    engineers with checklist and context tracking.
    """

    session_id: str
    from_engineer_id: str
    to_engineer_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    checklist_items: List[ChecklistItem]
    status: HandoffStatus = HandoffStatus.PENDING
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    context: Optional[HandoffContext] = None
    completions: Dict[str, ChecklistCompletion] = field(default_factory=dict)
    notes: str = ""
    quality_score: Optional[float] = None  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate session invariants."""
        if not self.session_id:
            raise ValueError("Session ID cannot be empty")
        if not self.from_engineer_id:
            raise ValueError("From engineer ID required")
        if not self.to_engineer_id:
            raise ValueError("To engineer ID required")
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("Invalid schedule")

        # Initialize completions
        if not self.completions:
            for item in self.checklist_items:
                self.completions[item.item_id] = ChecklistCompletion(item_id=item.item_id)

    def start(self) -> None:
        """Start handoff session."""
        if self.status != HandoffStatus.PENDING:
            raise ValueError(f"Cannot start session with status {self.status.value}")
        self.status = HandoffStatus.IN_PROGRESS
        self.actual_start = datetime.utcnow()

    def complete(self, notes: str = "") -> None:
        """Complete handoff session."""
        if self.status != HandoffStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete session with status {self.status.value}")
        self.status = HandoffStatus.COMPLETED
        self.actual_end = datetime.utcnow()
        self.notes = notes

    def fail(self, reason: str) -> None:
        """Mark handoff session as failed."""
        self.status = HandoffStatus.FAILED
        self.actual_end = datetime.utcnow()
        self.notes = f"Handoff failed: {reason}"

    def cancel(self) -> None:
        """Cancel handoff session."""
        self.status = HandoffStatus.CANCELLED
        self.actual_end = datetime.utcnow()

    def complete_item(
        self,
        item_id: str,
        completed_by: str,
        notes: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> bool:
        """
        Mark checklist item as complete.

        Args:
            item_id: ID of item to complete
            completed_by: Who completed it
            notes: Optional notes
            artifacts: Optional artifact links

        Returns:
            True if successful
        """
        if item_id not in self.completions:
            return False

        completion = self.completions[item_id]
        completion.is_completed = True
        completion.completed_by = completed_by
        completion.completed_at = datetime.utcnow()
        completion.notes = notes
        if artifacts:
            completion.artifacts.extend(artifacts)

        return True

    def get_completion_percentage(self) -> float:
        """Get checklist completion percentage."""
        if not self.completions:
            return 0.0

        required = [c for c in self.completions.values() if c.is_completed]
        return len(required) / len(self.completions) * 100

    def get_required_remaining(self) -> List[ChecklistItem]:
        """Get list of required items not yet completed."""
        remaining = []
        for item in self.checklist_items:
            if not item.is_required:
                continue
            if not self.completions.get(
                item.item_id, ChecklistCompletion(item_id=item.item_id)
            ).is_completed:
                remaining.append(item)
        return remaining

    def calculate_quality_score(self) -> float:
        """
        Calculate handoff quality score.

        Returns:
            Score from 0.0 to 1.0
        """
        # Completion score (40%)
        completion_score = self.get_completion_percentage() / 100 * 0.4

        # Duration score (20%) - was it within scheduled time?
        duration_score = 0.2
        if self.actual_start and self.actual_end:
            scheduled_duration = (self.scheduled_end - self.scheduled_start).total_seconds()
            actual_duration = (self.actual_end - self.actual_start).total_seconds()
            if actual_duration <= scheduled_duration:
                duration_score = 0.2
            elif actual_duration <= scheduled_duration * 1.5:
                duration_score = 0.1
            else:
                duration_score = 0.0

        # Context quality score (20%) - was context provided?
        context_score = 0.2 if self.context else 0.0

        # Required items score (20%) - all required items completed?
        required_items = [i for i in self.checklist_items if i.is_required]
        required_completed = sum(
            1
            for i in required_items
            if self.completions.get(i.item_id, ChecklistCompletion(item_id=i.item_id)).is_completed
        )
        required_score = (required_completed / len(required_items) * 0.2) if required_items else 0.2

        total_score = completion_score + duration_score + context_score + required_score
        self.quality_score = round(total_score, 2)

        return self.quality_score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "from_engineer_id": self.from_engineer_id,
            "to_engineer_id": self.to_engineer_id,
            "scheduled_start": self.scheduled_start.isoformat(),
            "scheduled_end": self.scheduled_end.isoformat(),
            "status": self.status.value,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "completion_percentage": round(self.get_completion_percentage(), 2),
            "required_remaining": len(self.get_required_remaining()),
            "quality_score": self.quality_score or self.calculate_quality_score(),
            "checklist_items": [item.to_dict() for item in self.checklist_items],
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class HandoffConfig:
    """Configuration for handoff manager."""

    # Timing settings
    default_handoff_duration_minutes: int = 30
    reminder_minutes_before: int = 15
    max_handoff_duration_minutes: int = 60

    # Quality thresholds
    min_quality_score: float = 0.7  # Require 70% quality
    require_all_required_items: bool = True

    # Notification settings
    notify_participants: bool = True
    notify_on_delay: bool = True
    delay_threshold_minutes: int = 10

    # Database
    db_path: str = "data/oncall_handoff.db"

    # Callbacks
    on_handoff_completed: Optional[Callable[[HandoffSession], None]] = None
    on_handoff_failed: Optional[Callable[[HandoffSession], None]] = None
    on_quality_low: Optional[Callable[[HandoffSession], None]] = None


class HandoffManager:
    """
    Handoff manager (SRE Rule 24).

    Responsibilities:
    - Create and schedule handoffs
    - Provide handoff checklists
    - Track handoff completion
    - Calculate quality scores
    - Monitor handoff metrics
    - Ensure knowledge transfer

    Domain Logic (Cosmic Python - Rule 16):
    - HandoffSession is the core domain entity
    - Handoff quality is a domain concern
    - Checklist requirements are business rules
    """

    # Default checklist items
    DEFAULT_CHECKLIST = [
        ChecklistItem(
            item_id="incident_review",
            title="Review Active Incidents",
            description="Discuss all active and recent incidents",
            item_type=ChecklistItemType.INCIDENT_REVIEW,
            is_required=True,
            estimated_minutes=10,
        ),
        ChecklistItem(
            item_id="system_status",
            title="Review System Status",
            description="Review overall system health and any anomalies",
            item_type=ChecklistItemType.SYSTEM_STATUS,
            is_required=True,
            estimated_minutes=5,
        ),
        ChecklistItem(
            item_id="outstanding_tasks",
            title="Review Outstanding Tasks",
            description="Discuss any pending tasks or follow-ups",
            item_type=ChecklistItemType.OUTSTANDING_TASKS,
            is_required=True,
            estimated_minutes=5,
        ),
        ChecklistItem(
            item_id="knowledge_transfer",
            title="Knowledge Transfer",
            description="Share any important learnings or insights",
            item_type=ChecklistItemType.KNOWLEDGE_TRANSFER,
            is_required=False,
            estimated_minutes=5,
        ),
        ChecklistItem(
            item_id="documentation",
            title="Update Documentation",
            description="Ensure all relevant docs are up to date",
            item_type=ChecklistItemType.DOCUMENTATION,
            is_required=False,
            estimated_minutes=3,
        ),
        ChecklistItem(
            item_id="runbook_review",
            title="Review Relevant Runbooks",
            description="Identify and review relevant runbooks",
            item_type=ChecklistItemType.RUNBOOK_REVIEW,
            is_required=True,
            estimated_minutes=5,
        ),
        ChecklistItem(
            item_id="metrics_review",
            title="Review Key Metrics",
            description="Review SLO compliance, error budgets, and key metrics",
            item_type=ChecklistItemType.METRICS_REVIEW,
            is_required=True,
            estimated_minutes=5,
        ),
    ]

    def __init__(
        self,
        config: Optional[HandoffConfig] = None,
        checklist_items: Optional[List[ChecklistItem]] = None,
    ):
        """
        Initialize handoff manager.

        Args:
            config: Handoff configuration
            checklist_items: Custom checklist items (uses default if None)
        """
        self.config = config or HandoffConfig()
        self.checklist_items = checklist_items or self.DEFAULT_CHECKLIST
        self.logger = logging.getLogger(f"{__name__}")

        # State
        self._sessions: Dict[str, HandoffSession] = {}
        self._lock = asyncio.Lock()

        self.logger.info(
            f"HandoffManager initialized with {len(self.checklist_items)} checklist items"
        )

    async def initialize(self) -> None:
        """Initialize the handoff manager."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()

                # Load active sessions
                await self._load_sessions()

                self.logger.info("HandoffManager initialized successfully")

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                # Handoff sessions table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS handoff_sessions (
                        session_id TEXT PRIMARY KEY,
                        from_engineer_id TEXT NOT NULL,
                        to_engineer_id TEXT NOT NULL,
                        scheduled_start TEXT NOT NULL,
                        scheduled_end TEXT NOT NULL,
                        status TEXT NOT NULL,
                        actual_start TEXT,
                        actual_end TEXT,
                        notes TEXT,
                        quality_score REAL,
                        created_at TEXT NOT NULL
                    )
                """
                )

                # Checklist completions table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS checklist_completions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        item_id TEXT NOT NULL,
                        is_completed BOOLEAN NOT NULL DEFAULT 0,
                        completed_by TEXT,
                        completed_at TEXT,
                        notes TEXT,
                        artifacts TEXT,
                        FOREIGN KEY (session_id) REFERENCES handoff_sessions(session_id),
                        UNIQUE(session_id, item_id)
                    )
                """
                )

                # Handoff context table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS handoff_context (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        context_data TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc')),
                        FOREIGN KEY (session_id) REFERENCES handoff_sessions(session_id)
                    )
                """
                )

                # Create indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_status
                    ON handoff_sessions(status)
                """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sessions_engineer
                    ON handoff_sessions(to_engineer_id)
                """
                )

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_sessions(self) -> None:
        """Load active handoff sessions."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT session_id, from_engineer_id, to_engineer_id,
                           scheduled_start, scheduled_end, status,
                           actual_start, actual_end, notes, quality_score, created_at
                    FROM handoff_sessions
                    WHERE status NOT IN ('completed', 'failed', 'cancelled')
                    ORDER BY scheduled_start ASC
                """
                )

                rows = await cursor.fetchall()
                self._sessions = {}

                for row in rows:
                    session = HandoffSession(
                        session_id=row[0],
                        from_engineer_id=row[1],
                        to_engineer_id=row[2],
                        scheduled_start=datetime.fromisoformat(row[3]),
                        scheduled_end=datetime.fromisoformat(row[4]),
                        checklist_items=self.checklist_items,
                        status=HandoffStatus(row[5]),
                        actual_start=datetime.fromisoformat(row[6]) if row[6] else None,
                        actual_end=datetime.fromisoformat(row[7]) if row[7] else None,
                        notes=row[8] or "",
                        quality_score=row[9],
                        created_at=datetime.fromisoformat(row[10]),
                    )

                    # Load completions
                    comp_cursor = await db.execute(
                        """
                        SELECT item_id, is_completed, completed_by, completed_at, notes, artifacts
                        FROM checklist_completions
                        WHERE session_id = ?
                        """,
                        (row[0],),
                    )

                    comp_rows = await comp_cursor.fetchall()
                    for comp_row in comp_rows:
                        completion = ChecklistCompletion(
                            item_id=comp_row[0],
                            is_completed=bool(comp_row[1]),
                            completed_by=comp_row[2],
                            completed_at=(
                                datetime.fromisoformat(comp_row[3]) if comp_row[3] else None
                            ),
                            notes=comp_row[4],
                            artifacts=eval(
                                comp_row[5]
                            )  # nosec B307 - internal data from controlled source
                            if comp_row[5]
                            else [],
                        )
                        session.completions[completion.item_id] = completion

                    self._sessions[session.session_id] = session

            self.logger.info(f"Loaded {len(self._sessions)} active sessions")

        except (aiosqlite.Error, ValueError) as e:
            self.logger.error(f"Error loading sessions: {e}")

    async def create_handoff(
        self,
        from_engineer_id: str,
        to_engineer_id: str,
        scheduled_start: datetime,
        context: Optional[HandoffContext] = None,
    ) -> HandoffSession:
        """
        Create new handoff session.

        Args:
            from_engineer_id: Engineer handing off
            to_engineer_id: Engineer receiving handoff
            scheduled_start: Scheduled start time
            context: Optional handoff context

        Returns:
            Created handoff session
        """
        async with self._lock:
            try:
                # Calculate end time
                scheduled_end = scheduled_start + timedelta(
                    minutes=self.config.default_handoff_duration_minutes
                )

                # Create session
                session_id = f"handoff_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                session = HandoffSession(
                    session_id=session_id,
                    from_engineer_id=from_engineer_id,
                    to_engineer_id=to_engineer_id,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    checklist_items=self.checklist_items,
                    context=context,
                )

                # Store session
                self._sessions[session_id] = session

                # Save to database
                await self._save_session(session)

                self.logger.info(f"Created handoff session: {session_id}")

                return session

            except Exception as e:
                self.logger.error(f"Error creating handoff: {e}")
                raise

    async def start_handoff(self, session_id: str) -> bool:
        """
        Start handoff session.

        Args:
            session_id: ID of session to start

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                session = self._sessions.get(session_id)
                if not session:
                    self.logger.error(f"Session {session_id} not found")
                    return False

                session.start()
                await self._save_session(session)

                self.logger.info(f"Started handoff session: {session_id}")

                return True

            except Exception as e:
                self.logger.error(f"Error starting handoff: {e}")
                return False

    async def complete_handoff(
        self,
        session_id: str,
        notes: str = "",
    ) -> bool:
        """
        Complete handoff session.

        Args:
            session_id: ID of session to complete
            notes: Optional notes

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                session = self._sessions.get(session_id)
                if not session:
                    self.logger.error(f"Session {session_id} not found")
                    return False

                # Check if all required items are completed
                if self.config.require_all_required_items:
                    required_remaining = session.get_required_remaining()
                    if required_remaining:
                        self.logger.warning(
                            f"Session {session_id} has {len(required_remaining)} "
                            f"required items remaining"
                        )

                # Complete session
                session.complete(notes)

                # Calculate quality score
                quality_score = session.calculate_quality_score()

                # Save to database
                await self._save_session(session)

                # Check quality threshold
                if quality_score < self.config.min_quality_score:
                    self.logger.warning(
                        f"Session {session_id} has low quality score: {quality_score}"
                    )

                    if self.config.on_quality_low:
                        try:
                            self.config.on_quality_low(session)
                        except Exception as e:
                            self.logger.error(f"Error in quality low callback: {e}")

                # Notify callback
                if self.config.on_handoff_completed:
                    try:
                        self.config.on_handoff_completed(session)
                    except Exception as e:
                        self.logger.error(f"Error in handoff completed callback: {e}")

                self.logger.info(
                    f"Completed handoff session: {session_id} " f"(quality: {quality_score})"
                )

                return True

            except Exception as e:
                self.logger.error(f"Error completing handoff: {e}")
                return False

    async def complete_checklist_item(
        self,
        session_id: str,
        item_id: str,
        completed_by: str,
        notes: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> bool:
        """
        Complete a checklist item.

        Args:
            session_id: Handoff session ID
            item_id: Checklist item ID
            completed_by: Who completed it
            notes: Optional notes
            artifacts: Optional artifact links

        Returns:
            True if successful
        """
        async with self._lock:
            try:
                session = self._sessions.get(session_id)
                if not session:
                    self.logger.error(f"Session {session_id} not found")
                    return False

                success = session.complete_item(item_id, completed_by, notes, artifacts)
                if success:
                    await self._save_session(session)

                return success

            except Exception as e:
                self.logger.error(f"Error completing checklist item: {e}")
                return False

    async def _save_session(self, session: HandoffSession) -> None:
        """Save session to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                # Save session
                await db.execute(
                    """
                    INSERT OR REPLACE INTO handoff_sessions
                    (session_id, from_engineer_id, to_engineer_id, scheduled_start,
                     scheduled_end, status, actual_start, actual_end, notes,
                     quality_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session.session_id,
                        session.from_engineer_id,
                        session.to_engineer_id,
                        session.scheduled_start.isoformat(),
                        session.scheduled_end.isoformat(),
                        session.status.value,
                        session.actual_start.isoformat() if session.actual_start else None,
                        session.actual_end.isoformat() if session.actual_end else None,
                        session.notes,
                        session.quality_score,
                        session.created_at.isoformat(),
                    ),
                )

                # Save completions
                for completion in session.completions.values():
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO checklist_completions
                        (session_id, item_id, is_completed, completed_by, completed_at, notes, artifacts)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            session.session_id,
                            completion.item_id,
                            completion.is_completed,
                            completion.completed_by,
                            (
                                completion.completed_at.isoformat()
                                if completion.completed_at
                                else None
                            ),
                            completion.notes,
                            str(completion.artifacts) if completion.artifacts else None,
                        ),
                    )

                # Save context if present
                if session.context:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO handoff_context
                        (session_id, context_data, created_at)
                        VALUES (?, ?, ?)
                    """,
                        (
                            session.session_id,
                            str(session.context.to_dict()),
                            datetime.utcnow().isoformat(),
                        ),
                    )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving session: {e}")

    async def get_handoff_metrics(self) -> Dict[str, Any]:
        """
        Get handoff metrics.

        Returns:
            Metrics dictionary
        """
        async with self._lock:
            total = len(self._sessions)
            active = sum(
                1 for s in self._sessions.values() if s.status == HandoffStatus.IN_PROGRESS
            )
            completed = sum(
                1 for s in self._sessions.values() if s.status == HandoffStatus.COMPLETED
            )

            # Quality scores
            quality_scores = [
                s.quality_score for s in self._sessions.values() if s.quality_score is not None
            ]

            avg_quality = np.mean(quality_scores) if quality_scores else 0.0

            return {
                "total_sessions": total,
                "active_sessions": active,
                "completed_sessions": completed,
                "average_quality_score": round(avg_quality, 2),
                "checklist_items": len(self.checklist_items),
            }
