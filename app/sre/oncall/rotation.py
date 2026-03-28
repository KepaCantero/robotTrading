"""
On-Call Rotation Management - SRE Rule 24

Implements fair and sustainable on-call rotation scheduling:
- Weekly rotation schedule
- Fair distribution of on-call burden
- Holiday and time-off handling
- Backup on-call assignment
- Rotation conflict detection
- On-call swap management
- Calendar integration
- Notification system

Domain Model (Cosmic Python - Rule 16):
- OncallEngineer: Domain entity for on-call personnel
- RotationSchedule: Value object for schedule configuration
- RotationSlot: Value object for scheduled slots
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class RotationType(str, Enum):
    """Types of rotation schedules."""

    WEEKLY = "weekly"  # Rotate every week
    DAILY = "daily"  # Rotate every day
    BIWEEKLY = "biweekly"  # Rotate every 2 weeks
    MONTHLY = "monthly"  # Rotate every month


class OncallStatus(str, Enum):
    """On-call engineer status."""

    AVAILABLE = "available"
    ONCALL = "oncall"
    BACKUP = "backup"
    UNAVAILABLE = "unavailable"
    VACATION = "vacation"
    SICK = "sick"
    TRAINING = "training"


@dataclass(frozen=True)
class TimeSlot:
    """Value object for time slot (Cosmic Python)."""

    start: datetime
    end: datetime

    @property
    def duration_hours(self) -> float:
        """Duration in hours."""
        return (self.end - self.start).total_seconds() / 3600

    @property
    def duration_days(self) -> float:
        """Duration in days."""
        return self.duration_hours / 24

    def overlaps(self, other: "TimeSlot") -> bool:
        """Check if this slot overlaps with another."""
        return not (self.end <= other.start or self.start >= other.end)

    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp is within slot."""
        return self.start <= timestamp <= self.end


@dataclass
class OncallEngineer:
    """
    Domain entity for on-call engineer (Cosmic Python).

    Represents an engineer who can be on-call with their
    availability, preferences, and on-call history.
    """

    engineer_id: str
    name: str
    email: str
    phone: str
    timezone: str
    status: OncallStatus = OncallStatus.AVAILABLE
    is_primary: bool = True  # Can be primary on-call
    is_backup: bool = True  # Can be backup on-call
    skills: List[str] = field(default_factory=list)
    preferred_days: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    unavailable_periods: List[TimeSlot] = field(default_factory=list)

    # Statistics
    oncall_count: int = 0
    backup_count: int = 0
    total_oncall_hours: float = 0.0
    last_oncall_date: Optional[datetime] = None

    # Constraints
    max_consecutive_weeks: int = 4
    min_hours_between_shifts: int = 12

    def __post_init__(self):
        """Validate engineer invariants."""
        if not self.engineer_id:
            raise ValueError("Engineer ID cannot be empty")
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email required")
        if not self.phone:
            raise ValueError("Phone number required")
        if not self.is_primary and not self.is_backup:
            raise ValueError("Engineer must be primary or backup")

    def is_available_during(self, slot: TimeSlot) -> bool:
        """Check if engineer is available during time slot."""
        # Check status
        if self.status in (OncallStatus.UNAVAILABLE, OncallStatus.VACATION, OncallStatus.SICK):
            return False

        # Check unavailable periods
        return all(not slot.overlaps(unavailable) for unavailable in self.unavailable_periods)

    def can_be_oncall(self, slot: TimeSlot, is_primary: bool = True) -> bool:
        """
        Check if engineer can be on-call for slot.

        Args:
            slot: Time slot to check
            is_primary: True for primary, False for backup

        Returns:
            True if engineer can be on-call
        """
        # Check availability
        if not self.is_available_during(slot):
            return False

        # Check role eligibility
        if is_primary and not self.is_primary:
            return False
        if not is_primary and not self.is_backup:
            return False

        # Check consecutive weeks
        if self.last_oncall_date:
            weeks_since_last = (slot.start - self.last_oncall_date).days / 7
            if weeks_since_last < 1 and self.oncall_count >= self.max_consecutive_weeks:
                return False

        return True

    def get_oncall_burden(self) -> float:
        """
        Calculate on-call burden score.

        Returns:
            Burden score (higher = more burden)
        """
        # Weight factors
        primary_weight = 1.0
        backup_weight = 0.3
        recency_weight = 0.5

        # Recent burden (last 90 days)
        recent_hours = self.total_oncall_hours
        recency_factor = min(recent_hours / (24 * 90), 1.0)  # Cap at 90 days

        burden = (
            (self.oncall_count * primary_weight)
            + (self.backup_count * backup_weight)
            + (recency_factor * recency_weight * 100)
        )

        return burden

    def assign_oncall(self, slot: TimeSlot, is_primary: bool = True) -> None:
        """
        Assign on-call shift to engineer.

        Args:
            slot: Time slot being assigned
            is_primary: True for primary, False for backup
        """
        if is_primary:
            self.oncall_count += 1
        else:
            self.backup_count += 1

        self.total_oncall_hours += slot.duration_hours
        self.last_oncall_date = slot.start

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "engineer_id": self.engineer_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "timezone": self.timezone,
            "status": self.status.value,
            "is_primary": self.is_primary,
            "is_backup": self.is_backup,
            "skills": self.skills,
            "oncall_count": self.oncall_count,
            "backup_count": self.backup_count,
            "total_oncall_hours": round(self.total_oncall_hours, 2),
            "burden_score": round(self.get_oncall_burden(), 2),
            "last_oncall_date": (
                self.last_oncall_date.isoformat() if self.last_oncall_date else None
            ),
        }


