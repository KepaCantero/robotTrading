"""
T18.1: Metrics Query Engine - Query builder and executor for time-series metrics

Provides flexible querying, aggregation, and analysis capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from .models import AggregatedMetrics, AggregationType, MetricPoint, MetricType, TimeSeriesQuery
from .questdb_connector import QuestDBConnector

logger = logging.getLogger(__name__)


class MetricsQueryEngine:
    """
    Query engine for time-series metrics.

    Features:
    - Flexible time-range queries
    - Aggregation (OHLC, statistics)
    - Downsampling for large datasets
    - Query result caching
    """

    def __init__(self, questdb_connector: QuestDBConnector, cache_enabled: bool = True):
        """
        Initialize query engine.

        Args:
            questdb_connector: QuestDB connector instance
            cache_enabled: Enable query result caching
        """
        self.questdb = questdb_connector
        self.cache_enabled = cache_enabled
        self._query_cache: Dict[str, List] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutes

    async def query_metric_range(
        self,
        metric_type: MetricType,
        start_time: datetime,
        end_time: datetime,
        symbol: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        limit: int = 10000,
    ) -> List[MetricPoint]:
        """
        Query metrics for a time range.

        Args:
            metric_type: Type of metric to query
            start_time: Start of time range
            end_time: End of time range
            symbol: Optional symbol filter
            portfolio_id: Optional portfolio filter
            limit: Maximum number of results

        Returns:
            List of MetricPoints
        """
        try:
            # Create query object
            query = TimeSeriesQuery(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time,
                symbol=symbol,
                portfolio_id=portfolio_id,
            )

            # Check cache
            cache_key = self._make_cache_key(query)
            if self.cache_enabled and cache_key in self._query_cache and self._is_cache_valid(cache_key):
                logger.debug(f"Cache hit for query: {cache_key}")
                return self._query_cache[cache_key]

            # Execute query
            logger.debug(f"Querying {metric_type.value} " f"from {start_time} to {end_time}")

            results = await self.questdb.query_metrics(query)

            # Apply limit
            if len(results) > limit:
                results = results[:limit]
                logger.warning(f"Query returned {len(results)} results, " f"limited to {limit}")

            # Cache results
            if self.cache_enabled:
                self._query_cache[cache_key] = results
                self._cache_timestamps[cache_key] = datetime.utcnow()

            return results

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Failed to query metric range: {e}")
            return []

    async def query_latest(
        self,
        metric_type: MetricType,
        symbol: Optional[str] = None,
        lookback_minutes: int = 60,
    ) -> Optional[MetricPoint]:
        """
        Get the latest metric value.

        Args:
            metric_type: Type of metric
            symbol: Optional symbol filter
            lookback_minutes: Minutes to look back for latest value

        Returns:
            Latest MetricPoint, or None if not found
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=lookback_minutes)

            results = await self.query_metric_range(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time,
                symbol=symbol,
                limit=1,
            )

            if results:
                return results[-1]  # Last result is most recent

            return None

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to get latest metric: {e}")
            return None

    async def query_ohlc(
        self,
        metric_type: MetricType,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 5,
        symbol: Optional[str] = None,
    ) -> List[AggregatedMetrics]:
        """
        Query OHLC (candle) data for a metric.

        Args:
            metric_type: Type of metric
            start_time: Start of time range
            end_time: End of time range
            interval_minutes: Candle interval in minutes
            symbol: Optional symbol filter

        Returns:
            List of AggregatedMetrics (candles)
        """
        try:
            logger.debug(f"Querying OHLC {metric_type.value} " f"interval: {interval_minutes}m")

            results = await self.questdb.query_aggregated(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time,
                aggregation_type=AggregationType.CLOSE,
                interval_minutes=interval_minutes,
                symbol=symbol,
            )

            return results

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to query OHLC: {e}")
            return []

    async def query_statistics(
        self,
        metric_type: MetricType,
        start_time: datetime,
        end_time: datetime,
        symbol: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Get statistics for a metric over a time range.

        Args:
            metric_type: Type of metric
            start_time: Start of time range
            end_time: End of time range
            symbol: Optional symbol filter

        Returns:
            Dictionary with statistics (min, max, avg, stddev, count)
        """
        try:
            stats = await self.questdb.get_statistics(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time,
                symbol=symbol,
            )

            return stats

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to get statistics: {e}")
            return None

    async def query_change_percentage(
        self,
        metric_type: MetricType,
        start_time: datetime,
        end_time: datetime,
        symbol: Optional[str] = None,
    ) -> Optional[Decimal]:
        """
        Calculate percentage change for a metric.

        Args:
            metric_type: Type of metric
            start_time: Start of time range
            end_time: End of time range
            symbol: Optional symbol filter

        Returns:
            Percentage change, or None if data unavailable
        """
        try:
            # Get first and last values
            start_results = await self.query_metric_range(
                metric_type=metric_type,
                start_time=start_time,
                end_time=start_time + timedelta(minutes=1),
                symbol=symbol,
                limit=1,
            )

            end_results = await self.query_metric_range(
                metric_type=metric_type,
                start_time=end_time - timedelta(minutes=1),
                end_time=end_time,
                symbol=symbol,
                limit=1,
            )

            if not start_results or not end_results:
                return None

            start_value = start_results[0].value
            end_value = end_results[-1].value

            if start_value == 0:
                return None

            change_pct = ((end_value - start_value) / start_value) * 100
            return change_pct

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Failed to calculate change: {e}")
            return None

    async def query_multiple_metrics(
        self,
        metric_types: List[MetricType],
        start_time: datetime,
        end_time: datetime,
        symbol: Optional[str] = None,
    ) -> Dict[str, List[MetricPoint]]:
        """
        Query multiple metrics at once.

        Args:
            metric_types: List of metric types to query
            start_time: Start of time range
            end_time: End of time range
            symbol: Optional symbol filter

        Returns:
            Dictionary mapping metric type to list of points
        """
        try:
            results: Dict[str, List[MetricPoint]] = {}

            for metric_type in metric_types:
                points = await self.query_metric_range(
                    metric_type=metric_type,
                    start_time=start_time,
                    end_time=end_time,
                    symbol=symbol,
                )
                results[metric_type.value] = points

            return results

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to query multiple metrics: {e}")
            return {}

    async def downsample_results(
        self,
        metrics: List[MetricPoint],
        target_points: int = 1000,
    ) -> List[MetricPoint]:
        """
        Downsample large result sets to target number of points.

        Args:
            metrics: Original metric points
            target_points: Target number of points

        Returns:
            Downsampled metric points
        """
        if len(metrics) <= target_points:
            return metrics

        # Calculate step size
        step = len(metrics) // target_points

        # Sample every step-th point
        downsampled = metrics[::step]

        # Ensure last point is included
        if metrics[-1] not in downsampled:
            downsampled.append(metrics[-1])

        logger.debug(f"Downsampled from {len(metrics)} to {len(downsampled)} points")

        return downsampled

    def clear_cache(self) -> None:
        """Clear query cache."""
        self._query_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cleared metrics query cache")

    def _make_cache_key(self, query: TimeSeriesQuery) -> str:
        """Create cache key for query."""
        return (
            f"{query.metric_type.value}:"
            f"{query.start_time.isoformat()}:"
            f"{query.end_time.isoformat()}:"
            f"{query.symbol}:"
            f"{query.portfolio_id}"
        )

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False

        age_seconds = (datetime.utcnow() - self._cache_timestamps[cache_key]).total_seconds()

        return age_seconds < self._cache_ttl_seconds

    async def get_metrics_summary(
        self,
        start_time: datetime,
        end_time: datetime,
        symbol: Optional[str] = None,
    ) -> Dict:
        """
        Get summary of all metrics for a time range.

        Args:
            start_time: Start of time range
            end_time: End of time range
            symbol: Optional symbol filter

        Returns:
            Dictionary with summary statistics for all metric types
        """
        try:
            summary = {}

            # Query statistics for each metric type
            for metric_type in MetricType:
                stats = await self.query_statistics(
                    metric_type=metric_type,
                    start_time=start_time,
                    end_time=end_time,
                    symbol=symbol,
                )

                if stats:
                    summary[metric_type.value] = stats

            return summary

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
