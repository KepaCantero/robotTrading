"""
Game Days - Scheduled Chaos Engineering Events (SRE Rule 20.7)

Implements Google SRE Game Day practices:
- Scheduled chaos events
- Team participation
- Learning objectives
- Incident response practice
- Post-event analysis

Usage:
    game_day = GameDay(
        name="quarterly-chaos-2024-q1",
        scenarios=[pod_kill_scenario, network_delay_scenario],
        participants=["sre-team", "dev-team"]
    )
    await game_day.run()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class GameDayStatus(str, Enum):
    """Status of game day."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ScenarioStatus(str, Enum):
    """Status of game day scenario."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class GameDayScenario:
    """A chaos engineering scenario for game day."""

    name: str
    description: str
    hypothesis: str
    failure_injector: str  # Name of failure injector to use
    injector_config: Dict[str, Any]
    duration_minutes: int
    success_criteria: List[str]
    rollback_procedure: str

    # Results
    status: ScenarioStatus = ScenarioStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Dict[str, Any] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "hypothesis": self.hypothesis,
            "failure_injector": self.failure_injector,
            "injector_config": self.injector_config,
            "duration_minutes": self.duration_minutes,
            "success_criteria": self.success_criteria,
            "rollback_procedure": self.rollback_procedure,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": self.results,
            "lessons_learned": self.lessons_learned,
        }


@dataclass
class GameDayReport:
    """Report from a game day event."""

    game_day_name: str
    date: datetime
    participants: List[str]
    scenarios: List[GameDayScenario]
    overall_status: GameDayStatus

    # Metrics
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    skipped_scenarios: int

    # Observations
    key_findings: List[str]
    improvement_areas: List[str]
    action_items: List[str]

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_minutes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "game_day_name": self.game_day_name,
            "date": self.date.isoformat(),
            "participants": self.participants,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "overall_status": self.overall_status.value,
            "metrics": {
                "total": self.total_scenarios,
                "passed": self.passed_scenarios,
                "failed": self.failed_scenarios,
                "skipped": self.skipped_scenarios,
                "pass_rate": (
                    f"{(self.passed_scenarios / self.total_scenarios * 100):.1f}%"
                    if self.total_scenarios > 0
                    else "N/A"
                ),
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_minutes": self.total_duration_minutes,
            "key_findings": self.key_findings,
            "improvement_areas": self.improvement_areas,
            "action_items": self.action_items,
        }


@dataclass
class GameDayConfig:
    """Configuration for game day."""

    name: str
    description: str
    scheduled_date: datetime
    participants: List[str]
    scenarios: List[GameDayScenario]

    # Options
    auto_rollback_on_failure: bool = True
    require_approval: bool = True
    approved_by: Optional[str] = None

    # Documentation
    pre_event_summary: str = ""
    post_event_template: str = ""

    # Database
    db_path: str = "data/game_days.db"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "scheduled_date": self.scheduled_date.isoformat(),
            "participants": self.participants,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "auto_rollback_on_failure": self.auto_rollback_on_failure,
            "require_approval": self.require_approval,
            "approved_by": self.approved_by,
        }


class GameDay:
    """
    Game day orchestration.

    Responsibilities:
    - Execute game day scenarios
    - Track results
    - Generate reports
    - Document lessons learned

    Usage:
        config = GameDayConfig(
            name="quarterly-chaos-2024-q1",
            description="Quarterly chaos engineering game day",
            scheduled_date=datetime(2024, 3, 15, 10, 0),
            participants=["sre-team", "dev-team"],
            scenarios=[scenario1, scenario2]
        )

        game_day = GameDay(config)
        await game_day.initialize()
        report = await game_day.run()
    """

    def __init__(
        self,
        config: GameDayConfig,
        failure_injectors: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize game day.

        Args:
            config: Game day configuration
            failure_injectors: Dictionary of available failure injectors
        """
        self.config = config
        self.failure_injectors = failure_injectors or {}
        self.logger = logging.getLogger(f"{__name__}.{config.name}")

        # State
        self._status = GameDayStatus.PLANNED
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

        # Callbacks
        self._on_scenario_complete: Optional[Callable] = None
        self._on_scenario_fail: Optional[Callable] = None

    async def initialize(self) -> None:
        """Initialize game day."""
        try:
            await self._init_database()
            self.logger.info("GameDay initialized")
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
                    CREATE TABLE IF NOT EXISTS game_days (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        scheduled_date TEXT NOT NULL,
                        participants TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        total_duration_minutes INTEGER,
                        key_findings TEXT,
                        improvement_areas TEXT,
                        action_items TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS game_day_scenarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_day_name TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        hypothesis TEXT NOT NULL,
                        failure_injector TEXT NOT NULL,
                        injector_config TEXT NOT NULL,
                        duration_minutes INTEGER NOT NULL,
                        success_criteria TEXT NOT NULL,
                        rollback_procedure TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        results TEXT,
                        lessons_learned TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                # Indexes
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_game_days_name
                    ON game_days(name)
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def run(self) -> GameDayReport:
        """
        Run the game day.

        Returns:
            GameDayReport with results
        """
        self.logger.info(f"Starting game day: {self.config.name}")

        self._status = GameDayStatus.IN_PROGRESS
        self._started_at = datetime.utcnow()

        try:
            # Save game day start
            await self._save_game_day_start()

            # Run each scenario
            for scenario in self.config.scenarios:
                try:
                    await self._run_scenario(scenario)

                except Exception as e:
                    self.logger.error(f"Scenario {scenario.name} failed: {e}")
                    scenario.status = ScenarioStatus.FAILED
                    scenario.completed_at = datetime.utcnow()

                    if self._on_scenario_fail:
                        await self._on_scenario_fail(scenario, e)

            # Complete game day
            self._status = GameDayStatus.COMPLETED
            self._completed_at = datetime.utcnow()

            # Generate report
            report = await self._generate_report()

            # Save report
            await self._save_game_day_complete(report)

            self.logger.info(f"Game day completed: {self.config.name}")

            return report

        except Exception as e:
            self.logger.error(f"Game day failed: {e}")
            self._status = GameDayStatus.CANCELLED
            self._completed_at = datetime.utcnow()
            raise

    async def _run_scenario(self, scenario: GameDayScenario) -> None:
        """
        Run a single scenario.

        Args:
            scenario: Scenario to run
        """
        self.logger.info(f"Running scenario: {scenario.name}")

        scenario.status = ScenarioStatus.RUNNING
        scenario.started_at = datetime.utcnow()

        try:
            # Get failure injector
            injector = self.failure_injectors.get(scenario.failure_injector)

            if not injector:
                raise ValueError(f"Failure injector not found: {scenario.failure_injector}")

            # Inject failure
            await injector.inject()

            # Wait for scenario duration
            await asyncio.sleep(scenario.duration_minutes * 60)

            # Validate success criteria
            success = await self._validate_success_criteria(scenario)

            if success:
                scenario.status = ScenarioStatus.PASSED
                self.logger.info(f"Scenario {scenario.name} passed")
            else:
                scenario.status = ScenarioStatus.FAILED
                self.logger.warning(f"Scenario {scenario.name} failed")

            # Rollback
            await injector.rollback()

            scenario.completed_at = datetime.utcnow()

            # Save scenario
            await self._save_scenario(scenario)

            # Trigger callback
            if self._on_scenario_complete:
                await self._on_scenario_complete(scenario)

        except Exception as e:
            self.logger.error(f"Scenario {scenario.name} error: {e}")

            # Attempt rollback
            try:
                if injector:
                    await injector.rollback()
            except:
                pass

            scenario.status = ScenarioStatus.FAILED
            scenario.completed_at = datetime.utcnow()
            scenario.results["error"] = str(e)

            await self._save_scenario(scenario)

            raise

    async def _validate_success_criteria(self, scenario: GameDayScenario) -> bool:
        """
        Validate scenario success criteria.

        Args:
            scenario: Scenario to validate

        Returns:
            True if all criteria met
        """
        # Placeholder implementation
        # In production, this would check actual metrics against criteria

        # For now, assume success
        return True

    async def _generate_report(self) -> GameDayReport:
        """Generate game day report."""
        scenarios = self.config.scenarios

        passed = sum(1 for s in scenarios if s.status == ScenarioStatus.PASSED)
        failed = sum(1 for s in scenarios if s.status == ScenarioStatus.FAILED)
        skipped = sum(1 for s in scenarios if s.status == ScenarioStatus.SKIPPED)

        total_duration = None
        if self._started_at and self._completed_at:
            total_duration = int((self._completed_at - self._started_at).total_seconds() / 60)

        return GameDayReport(
            game_day_name=self.config.name,
            date=self.config.scheduled_date,
            participants=self.config.participants,
            scenarios=scenarios,
            overall_status=self._status,
            total_scenarios=len(scenarios),
            passed_scenarios=passed,
            failed_scenarios=failed,
            skipped_scenarios=skipped,
            key_findings=[],
            improvement_areas=[],
            action_items=[],
            started_at=self._started_at,
            completed_at=self._completed_at,
            total_duration_minutes=total_duration,
        )

    async def _save_game_day_start(self) -> None:
        """Save game day start to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO game_days
                    (name, description, scheduled_date, participants, status, started_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.config.name,
                        self.config.description,
                        self.config.scheduled_date.isoformat(),
                        str(self.config.participants),
                        self._status.value,
                        self._started_at.isoformat() if self._started_at else None,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving game day: {e}")

    async def _save_game_day_complete(self, report: GameDayReport) -> None:
        """Save completed game day to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    UPDATE game_days
                    SET status = ?, completed_at = ?, total_duration_minutes = ?,
                        key_findings = ?, improvement_areas = ?, action_items = ?
                    WHERE name = ?
                """,
                    (
                        self._status.value,
                        self._completed_at.isoformat() if self._completed_at else None,
                        report.total_duration_minutes,
                        str(report.key_findings),
                        str(report.improvement_areas),
                        str(report.action_items),
                        self.config.name,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error updating game day: {e}")

    async def _save_scenario(self, scenario: GameDayScenario) -> None:
        """Save scenario to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO game_day_scenarios
                    (game_day_name, name, description, hypothesis, failure_injector,
                     injector_config, duration_minutes, success_criteria, rollback_procedure,
                     status, started_at, completed_at, results, lessons_learned)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.config.name,
                        scenario.name,
                        scenario.description,
                        scenario.hypothesis,
                        scenario.failure_injector,
                        str(scenario.injector_config),
                        scenario.duration_minutes,
                        str(scenario.success_criteria),
                        scenario.rollback_procedure,
                        scenario.status.value,
                        scenario.started_at.isoformat() if scenario.started_at else None,
                        scenario.completed_at.isoformat() if scenario.completed_at else None,
                        str(scenario.results),
                        str(scenario.lessons_learned),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving scenario: {e}")

    def set_scenario_complete_callback(self, callback: Callable) -> None:
        """Set callback for scenario completion."""
        self._on_scenario_complete = callback

    def set_scenario_fail_callback(self, callback: Callable) -> None:
        """Set callback for scenario failure."""
        self._on_scenario_fail = callback

    @property
    def status(self) -> GameDayStatus:
        """Get current status."""
        return self._status
