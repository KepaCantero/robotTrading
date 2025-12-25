"""
Integration Tests for Metrics Database Pipeline

Tests cover:
- End-to-end collection, storage, and querying flows
- Multi-source metrics collection
- Cache behavior across services
- Complete pipeline workflows
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.metrics_database import (
    MetricsCollector,
    MetricsQueryEngine,
    QuestDBConnector,
    MetricPoint,
    MetricType,
)


@pytest.fixture
def mock_questdb():
    """Create mock QuestDB connector for integration tests."""
    mock = AsyncMock(spec=QuestDBConnector)
    mock.insert_metrics_batch = AsyncMock(return_value=0)
    mock.query_metrics = AsyncMock(return_value=[])
    mock.get_statistics = AsyncMock(
        return_value={
            "min": Decimal("0"),
            "max": Decimal("100"),
            "avg": Decimal("50"),
            "stddev": Decimal("15"),
            "count": 1000,
        }
    )
    mock.health_check = AsyncMock(return_value=True)
    mock.connect = AsyncMock(return_value=True)
    return mock


class TestMetricsPipelineCollectAndStore:
    """Test collection and storage pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_collect_and_store(self, mock_questdb):
        """Test complete collect and store pipeline."""
        # Create collector with multiple sources
        collector = MetricsCollector(
            questdb_connector=mock_questdb,
            auto_flush=True,
        )

        # Register multiple metric sources
        async def portfolio_metrics():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                    portfolio_id="port_001",
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_VOLATILITY,
                    value=Decimal("0.15"),
                    portfolio_id="port_001",
                ),
            ]

        async def risk_metrics():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.RISK_ADJUSTMENT,
                    value=Decimal("1.2"),
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.LEVERAGE_FACTOR,
                    value=Decimal("2.0"),
                ),
            ]

        collector.register_metric_source("portfolio", portfolio_metrics)
        collector.register_metric_source("risk", risk_metrics)

        # Collect metrics
        result = await collector.collect_once()

        # Verify collection succeeded
        assert result.success is True
        assert result.metrics_collected == 4
        assert result.metrics_failed == 0

        # Verify metrics were flushed
        assert mock_questdb.insert_metrics_batch.called

    @pytest.mark.asyncio
    async def test_collect_store_multiple_cycles(self, mock_questdb):
        """Test multiple collection cycles."""
        collector = MetricsCollector(
            questdb_connector=mock_questdb,
            collection_interval_seconds=0.1,
            auto_flush=True,
        )

        cycle_count = 0

        async def test_metrics():
            nonlocal cycle_count
            cycle_count += 1
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal(str(0.01 * cycle_count)),
                )
            ]

        collector.register_metric_source("test", test_metrics)

        # Run multiple cycles
        for _ in range(3):
            result = await collector.collect_once()
            assert result.success is True

        assert cycle_count == 3


