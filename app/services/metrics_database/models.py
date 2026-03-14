"""
T18.1: Real-Time Metrics Database Models

Data models for time-series metrics storage and querying.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics tracked."""

    # Risk metrics
    PORTFOLIO_RETURN = "portfolio_return"
    PORTFOLIO_DRAWDOWN = "portfolio_drawdown"
    PORTFOLIO_VOLATILITY = "portfolio_volatility"
    PORTFOLIO_SHARPE = "portfolio_sharpe"

    # Position metrics
    POSITION_SIZE = "position_size"
    POSITION_PNL = "position_pnl"
    POSITION_RETURN = "position_return"

    # Risk scaling metrics
    RISK_ADJUSTMENT = "risk_adjustment"
    LEVERAGE_FACTOR = "leverage_factor"
    VOLATILITY_SCALING = "volatility_scaling"
    DRAWDOWN_SCALING = "drawdown_scaling"

    # Execution metrics
    ORDER_COST = "order_cost"
    SLIPPAGE = "slippage"
    FILL_RATIO = "fill_ratio"
    EXECUTION_TIME = "execution_time"

    # System metrics
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    LATENCY_MS = "latency_ms"
    ERROR_RATE = "error_rate"


class AggregationType(str, Enum):
    """Types of time-series aggregations."""

    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    FIRST = "first"
    LAST = "last"
    MIN = "min"
    MAX = "max"
    AVG = "avg"
    SUM = "sum"
    COUNT = "count"
    STDDEV = "stddev"


@dataclass
class MetricPoint:
    """Single metric data point."""

    timestamp: datetime
    metric_type: MetricType
    value: Decimal
    symbol: Optional[str] = None
    portfolio_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_type": self.metric_type.value,
            "value": str(self.value),
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "tags": self.tags,
        }


