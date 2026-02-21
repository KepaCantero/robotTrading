"""
Chaos Orchestrator - Coordinates Chaos Engineering Experiments

Implements Google SRE chaos engineering practices:
- Hypothesis-driven experimentation
- Controlled failure injection
- Automated validation
- Blast radius control
- Rollback automation

Usage:
    orchestrator = ChaosOrchestrator(
        failure_injectors=[pod_killer, delay_injector],
        blast_radius_controller=blast_controller,
        metrics_collector=metrics
    )

    experiment = await orchestrator.run_experiment(
        name="pod-kill-resilience",
        hypothesis="System remains available when random pods are killed",
        injectors=["pod_killer"],
        duration_minutes=30
    )
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import aiosqlite

from app.core.utils.safe_parse import safe_parse
from .blast_radius import BlastRadiusController
from .hypothesis import ChaosHypothesis, HypothesisStatus, HypothesisValidator, ValidationResult

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    """Status of chaos experiment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


@dataclass
class ChaosExperiment:
    """
    Chaos engineering experiment.

    Represents a complete chaos experiment with hypothesis,
    failure injection, and validation.
    """

    id: str
    name: str
    hypothesis: str
    description: str
    injectors: List[str]
    duration_minutes: int
    status: ExperimentStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    blast_radius_config: Optional[Dict[str, Any]] = None
    validation_result: Optional[ValidationResult] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    incidents: List[Dict[str, Any]] = field(default_factory=list)
    rollback_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "hypothesis": self.hypothesis,
            "description": self.description,
            "injectors": self.injectors,
            "duration_minutes": self.duration_minutes,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "blast_radius_config": self.blast_radius_config,
            "validation_result": (
                self.validation_result.to_dict() if self.validation_result else None
            ),
            "metrics": self.metrics,
            "incidents": self.incidents,
            "rollback_actions": self.rollback_actions,
        }


@dataclass
class ChaosConfig:
    """Configuration for chaos orchestrator."""

    # Safety limits
    max_experiments_per_day: int = 5
    max_duration_minutes: int = 60
    require_approval: bool = True
    allowed_hours: tuple[int, int] = (9, 17)  # 9 AM - 5 PM only

    # Rollback
    auto_rollback_on_failure: bool = True
    rollback_timeout_seconds: int = 300

    # Database
    db_path: str = "data/chaos_experiments.db"

    # Monitoring
    collect_metrics_during_experiment: bool = True
    alert_on_incident: bool = True


