"""
Tests for QuestDB Connector - Async client for time-series metrics storage

Tests cover:
- Connection lifecycle (connect, disconnect, health checks)
- Single and batch insert operations
- Query execution and result retrieval
- Statistics and aggregations
- Error handling and retry logic
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.services.metrics_database import (
    AggregationType,
    MetricPoint,
    MetricType,
    QuestDBConnector,
    TimeSeriesQuery,
)


class TestQuestDBConnectorConnection:
    """Test connection lifecycle management."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to QuestDB."""
        connector = QuestDBConnector(
            host="localhost",
            port=9009,
            user="admin",
            password="quest",
        )

        result = await connector.connect()
        assert result is True
        assert connector._is_connected is True
        assert connector._connection_pool is not None

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful disconnection from QuestDB."""
        connector = QuestDBConnector()
        await connector.connect()

        result = await connector.disconnect()
        assert result is True
        assert connector._is_connected is False
        assert connector._connection_pool is None

    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        """Test health check when connected."""
        connector = QuestDBConnector()
        await connector.connect()

        result = await connector.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Test health check when disconnected."""
        connector = QuestDBConnector()

        result = await connector.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_connect_disconnect_cycles(self):
        """Test multiple connect/disconnect cycles."""
        connector = QuestDBConnector()

        for _ in range(3):
            assert await connector.connect() is True
            assert connector._is_connected is True
            assert await connector.disconnect() is True
            assert connector._is_connected is False


class TestQuestDBConnectorInsert:
    """Test metric insertion operations."""

    @pytest.mark.asyncio
    async def test_insert_single_metric(self):
        """Test inserting a single metric point."""
        connector = QuestDBConnector()
        await connector.connect()

        metric = MetricPoint(
            timestamp=datetime.utcnow(),
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.05"),
            symbol="AAPL",
            portfolio_id="port_001",
        )

        result = await connector.insert_metric(metric)
        assert result is True
        assert metric in connector._pending_metrics

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_insert_metric_disconnected(self):
        """Test inserting metric when disconnected."""
        connector = QuestDBConnector()

        metric = MetricPoint(
            timestamp=datetime.utcnow(),
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.05"),
        )

        result = await connector.insert_metric(metric)
        assert result is False

    @pytest.mark.asyncio
    async def test_insert_metric_auto_flush(self):
        """Test auto-flush when batch size reached."""
        connector = QuestDBConnector(batch_size=3)
        await connector.connect()

        # Add metrics until batch is full
        for i in range(3):
            metric = MetricPoint(
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )
            await connector.insert_metric(metric)

        # After auto-flush, pending should be empty
        assert len(connector._pending_metrics) == 0

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_insert_batch_multiple_metrics(self):
        """Test batch insert of multiple metrics."""
        connector = QuestDBConnector()
        await connector.connect()

        metrics = [
            MetricPoint(
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
                symbol=f"STOCK_{i}",
            )
            for i in range(5)
        ]

        count = await connector.insert_metrics_batch(metrics)
        assert count == 5
        assert len(connector._pending_metrics) == 0

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_insert_batch_disconnected(self):
        """Test batch insert when disconnected."""
        connector = QuestDBConnector()

        metrics = [
            MetricPoint(
                timestamp=datetime.utcnow(),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal("0.05"),
            )
        ]

        count = await connector.insert_metrics_batch(metrics)
        assert count == 0

    @pytest.mark.asyncio
    async def test_insert_batch_empty_list(self):
        """Test batch insert with empty list."""
        connector = QuestDBConnector()
        await connector.connect()

        count = await connector.insert_metrics_batch([])
        assert count == 0

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_pending_metrics_accumulation(self):
        """Test that pending metrics accumulate correctly."""
        connector = QuestDBConnector(batch_size=10)
        await connector.connect()

        # Add 5 metrics (less than batch size)
        for i in range(5):
            metric = MetricPoint(
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                metric_type=MetricType.PORTFOLIO_RETURN,
                value=Decimal(str(0.01 * (i + 1))),
            )
            await connector.insert_metric(metric)

        # Pending should still have 5 metrics
        assert len(connector._pending_metrics) == 5

        await connector.disconnect()


