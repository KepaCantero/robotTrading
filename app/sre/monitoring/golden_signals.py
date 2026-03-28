"""
Golden Signals Monitoring for Algorithmic Trading System.

Google SRE Golden Signals:
1. Latency: Time to process requests
2. Traffic: Request rate
3. Errors: Rate of failed requests
4. Saturation: How full is the service

This module provides comprehensive monitoring of the four golden signals
with intelligent alerting, trend analysis, and SLO integration.

Usage:
    monitor = GoldenSignalsMonitor(service_name="trading-engine")
    await monitor.initialize()

    # Collect current metrics
    metrics = await monitor.collect_metrics()
    health = monitor.evaluate_health()

    # Check SLO compliance
    slo_status = await monitor.check_slo_compliance()

References:
    - Google SRE Book: https://sre.google/sre-book/monitoring-distributed-systems/
    - SLI/SRE implementation patterns
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiosqlite
import psutil
import contextlib

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """System health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class SignalType(str, Enum):
    """Types of golden signals."""

    LATENCY = "latency"
    TRAFFIC = "traffic"
    ERRORS = "errors"
    SATURATION = "saturation"


@dataclass(frozen=True)
class LatencyMetrics:
    """Latency signal measurements."""

    p50_ms: float  # Median latency
    p95_ms: float  # 95th percentile
    p99_ms: float  # 99th percentile
    p999_ms: float  # 99.9th percentile
    max_ms: float
    mean_ms: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "p999_ms": self.p999_ms,
            "max_ms": self.max_ms,
            "mean_ms": self.mean_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class TrafficMetrics:
    """Traffic signal measurements."""

    requests_per_second: float
    requests_per_minute: float
    requests_per_hour: float
    peak_rps: float
    current_connections: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requests_per_second": self.requests_per_second,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "peak_rps": self.peak_rps,
            "current_connections": self.current_connections,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class ErrorMetrics:
    """Error signal measurements."""

    error_rate_pct: float
    error_count: int
    total_requests: int
    errors_by_type: Dict[str, int]
    critical_errors: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_rate_pct": self.error_rate_pct,
            "error_count": self.error_count,
            "total_requests": self.total_requests,
            "errors_by_type": self.errors_by_type,
            "critical_errors": self.critical_errors,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class SaturationMetrics:
    """Saturation signal measurements."""

    cpu_usage_pct: float
    memory_usage_pct: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_pct: float
    disk_used_gb: float
    disk_free_gb: float
    network_utilization_pct: float
    load_average: Tuple[float, float, float]  # 1min, 5min, 15min
    open_files: int
    thread_count: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_usage_pct": self.cpu_usage_pct,
            "memory_usage_pct": self.memory_usage_pct,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_usage_pct": self.disk_usage_pct,
            "disk_used_gb": self.disk_used_gb,
            "disk_free_gb": self.disk_free_gb,
            "network_utilization_pct": self.network_utilization_pct,
            "load_average_1min": self.load_average[0],
            "load_average_5min": self.load_average[1],
            "load_average_15min": self.load_average[2],
            "open_files": self.open_files,
            "thread_count": self.thread_count,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class GoldenSignalMetrics:
    """Container for all golden signal measurements."""

    service_name: str
    latency: LatencyMetrics
    traffic: TrafficMetrics
    errors: ErrorMetrics
    saturation: SaturationMetrics
    overall_health: HealthStatus
    collected_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "overall_health": self.overall_health.value,
            "latency": self.latency.to_dict(),
            "traffic": self.traffic.to_dict(),
            "errors": self.errors.to_dict(),
            "saturation": self.saturation.to_dict(),
            "collected_at": self.collected_at.isoformat(),
        }


@dataclass
class SLOTarget:
    """SLO target for a golden signal."""

    signal_type: SignalType
    metric_name: str
    target_value: Decimal
    comparison_op: str  # "lt", "lte", "gt", "gte"
    window_minutes: int
    description: str

    def is_compliant(self, actual_value: float) -> bool:
        """Check if actual value meets SLO target."""
        actual = Decimal(str(actual_value))
        target = self.target_value

        if self.comparison_op == "lt":
            return actual < target
        elif self.comparison_op == "lte":
            return actual <= target
        elif self.comparison_op == "gt":
            return actual > target
        elif self.comparison_op == "gte":
            return actual >= target
        else:
            logger.warning(f"Unknown comparison operator: {self.comparison_op}")
            return False


