"""
Canary Deployment - Progressive Rollout with Auto-Rollback

Implements Google SRE canary deployment practices:
- Gradual traffic shifting
- Automated rollback on degradation
- Metrics comparison between canary and baseline
- Progressive rollout stages
- Blast radius control
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class CanaryStatus(str, Enum):
    """Status of canary deployment."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    ROLLED_BACK = "rolled_back"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CanaryConfig:
    """Configuration for canary deployment."""

    # Deployment details
    strategy_name: str
    version: str
    description: str = ""

    # Traffic progression (percentages)
    stages: List[Decimal] = field(
        default_factory=lambda: [
            Decimal("1"),  # 1% initial
            Decimal("5"),  # 5%
            Decimal("10"),  # 10%
            Decimal("25"),  # 25%
            Decimal("50"),  # 50%
            Decimal("100"),  # 100%
        ]
    )

    # Timing
    stage_duration_minutes: int = 10  # Duration per stage
    min_wait_seconds: int = 60  # Minimum wait before promotion
    warmup_seconds: int = 30  # Warmup period before metrics

    # Rollback thresholds
    rollback_on_error_rate_increase: Decimal = Decimal("0.5")  # 50% increase
    rollback_on_latency_increase: Decimal = Decimal("0.5")  # 50% increase
    rollback_on_availability_drop: Decimal = Decimal("0.99")  # Must maintain 99%

    # Minimum samples for valid comparison
    min_requests_per_stage: int = 100
    min_successful_requests: int = 95

    # Approval
    require_approval: bool = True
    auto_promote: bool = True  # Auto-promote if metrics pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "version": self.version,
            "description": self.description,
            "stages": [f"{s}%" for s in self.stages],
            "stage_duration_minutes": self.stage_duration_minutes,
            "min_wait_seconds": self.min_wait_seconds,
            "warmup_seconds": self.warmup_seconds,
            "rollback_thresholds": {
                "error_rate_increase": f"{self.rollback_on_error_rate_increase * 100}%",
                "latency_increase": f"{self.rollback_on_latency_increase * 100}%",
                "availability_drop": f"{self.rollback_on_availability_drop * 100}%",
            },
            "min_samples": {
                "requests": self.min_requests_per_stage,
                "successful": self.min_successful_requests,
            },
            "require_approval": self.require_approval,
            "auto_promote": self.auto_promote,
        }


@dataclass
class CanaryMetrics:
    """Metrics collected during canary deployment."""

    timestamp: datetime
    stage: int

    # Canary metrics
    canary_requests: int = 0
    canary_successful: int = 0
    canary_failed: int = 0
    canary_latency_p50: float = 0.0
    canary_latency_p95: float = 0.0
    canary_latency_p99: float = 0.0
    canary_error_rate: Decimal = Decimal("0")
    canary_throughput: float = 0.0

    # Baseline (production) metrics
    baseline_requests: int = 0
    baseline_successful: int = 0
    baseline_failed: int = 0
    baseline_latency_p50: float = 0.0
    baseline_latency_p95: float = 0.0
    baseline_latency_p99: float = 0.0
    baseline_error_rate: Decimal = Decimal("0")
    baseline_throughput: float = 0.0

    # Calculated deltas
    error_rate_delta: Optional[Decimal] = None
    latency_delta: Optional[Decimal] = None
    throughput_delta: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "stage": self.stage,
            "canary": {
                "requests": self.canary_requests,
                "successful": self.canary_successful,
                "failed": self.canary_failed,
                "latency_ms": {
                    "p50": self.canary_latency_p50,
                    "p95": self.canary_latency_p95,
                    "p99": self.canary_latency_p99,
                },
                "error_rate": f"{self.canary_error_rate * 100:.2f}%",
                "throughput": self.canary_throughput,
            },
            "baseline": {
                "requests": self.baseline_requests,
                "successful": self.baseline_successful,
                "failed": self.baseline_failed,
                "latency_ms": {
                    "p50": self.baseline_latency_p50,
                    "p95": self.baseline_latency_p95,
                    "p99": self.baseline_latency_p99,
                },
                "error_rate": f"{self.baseline_error_rate * 100:.2f}%",
                "throughput": self.baseline_throughput,
            },
            "deltas": {
                "error_rate": (
                    f"{self.error_rate_delta * 100:.2f}%" if self.error_rate_delta else None
                ),
                "latency": f"{self.latency_delta * 100:.2f}%" if self.latency_delta else None,
                "throughput": (
                    f"{self.throughput_delta * 100:.2f}%" if self.throughput_delta else None
                ),
            },
        }


