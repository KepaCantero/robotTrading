"""
Stress Tester - Load and Stress Testing (SRE Rule 20)

Implements load testing to find system breaking points:
- Gradual load ramp-up
- Sustained load testing
- Spike testing
- Break point analysis
- Performance degradation detection

Usage:
    tester = StressTester(service_name, load_generator)
    report = await tester.run_stress_test(
        name="high-load-test",
        target_rps=1000,
        duration_minutes=30,
        ramp_up_minutes=10
    )
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
import aiosqlite

logger = logging.getLogger(__name__)


class StressTestType(str, Enum):
    """Types of stress tests."""

    GRADUAL_RAMP = "gradual_ramp"  # Gradually increase load
    SUSTAINED_LOAD = "sustained_load"  # Constant high load
    SPIKE = "spike"  # Sudden load spike
    BREAK_POINT = "break_point"  # Find breaking point


class TestStatus(str, Enum):
    """Status of stress test."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED_EARLY = "stopped_early"


@dataclass
class LoadTest:
    """
    Load test configuration.

    Defines how to generate load for stress testing.
    """

    name: str
    target_rps: int  # Requests per second
    duration_minutes: int
    ramp_up_minutes: int = 0
    endpoints: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    payload_template: Optional[Dict[str, Any]] = None

    # Load pattern
    test_type: StressTestType = StressTestType.GRADUAL_RAMP
    spike_multiplier: Decimal = Decimal("2.0")  # For spike tests

    # Stopping conditions
    stop_on_error_rate: Decimal = Decimal("0.05")  # 5% error rate
    stop_on_latency_ms: int = 5000  # 5 seconds
    stop_on_availability_drop: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "target_rps": self.target_rps,
            "duration_minutes": self.duration_minutes,
            "ramp_up_minutes": self.ramp_up_minutes,
            "endpoints": self.endpoints,
            "test_type": self.test_type.value,
            "stop_on_error_rate": f"{self.stop_on_error_rate * 100}%",
            "stop_on_latency_ms": self.stop_on_latency_ms,
        }


@dataclass
class StressTestReport:
    """
    Stress test results report.

    Comprehensive analysis of stress test execution.
    """

    test_name: str
    status: TestStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: int

    # Performance metrics
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float

    # Latency metrics (milliseconds)
    latency_p50: float
    latency_p75: float
    latency_p95: float
    latency_p99: float
    latency_max: float
    latency_avg: float

    # Availability
    availability: Decimal

    # Error analysis
    error_rate: Decimal
    error_types: Dict[str, int]

    # Break point analysis
    max_sustained_rps: Optional[int] = None
    breaking_point_rps: Optional[int] = None
    performance_degradation_start: Optional[int] = None

    # Resource usage
    cpu_usage_avg: Optional[float] = None
    memory_usage_avg: Optional[float] = None

    # Incidents
    incidents: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_name": self.test_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "rps": self.requests_per_second,
            },
            "latency_ms": {
                "p50": self.latency_p50,
                "p75": self.latency_p75,
                "p95": self.latency_p95,
                "p99": self.latency_p99,
                "max": self.latency_max,
                "avg": self.latency_avg,
            },
            "availability": f"{self.availability * 100:.2f}%",
            "error_rate": f"{self.error_rate * 100:.2f}%",
            "error_types": self.error_types,
            "break_point": {
                "max_sustained_rps": self.max_sustained_rps,
                "breaking_point_rps": self.breaking_point_rps,
                "degradation_start": self.performance_degradation_start,
            },
            "resources": {
                "cpu_avg": f"{self.cpu_usage_avg:.1f}%" if self.cpu_usage_avg else None,
                "memory_avg": f"{self.memory_usage_avg:.1f}%" if self.memory_usage_avg else None,
            },
            "incidents": self.incidents,
        }


@dataclass
class StressTestConfig:
    """Configuration for stress tester."""

    # Load generator
    base_url: str = "http://localhost:8000"
    concurrent_requests: int = 10
    timeout_seconds: int = 30

    # Monitoring
    collect_metrics: bool = True
    metrics_interval_seconds: int = 5

    # Database
    db_path: str = "data/stress_tests.db"

    # Safety
    max_test_duration_minutes: int = 120
    require_approval: bool = False


