"""
Integration tests for TimeSyncMonitor.

Phase 2.7: Time Sync Monitor Integration Tests
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import pytest

from app.services.monitoring.time_sync_monitor import (
    TimeSyncConfig,
    TimeSyncMonitor,
    get_time_sync_monitor,
    reset_time_sync_monitor,
)


class TestTimeSyncMonitorIntegration:
    """Integration tests for TimeSyncMonitor."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_time_sync_monitor()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_time_sync_monitor()

    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self):
        """Test complete monitoring lifecycle: start -> monitor -> stop."""
        monitor = get_time_sync_monitor()

        # Start monitoring
        assert await monitor.start() is True
        assert monitor._is_monitoring is True

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Stop monitoring
        assert await monitor.stop() is True
        assert monitor._is_monitoring is False

    @pytest.mark.asyncio
    async def test_monitoring_with_callbacks(self):
        """Test monitoring with drift detection callbacks."""
        drift_events = []
        critical_events = []

        def on_drift(drift: float):
            drift_events.append(drift)

        def on_critical(drift: float):
            critical_events.append(drift)

        config = TimeSyncConfig(
            check_interval_seconds=0.1,  # Fast for testing
            drift_threshold_seconds=0.5,
            critical_threshold_seconds=2.0,
            on_drift_detected=on_drift,
            on_critical_drift=on_critical,
        )

        monitor = TimeSyncMonitor(config)

        # Start monitoring
        await monitor.start()

        # Let it run for a few checks
        await asyncio.sleep(0.5)

        # Stop monitoring
        await monitor.stop()

        # Note: Callbacks may or may not be called depending on actual system clock
        # This test mainly ensures the monitoring loop runs without errors

    @pytest.mark.asyncio
    async def test_multiple_force_checks(self):
        """Test performing multiple force checks."""
        monitor = get_time_sync_monitor()

        # Perform multiple force checks
        results = []
        for _ in range(3):
            result = await monitor.force_check()
            results.append(result)
            await asyncio.sleep(0.1)

        # All results should be dictionaries
        assert all(isinstance(r, dict) for r in results)

        # All results should have required fields
        required_fields = [
            "drift_seconds",
            "is_synced",
            "threshold",
            "ntp_server",
            "local_time",
            "ntp_time",
            "ntp_available",
        ]
        for result in results:
            for field in required_fields:
                assert field in result

    @pytest.mark.asyncio
    async def test_status_consistency(self):
        """Test that status remains consistent across checks."""
        monitor = get_time_sync_monitor()

        # Get initial status
        status1 = monitor.get_status()

        # Perform a check
        await monitor.check_time_drift()

        # Get status after check
        status2 = monitor.get_status()

        # Check counts should have increased
        assert status2.checks_total >= status1.checks_total

        # Status should be a TimeSyncStatus object
        assert isinstance(status2, type(status1))

    @pytest.mark.asyncio
    async def test_order_validation_sequence(self):
        """Test validating multiple orders in sequence."""
        monitor = get_time_sync_monitor()

        # Test orders
        orders = [
            {"symbol": "AAPL", "quantity": 100, "side": "buy"},
            {"symbol": "GOOGL", "quantity": 50, "side": "buy"},
            {"symbol": "MSFT", "quantity": 75, "side": "sell"},
        ]

        results = []
        for order in orders:
            result = await monitor.validate_order_timestamp(order)
            results.append(result)

        # All orders should be validated (assuming clock is synced)
        # If clock is not synced, all should be rejected
        assert all(isinstance(r, bool) for r in results)

        # If first passed, all should pass (same clock state)
        if results[0]:
            assert all(results)

    @pytest.mark.asyncio
    async def test_monitoring_with_actual_ntp(self):
        """Test monitoring with actual NTP servers (if available)."""
        monitor = get_time_sync_monitor()

        if not monitor.get_ntp_availability():
            pytest.skip("NTP not available")

        # Perform a real check
        drift = await monitor.check_time_drift()

        # Drift should be a number
        assert isinstance(drift, float)

        # Status should be updated
        status = monitor.get_status()
        assert status.checks_total > 0
        assert status.last_check is not None

    @pytest.mark.asyncio
    async def test_concurrent_monitoring_tasks(self):
        """Test that concurrent monitoring operations are handled correctly."""
        monitor = get_time_sync_monitor()

        # Start monitoring
        await monitor.start()

        # Run multiple concurrent checks
        tasks = [
            monitor.check_time_drift(),
            monitor.check_time_drift(),
            monitor.check_time_drift(),
        ]

        results = await asyncio.gather(*tasks)

        # All should complete
        assert len(results) == 3
        assert all(isinstance(r, float) for r in results)

        # Stop monitoring
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_status_serialization(self):
        """Test that status can be serialized to dict."""
        monitor = get_time_sync_monitor()

        # Get status
        status = monitor.get_status()

        # Convert to dict
        status_dict = status.to_dict()

        # Check required fields
        required_fields = [
            "is_synced",
            "drift_seconds",
            "local_time",
            "ntp_time",
            "ntp_server",
            "last_check",
            "checks_total",
            "checks_failed",
        ]

        for field in required_fields:
            assert field in status_dict
            assert status_dict[field] is not None or field in ["ntp_time", "ntp_server"]

        # ISO format strings should be parseable
        datetime.fromisoformat(status_dict["local_time"])
        if status_dict["ntp_time"]:
            datetime.fromisoformat(status_dict["ntp_time"])
        datetime.fromisoformat(status_dict["last_check"])

    @pytest.mark.asyncio
    async def test_monitor_restart(self):
        """Test restarting monitoring multiple times."""
        monitor = get_time_sync_monitor()

        # First start
        await monitor.start()
        assert monitor._is_monitoring is True
        await asyncio.sleep(0.1)
        await monitor.stop()
        assert monitor._is_monitoring is False

        # Second start
        await monitor.start()
        assert monitor._is_monitoring is True
        await asyncio.sleep(0.1)
        await monitor.stop()
        assert monitor._is_monitoring is False

        # Third start
        await monitor.start()
        assert monitor._is_monitoring is True
        await asyncio.sleep(0.1)
        await monitor.stop()
        assert monitor._is_monitoring is False

    @pytest.mark.asyncio
    async def test_threshold_configuration(self):
        """Test different threshold configurations."""
        # Strict config
        strict_config = TimeSyncConfig(
            drift_threshold_seconds=0.1,
            critical_threshold_seconds=0.5,
        )

        strict_monitor = TimeSyncMonitor(strict_config)

        # Lenient config
        lenient_config = TimeSyncConfig(
            drift_threshold_seconds=5.0,
            critical_threshold_seconds=10.0,
        )

        lenient_monitor = TimeSyncMonitor(lenient_config)

        # Both should have different thresholds
        assert strict_monitor.config.drift_threshold_seconds == 0.1
        assert lenient_monitor.config.drift_threshold_seconds == 5.0

        # Both should work independently
        await strict_monitor.check_time_drift()
        await lenient_monitor.check_time_drift()

        assert strict_monitor.get_status().checks_total == 1
        assert lenient_monitor.get_status().checks_total == 1


