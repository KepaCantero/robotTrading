"""
Tests for Metrics Collector - Centralized metrics collection from all monitors

Tests cover:
- Metric source registration
- Single collection cycles
- Continuous collection loops
- Manual flushing
- Error handling and statistics
"""

import asyncio
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.metrics_database import (
    MetricsCollector,
    QuestDBConnector,
    MetricPoint,
    MetricType,
)


@pytest.fixture
def mock_questdb():
    """Create mock QuestDB connector."""
    mock = AsyncMock(spec=QuestDBConnector)
    mock.insert_metrics_batch = AsyncMock(return_value=5)
    mock.health_check = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def metrics_collector(mock_questdb):
    """Create MetricsCollector with mock QuestDB."""
    return MetricsCollector(
        questdb_connector=mock_questdb,
        collection_interval_seconds=1,
        auto_flush=True,
    )


class TestMetricsCollectorRegistration:
    """Test metric source registration."""

    def test_register_single_source(self, metrics_collector):
        """Test registering a single metric source."""
        async def collect_func():
            return []

        metrics_collector.register_metric_source("test_source", collect_func)
        assert "test_source" in metrics_collector._metric_sources
        assert metrics_collector._metric_sources["test_source"] == collect_func

    def test_register_multiple_sources(self, metrics_collector):
        """Test registering multiple metric sources."""
        async def collect_func1():
            return []

        async def collect_func2():
            return []

        metrics_collector.register_metric_source("source1", collect_func1)
        metrics_collector.register_metric_source("source2", collect_func2)

        assert len(metrics_collector._metric_sources) == 2
        assert "source1" in metrics_collector._metric_sources
        assert "source2" in metrics_collector._metric_sources

    def test_register_overwrites_existing(self, metrics_collector):
        """Test that registering overwrites existing source."""
        async def collect_func1():
            return []

        async def collect_func2():
            return []

        metrics_collector.register_metric_source("same_source", collect_func1)
        metrics_collector.register_metric_source("same_source", collect_func2)

        assert len(metrics_collector._metric_sources) == 1
        assert metrics_collector._metric_sources["same_source"] == collect_func2


class TestMetricsCollectorCollection:
    """Test metric collection operations."""

    @pytest.mark.asyncio
    async def test_collect_once_no_sources(self, metrics_collector):
        """Test collection cycle with no registered sources."""
        result = await metrics_collector.collect_once()

        assert result.success is True
        assert result.metrics_collected == 0
        assert result.metrics_failed == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_collect_once_single_source(self, metrics_collector):
        """Test collection cycle with single source."""
        metrics = [
            MetricPoint(
                timestamp=datetime.utcnow(),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            ),
            MetricPoint(
                timestamp=datetime.utcnow(),
                metric_type=MetricType.PORTFOLIO_VOLATILITY,
                value=Decimal("0.15"),
            ),
        ]

        async def collect_func():
            return metrics

        metrics_collector.register_metric_source("test_source", collect_func)
        result = await metrics_collector.collect_once()

        assert result.success is True
        assert result.metrics_collected == 2
        assert result.metrics_failed == 0

    @pytest.mark.asyncio
    async def test_collect_once_multiple_sources(self, metrics_collector):
        """Test collection cycle with multiple sources."""
        async def collect_func1():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                )
            ]

        async def collect_func2():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_VOLATILITY,
                    value=Decimal("0.15"),
                )
            ]

        metrics_collector.register_metric_source("source1", collect_func1)
        metrics_collector.register_metric_source("source2", collect_func2)

        result = await metrics_collector.collect_once()

        assert result.success is True
        assert result.metrics_collected == 2

    @pytest.mark.asyncio
    async def test_collect_once_with_error(self, metrics_collector):
        """Test collection with source error."""
        async def good_func():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                )
            ]

        async def bad_func():
            raise ValueError("Collection error")

        metrics_collector.register_metric_source("good", good_func)
        metrics_collector.register_metric_source("bad", bad_func)

        result = await metrics_collector.collect_once()

        assert result.success is False
        assert result.metrics_collected == 1
        assert result.metrics_failed == 1
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_collect_once_auto_flush(self, metrics_collector):
        """Test auto-flush during collection."""
        async def collect_func():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                )
            ]

        metrics_collector.register_metric_source("test", collect_func)
        await metrics_collector.collect_once()

        # Verify auto-flush was called
        metrics_collector.questdb.insert_metrics_batch.assert_called()

    @pytest.mark.asyncio
    async def test_collect_once_no_auto_flush(self, mock_questdb):
        """Test collection without auto-flush."""
        collector = MetricsCollector(
            questdb_connector=mock_questdb,
            auto_flush=False,
        )

        async def collect_func():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                )
            ]

        collector.register_metric_source("test", collect_func)
        await collector.collect_once()

        # Verify auto-flush was NOT called
        mock_questdb.insert_metrics_batch.assert_not_called()


