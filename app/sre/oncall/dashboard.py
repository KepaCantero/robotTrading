# mypy: ignore-errors
"""
On-Call Status Dashboard - SRE Rule 24

Implements comprehensive on-call dashboard for visibility:
- Current on-call display
- Upcoming schedule view
- Active incidents tracking
- Handoff status monitoring
- On-call burden metrics
- Escalation status display
- System health overview
- Quick access to runbooks

Domain Model (Cosmic Python - Rule 16):
- OncallStatus: Value object for current status
- OncallMetrics: Value object for KPIs
- DashboardView: Domain entity for presentation
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import aiosqlite

logger = logging.getLogger(__name__)


class DashboardViewType(str, Enum):
    """Types of dashboard views."""

    OVERVIEW = "overview"
    SCHEDULE = "schedule"
    INCIDENTS = "incidents"
    METRICS = "metrics"
    HANDOFFS = "handoffs"
    RUNBOOKS = "runbooks"


class StatusIndicator(str, Enum):
    """Status indicator levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OncallStatus:
    """
    Value object for current on-call status (Cosmic Python).

    Provides a snapshot of the current on-call state including
    primary, backup, and coverage information.
    """

    primary_engineer_id: str | None
    primary_engineer_name: str | None
    primary_contact: str | None
    backup_engineer_id: str | None
    backup_engineer_name: str | None
    backup_contact: str | None
    shift_start: datetime | None
    shift_end: datetime | None
    is_in_shift: bool = True
    coverage_status: StatusIndicator = StatusIndicator.HEALTHY
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary_engineer_id": self.primary_engineer_id,
            "primary_engineer_name": self.primary_engineer_name,
            "primary_contact": self.primary_contact,
            "backup_engineer_id": self.backup_engineer_id,
            "backup_engineer_name": self.backup_engineer_name,
            "backup_contact": self.backup_contact,
            "shift_start": self.shift_start.isoformat() if self.shift_start else None,
            "shift_end": self.shift_end.isoformat() if self.shift_end else None,
            "is_in_shift": self.is_in_shift,
            "coverage_status": self.coverage_status.value,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass(frozen=True)
class OncallMetrics:
    """
    Value object for on-call metrics (Cosmic Python).

    Contains key performance indicators for on-call operations
    including burden, response times, and handoff quality.
    """

    total_oncalls: int
    active_incidents: int
    avg_response_time_minutes: float
    avg_handoff_quality: float
    burden_fairness_score: float  # 0.0 to 1.0, 1.0 = perfectly fair
    escalation_rate: float  # Percentage of incidents escalated
    handoff_completion_rate: float  # Percentage of handoffs completed
    coverage_gaps: int  # Number of coverage gaps in schedule

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_oncalls": self.total_oncalls,
            "active_incidents": self.active_incidents,
            "avg_response_time_minutes": round(self.avg_response_time_minutes, 2),
            "avg_handoff_quality": round(self.avg_handoff_quality, 2),
            "burden_fairness_score": round(self.burden_fairness_score, 2),
            "escalation_rate_pct": round(self.escalation_rate, 2),
            "handoff_completion_rate_pct": round(self.handoff_completion_rate, 2),
            "coverage_gaps": self.coverage_gaps,
        }


@dataclass
class DashboardConfig:
    """Configuration for dashboard."""

    # Update settings
    refresh_interval_seconds: int = 30
    cache_duration_seconds: int = 60

    # Display settings
    show_upcoming_weeks: int = 4
    show_recent_incidents: int = 10
    show_active_handoffs: bool = True

    # Alert thresholds
    warning_coverage_hours: int = 1  # Warning if < 1 hour coverage remaining
    critical_coverage_hours: int = 0  # Critical if no coverage

    # Database
    db_path: str = "data/oncall_dashboard.db"

    # Callbacks
    on_status_change: Callable[[OncallStatus], None] | None = None
    on_metric_update: Callable[[OncallMetrics], None] | None = None