class TestMetricsPipelineQueryFlow:
    """Test querying pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_query_flow(self, mock_questdb):
        """Test complete query pipeline."""
        query_engine = MetricsQueryEngine(mock_questdb, cache_enabled=True)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        # Setup mock to return test data
        test_metrics = [
            MetricPoint(
                timestamp=start_time + timedelta(minutes=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )
            for i in range(60)
        ]
        mock_questdb.query_metrics.return_value = test_metrics

        # Query metrics
        results = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        assert len(results) == 60

        # Query latest
        mock_questdb.query_metrics.return_value = [test_metrics[-1]]
        latest = await query_engine.query_latest(
            metric_type=MetricType.PORTFOLIO_RETURN,
        )

        assert latest is not None
        assert latest.value == test_metrics[-1].value


class TestMetricsPipelineMultiMetricTypes:
    """Test pipeline with multiple metric types."""

    @pytest.mark.asyncio
    async def test_collect_multiple_metric_types(self, mock_questdb):
        """Test collecting different metric types."""
        collector = MetricsCollector(questdb_connector=mock_questdb)

        async def multi_source():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.POSITION_SIZE,
                    value=Decimal("1000"),
                    symbol="AAPL",
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.ORDER_COST,
                    value=Decimal("50"),
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.SLIPPAGE,
                    value=Decimal("0.01"),
                ),
            ]

        collector.register_metric_source("multi", multi_source)
        result = await collector.collect_once()

        assert result.metrics_collected == 4

    @pytest.mark.asyncio
    async def test_query_different_metric_types(self, mock_questdb):
        """Test querying different metric types."""
        query_engine = MetricsQueryEngine(mock_questdb)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        mock_questdb.query_metrics.return_value = [
            MetricPoint(
                timestamp=start_time,
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            )
        ]

        # Query different types
        for metric_type in [
            MetricType.PORTFOLIO_RETURN,
            MetricType.POSITION_SIZE,
            MetricType.ORDER_COST,
        ]:
            results = await query_engine.query_metric_range(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time,
            )
            assert isinstance(results, list)


class TestMetricsPipelineSymbolFiltering:
    """Test filtering by symbol."""

    @pytest.mark.asyncio
    async def test_collect_symbol_specific_metrics(self, mock_questdb):
        """Test collecting symbol-specific metrics."""
        collector = MetricsCollector(questdb_connector=mock_questdb)

        async def stock_metrics():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.POSITION_SIZE,
                    value=Decimal("1000"),
                    symbol="AAPL",
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.POSITION_SIZE,
                    value=Decimal("2000"),
                    symbol="MSFT",
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.POSITION_SIZE,
                    value=Decimal("1500"),
                    symbol="GOOGL",
                ),
            ]

        collector.register_metric_source("stocks", stock_metrics)
        result = await collector.collect_once()

        assert result.metrics_collected == 3

    @pytest.mark.asyncio
    async def test_query_symbol_filtered_metrics(self, mock_questdb):
        """Test querying with symbol filter."""
        query_engine = MetricsQueryEngine(mock_questdb)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        aapl_metrics = [
            MetricPoint(
                timestamp=start_time + timedelta(minutes=i),
                metric_type=MetricType.POSITION_SIZE,
                value=Decimal(str(1000 + i * 10)),
                symbol="AAPL",
            )
            for i in range(10)
        ]
        mock_questdb.query_metrics.return_value = aapl_metrics

        results = await query_engine.query_metric_range(
            metric_type=MetricType.POSITION_SIZE,
            start_time=start_time,
            end_time=end_time,
            symbol="AAPL",
        )

        assert len(results) == 10
        assert all(m.symbol == "AAPL" for m in results)


class TestMetricsPipelinePortfolioTracking:
    """Test portfolio-level metrics tracking."""

    @pytest.mark.asyncio
    async def test_collect_portfolio_metrics(self, mock_questdb):
        """Test collecting portfolio-level metrics."""
        collector = MetricsCollector(questdb_connector=mock_questdb)

        async def portfolio_data():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                    portfolio_id="port_001",
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_DRAWDOWN,
                    value=Decimal("-0.10"),
                    portfolio_id="port_001",
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_SHARPE,
                    value=Decimal("1.5"),
                    portfolio_id="port_001",
                ),
            ]

        collector.register_metric_source("portfolio", portfolio_data)
        result = await collector.collect_once()

        assert result.metrics_collected == 3

    @pytest.mark.asyncio
    async def test_query_portfolio_metrics(self, mock_questdb):
        """Test querying portfolio metrics."""
        query_engine = MetricsQueryEngine(mock_questdb)

        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()

        portfolio_data = [
            MetricPoint(
                timestamp=start_time + timedelta(hours=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.001 * (i + 1))),
                portfolio_id="port_001",
            )
            for i in range(24)
        ]
        mock_questdb.query_metrics.return_value = portfolio_data

        results = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
            portfolio_id="port_001",
        )

        assert len(results) == 24


class TestMetricsPipelineErrorRecovery:
    """Test error handling in pipeline."""

    @pytest.mark.asyncio
    async def test_collection_with_partial_failure(self, mock_questdb):
        """Test collection continues when one source fails."""
        collector = MetricsCollector(questdb_connector=mock_questdb)

        async def good_source():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                )
            ]

        async def bad_source():
            raise Exception("Source error")

        async def another_good_source():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_VOLATILITY,
                    value=Decimal("0.15"),
                )
            ]

        collector.register_metric_source("good1", good_source)
        collector.register_metric_source("bad", bad_source)
        collector.register_metric_source("good2", another_good_source)

        result = await collector.collect_once()

        # Should have collected from 2 good sources despite 1 failure
        assert result.metrics_collected == 2
        assert result.metrics_failed == 1
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_query_error_handling(self, mock_questdb):
        """Test query error handling."""
        query_engine = MetricsQueryEngine(mock_questdb)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        # Setup mock to raise error
        mock_questdb.query_metrics.side_effect = Exception("Query error")

        results = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        # Should return empty list on error
        assert results == []


class TestMetricsPipelineCacheIntegration:
    """Test caching across the pipeline."""

    @pytest.mark.asyncio
    async def test_query_cache_across_calls(self, mock_questdb):
        """Test cache efficiency across multiple queries."""
        query_engine = MetricsQueryEngine(mock_questdb, cache_enabled=True)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        test_metrics = [
            MetricPoint(
                timestamp=start_time + timedelta(minutes=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )
            for i in range(60)
        ]
        mock_questdb.query_metrics.return_value = test_metrics

        # Execute same query 5 times
        for _ in range(5):
            await query_engine.query_metric_range(
                metric_type=MetricType.PORTFOLIO_RETURN,
                start_time=start_time,
                end_time=end_time,
            )

        # Should only hit database once due to cache
        assert mock_questdb.query_metrics.call_count == 1


class TestMetricsPipelineDataIntegrity:
    """Test data integrity throughout pipeline."""

    @pytest.mark.asyncio
    async def test_metric_values_preserved(self, mock_questdb):
        """Test that metric values are preserved through pipeline."""
        collector = MetricsCollector(questdb_connector=mock_questdb, auto_flush=False)

        test_value = Decimal("123.45")

        async def source():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=test_value,
                    symbol="TEST",
                    portfolio_id="port_test",
                )
            ]

        collector.register_metric_source("test", source)
        result = await collector.collect_once()

        # Verify metric was preserved
        assert result.metrics_collected == 1
        assert len(collector._pending_metrics) == 1
        assert collector._pending_metrics[0].value == test_value
        assert collector._pending_metrics[0].symbol == "TEST"
        assert collector._pending_metrics[0].portfolio_id == "port_test"

    @pytest.mark.asyncio
    async def test_timestamp_ordering(self, mock_questdb):
        """Test that timestamps are preserved in order."""
        query_engine = MetricsQueryEngine(mock_questdb)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        # Create metrics with specific timestamps
        metrics = [
            MetricPoint(
                timestamp=start_time + timedelta(minutes=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )
            for i in range(10)
        ]
        mock_questdb.query_metrics.return_value = metrics

        results = await query_engine.query_metric_range(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=start_time,
            end_time=end_time,
        )

        # Verify timestamps are in order
        for i in range(len(results) - 1):
            assert results[i].timestamp <= results[i + 1].timestamp


class TestMetricsPipelinePerformance:
    """Test pipeline performance characteristics."""

    @pytest.mark.asyncio
    async def test_bulk_collection_performance(self, mock_questdb):
        """Test collection of many metrics."""
        collector = MetricsCollector(questdb_connector=mock_questdb)

        async def large_source():
            # Return 1000 metrics in one cycle
            return [
                MetricPoint(
                    timestamp=datetime.utcnow() + timedelta(seconds=i),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal(str(0.001 * (i % 100))),
                )
                for i in range(1000)
            ]

        collector.register_metric_source("bulk", large_source)
        result = await collector.collect_once()

        assert result.metrics_collected == 1000
        assert result.success is True

    @pytest.mark.asyncio
    async def test_downsample_large_results(self, mock_questdb):
        """Test downsampling large result sets."""
        query_engine = MetricsQueryEngine(mock_questdb)

        # Create 50,000 metrics
        large_dataset = [
            MetricPoint(
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.001 * (i % 100))),
            )
            for i in range(50000)
        ]

        downsampled = await query_engine.downsample_results(
            metrics=large_dataset,
            target_points=1000,
        )

        # Verify reasonable size
        assert len(downsampled) <= 1100
        # Verify first and last preserved
        assert downsampled[0] == large_dataset[0]
        assert downsampled[-1] == large_dataset[-1]
