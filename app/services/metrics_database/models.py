"""
T18.1: Real-Time Metrics Database Models

Data models for time-series metrics storage and querying.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


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