class TestMetricsCollectorContinuous:
    """Test continuous collection operations."""

    @pytest.mark.asyncio
    async def test_continuous_collection_start_stop(self, metrics_collector):
        """Test starting and stopping continuous collection."""
        assert metrics_collector._collection_running is False

        await metrics_collector.start_continuous_collection()
        assert metrics_collector._collection_running is True

        await metrics_collector.stop_continuous_collection()
        assert metrics_collector._collection_running is False

    @pytest.mark.asyncio
    async def test_continuous_collection_already_running(self, metrics_collector):
        """Test starting when already running."""
        await metrics_collector.start_continuous_collection()
        # Try to start again - should return early
        await metrics_collector.start_continuous_collection()

        assert metrics_collector._collection_running is True

    @pytest.mark.asyncio
    async def test_continuous_collection_not_running(self, metrics_collector):
        """Test stopping when not running."""
        # Should not raise error
        await metrics_collector.stop_continuous_collection()

    @pytest.mark.asyncio
    async def test_continuous_collection_loop(self, metrics_collector):
        """Test continuous collection loop executes."""
        call_count = 0

        async def collect_func():
            nonlocal call_count
            call_count += 1
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                )
            ]

        metrics_collector.register_metric_source("test", collect_func)
        metrics_collector.collection_interval_seconds = 0.1

        await metrics_collector.start_continuous_collection()
        await asyncio.sleep(0.25)  # Allow at least 2 cycles
        await metrics_collector.stop_continuous_collection()

        assert call_count >= 2


class TestMetricsCollectorFlushing:
    """Test flushing operations."""

    @pytest.mark.asyncio
    async def test_flush_metrics_with_pending(self, metrics_collector, mock_questdb):
        """Test flushing pending metrics."""
        # Configure mock to return the count of metrics passed
        mock_questdb.insert_metrics_batch = AsyncMock(side_effect=lambda metrics: len(metrics))

        # Add metrics to pending
        for i in range(3):
            metrics_collector._pending_metrics.append(
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal(str(0.01 * (i + 1))),
                )
            )

        flushed = await metrics_collector.flush_metrics()
        assert flushed == 3
        assert len(metrics_collector._pending_metrics) == 0

    @pytest.mark.asyncio
    async def test_flush_metrics_empty(self, metrics_collector):
        """Test flushing with no pending metrics."""
        flushed = await metrics_collector.flush_metrics()
        assert flushed == 0

    @pytest.mark.asyncio
    async def test_flush_metrics_error(self, metrics_collector):
        """Test flushing with database error."""
        metrics_collector.questdb.insert_metrics_batch = AsyncMock(
            side_effect=Exception("DB Error")
        )

        metrics_collector._pending_metrics.append(
            MetricPoint(
                timestamp=datetime.utcnow(),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            )
        )

        flushed = await metrics_collector.flush_metrics()
        assert flushed == 0


