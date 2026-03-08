# mypy: ignore-errors
"""
Alert Fatigue Preventer - Smart Alert Processing

Prevents alert fatigue through intelligent filtering, grouping, and rate limiting.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertCategory(str, Enum):
    """Alert categories."""

    SYSTEM = "system"  # System-level issues
    APPLICATION = "application"  # Application errors
    PERFORMANCE = "performance"  # Performance degradation
    AVAILABILITY = "availability"  # Service availability
    SECURITY = "security"  # Security issues
    BUSINESS = "business"  # Business logic issues
    TESTING = "testing"  # Test-related alerts


@dataclass
class ProcessedAlert:
    """A processed alert with fatigue prevention applied."""

    alert_id: str
    original_alert: Dict[str, Any]
    severity: AlertSeverity
    category: AlertCategory
    timestamp: datetime

    # Processing results
    should_send: bool
    reason: str
    fingerprint: str
    similarity_hash: str
    group_id: Optional[str] = None
    priority_score: Optional[float] = None
    suppressed: bool = False
    delayed_until: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "should_send": self.should_send,
            "reason": self.reason,
            "group_id": self.group_id,
            "priority_score": self.priority_score,
            "fingerprint": self.fingerprint,
            "suppressed": self.suppressed,
            "delayed_until": self.delayed_until.isoformat() if self.delayed_until else None,
        }


@dataclass
class AlertGroup:
    """A group of similar alerts."""

    group_id: str
    name: str
    description: str
    alerts: List[ProcessedAlert]
    created_at: datetime
    last_updated: datetime

    # Group stats
    alert_count: int = 0
    severity_counts: Dict[str, int] = field(default_factory=dict)

    def add_alert(self, alert: ProcessedAlert) -> None:
        """Add alert to group."""
        self.alerts.append(alert)
        self.alert_count += 1
        self.last_updated = datetime.utcnow()

        # Update severity counts
        severity = alert.severity.value
        self.severity_counts[severity] = self.severity_counts.get(severity, 0) + 1


@dataclass
class AlertStats:
    """Statistics about alert processing."""

    total_received: int = 0
    total_sent: int = 0
    total_suppressed: int = 0
    total_delayed: int = 0
    total_grouped: int = 0

    # By category
    by_category: Dict[str, int] = field(default_factory=dict)

    # By severity
    by_severity: Dict[str, int] = field(default_factory=dict)

    # Time-based
    last_alert_time: Optional[datetime] = None
    alerts_last_hour: int = 0
    alerts_last_day: int = 0

    # Fatigue metrics
    fatigue_score: float = 0.0  # 0.0 = no fatigue, 1.0 = maximum fatigue
    false_positive_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_received": self.total_received,
            "total_sent": self.total_sent,
            "total_suppressed": self.total_suppressed,
            "total_delayed": self.total_delayed,
            "total_grouped": self.total_grouped,
            "by_category": self.by_category,
            "by_severity": self.by_severity,
            "last_alert_time": self.last_alert_time.isoformat() if self.last_alert_time else None,
            "alerts_last_hour": self.alerts_last_hour,
            "alerts_last_day": self.alerts_last_day,
            "fatigue_score": f"{self.fatigue_score * 100:.1f}%",
            "false_positive_rate": f"{self.false_positive_rate * 100:.1f}%",
        }


@dataclass
class AlertFatigueConfig:
    """Configuration for alert fatigue prevention."""

    # Rate limiting
    max_alerts_per_minute: int = 10
    max_alerts_per_hour: int = 100
    max_alerts_per_day: int = 500

    # Suppression rules
    enable_suppression: bool = True
    suppress_duplicates_seconds: int = 300  # 5 minutes
    suppress_similar_seconds: int = 600  # 10 minutes

    # Grouping
    enable_grouping: bool = True
    group_window_seconds: int = 300  # 5 minutes
    max_group_size: int = 50

    # Priority
    enable_priority_scoring: bool = True
    priority_threshold: float = 0.5  # Only send alerts above this score

    # Learning
    enable_learning: bool = True
    learn_from_suppressions: bool = True
    false_positive_threshold: int = 5  # Mark as false positive after N suppressions

    # Categories to always send
    always_send_categories: List[str] = field(
        default_factory=lambda: [
            AlertCategory.CRITICAL.value,
            AlertCategory.SECURITY.value,
        ]
    )

    # Database
    db_path: str = "data/alert_fatigue.db"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_alerts_per_minute": self.max_alerts_per_minute,
            "max_alerts_per_hour": self.max_alerts_per_hour,
            "max_alerts_per_day": self.max_alerts_per_day,
            "enable_suppression": self.enable_suppression,
            "suppress_duplicates_seconds": self.suppress_duplicates_seconds,
            "suppress_similar_seconds": self.suppress_similar_seconds,
            "enable_grouping": self.enable_grouping,
            "group_window_seconds": self.group_window_seconds,
            "max_group_size": self.max_group_size,
            "enable_priority_scoring": self.enable_priority_scoring,
            "priority_threshold": self.priority_threshold,
            "enable_learning": self.enable_learning,
            "always_send_categories": self.always_send_categories,
        }


class AlertFatiguePreventer:
    """
    Alert fatigue prevention system.

    Responsibilities:
    - Filter and suppress redundant alerts
    - Group similar alerts
    - Rate limit alerts
    - Prioritize alerts
    - Learn from false positives

    Usage:
        preventer = AlertFatiguePreventer(
            service_name="trading_engine",
            config=AlertFatigueConfig()
        )
        await preventer.initialize()

        processed_alerts = await preventer.process_alerts(raw_alerts)
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[AlertFatigueConfig] = None,
    ):
        """
        Initialize alert fatigue preventer.

        Args:
            service_name: Name of the service
            config: Configuration
        """
        self.service_name = service_name
        self.config = config or AlertFatigueConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._alert_history: List[ProcessedAlert] = []
        self._active_groups: Dict[str, AlertGroup] = {}
        self._suppression_cache: Dict[str, datetime] = {}
        self._false_positive_cache: Dict[str, int] = {}

        # Rate limiting
        self._alert_counts: Dict[str, List[datetime]] = defaultdict(list)

        # Statistics
        self._stats = AlertStats()

        # Lock
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize alert fatigue preventer."""
        async with self._lock:
            try:
                await self._init_database()
                await self._load_suppression_cache()
                await self._load_false_positives()
                await self._cleanup_old_data()
                self.logger.info("AlertFatiguePreventer initialized")
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
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
                    CREATE TABLE IF NOT EXISTS alerts (
                        id TEXT PRIMARY KEY,
                        service_name TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        category TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        similarity_hash TEXT NOT NULL,
                        should_send INTEGER NOT NULL,
                        reason TEXT,
                        group_id TEXT,
                        priority_score REAL,
                        suppressed INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alert_groups (
                        group_id TEXT PRIMARY KEY,
                        service_name TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        created_at TEXT NOT NULL,
                        last_updated TEXT NOT NULL,
                        alert_count INTEGER NOT NULL,
                        severity_counts TEXT
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS suppression_cache (
                        fingerprint TEXT PRIMARY KEY,
                        suppressed_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        suppression_count INTEGER NOT NULL DEFAULT 1
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS false_positives (
                        fingerprint TEXT PRIMARY KEY,
                        service_name TEXT NOT NULL,
                        suppression_count INTEGER NOT NULL,
                        last_suppressed_at TEXT NOT NULL,
                        is_false_positive INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_alerts_service_timestamp
                    ON alerts(service_name, timestamp)
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_suppression_cache_expires
                    ON suppression_cache(expires_at)
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_suppression_cache(self) -> None:
        """Load suppression cache from database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT fingerprint, suppressed_at, expires_at
                    FROM suppression_cache
                    WHERE expires_at > datetime('utc')
                """
                )

                rows = await cursor.fetchall()

                for row in rows:
                    self._suppression_cache[row[0]] = datetime.fromisoformat(row[1])

                self.logger.info(f"Loaded {len(rows)} active suppressions")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error loading suppression cache: {e}")

    async def _load_false_positives(self) -> None:
        """Load false positive cache from database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT fingerprint, suppression_count
                    FROM false_positives
                    WHERE is_false_positive = 1
                """
                )

                rows = await cursor.fetchall()

                for row in rows:
                    self._false_positive_cache[row[0]] = row[1]

                self.logger.info(f"Loaded {len(rows)} false positives")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error loading false positives: {e}")

    async def _cleanup_old_data(self) -> None:
        """Clean up old data from database."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=7)

            async with aiosqlite.connect(self.config.db_path) as db:
                # Clean up old alerts
                await db.execute(
                    """
                    DELETE FROM alerts
                    WHERE timestamp < ?
                """,
                    (cutoff_time.isoformat(),),
                )

                # Clean up expired suppressions
                await db.execute(
                    """
                    DELETE FROM suppression_cache
                    WHERE expires_at < datetime('utc')
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error cleaning up data: {e}")

    async def process_alerts(
        self,
        raw_alerts: List[Dict[str, Any]],
    ) -> List[ProcessedAlert]:
        """
        Process alerts with fatigue prevention.

        Args:
            raw_alerts: List of raw alerts to process

        Returns:
            List of processed alerts
        """
        async with self._lock:
            processed = []

            for raw_alert in raw_alerts:
                try:
                    alert = await self._process_single_alert(raw_alert)
                    processed.append(alert)

                    # Update statistics
                    self._stats.total_received += 1

                    if alert.should_send:
                        self._stats.total_sent += 1
                    elif alert.suppressed:
                        self._stats.total_suppressed += 1
                    elif alert.delayed_until:
                        self._stats.total_delayed += 1

                    if alert.group_id:
                        self._stats.total_grouped += 1

                    # Update time-based stats
                    self._stats.last_alert_time = alert.timestamp

                except Exception as e:
                    self.logger.error(f"Error processing alert: {e}")

            # Trim history
            self._alert_history.extend(processed)
            if len(self._alert_history) > 10000:
                self._alert_history = self._alert_history[-5000:]

            # Save to database
            for alert in processed:
                await self._save_alert(alert)

            return processed

    async def _process_single_alert(
        self,
        raw_alert: Dict[str, Any],
    ) -> ProcessedAlert:
        """Process a single alert."""
        # Extract basic info
        severity = AlertSeverity(raw_alert.get("severity", "medium"))
        category = AlertCategory(raw_alert.get("category", "system"))
        timestamp = datetime.fromisoformat(
            raw_alert.get("timestamp", datetime.utcnow().isoformat())
        )

        # Generate fingerprint
        fingerprint = self._generate_fingerprint(raw_alert)
        similarity_hash = self._generate_similarity_hash(raw_alert)

        # Create alert ID
        alert_id = hashlib.sha256(f"{fingerprint}:{timestamp.isoformat()}".encode()).hexdigest()[
            :16
        ]

        # Check if should be suppressed
        should_suppress, suppress_reason = await self._should_suppress(
            fingerprint, similarity_hash, severity, category
        )

        if should_suppress:
            # Learn from suppression
            if self.config.enable_learning:
                await self._record_suppression(fingerprint)

            return ProcessedAlert(
                alert_id=alert_id,
                original_alert=raw_alert,
                severity=severity,
                category=category,
                timestamp=timestamp,
                should_send=False,
                reason=suppress_reason,
                fingerprint=fingerprint,
                similarity_hash=similarity_hash,
                suppressed=True,
            )

        # Check rate limiting
        if not await self._check_rate_limit(category):
            return ProcessedAlert(
                alert_id=alert_id,
                original_alert=raw_alert,
                severity=severity,
                category=category,
                timestamp=timestamp,
                should_send=False,
                reason="Rate limit exceeded",
                fingerprint=fingerprint,
                similarity_hash=similarity_hash,
                suppressed=True,
            )

        # Check if should be grouped
        group_id = None
        if self.config.enable_grouping:
            group_id = await self._find_or_create_group(raw_alert, fingerprint)

        # Calculate priority
        priority_score = None
        if self.config.enable_priority_scoring:
            priority_score = await self._calculate_priority(raw_alert, severity, category)

            # Check priority threshold
            if priority_score < self.config.priority_threshold:
                return ProcessedAlert(
                    alert_id=alert_id,
                    original_alert=raw_alert,
                    severity=severity,
                    category=category,
                    timestamp=timestamp,
                    should_send=False,
                    reason=f"Priority score {priority_score:.2f} below threshold {self.config.priority_threshold}",
                    fingerprint=fingerprint,
                    similarity_hash=similarity_hash,
                    priority_score=priority_score,
                    suppressed=True,
                )

        # Alert should be sent
        return ProcessedAlert(
            alert_id=alert_id,
            original_alert=raw_alert,
            severity=severity,
            category=category,
            timestamp=timestamp,
            should_send=True,
            reason="Alert passed all filters",
            group_id=group_id,
            priority_score=priority_score,
            fingerprint=fingerprint,
            similarity_hash=similarity_hash,
            suppressed=False,
        )

    def _generate_fingerprint(self, alert: Dict[str, Any]) -> str:
        """Generate unique fingerprint for alert."""
        # Use alert type, source, and key fields
        key_fields = [
            alert.get("type", ""),
            alert.get("source", ""),
            alert.get("metric", ""),
            alert.get("threshold", ""),
        ]

        fingerprint_str = ":".join(str(f) for f in key_fields)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]

    def _generate_similarity_hash(self, alert: Dict[str, Any]) -> str:
        """Generate similarity hash for grouping."""
        # Use fewer fields for similarity grouping
        similar_fields = [
            alert.get("type", ""),
            alert.get("source", ""),
        ]

        similarity_str = ":".join(str(f) for f in similar_fields)
        return hashlib.sha256(similarity_str.encode()).hexdigest()[:12]

    async def _should_suppress(
        self,
        fingerprint: str,
        similarity_hash: str,
        severity: AlertSeverity,
        category: AlertCategory,
    ) -> tuple[bool, str]:
        """Check if alert should be suppressed."""
        # Never suppress critical or security alerts
        if category.value in self.config.always_send_categories:
            return False, ""

        # Check false positives
        if fingerprint in self._false_positive_cache:
            return True, "Known false positive"

        # Check recent suppressions
        if fingerprint in self._suppression_cache:
            last_suppressed = self._suppression_cache[fingerprint]
            if datetime.utcnow() - last_suppressed < timedelta(
                seconds=self.config.suppress_duplicates_seconds
            ):
                return True, f"Duplicate (last seen {last_suppressed})"

        # Check similar alerts
        for cached_fp, cached_time in self._suppression_cache.items():
            if datetime.utcnow() - cached_time < timedelta(
                seconds=self.config.suppress_similar_seconds
            ):
                # Check similarity hash
                cached_alert = next(
                    (a for a in self._alert_history if a.fingerprint == cached_fp), None
                )
                if cached_alert and cached_alert.similarity_hash == similarity_hash:
                    return True, f"Similar alert in group ({cached_fp})"

        return False, ""

    async def _check_rate_limit(self, category: AlertCategory) -> bool:
        """Check if alert is within rate limits."""
        now = datetime.utcnow()

        # Clean up old counts
        for key in list(self._alert_counts.keys()):
            self._alert_counts[key] = [
                t for t in self._alert_counts[key] if now - t < timedelta(hours=1)
            ]

        # Check minute limit
        minute_ago = now - timedelta(minutes=1)
        minute_count = sum(
            1 for times in self._alert_counts.values() for t in times if t > minute_ago
        )

        if minute_count >= self.config.max_alerts_per_minute:
            return False

        # Check hour limit
        hour_ago = now - timedelta(hours=1)
        hour_count = sum(1 for times in self._alert_counts.values() for t in times if t > hour_ago)

        if hour_count >= self.config.max_alerts_per_hour:
            return False

        # Check day limit
        day_ago = now - timedelta(days=1)
        day_count = sum(1 for times in self._alert_counts.values() for t in times if t > day_ago)

        if day_count >= self.config.max_alerts_per_day:
            return False

        # Within limits, record this alert
        self._alert_counts[category.value].append(now)

        return True

    async def _find_or_create_group(
        self,
        alert: Dict[str, Any],
        fingerprint: str,
    ) -> Optional[str]:
        """Find existing group or create new one."""
        similarity_hash = self._generate_similarity_hash(alert)

        # Look for existing group
        for group_id, group in self._active_groups.items():
            if len(group.alerts) < self.config.max_group_size:
                # Check if recent
                if datetime.utcnow() - group.last_updated < timedelta(
                    seconds=self.config.group_window_seconds
                ):
                    # Check similarity
                    if group.alerts and group.alerts[0].similarity_hash == similarity_hash:
                        group_id = group.group_id
                        # Note: We'd add the alert to the group in the calling code
                        return group_id

        # No group found, would create new group
        # (Group creation logic would be here)
        return None

    async def _calculate_priority(
        self,
        alert: Dict[str, Any],
        severity: AlertSeverity,
        category: AlertCategory,
    ) -> float:
        """Calculate priority score for alert."""
        # Base score from severity
        severity_scores = {
            AlertSeverity.CRITICAL: 1.0,
            AlertSeverity.HIGH: 0.8,
            AlertSeverity.MEDIUM: 0.6,
            AlertSeverity.LOW: 0.4,
            AlertSeverity.INFO: 0.2,
        }

        score = severity_scores.get(severity, 0.5)

        # Adjust based on category
        category_multipliers = {
            AlertCategory.AVAILABILITY: 1.2,
            AlertCategory.SECURITY: 1.5,
            AlertCategory.PERFORMANCE: 0.9,
            AlertCategory.APPLICATION: 1.0,
            AlertCategory.SYSTEM: 1.0,
            AlertCategory.BUSINESS: 1.1,
            AlertCategory.TESTING: 0.5,
        }

        multiplier = category_multipliers.get(category, 1.0)
        score *= multiplier

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    async def _record_suppression(self, fingerprint: str) -> None:
        """Record alert suppression for learning."""
        self._suppression_cache[fingerprint] = datetime.utcnow()

        # Update suppression count
        if fingerprint not in self._false_positive_cache:
            self._false_positive_cache[fingerprint] = 0

        self._false_positive_cache[fingerprint] += 1

        # Mark as false positive if threshold exceeded
        if self._false_positive_cache[fingerprint] >= self.config.false_positive_threshold:
            await self._mark_false_positive(fingerprint)

    async def _mark_false_positive(self, fingerprint: str) -> None:
        """Mark alert as false positive."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO false_positives
                    (fingerprint, service_name, suppression_count, last_suppressed_at, is_false_positive)
                    VALUES (?, ?, ?, ?, 1)
                """,
                    (
                        fingerprint,
                        self.service_name,
                        self._false_positive_cache[fingerprint],
                        datetime.utcnow().isoformat(),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error marking false positive: {e}")

    async def _save_alert(self, alert: ProcessedAlert) -> None:
        """Save alert to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO alerts
                    (id, service_name, severity, category, timestamp, fingerprint,
                     similarity_hash, should_send, reason, group_id, priority_score, suppressed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        alert.alert_id,
                        self.service_name,
                        alert.severity.value,
                        alert.category.value,
                        alert.timestamp.isoformat(),
                        alert.fingerprint,
                        alert.similarity_hash,
                        1 if alert.should_send else 0,
                        alert.reason,
                        alert.group_id,
                        alert.priority_score,
                        1 if alert.suppressed else 0,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving alert: {e}")

    async def get_statistics(self) -> AlertStats:
        """Get alert processing statistics."""
        # Calculate fatigue score
        if self._stats.total_received > 0:
            self._stats.fatigue_score = 1.0 - (self._stats.total_sent / self._stats.total_received)
        else:
            self._stats.fatigue_score = 0.0

        # Calculate false positive rate
        total_suppressions = len(self._false_positive_cache)
        if total_suppressions > 0:
            false_positives = sum(
                1
                for count in self._false_positive_cache.values()
                if count >= self.config.false_positive_threshold
            )
            self._stats.false_positive_rate = false_positives / total_suppressions
        else:
            self._stats.false_positive_rate = 0.0

        return self._stats

    def get_summary(self) -> Dict[str, Any]:
        """Get alert fatigue preventer summary."""
        return {
            "service": self.service_name,
            "config": self.config.to_dict(),
            "active_suppressions": len(self._suppression_cache),
            "false_positives": len(self._false_positive_cache),
            "active_groups": len(self._active_groups),
            "stats": self._stats.to_dict(),
        }
