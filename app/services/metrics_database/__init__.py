"""
T18.1: Real-Time Metrics Database Package

Provides high-performance time-series metrics storage and querying with:
- Async QuestDB connector for persistence
- Centralized metrics collection from multiple sources
- Flexible query engine with caching and aggregations
"""

from .metrics_collector import MetricsCollector
from .metrics_query_engine import MetricsQueryEngine
from .models import (
    AggregatedMetrics,
    AggregationType,
    MetricPoint,
    MetricsCollectionResult,
    MetricsStorageStats,
    MetricType,
    TimeSeriesQuery,
)
from .questdb_connector import QuestDBConnector

# Services
__all__ = [
    "AggregatedMetrics",
    "AggregationType",
    "MetricPoint",
    # Models
    "MetricType",
    "MetricsCollectionResult",
    "MetricsCollector",
    "MetricsQueryEngine",
    "MetricsStorageStats",
    "QuestDBConnector",
    "TimeSeriesQuery",
]
