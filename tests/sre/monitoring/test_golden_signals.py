"""
Tests for Golden Signals Monitoring Module.

Tests the implementation of Google SRE's golden signals:
- Latency monitoring
- Traffic tracking
- Error rate calculation
- Saturation measurement
- SLO compliance checking
- Health status evaluation
"""

import asyncio
from decimal import Decimal

import pytest

from app.sre.monitoring import (
    GoldenSignalsConfig,
    GoldenSignalsMonitor,
    HealthStatus,
    LatencyCollector,
    RequestTracker,
    SignalType,
    SLOTarget,
    get_golden_signals_monitor,
)


class TestRequestTracker:
    """Test request tracking functionality."""

    @pytest.fixture
    def tracker(self):
        """Create a request tracker."""
        return RequestTracker(window_seconds=60)

    def test_record_request_success(self, tracker):
        """Test recording successful requests."""
        tracker.record_request(success=True)
        total, errors, types = asyncio.run(tracker.get_metrics())

        assert total == 1
        assert errors == 0
        assert types == {}

    def test_record_request_failure(self, tracker):
        """Test recording failed requests."""
        tracker.record_request(success=False, error_type="timeout")
        total, errors, types = asyncio.run(tracker.get_metrics())

        assert total == 1
        assert errors == 1
        assert types == {"timeout": 1}

    def test_window_cleanup(self, tracker):
        """Test that old requests are cleaned up."""
        # Record requests with old timestamps
        tracker._requests.append(0)  # Very old timestamp
        tracker._errors.append(0)

        # Record recent request
        tracker.record_request(success=True)

        total, errors, types = asyncio.run(tracker.get_metrics())

        # Only recent request should count
        assert total == 1
        assert errors == 0


class TestLatencyCollector:
    """Test latency collection functionality."""

    @pytest.fixture
    def collector(self):
        """Create a latency collector."""
        return LatencyCollector(sample_size=100)

    def test_record_latency(self, collector):
        """Test recording latency measurements."""
        collector.record_latency(100.0)
        collector.record_latency(200.0)
        collector.record_latency(150.0)

        metrics = asyncio.run(collector.get_metrics())

        assert metrics is not None
        assert metrics.mean_ms == 150.0
        assert metrics.p50_ms == 150.0  # Median

    def test_percentile_calculation(self, collector):
        """Test percentile calculation."""
        # Record 100 measurements
        for i in range(100):
            collector.record_latency(float(i * 10))

        metrics = asyncio.run(collector.get_metrics())

        assert metrics.p50_ms == 495.0  # Approx median
        assert metrics.p95_ms == 940.0  # Approx 95th percentile
        assert metrics.p99_ms == 989.0  # Approx 99th percentile

    def test_max_sample_size(self, collector):
        """Test that collector respects max sample size."""
        # Record more than sample_size
        for i in range(200):
            collector.record_latency(float(i))

        asyncio.run(collector.get_metrics())

        # Should only keep last 100 samples
        assert len(collector._latencies) == 100


class TestSLOTarget:
    """Test SLO target functionality."""

    def test_slo_compliance_less_than(self):
        """Test SLO compliance with less than operator."""
        slo = SLOTarget(
            signal_type=SignalType.LATENCY,
            metric_name="p95_ms",
            target_value=Decimal("500"),
            comparison_op="lt",
            window_minutes=5,
            description="Test SLO",
        )

        assert slo.is_compliant(400.0) is True
        assert slo.is_compliant(500.0) is False
        assert slo.is_compliant(600.0) is False

    def test_slo_compliance_less_than_equal(self):
        """Test SLO compliance with less than or equal operator."""
        slo = SLOTarget(
            signal_type=SignalType.LATENCY,
            metric_name="p95_ms",
            target_value=Decimal("500"),
            comparison_op="lte",
            window_minutes=5,
            description="Test SLO",
        )

        assert slo.is_compliant(400.0) is True
        assert slo.is_compliant(500.0) is True
        assert slo.is_compliant(600.0) is False

    def test_slo_compliance_greater_than(self):
        """Test SLO compliance with greater than operator."""
        slo = SLOTarget(
            signal_type=SignalType.TRAFFIC,
            metric_name="requests_per_second",
            target_value=Decimal("100"),
            comparison_op="gt",
            window_minutes=5,
            description="Test SLO",
        )

        assert slo.is_compliant(150.0) is True
        assert slo.is_compliant(100.0) is False
        assert slo.is_compliant(50.0) is False