@dataclass
class GoldenSignalsConfig:
    """Configuration for golden signals monitor."""

    service_name: str = "trading-system"

    # SLO Targets
    slo_targets: List[SLOTarget] = field(default_factory=list)

    # Alert thresholds
    latency_warning_ms: float = 500.0
    latency_critical_ms: float = 1000.0
    error_rate_warning_pct: float = 1.0
    error_rate_critical_pct: float = 5.0
    cpu_warning_pct: float = 70.0
    cpu_critical_pct: float = 90.0
    memory_warning_pct: float = 75.0
    memory_critical_pct: float = 90.0
    disk_warning_pct: float = 80.0
    disk_critical_pct: float = 95.0

    # Collection settings
    collection_interval_seconds: int = 60
    history_size: int = 1440  # 24 hours at 1-minute intervals
    latency_sample_size: int = 1000

    # Request tracking for traffic/errors
    enable_request_tracking: bool = True
    request_window_seconds: int = 60

    # Database
    db_path: str = "data/golden_signals.db"

    # Callbacks
    on_health_change: Optional[Callable[[HealthStatus, HealthStatus], None]] = None
    on_slo_violation: Optional[Callable[[SLOTarget, float], None]] = None

    def __post_init__(self):
        """Initialize default SLO targets if none provided."""
        if not self.slo_targets:
            self.slo_targets = [
                # Latency SLOs
                SLOTarget(
                    signal_type=SignalType.LATENCY,
                    metric_name="p95_ms",
                    target_value=Decimal("500"),
                    comparison_op="lte",
                    window_minutes=5,
                    description="95th percentile latency under 500ms",
                ),
                # Error rate SLO
                SLOTarget(
                    signal_type=SignalType.ERRORS,
                    metric_name="error_rate_pct",
                    target_value=Decimal("0.5"),
                    comparison_op="lte",
                    window_minutes=5,
                    description="Error rate under 0.5%",
                ),
                # Saturation SLOs
                SLOTarget(
                    signal_type=SignalType.SATURATION,
                    metric_name="cpu_usage_pct",
                    target_value=Decimal("80"),
                    comparison_op="lte",
                    window_minutes=5,
                    description="CPU usage under 80%",
                ),
                SLOTarget(
                    signal_type=SignalType.SATURATION,
                    metric_name="memory_usage_pct",
                    target_value=Decimal("85"),
                    comparison_op="lte",
                    window_minutes=5,
                    description="Memory usage under 85%",
                ),
            ]