class ChaosOrchestrator:
    """
    Chaos engineering orchestration.

    Responsibilities:
    - Design and execute chaos experiments
    - Coordinate failure injectors
    - Validate hypotheses
    - Control blast radius
    - Auto-rollback on failure
    - Track experiment history

    Safety Features:
    - Blast radius limiting
    - Time window restrictions
    - Approval gates
    - Automatic rollback
    - Real-time monitoring
    """

    def __init__(
        self,
        service_name: str,
        failure_injectors: Dict[str, Any],
        blast_radius_controller: BlastRadiusController,
        hypothesis_validator: HypothesisValidator,
        metrics_collector: Optional[Any] = None,
        config: Optional[ChaosConfig] = None,
    ):
        """
        Initialize chaos orchestrator.

        Args:
            service_name: Name of service under test
            failure_injectors: Dictionary of failure injectors
            blast_radius_controller: Blast radius controller
            hypothesis_validator: Hypothesis validator
            metrics_collector: Optional metrics collector
            config: Chaos configuration
        """
        self.service_name = service_name
        self.failure_injectors = failure_injectors
        self.blast_radius_controller = blast_radius_controller
        self.hypothesis_validator = hypothesis_validator
        self.metrics_collector = metrics_collector
        self.config = config or ChaosConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._active_experiments: Dict[str, ChaosExperiment] = {}
        self._experiment_history: List[ChaosExperiment] = []
        self._lock = asyncio.Lock()

        # Approval tracking
        self._approved_experiments: Dict[str, datetime] = {}

        self.logger.info(f"ChaosOrchestrator initialized for {service_name}")

    async def initialize(self) -> None:
        """Initialize chaos orchestrator."""
        async with self._lock:
            try:
                await self._init_database()
                await self._load_active_experiments()
                self.logger.info("ChaosOrchestrator initialized successfully")
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            from pathlib import Path

            db_path = Path(self.config.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chaos_experiments (
                        id TEXT PRIMARY KEY,
                        service_name TEXT NOT NULL,
                        name TEXT NOT NULL,
                        hypothesis TEXT NOT NULL,
                        description TEXT,
                        injectors TEXT NOT NULL,
                        duration_minutes INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        blast_radius_config TEXT,
                        validation_result TEXT,
                        metrics TEXT,
                        incidents TEXT,
                        rollback_actions TEXT
                    )
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_experiments_service_status
                    ON chaos_experiments(service_name, status)
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _load_active_experiments(self) -> None:
        """Load active experiments from database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT id, name, hypothesis, description, injectors,
                           duration_minutes, status, created_at, started_at,
                           completed_at, blast_radius_config, validation_result,
                           metrics, incidents, rollback_actions
                    FROM chaos_experiments
                    WHERE service_name = ? AND status IN ('running', 'pending')
                    """,
                    (self.service_name,),
                )

                rows = await cursor.fetchall()
                for row in rows:
                    experiment = ChaosExperiment(
                        id=row[0],
                        name=row[1],
                        hypothesis=row[2],
                        description=row[3] or "",
                        injectors=safe_parse(row[4], default=[]),
                        duration_minutes=row[5],
                        status=ExperimentStatus(row[6]),
                        created_at=datetime.fromisoformat(row[7]),
                        started_at=datetime.fromisoformat(row[8]) if row[8] else None,
                        completed_at=datetime.fromisoformat(row[9]) if row[9] else None,
                        blast_radius_config=safe_parse(row[10], default=None),
                        validation_result=safe_parse(row[11], default=None),
                        metrics=safe_parse(row[12], default={}),
                        incidents=safe_parse(row[13], default=[]),
                        rollback_actions=safe_parse(row[14], default=[]),
                    )
                    self._active_experiments[experiment.id] = experiment

                self.logger.info(f"Loaded {len(self._active_experiments)} active experiments")

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error loading active experiments: {e}")

    async def run_experiment(
        self,
        name: str,
        hypothesis: str,
        injectors: List[str],
        duration_minutes: int = 30,
        description: str = "",
        blast_radius_config: Optional[Dict[str, Any]] = None,
        approved_by: Optional[str] = None,
    ) -> ChaosExperiment:
        """
        Run a chaos experiment.

        Args:
            name: Experiment name
            hypothesis: Hypothesis to test
            injectors: List of failure injectors to use
            duration_minutes: Experiment duration
            description: Experiment description
            blast_radius_config: Blast radius configuration
            approved_by: User approving the experiment

        Returns:
            ChaosExperiment result
        """
        async with self._lock:
            # Validate experiment can run
            await self._validate_experiment_request(injectors, duration_minutes, approved_by)

            # Create experiment
            experiment = ChaosExperiment(
                id=str(uuid.uuid4()),
                name=name,
                hypothesis=hypothesis,
                description=description,
                injectors=injectors,
                duration_minutes=duration_minutes,
                status=ExperimentStatus.PENDING,
                created_at=datetime.utcnow(),
                blast_radius_config=blast_radius_config or {},
            )

            self._active_experiments[experiment.id] = experiment

            # Save to database
            await self._save_experiment(experiment)

            self.logger.info(f"Chaos experiment created: {name} ({experiment.id})")

            # Run experiment
            try:
                await self._execute_experiment(experiment)
            except Exception as e:
                self.logger.error(f"Experiment failed: {e}")
                experiment.status = ExperimentStatus.FAILED
                experiment.completed_at = datetime.utcnow()
                await self._save_experiment(experiment)
                raise

            return experiment

    async def _validate_experiment_request(
        self,
        injectors: List[str],
        duration_minutes: int,
        approved_by: Optional[str],
    ) -> None:
        """Validate experiment request."""
        # Check time window
        now = datetime.utcnow()
        current_hour = now.hour
        allowed_start, allowed_end = self.config.allowed_hours

        if not (allowed_start <= current_hour < allowed_end):
            raise ValueError(
                f"Experiments only allowed between {allowed_start}:00-{allowed_end}:00. "
                f"Current hour: {current_hour}"
            )

        # Check duration
        if duration_minutes > self.config.max_duration_minutes:
            raise ValueError(
                f"Duration {duration_minutes}min exceeds maximum {self.config.max_duration_minutes}min"
            )

        # Check injectors exist
        for injector_name in injectors:
            if injector_name not in self.failure_injectors:
                raise ValueError(f"Unknown failure injector: {injector_name}")

        # Check approval requirement
        if self.config.require_approval and not approved_by:
            raise ValueError("Experiment approval required but not provided")

        # Check daily limit
        today = now.date()
        today_experiments = [
            e
            for e in self._experiment_history
            if e.created_at.date() == today and e.status != ExperimentStatus.CANCELLED
        ]

        if len(today_experiments) >= self.config.max_experiments_per_day:
            raise ValueError(
                f"Daily experiment limit reached ({self.config.max_experiments_per_day})"
            )

    async def _execute_experiment(self, experiment: ChaosExperiment) -> None:
        """Execute chaos experiment."""
        self.logger.info(f"Starting experiment: {experiment.name}")

        # Update status
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        await self._save_experiment(experiment)

        try:
            # Phase 1: Pre-experiment baseline
            self.logger.info("Phase 1: Collecting baseline metrics...")
            baseline_metrics = await self._collect_baseline_metrics()
            experiment.metrics["baseline"] = baseline_metrics

            # Phase 2: Apply blast radius controls
            self.logger.info("Phase 2: Applying blast radius controls...")
            await self._apply_blast_radius_controls(experiment)

            # Phase 3: Inject failures
            self.logger.info("Phase 3: Injecting failures...")
            await self._inject_failures(experiment)

            # Phase 4: Monitor and validate
            self.logger.info("Phase 4: Monitoring and validating...")
            await self._monitor_experiment(experiment)

            # Phase 5: Validate hypothesis
            self.logger.info("Phase 5: Validating hypothesis...")
            validation_result = await self._validate_hypothesis(experiment, baseline_metrics)
            experiment.validation_result = validation_result

            # Phase 6: Rollback failures
            self.logger.info("Phase 6: Rolling back failures...")
            await self._rollback_failures(experiment)

            # Complete experiment
            experiment.status = ExperimentStatus.COMPLETED
            experiment.completed_at = datetime.utcnow()

            # Remove from active
            if experiment.id in self._active_experiments:
                del self._active_experiments[experiment.id]

            # Add to history
            self._experiment_history.append(experiment)

            # Save final state
            await self._save_experiment(experiment)

            self.logger.info(f"Experiment completed: {experiment.name}")

        except Exception as e:
            self.logger.error(f"Experiment execution failed: {e}")

            # Rollback on failure
            if self.config.auto_rollback_on_failure:
                self.logger.info("Auto-rolling back due to failure...")
                await self._rollback_failures(experiment)
                experiment.status = ExperimentStatus.ROLLED_BACK

            experiment.completed_at = datetime.utcnow()
            await self._save_experiment(experiment)
            raise

    async def _collect_baseline_metrics(self) -> Dict[str, Any]:
        """Collect baseline metrics before chaos."""
        if not self.metrics_collector:
            return {}

        try:
            # Collect current metrics
            metrics = await self.metrics_collector.collect_metrics()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "availability": metrics.get("availability", 0),
                "latency_p50": metrics.get("latency_p50", 0),
                "latency_p95": metrics.get("latency_p95", 0),
                "latency_p99": metrics.get("latency_p99", 0),
                "error_rate": metrics.get("error_rate", 0),
                "throughput": metrics.get("throughput", 0),
            }
        except Exception as e:
            self.logger.error(f"Error collecting baseline: {e}")
            return {}

    async def _apply_blast_radius_controls(self, experiment: ChaosExperiment) -> None:
        """Apply blast radius controls."""
        try:
            if experiment.blast_radius_config:
                await self.blast_radius_controller.apply_controls(experiment.blast_radius_config)
                experiment.rollback_actions.append("blast_radius_controls")
        except Exception as e:
            self.logger.error(f"Error applying blast radius: {e}")
            raise

    async def _inject_failures(self, experiment: ChaosExperiment) -> None:
        """Inject failures based on experiment config."""
        for injector_name in experiment.injectors:
            try:
                injector = self.failure_injectors.get(injector_name)
                if not injector:
                    self.logger.warning(f"Injector not found: {injector_name}")
                    continue

                self.logger.info(f"Injecting failures with: {injector_name}")

                # Start injection
                await injector.inject()

                # Track for rollback
                experiment.rollback_actions.append(f"injector_{injector_name}")

            except Exception as e:
                self.logger.error(f"Error injecting with {injector_name}: {e}")
                experiment.incidents.append(
                    {
                        "type": "injection_failure",
                        "injector": injector_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

    async def _monitor_experiment(self, experiment: ChaosExperiment) -> None:
        """Monitor experiment during execution."""
        end_time = datetime.utcnow() + timedelta(minutes=experiment.duration_minutes)

        while datetime.utcnow() < end_time:
            try:
                # Collect metrics
                if self.metrics_collector:
                    metrics = await self.metrics_collector.collect_metrics()

                    # Check for critical degradation
                    if metrics.get("availability", 1.0) < 0.90:
                        self.logger.critical("Critical availability degradation detected!")
                        experiment.incidents.append(
                            {
                                "type": "critical_degradation",
                                "metric": "availability",
                                "value": metrics.get("availability"),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                        # Rollback if configured
                        if self.config.auto_rollback_on_failure:
                            self.logger.warning("Auto-rolling back due to critical degradation")
                            await self._rollback_failures(experiment)
                            return

                # Wait before next check
                await asyncio.sleep(30)

            except Exception as e:
                self.logger.error(f"Error monitoring experiment: {e}")

    async def _validate_hypothesis(
        self,
        experiment: ChaosExperiment,
        baseline_metrics: Dict[str, Any],
    ) -> ValidationResult:
        """Validate experiment hypothesis."""
        try:
            # Collect post-experiment metrics
            post_metrics = await self._collect_baseline_metrics()

            # Create hypothesis
            hypothesis = ChaosHypothesis(
                name=experiment.name,
                description=experiment.hypothesis,
                expected_behavior="System maintains SLOs during chaos",
                baseline_metrics=baseline_metrics,
                actual_metrics=post_metrics,
            )

            # Validate
            result = await self.hypothesis_validator.validate(hypothesis)

            return result

        except Exception as e:
            self.logger.error(f"Error validating hypothesis: {e}")
            return ValidationResult(
                hypothesis_name=experiment.name,
                status=HypothesisStatus.FAILED,
                confidence=Decimal("0"),
                details={"error": str(e)},
            )

    async def _rollback_failures(self, experiment: ChaosExperiment) -> None:
        """Rollback all injected failures."""
        self.logger.info("Rolling back failures...")

        for action in reversed(experiment.rollback_actions):
            try:
                if action == "blast_radius_controls":
                    await self.blast_radius_controller.remove_controls()

                elif action.startswith("injector_"):
                    injector_name = action.replace("injector_", "")
                    injector = self.failure_injectors.get(injector_name)
                    if injector:
                        await injector.rollback()

                self.logger.info(f"Rolled back: {action}")

            except Exception as e:
                self.logger.error(f"Error rolling back {action}: {e}")

    async def _save_experiment(self, experiment: ChaosExperiment) -> None:
        """Save experiment to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO chaos_experiments
                    (id, service_name, name, hypothesis, description, injectors,
                     duration_minutes, status, created_at, started_at, completed_at,
                     blast_radius_config, validation_result, metrics, incidents, rollback_actions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        experiment.id,
                        self.service_name,
                        experiment.name,
                        experiment.hypothesis,
                        experiment.description,
                        str(experiment.injectors),
                        experiment.duration_minutes,
                        experiment.status.value,
                        experiment.created_at.isoformat(),
                        experiment.started_at.isoformat() if experiment.started_at else None,
                        experiment.completed_at.isoformat() if experiment.completed_at else None,
                        (
                            str(experiment.blast_radius_config)
                            if experiment.blast_radius_config
                            else None
                        ),
                        (
                            str(experiment.validation_result.to_dict())
                            if experiment.validation_result
                            else None
                        ),
                        str(experiment.metrics),
                        str(experiment.incidents),
                        str(experiment.rollback_actions),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving experiment: {e}")

    async def get_active_experiments(self) -> List[ChaosExperiment]:
        """Get active experiments."""
        return list(self._active_experiments.values())

    async def get_experiment_history(self, limit: int = 100) -> List[ChaosExperiment]:
        """Get experiment history."""
        return self._experiment_history[-limit:]

    async def cancel_experiment(self, experiment_id: str) -> bool:
        """Cancel an active experiment."""
        if experiment_id not in self._active_experiments:
            return False

        experiment = self._active_experiments[experiment_id]

        # Rollback
        await self._rollback_failures(experiment)

        # Update status
        experiment.status = ExperimentStatus.CANCELLED
        experiment.completed_at = datetime.utcnow()

        # Save
        await self._save_experiment(experiment)

        # Remove from active
        del self._active_experiments[experiment_id]

        self.logger.info(f"Cancelled experiment: {experiment.name}")
        return True

    async def get_summary(self) -> Dict[str, Any]:
        """Get chaos orchestrator summary."""
        active = list(self._active_experiments.values())

        return {
            "service": self.service_name,
            "active_experiments": len(active),
            "total_experiments": len(self._experiment_history),
            "injectors_available": list(self.failure_injectors.keys()),
            "active": [e.to_dict() for e in active],
            "config": {
                "max_duration_minutes": self.config.max_duration_minutes,
                "require_approval": self.config.require_approval,
                "auto_rollback": self.config.auto_rollback_on_failure,
            },
        }