class TestMetricsCollectorManualAdd:
    """Test manual metric addition."""

    def test_add_metric_simple(self, metrics_collector):
        """Test adding a simple metric."""
        metrics_collector.add_metric(
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.05"),
        )

        assert len(metrics_collector._pending_metrics) == 1
        metric = metrics_collector._pending_metrics[0]
        assert metric.metric_type == MetricType.PORTFOLIO_RETURN
        assert metric.value == Decimal("0.05")

    def test_add_metric_with_symbol(self, metrics_collector):
        """Test adding metric with symbol."""
        metrics_collector.add_metric(
            metric_type=MetricType.POSITION_SIZE,
            value=Decimal("1000"),
            symbol="AAPL",
        )

        metric = metrics_collector._pending_metrics[0]
        assert metric.symbol == "AAPL"

    def test_add_metric_with_portfolio_id(self, metrics_collector):
        """Test adding metric with portfolio ID."""
        metrics_collector.add_metric(
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.05"),
            portfolio_id="port_001",
        )

        metric = metrics_collector._pending_metrics[0]
        assert metric.portfolio_id == "port_001"

    def test_add_metric_with_tags(self, metrics_collector):
        """Test adding metric with tags."""
        tags = {"strategy": "momentum", "tier": "large"}
        metrics_collector.add_metric(
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.05"),
            tags=tags,
        )

        metric = metrics_collector._pending_metrics[0]
        assert metric.tags == tags

    def test_add_multiple_metrics(self, metrics_collector):
        """Test adding multiple metrics."""
        for i in range(5):
            metrics_collector.add_metric(
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )

        assert len(metrics_collector._pending_metrics) == 5


class TestMetricsCollectorStatistics:
    """Test statistics and monitoring."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, metrics_collector):
        """Test retrieving collector statistics."""
        # Add some metrics
        for i in range(3):
            metrics_collector.add_metric(
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )

        metrics_collector._total_collected = 10
        metrics_collector._total_stored = 8
        metrics_collector._total_errors = 2

        stats = await metrics_collector.get_statistics()

        assert stats["total_collected"] == 10
        assert stats["total_stored"] == 8
        assert stats["total_errors"] == 2
        assert stats["pending_metrics"] == 3
        assert stats["collection_running"] is False

    @pytest.mark.asyncio
    async def test_health_check(self, metrics_collector):
        """Test health check."""
        result = await metrics_collector.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_db_failure(self, metrics_collector):
        """Test health check with DB failure."""
        metrics_collector.questdb.health_check = AsyncMock(return_value=False)

        result = await metrics_collector.health_check()
        assert result is False


class TestMetricsCollectorIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_register_and_collect_multiple_sources(self, metrics_collector):
        """Test registering and collecting from multiple sources."""
        async def portfolio_metrics():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                ),
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_VOLATILITY,
                    value=Decimal("0.15"),
                ),
            ]

        async def position_metrics():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.POSITION_PNL,
                    value=Decimal("500"),
                    symbol="AAPL",
                ),
            ]

        async def risk_metrics():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.RISK_ADJUSTMENT,
                    value=Decimal("1.2"),
                ),
            ]

        metrics_collector.register_metric_source("portfolio", portfolio_metrics)
        metrics_collector.register_metric_source("positions", position_metrics)
        metrics_collector.register_metric_source("risk", risk_metrics)

        result = await metrics_collector.collect_once()

        assert result.success is True
        assert result.metrics_collected == 4

    @pytest.mark.asyncio
    async def test_sync_collector_function(self, metrics_collector):
        """Test with synchronous collector function."""

        def sync_collect():
            return [
                MetricPoint(
                    timestamp=datetime.utcnow(),
                    metric_type=MetricType.PORTFOLIO_RETURN,
                    value=Decimal("0.05"),
                )
            ]

        metrics_collector.register_metric_source("sync", sync_collect)
        result = await metrics_collector.collect_once()

        assert result.success is True
        assert result.metrics_collected == 1


class TestMetricsCollectorConfiguration:
    """Test collector configuration."""

    def test_collection_interval_configuration(self):
        """Test collection interval configuration."""
        mock_db = AsyncMock(spec=QuestDBConnector)
        collector = MetricsCollector(
            questdb_connector=mock_db,
            collection_interval_seconds=30,
        )

        assert collector.collection_interval_seconds == 30

    def test_auto_flush_configuration(self):
        """Test auto-flush configuration."""
        mock_db = AsyncMock(spec=QuestDBConnector)
        collector_with_flush = MetricsCollector(
            questdb_connector=mock_db,
            auto_flush=True,
        )
        collector_without_flush = MetricsCollector(
            questdb_connector=mock_db,
            auto_flush=False,
        )

        assert collector_with_flush.auto_flush is True
        assert collector_without_flush.auto_flush is False