class RequestTracker:
    """Track requests for traffic and error metrics."""

    def __init__(self, window_seconds: int = 60):
        """
        Initialize request tracker.

        Args:
            window_seconds: Time window for request counting
        """
        self.window_seconds = window_seconds
        self._requests: deque = deque()
        self._errors: deque = deque()
        self._error_types: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    def record_request(self, success: bool = True, error_type: Optional[str] = None) -> None:
        """
        Record a request.

        Args:
            success: Whether the request succeeded
            error_type: Type of error if failed
        """
        timestamp = time.time()
        self._requests.append(timestamp)

        if not success:
            self._errors.append(timestamp)
            if error_type:
                self._error_types[error_type] = self._error_types.get(error_type, 0) + 1

    async def get_metrics(self) -> Tuple[int, int, Dict[str, int]]:
        """
        Get request metrics.

        Returns:
            Tuple of (total_requests, error_count, errors_by_type)
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Clean old requests
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()

            while self._errors and self._errors[0] < cutoff:
                self._errors.popleft()

            return len(self._requests), len(self._errors), self._error_types.copy()


class LatencyCollector:
    """Collect latency measurements."""

    def __init__(self, sample_size: int = 1000):
        """
        Initialize latency collector.

        Args:
            sample_size: Maximum number of samples to keep
        """
        self.sample_size = sample_size
        self._latencies: deque = deque(maxlen=sample_size)
        self._lock = asyncio.Lock()

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self._latencies.append(latency_ms)

    async def get_metrics(self) -> Optional[LatencyMetrics]:
        """
        Get latency metrics.

        Returns:
            LatencyMetrics or None if no samples
        """
        async with self._lock:
            if not self._latencies:
                return None

            latencies = sorted(self._latencies)
            count = len(latencies)

            return LatencyMetrics(
                p50_ms=latencies[int(count * 0.5)],
                p95_ms=latencies[int(count * 0.95)],
                p99_ms=latencies[int(count * 0.99)],
                p999_ms=latencies[int(count * 0.999)] if count >= 1000 else latencies[-1],
                max_ms=latencies[-1],
                mean_ms=sum(latencies) / count,
                timestamp=datetime.utcnow(),
            )


class GoldenSignalsMonitor:
    """
    Monitor golden signals for the trading system.

    Implements Google SRE's four golden signals:
    1. Latency: Time to process requests
    2. Traffic: Request rate
    3. Errors: Rate of failed requests
    4. Saturation: How full is the service

    Features:
    - Real-time metrics collection
    - SLO compliance checking
    - Health status evaluation
    - Historical data tracking
    - Intelligent alerting
    - Trend analysis
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[GoldenSignalsConfig] = None,
    ):
        """
        Initialize golden signals monitor.

        Args:
            service_name: Name of the service being monitored
            config: Optional configuration
        """
        self.service_name = service_name
        self.config = config or GoldenSignalsConfig(service_name=service_name)
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # State
        self._current_health: HealthStatus = HealthStatus.HEALTHY
        self._metrics_history: deque = deque(maxlen=self.config.history_size)
        self._lock = asyncio.Lock()

        # Collectors
        self._latency_collector = LatencyCollector(sample_size=self.config.latency_sample_size)
        self._request_tracker = RequestTracker(window_seconds=self.config.request_window_seconds)

        # Network baseline for saturation
        self._network_baseline: Dict[str, float] = {}

        # Collection task
        self._collection_task: Optional[asyncio.Task] = None
        self._is_running = False

        self.logger.info(f"GoldenSignalsMonitor initialized for {service_name}")

    async def initialize(self) -> None:
        """Initialize the monitor."""
        async with self._lock:
            try:
                # Initialize database
                await self._init_database()

                # Initialize network baseline
                await self._initialize_network_baseline()

                self.logger.info("GoldenSignalsMonitor initialized successfully")

            except (asyncio.TimeoutError, OSError) as e:
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
                    CREATE TABLE IF NOT EXISTS golden_signals_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        latency_p50 REAL,
                        latency_p95 REAL,
                        latency_p99 REAL,
                        traffic_rps REAL,
                        error_rate_pct REAL,
                        saturation_cpu REAL,
                        saturation_memory REAL,
                        saturation_disk REAL,
                        health_status TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_signals_service_timestamp
                    ON golden_signals_history(service_name, timestamp)
                """
                )

                await db.commit()

            self.logger.debug("Database schema initialized")

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def _initialize_network_baseline(self) -> None:
        """Initialize network usage baseline."""
        try:
            net_io = psutil.net_io_counters()
            self._network_baseline = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "timestamp": time.time(),
            }
        except Exception as e:
            self.logger.warning(f"Could not initialize network baseline: {e}")

    async def start_collection(self) -> None:
        """Start automatic metrics collection."""
        if self._is_running:
            self.logger.warning("Collection already running")
            return

        self._is_running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        self.logger.info("Started metrics collection")

    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        self._is_running = False
        if self._collection_task:
            self._collection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._collection_task
        self.logger.info("Stopped metrics collection")

    async def _collection_loop(self) -> None:
        """Main collection loop."""
        while self._is_running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.config.collection_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(self.config.collection_interval_seconds)

    async def collect_metrics(self) -> GoldenSignalMetrics:
        """
        Collect all golden signal metrics.

        Returns:
            GoldenSignalMetrics with current measurements
        """
        # Collect individual signals
        latency = await self._collect_latency()
        traffic = await self._collect_traffic()
        errors = await self._collect_errors()
        saturation = await self._collect_saturation()

        # Create metrics container
        metrics = GoldenSignalMetrics(
            service_name=self.service_name,
            latency=latency,
            traffic=traffic,
            errors=errors,
            saturation=saturation,
            overall_health=HealthStatus.HEALTHY,
            collected_at=datetime.utcnow(),
        )

        # Evaluate overall health
        metrics.overall_health = self._evaluate_overall_health(metrics)

        # Check for health changes
        await self._check_health_change(metrics.overall_health)

        # Check SLO compliance
        await self._check_slo_compliance(metrics)

        # Store in history
        async with self._lock:
            self._metrics_history.append(metrics)

        # Persist to database
        await self._persist_metrics(metrics)

        return metrics

    async def _collect_latency(self) -> LatencyMetrics:
        """Collect latency metrics."""
        latency_data = await self._latency_collector.get_metrics()

        if latency_data:
            return latency_data

        # Return zeros if no data
        now = datetime.utcnow()
        return LatencyMetrics(
            p50_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            p999_ms=0.0,
            max_ms=0.0,
            mean_ms=0.0,
            timestamp=now,
        )

    async def _collect_traffic(self) -> TrafficMetrics:
        """Collect traffic metrics."""
        total_requests, _, _ = await self._request_tracker.get_metrics()

        window_seconds = self._request_tracker.window_seconds
        rps = total_requests / window_seconds if window_seconds > 0 else 0.0

        return TrafficMetrics(
            requests_per_second=rps,
            requests_per_minute=rps * 60,
            requests_per_hour=rps * 3600,
            peak_rps=rps,  # NOTE: Track peak separately
            current_connections=self._get_connection_count(),
            timestamp=datetime.utcnow(),
        )

    async def _collect_errors(self) -> ErrorMetrics:
        """Collect error metrics."""
        total_requests, error_count, errors_by_type = await self._request_tracker.get_metrics()

        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0.0

        # Count critical errors
        critical_errors = sum(
            count
            for error_type, count in errors_by_type.items()
            if "critical" in error_type.lower() or "timeout" in error_type.lower()
        )

        return ErrorMetrics(
            error_rate_pct=error_rate,
            error_count=error_count,
            total_requests=total_requests,
            errors_by_type=errors_by_type,
            critical_errors=critical_errors,
            timestamp=datetime.utcnow(),
        )

    async def _collect_saturation(self) -> SaturationMetrics:
        """Collect saturation metrics."""
        try:
            # CPU
            cpu_pct = psutil.cpu_percent(interval=0.1)

            # Memory
            memory = psutil.virtual_memory()
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)

            # Disk
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_free_gb = disk.free / (1024 * 1024 * 1024)

            # Network
            net_util = await self._calculate_network_utilization()

            # Load average (Unix-like systems)
            try:
                load_avg = os.getloadavg()
            except OSError:
                load_avg = (0.0, 0.0, 0.0)

            # Process info
            process = psutil.Process()
            open_files = len(process.open_files()) if hasattr(process, 'open_files') else 0
            thread_count = process.num_threads()

            return SaturationMetrics(
                cpu_usage_pct=cpu_pct,
                memory_usage_pct=memory.percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_pct=disk.percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                network_utilization_pct=net_util,
                load_average=load_avg,
                open_files=open_files,
                thread_count=thread_count,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            self.logger.error(f"Error collecting saturation: {e}")
            # Return zeros on error
            now = datetime.utcnow()
            return SaturationMetrics(
                cpu_usage_pct=0.0,
                memory_usage_pct=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_pct=0.0,
                disk_used_gb=0.0,
                disk_free_gb=0.0,
                network_utilization_pct=0.0,
                load_average=(0.0, 0.0, 0.0),
                open_files=0,
                thread_count=0,
                timestamp=now,
            )

    async def _calculate_network_utilization(self) -> float:
        """Calculate network utilization percentage."""
        try:
            net_io = psutil.net_io_counters()

            if not self._network_baseline:
                return 0.0

            time_delta = time.time() - self._network_baseline["timestamp"]
            if time_delta == 0:
                return 0.0

            bytes_sent_delta = net_io.bytes_sent - self._network_baseline["bytes_sent"]
            bytes_recv_delta = net_io.bytes_recv - self._network_baseline["bytes_recv"]

            total_bytes = bytes_sent_delta + bytes_recv_delta
            bytes_per_second = total_bytes / time_delta

            # Assume 1 Gbps network
            max_bytes_per_second = 1_000_000_000 / 8
            utilization = (bytes_per_second / max_bytes_per_second) * 100

            # Update baseline
            self._network_baseline = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "timestamp": time.time(),
            }

            return min(utilization, 100.0)

        except Exception as e:
            self.logger.warning(f"Error calculating network utilization: {e}")
            return 0.0

    def _get_connection_count(self) -> int:
        """Get current connection count."""
        try:
            # Count network connections
            process = psutil.Process()
            connections = process.connections()
            return len([c for c in connections if c.status == 'ESTABLISHED'])
        except Exception:
            return 0

    def _evaluate_overall_health(self, metrics: GoldenSignalMetrics) -> HealthStatus:
        """
        Evaluate overall system health from golden signals.

        Returns:
            HealthStatus indicating system health
        """
        critical_count = 0
        warning_count = 0

        # Check latency
        if metrics.latency.p99_ms > self.config.latency_critical_ms:
            critical_count += 1
        elif metrics.latency.p99_ms > self.config.latency_warning_ms:
            warning_count += 1

        # Check errors
        if metrics.errors.error_rate_pct > self.config.error_rate_critical_pct:
            critical_count += 1
        elif metrics.errors.error_rate_pct > self.config.error_rate_warning_pct:
            warning_count += 1

        # Check CPU
        if metrics.saturation.cpu_usage_pct > self.config.cpu_critical_pct:
            critical_count += 1
        elif metrics.saturation.cpu_usage_pct > self.config.cpu_warning_pct:
            warning_count += 1

        # Check memory
        if metrics.saturation.memory_usage_pct > self.config.memory_critical_pct:
            critical_count += 1
        elif metrics.saturation.memory_usage_pct > self.config.memory_warning_pct:
            warning_count += 1

        # Check disk
        if metrics.saturation.disk_usage_pct > self.config.disk_critical_pct:
            critical_count += 1
        elif metrics.saturation.disk_usage_pct > self.config.disk_warning_pct:
            warning_count += 1

        # Determine overall health
        if critical_count >= 2:
            return HealthStatus.CRITICAL
        elif critical_count >= 1 or warning_count >= 3:
            return HealthStatus.DEGRADED
        elif warning_count >= 1:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    async def _check_health_change(self, new_health: HealthStatus) -> None:
        """Check if health status has changed."""
        old_health = self._current_health

        if old_health != new_health:
            self.logger.warning(f"Health status changed: {old_health.value} -> {new_health.value}")

            # Notify callback
            if self.config.on_health_change:
                try:
                    self.config.on_health_change(old_health, new_health)
                except Exception as e:
                    self.logger.error(f"Error in health change callback: {e}")

            self._current_health = new_health

    async def _check_slo_compliance(self, metrics: GoldenSignalMetrics) -> None:
        """Check SLO compliance for all targets."""
        for slo_target in self.config.slo_targets:
            try:
                # Get actual value from metrics
                actual_value = self._get_metric_value(metrics, slo_target)

                if actual_value is None:
                    continue

                # Check compliance
                if not slo_target.is_compliant(actual_value):
                    self.logger.warning(
                        f"SLO violation: {slo_target.metric_name}={actual_value} "
                        f"(target: {slo_target.target_value})"
                    )

                    # Notify callback
                    if self.config.on_slo_violation:
                        try:
                            self.config.on_slo_violation(slo_target, actual_value)
                        except Exception as e:
                            self.logger.error(f"Error in SLO violation callback: {e}")

            except Exception as e:
                self.logger.error(f"Error checking SLO compliance: {e}")

    def _get_metric_value(
        self, metrics: GoldenSignalMetrics, slo_target: SLOTarget
    ) -> Optional[float]:
        """Get metric value from metrics based on SLO target."""
        try:
            if slo_target.signal_type == SignalType.LATENCY:
                return getattr(metrics.latency, slo_target.metric_name, None)
            elif slo_target.signal_type == SignalType.TRAFFIC:
                return getattr(metrics.traffic, slo_target.metric_name, None)
            elif slo_target.signal_type == SignalType.ERRORS:
                return getattr(metrics.errors, slo_target.metric_name, None)
            elif slo_target.signal_type == SignalType.SATURATION:
                return getattr(metrics.saturation, slo_target.metric_name, None)
            else:
                return None
        except (AttributeError, TypeError):
            return None

    async def _persist_metrics(self, metrics: GoldenSignalMetrics) -> None:
        """Persist metrics to database."""
        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                # Use current timestamp for created_at
                created_at = datetime.utcnow().isoformat()

                await db.execute(
                    """
                    INSERT INTO golden_signals_history
                    (service_name, timestamp, latency_p50, latency_p95, latency_p99,
                     traffic_rps, error_rate_pct, saturation_cpu, saturation_memory,
                     saturation_disk, health_status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.service_name,
                        metrics.collected_at.isoformat(),
                        metrics.latency.p50_ms,
                        metrics.latency.p95_ms,
                        metrics.latency.p99_ms,
                        metrics.traffic.requests_per_second,
                        metrics.errors.error_rate_pct,
                        metrics.saturation.cpu_usage_pct,
                        metrics.saturation.memory_usage_pct,
                        metrics.saturation.disk_usage_pct,
                        metrics.overall_health.value,
                        created_at,
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error persisting metrics: {e}")

    def record_request(self, success: bool = True, error_type: Optional[str] = None) -> None:
        """Record a request for traffic/error tracking."""
        self._request_tracker.record_request(success, error_type)

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self._latency_collector.record_latency(latency_ms)

    def evaluate_health(self) -> HealthStatus:
        """Get current health status."""
        return self._current_health

    async def get_current_metrics(self) -> Optional[GoldenSignalMetrics]:
        """Get most recent metrics."""
        async with self._lock:
            if self._metrics_history:
                return self._metrics_history[-1]
            return None

    async def get_metrics_history(
        self,
        limit: int = 100,
    ) -> List[GoldenSignalMetrics]:
        """Get metrics history."""
        async with self._lock:
            history = list(self._metrics_history)
            return history[-limit:] if limit else history

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        current = await self.get_current_metrics()

        if not current:
            return {
                "service": self.service_name,
                "status": "no_data",
                "message": "No metrics collected yet",
            }

        return {
            "service": self.service_name,
            "health_status": current.overall_health.value,
            "latency": {
                "p99_ms": current.latency.p99_ms,
                "p95_ms": current.latency.p95_ms,
                "status": (
                    "ok" if current.latency.p99_ms < self.config.latency_warning_ms else "warning"
                ),
            },
            "traffic": {
                "rps": current.traffic.requests_per_second,
                "connections": current.traffic.current_connections,
            },
            "errors": {
                "rate_pct": current.errors.error_rate_pct,
                "count": current.errors.error_count,
                "status": (
                    "ok"
                    if current.errors.error_rate_pct < self.config.error_rate_warning_pct
                    else "warning"
                ),
            },
            "saturation": {
                "cpu_pct": current.saturation.cpu_usage_pct,
                "memory_pct": current.saturation.memory_usage_pct,
                "disk_pct": current.saturation.disk_usage_pct,
                "status": (
                    "ok"
                    if all(
                        [
                            current.saturation.cpu_usage_pct < self.config.cpu_warning_pct,
                            current.saturation.memory_usage_pct < self.config.memory_warning_pct,
                            current.saturation.disk_usage_pct < self.config.disk_warning_pct,
                        ]
                    )
                    else "warning"
                ),
            },
            "collected_at": current.collected_at.isoformat(),
        }

    async def check_slo_compliance(self) -> Dict[str, bool]:
        """
        Check compliance with all SLO targets.

        Returns:
            Dictionary mapping SLO descriptions to compliance status
        """
        current = await self.get_current_metrics()

        if not current:
            return {}

        compliance = {}
        for slo_target in self.config.slo_targets:
            actual_value = self._get_metric_value(current, slo_target)
            if actual_value is not None:
                compliance[slo_target.description] = slo_target.is_compliant(actual_value)

        return compliance


# Singleton instances
_monitors: Dict[str, GoldenSignalsMonitor] = {}


def get_golden_signals_monitor(
    service_name: str,
    config: Optional[GoldenSignalsConfig] = None,
) -> GoldenSignalsMonitor:
    """
    Get or create singleton golden signals monitor for service.

    Args:
        service_name: Name of the service
        config: Optional configuration

    Returns:
        GoldenSignalsMonitor instance
    """
    if service_name not in _monitors:
        _monitors[service_name] = GoldenSignalsMonitor(
            service_name=service_name,
            config=config,
        )
        logger.info(f"Created GoldenSignalsMonitor for {service_name}")
    return _monitors[service_name]