class TestTimeSyncMonitorMetrics:
    """Test metrics and reporting functionality."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_time_sync_monitor()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_time_sync_monitor()

    @pytest.mark.asyncio
    async def test_monitoring_metrics_collection(self):
        """Test that monitoring collects accurate metrics."""
        monitor = get_time_sync_monitor()

        # Perform several checks
        for _ in range(5):
            await monitor.check_time_drift()

        status = monitor.get_status()

        # Should have 5 total checks
        assert status.checks_total == 5

        # Get drift
        drift = monitor.get_drift_seconds()
        assert isinstance(drift, float)

        # Check sync status
        is_synced = monitor.is_synced()
        assert isinstance(is_synced, bool)

    @pytest.mark.asyncio
    async def test_error_counting(self):
        """Test that errors are counted correctly."""
        monitor = get_time_sync_monitor()

        # If NTP is not available, all checks should fail
        if not monitor.get_ntp_availability():
            await monitor.check_time_drift()
            status = monitor.get_status()

            # Failed checks should not increment (no NTP = assume synced)
            assert status.checks_failed == 0

    @pytest.mark.asyncio
    async def test_force_check_metrics(self):
        """Test metrics from force check."""
        monitor = get_time_sync_monitor()

        result = await monitor.force_check()

        # Result should contain all metrics
        assert "drift_seconds" in result
        assert "is_synced" in result
        assert "checks_total" not in result  # Not in force check result
        assert "checks_failed" not in result  # Not in force check result