@dataclass
class CanaryRollbackDecision:
    """Decision to rollback canary deployment."""

    should_rollback: bool
    reason: str
    trigger_metric: Optional[str] = None
    canary_value: Optional[Decimal] = None
    baseline_value: Optional[Decimal] = None
    threshold_exceeded: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "should_rollback": self.should_rollback,
            "reason": self.reason,
            "trigger_metric": self.trigger_metric,
            "canary_value": f"{self.canary_value * 100:.2f}%" if self.canary_value else None,
            "baseline_value": f"{self.baseline_value * 100:.2f}%" if self.baseline_value else None,
            "threshold_exceeded": (
                f"{self.threshold_exceeded * 100:.2f}%" if self.threshold_exceeded else None
            ),
        }


class CanaryDeployment:
    """
    Canary deployment orchestration.

    Responsibilities:
    - Execute progressive rollout stages
    - Collect metrics from canary and baseline
    - Compare metrics and decide on rollback/promotion
    - Auto-rollback on degradation
    - Track deployment history
    """

    def __init__(
        self,
        config: CanaryConfig,
        db_path: str = "data/canary_deployments.db",
        metrics_collector: Optional[Any] = None,
    ):
        """
        Initialize canary deployment.

        Args:
            config: Canary configuration
            db_path: Path to database
            metrics_collector: Optional metrics collector
        """
        self.config = config
        self.db_path = db_path
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(f"{__name__}.{config.strategy_name}")

        # State
        self._status = CanaryStatus.PENDING
        self._current_stage = 0
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._metrics_history: List[CanaryMetrics] = []
        self._rollback_decisions: List[CanaryRollbackDecision] = []
        self._lock = asyncio.Lock()

        # Callbacks
        self._on_stage_complete: Optional[Callable] = None
        self._on_rollback: Optional[Callable] = None
        self._on_complete: Optional[Callable] = None

    async def initialize(self) -> None:
        """Initialize canary deployment."""
        async with self._lock:
            try:
                await self._init_database()
                self.logger.info("CanaryDeployment initialized")
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                self.logger.error(f"Error initializing: {e}")
                raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS canary_deployments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_name TEXT NOT NULL,
                        version TEXT NOT NULL,
                        description TEXT,
                        stages TEXT NOT NULL,
                        status TEXT NOT NULL,
                        current_stage INTEGER NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        rollback_reason TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """)

                await db.execute("""
                    CREATE TABLE IF NOT EXISTS canary_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        deployment_id INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        stage INTEGER NOT NULL,
                        canary_requests INTEGER NOT NULL,
                        canary_successful INTEGER NOT NULL,
                        canary_failed INTEGER NOT NULL,
                        canary_latency_p50 REAL NOT NULL,
                        canary_latency_p95 REAL NOT NULL,
                        canary_latency_p99 REAL NOT NULL,
                        canary_error_rate TEXT NOT NULL,
                        canary_throughput REAL NOT NULL,
                        baseline_requests INTEGER NOT NULL,
                        baseline_successful INTEGER NOT NULL,
                        baseline_failed INTEGER NOT NULL,
                        baseline_latency_p50 REAL NOT NULL,
                        baseline_latency_p95 REAL NOT NULL,
                        baseline_latency_p99 REAL NOT NULL,
                        baseline_error_rate TEXT NOT NULL,
                        baseline_throughput REAL NOT NULL,
                        error_rate_delta TEXT,
                        latency_delta TEXT,
                        throughput_delta TEXT,
                        FOREIGN KEY (deployment_id) REFERENCES canary_deployments(id)
                    )
                """)

                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_canary_deployment_strategy
                    ON canary_deployments(strategy_name)
                """)

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def start(self) -> None:
        """
        Start canary deployment.

        Executes progressive rollout through all stages.
        """
        async with self._lock:
            self._status = CanaryStatus.RUNNING
            self._started_at = datetime.utcnow()

            # Save to database
            deployment_id = await self._save_deployment()

            self.logger.info(
                f"Starting canary deployment: {self.config.strategy_name} v{self.config.version}"
            )

            try:
                # Execute each stage
                for stage_idx, percentage in enumerate(self.config.stages):
                    self._current_stage = stage_idx

                    self.logger.info(
                        f"Stage {stage_idx + 1}/{len(self.config.stages)}: {percentage}% traffic"
                    )

                    # Execute stage
                    await self._execute_stage(stage_idx, percentage, deployment_id)

                    # Check for rollback
                    if self._rollback_decisions and self._rollback_decisions[-1].should_rollback:
                        self.logger.warning(f"Rollback triggered at stage {stage_idx + 1}")
                        await self._rollback(deployment_id)
                        return

                    # Wait before next stage
                    if stage_idx < len(self.config.stages) - 1:
                        await asyncio.sleep(self.config.stage_duration_minutes * 60)

                # All stages completed successfully
                self._status = CanaryStatus.COMPLETED
                self._completed_at = datetime.utcnow()
                await self._update_deployment(deployment_id)

                self.logger.info(
                    f"Canary deployment completed successfully: {self.config.strategy_name}"
                )

                # Trigger callback
                if self._on_complete:
                    await self._on_complete(self)

            except Exception as e:
                self.logger.error(f"Canary deployment failed: {e}")
                self._status = CanaryStatus.FAILED
                self._completed_at = datetime.utcnow()
                await self._update_deployment(deployment_id)
                raise

    async def _execute_stage(
        self,
        stage_idx: int,
        percentage: Decimal,
        deployment_id: int,
    ) -> None:
        """
        Execute a single canary stage.

        Args:
            stage_idx: Stage index
            percentage: Traffic percentage for canary
            deployment_id: Deployment ID in database
        """
        # Warmup period
        if self.config.warmup_seconds > 0:
            self.logger.debug(f"Warming up for {self.config.warmup_seconds}s")
            await asyncio.sleep(self.config.warmup_seconds)

        # Collect metrics
        stage_duration = self.config.stage_duration_minutes * 60
        collection_interval = 30  # Collect every 30 seconds

        end_time = datetime.utcnow() + timedelta(seconds=stage_duration)

        while datetime.utcnow() < end_time:
            # Collect metrics
            metrics = await self._collect_metrics(stage_idx, percentage)
            self._metrics_history.append(metrics)

            # Save metrics
            await self._save_metrics(deployment_id, metrics)

            # Analyze metrics
            rollback_decision = await self._analyze_metrics(metrics)

            if rollback_decision.should_rollback:
                self._rollback_decisions.append(rollback_decision)

                # Trigger callback
                if self._on_rollback:
                    await self._on_rollback(self, rollback_decision)

                return

            # Wait before next collection
            await asyncio.sleep(collection_interval)

        # Stage completed successfully
        self.logger.info(f"Stage {stage_idx + 1} completed")

        # Trigger callback
        if self._on_stage_complete:
            await self._on_stage_complete(self, stage_idx)

    async def _collect_metrics(self, stage: int, percentage: Decimal) -> CanaryMetrics:
        """
        Collect metrics from canary and baseline.

        Args:
            stage: Current stage
            percentage: Traffic percentage

        Returns:
            CanaryMetrics
        """
        if not self.metrics_collector:
            # Return empty metrics if no collector
            return CanaryMetrics(timestamp=datetime.utcnow(), stage=stage)

        try:
            # Collect metrics from both canary and baseline
            canary_metrics = await self.metrics_collector.collect_canary_metrics(
                self.config.strategy_name,
                self.config.version,
            )

            baseline_metrics = await self.metrics_collector.collect_baseline_metrics(
                self.config.strategy_name,
            )

            # Calculate deltas
            error_rate_delta = self._calculate_delta(
                canary_metrics.get("error_rate", Decimal("0")),
                baseline_metrics.get("error_rate", Decimal("0")),
            )

            latency_delta = self._calculate_delta(
                Decimal(str(canary_metrics.get("latency_p95", 0))),
                Decimal(str(baseline_metrics.get("latency_p95", 0))),
            )

            throughput_delta = self._calculate_delta(
                Decimal(str(canary_metrics.get("throughput", 0))),
                Decimal(str(baseline_metrics.get("throughput", 0))),
            )

            return CanaryMetrics(
                timestamp=datetime.utcnow(),
                stage=stage,
                canary_requests=canary_metrics.get("requests", 0),
                canary_successful=canary_metrics.get("successful", 0),
                canary_failed=canary_metrics.get("failed", 0),
                canary_latency_p50=canary_metrics.get("latency_p50", 0.0),
                canary_latency_p95=canary_metrics.get("latency_p95", 0.0),
                canary_latency_p99=canary_metrics.get("latency_p99", 0.0),
                canary_error_rate=canary_metrics.get("error_rate", Decimal("0")),
                canary_throughput=canary_metrics.get("throughput", 0.0),
                baseline_requests=baseline_metrics.get("requests", 0),
                baseline_successful=baseline_metrics.get("successful", 0),
                baseline_failed=baseline_metrics.get("failed", 0),
                baseline_latency_p50=baseline_metrics.get("latency_p50", 0.0),
                baseline_latency_p95=baseline_metrics.get("latency_p95", 0.0),
                baseline_latency_p99=baseline_metrics.get("latency_p99", 0.0),
                baseline_error_rate=baseline_metrics.get("error_rate", Decimal("0")),
                baseline_throughput=baseline_metrics.get("throughput", 0.0),
                error_rate_delta=error_rate_delta,
                latency_delta=latency_delta,
                throughput_delta=throughput_delta,
            )

        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return CanaryMetrics(timestamp=datetime.utcnow(), stage=stage)

    def _calculate_delta(self, canary_value: Decimal, baseline_value: Decimal) -> Optional[Decimal]:
        """Calculate percentage delta between canary and baseline."""
        if baseline_value == 0:
            return None

        return (canary_value - baseline_value) / baseline_value

    async def _analyze_metrics(self, metrics: CanaryMetrics) -> CanaryRollbackDecision:
        """
        Analyze metrics and decide if rollback is needed.

        Args:
            metrics: Collected metrics

        Returns:
            CanaryRollbackDecision
        """
        # Check minimum samples
        if metrics.canary_requests < self.config.min_requests_per_stage:
            # Not enough data, don't rollback yet
            return CanaryRollbackDecision(
                should_rollback=False,
                reason=f"Insufficient samples: {metrics.canary_requests} < {self.config.min_requests_per_stage}",
            )

        # Calculate canary availability
        if metrics.canary_requests > 0:
            canary_availability = Decimal(metrics.canary_successful) / Decimal(
                metrics.canary_requests
            )
        else:
            canary_availability = Decimal("0")

        # Check availability threshold
        if canary_availability < self.config.rollback_on_availability_drop:
            return CanaryRollbackDecision(
                should_rollback=True,
                reason="Availability dropped below threshold",
                trigger_metric="availability",
                canary_value=canary_availability,
                baseline_value=self.config.rollback_on_availability_drop,
                threshold_exceeded=self.config.rollback_on_availability_drop,
            )

        # Check error rate increase
        if metrics.error_rate_delta and metrics.baseline_error_rate > 0:
            if metrics.error_rate_delta > self.config.rollback_on_error_rate_increase:
                return CanaryRollbackDecision(
                    should_rollback=True,
                    reason=f"Error rate increased by {metrics.error_rate_delta * 100:.1f}%",
                    trigger_metric="error_rate",
                    canary_value=metrics.canary_error_rate,
                    baseline_value=metrics.baseline_error_rate,
                    threshold_exceeded=self.config.rollback_on_error_rate_increase,
                )

        # Check latency increase
        if metrics.latency_delta and metrics.baseline_latency_p95 > 0:
            if metrics.latency_delta > self.config.rollback_on_latency_increase:
                return CanaryRollbackDecision(
                    should_rollback=True,
                    reason=f"Latency increased by {metrics.latency_delta * 100:.1f}%",
                    trigger_metric="latency",
                    canary_value=Decimal(str(metrics.canary_latency_p95)),
                    baseline_value=Decimal(str(metrics.baseline_latency_p95)),
                    threshold_exceeded=self.config.rollback_on_latency_increase,
                )

        # All checks passed
        return CanaryRollbackDecision(
            should_rollback=False,
            reason="All metrics within acceptable range",
        )

    async def _rollback(self, deployment_id: int) -> None:
        """
        Rollback canary deployment.

        Args:
            deployment_id: Deployment ID
        """
        self.logger.warning("Rolling back canary deployment")

        self._status = CanaryStatus.ROLLED_BACK
        self._completed_at = datetime.utcnow()

        # Update database
        await self._update_deployment(
            deployment_id,
            rollback_reason=(
                self._rollback_decisions[-1].reason if self._rollback_decisions else None
            ),
        )

        # In real implementation, this would:
        # 1. Shift all traffic back to baseline
        # 2. Scale down canary pods
        # 3. Alert team about rollback

        self.logger.info("Rollback completed")

    async def _save_deployment(self) -> int:
        """Save deployment to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    INSERT INTO canary_deployments
                    (strategy_name, version, description, stages, status, current_stage, started_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.config.strategy_name,
                        self.config.version,
                        self.config.description,
                        str([float(s) for s in self.config.stages]),
                        self._status.value,
                        self._current_stage,
                        self._started_at.isoformat() if self._started_at else None,
                    ),
                )

                await db.commit()

                return cursor.lastrowid

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving deployment: {e}")
            raise

    async def _update_deployment(
        self, deployment_id: int, rollback_reason: Optional[str] = None
    ) -> None:
        """Update deployment in database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE canary_deployments
                    SET status = ?, current_stage = ?, completed_at = ?, rollback_reason = ?
                    WHERE id = ?
                """,
                    (
                        self._status.value,
                        self._current_stage,
                        self._completed_at.isoformat() if self._completed_at else None,
                        rollback_reason,
                        deployment_id,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error updating deployment: {e}")

    async def _save_metrics(self, deployment_id: int, metrics: CanaryMetrics) -> None:
        """Save metrics to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO canary_metrics
                    (deployment_id, timestamp, stage, canary_requests, canary_successful,
                     canary_failed, canary_latency_p50, canary_latency_p95, canary_latency_p99,
                     canary_error_rate, canary_throughput, baseline_requests, baseline_successful,
                     baseline_failed, baseline_latency_p50, baseline_latency_p95, baseline_latency_p99,
                     baseline_error_rate, baseline_throughput, error_rate_delta, latency_delta, throughput_delta)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        deployment_id,
                        metrics.timestamp.isoformat(),
                        metrics.stage,
                        metrics.canary_requests,
                        metrics.canary_successful,
                        metrics.canary_failed,
                        metrics.canary_latency_p50,
                        metrics.canary_latency_p95,
                        metrics.canary_latency_p99,
                        str(metrics.canary_error_rate),
                        metrics.canary_throughput,
                        metrics.baseline_requests,
                        metrics.baseline_successful,
                        metrics.baseline_failed,
                        metrics.baseline_latency_p50,
                        metrics.baseline_latency_p95,
                        metrics.baseline_latency_p99,
                        str(metrics.baseline_error_rate),
                        metrics.baseline_throughput,
                        str(metrics.error_rate_delta) if metrics.error_rate_delta else None,
                        str(metrics.latency_delta) if metrics.latency_delta else None,
                        str(metrics.throughput_delta) if metrics.throughput_delta else None,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving metrics: {e}")

    def set_stage_complete_callback(self, callback: Callable) -> None:
        """Set callback for stage completion."""
        self._on_stage_complete = callback

    def set_rollback_callback(self, callback: Callable) -> None:
        """Set callback for rollback."""
        self._on_rollback = callback

    def set_complete_callback(self, callback: Callable) -> None:
        """Set callback for deployment completion."""
        self._on_complete = callback

    @property
    def status(self) -> CanaryStatus:
        """Get current status."""
        return self._status

    @property
    def current_stage(self) -> int:
        """Get current stage."""
        return self._current_stage

    @property
    def metrics_history(self) -> List[CanaryMetrics]:
        """Get metrics history."""
        return self._metrics_history

    def get_summary(self) -> Dict[str, Any]:
        """Get deployment summary."""
        return {
            "strategy": self.config.strategy_name,
            "version": self.config.version,
            "status": self._status.value,
            "current_stage": self._current_stage,
            "total_stages": len(self.config.stages),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
            "metrics_collected": len(self._metrics_history),
            "rollback_count": len([d for d in self._rollback_decisions if d.should_rollback]),
        }