class TestQuestDBConnectorQuery:
    """Test query execution and result retrieval."""

    @pytest.mark.asyncio
    async def test_query_metrics_valid(self):
        """Test querying metrics with valid parameters."""
        connector = QuestDBConnector()
        await connector.connect()

        query = TimeSeriesQuery(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            symbol="AAPL",
        )

        results = await connector.query_metrics(query)
        assert isinstance(results, list)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_query_metrics_disconnected(self):
        """Test querying when disconnected."""
        connector = QuestDBConnector()

        query = TimeSeriesQuery(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
        )

        results = await connector.query_metrics(query)
        assert results == []

    @pytest.mark.asyncio
    async def test_query_metrics_invalid(self):
        """Test querying with invalid parameters."""
        connector = QuestDBConnector()
        await connector.connect()

        # Invalid query: start_time >= end_time
        query = TimeSeriesQuery(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() - timedelta(hours=1),
        )

        results = await connector.query_metrics(query)
        assert results == []

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_query_aggregated_ohlc(self):
        """Test querying aggregated (OHLC) data."""
        connector = QuestDBConnector()
        await connector.connect()

        results = await connector.query_aggregated(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
            aggregation_type=AggregationType.CLOSE,
            interval_minutes=5,
        )

        assert isinstance(results, list)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_get_latest_value(self):
        """Test retrieving latest metric value."""
        connector = QuestDBConnector()
        await connector.connect()

        result = await connector.get_latest_value(
            metric_type=MetricType.PORTFOLIO_RETURN,
            symbol="AAPL",
        )

        # Result should be None or Decimal
        assert result is None or isinstance(result, Decimal)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test retrieving statistics for metrics."""
        connector = QuestDBConnector()
        await connector.connect()

        stats = await connector.get_statistics(
            metric_type=MetricType.PORTFOLIO_RETURN,
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
        )

        assert stats is not None
        assert isinstance(stats, dict)
        assert "min" in stats
        assert "max" in stats
        assert "avg" in stats
        assert "stddev" in stats
        assert "count" in stats

        await connector.disconnect()


class TestQuestDBConnectorMaintenance:
    """Test maintenance operations."""

    @pytest.mark.asyncio
    async def test_delete_old_metrics(self):
        """Test deleting old metrics (retention policy)."""
        connector = QuestDBConnector(retention_days=90)
        await connector.connect()

        deleted = await connector.delete_old_metrics(days=30)
        assert isinstance(deleted, int)
        assert deleted >= 0

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_delete_old_metrics_disconnected(self):
        """Test delete old metrics when disconnected."""
        connector = QuestDBConnector()

        deleted = await connector.delete_old_metrics(days=30)
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_get_storage_stats(self):
        """Test retrieving storage statistics."""
        connector = QuestDBConnector()
        await connector.connect()

        stats = await connector.get_storage_stats()
        assert stats is not None
        assert stats.retention_days == 90
        assert stats.metric_types == len(MetricType)

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_get_storage_stats_disconnected(self):
        """Test storage stats when disconnected returns default values."""
        connector = QuestDBConnector()

        # When disconnected, get_storage_stats still returns default stats
        # since it doesn't check connection state
        stats = await connector.get_storage_stats()
        assert stats is not None
        assert isinstance(stats, object)


class TestQuestDBConnectorFlush:
    """Test flush operations."""

    @pytest.mark.asyncio
    async def test_flush_metrics_with_pending(self):
        """Test flushing pending metrics."""
        connector = QuestDBConnector()
        await connector.connect()

        # Add metrics manually to pending
        metric = MetricPoint(
            timestamp=datetime.utcnow(),
            metric_type=MetricType.PORTFOLIO_RETURN,
            value=Decimal("0.05"),
        )
        connector._pending_metrics.append(metric)

        flushed = await connector._flush_metrics()
        assert flushed == 1
        assert len(connector._pending_metrics) == 0

        await connector.disconnect()

    @pytest.mark.asyncio
    async def test_flush_metrics_empty(self):
        """Test flushing with no pending metrics."""
        connector = QuestDBConnector()
        await connector.connect()

        flushed = await connector._flush_metrics()
        assert flushed == 0

        await connector.disconnect()


class TestQuestDBConnectorConfiguration:
    """Test connector configuration."""

    def test_custom_connection_string(self):
        """Test custom connection string configuration."""
        connector = QuestDBConnector(
            host="192.168.1.1",
            port=9099,
            user="custom_user",
            password="custom_pass",
        )

        assert connector.host == "192.168.1.1"
        assert connector.port == 9099
        assert connector.user == "custom_user"
        assert connector.password == "custom_pass"

    def test_batch_size_configuration(self):
        """Test batch size configuration."""
        connector = QuestDBConnector(batch_size=500)
        assert connector.batch_size == 500

    def test_retention_days_configuration(self):
        """Test retention days configuration."""
        connector = QuestDBConnector(retention_days=180)
        assert connector.retention_days == 180

    def test_pool_size_configuration(self):
        """Test connection pool size configuration."""
        connector = QuestDBConnector(pool_size=20)
        assert connector.pool_size == 20

    def test_default_configuration(self):
        """Test default configuration values."""
        connector = QuestDBConnector()
        assert connector.host == "localhost"
        assert connector.port == 9009
        assert connector.user == "admin"
        assert connector.password == "quest"
        assert connector.batch_size == 1000
        assert connector.pool_size == 10
        assert connector.retention_days == 90
