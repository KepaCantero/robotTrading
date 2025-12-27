"""
FASE 3: Unit tests for PrometheusMetricsCollector

Tests metric collection, storage, and export functionality.
"""

import pytest
from app.services.monitoring import get_prometheus_collector, MetricType


class TestPrometheusMetricsCollector:
    """Tests for PrometheusMetricsCollector."""

    @pytest.fixture
    def collector(self):
        """Create collector instance."""
        return get_prometheus_collector()

    def test_collector_initialization(self, collector):
        """Test collector initializes with standard metrics."""
        assert collector is not None
        assert len(collector.metrics) > 20  # At least 20 standard metrics
        assert "portfolio_value_usd" in collector.metrics
        assert "trades_executed_total" in collector.metrics
        assert "sharpe_ratio" in collector.metrics

    def test_set_gauge_metric(self, collector):
        """Test setting gauge metric values."""
        success = collector.set_gauge("portfolio_value_usd", 100000.0)
        assert success is True

        value = collector.get_metric_value("portfolio_value_usd")
        assert value == 100000.0

    def test_set_gauge_with_labels(self, collector):
        """Test gauge with dimension labels."""
        labels = {"symbol": "AAPL", "account_id": "acc_001"}
        success = collector.set_gauge("portfolio_value_usd", 50000.0, labels)
        assert success is True

        value = collector.get_metric_value("portfolio_value_usd", labels)
        assert value == 50000.0

    def test_increment_counter(self, collector):
        """Test incrementing counter metrics."""
        success = collector.increment_counter("trades_executed_total", 1.0)
        assert success is True

        # Increment again
        collector.increment_counter("trades_executed_total", 1.0)
        value = collector.get_metric_value("trades_executed_total")
        assert value == 2.0

    def test_increment_counter_default_value(self, collector):
        """Test counter increment with default value of 1."""
        collector.increment_counter("winning_trades_total")
        value = collector.get_metric_value("winning_trades_total")
        assert value == 1.0

    def test_observe_histogram(self, collector):
        """Test recording histogram observations."""
        for i in range(10):
            collector.observe_histogram(
                "api_response_time_milliseconds", float(i * 100)
            )

        value = collector.get_metric_value("api_response_time_milliseconds")
        assert value == 10.0  # Count of observations

    def test_invalid_metric_type(self, collector):
        """Test error handling for wrong metric type."""
        # Try to increment gauge (should fail)
        success = collector.increment_counter("portfolio_value_usd", 1000.0)
        assert success is False

    def test_nonexistent_metric(self, collector):
        """Test handling of nonexistent metrics."""
        success = collector.set_gauge("nonexistent_metric", 100.0)
        assert success is False

        value = collector.get_metric_value("nonexistent_metric")
        assert value is None

    def test_prometheus_format_export(self, collector):
        """Test Prometheus text format export."""
        collector.set_gauge("portfolio_value_usd", 100000.0)
        collector.set_gauge("total_return_pct", 15.5)

        prometheus_text = collector.export_prometheus_format()
        assert "portfolio_value_usd" in prometheus_text
        assert "total_return_pct" in prometheus_text
        assert "HELP" in prometheus_text
        assert "TYPE" in prometheus_text

    def test_metrics_summary(self, collector):
        """Test metrics summary information."""
        collector.set_gauge("portfolio_value_usd", 100000.0)

        summary = collector.get_metrics_summary()
        assert summary["total_metrics"] > 20
        assert "metrics_by_type" in summary
        assert "gauge" in summary["metrics_by_type"]
        assert "counter" in summary["metrics_by_type"]

    def test_reset_metrics(self, collector):
        """Test resetting all metrics."""
        collector.set_gauge("portfolio_value_usd", 100000.0)
        collector.increment_counter("trades_executed_total", 5.0)

        collector.reset_metrics()

        value1 = collector.get_metric_value("portfolio_value_usd")
        value2 = collector.get_metric_value("trades_executed_total")
        assert value1 is None
        assert value2 is None

    def test_multiple_label_combinations(self, collector):
        """Test same metric with different label combinations."""
        labels1 = {"strategy": "momentum"}
        labels2 = {"strategy": "mean_reversion"}

        collector.set_gauge("sharpe_ratio", 1.5, labels1)
        collector.set_gauge("sharpe_ratio", 0.8, labels2)

        value1 = collector.get_metric_value("sharpe_ratio", labels1)
        value2 = collector.get_metric_value("sharpe_ratio", labels2)

        assert value1 == 1.5
        assert value2 == 0.8

    def test_histogram_bucket_calculation(self, collector):
        """Test histogram bucket calculation."""
        values = [0.05, 0.5, 1.5, 5.5, 10.5, 50.5]
        for v in values:
            collector.observe_histogram("backtest_duration_seconds", v)

        prometheus_text = collector.export_prometheus_format()
        assert "backtest_duration_seconds_bucket" in prometheus_text
        assert 'le="1"' in prometheus_text  # One of the buckets
        assert 'le="+Inf"' in prometheus_text  # Infinity bucket