@dataclass
class RotationSlot:
    """Value object for a scheduled on-call slot."""

    slot_id: str
    time_slot: TimeSlot
    primary_engineer_id: str
    backup_engineer_id: Optional[str] = None
    rotation_type: RotationType = RotationType.WEEKLY
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate slot invariants."""
        if not self.slot_id:
            raise ValueError("Slot ID cannot be empty")
        if self.time_slot.end <= self.time_slot.start:
            raise ValueError("Invalid time slot")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slot_id": self.slot_id,
            "start": self.time_slot.start.isoformat(),
            "end": self.time_slot.end.isoformat(),
            "duration_hours": self.time_slot.duration_hours,
            "primary_engineer_id": self.primary_engineer_id,
            "backup_engineer_id": self.backup_engineer_id,
            "rotation_type": self.rotation_type.value,
            "is_active": self.is_active,
            "notes": self.notes,
        }


@dataclass
class RotationConfig:
    """Configuration for rotation manager."""

    # Schedule settings
    rotation_type: RotationType = RotationType.WEEKLY
    rotation_start_day: int = 0  # 0=Monday
    handoff_hour: int = 9  # 9 AM
    handoff_minute: int = 0

    # Constraint settings
    max_consecutive_weeks: int = 4
    min_backup_assignments: int = 1
    require_backup: bool = True

    # Burden balancing
    enable_burden_balancing: bool = True
    max_burden_imbalance_pct: float = 20.0  # Max 20% difference

    # Notifications
    notify_in_advance_hours: int = 48  # Notify 48 hours before shift
    reminder_hours_before: int = 2  # Reminder 2 hours before

    # Database
    db_path: str = "data/oncall_rotation.db"

    # Callbacks
    on_rotation_assigned: Optional[Callable[[RotationSlot], None]] = None
    on_engineer_unavailable: Optional[Callable[[str, TimeSlot], None]] = None


class OncallRotation:
    """
    On-call rotation manager (SRE Rule 24).

    Responsibilities:
    - Generate fair rotation schedules
    - Assign primary and backup on-call
    - Handle time-off and conflicts
    - Track on-call burden
    - Enable on-call swaps
    - Manage rotation calendar

    Domain Logic (Cosmic Python - Rule 16):
    - OncallEngineer is the core domain entity
    - Business rules encapsulated in domain methods
    - Fairness and burden balancing are domain concerns
    """

    def __init__(
        self,
        engineers: List[OncallEngineer],
        config: Optional[RotationConfig] = None,
    ):
        """
        Initialize rotation manager.

        Args:
            engineers: List of available engineers
            config: Rotation configuration
        """
        self.engineers = {e.engineer_id: e for e in engineers}
        self.config = config or RotationConfig()
        self.logger = logging.getLogger(f"{__name__}")

        # State
        self._slots: List[RotationSlot] = []
        self._lock = asyncio.Lock()

        self.logger.info(
            f"OncallRotation initialized with {len(engineers)} engineers "
            f"(rotation: {self.config.rotation_type.value})"
        )

    async def initialize(self) -> None:
        """Initialize the rotation manager."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()

                # Load existing slots
                await self._load_slots()

                # Load engineer statistics
                await self._load_engineer_stats()

                self.logger.info("OncallRotation initialized successfully")

            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                # Rotation slots table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rotation_slots (
                        slot_id TEXT PRIMARY KEY,
                        start_datetime TEXT NOT NULL,
                        end_datetime TEXT NOT NULL,
                        primary_engineer_id TEXT NOT NULL,
                        backup_engineer_id TEXT,
                        rotation_type TEXT NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        notes TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (primary_engineer_id) REFERENCES engineers(engineer_id),
                        FOREIGN KEY (backup_engineer_id) REFERENCES engineers(engineer_id)
                    )
                """
                )

                # Engineers table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS engineers (
                        engineer_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        timezone TEXT NOT NULL,
                        status TEXT NOT NULL,
                        is_primary BOOLEAN NOT NULL DEFAULT 1,
                        is_backup BOOLEAN NOT NULL DEFAULT 1,
                        skills TEXT,
                        oncall_count INTEGER NOT NULL DEFAULT 0,
                        backup_count INTEGER NOT NULL DEFAULT 0,
                        total_oncall_hours REAL NOT NULL DEFAULT 0,
                        last_oncall_date TEXT,
                        max_consecutive_weeks INTEGER NOT NULL DEFAULT 4,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc')),
                        updated_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Unavailable periods table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS unavailable_periods (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        engineer_id TEXT NOT NULL,
                        start_datetime TEXT NOT NULL,
                        end_datetime TEXT NOT NULL,
                        reason TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc')),
                        FOREIGN KEY (engineer_id) REFERENCES engineers(engineer_id)
                    )
                """
                )

                # Swap requests table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS swap_requests (
                        swap_id TEXT PRIMARY KEY,
                        requester_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        slot_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        requested_at TEXT NOT NULL,
                        responded_at TEXT,
                        reason TEXT,
                        FOREIGN KEY (requester_id) REFERENCES engineers(engineer_id),
                        FOREIGN KEY (target_id) REFERENCES engineers(engineer_id),
                        FOREIGN KEY (slot_id) REFERENCES rotation_slots(slot_id)
                    )
                """
                )

                # Create indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_slots_start_time
                    ON rotation_slots(start_datetime)
                """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_slots_engineer
                    ON rotation_slots(primary_engineer_id)
                """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_unavailable_engineer
                    ON unavailable_periods(engineer_id)
                """
                )

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_slots(self) -> None:
        """Load existing rotation slots."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT slot_id, start_datetime, end_datetime,
                           primary_engineer_id, backup_engineer_id,
                           rotation_type, is_active, notes, created_at
                    FROM rotation_slots
                    WHERE end_datetime >= datetime('utc')
                    ORDER BY start_datetime ASC
                """
                )

                rows = await cursor.fetchall()
                self._slots = []

                for row in rows:
                    slot = RotationSlot(
                        slot_id=row[0],
                        time_slot=TimeSlot(
                            start=datetime.fromisoformat(row[1]),
                            end=datetime.fromisoformat(row[2]),
                        ),
                        primary_engineer_id=row[3],
                        backup_engineer_id=row[4],
                        rotation_type=RotationType(row[5]),
                        is_active=bool(row[6]),
                        notes=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                    )
                    self._slots.append(slot)

            self.logger.info(f"Loaded {len(self._slots)} rotation slots")

        except (aiosqlite.Error, ValueError) as e:
            self.logger.error(f"Error loading slots: {e}")

    async def _load_engineer_stats(self) -> None:
        """Load engineer statistics from database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                for engineer_id, engineer in self.engineers.items():
                    cursor = await db.execute(
                        """
                        SELECT oncall_count, backup_count, total_oncall_hours, last_oncall_date
                        FROM engineers
                        WHERE engineer_id = ?
                        """,
                        (engineer_id,),
                    )

                    row = await cursor.fetchone()
                    if row:
                        engineer.oncall_count = row[0] or 0
                        engineer.backup_count = row[1] or 0
                        engineer.total_oncall_hours = row[2] or 0.0
                        engineer.last_oncall_date = (
                            datetime.fromisoformat(row[3]) if row[3] else None
                        )

                    # Load unavailable periods
                    cursor = await db.execute(
                        """
                        SELECT start_datetime, end_datetime
                        FROM unavailable_periods
                        WHERE engineer_id = ? AND end_datetime >= datetime('utc')
                        ORDER BY start_datetime ASC
                        """,
                        (engineer_id,),
                    )

                    rows = await cursor.fetchall()
                    engineer.unavailable_periods = [
                        TimeSlot(
                            start=datetime.fromisoformat(row[0]),
                            end=datetime.fromisoformat(row[1]),
                        )
                        for row in rows
                    ]

            self.logger.debug("Engineer statistics loaded")

        except (aiosqlite.Error, ValueError) as e:
            self.logger.error(f"Error loading engineer stats: {e}")

    async def generate_schedule(
        self,
        start_date: datetime,
        num_weeks: int = 12,
    ) -> List[RotationSlot]:
        """
        Generate rotation schedule for specified period.

        Args:
            start_date: Start date for schedule
            num_weeks: Number of weeks to schedule

        Returns:
            List of scheduled rotation slots
        """
        async with self._lock:
            slots = []

            try:
                # Calculate rotation duration
                if self.config.rotation_type == RotationType.WEEKLY:
                    duration_days = 7
                elif self.config.rotation_type == RotationType.BIWEEKLY:
                    duration_days = 14
                elif self.config.rotation_type == RotationType.MONTHLY:
                    duration_days = 30
                else:  # DAILY
                    duration_days = 1

                # Generate slots
                current_start = start_date
                week_count = 0

                while week_count < num_weeks:
                    current_end = current_start + timedelta(days=duration_days)
                    time_slot = TimeSlot(start=current_start, end=current_end)

                    # Assign primary
                    primary_id = await self._assign_primary(time_slot)

                    if not primary_id:
                        self.logger.warning(f"No primary available for {current_start}")
                        current_start = current_end
                        continue

                    # Assign backup if required
                    backup_id = None
                    if self.config.require_backup:
                        backup_id = await self._assign_backup(time_slot, primary_id)

                    # Create slot
                    slot_id = f"slot_{current_start.strftime('%Y%m%d')}_{primary_id}"
                    slot = RotationSlot(
                        slot_id=slot_id,
                        time_slot=time_slot,
                        primary_engineer_id=primary_id,
                        backup_engineer_id=backup_id,
                        rotation_type=self.config.rotation_type,
                    )

                    slots.append(slot)
                    self._slots.append(slot)

                    # Save to database
                    await self._save_slot(slot)

                    # Notify callback
                    if self.config.on_rotation_assigned:
                        try:
                            self.config.on_rotation_assigned(slot)
                        except Exception as e:
                            self.logger.error(f"Error in rotation assigned callback: {e}")

                    # Update engineer stats
                    self.engineers[primary_id].assign_oncall(time_slot, is_primary=True)
                    if backup_id:
                        self.engineers[backup_id].assign_oncall(time_slot, is_primary=False)

                    # Move to next slot
                    current_start = current_end
                    week_count += 1

                self.logger.info(f"Generated {len(slots)} rotation slots")

                return slots

            except Exception as e:
                self.logger.error(f"Error generating schedule: {e}")
                raise

    async def _assign_primary(self, slot: TimeSlot) -> Optional[str]:
        """Assign primary on-call for slot."""
        # Get eligible engineers
        eligible = [
            (eng_id, eng)
            for eng_id, eng in self.engineers.items()
            if eng.can_be_oncall(slot, is_primary=True)
        ]

        if not eligible:
            return None

        # Sort by burden (lowest first) for fairness
        eligible.sort(key=lambda x: x[1].get_oncall_burden())

        # Apply burden balancing if enabled
        if self.config.enable_burden_balancing and len(eligible) > 1:
            # Check if there's significant imbalance
            min_burden = eligible[0][1].get_oncall_burden()
            max_burden = eligible[-1][1].get_oncall_burden()

            if max_burden > 0:
                imbalance_pct = ((max_burden - min_burden) / max_burden) * 100

                # If imbalance is high, prefer lowest burden
                if imbalance_pct > self.config.max_burden_imbalance_pct:
                    return eligible[0][0]

        # Return engineer with lowest burden
        return eligible[0][0]

    async def _assign_backup(
        self,
        slot: TimeSlot,
        primary_id: str,
    ) -> Optional[str]:
        """Assign backup on-call for slot."""
        # Get eligible engineers (excluding primary)
        eligible = [
            (eng_id, eng)
            for eng_id, eng in self.engineers.items()
            if eng_id != primary_id and eng.can_be_oncall(slot, is_primary=False)
        ]

        if not eligible:
            return None

        # Sort by burden (lowest first)
        eligible.sort(key=lambda x: x[1].get_oncall_burden())

        return eligible[0][0]

    async def _save_slot(self, slot: RotationSlot) -> None:
        """Save slot to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO rotation_slots
                    (slot_id, start_datetime, end_datetime, primary_engineer_id,
                     backup_engineer_id, rotation_type, is_active, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        slot.slot_id,
                        slot.time_slot.start.isoformat(),
                        slot.time_slot.end.isoformat(),
                        slot.primary_engineer_id,
                        slot.backup_engineer_id,
                        slot.rotation_type.value,
                        slot.is_active,
                        slot.notes,
                        slot.created_at.isoformat(),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving slot: {e}")

    async def get_current_oncall(self) -> Optional[Dict[str, Any]]:
        """
        Get current on-call assignment.

        Returns:
            Dictionary with primary and backup, or None
        """
        try:
            now = datetime.utcnow()

            # Find active slot
            current_slot = None
            for slot in self._slots:
                if slot.is_active and slot.time_slot.contains(now):
                    current_slot = slot
                    break

            if not current_slot:
                return None

            primary = self.engineers.get(current_slot.primary_engineer_id)
            backup = None
            if current_slot.backup_engineer_id:
                backup = self.engineers.get(current_slot.backup_engineer_id)

            return {
                "slot_id": current_slot.slot_id,
                "start": current_slot.time_slot.start.isoformat(),
                "end": current_slot.time_slot.end.isoformat(),
                "primary": primary.to_dict() if primary else None,
                "backup": backup.to_dict() if backup else None,
                "rotation_type": current_slot.rotation_type.value,
            }

        except Exception as e:
            self.logger.error(f"Error getting current on-call: {e}")
            return None

    async def add_unavailable_period(
        self,
        engineer_id: str,
        start: datetime,
        end: datetime,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Add unavailable period for engineer.

        Args:
            engineer_id: Engineer ID
            start: Start of unavailable period
            end: End of unavailable period
            reason: Optional reason

        Returns:
            True if added successfully
        """
        try:
            if engineer_id not in self.engineers:
                self.logger.error(f"Engineer {engineer_id} not found")
                return False

            # Add to engineer
            time_slot = TimeSlot(start=start, end=end)
            self.engineers[engineer_id].unavailable_periods.append(time_slot)

            # Save to database
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO unavailable_periods
                    (engineer_id, start_datetime, end_datetime, reason)
                    VALUES (?, ?, ?, ?)
                """,
                    (engineer_id, start.isoformat(), end.isoformat(), reason),
                )
                await db.commit()

            self.logger.info(f"Added unavailable period for {engineer_id}: {start} to {end}")

            # Check for conflicts
            await self._check_conflicts(engineer_id, time_slot)

            return True

        except Exception as e:
            self.logger.error(f"Error adding unavailable period: {e}")
            return False

    async def _check_conflicts(
        self,
        engineer_id: str,
        unavailable_slot: TimeSlot,
    ) -> None:
        """Check if unavailable period conflicts with scheduled shifts."""
        conflicts = []

        for slot in self._slots:
            if not slot.is_active:
                continue

            if (slot.primary_engineer_id == engineer_id or slot.backup_engineer_id == engineer_id) and unavailable_slot.overlaps(slot.time_slot):
                conflicts.append(slot)

        if conflicts:
            self.logger.warning(
                f"Found {len(conflicts)} conflicts for {engineer_id}. " f"May need reassignment."
            )

            # Notify callback
            if self.config.on_engineer_unavailable:
                try:
                    for conflict in conflicts:
                        self.config.on_engineer_unavailable(engineer_id, conflict.time_slot)
                except Exception as e:
                    self.logger.error(f"Error in unavailable callback: {e}")

    async def get_engineer_burden_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get burden statistics for all engineers.

        Returns:
            Dictionary mapping engineer_id to stats
        """
        stats = {}

        for eng_id, engineer in self.engineers.items():
            stats[eng_id] = {
                **engineer.to_dict(),
                "fairness_ratio": self._calculate_fairness_ratio(engineer),
            }

        return stats

    def _calculate_fairness_ratio(self, engineer: OncallEngineer) -> float:
        """
        Calculate fairness ratio for engineer.

        Returns:
            Ratio where 1.0 = fair, < 1.0 = underutilized, > 1.0 = overutilized
        """
        # Calculate average burden across all engineers
        total_burden = sum(e.get_oncall_burden() for e in self.engineers.values())
        avg_burden = total_burden / len(self.engineers) if self.engineers else 0

        if avg_burden == 0:
            return 1.0

        return engineer.get_oncall_burden() / avg_burden

    async def get_upcoming_schedule(
        self,
        weeks: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming rotation schedule.

        Args:
            weeks: Number of weeks to return

        Returns:
            List of upcoming slots
        """
        try:
            now = datetime.utcnow()
            cutoff = now + timedelta(weeks=weeks)

            upcoming = [
                slot.to_dict()
                for slot in self._slots
                if slot.is_active and slot.time_slot.start > now and slot.time_slot.start <= cutoff
            ]

            # Add engineer details
            for slot_dict in upcoming:
                primary_id = slot_dict["primary_engineer_id"]
                if primary_id in self.engineers:
                    slot_dict["primary_engineer"] = self.engineers[primary_id].to_dict()

                backup_id = slot_dict.get("backup_engineer_id")
                if backup_id and backup_id in self.engineers:
                    slot_dict["backup_engineer"] = self.engineers[backup_id].to_dict()

            return upcoming

        except Exception as e:
            self.logger.error(f"Error getting upcoming schedule: {e}")
            return []