class StressTester:
    """
    Stress testing orchestration.

    Responsibilities:
    - Execute stress tests
    - Gradually increase load
    - Monitor performance degradation
    - Detect breaking points
    - Generate comprehensive reports
    """

    def __init__(
        self,
        service_name: str,
        metrics_collector: Optional[Any] = None,
        config: Optional[StressTestConfig] = None,
    ):
        """
        Initialize stress tester.

        Args:
            service_name: Name of service under test
            metrics_collector: Optional metrics collector
            config: Stress test configuration
        """
        self.service_name = service_name
        self.metrics_collector = metrics_collector
        self.config = config or StressTestConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._active_test: Optional[StressTestReport] = None
        self._test_history: List[StressTestReport] = []
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize stress tester."""
        async with self._lock:
            try:
                await self._init_database()
                self.logger.info("StressTester initialized")
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
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS stress_tests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        test_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        duration_seconds INTEGER NOT NULL,
                        total_requests INTEGER NOT NULL,
                        successful_requests INTEGER NOT NULL,
                        failed_requests INTEGER NOT NULL,
                        requests_per_second REAL NOT NULL,
                        latency_p50 REAL NOT NULL,
                        latency_p75 REAL NOT NULL,
                        latency_p95 REAL NOT NULL,
                        latency_p99 REAL NOT NULL,
                        latency_max REAL NOT NULL,
                        latency_avg REAL NOT NULL,
                        availability TEXT NOT NULL,
                        error_rate TEXT NOT NULL,
                        error_types TEXT NOT NULL,
                        max_sustained_rps INTEGER,
                        breaking_point_rps INTEGER,
                        performance_degradation_start INTEGER,
                        incidents TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """)

                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_stress_tests_service
                    ON stress_tests(service_name)
                """)

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def run_stress_test(self, load_test: LoadTest) -> StressTestReport:
        """
        Run stress test.

        Args:
            load_test: Load test configuration

        Returns:
            StressTestReport with results
        """
        async with self._lock:
            self.logger.info(f"Starting stress test: {load_test.name}")

            # Initialize report
            report = StressTestReport(
                test_name=load_test.name,
                status=TestStatus.RUNNING,
                started_at=datetime.utcnow(),
                completed_at=None,
                duration_seconds=0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                requests_per_second=0.0,
                latency_p50=0.0,
                latency_p75=0.0,
                latency_p95=0.0,
                latency_p99=0.0,
                latency_max=0.0,
                latency_avg=0.0,
                availability=Decimal("1.0"),
                error_rate=Decimal("0.0"),
                error_types={},
            )

            self._active_test = report

            try:
                # Execute test based on type
                if load_test.test_type == StressTestType.GRADUAL_RAMP:
                    await self._run_gradual_ramp_test(load_test, report)
                elif load_test.test_type == StressTestType.SUSTAINED_LOAD:
                    await self._run_sustained_load_test(load_test, report)
                elif load_test.test_type == StressTestType.SPIKE:
                    await self._run_spike_test(load_test, report)
                elif load_test.test_type == StressTestType.BREAK_POINT:
                    await self._run_break_point_test(load_test, report)

                # Complete report
                report.status = TestStatus.COMPLETED
                report.completed_at = datetime.utcnow()
                report.duration_seconds = int(
                    (report.completed_at - report.started_at).total_seconds()
                )

                # Save to database
                await self._save_report(report)

                # Add to history
                self._test_history.append(report)

                self.logger.info(f"Stress test completed: {load_test.name}")

            except Exception as e:
                self.logger.error(f"Stress test failed: {e}")
                report.status = TestStatus.FAILED
                report.completed_at = datetime.utcnow()
                await self._save_report(report)
                raise

            return report

    async def _run_gradual_ramp_test(
        self,
        load_test: LoadTest,
        report: StressTestReport,
    ) -> None:
        """Run gradual ramp-up test."""
        self.logger.info("Running gradual ramp-up test")

        latencies = []
        errors: Dict[str, int] = {}

        # Calculate ramp-up steps
        total_steps = 20
        step_duration = (load_test.duration_minutes * 60) / total_steps

        for step in range(total_steps):
            # Calculate current RPS
            current_rps = int(load_test.target_rps * (step + 1) / total_steps)

            self.logger.info(f"Step {step + 1}/{total_steps}: {current_rps} RPS")

            # Execute requests for this step
            step_latencies, step_errors = await self._execute_load_step(
                load_test, current_rps, int(step_duration)
            )

            latencies.extend(step_latencies)

            # Track errors
            for error_type, count in step_errors.items():
                errors[error_type] = errors.get(error_type, 0) + count

            # Check stopping conditions
            if await self._should_stop_early(load_test, latencies, errors):
                self.logger.warning("Stopping test early due to threshold breach")
                report.incidents.append(
                    {
                        "type": "early_stop",
                        "step": step + 1,
                        "reason": "Threshold breach",
                    }
                )
                break

        # Update report
        self._update_report_from_metrics(report, latencies, errors)

    async def _run_sustained_load_test(
        self,
        load_test: LoadTest,
        report: StressTestReport,
    ) -> None:
        """Run sustained load test."""
        self.logger.info("Running sustained load test")

        latencies = []
        errors: Dict[str, int] = {}

        # Ramp up first
        if load_test.ramp_up_minutes > 0:
            self.logger.info(f"Ramping up over {load_test.ramp_up_minutes} minutes")
            await self._ramp_up(load_test, load_test.ramp_up_minutes * 60)

        # Sustained load phase
        sustained_duration = (load_test.duration_minutes - load_test.ramp_up_minutes) * 60

        self.logger.info(f"Sustaining {load_test.target_rps} RPS for {sustained_duration}s")

        start_time = time.time()
        while time.time() - start_time < sustained_duration:
            # Execute requests
            step_latencies, step_errors = await self._execute_load_step(
                load_test, load_test.target_rps, 30
            )

            latencies.extend(step_latencies)

            for error_type, count in step_errors.items():
                errors[error_type] = errors.get(error_type, 0) + count

            # Check stopping conditions
            if await self._should_stop_early(load_test, latencies, errors):
                self.logger.warning("Stopping test early")
                break

        # Update report
        self._update_report_from_metrics(report, latencies, errors)

    async def _run_spike_test(
        self,
        load_test: LoadTest,
        report: StressTestReport,
    ) -> None:
        """Run spike test."""
        self.logger.info("Running spike test")

        latencies = []
        errors: Dict[str, int] = {}

        # Baseline phase
        baseline_rps = load_test.target_rps // 2
        spike_rps = int(load_test.target_rps * float(load_test.spike_multiplier))

        # Baseline (5 minutes)
        self.logger.info(f"Baseline: {baseline_rps} RPS")
        step_latencies, step_errors = await self._execute_load_step(load_test, baseline_rps, 300)
        latencies.extend(step_latencies)
        for error_type, count in step_errors.items():
            errors[error_type] = errors.get(error_type, 0) + count

        # Spike (5 minutes)
        self.logger.info(f"Spike: {spike_rps} RPS")
        step_latencies, step_errors = await self._execute_load_step(load_test, spike_rps, 300)
        latencies.extend(step_latencies)
        for error_type, count in step_errors.items():
            errors[error_type] = errors.get(error_type, 0) + count

        # Recovery (5 minutes)
        self.logger.info(f"Recovery: {baseline_rps} RPS")
        step_latencies, step_errors = await self._execute_load_step(load_test, baseline_rps, 300)
        latencies.extend(step_latencies)
        for error_type, count in step_errors.items():
            errors[error_type] = errors.get(error_type, 0) + count

        # Update report
        self._update_report_from_metrics(report, latencies, errors)

    async def _run_break_point_test(
        self,
        load_test: LoadTest,
        report: StressTestReport,
    ) -> None:
        """Run break point test."""
        self.logger.info("Running break point test")

        latencies = []
        errors: Dict[str, int] = {}

        # Binary search for breaking point
        min_rps = 10
        max_rps = load_test.target_rps * 2
        breaking_point = None

        while min_rps <= max_rps:
            current_rps = (min_rps + max_rps) // 2

            self.logger.info(f"Testing {current_rps} RPS")

            step_latencies, step_errors = await self._execute_load_step(load_test, current_rps, 60)

            error_rate = sum(step_errors.values()) / max(1, len(step_latencies))

            if error_rate > float(load_test.stop_on_error_rate):
                # Too much load, reduce
                breaking_point = current_rps
                max_rps = current_rps - 1
                self.logger.info(f"Breaking point found: {current_rps} RPS")
            else:
                # System handles it, increase
                latencies.extend(step_latencies)
                for error_type, count in step_errors.items():
                    errors[error_type] = errors.get(error_type, 0) + count
                min_rps = current_rps + 1

        report.breaking_point_rps = breaking_point
        report.max_sustained_rps = min_rps - 1

        # Update report
        self._update_report_from_metrics(report, latencies, errors)

    async def _execute_load_step(
        self,
        load_test: LoadTest,
        target_rps: int,
        duration_seconds: int,
    ) -> tuple[List[float], Dict[str, int]]:
        """Execute load for a step."""
        latencies = []
        errors: Dict[str, int] = {}

        # Calculate request interval
        interval = 1.0 / target_rps

        # Create session
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration_seconds

            while time.time() < end_time:
                for endpoint in load_test.endpoints or ["/health"]:
                    try:
                        start = time.time()

                        async with session.get(
                            f"{self.config.base_url}{endpoint}",
                            headers=load_test.headers,
                            timeout=self.config.timeout_seconds,
                        ) as response:
                            await response.read()

                            latency_ms = (time.time() - start) * 1000
                            latencies.append(latency_ms)

                            if response.status >= 400:
                                error_type = f"HTTP_{response.status}"
                                errors[error_type] = errors.get(error_type, 0) + 1

                    except asyncio.TimeoutError:
                        errors["timeout"] = errors.get("timeout", 0) + 1
                    except Exception as e:
                        errors[str(type(e).__name__)] = errors.get(str(type(e).__name__), 0) + 1

                # Wait to maintain RPS
                await asyncio.sleep(interval)

        return latencies, errors

    async def _ramp_up(self, load_test: LoadTest, duration_seconds: int) -> None:
        """Ramp up load gradually."""
        steps = 10
        step_duration = duration_seconds / steps

        for step in range(steps):
            current_rps = int(load_test.target_rps * (step + 1) / steps)
            await self._execute_load_step(load_test, current_rps, int(step_duration))

    async def _should_stop_early(
        self,
        load_test: LoadTest,
        latencies: List[float],
        errors: Dict[str, int],
    ) -> bool:
        """Check if test should stop early."""
        if not latencies:
            return False

        # Check error rate
        error_count = sum(errors.values())
        error_rate = error_count / len(latencies)

        if error_rate > float(load_test.stop_on_error_rate):
            return True

        # Check latency
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            if avg_latency > load_test.stop_on_latency_ms:
                return True

        return False

    def _update_report_from_metrics(
        self,
        report: StressTestReport,
        latencies: List[float],
        errors: Dict[str, int],
    ) -> None:
        """Update report from collected metrics."""
        if not latencies:
            return

        report.total_requests = len(latencies) + sum(errors.values())
        report.successful_requests = len(latencies)
        report.failed_requests = sum(errors.values())

        # Calculate RPS
        duration_hours = report.duration_seconds / 3600
        if duration_hours > 0:
            report.requests_per_second = report.total_requests / report.duration_seconds

        # Calculate latency percentiles
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        report.latency_p50 = sorted_latencies[int(n * 0.50)]
        report.latency_p75 = sorted_latencies[int(n * 0.75)]
        report.latency_p95 = sorted_latencies[int(n * 0.95)]
        report.latency_p99 = sorted_latencies[int(n * 0.99)]
        report.latency_max = max(latencies)
        report.latency_avg = sum(latencies) / n

        # Calculate availability
        report.availability = Decimal(report.successful_requests) / Decimal(report.total_requests)

        # Calculate error rate
        report.error_rate = Decimal(report.failed_requests) / Decimal(report.total_requests)

        # Store error types
        report.error_types = errors

    async def _save_report(self, report: StressTestReport) -> None:
        """Save report to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO stress_tests
                    (service_name, test_name, status, started_at, completed_at,
                     duration_seconds, total_requests, successful_requests, failed_requests,
                     requests_per_second, latency_p50, latency_p75, latency_p95, latency_p99,
                     latency_max, latency_avg, availability, error_rate, error_types,
                     max_sustained_rps, breaking_point_rps, performance_degradation_start, incidents)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.service_name,
                        report.test_name,
                        report.status.value,
                        report.started_at.isoformat(),
                        report.completed_at.isoformat() if report.completed_at else None,
                        report.duration_seconds,
                        report.total_requests,
                        report.successful_requests,
                        report.failed_requests,
                        report.requests_per_second,
                        report.latency_p50,
                        report.latency_p75,
                        report.latency_p95,
                        report.latency_p99,
                        report.latency_max,
                        report.latency_avg,
                        str(report.availability),
                        str(report.error_rate),
                        str(report.error_types),
                        report.max_sustained_rps,
                        report.breaking_point_rps,
                        report.performance_degradation_start,
                        str(report.incidents),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error saving report: {e}")

    async def get_test_history(self, limit: int = 100) -> List[StressTestReport]:
        """Get test history."""
        return self._test_history[-limit:]

    async def get_summary(self) -> Dict[str, Any]:
        """Get stress tester summary."""
        return {
            "service": self.service_name,
            "total_tests": len(self._test_history),
            "active_test": self._active_test.to_dict() if self._active_test else None,
        }
