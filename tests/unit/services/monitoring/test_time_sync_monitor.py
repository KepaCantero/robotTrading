"""
Unit tests for TimeSyncMonitor.

Phase 2.7: Time Sync Monitor Tests
"""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional

import pytest

from app.services.monitoring.time_sync_monitor import (
    TimeSyncConfig,
    TimeSyncMonitor,
    TimeSyncStatus,
    get_time_sync_monitor,
    reset_time_sync_monitor,
    NTP_SERVERS,
)


class TestTimeSyncConfig:
    """Test TimeSyncConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TimeSyncConfig()

        assert config.check_interval_seconds == 60.0
        assert config.drift_threshold_seconds == 1.0
        assert config.critical_threshold_seconds == 5.0
        assert config.max_retries == 3
        assert config.timeout_seconds == 5.0
        assert config.on_drift_detected is None
        assert config.on_critical_drift is None
        assert config.on_sync_error is None

    def test_custom_config(self):
        """Test custom configuration values."""
        callback = Mock()

        config = TimeSyncConfig(
            check_interval_seconds=30.0,
            drift_threshold_seconds=0.5,
            critical_threshold_seconds=2.0,
            max_retries=5,
            timeout_seconds=10.0,
            on_drift_detected=callback,
        )

        assert config.check_interval_seconds == 30.0
        assert config.drift_threshold_seconds == 0.5
        assert config.critical_threshold_seconds == 2.0
        assert config.max_retries == 5
        assert config.timeout_seconds == 10.0
        assert config.on_drift_detected == callback


class TestTimeSyncStatus:
    """Test TimeSyncStatus dataclass."""

    def test_status_creation(self):
        """Test creating a status object."""
        now = datetime.now(timezone.utc)

        status = TimeSyncStatus(
            is_synced=True,
            drift_seconds=0.1,
            local_time=now,
            ntp_time=now,
            ntp_server="pool.ntp.org",
            last_check=now,
            checks_total=10,
            checks_failed=1,
        )

        assert status.is_synced is True
        assert status.drift_seconds == 0.1
        assert status.local_time == now
        assert status.ntp_time == now
        assert status.ntp_server == "pool.ntp.org"
        assert status.last_check == now
        assert status.checks_total == 10
        assert status.checks_failed == 1

    def test_status_to_dict(self):
        """Test converting status to dictionary."""
        now = datetime.now(timezone.utc)

        status = TimeSyncStatus(
            is_synced=True,
            drift_seconds=0.1,
            local_time=now,
            ntp_time=now,
            ntp_server="pool.ntp.org",
            last_check=now,
        )

        result = status.to_dict()

        assert result["is_synced"] is True
        assert result["drift_seconds"] == 0.1
        assert result["local_time"] == now.isoformat()
        assert result["ntp_time"] == now.isoformat()
        assert result["ntp_server"] == "pool.ntp.org"
        assert result["last_check"] == now.isoformat()
        assert result["checks_total"] == 0
        assert result["checks_failed"] == 0

    def test_status_to_dict_with_none_ntp(self):
        """Test converting status to dictionary when NTP time is None."""
        now = datetime.now(timezone.utc)

        status = TimeSyncStatus(
            is_synced=False,
            drift_seconds=0.0,
            local_time=now,
            ntp_time=None,
            ntp_server=None,
            last_check=now,
        )

        result = status.to_dict()

        assert result["ntp_time"] is None
        assert result["ntp_server"] is None


class TestTimeSyncMonitor:
    """Test TimeSyncMonitor class."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_time_sync_monitor()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_time_sync_monitor()

    def test_initialization_without_ntp(self):
        """Test initialization when ntplib is not available."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            assert monitor._is_monitoring is False
            assert monitor._monitor_task is None
            assert isinstance(monitor._status, TimeSyncStatus)
            assert monitor._status.is_synced is True

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = TimeSyncConfig(
            check_interval_seconds=30.0,
            drift_threshold_seconds=0.5,
        )

        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor(config)

            assert monitor.config.check_interval_seconds == 30.0
            assert monitor.config.drift_threshold_seconds == 0.5

    def test_ntp_availability_check(self):
        """Test NTP availability check."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            # Check that NTP availability is set correctly
            # (This depends on whether ntplib is actually installed)
            assert isinstance(monitor._ntp_available, bool)

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping the monitoring loop."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            # Start monitoring
            started = await monitor.start()
            assert started is True
            assert monitor._is_monitoring is True
            assert monitor._monitor_task is not None

            # Try to start again (should fail)
            started_again = await monitor.start()
            assert started_again is False

            # Stop monitoring
            stopped = await monitor.stop()
            assert stopped is True
            assert monitor._is_monitoring is False
            assert monitor._monitor_task is None

    @pytest.mark.asyncio
    async def test_stop_when_not_monitoring(self):
        """Test stopping when monitor is not running."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            stopped = await monitor.stop()
            assert stopped is False

    @pytest.mark.asyncio
    async def test_check_time_drift_without_ntp(self):
        """Test checking time drift when NTP is not available."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()
            monitor._ntp_available = False

            drift = await monitor.check_time_drift()

            assert drift == 0.0
            assert monitor._status.is_synced is True
            assert monitor._status.drift_seconds == 0.0

    @pytest.mark.asyncio
    async def test_check_time_drift_with_ntp_success(self):
        """Test checking time drift with successful NTP response."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()
            monitor._ntp_available = True

            # Create a mock NTP client
            mock_ntp_client = MagicMock()
            mock_response = MagicMock()
            mock_response.tx_time = datetime.now(timezone.utc).timestamp()
            mock_ntp_client.request.return_value = mock_response

            # Set the mock client
            monitor._ntp_client = mock_ntp_client

            drift = await monitor.check_time_drift()

            # Drift should be small (local time vs NTP time)
            assert isinstance(drift, float)
            assert monitor._status.checks_total == 1
            assert monitor._status.ntp_time is not None
            assert monitor._status.ntp_server is not None

    @pytest.mark.asyncio
    async def test_check_time_drift_with_ntp_all_fail(self):
        """Test checking time drift when all NTP servers fail."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()
            monitor._ntp_available = True

            # Create a mock NTP client that raises exception
            mock_ntp_client = MagicMock()
            mock_ntp_client.request.side_effect = Exception("Connection failed")

            # Set the mock client
            monitor._ntp_client = mock_ntp_client

            drift = await monitor.check_time_drift()

            assert drift == 0.0
            assert monitor._status.is_synced is False
            assert monitor._status.checks_failed == 1

    @pytest.mark.asyncio
    async def test_drift_detected_callback(self):
        """Test that drift detected callback is called."""
        callback = Mock()
        config = TimeSyncConfig(
            drift_threshold_seconds=0.1,  # Low threshold for testing
            on_drift_detected=callback,
        )

        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor(config)
            monitor._ntp_available = True

            # Create a mock NTP client
            mock_ntp_client = MagicMock()
            mock_response = MagicMock()
            ntp_time = datetime.now(timezone.utc) - timedelta(seconds=1)
            mock_response.tx_time = ntp_time.timestamp()
            mock_ntp_client.request.return_value = mock_response

            # Set the mock client
            monitor._ntp_client = mock_ntp_client

            await monitor.check_time_drift()

            # Callback should be called
            callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_critical_drift_callback(self):
        """Test that critical drift callback is called in monitor loop."""
        callback = Mock()
        config = TimeSyncConfig(
            check_interval_seconds=0.01,  # Very fast for testing
            drift_threshold_seconds=0.1,
            critical_threshold_seconds=1.0,
            on_critical_drift=callback,
        )

        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor(config)
            monitor._ntp_available = True

            # Create a mock NTP client
            mock_ntp_client = MagicMock()
            mock_response = MagicMock()
            ntp_time = datetime.now(timezone.utc) - timedelta(seconds=6)
            mock_response.tx_time = ntp_time.timestamp()
            mock_ntp_client.request.return_value = mock_response

            # Set the mock client
            monitor._ntp_client = mock_ntp_client

            # Start monitoring (which calls the critical callback)
            await monitor.start()

            # Wait for at least one monitor loop iteration
            await asyncio.sleep(0.1)

            # Stop monitoring
            await monitor.stop()

            # Callback should have been called at least once
            assert callback.call_count > 0

    @pytest.mark.asyncio
    async def test_validate_order_timestamp_success(self):
        """Test order validation when clock is synced."""
        config = TimeSyncConfig(drift_threshold_seconds=1.0)

        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor(config)
            monitor._status.drift_seconds = 0.5  # Within threshold

            order = {"symbol": "AAPL", "quantity": 100}
            result = await monitor.validate_order_timestamp(order)

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_order_timestamp_failure(self):
        """Test order validation when clock is not synced."""
        config = TimeSyncConfig(drift_threshold_seconds=1.0)

        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor(config)
            monitor._status.drift_seconds = 2.0  # Exceeds threshold

            order = {"symbol": "AAPL", "quantity": 100}
            result = await monitor.validate_order_timestamp(order)

            assert result is False

    def test_get_status(self):
        """Test getting current status."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            status = monitor.get_status()

            assert isinstance(status, TimeSyncStatus)
            assert status == monitor._status

    def test_get_drift_seconds(self):
        """Test getting drift seconds."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()
            monitor._status.drift_seconds = 1.5

            drift = monitor.get_drift_seconds()

            assert drift == 1.5

    def test_is_synced(self):
        """Test checking if clock is synced."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            monitor._status.is_synced = True
            assert monitor.is_synced() is True

            monitor._status.is_synced = False
            assert monitor.is_synced() is False

    def test_get_ntp_availability(self):
        """Test getting NTP availability."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            availability = monitor.get_ntp_availability()
            assert isinstance(availability, bool)

    @pytest.mark.asyncio
    async def test_sync_clock_without_ntp(self):
        """Test clock sync when NTP is not available."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()
            monitor._ntp_available = False

            result = await monitor.sync_clock()

            assert result is False

    @pytest.mark.asyncio
    async def test_sync_clock_already_synced(self):
        """Test clock sync when already synced."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()
            monitor._ntp_available = True

            # Mock small drift
            with patch.object(monitor, "check_time_drift", return_value=0.05):
                result = await monitor.sync_clock()

                assert result is True

    @pytest.mark.asyncio
    async def test_force_check(self):
        """Test forcing an immediate time sync check."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor = TimeSyncMonitor()

            # Mock check_time_drift
            expected_drift = 0.5
            with patch.object(monitor, "check_time_drift", return_value=expected_drift):
                result = await monitor.force_check()

                assert result["drift_seconds"] == expected_drift
                assert "is_synced" in result
                assert "threshold" in result
                assert "ntp_server" in result
                assert "local_time" in result
                assert "ntp_available" in result


class TestTimeSyncMonitorSingleton:
    """Test TimeSyncMonitor singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_time_sync_monitor()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_time_sync_monitor()

    def test_get_singleton(self):
        """Test getting singleton instance."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor1 = get_time_sync_monitor()
            monitor2 = get_time_sync_monitor()

            assert monitor1 is monitor2

    def test_get_singleton_with_config(self):
        """Test that config is only used on first call."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            config1 = TimeSyncConfig(check_interval_seconds=30.0)
            config2 = TimeSyncConfig(check_interval_seconds=60.0)

            monitor1 = get_time_sync_monitor(config1)
            monitor2 = get_time_sync_monitor(config2)

            assert monitor1 is monitor2
            # First config should be used
            assert monitor1.config.check_interval_seconds == 30.0

    def test_reset_singleton(self):
        """Test resetting singleton."""
        with patch(
            "app.services.monitoring.time_sync_monitor.TimeSyncMonitor._check_ntp_availability"
        ):
            monitor1 = get_time_sync_monitor()
            reset_time_sync_monitor()
            monitor2 = get_time_sync_monitor()

            assert monitor1 is not monitor2


class TestNTPServers:
    """Test NTP server configuration."""

    def test_ntp_servers_defined(self):
        """Test that NTP servers are defined."""
        assert len(NTP_SERVERS) > 0
        assert all(isinstance(server, str) for server in NTP_SERVERS)

    def test_ntp_servers_include_common_servers(self):
        """Test that common NTP servers are included."""
        assert "pool.ntp.org" in NTP_SERVERS
        assert "time.google.com" in NTP_SERVERS
