"""
Error Budget Manager - Core Error Budget Tracking (SRE Rule 20)

Implements Google SRE error budget methodology:
- Monthly budget for 99.5% SLO = 216 minutes downtime
- Real-time budget consumption tracking
- Automatic budget rollover
- Historical budget tracking

Domain Model (Cosmic Python - Rule 16):
- ErrorBudget: Domain entity representing error budget state
- BudgetPeriod: Value object for time periods
- BudgetConsumption: Value object for tracking consumption
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import aiosqlite

logger = logging.getLogger(__name__)


class BudgetPeriod(str, Enum):
    """Error budget calculation periods."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class BudgetStatus(str, Enum):
    """Current status of error budget."""

    HEALTHY = "healthy"  # > 50% budget remaining
    WARNING = "warning"  # 25-50% budget remaining
    CRITICAL = "critical"  # 10-25% budget remaining
    EXHAUSTED = "exhausted"  # < 10% budget remaining
    BURN_RATE_HIGH = "burn_rate_high"  # consuming too fast


@dataclass(frozen=True)
class TimeWindow:
    """Value object for time windows (Cosmic Python)."""

    start: datetime
    end: datetime

    @property
    def duration_minutes(self) -> int:
        """Duration in minutes."""
        return int((self.end - self.start).total_seconds() / 60)

    @property
    def duration_hours(self) -> float:
        """Duration in hours."""
        return self.duration_minutes / 60

    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp is within window."""
        return self.start <= timestamp <= self.end


@dataclass(frozen=True)
class BudgetAllowance:
    """Value object for budget allowance (Cosmic Python)."""

    total_minutes: int
    target_slo: Decimal  # e.g., Decimal("0.995") for 99.5%
    period: BudgetPeriod

    @classmethod
    def from_slo(
        cls, total_minutes: int, slo_percentage: Decimal, period: BudgetPeriod
    ) -> BudgetAllowance:
        """
        Create budget allowance from SLO target.

        Args:
            total_minutes: Total minutes in period
            slo_percentage: Target SLO (e.g., 0.995 for 99.5%)
            period: Budget period

        Returns:
            BudgetAllowance with calculated downtime allowance
        """
        total_minutes * (Decimal("1.0") - slo_percentage)
        return cls(
            total_minutes=total_minutes,
            target_slo=slo_percentage,
            period=period,
        )

    @property
    def allowed_downtime_minutes(self) -> int:
        """Calculate allowed downtime in minutes."""
        return int(self.total_minutes * (Decimal("1.0") - self.target_slo))

    @property
    def allowed_downtime_seconds(self) -> int:
        """Calculate allowed downtime in seconds."""
        return self.allowed_downtime_minutes * 60


@dataclass
class BudgetConsumption:
    """Value object for budget consumption tracking."""

    downtime_minutes: int
    error_count: int
    last_incident: datetime | None = None
    incidents: list[dict[str, Any]] = field(default_factory=list)

    def add_incident(self, downtime_minutes: int, incident_data: dict[str, Any]) -> None:
        """Add an incident to consumption."""
        self.downtime_minutes += downtime_minutes
        self.error_count += 1
        self.last_incident = datetime.utcnow()
        self.incidents.append(
            {
                "timestamp": self.last_incident.isoformat(),
                "downtime_minutes": downtime_minutes,
                **incident_data,
            }
        )


@dataclass
class ErrorBudgetState:
    """Domain entity representing current error budget state."""

    service_name: str
    allowance: BudgetAllowance
    consumption: BudgetConsumption
    current_window: TimeWindow
    status: BudgetStatus
    calculated_at: datetime
    burn_rate: Decimal | None = None  # minutes per hour

    @property
    def remaining_minutes(self) -> int:
        """Calculate remaining budget in minutes."""
        return max(
            0,
            self.allowance.allowed_downtime_minutes - self.consumption.downtime_minutes,
        )

    @property
    def remaining_percentage(self) -> Decimal:
        """Calculate remaining budget as percentage."""
        if self.allowance.allowed_downtime_minutes == 0:
            return Decimal("0")
        remaining = Decimal(self.remaining_minutes)
        total = Decimal(self.allowance.allowed_downtime_minutes)
        return (remaining / total) * Decimal("100")

    @property
    def consumed_percentage(self) -> Decimal:
        """Calculate consumed budget as percentage."""
        return Decimal("100") - self.remaining_percentage

    @property
    def actual_slo(self) -> Decimal:
        """Calculate actual SLO achieved."""
        if self.allowance.total_minutes == 0:
            return Decimal("0")
        uptime_minutes = self.allowance.total_minutes - self.consumption.downtime_minutes
        return Decimal(uptime_minutes) / Decimal(self.allowance.total_minutes)

    def is_exhausted(self, threshold_pct: Decimal | None = None) -> bool:
        """Check if budget is exhausted (below threshold)."""
        if threshold_pct is None:
            threshold_pct = Decimal("10")
        return self.remaining_percentage < threshold_pct

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "period": self.allowance.period.value,
            "target_slo": f"{self.allowance.target_slo * 100}%",
            "actual_slo": f"{self.actual_slo * 100}%",
            "allowed_downtime_minutes": self.allowance.allowed_downtime_minutes,
            "consumed_downtime_minutes": self.consumption.downtime_minutes,
            "remaining_minutes": self.remaining_minutes,
            "remaining_percentage": f"{self.remaining_percentage:.2f}%",
            "consumed_percentage": f"{self.consumed_percentage:.2f}%",
            "status": self.status.value,
            "error_count": self.consumption.error_count,
            "burn_rate_minutes_per_hour": f"{self.burn_rate:.2f}" if self.burn_rate else None,
            "window_start": self.current_window.start.isoformat(),
            "window_end": self.current_window.end.isoformat(),
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class ErrorBudgetConfig:
    """Configuration for error budget manager."""

    # SLO targets
    target_slo: Decimal = Decimal("0.995")  # 99.5%
    period: BudgetPeriod = BudgetPeriod.MONTHLY

    # Alert thresholds
    warning_threshold_pct: Decimal = Decimal("50")  # Alert at 50% remaining
    critical_threshold_pct: Decimal = Decimal("25")  # Alert at 25% remaining
    exhausted_threshold_pct: Decimal = Decimal("10")  # Block at 10% remaining

    # Burn rate thresholds
    high_burn_rate_threshold: Decimal | None = None  # 2x normal rate

    # Database
    db_path: str = "data/error_budgets.db"

    # Callbacks
    on_budget_exhausted: Callable[[ErrorBudgetState], None] | None = None
    on_burn_rate_high: Callable[[ErrorBudgetState], None] | None = None


class ErrorBudgetManager:
    """
    Main error budget tracking and calculation (SRE Rule 20).

    Responsibilities:
    - Calculate error budgets based on SLO targets
    - Track downtime and consumption in real-time
    - Monitor burn rate (consumption velocity)
    - Trigger alerts on thresholds
    - Persist budget history

    Domain Logic (Cosmic Python - Rule 16):
    - ErrorBudget is the core domain entity
    - Business rules encapsulated in domain methods
    - Persistence separated from domain logic
    """

    def __init__(
        self,
        service_name: str,
        config: ErrorBudgetConfig | None = None,
    ):
        """
        Initialize error budget manager.

        Args:
            service_name: Name of the service being monitored
            config: Error budget configuration
        """
        self.service_name = service_name
        self.config = config or ErrorBudgetConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._current_state: ErrorBudgetState | None = None
        self._history: list[ErrorBudgetState] = []
        self._lock = asyncio.Lock()

        # Time windows for different periods
        self._time_windows: dict[BudgetPeriod, TimeWindow] = {}

        # Initialize time windows
        self._initialize_time_windows()

        self.logger.info(
            f"ErrorBudgetManager initialized for {service_name} "
            f"(SLO: {self.config.target_slo * 100}%, "
            f"Period: {self.config.period.value})"
        )

    def _initialize_time_windows(self) -> None:
        """Initialize time windows for all periods."""
        now = datetime.utcnow()

        # Monthly window (current month)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1)
        month_end = month_end - timedelta(seconds=1)

        # Weekly window (current week, Monday start)
        weekday = now.weekday()
        week_start = (now - timedelta(days=weekday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(days=7) - timedelta(seconds=1)

        # Daily window (current day)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(seconds=1)

        # Hourly window (current hour)
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1) - timedelta(seconds=1)

        self._time_windows = {
            BudgetPeriod.HOURLY: TimeWindow(hour_start, hour_end),
            BudgetPeriod.DAILY: TimeWindow(day_start, day_end),
            BudgetPeriod.WEEKLY: TimeWindow(week_start, week_end),
            BudgetPeriod.MONTHLY: TimeWindow(month_start, month_end),
        }

        self.logger.debug(f"Time windows initialized: {self._time_windows}")

    def get_time_window(self, period: BudgetPeriod) -> TimeWindow:
        """Get time window for period."""
        return self._time_windows.get(period, TimeWindow(datetime.utcnow(), datetime.utcnow()))

    async def initialize(self) -> None:
        """Initialize the error budget manager."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()

                # Load current state from database
                await self._load_current_state()

                # If no state exists, create initial state
                if self._current_state is None:
                    await self._create_initial_state()

                self.logger.info("ErrorBudgetManager initialized successfully")

            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            # Ensure data directory exists
            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS error_budgets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        period TEXT NOT NULL,
                        window_start TEXT NOT NULL,
                        window_end TEXT NOT NULL,
                        target_slo TEXT NOT NULL,
                        allowed_downtime_minutes INTEGER NOT NULL,
                        consumed_downtime_minutes INTEGER NOT NULL,
                        error_count INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        burn_rate TEXT,
                        calculated_at TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc')),
                        UNIQUE(service_name, period, window_start)
                    )
                """)

                await db.execute("""
                    CREATE TABLE IF NOT EXISTS budget_incidents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        incident_timestamp TEXT NOT NULL,
                        downtime_minutes INTEGER NOT NULL,
                        error_type TEXT,
                        description TEXT,
                        metadata TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """)

                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_budget_service_period
                    ON error_budgets(service_name, period)
                    """)

                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_incidents_service_timestamp
                    ON budget_incidents(service_name, incident_timestamp)
                    """)

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_current_state(self) -> None:
        """Load current state from database."""
        try:
            window = self.get_time_window(self.config.period)

            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT
                        target_slo, allowed_downtime_minutes, consumed_downtime_minutes,
                        error_count, status, burn_rate, calculated_at
                    FROM error_budgets
                    WHERE service_name = ? AND period = ? AND window_start = ?
                    ORDER BY calculated_at DESC
                    LIMIT 1
                    """,
                    (self.service_name, self.config.period.value, window.start.isoformat()),
                )

                row = await cursor.fetchone()

                if row:
                    # Reconstruct state from database
                    allowance = BudgetAllowance(
                        total_minutes=window.duration_minutes,
                        target_slo=Decimal(row[0]),
                        period=self.config.period,
                    )

                    consumption = BudgetConsumption(
                        downtime_minutes=row[2],
                        error_count=row[3],
                    )

                    # Load incidents for this period
                    await cursor.execute(
                        """
                        SELECT incident_timestamp, downtime_minutes, error_type, description, metadata
                        FROM budget_incidents
                        WHERE service_name = ? AND incident_timestamp >= ?
                        ORDER BY incident_timestamp DESC
                        """,
                        (self.service_name, window.start.isoformat()),
                    )

                    incident_rows = await cursor.fetchall()
                    for inc_row in incident_rows:
                        consumption.incidents.append(
                            {
                                "timestamp": inc_row[0],
                                "downtime_minutes": inc_row[1],
                                "error_type": inc_row[2],
                                "description": inc_row[3],
                                "metadata": inc_row[4],
                            }
                        )

                    self._current_state = ErrorBudgetState(
                        service_name=self.service_name,
                        allowance=allowance,
                        consumption=consumption,
                        current_window=window,
                        status=BudgetStatus(row[4]),
                        calculated_at=datetime.fromisoformat(row[6]),
                        burn_rate=Decimal(row[5]) if row[5] else None,
                    )

                    self.logger.info(f"Loaded existing state: {self._current_state.status}")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error loading state: {e}")

    async def _create_initial_state(self) -> None:
        """Create initial error budget state."""
        try:
            window = self.get_time_window(self.config.period)

            allowance = BudgetAllowance.from_slo(
                total_minutes=window.duration_minutes,
                slo_percentage=self.config.target_slo,
                period=self.config.period,
            )

            consumption = BudgetConsumption(downtime_minutes=0, error_count=0)

            self._current_state = ErrorBudgetState(
                service_name=self.service_name,
                allowance=allowance,
                consumption=consumption,
                current_window=window,
                status=BudgetStatus.HEALTHY,
                calculated_at=datetime.utcnow(),
            )

            await self._save_state()

            self.logger.info("Created initial error budget state")

        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error creating initial state: {e}")
            raise

    async def _save_state(self) -> None:
        """Save current state to database."""
        if self._current_state is None:
            return

        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO error_budgets (
                        service_name, period, window_start, window_end,
                        target_slo, allowed_downtime_minutes, consumed_downtime_minutes,
                        error_count, status, burn_rate, calculated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.service_name,
                        self.config.period.value,
                        self._current_state.current_window.start.isoformat(),
                        self._current_state.current_window.end.isoformat(),
                        str(self._current_state.allowance.target_slo),
                        self._current_state.allowance.allowed_downtime_minutes,
                        self._current_state.consumption.downtime_minutes,
                        self._current_state.consumption.error_count,
                        self._current_state.status.value,
                        (
                            str(self._current_state.burn_rate)
                            if self._current_state.burn_rate
                            else None
                        ),
                        self._current_state.calculated_at.isoformat(),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving state: {e}")

    async def record_downtime(
        self,
        downtime_minutes: int,
        error_type: str = "unknown",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ErrorBudgetState:
        """
        Record downtime and update error budget.

        Args:
            downtime_minutes: Minutes of downtime to record
            error_type: Type of error (e.g., "database", "api", "broker")
            description: Human-readable description
            metadata: Additional metadata

        Returns:
            Updated error budget state
        """
        async with self._lock:
            try:
                if self._current_state is None:
                    await self.initialize()

                # Add to consumption
                incident_data = {
                    "error_type": error_type,
                    "description": description,
                    "metadata": metadata,
                }
                self._current_state.consumption.add_incident(downtime_minutes, incident_data)

                # Save incident to database
                await self._save_incident(downtime_minutes, error_type, description, metadata)

                # Recalculate state
                await self._recalculate_state()

                # Check for alerts
                await self._check_alerts()

                self.logger.warning(
                    f"Recorded {downtime_minutes}min downtime (type: {error_type}), "
                    f"budget remaining: {self._current_state.remaining_percentage:.1f}%"
                )

                return self._current_state

            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error recording downtime: {e}")
                raise

    async def _save_incident(
        self,
        downtime_minutes: int,
        error_type: str,
        description: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        """Save incident to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO budget_incidents (
                        service_name, incident_timestamp, downtime_minutes,
                        error_type, description, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.service_name,
                        datetime.utcnow().isoformat(),
                        downtime_minutes,
                        error_type,
                        description,
                        str(metadata) if metadata else None,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving incident: {e}")

    async def _recalculate_state(self) -> None:
        """Recalculate error budget state."""
        if self._current_state is None:
            return

        # Calculate status based on remaining percentage
        remaining_pct = self._current_state.remaining_percentage

        if remaining_pct < Decimal("10"):
            self._current_state.status = BudgetStatus.EXHAUSTED
        elif remaining_pct < Decimal("25"):
            self._current_state.status = BudgetStatus.CRITICAL
        elif remaining_pct < Decimal("50"):
            self._current_state.status = BudgetStatus.WARNING
        else:
            self._current_state.status = BudgetStatus.HEALTHY

        # Calculate burn rate (minutes per hour)
        window = self._current_state.current_window
        elapsed_hours = (datetime.utcnow() - window.start).total_seconds() / 3600

        if elapsed_hours > 0:
            burn_rate = Decimal(self._current_state.consumption.downtime_minutes) / Decimal(
                elapsed_hours
            )
            self._current_state.burn_rate = burn_rate

            # Check for high burn rate
            if burn_rate > self.config.high_burn_rate_threshold:
                self._current_state.status = BudgetStatus.BURN_RATE_HIGH

        self._current_state.calculated_at = datetime.utcnow()

        # Save to database
        await self._save_state()

        # Add to history
        self._history.append(self._current_state)

    async def _check_alerts(self) -> None:
        """Check if alerts should be triggered."""
        if self._current_state is None:
            return

        # Check for exhausted budget
        if self._current_state.is_exhausted(self.config.exhausted_threshold_pct):
            self.logger.critical(
                f"ERROR BUDGET EXHAUSTED: {self.service_name} "
                f"({self._current_state.remaining_percentage:.1f}% remaining)"
            )
            if self.config.on_budget_exhausted:
                try:
                    self.config.on_budget_exhausted(self._current_state)
                except (asyncio.TimeoutError, OSError) as e:
                    self.logger.error(f"Error in exhausted callback: {e}")

        # Check for high burn rate
        if (
            self._current_state.burn_rate
            and self._current_state.burn_rate > self.config.high_burn_rate_threshold
        ):
            self.logger.warning(
                f"HIGH BURN RATE: {self.service_name} ({self._current_state.burn_rate:.2f} min/hr)"
            )
            if self.config.on_burn_rate_high:
                try:
                    self.config.on_burn_rate_high(self._current_state)
                except (asyncio.TimeoutError, OSError) as e:
                    self.logger.error(f"Error in burn rate callback: {e}")

    async def get_current_state(self) -> ErrorBudgetState | None:
        """Get current error budget state."""
        async with self._lock:
            return self._current_state

    async def get_budget_summary(self) -> dict[str, Any]:
        """Get comprehensive budget summary."""
        async with self._lock:
            if self._current_state is None:
                await self.initialize()

            return {
                "service": self.service_name,
                "state": self._current_state.to_dict() if self._current_state else {},
                "thresholds": {
                    "warning_pct": f"{self.config.warning_threshold_pct}%",
                    "critical_pct": f"{self.config.critical_threshold_pct}%",
                    "exhausted_pct": f"{self.config.exhausted_threshold_pct}%",
                    "high_burn_rate": f"{self.config.high_burn_rate_threshold}x",
                },
            }

    async def get_incident_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get incident history."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT incident_timestamp, downtime_minutes, error_type, description, metadata
                    FROM budget_incidents
                    WHERE service_name = ?
                    ORDER BY incident_timestamp DESC
                    LIMIT ?
                    """,
                    (self.service_name, limit),
                )

                rows = await cursor.fetchall()
                return [
                    {
                        "timestamp": row[0],
                        "downtime_minutes": row[1],
                        "error_type": row[2],
                        "description": row[3],
                        "metadata": row[4],
                    }
                    for row in rows
                ]

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error getting incident history: {e}")
            return []

    async def check_deployment_allowed(self) -> tuple[bool, str]:
        """
        Check if deployment is allowed based on error budget.

        Returns:
            Tuple of (allowed, reason)
        """
        async with self._lock:
            if self._current_state is None:
                await self.initialize()

            # Block if budget exhausted
            if self._current_state.is_exhausted(self.config.exhausted_threshold_pct):
                return False, (
                    f"Error budget exhausted ({self._current_state.remaining_percentage:.1f}% "
                    f"remaining < {self.config.exhausted_threshold_pct}% threshold)"
                )

            # Warn if high burn rate
            if (
                self._current_state.burn_rate
                and self._current_state.burn_rate > self.config.high_burn_rate_threshold
            ):
                return True, (
                    f"High burn rate detected ({self._current_state.burn_rate:.2f} min/hr), "
                    f"proceed with caution"
                )

            return True, "Deployment allowed within error budget"


# Singleton instances
_managers: dict[str, ErrorBudgetManager] = {}


def get_error_budget_manager(
    service_name: str,
    config: ErrorBudgetConfig | None = None,
) -> ErrorBudgetManager:
    """
    Get or create singleton error budget manager for service.

    Args:
        service_name: Name of the service
        config: Optional configuration

    Returns:
        ErrorBudgetManager instance
    """
    if service_name not in _managers:
        _managers[service_name] = ErrorBudgetManager(service_name, config)
        logger.info(f"Created ErrorBudgetManager for {service_name}")
    return _managers[service_name]