@dataclass
class TimeSeriesQuery:
    """Query specification for time-series data."""

    metric_type: MetricType
    start_time: datetime
    end_time: datetime
    symbol: Optional[str] = None
    portfolio_id: Optional[str] = None
    aggregation_type: Optional[AggregationType] = None
    aggregation_interval_minutes: int = 5  # Default: 5-minute candles
    tags_filter: Optional[Dict[str, str]] = None

    def validate(self) -> bool:
        """Validate query parameters."""
        if self.start_time >= self.end_time:
            return False
        if self.aggregation_interval_minutes < 1:
            return False
        return True


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time period."""

    metric_type: MetricType
    symbol: Optional[str]
    portfolio_id: Optional[str]
    period_start: datetime
    period_end: datetime
    aggregation_type: AggregationType

    # Aggregated values
    open_value: Optional[Decimal] = None
    high_value: Optional[Decimal] = None
    low_value: Optional[Decimal] = None
    close_value: Optional[Decimal] = None
    first_value: Optional[Decimal] = None
    last_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    avg_value: Optional[Decimal] = None
    sum_value: Optional[Decimal] = None
    stddev_value: Optional[Decimal] = None
    count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "metric_type": self.metric_type.value,
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "aggregation_type": self.aggregation_type.value,
            "open": str(self.open_value) if self.open_value else None,
            "high": str(self.high_value) if self.high_value else None,
            "low": str(self.low_value) if self.low_value else None,
            "close": str(self.close_value) if self.close_value else None,
            "first": str(self.first_value) if self.first_value else None,
            "last": str(self.last_value) if self.last_value else None,
            "min": str(self.min_value) if self.min_value else None,
            "max": str(self.max_value) if self.max_value else None,
            "avg": str(self.avg_value) if self.avg_value else None,
            "sum": str(self.sum_value) if self.sum_value else None,
            "stddev": str(self.stddev_value) if self.stddev_value else None,
            "count": self.count,
        }


@dataclass
class MetricsCollectionResult:
    """Result of metrics collection operation."""

    success: bool
    metrics_collected: int
    metrics_failed: int
    total_duration_ms: float
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.metrics_collected + self.metrics_failed
        if total == 0:
            return 0.0
        return (self.metrics_collected / total) * 100


@dataclass
class MetricsStorageStats:
    """Statistics about metrics storage."""

    total_metrics_stored: int
    metric_types: int
    date_range_start: datetime
    date_range_end: datetime
    database_size_mb: float
    avg_points_per_metric: float
    retention_days: int

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_metrics_stored": self.total_metrics_stored,
            "metric_types": self.metric_types,
            "date_range_start": self.date_range_start.isoformat(),
            "date_range_end": self.date_range_end.isoformat(),
            "database_size_mb": self.database_size_mb,
            "avg_points_per_metric": self.avg_points_per_metric,
            "retention_days": self.retention_days,
        }


@dataclass
class MetricStatistics:
    """Statistical metrics for a time period."""

    metric_type: MetricType
    symbol: Optional[str]
    portfolio_id: Optional[str]
    period_start: datetime
    period_end: datetime

    # Aggregated statistics
    count: int = 0
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    avg_value: Optional[Decimal] = None
    stddev_value: Optional[Decimal] = None
    sum_value: Optional[Decimal] = None

    # Percentiles
    p25_value: Optional[Decimal] = None
    p50_value: Optional[Decimal] = None
    p75_value: Optional[Decimal] = None
    p95_value: Optional[Decimal] = None
    p99_value: Optional[Decimal] = None

    # Change metrics
    first_value: Optional[Decimal] = None
    last_value: Optional[Decimal] = None
    change_value: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "metric_type": self.metric_type.value,
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "count": self.count,
            "min": str(self.min_value) if self.min_value else None,
            "max": str(self.max_value) if self.max_value else None,
            "avg": str(self.avg_value) if self.avg_value else None,
            "stddev": str(self.stddev_value) if self.stddev_value else None,
            "sum": str(self.sum_value) if self.sum_value else None,
            "p25": str(self.p25_value) if self.p25_value else None,
            "p50": str(self.p50_value) if self.p50_value else None,
            "p75": str(self.p75_value) if self.p75_value else None,
            "p95": str(self.p95_value) if self.p95_value else None,
            "p99": str(self.p99_value) if self.p99_value else None,
            "first": str(self.first_value) if self.first_value else None,
            "last": str(self.last_value) if self.last_value else None,
            "change": str(self.change_value) if self.change_value else None,
            "change_percent": str(self.change_percent) if self.change_percent else None,
        }


@dataclass
class CandlePoint:
    """OHLC candlestick data point."""

    timestamp: datetime
    metric_type: MetricType
    symbol: Optional[str]
    portfolio_id: Optional[str]
    period: str  # "1m", "5m", "15m", "1h", "1d", etc.

    open_value: Decimal
    high_value: Decimal
    low_value: Decimal
    close_value: Decimal
    volume: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_type": self.metric_type.value,
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "period": self.period,
            "open": str(self.open_value),
            "high": str(self.high_value),
            "low": str(self.low_value),
            "close": str(self.close_value),
            "volume": self.volume,
        }


@dataclass
class CachedResult:
    """Cached query result."""

    query_hash: str
    result: List[Any]
    timestamp: datetime
    ttl_seconds: int = 300  # 5 minutes default

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() > (self.timestamp + timedelta(seconds=self.ttl_seconds))


@dataclass
class CollectorSource:
    """Definition of a metric collection source."""

    name: str
    collector_fn: Callable
    enabled: bool = True
    priority: int = 0  # Higher priority = collected first
    timeout_seconds: float = 5.0

    async def collect(self) -> List[MetricPoint]:
        """Execute collection."""
        try:
            logger.debug(
                "Starting metric collection",
                extra={
                    "source_name": self.name,
                    "priority": self.priority,
                    "timeout_seconds": self.timeout_seconds,
                },
            )
            result = await self.collector_fn()
            logger.info(
                "Metric collection completed",
                extra={
                    "source_name": self.name,
                    "metrics_collected": len(result),
                },
            )
            return result
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(
                "Metric collection failed",
                extra={
                    "source_name": self.name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            # Log error but don't raise to allow other sources to continue
            return []


@dataclass
class QuestDBConfig:
    """
    QuestDB connection and configuration.

    Rule 28 Compliant: No hardcoded passwords.
    All credentials read from environment variables.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "qdb"
    user: str = "admin"
    # Rule 28: No default password - must come from environment
    password: str = ""
    pool_size: int = 10
    pool_timeout: float = 10.0
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    batch_size: int = 1000
    retention_days: int = 90

    def __post_init__(self):
        """Validate configuration after initialization."""
        import os

        logger.debug(
            "Initializing QuestDB configuration",
            extra={
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.user,
            },
        )

        # Rule 28: Read password from environment if not provided
        if not self.password:
            self.password = os.getenv("QUESTDB_PASSWORD", "")
        if not self.password:
            import warnings

            logger.warning(
                "QuestDB password not configured",
                extra={
                    "host": self.host,
                    "environment_variable": "QUESTDB_PASSWORD",
                },
            )
            warnings.warn(
                "QUESTDB_PASSWORD not set. QuestDB features may not work correctly.",
                UserWarning,
                stacklevel=2,
            )

    @property
    def connection_string(self) -> str:
        """
        Generate PostgreSQL connection string for QuestDB.

        Rule 28 Compliant: Builds string dynamically from environment variables.
        Never hardcodes credentials in connection strings.
        """
        if not self.password:
            logger.error(
                "Cannot build connection string: password not configured",
                extra={
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                },
            )
            raise ValueError(
                "QUESTDB_PASSWORD environment variable not set. "
                "Cannot build secure connection string."
            )
        logger.debug(
            "QuestDB connection string generated",
            extra={
                "host": self.host,
                "port": self.port,
                "database": self.database,
            },
        )
        return (
            f"postgresql://{self.user}:{self.password}@" f"{self.host}:{self.port}/{self.database}"
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary (safe, without password)."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "pool_size": self.pool_size,
            "batch_size": self.batch_size,
            "retention_days": self.retention_days,
        }


@dataclass
class MetricsCollectorConfig:
    """MetricsCollector configuration."""

    enabled: bool = True
    collection_interval_seconds: int = 60
    batch_size: int = 1000
    flush_interval_seconds: int = 30
    max_pending_metrics: int = 10000

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "collection_interval_seconds": self.collection_interval_seconds,
            "batch_size": self.batch_size,
            "flush_interval_seconds": self.flush_interval_seconds,
            "max_pending_metrics": self.max_pending_metrics,
        }


@dataclass
class MetricsQueryEngineConfig:
    """MetricsQueryEngine configuration."""

    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    max_query_points: int = 100000
    max_cache_entries: int = 1000
    downsampling_enabled: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_query_points": self.max_query_points,
            "max_cache_entries": self.max_cache_entries,
            "downsampling_enabled": self.downsampling_enabled,
        }
