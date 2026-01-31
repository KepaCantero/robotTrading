"""
SLO/SLI Tracker - Service Level Objective Monitoring (SRE Rule 20)

Monitors Service Level Objectives (SLOs) and Service Level Indicators (SLIs).
Tracks compliance, detects violations, and generates compliance reports.

Key Concepts:
- SLO: Service Level Objective (target, e.g., 99.5% availability)
- SLI: Service Level Indicator (metric, e.g., request latency, error rate)
- SLO Compliance: Measurement of actual vs target performance
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class SLIMetricType(str, Enum):
    """Types of SLI metrics."""

    AVAILABILITY = "availability"  # Uptime percentage
    LATENCY = "latency"  # Response time
    ERROR_RATE = "error_rate"  # Error percentage
    THROUGHPUT = "throughput"  # Requests per second
    SATISFACTION = "satisfaction"  # User satisfaction


class SLOComplianceStatus(str, Enum):
    """SLO compliance status."""

    COMPLIANT = "compliant"  # Meeting SLO target
    VIOLATION = "violation"  # Below SLO target
    AT_RISK = "at_risk"  # Risk of violation (trending down)
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough data


@dataclass
class SLIMetric:
    """
    Service Level Indicator measurement.

    Represents a single measurement of a service metric.
    """

    name: str
    value: Decimal
    timestamp: datetime
    metric_type: SLIMetricType
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": str(self.value),
            "timestamp": self.timestamp.isoformat(),
            "type": self.metric_type.value,
            "metadata": self.metadata,
        }


@dataclass
class SLOConfig:
    """
    Service Level Objective configuration.

    Defines target performance goals for a service.
    """

    name: str
    slo_target: Decimal  # e.g., 0.995 for 99.5%
    metric_type: SLIMetricType
    measurement_window_minutes: int  # Rolling window for SLO calculation
    description: str = ""

    # Alert thresholds
    warning_threshold_pct: Decimal = Decimal("95")  # 95% of target
    violation_threshold_pct: Decimal = Decimal("100")  # 100% = SLO target

    # Minimum samples required for valid measurement
    min_samples: int = 10

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "target": f"{self.slo_target * 100}%",
            "type": self.metric_type.value,
            "window_minutes": self.measurement_window_minutes,
            "description": self.description,
            "warning_threshold": f"{self.warning_threshold_pct}%",
            "violation_threshold": f"{self.violation_threshold_pct}%",
            "min_samples": self.min_samples,
        }


@dataclass
class SLOViolation:
    """Record of an SLO violation."""

    slo_name: str
    violation_start: datetime
    violation_end: Optional[datetime]
    actual_value: Decimal
    target_value: Decimal
    severity: str  # "warning" or "critical"
    resolved: bool = False

    def duration_minutes(self) -> Optional[int]:
        """Calculate violation duration."""
        if self.violation_end:
            return int((self.violation_end - self.violation_start).total_seconds() / 60)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slo_name": self.slo_name,
            "start": self.violation_start.isoformat(),
            "end": self.violation_end.isoformat() if self.violation_end else None,
            "duration_minutes": self.duration_minutes(),
            "actual_value": str(self.actual_value),
            "target_value": str(self.target_value),
            "severity": self.severity,
            "resolved": self.resolved,
        }


@dataclass
class SLOComplianceReport:
    """
    SLO compliance report for a time period.

    Provides comprehensive SLO performance analysis.
    """

    slo_name: str
    period_start: datetime
    period_end: datetime
    target_slo: Decimal
    actual_slo: Decimal
    status: SLOComplianceStatus
    total_measurements: int
    valid_measurements: int
    violations: List[SLOViolation]
    calculated_at: datetime

    @property
    def compliance_percentage(self) -> Decimal:
        """Calculate compliance as percentage of target."""
        if self.target_slo == 0:
            return Decimal("0")
        return (self.actual_slo / self.target_slo) * Decimal("100")

    @property
    def violation_count(self) -> int:
        """Get number of violations."""
        return len(self.violations)

    @property
    def total_violation_minutes(self) -> int:
        """Get total minutes in violation state."""
        return sum(v.duration_minutes() or 0 for v in self.violations if v.duration_minutes())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slo_name": self.slo_name,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "target_slo": f"{self.target_slo * 100}%",
            "actual_slo": f"{self.actual_slo * 100}%",
            "compliance_pct": f"{self.compliance_percentage:.2f}%",
            "status": self.status.value,
            "measurements": {
                "total": self.total_measurements,
                "valid": self.valid_measurements,
                "invalid": self.total_measurements - self.valid_measurements,
            },
            "violations": {
                "count": self.violation_count,
                "total_minutes": self.total_violation_minutes,
                "details": [v.to_dict() for v in self.violations[-10:]],  # Last 10
            },
            "calculated_at": self.calculated_at.isoformat(),
        }


class SLOTracker:
    """
    SLO/SLI monitoring and compliance tracking.

    Responsibilities:
    - Track SLI metrics over time
    - Calculate SLO compliance in rolling windows
    - Detect SLO violations
    - Generate compliance reports
    - Persist SLO data

    Integration:
    - Connects to health check endpoints
    - Monitors application metrics
    - Feeds into error budget calculations
    """

    def __init__(
        self,
        service_name: str,
        db_path: str = "data/slo_metrics.db",
    ):
        """
        Initialize SLO tracker.

        Args:
            service_name: Name of the service being monitored
            db_path: Path to metrics database
        """
        self.service_name = service_name
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # SLO configurations
        self._slo_configs: Dict[str, SLOConfig] = {}

        # Active violations
        self._active_violations: Dict[str, SLOViolation] = {}

        # Metric buffer (in-memory cache)
        self._metric_buffer: Dict[str, List[SLIMetric]] = defaultdict(list)

        # Callbacks
        self._on_violation: Optional[Callable[[SLOViolation], None]] = None
        self._on_violation_resolved: Optional[Callable[[SLOViolation], None]] = None

        # Lock
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize SLO tracker."""
        async with self._lock:
            try:
                await self._init_database()
                await self._load_active_violations()
                await self._register_default_slos()
                self.logger.info("SLOTracker initialized")
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            from pathlib import Path

            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS slo_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        metadata TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS slo_configs (
                        service_name TEXT NOT NULL,
                        slo_name TEXT NOT NULL,
                        slo_target TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        window_minutes INTEGER NOT NULL,
                        description TEXT,
                        warning_threshold TEXT,
                        violation_threshold TEXT,
                        min_samples INTEGER,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc')),
                        UNIQUE(service_name, slo_name)
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS slo_violations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        slo_name TEXT NOT NULL,
                        violation_start TEXT NOT NULL,
                        violation_end TEXT,
                        actual_value TEXT NOT NULL,
                        target_value TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        resolved INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_metrics_service_timestamp
                    ON slo_metrics(service_name, timestamp)
                    """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_violations_service_active
                    ON slo_violations(service_name, resolved)
                    """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_active_violations(self) -> None:
        """Load active violations from database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT slo_name, violation_start, actual_value, target_value, severity
                    FROM slo_violations
                    WHERE service_name = ? AND resolved = 0
                    """,
                    (self.service_name,),
                )

                rows = await cursor.fetchall()
                for row in rows:
                    violation = SLOViolation(
                        slo_name=row[0],
                        violation_start=datetime.fromisoformat(row[1]),
                        violation_end=None,
                        actual_value=Decimal(row[2]),
                        target_value=Decimal(row[3]),
                        severity=row[4],
                    )
                    self._active_violations[row[0]] = violation

                self.logger.info(f"Loaded {len(self._active_violations)} active violations")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error loading violations: {e}")

    async def _register_default_slos(self) -> None:
        """Register default SLOs for trading system."""
        default_slos = [
            SLOConfig(
                name="availability",
                slo_target=Decimal("0.995"),  # 99.5%
                metric_type=SLIMetricType.AVAILABILITY,
                measurement_window_minutes=30,
                description="Service availability (uptime)",
                min_samples=5,
            ),
            SLOConfig(
                name="api_latency",
                slo_target=Decimal("0.95"),  # 95% of requests under 1s
                metric_type=SLIMetricType.LATENCY,
                measurement_window_minutes=5,
                description="API request latency < 1 second",
                min_samples=10,
            ),
            SLOConfig(
                name="error_rate",
                slo_target=Decimal("0.99"),  # 99% success rate
                metric_type=SLIMetricType.ERROR_RATE,
                measurement_window_minutes=10,
                description="API error rate < 1%",
                min_samples=20,
            ),
        ]

        for slo in default_slos:
            await self.register_slo(slo)

        self.logger.info(f"Registered {len(default_slos)} default SLOs")

    async def register_slo(self, config: SLOConfig) -> None:
        """
        Register an SLO configuration.

        Args:
            config: SLO configuration
        """
        try:
            self._slo_configs[config.name] = config

            # Persist to database
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO slo_configs (
                        service_name, slo_name, slo_target, metric_type,
                        window_minutes, description, warning_threshold,
                        violation_threshold, min_samples
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.service_name,
                        config.name,
                        str(config.slo_target),
                        config.metric_type.value,
                        config.measurement_window_minutes,
                        config.description,
                        str(config.warning_threshold_pct),
                        str(config.violation_threshold_pct),
                        config.min_samples,
                    ),
                )
                await db.commit()

            self.logger.info(f"Registered SLO: {config.name}")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error registering SLO: {e}")

    async def record_metric(self, metric: SLIMetric) -> None:
        """
        Record an SLI metric measurement.

        Args:
            metric: SLI metric to record
        """
        async with self._lock:
            try:
                # Add to buffer
                self._metric_buffer[metric.name].append(metric)

                # Persist to database
                await self._save_metric(metric)

                # Check for SLO violations
                await self._check_slo_violations(metric.name)

                # Trim buffer
                if len(self._metric_buffer[metric.name]) > 1000:
                    self._metric_buffer[metric.name] = self._metric_buffer[metric.name][-500:]

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error recording metric: {e}")

    async def _save_metric(self, metric: SLIMetric) -> None:
        """Save metric to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO slo_metrics (
                        service_name, metric_name, metric_value, metric_type,
                        timestamp, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.service_name,
                        metric.name,
                        str(metric.value),
                        metric.metric_type.value,
                        metric.timestamp.isoformat(),
                        str(metric.metadata),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving metric: {e}")

    async def _check_slo_violations(self, metric_name: str) -> None:
        """Check for SLO violations based on recent metrics."""
        if metric_name not in self._slo_configs:
            return

        config = self._slo_configs[metric_name]
        metrics = self._metric_buffer[metric_name]

        if len(metrics) < config.min_samples:
            return

        # Calculate compliance over measurement window
        cutoff = datetime.utcnow() - timedelta(minutes=config.measurement_window_minutes)
        window_metrics = [m for m in metrics if m.timestamp >= cutoff]

        if len(window_metrics) < config.min_samples:
            return

        # Calculate actual SLO value
        actual_value = await self._calculate_slo_value(config, window_metrics)

        # Check for violations
        violation_threshold = config.slo_target
        warning_threshold = config.slo_target * (config.warning_threshold_pct / Decimal("100"))

        if actual_value < violation_threshold:
            # Critical violation
            await self._handle_violation(
                metric_name,
                actual_value,
                violation_threshold,
                "critical",
            )
        elif actual_value < warning_threshold:
            # Warning violation
            await self._handle_violation(
                metric_name,
                actual_value,
                warning_threshold,
                "warning",
            )
        else:
            # Check if we should resolve an existing violation
            if metric_name in self._active_violations:
                await self._resolve_violation(metric_name, actual_value)

    async def _calculate_slo_value(
        self,
        config: SLOConfig,
        metrics: List[SLIMetric],
    ) -> Decimal:
        """Calculate SLO value from metrics."""
        if config.metric_type == SLIMetricType.AVAILABILITY:
            # Percentage of successful measurements
            successful = sum(1 for m in metrics if m.value > Decimal("0"))
            return Decimal(successful) / Decimal(len(metrics))

        elif config.metric_type == SLIMetricType.LATENCY:
            # Percentage under threshold (assume value is 0 or 1 for pass/fail)
            successful = sum(1 for m in metrics if m.value < Decimal("1000"))  # < 1s
            return Decimal(successful) / Decimal(len(metrics))

        elif config.metric_type == SLIMetricType.ERROR_RATE:
            # Success rate (inverse of error rate)
            avg_value = sum(m.value for m in metrics) / Decimal(len(metrics))
            return Decimal("1") - avg_value

        elif config.metric_type == SLIMetricType.THROUGHPUT:
            # Average throughput relative to target
            avg_value = sum(m.value for m in metrics) / Decimal(len(metrics))
            return avg_value

        else:
            # Default: average of values
            return sum(m.value for m in metrics) / Decimal(len(metrics))

    async def _handle_violation(
        self,
        slo_name: str,
        actual_value: Decimal,
        target_value: Decimal,
        severity: str,
    ) -> None:
        """Handle SLO violation."""
        if slo_name in self._active_violations:
            # Already in violation, update existing
            self._active_violations[slo_name].actual_value = actual_value
            return

        # Create new violation
        violation = SLOViolation(
            slo_name=slo_name,
            violation_start=datetime.utcnow(),
            violation_end=None,
            actual_value=actual_value,
            target_value=target_value,
            severity=severity,
        )

        self._active_violations[slo_name] = violation

        # Persist to database
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO slo_violations (
                        service_name, slo_name, violation_start, actual_value,
                        target_value, severity, resolved
                    ) VALUES (?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        self.service_name,
                        slo_name,
                        violation.violation_start.isoformat(),
                        str(actual_value),
                        str(target_value),
                        severity,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving violation: {e}")

        # Trigger callback
        if self._on_violation:
            try:
                self._on_violation(violation)
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error in violation callback: {e}")

        self.logger.error(
            f"SLO VIOLATION: {slo_name} "
            f"(actual: {actual_value:.4f} < target: {target_value:.4f}, severity: {severity})"
        )

    async def _resolve_violation(self, slo_name: str, actual_value: Decimal) -> None:
        """Resolve SLO violation."""
        if slo_name not in self._active_violations:
            return

        violation = self._active_violations[slo_name]
        violation.violation_end = datetime.utcnow()
        violation.resolved = True

        # Update database
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE slo_violations
                    SET violation_end = ?, resolved = 1
                    WHERE service_name = ? AND slo_name = ? AND resolved = 0
                    """,
                    (
                        violation.violation_end.isoformat(),
                        self.service_name,
                        slo_name,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error resolving violation: {e}")

        # Remove from active
        del self._active_violations[slo_name]

        # Trigger callback
        if self._on_violation_resolved:
            try:
                self._on_violation_resolved(violation)
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error in resolve callback: {e}")

        self.logger.info(
            f"SLO violation resolved: {slo_name} " f"(duration: {violation.duration_minutes()}min)"
        )

    async def generate_compliance_report(
        self,
        slo_name: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> List[SLOComplianceReport]:
        """
        Generate SLO compliance report.

        Args:
            slo_name: Specific SLO to report (None = all)
            period_start: Report period start (None = last 24h)
            period_end: Report period end (None = now)

        Returns:
            List of compliance reports
        """
        try:
            # Default to last 24 hours
            if period_start is None:
                period_start = datetime.utcnow() - timedelta(hours=24)
            if period_end is None:
                period_end = datetime.utcnow()

            reports = []

            # Generate report for each SLO
            slo_names = [slo_name] if slo_name else list(self._slo_configs.keys())

            for name in slo_names:
                if name not in self._slo_configs:
                    continue

                config = self._slo_configs[name]
                report = await self._generate_report_for_slo(config, period_start, period_end)
                reports.append(report)

            return reports

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error generating report: {e}")
            return []

    async def _generate_report_for_slo(
        self,
        config: SLOConfig,
        period_start: datetime,
        period_end: datetime,
    ) -> SLOComplianceReport:
        """Generate compliance report for a single SLO."""
        try:
            # Load metrics from database
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT metric_value, timestamp
                    FROM slo_metrics
                    WHERE service_name = ? AND metric_name = ?
                    AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp
                    """,
                    (
                        self.service_name,
                        config.name,
                        period_start.isoformat(),
                        period_end.isoformat(),
                    ),
                )

                rows = await cursor.fetchall()
                total_measurements = len(rows)

                # Convert to SLIMetric objects
                metrics = [
                    SLIMetric(
                        name=config.name,
                        value=Decimal(row[0]),
                        timestamp=datetime.fromisoformat(row[1]),
                        metric_type=config.metric_type,
                    )
                    for row in rows
                ]

                valid_measurements = len(metrics)

                # Calculate actual SLO
                if valid_measurements >= config.min_samples:
                    actual_slo = await self._calculate_slo_value(config, metrics)
                    status = SLOComplianceStatus.COMPLIANT

                    if actual_slo < config.slo_target:
                        status = SLOComplianceStatus.VIOLATION
                    elif actual_slo < config.slo_target * Decimal("0.95"):
                        status = SLOComplianceStatus.AT_RISK
                else:
                    actual_slo = Decimal("0")
                    status = SLOComplianceStatus.INSUFFICIENT_DATA

                # Load violations
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        """
                        SELECT violation_start, violation_end, actual_value,
                               target_value, severity, resolved
                        FROM slo_violations
                        WHERE service_name = ? AND slo_name = ?
                        AND violation_start >= ? AND violation_start <= ?
                        ORDER BY violation_start
                        """,
                        (
                            self.service_name,
                            config.name,
                            period_start.isoformat(),
                            period_end.isoformat(),
                        ),
                    )

                    violation_rows = await cursor.fetchall()
                    violations = [
                        SLOViolation(
                            slo_name=config.name,
                            violation_start=datetime.fromisoformat(row[0]),
                            violation_end=datetime.fromisoformat(row[1]) if row[1] else None,
                            actual_value=Decimal(row[2]),
                            target_value=Decimal(row[3]),
                            severity=row[4],
                            resolved=bool(row[5]),
                        )
                        for row in violation_rows
                    ]

                return SLOComplianceReport(
                    slo_name=config.name,
                    period_start=period_start,
                    period_end=period_end,
                    target_slo=config.slo_target,
                    actual_slo=actual_slo,
                    status=status,
                    total_measurements=total_measurements,
                    valid_measurements=valid_measurements,
                    violations=violations,
                    calculated_at=datetime.utcnow(),
                )

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error generating report for SLO {config.name}: {e}")
            raise

    def set_violation_callback(
        self,
        callback: Optional[Callable[[SLOViolation], None]],
    ) -> None:
        """Set callback for SLO violations."""
        self._on_violation = callback

    def set_resolution_callback(
        self,
        callback: Optional[Callable[[SLOViolation], None]],
    ) -> None:
        """Set callback for violation resolutions."""
        self._on_violation_resolved = callback

    async def get_active_violations(self) -> List[SLOViolation]:
        """Get list of active violations."""
        return list(self._active_violations.values())

    async def get_slo_configs(self) -> Dict[str, SLOConfig]:
        """Get all SLO configurations."""
        return dict(self._slo_configs)

    async def get_summary(self) -> Dict[str, Any]:
        """Get SLO tracker summary."""
        active = list(self._active_violations.values())

        return {
            "service": self.service_name,
            "slos_registered": len(self._slo_configs),
            "active_violations": len(active),
            "violations": [v.to_dict() for v in active],
            "slos": {name: config.to_dict() for name, config in self._slo_configs.items()},
        }
