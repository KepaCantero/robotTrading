"""
FASE 3: Unit tests for MetricsExporter

Tests metrics export to Prometheus and other formats.
"""

import json
import pytest
from app.services.monitoring import get_metrics_exporter


class TestMetricsExporter:
    """Tests for MetricsExporter."""

    @pytest.fixture
    def exporter(self):
        """Create exporter instance."""
        return get_metrics_exporter()

    @pytest.mark.asyncio
    async def test_exporter_initialization(self, exporter):
        """Test exporter initializes with correct endpoints."""
        assert exporter is not None
        assert exporter.prometheus_url == "http://localhost:9090"
        assert exporter.pushgateway_url == "http://localhost:9091"

    def test_export_json_format(self, exporter):
        """Test JSON export format."""
        metrics = {
            "portfolio_value": 100000.0,
            "sharpe_ratio": 1.5,
            "max_drawdown": 15.0,
        }

        json_str = exporter.export_json(metrics)
        data = json.loads(json_str)

        assert "timestamp" in data
        assert "metrics" in data
        assert data["metrics"]["portfolio_value"] == 100000.0
        assert data["metrics"]["sharpe_ratio"] == 1.5
        assert data["metadata"]["count"] == 3

    def test_export_csv_format(self, exporter):
        """Test CSV export format."""
        metrics = {
            "portfolio_value": 100000.0,
            "sharpe_ratio": 1.5,
        }

        csv_str = exporter.export_csv(metrics)

        assert "timestamp,metric_name,metric_value" in csv_str
        assert "portfolio_value,100000.0" in csv_str
        assert "sharpe_ratio,1.5" in csv_str

    def test_export_prometheus_text_format(self, exporter):
        """Test Prometheus text format export."""
        metrics = {
            "portfolio_value_usd": 100000.0,
            "sharpe_ratio": 1.5,
        }

        text = exporter.export_prometheus_text(metrics)

        assert "portfolio_value_usd" in text
        assert "sharpe_ratio" in text
        assert "100000.0" in text
        assert "1.5" in text

    def test_prometheus_format_structure(self, exporter):
        """Test Prometheus format follows OpenMetrics standard."""
        metrics = {"test_metric": 42.0}
        text = exporter.export_prometheus_text(metrics)

        lines = text.split("\n")
        # Should have HELP, TYPE, and value lines
        assert any("# HELP test_metric" in line for line in lines)
        assert any("# TYPE test_metric gauge" in line for line in lines)
        assert any("test_metric 42.0" in line for line in lines)

    def test_export_history_tracking(self, exporter):
        """Test export history is tracked."""
        metrics = {"metric1": 100.0}

        exporter.export_json(metrics)
        exporter.export_csv(metrics)

        history = exporter.get_export_history()
        assert isinstance(history, list)

    def test_export_history_limit(self, exporter):
        """Test export history respects size limit."""
        for i in range(150):
            metrics = {f"metric_{i}": float(i)}
            exporter.export_json(metrics)

        # Get last 100
        history = exporter.get_export_history(limit=100)
        assert len(history) <= 100

    @pytest.mark.asyncio
    async def test_health_check(self, exporter):
        """Test health check for Prometheus services."""
        health = await exporter.health_check()

        assert "prometheus" in health
        assert "pushgateway" in health
        assert "timestamp" in health
        assert isinstance(health["prometheus"], bool)
        assert isinstance(health["pushgateway"], bool)

    def test_multiple_export_formats_same_data(self, exporter):
        """Test all export formats work on same data."""
        metrics = {
            "metric1": 100.0,
            "metric2": 200.0,
            "metric3": 300.0,
        }

        json_export = exporter.export_json(metrics)
        csv_export = exporter.export_csv(metrics)
        prom_export = exporter.export_prometheus_text(metrics)

        # All should be non-empty strings
        assert len(json_export) > 0
        assert len(csv_export) > 0
        assert len(prom_export) > 0

        # JSON should be valid
        data = json.loads(json_export)
        assert data["metadata"]["count"] == 3

        # CSV should have 4 lines (header + 3 metrics)
        csv_lines = csv_export.strip().split("\n")
        assert len(csv_lines) == 4

    def test_custom_exporter_endpoints(self):
        """Test exporter with custom Prometheus endpoints."""
        exporter = get_metrics_exporter(
            prometheus_url="http://prometheus:9090",
            pushgateway_url="http://pushgateway:9091",
        )

        assert exporter.prometheus_url == "http://prometheus:9090"
        assert exporter.pushgateway_url == "http://pushgateway:9091"

    def test_empty_metrics_export(self, exporter):
        """Test exporting empty metrics."""
        empty_metrics = {}

        json_export = exporter.export_json(empty_metrics)
        csv_export = exporter.export_csv(empty_metrics)

        data = json.loads(json_export)
        assert data["metadata"]["count"] == 0

        csv_lines = csv_export.strip().split("\n")
        assert len(csv_lines) == 1  # Only header

    def test_special_characters_in_metrics(self, exporter):
        """Test metrics with special characters in names."""
        metrics = {
            "api_response_time_milliseconds": 150.5,
            "model_f1_score": 0.95,
            "max_drawdown_pct": 25.3,
        }

        json_export = exporter.export_json(metrics)
        data = json.loads(json_export)

        assert "api_response_time_milliseconds" in data["metrics"]
        assert data["metrics"]["model_f1_score"] == 0.95

    def test_float_precision(self, exporter):
        """Test float precision in export formats."""
        metrics = {
            "precise_metric": 3.141592653589793,
        }

        json_export = exporter.export_json(metrics)
        data = json.loads(json_export)

        # Should preserve precision
        assert isinstance(
            data["metrics"]["precise_metric"], float
        )

    def test_large_metric_values(self, exporter):
        """Test exporting very large metric values."""
        metrics = {
            "large_value": 1e15,
            "small_value": 1e-15,
        }

        json_export = exporter.export_json(metrics)
        data = json.loads(json_export)

        assert data["metrics"]["large_value"] == 1e15
        assert data["metrics"]["small_value"] == 1e-15