@pytest.mark.asyncio
class TestGoldenSignalsMonitor:
    """Test golden signals monitor functionality."""

    @pytest.fixture
    async def monitor(self):
        """Create a monitor instance."""
        config = GoldenSignalsConfig(
            service_name="test-service",
            collection_interval_seconds=1,
        )
        monitor = GoldenSignalsMonitor(service_name="test-service", config=config)
        await monitor.initialize()
        yield monitor
        await monitor.stop_collection()

    async def test_initialize(self, monitor):
        """Test monitor initialization."""
        assert monitor.service_name == "test-service"
        assert monitor._current_health == HealthStatus.HEALTHY

    async def test_record_request(self, monitor):
        """Test recording requests."""
        monitor.record_request(success=True)
        monitor.record_request(success=False, error_type="timeout")

        total, errors, types = await monitor._request_tracker.get_metrics()

        assert total == 2
        assert errors == 1
        assert "timeout" in types

    async def test_record_latency(self, monitor):
        """Test recording latency."""
        monitor.record_latency(100.0)
        monitor.record_latency(200.0)

        metrics = await monitor._latency_collector.get_metrics()

        assert metrics is not None
        assert metrics.mean_ms == 150.0

    async def test_collect_metrics(self, monitor):
        """Test collecting all metrics."""
        # Record some data
        for i in range(10):
            monitor.record_latency(100.0 + i * 10)
            monitor.record_request(success=True)

        metrics = await monitor.collect_metrics()

        assert metrics.service_name == "test-service"
        assert metrics.latency.p50_ms > 0
        assert metrics.traffic.requests_per_second > 0
        assert isinstance(metrics.errors.error_rate_pct, float)
        assert metrics.saturation.cpu_usage_pct >= 0

    async def test_health_evaluation_healthy(self, monitor):
        """Test health evaluation when system is healthy."""
        # Record normal latencies
        for _ in range(10):
            monitor.record_latency(100.0)
            monitor.record_request(success=True)

        metrics = await monitor.collect_metrics()

        assert metrics.overall_health == HealthStatus.HEALTHY

    async def test_health_evaluation_warning(self, monitor):
        """Test health evaluation when system has warnings."""
        # Record high latencies
        for _ in range(10):
            monitor.record_latency(600.0)  # Above warning threshold
            monitor.record_request(success=True)

        metrics = await monitor.collect_metrics()

        # Should be at least warning due to high latency
        assert metrics.overall_health in [HealthStatus.WARNING, HealthStatus.DEGRADED]

    async def test_get_current_metrics(self, monitor):
        """Test getting current metrics."""
        # Record some data
        monitor.record_latency(150.0)
        monitor.record_request(success=True)

        await monitor.collect_metrics()

        current = await monitor.get_current_metrics()

        assert current is not None
        assert current.service_name == "test-service"

    async def test_get_metrics_history(self, monitor):
        """Test getting metrics history."""
        # Collect multiple metrics
        for _ in range(3):
            await monitor.collect_metrics()

        history = await monitor.get_metrics_history(limit=2)

        assert len(history) == 2

    async def test_get_metrics_summary(self, monitor):
        """Test getting metrics summary."""
        monitor.record_latency(150.0)
        monitor.record_request(success=True)
        await monitor.collect_metrics()

        summary = await monitor.get_metrics_summary()

        assert summary["service"] == "test-service"
        assert "health_status" in summary
        assert "latency" in summary
        assert "traffic" in summary
        assert "errors" in summary
        assert "saturation" in summary

    async def test_slo_compliance_checking(self, monitor):
        """Test SLO compliance checking."""
        monitor.record_latency(400.0)  # Should meet default SLO
        monitor.record_request(success=True)
        await monitor.collect_metrics()

        compliance = await monitor.check_slo_compliance()

        assert isinstance(compliance, dict)
        # At least latency SLO should be checked
        assert len(compliance) > 0


class TestMonitorSingleton:
    """Test monitor singleton pattern."""

    def test_get_singleton(self):
        """Test getting singleton instance."""
        monitor1 = get_golden_signals_monitor("test-service-1")
        monitor2 = get_golden_signals_monitor("test-service-1")

        # Same service should return same instance
        assert monitor1 is monitor2

    def test_different_services(self):
        """Test that different services get different instances."""
        monitor1 = get_golden_signals_monitor("service-1")
        monitor2 = get_golden_signals_monitor("service-2")

        # Different services should get different instances
        assert monitor1 is not monitor2
        assert monitor1.service_name == "service-1"
        assert monitor2.service_name == "service-2"


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for golden signals monitoring."""

    async def test_full_workflow(self):
        """Test complete monitoring workflow."""
        # Create monitor
        config = GoldenSignalsConfig(
            service_name="integration-test",
            collection_interval_seconds=1,
        )
        monitor = get_golden_signals_monitor("integration-test", config)
        await monitor.initialize()

        # Start collection
        await monitor.start_collection()

        # Simulate activity
        for i in range(20):
            monitor.record_latency(100.0 + i * 5)
            monitor.record_request(success=(i % 5 != 0))

        # Wait for collection
        await asyncio.sleep(2)

        # Get metrics
        metrics = await monitor.get_current_metrics()
        assert metrics is not None

        # Get summary
        summary = await monitor.get_metrics_summary()
        assert summary["service"] == "integration-test"

        # Check compliance
        compliance = await monitor.check_slo_compliance()
        assert isinstance(compliance, dict)

        # Stop collection
        await monitor.stop_collection()

        # Clean up
        del monitor._monitors["integration-test"]
