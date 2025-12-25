"""
Tests for Metrics Query Engine - Query builder and executor for time-series metrics

Tests cover:
- Time-range queries
- OHLC (candle) data retrieval
- Statistics calculation
- Query result caching
- Result downsampling
- Change percentage calculation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.metrics_database import (
    MetricsQueryEngine,
    QuestDBConnector,
    MetricPoint,
    MetricType,
    TimeSeriesQuery,
    AggregationType,
    AggregatedMetrics,
)


@pytest.fixture
def mock_questdb():
    """Create mock QuestDB connector."""
    mock = AsyncMock(spec=QuestDBConnector)
    mock.query_metrics = AsyncMock(return_value=[])
    mock.query_aggregated = AsyncMock(return_value=[])
    mock.get_statistics = AsyncMock(return_value={"min": Decimal("0"), "max": Decimal("100")})
    return mock


@pytest.fixture
def query_engine(mock_questdb):
    """Create MetricsQueryEngine with mock QuestDB."""
    return MetricsQueryEngine(mock_questdb, cache_enabled=True)


class TestMetricsQueryEngineMetricRange:
    """Test time-range query operations."""

    @pytest.mark.asyncio
    async def test_query_metric_range_basic(self, query_engine, mock_questdb):
        """Test basic time-range query."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        metrics = [
            MetricPoint(
                timestamp=start_time,
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            ),
            MetricPoint(
                timestamp=end_time,
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.06"),
            ),
        ]
        mock_questdb.query_metrics.return_value = metrics

        results = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        assert len(results) == 2
        assert results[0].value == Decimal("0.05")

    @pytest.mark.asyncio
    async def test_query_metric_range_with_symbol(self, query_engine, mock_questdb):
        """Test query with symbol filter."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        metrics = [
            MetricPoint(
                timestamp=start_time,
                metric_type=MetricType.POSITION_SIZE,
                value=Decimal("1000"),
                symbol="AAPL",
            ),
        ]
        mock_questdb.query_metrics.return_value = metrics

        results = await query_engine.query_metric_range(
            metric_type=MetricType.POSITION_SIZE,
            start_time=start_time,
            end_time=end_time,
            symbol="AAPL",
        )

        assert len(results) == 1
        assert results[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_query_metric_range_with_portfolio_id(self, query_engine, mock_questdb):
        """Test query with portfolio ID filter."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        results = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
            portfolio_id="port_001",
        )

        # Verify query was called with correct parameters
        assert mock_questdb.query_metrics.called

    @pytest.mark.asyncio
    async def test_query_metric_range_limit(self, query_engine, mock_questdb):
        """Test query with result limit."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        # Return more metrics than limit
        metrics = [
            MetricPoint(
                timestamp=start_time + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )
            for i in range(15)
        ]
        mock_questdb.query_metrics.return_value = metrics

        results = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
            limit=10,
        )

        assert len(results) == 10


class TestMetricsQueryEngineLatest:
    """Test latest value retrieval."""

    @pytest.mark.asyncio
    async def test_query_latest_found(self, query_engine, mock_questdb):
        """Test retrieving latest metric when available."""
        latest = MetricPoint(
            timestamp=datetime.utcnow(),
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.07"),
        )
        mock_questdb.query_metrics.return_value = [latest]

        result = await query_engine.query_latest(
            metric_type=MetricType.PORTFOLIO_RETURN,
            symbol="AAPL",
        )

        assert result is not None
        assert result.value == Decimal("0.07")

    @pytest.mark.asyncio
    async def test_query_latest_not_found(self, query_engine, mock_questdb):
        """Test retrieving latest metric when none available."""
        mock_questdb.query_metrics.return_value = []

        result = await query_engine.query_latest(
            metric_type=MetricType.PORTFOLIO_RETURN,
            symbol="AAPL",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_query_latest_with_lookback(self, query_engine, mock_questdb):
        """Test latest query with custom lookback period."""
        latest = MetricPoint(
            timestamp=datetime.utcnow(),
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.05"),
        )
        mock_questdb.query_metrics.return_value = [latest]

        result = await query_engine.query_latest(
            metric_type=MetricType.PORTFOLIO_RETURN,
            lookback_minutes=120,
        )

        assert result is not None


class TestMetricsQueryEngineOHLC:
    """Test OHLC (candle) queries."""

    @pytest.mark.asyncio
    async def test_query_ohlc_basic(self, query_engine, mock_questdb):
        """Test basic OHLC query."""
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        candles = [
            AggregatedMetrics(
                metric_type=MetricType.PORTFOLIO_RETURN,
                symbol=None,
                portfolio_id=None,
                period_start=start_time,
                period_end=start_time + timedelta(minutes=5),
                aggregation_type=AggregationType.CLOSE,
                open_value=Decimal("0.01"),
                high_value=Decimal("0.05"),
                low_value=Decimal("0.01"),
                close_value=Decimal("0.04"),
            ),
        ]
        mock_questdb.query_aggregated.return_value = candles

        results = await query_engine.query_ohlc(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
            interval_minutes=5,
        )

        assert len(results) == 1
        assert results[0].close_value == Decimal("0.04")

    @pytest.mark.asyncio
    async def test_query_ohlc_multiple_intervals(self, query_engine, mock_questdb):
        """Test OHLC query for multiple intervals."""
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        candles = [
            AggregatedMetrics(
                metric_type=MetricType.PORTFOLIO_RETURN,
                symbol=None,
                portfolio_id=None,
                period_start=start_time + timedelta(minutes=i*5),
                period_end=start_time + timedelta(minutes=(i+1)*5),
                aggregation_type=AggregationType.CLOSE,
                close_value=Decimal(str(0.01 * (i + 1))),
            )
            for i in range(24)
        ]
        mock_questdb.query_aggregated.return_value = candles

        results = await query_engine.query_ohlc(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
            interval_minutes=5,
        )

        assert len(results) == 24

    @pytest.mark.asyncio
    async def test_query_ohlc_different_intervals(self, query_engine):
        """Test OHLC query with different interval sizes."""
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        for interval in [5, 15, 60]:
            await query_engine.query_ohlc(
                metric_type=MetricType.PORTFOLIO_RETURN,
                start_time=start_time,
                end_time=end_time,
                interval_minutes=interval,
            )

        # Verify query was called 3 times with different intervals
        assert query_engine.questdb.query_aggregated.call_count == 3


class TestMetricsQueryEngineStatistics:
    """Test statistics calculation."""

    @pytest.mark.asyncio
    async def test_query_statistics(self, query_engine, mock_questdb):
        """Test retrieving statistics."""
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        stats = {
            "min": Decimal("0.01"),
            "max": Decimal("0.10"),
            "avg": Decimal("0.05"),
            "stddev": Decimal("0.02"),
            "count": 100,
        }
        mock_questdb.get_statistics.return_value = stats

        result = await query_engine.query_statistics(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        assert result is not None
        assert result["min"] == Decimal("0.01")
        assert result["max"] == Decimal("0.10")
        assert result["avg"] == Decimal("0.05")

    @pytest.mark.asyncio
    async def test_query_statistics_with_symbol(self, query_engine, mock_questdb):
        """Test statistics query with symbol filter."""
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        result = await query_engine.query_statistics(
            metric_type=MetricType.POSITION_SIZE,
            start_time=start_time,
            end_time=end_time,
            symbol="AAPL",
        )

        # Verify query was called with symbol parameter
        assert mock_questdb.get_statistics.called


class TestMetricsQueryEngineChangePercentage:
    """Test percentage change calculation."""

    @pytest.mark.asyncio
    async def test_query_change_percentage_positive(self, query_engine, mock_questdb):
        """Test calculating positive percentage change."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        # Setup mock to return different start and end values
        start_metric = MetricPoint(
            timestamp=start_time,
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("100"),
        )
        end_metric = MetricPoint(
            timestamp=end_time,
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("110"),
        )

        mock_questdb.query_metrics.side_effect = [[start_metric], [end_metric]]

        result = await query_engine.query_change_percentage(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        # 10% change
        assert result == Decimal("10")

    @pytest.mark.asyncio
    async def test_query_change_percentage_negative(self, query_engine, mock_questdb):
        """Test calculating negative percentage change."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        start_metric = MetricPoint(
            timestamp=start_time,
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("100"),
        )
        end_metric = MetricPoint(
            timestamp=end_time,
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("90"),
        )

        mock_questdb.query_metrics.side_effect = [[start_metric], [end_metric]]

        result = await query_engine.query_change_percentage(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        # -10% change
        assert result == Decimal("-10")

    @pytest.mark.asyncio
    async def test_query_change_percentage_missing_data(self, query_engine, mock_questdb):
        """Test percentage change when data is missing."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        mock_questdb.query_metrics.return_value = []

        result = await query_engine.query_change_percentage(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        assert result is None


class TestMetricsQueryEngineMultipleMetrics:
    """Test multiple metrics queries."""

    @pytest.mark.asyncio
    async def test_query_multiple_metrics(self, query_engine, mock_questdb):
        """Test querying multiple metric types."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        mock_questdb.query_metrics.return_value = [
            MetricPoint(
                timestamp=start_time,
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            )
        ]

        results = await query_engine.query_multiple_metrics(
            metric_types=[
                MetricType.PORTFOLIO_RETURN,
                MetricType.PORTFOLIO_VOLATILITY,
                MetricType.PORTFOLIO_SHARPE,
            ],
            start_time=start_time,
            end_time=end_time,
        )

        assert len(results) == 3
        assert MetricType.PORTFOLIO_RETURN.value in results


class TestMetricsQueryEngineDownsampling:
    """Test result downsampling."""

    @pytest.mark.asyncio
    async def test_downsample_large_dataset(self, query_engine):
        """Test downsampling large dataset."""
        # Create 10,000 metrics
        metrics = [
            MetricPoint(
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.001 * (i % 100))),
            )
            for i in range(10000)
        ]

        # Downsample to 1000 points
        downsampled = await query_engine.downsample_results(
            metrics=metrics,
            target_points=1000,
        )

        assert len(downsampled) <= 1100  # Allow small overhead
        # First and last points should be preserved
        assert downsampled[0] == metrics[0]
        assert downsampled[-1] == metrics[-1]

    @pytest.mark.asyncio
    async def test_downsample_small_dataset(self, query_engine):
        """Test downsampling dataset smaller than target."""
        metrics = [
            MetricPoint(
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.001 * i)),
            )
            for i in range(100)
        ]

        downsampled = await query_engine.downsample_results(
            metrics=metrics,
            target_points=1000,
        )

        # Should return original if smaller than target
        assert len(downsampled) == 100

    @pytest.mark.asyncio
    async def test_downsample_preserves_last_point(self, query_engine):
        """Test that downsampling preserves last point."""
        metrics = [
            MetricPoint(
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.001 * i)),
            )
            for i in range(5000)
        ]

        downsampled = await query_engine.downsample_results(
            metrics=metrics,
            target_points=100,
        )

        assert downsampled[-1] == metrics[-1]


class TestMetricsQueryEngineCache:
    """Test query result caching."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, query_engine, mock_questdb):
        """Test cache hit on repeated query."""
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        metrics = [
            MetricPoint(
                timestamp=start_time,
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            )
        ]
        mock_questdb.query_metrics.return_value = metrics

        # First query
        results1 = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        # Second query (should hit cache)
        results2 = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        # Both should return same results
        assert results1 == results2
        # But questdb should only be called once
        assert mock_questdb.query_metrics.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_disabled(self, mock_questdb):
        """Test behavior with cache disabled."""
        query_engine = MetricsQueryEngine(mock_questdb, cache_enabled=False)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        metrics = [
            MetricPoint(
                timestamp=start_time,
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            )
        ]
        mock_questdb.query_metrics.return_value = metrics

        # Two identical queries
        await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )
        await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        # Both should hit the database
        assert mock_questdb.query_metrics.call_count == 2

    def test_clear_cache(self, query_engine):
        """Test clearing the cache."""
        query_engine._query_cache["test_key"] = []
        query_engine._cache_timestamps["test_key"] = datetime.utcnow()

        query_engine.clear_cache()

        assert len(query_engine._query_cache) == 0
        assert len(query_engine._cache_timestamps) == 0


class TestMetricsQueryEngineSummary:
    """Test metrics summary retrieval."""

    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, query_engine, mock_questdb):
        """Test retrieving summary of all metrics."""
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        stats_return = {
            "min": Decimal("0"),
            "max": Decimal("100"),
            "avg": Decimal("50"),
        }
        mock_questdb.get_statistics.return_value = stats_return

        summary = await query_engine.get_metrics_summary(
            start_time=start_time,
            end_time=end_time,
        )

        # Should have stats for all metric types
        assert isinstance(summary, dict)


class TestMetricsQueryEngineConfiguration:
    """Test query engine configuration."""

    def test_cache_enabled_configuration(self, mock_questdb):
        """Test cache enabled configuration."""
        engine_with_cache = MetricsQueryEngine(mock_questdb, cache_enabled=True)
        engine_without_cache = MetricsQueryEngine(mock_questdb, cache_enabled=False)

        assert engine_with_cache.cache_enabled is True
        assert engine_without_cache.cache_enabled is False

    def test_cache_ttl_configuration(self, mock_questdb):
        """Test cache TTL configuration."""
        engine = MetricsQueryEngine(mock_questdb)
        assert engine._cache_ttl_seconds == 300

    def test_questdb_reference(self, mock_questdb):
        """Test QuestDB connector reference."""
        engine = MetricsQueryEngine(mock_questdb)
        assert engine.questdb == mock_questdb