class OncallDashboard:
    """
    On-call dashboard (SRE Rule 24).

    Responsibilities:
    - Display current on-call status
    - Show upcoming schedule
    - Track active incidents
    - Monitor handoff progress
    - Calculate on-call metrics
    - Provide quick access to resources

    Domain Logic (Cosmic Python - Rule 16):
    - DashboardView is the presentation layer
    - Metrics calculation is domain logic
    - Status aggregation is a domain concern
    """

    def __init__(
        self,
        config: DashboardConfig | None = None,
    ):
        """
        Initialize on-call dashboard.

        Args:
            config: Dashboard configuration
        """
        self.config = config or DashboardConfig()
        self.logger = logging.getLogger(f"{__name__}")

        # State
        self._current_status: OncallStatus | None = None
        self._current_metrics: OncallMetrics | None = None
        self._cache_timestamp: datetime | None = None
        self._lock = asyncio.Lock()

        # Update task
        self._update_task: asyncio.Task | None = None
        self._is_running = False

        self.logger.info("OncallDashboard initialized")

    async def initialize(self) -> None:
        """Initialize the dashboard."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()

                # Load initial data
                await self._refresh_data()

                # Start automatic updates
                await self.start_updates()

                self.logger.info("OncallDashboard initialized successfully")

            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                # Dashboard cache table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dashboard_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Status history table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS status_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        status_data TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Metrics history table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS metrics_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metrics_data TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Create indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_status_history_created
                    ON status_history(created_at)
                """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_metrics_history_created
                    ON metrics_history(created_at)
                """
                )

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _refresh_data(self) -> None:
        """Refresh all dashboard data."""
        try:
            # Refresh status
            self._current_status = await self._calculate_status()

            # Refresh metrics
            self._current_metrics = await self._calculate_metrics()

            # Update cache timestamp
            self._cache_timestamp = datetime.utcnow()

            # Save to cache
            await self._save_to_cache()

            # Notify callbacks
            if self._current_status and self.config.on_status_change:
                try:
                    self.config.on_status_change(self._current_status)
                except Exception as e:
                    self.logger.error(f"Error in status change callback: {e}")

            if self._current_metrics and self.config.on_metric_update:
                try:
                    self.config.on_metric_update(self._current_metrics)
                except Exception as e:
                    self.logger.error(f"Error in metric update callback: {e}")

        except Exception as e:
            self.logger.error(f"Error refreshing data: {e}")

    async def _calculate_status(self) -> OncallStatus:
        """
        Calculate current on-call status.

        Returns:
            Current on-call status
        """
        # In production, this would query the rotation system
        # For now, return a placeholder
        return OncallStatus(
            primary_engineer_id="eng_1",
            primary_engineer_name="On-Call Engineer",
            primary_contact="oncall@example.com",
            backup_engineer_id="eng_2",
            backup_engineer_name="Backup Engineer",
            backup_contact="backup@example.com",
            shift_start=datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0),
            shift_end=datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
            + timedelta(days=7),
            is_in_shift=True,
            coverage_status=StatusIndicator.HEALTHY,
        )

    async def _calculate_metrics(self) -> OncallMetrics:
        """
        Calculate on-call metrics.

        Returns:
            Current metrics
        """
        # In production, this would aggregate from various sources
        # For now, return placeholders
        return OncallMetrics(
            total_oncalls=52,
            active_incidents=0,
            avg_response_time_minutes=5.2,
            avg_handoff_quality=0.85,
            burden_fairness_score=0.92,
            escalation_rate=8.5,
            handoff_completion_rate=95.0,
            coverage_gaps=0,
        )

    async def _save_to_cache(self) -> None:
        """Save current data to cache."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                # Save status
                if self._current_status:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO dashboard_cache (key, value, updated_at)
                        VALUES ('status', ?, ?)
                    """,
                        (json.dumps(self._current_status.to_dict()), datetime.utcnow().isoformat()),
                    )

                # Save metrics
                if self._current_metrics:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO dashboard_cache (key, value, updated_at)
                        VALUES ('metrics', ?, ?)
                    """,
                        (
                            json.dumps(self._current_metrics.to_dict()),
                            datetime.utcnow().isoformat(),
                        ),
                    )

                # Save status history
                if self._current_status:
                    await db.execute(
                        """
                        INSERT INTO status_history (status_data, created_at)
                        VALUES (?, ?)
                    """,
                        (json.dumps(self._current_status.to_dict()), datetime.utcnow().isoformat()),
                    )

                # Save metrics history
                if self._current_metrics:
                    await db.execute(
                        """
                        INSERT INTO metrics_history (metrics_data, created_at)
                        VALUES (?, ?)
                    """,
                        (
                            json.dumps(self._current_metrics.to_dict()),
                            datetime.utcnow().isoformat(),
                        ),
                    )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving to cache: {e}")

    async def start_updates(self) -> None:
        """Start automatic dashboard updates."""
        if self._is_running:
            self.logger.warning("Dashboard updates already running")
            return

        self._is_running = True
        self._update_task = asyncio.create_task(self._update_loop())
        self.logger.info("Started dashboard updates")

    async def stop_updates(self) -> None:
        """Stop automatic dashboard updates."""
        self._is_running = False
        if self._update_task:
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task
        self.logger.info("Stopped dashboard updates")

    async def _update_loop(self) -> None:
        """Main update loop."""
        while self._is_running:
            try:
                await self._refresh_data()
                await asyncio.sleep(self.config.refresh_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(self.config.refresh_interval_seconds)

    async def get_current_status(self) -> OncallStatus | None:
        """
        Get current on-call status.

        Returns:
            Current status or None
        """
        async with self._lock:
            # Check if cache is stale
            if self._cache_timestamp:
                age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
                if age > self.config.cache_duration_seconds:
                    await self._refresh_data()

            return self._current_status

    async def get_current_metrics(self) -> OncallMetrics | None:
        """
        Get current on-call metrics.

        Returns:
            Current metrics or None
        """
        async with self._lock:
            # Check if cache is stale
            if self._cache_timestamp:
                age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
                if age > self.config.cache_duration_seconds:
                    await self._refresh_data()

            return self._current_metrics

    async def get_dashboard_view(
        self,
        view_type: DashboardViewType = DashboardViewType.OVERVIEW,
    ) -> dict[str, Any]:
        """
        Get dashboard view data.

        Args:
            view_type: Type of view to return

        Returns:
            View data dictionary
        """
        async with self._lock:
            # Ensure fresh data
            if not self._cache_timestamp:
                await self._refresh_data()

            view_data = {
                "view_type": view_type.value,
                "generated_at": datetime.utcnow().isoformat(),
                "status": self._current_status.to_dict() if self._current_status else None,
                "metrics": self._current_metrics.to_dict() if self._current_metrics else None,
            }

            # Add view-specific data
            if view_type == DashboardViewType.OVERVIEW:
                view_data["summary"] = await self._get_overview_summary()
            elif view_type == DashboardViewType.SCHEDULE:
                view_data["schedule"] = await self._get_schedule_view()
            elif view_type == DashboardViewType.INCIDENTS:
                view_data["incidents"] = await self._get_incidents_view()
            elif view_type == DashboardViewType.METRICS:
                view_data["detailed_metrics"] = await self._get_detailed_metrics()
            elif view_type == DashboardViewType.HANDOFFS:
                view_data["handoffs"] = await self._get_handoffs_view()
            elif view_type == DashboardViewType.RUNBOOKS:
                view_data["runbooks"] = await self._get_runbooks_view()

            return view_data

    async def _get_overview_summary(self) -> dict[str, Any]:
        """Get overview summary."""
        return {
            "health_status": "healthy",
            "active_incidents": 0,
            "upcoming_handoffs": 1,
            "coverage_until": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "recent_activity": [],
        }

    async def _get_schedule_view(self) -> dict[str, Any]:
        """Get schedule view."""
        return {
            "current_week": {},
            "upcoming_weeks": [],
            "coverage_gaps": [],
        }

    async def _get_incidents_view(self) -> dict[str, Any]:
        """Get incidents view."""
        return {
            "active_incidents": [],
            "recent_incidents": [],
            "escalation_status": {},
        }

    async def _get_detailed_metrics(self) -> dict[str, Any]:
        """Get detailed metrics view."""
        return {
            "response_times": {},
            "burden_metrics": {},
            "quality_metrics": {},
            "trends": [],
        }

    async def _get_handoffs_view(self) -> dict[str, Any]:
        """Get handoffs view."""
        return {
            "pending_handoffs": [],
            "recent_handoffs": [],
            "quality_trends": [],
        }

    async def _get_runbooks_view(self) -> dict[str, Any]:
        """Get runbooks view."""
        return {
            "common_runbooks": [],
            "recently_used": [],
            "categories": [],
        }

    async def get_status_history(
        self,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Get status history.

        Args:
            hours: Number of hours of history to return

        Returns:
            List of historical status entries
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT status_data, created_at
                    FROM status_history
                    WHERE created_at >= ?
                    ORDER BY created_at ASC
                """,
                    (cutoff.isoformat(),),
                )

                rows = await cursor.fetchall()
                return [
                    {
                        "data": json.loads(row[0]),
                        "timestamp": row[1],
                    }
                    for row in rows
                ]

        except (aiosqlite.Error, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Error getting status history: {e}")
            return []

    async def get_metrics_history(
        self,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Get metrics history.

        Args:
            hours: Number of hours of history to return

        Returns:
            List of historical metrics entries
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT metrics_data, created_at
                    FROM metrics_history
                    WHERE created_at >= ?
                    ORDER BY created_at ASC
                """,
                    (cutoff.isoformat(),),
                )

                rows = await cursor.fetchall()
                return [
                    {
                        "data": json.loads(row[0]),
                        "timestamp": row[1],
                    }
                    for row in rows
                ]

        except (aiosqlite.Error, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Error getting metrics history: {e}")
            return []

    async def get_health_summary(self) -> dict[str, Any]:
        """
        Get overall health summary.

        Returns:
            Health summary dictionary
        """
        async with self._lock:
            status = await self.get_current_status()
            metrics = await self.get_current_metrics()

            health = {
                "overall_status": "healthy",
                "coverage_status": status.coverage_status.value if status else "unknown",
                "incident_count": metrics.active_incidents if metrics else 0,
                "quality_score": metrics.avg_handoff_quality if metrics else 0.0,
                "last_updated": (
                    self._cache_timestamp.isoformat() if self._cache_timestamp else None
                ),
            }

            # Determine overall status
            if health["incident_count"] > 0:
                health["overall_status"] = "warning"

            if health["coverage_status"] == "critical":
                health["overall_status"] = "critical"

            return health
