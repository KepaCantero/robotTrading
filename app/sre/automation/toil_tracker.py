# mypy: ignore-errors
"""
Toil Tracking System for SRE (Google SRE Chapter 1).

Toil = "Manual, repetitive work that could be automated."
Target: Reduce toil to <50% of total work.

This module implements comprehensive toil tracking following Google SRE principles:
- Track all operational work (toil vs. engineering)
- Calculate toil percentage over time windows
- Identify top sources of toil
- Generate automation opportunity reports
- Monitor progress toward toil reduction goals

Key Concepts:
- Toil: Manual, repetitive operational work (tickets, on-call, deployment, etc.)
- Engineering: Sustainable work that reduces future toil
- Target: Toil should be <50% of total work time
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


class ToilCategory(str, Enum):
    """Categories of toil work (Google SRE Chapter 1)."""

    INCIDENT_RESPONSE = "incident_response"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    CAPACITY_PLANNING = "capacity_planning"
    MAINTENANCE = "maintenance"
    SUPPORT = "support"
    DOCUMENTATION = "documentation"
    TROUBLESHOOTING = "troubleshooting"
    CONFIGURATION = "configuration"
    MANUAL_DATA = "manual_data"
    ON_CALL = "on_call"
    REVIEW = "review"
    OTHER = "other"


class AutomationPotential(str, Enum):
    """Potential for automation."""

    HIGH = "high"  # Clearly automatable with existing tools
    MEDIUM = "medium"  # Automatable with some development effort
    LOW = "low"  # Difficult to automate or requires significant effort
    NONE = "none"  # Human judgment required


@dataclass
class ToilEntry:
    """
    A single work entry for toil tracking.

    Attributes:
        timestamp: When the work occurred
        task: Description of the task
        category: Type of work (from ToilCategory)
        duration_minutes: Time spent on task
        automated: Whether this was automated or manual
        assignable: Whether this could be automated in the future
        automation_potential: Potential level for automation
        engineer: Engineer who performed the work (optional)
        tags: Additional tags for categorization
        notes: Free-form notes about the task
    """

    timestamp: datetime
    task: str
    category: ToilCategory
    duration_minutes: int
    automated: bool = False
    assignable: bool = True
    automation_potential: AutomationPotential = AutomationPotential.MEDIUM
    engineer: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        """Validate toil entry."""
        if self.duration_minutes < 0:
            raise ValueError("duration_minutes must be non-negative")
        if self.automated and not self.assignable:
            # If already automated, it must be assignable
            self.assignable = True

    @property
    def is_toil(self) -> bool:
        """
        Check if this entry represents toil.

        Toil is defined as manual work that could be automated.
        Engineering work (assignable=False) is not toil.
        """
        return not self.automated and self.assignable

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "task": self.task,
            "category": self.category.value,
            "duration_minutes": self.duration_minutes,
            "automated": self.automated,
            "assignable": self.assignable,
            "automation_potential": self.automation_potential.value,
            "engineer": self.engineer,
            "tags": self.tags,
            "notes": self.notes,
        }


@dataclass
class ToilMetrics:
    """Metrics for toil analysis."""

    total_minutes: int
    toil_minutes: int
    engineering_minutes: int
    toil_percentage: float
    engineering_percentage: float
    automated_minutes: int
    automation_coverage: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_minutes": self.total_minutes,
            "toil_minutes": self.toil_minutes,
            "engineering_minutes": self.engineering_minutes,
            "toil_percentage": round(self.toil_percentage, 2),
            "engineering_percentage": round(self.engineering_percentage, 2),
            "automated_minutes": self.automated_minutes,
            "automation_coverage": round(self.automation_coverage, 2),
        }


@dataclass
class AutomationOpportunity:
    """
    An identified opportunity for automation.

    Attributes:
        category: Category of toil
        task_pattern: Common task pattern (e.g., "manual deployment")
        frequency: How often this occurs (per month)
        avg_duration_minutes: Average time spent per occurrence
        total_toil_minutes: Total toil minutes per month
        automation_potential: Potential level for automation
        estimated_savings_hours: Estimated hours saved per month
        implementation_effort: Estimated implementation effort (LOW/MEDIUM/HIGH)
        priority: Priority score (0-100)
    """

    category: ToilCategory
    task_pattern: str
    frequency: int
    avg_duration_minutes: int
    total_toil_minutes: int
    automation_potential: AutomationPotential
    estimated_savings_hours: float
    implementation_effort: str
    priority: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "task_pattern": self.task_pattern,
            "frequency": self.frequency,
            "avg_duration_minutes": self.avg_duration_minutes,
            "total_toil_minutes": self.total_toil_minutes,
            "automation_potential": self.automation_potential.value,
            "estimated_savings_hours": round(self.estimated_savings_hours, 2),
            "implementation_effort": self.implementation_effort,
            "priority": self.priority,
        }


@dataclass
class ToilReport:
    """
    Comprehensive toil report.

    Attributes:
        period_start: Start of reporting period
        period_end: End of reporting period
        metrics: Overall toil metrics
        top_toil_sources: Top sources of toil
        automation_opportunities: Identified automation opportunities
        engineer_breakdown: Breakdown by engineer (if available)
        trend_data: Historical trend data
        recommendations: Recommendations for toil reduction
    """

    period_start: datetime
    period_end: datetime
    metrics: ToilMetrics
    top_toil_sources: List[Tuple[str, int]]
    automation_opportunities: List[AutomationOpportunity]
    engineer_breakdown: Dict[str, ToilMetrics]
    trend_data: List[Dict[str, Any]]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "metrics": self.metrics.to_dict(),
            "top_toil_sources": [
                {"source": source, "minutes": minutes} for source, minutes in self.top_toil_sources
            ],
            "automation_opportunities": [opp.to_dict() for opp in self.automation_opportunities],
            "engineer_breakdown": {
                eng: metrics.to_dict() for eng, metrics in self.engineer_breakdown.items()
            },
            "trend_data": self.trend_data,
            "recommendations": self.recommendations,
        }


@dataclass
class ToilConfig:
    """Configuration for toil tracker."""

    # Database
    db_path: str = "data/toil_tracker.db"

    # Thresholds
    toil_warning_threshold: float = 50.0  # Alert if toil > 50%
    toil_critical_threshold: float = 70.0  # Critical if toil > 70%

    # Automation targets
    automation_target_coverage: float = 80.0  # Target automation coverage %

    # Callbacks
    on_toil_threshold_exceeded: Optional[Callable[[ToilMetrics], None]] = None


class ToilTracker:
    """
    Track toil vs engineering work (Google SRE Chapter 1).

    Responsibilities:
    - Log work entries (toil vs engineering)
    - Calculate toil percentage over time windows
    - Identify top sources of toil
    - Generate automation opportunity reports
    - Track progress toward toil reduction goals
    - Alert when toil thresholds are exceeded

    Usage:
        tracker = ToilTracker("trading_system")

        # Log work
        tracker.log_work(
            task="Manual deployment to production",
            category=ToilCategory.DEPLOYMENT,
            duration=45,
            automated=False,
            assignable=True,
        )

        # Get toil percentage
        toil_pct = tracker.calculate_toil_percentage(days=30)

        # Generate report
        report = await tracker.generate_report(days=30)
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[ToilConfig] = None,
    ):
        """
        Initialize toil tracker.

        Args:
            service_name: Name of the service being tracked
            config: Toil tracker configuration
        """
        self.service_name = service_name
        self.config = config or ToilConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._entries: List[ToilEntry] = []
        self._lock = asyncio.Lock()

        # Category mappings for analysis
        self._category_patterns: Dict[ToilCategory, List[str]] = {
            ToilCategory.INCIDENT_RESPONSE: [
                "incident",
                "outage",
                "sev",
                "alert",
                "page",
                "emergency",
            ],
            ToilCategory.DEPLOYMENT: [
                "deploy",
                "release",
                "rollout",
                "rollback",
                "promotion",
            ],
            ToilCategory.MONITORING: [
                "monitor",
                "alert",
                "dashboard",
                "metric",
                "graph",
            ],
            ToilCategory.CAPACITY_PLANNING: [
                "capacity",
                "scaling",
                "resource",
                "forecast",
            ],
            ToilCategory.MAINTENANCE: [
                "maintenance",
                "patch",
                "upgrade",
                "cleanup",
            ],
            ToilCategory.SUPPORT: [
                "support",
                "ticket",
                "help",
                "user issue",
            ],
            ToilCategory.DOCUMENTATION: [
                "document",
                "wiki",
                "runbook",
                "sop",
            ],
            ToilCategory.TROUBLESHOOTING: [
                "troubleshoot",
                "debug",
                "investigate",
                "diagnose",
            ],
            ToilCategory.CONFIGURATION: [
                "config",
                "setting",
                "parameter",
            ],
            ToilCategory.MANUAL_DATA: [
                "manual data",
                "data entry",
                "spreadsheet",
            ],
            ToilCategory.ON_CALL: [
                "on-call",
                "handoff",
                "escalation",
            ],
            ToilCategory.REVIEW: [
                "review",
                "audit",
                "check",
            ],
        }

        self.logger.info(
            f"ToilTracker initialized for {service_name} "
            f"(thresholds: warning={self.config.toil_warning_threshold}%, "
            f"critical={self.config.toil_critical_threshold}%)"
        )

    async def initialize(self) -> None:
        """Initialize the toil tracker."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()

                # Load recent entries
                await self._load_recent_entries()

                self.logger.info("ToilTracker initialized successfully")

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            # Ensure data directory exists
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                # Create toil entries table
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS toil_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        task TEXT NOT NULL,
                        category TEXT NOT NULL,
                        duration_minutes INTEGER NOT NULL,
                        automated BOOLEAN NOT NULL,
                        assignable BOOLEAN NOT NULL,
                        automation_potential TEXT NOT NULL,
                        engineer TEXT,
                        tags TEXT,
                        notes TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Create indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_toil_service_timestamp
                    ON toil_entries(service_name, timestamp)
                    """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_toil_category
                    ON toil_entries(category)
                    """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_toil_engineer
                    ON toil_entries(engineer)
                    """
                )

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_recent_entries(self, days: int = 30) -> None:
        """Load recent entries from database."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT timestamp, task, category, duration_minutes,
                           automated, assignable, automation_potential,
                           engineer, tags, notes
                    FROM toil_entries
                    WHERE service_name = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    """,
                    (self.service_name, cutoff.isoformat()),
                )

                rows = await cursor.fetchall()

                self._entries = [
                    ToilEntry(
                        timestamp=datetime.fromisoformat(row[0]),
                        task=row[1],
                        category=ToilCategory(row[2]),
                        duration_minutes=row[3],
                        automated=bool(row[4]),
                        assignable=bool(row[5]),
                        automation_potential=AutomationPotential(row[6]),
                        engineer=row[7],
                        tags=json.loads(row[8]) if row[8] else [],
                        notes=row[9] if row[9] else "",
                    )
                    for row in rows
                ]

                self.logger.debug(f"Loaded {len(self._entries)} recent entries")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error loading entries: {e}")

    def log_work(
        self,
        task: str,
        category: str,
        duration: int,
        automated: bool = False,
        assignable: bool = True,
        automation_potential: str = "medium",
        engineer: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> ToilEntry:
        """
        Log a work entry.

        Args:
            task: Description of the task
            category: Category of work (string or ToilCategory)
            duration: Duration in minutes
            automated: Whether this was automated
            assignable: Whether this could be automated
            automation_potential: Potential for automation (high/medium/low/none)
            engineer: Engineer who performed the work
            tags: Additional tags
            notes: Additional notes

        Returns:
            Created ToilEntry
        """
        try:
            # Convert category to enum
            if isinstance(category, str):
                try:
                    category_enum = ToilCategory(category)
                except ValueError:
                    # Auto-detect category from task description
                    category_enum = self._detect_category(task)
            else:
                category_enum = category

            # Convert automation potential
            if isinstance(automation_potential, str):
                potential = AutomationPotential(automation_potential)
            else:
                potential = automation_potential

            entry = ToilEntry(
                timestamp=datetime.utcnow(),
                task=task,
                category=category_enum,
                duration_minutes=duration,
                automated=automated,
                assignable=assignable,
                automation_potential=potential,
                engineer=engineer,
                tags=tags or [],
                notes=notes,
            )

            self._entries.append(entry)

            self.logger.debug(
                f"Logged work: {task} ({duration}min, "
                f"category={category_enum.value}, automated={automated})"
            )

            return entry

        except (ValueError, TypeError) as e:
            self.logger.error(f"Error logging work: {e}")
            raise

    def _detect_category(self, task: str) -> ToilCategory:
        """Auto-detect category from task description."""
        task_lower = task.lower()

        for category, patterns in self._category_patterns.items():
            if any(pattern in task_lower for pattern in patterns):
                return category

        return ToilCategory.OTHER

    async def save_entry(self, entry: ToilEntry) -> None:
        """Save entry to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO toil_entries (
                        service_name, timestamp, task, category, duration_minutes,
                        automated, assignable, automation_potential,
                        engineer, tags, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.service_name,
                        entry.timestamp.isoformat(),
                        entry.task,
                        entry.category.value,
                        entry.duration_minutes,
                        entry.automated,
                        entry.assignable,
                        entry.automation_potential.value,
                        entry.engineer,
                        json.dumps(entry.tags) if entry.tags else None,
                        entry.notes,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving entry: {e}")

    async def save_all_entries(self) -> None:
        """Save all in-memory entries to database."""
        for entry in self._entries:
            await self.save_entry(entry)

    def calculate_toil_percentage(
        self,
        days: int = 30,
        engineer: Optional[str] = None,
    ) -> float:
        """
        Calculate toil as percentage of total work.

        Args:
            days: Number of days to analyze
            engineer: Filter by specific engineer

        Returns:
            Toil percentage (0-100)
        """
        try:
            # Filter entries by time window
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = [
                e
                for e in self._entries
                if e.timestamp >= cutoff and (engineer is None or e.engineer == engineer)
            ]

            if not filtered:
                return 0.0

            # Calculate metrics
            total_minutes = sum(e.duration_minutes for e in filtered)
            toil_minutes = sum(e.duration_minutes for e in filtered if e.is_toil)

            if total_minutes == 0:
                return 0.0

            toil_percentage = (toil_minutes / total_minutes) * 100

            # Check thresholds
            if toil_percentage > self.config.toil_critical_threshold:
                self.logger.critical(
                    f"CRITICAL: Toil at {toil_percentage:.1f}% "
                    f">(critical threshold: {self.config.toil_critical_threshold}%)"
                )
                if self.config.on_toil_threshold_exceeded:
                    metrics = self._calculate_metrics(filtered)
                    self.config.on_toil_threshold_exceeded(metrics)

            elif toil_percentage > self.config.toil_warning_threshold:
                self.logger.warning(
                    f"WARNING: Toil at {toil_percentage:.1f}% "
                    f">(warning threshold: {self.config.toil_warning_threshold}%)"
                )

            return toil_percentage

        except (ZeroDivisionError, ValueError) as e:
            self.logger.error(f"Error calculating toil percentage: {e}")
            return 0.0

    def _calculate_metrics(self, entries: List[ToilEntry]) -> ToilMetrics:
        """Calculate metrics from entries."""
        total_minutes = sum(e.duration_minutes for e in entries)
        toil_minutes = sum(e.duration_minutes for e in entries if e.is_toil)
        engineering_minutes = sum(e.duration_minutes for e in entries if not e.is_toil)
        automated_minutes = sum(e.duration_minutes for e in entries if e.automated)

        toil_pct = (toil_minutes / total_minutes * 100) if total_minutes > 0 else 0
        eng_pct = (engineering_minutes / total_minutes * 100) if total_minutes > 0 else 0
        automation_coverage = (automated_minutes / total_minutes * 100) if total_minutes > 0 else 0

        return ToilMetrics(
            total_minutes=total_minutes,
            toil_minutes=toil_minutes,
            engineering_minutes=engineering_minutes,
            toil_percentage=toil_pct,
            engineering_percentage=eng_pct,
            automated_minutes=automated_minutes,
            automation_coverage=automation_coverage,
        )

    def get_top_toil_sources(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> List[Tuple[str, int]]:
        """
        Get top sources of toil.

        Args:
            days: Number of days to analyze
            limit: Maximum number of sources to return

        Returns:
            List of (category, minutes) tuples
        """
        try:
            # Filter entries
            cutoff = datetime.utcnow() - timedelta(days=days)
            toil_entries = [e for e in self._entries if e.timestamp >= cutoff and e.is_toil]

            # Group by category
            category_minutes: Dict[str, int] = {}
            for entry in toil_entries:
                category = entry.category.value
                category_minutes[category] = (
                    category_minutes.get(category, 0) + entry.duration_minutes
                )

            # Sort by minutes (descending)
            sorted_sources = sorted(
                category_minutes.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            return sorted_sources[:limit]

        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error getting top toil sources: {e}")
            return []

    def get_top_toil_tasks(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> List[Tuple[str, int]]:
        """
        Get top individual toil tasks.

        Args:
            days: Number of days to analyze
            limit: Maximum number of tasks to return

        Returns:
            List of (task, minutes) tuples
        """
        try:
            # Filter entries
            cutoff = datetime.utcnow() - timedelta(days=days)
            toil_entries = [e for e in self._entries if e.timestamp >= cutoff and e.is_toil]

            # Group by task pattern (similar tasks)
            task_minutes: Dict[str, int] = {}
            for entry in toil_entries:
                task = entry.task
                task_minutes[task] = task_minutes.get(task, 0) + entry.duration_minutes

            # Sort by minutes (descending)
            sorted_tasks = sorted(
                task_minutes.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            return sorted_tasks[:limit]

        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error getting top toil tasks: {e}")
            return []

    def generate_automation_opportunities(
        self,
        days: int = 30,
    ) -> List[AutomationOpportunity]:
        """
        Identify automation opportunities.

        Analyzes toil entries to identify common patterns that could be automated.

        Args:
            days: Number of days to analyze

        Returns:
            List of automation opportunities ranked by priority
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            toil_entries = [
                e for e in self._entries if e.timestamp >= cutoff and e.is_toil and e.assignable
            ]

            # Group by category and task pattern
            opportunities_dict: Dict[str, Dict[str, Any]] = {}

            for entry in toil_entries:
                key = f"{entry.category.value}:{entry.task}"

                if key not in opportunities_dict:
                    opportunities_dict[key] = {
                        "category": entry.category,
                        "task_pattern": entry.task,
                        "count": 0,
                        "total_minutes": 0,
                        "potential": entry.automation_potential,
                    }

                opportunities_dict[key]["count"] += 1
                opportunities_dict[key]["total_minutes"] += entry.duration_minutes

            # Convert to opportunities
            opportunities = []
            for data in opportunities_dict.values():
                count = data["count"]
                total_minutes = data["total_minutes"]
                avg_duration = total_minutes // count if count > 0 else 0

                # Calculate frequency (per month)
                frequency = int((count / days) * 30)

                # Estimate savings (80% of time if automated)
                savings_hours = (total_minutes * 0.8) / 60

                # Determine implementation effort
                potential = data["potential"]
                if potential == AutomationPotential.HIGH:
                    effort = "LOW"
                elif potential == AutomationPotential.MEDIUM:
                    effort = "MEDIUM"
                else:
                    effort = "HIGH"

                # Calculate priority (frequency * avg_duration * automation_potential)
                potential_score = {
                    AutomationPotential.HIGH: 3.0,
                    AutomationPotential.MEDIUM: 2.0,
                    AutomationPotential.LOW: 1.0,
                    AutomationPotential.NONE: 0.0,
                }
                priority = int(frequency * (avg_duration / 60) * potential_score[potential])
                priority = min(100, max(0, priority))

                opportunity = AutomationOpportunity(
                    category=data["category"],
                    task_pattern=data["task_pattern"],
                    frequency=frequency,
                    avg_duration_minutes=avg_duration,
                    total_toil_minutes=total_minutes,
                    automation_potential=potential,
                    estimated_savings_hours=savings_hours,
                    implementation_effort=effort,
                    priority=priority,
                )

                opportunities.append(opportunity)

            # Sort by priority (descending)
            opportunities.sort(key=lambda x: x.priority, reverse=True)

            return opportunities

        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error generating automation opportunities: {e}")
            return []

    def get_engineer_breakdown(
        self,
        days: int = 30,
    ) -> Dict[str, ToilMetrics]:
        """
        Get toil breakdown by engineer.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary mapping engineer name to their metrics
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = [e for e in self._entries if e.timestamp >= cutoff and e.engineer]

            # Group by engineer
            engineer_entries: Dict[str, List[ToilEntry]] = {}
            for entry in filtered:
                engineer = entry.engineer or "unknown"
                if engineer not in engineer_entries:
                    engineer_entries[engineer] = []
                engineer_entries[engineer].append(entry)

            # Calculate metrics for each engineer
            breakdown = {}
            for engineer, entries in engineer_entries.items():
                breakdown[engineer] = self._calculate_metrics(entries)

            return breakdown

        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error getting engineer breakdown: {e}")
            return {}

    def get_trend_data(
        self,
        days: int = 30,
        bucket_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Get historical trend data for toil.

        Args:
            days: Total days to analyze
            bucket_days: Size of each time bucket in days

        Returns:
            List of trend data points
        """
        try:
            trends = []
            cutoff = datetime.utcnow() - timedelta(days=days)

            # Create time buckets
            num_buckets = days // bucket_days
            for i in range(num_buckets):
                bucket_start = cutoff + timedelta(days=i * bucket_days)
                bucket_end = bucket_start + timedelta(days=bucket_days)

                # Filter entries in this bucket
                bucket_entries = [
                    e for e in self._entries if bucket_start <= e.timestamp < bucket_end
                ]

                if bucket_entries:
                    metrics = self._calculate_metrics(bucket_entries)
                    trends.append(
                        {
                            "period_start": bucket_start.isoformat(),
                            "period_end": bucket_end.isoformat(),
                            "metrics": metrics.to_dict(),
                        }
                    )

            return trends

        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error getting trend data: {e}")
            return []

    async def generate_report(
        self,
        days: int = 30,
    ) -> ToilReport:
        """
        Generate comprehensive toil report.

        Args:
            days: Number of days to analyze

        Returns:
            Comprehensive toil report
        """
        try:
            # Ensure we have recent data
            await self._load_recent_entries(days)

            # Calculate time window
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=days)

            # Filter entries
            filtered = [e for e in self._entries if e.timestamp >= period_start]

            # Calculate overall metrics
            metrics = self._calculate_metrics(filtered)

            # Get top toil sources
            top_sources = self.get_top_toil_sources(days, limit=10)

            # Generate automation opportunities
            automation_ops = self.generate_automation_opportunities(days)

            # Get engineer breakdown
            engineer_breakdown = self.get_engineer_breakdown(days)

            # Get trend data
            trend_data = self.get_trend_data(days)

            # Generate recommendations
            recommendations = self._generate_recommendations(metrics, top_sources, automation_ops)

            report = ToilReport(
                period_start=period_start,
                period_end=period_end,
                metrics=metrics,
                top_toil_sources=top_sources,
                automation_opportunities=automation_ops[:5],  # Top 5
                engineer_breakdown=engineer_breakdown,
                trend_data=trend_data,
                recommendations=recommendations,
            )

            self.logger.info(f"Generated toil report for {days} days")

            return report

        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error generating report: {e}")
            raise

    def _generate_recommendations(
        self,
        metrics: ToilMetrics,
        top_sources: List[Tuple[str, int]],
        automation_ops: List[AutomationOpportunity],
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        # Overall toil level
        if metrics.toil_percentage > self.config.toil_critical_threshold:
            recommendations.append(
                f"CRITICAL: Toil is at {metrics.toil_percentage:.1f}%, "
                f"well above the {self.config.toil_critical_threshold}% threshold. "
                f"Immediate action required to reduce manual work."
            )
        elif metrics.toil_percentage > self.config.toil_warning_threshold:
            recommendations.append(
                f"WARNING: Toil is at {metrics.toil_percentage:.1f}%, "
                f"above the {self.config.toil_warning_threshold}% target. "
                f"Focus on automating top toil sources."
            )
        else:
            recommendations.append(
                f"Good: Toil is at {metrics.toil_percentage:.1f}%, "
                f"within the target of <{self.config.toil_warning_threshold}%."
            )

        # Top toil sources
        if top_sources:
            top_category, top_minutes = top_sources[0]
            recommendations.append(
                f"Top toil source: {top_category} ({top_minutes} minutes). "
                f"Focus automation efforts here."
            )

        # Automation coverage
        if metrics.automation_coverage < self.config.automation_target_coverage:
            recommendations.append(
                f"Automation coverage is {metrics.automation_coverage:.1f}%, "
                f"below the target of {self.config.automation_target_coverage}%. "
                f"Invest in automation for high-frequency tasks."
            )

        # Top automation opportunities
        if automation_ops:
            top_opp = automation_ops[0]
            recommendations.append(
                f"Highest priority automation: {top_opp.task_pattern} "
                f"(could save ~{top_opp.estimated_savings_hours:.1f} hours/month)"
            )

        return recommendations

    def export_to_json(
        self,
        days: int = 30,
        filepath: Optional[str] = None,
    ) -> str:
        """
        Export toil data to JSON.

        Args:
            days: Number of days to export
            filepath: Optional filepath to save to

        Returns:
            JSON string
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = [e for e in self._entries if e.timestamp >= cutoff]

            data = {
                "service_name": self.service_name,
                "period_days": days,
                "entries": [e.to_dict() for e in filtered],
                "metrics": self._calculate_metrics(filtered).to_dict(),
                "top_sources": self.get_top_toil_sources(days),
                "automation_opportunities": [
                    opp.to_dict() for opp in self.generate_automation_opportunities(days)
                ],
                "exported_at": datetime.utcnow().isoformat(),
            }

            json_str = json.dumps(data, indent=2)

            if filepath:
                Path(filepath).parent.mkdir(parents=True, exist_ok=True)
                Path(filepath).write_text(json_str)
                self.logger.info(f"Exported toil data to {filepath}")

            return json_str

        except (ValueError, OSError, json.JSONEncodeError) as e:
            self.logger.error(f"Error exporting to JSON: {e}")
            raise


# Singleton instances
_trackers: Dict[str, ToilTracker] = {}


def get_toil_tracker(
    service_name: str,
    config: Optional[ToilConfig] = None,
) -> ToilTracker:
    """
    Get or create singleton toil tracker for service.

    Args:
        service_name: Name of the service
        config: Optional configuration

    Returns:
        ToilTracker instance
    """
    if service_name not in _trackers:
        _trackers[service_name] = ToilTracker(service_name, config)
        logger.info(f"Created ToilTracker for {service_name}")
    return _trackers[service_name]
