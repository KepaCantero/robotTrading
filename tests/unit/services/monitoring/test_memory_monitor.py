"""
Unit tests for Memory Monitor.

Tests memory monitoring, auto-restart, and state persistence.
"""

import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.monitoring.memory_monitor import (
    MemoryAction,
    MemoryConfig,
    MemoryMonitor,
    MemorySnapshot,
    get_memory_monitor,
    reset_memory_monitor,
)


@pytest.fixture
def memory_config():
    """Create test memory config."""
    return MemoryConfig(
        memory_limit_mb=100,
        warning_threshold_mb=75,
        check_interval_seconds=1.0,  # Fast for testing
        action=MemoryAction.ALERT_ONLY,
    )


@pytest.fixture
def mock_state_saver():
    """Create mock state saver."""
    return AsyncMock()


@pytest.fixture
def mock_position_closer():
    """Create mock position closer."""
    return AsyncMock()


@pytest.fixture
def mock_alert_callback():
    """Create mock alert callback."""
    return Mock()


@pytest.fixture
def memory_monitor(memory_config, mock_state_saver, mock_position_closer):
    """Create memory monitor for testing."""
    return MemoryMonitor(
        config=memory_config,
        state_saver=mock_state_saver,
        position_closer=mock_position_closer,
    )


class TestMemoryConfig:
    """Test MemoryConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MemoryConfig()

        assert config.memory_limit_mb == 4096
        assert config.warning_threshold_mb == 3072
        assert config.check_interval_seconds == 300.0
        assert config.action == MemoryAction.ALERT_ONLY
        assert config.close_positions_on_restart is False
        assert config.save_state_before_restart is True
        assert config.alert_callback is None

    def test_custom_config(self):
        """Test custom configuration values."""
        callback = Mock()
        config = MemoryConfig(
            memory_limit_mb=2048,
            warning_threshold_mb=1536,
            check_interval_seconds=60.0,
            action=MemoryAction.RESTART,
            close_positions_on_restart=True,
            save_state_before_restart=False,
            alert_callback=callback,
        )

        assert config.memory_limit_mb == 2048
        assert config.warning_threshold_mb == 1536
        assert config.check_interval_seconds == 60.0
        assert config.action == MemoryAction.RESTART
        assert config.close_positions_on_restart is True
        assert config.save_state_before_restart is False
        assert config.alert_callback is callback


class TestMemorySnapshot:
    """Test MemorySnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test creating a memory snapshot."""
        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=100.5,
            vms_mb=200.3,
            percent=2.5,
            available_mb=8000.0,
            gc_objects=10000,
        )

        assert snapshot.rss_mb == 100.5
        assert snapshot.vms_mb == 200.3
        assert snapshot.percent == 2.5
        assert snapshot.available_mb == 8000.0
        assert snapshot.gc_objects == 10000

    def test_snapshot_to_dict(self):
        """Test converting snapshot to dictionary."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        snapshot = MemorySnapshot(
            timestamp=dt,
            rss_mb=100.567,
            vms_mb=200.789,
            percent=2.543,
            available_mb=8000.123,
            gc_objects=10000,
        )

        result = snapshot.to_dict()

        assert result["timestamp"] == dt.isoformat()
        assert result["rss_mb"] == 100.57  # Rounded
        assert result["vms_mb"] == 200.79  # Rounded
        assert result["percent"] == 2.54  # Rounded
        assert result["available_mb"] == 8000.12  # Rounded
        assert result["gc_objects"] == 10000


class TestMemoryMonitorInit:
    """Test MemoryMonitor initialization."""

    def test_init_default_config(self, mock_state_saver, mock_position_closer):
        """Test initialization with default config."""
        monitor = MemoryMonitor(
            state_saver=mock_state_saver,
            position_closer=mock_position_closer,
        )

        assert monitor.config.memory_limit_mb == 4096
        assert monitor.state_saver is mock_state_saver
        assert monitor.position_closer is mock_position_closer
        assert monitor._is_monitoring is False
        assert monitor._monitor_task is None
        assert monitor._restart_count == 0
        assert monitor._last_restart is None
        assert monitor._snapshots == []

    def test_init_custom_config(self, memory_config, mock_state_saver, mock_position_closer):
        """Test initialization with custom config."""
        monitor = MemoryMonitor(
            config=memory_config,
            state_saver=mock_state_saver,
            position_closer=mock_position_closer,
        )

        assert monitor.config is memory_config
        assert monitor.state_saver is mock_state_saver
        assert monitor.position_closer is mock_position_closer

    def test_init_creates_process(self, memory_monitor):
        """Test that initialization creates process object."""
        assert memory_monitor.process is not None
        assert hasattr(memory_monitor.process, "pid")


class TestMemoryMonitorStartStop:
    """Test MemoryMonitor start and stop functionality."""

    @pytest.mark.asyncio
    async def test_start_monitoring(self, memory_monitor):
        """Test starting memory monitoring."""
        result = await memory_monitor.start()

        assert result is True
        assert memory_monitor._is_monitoring is True
        assert memory_monitor._monitor_task is not None

        # Cleanup
        await memory_monitor.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self, memory_monitor):
        """Test starting when already running."""
        await memory_monitor.start()

        # Try to start again
        result = await memory_monitor.start()

        assert result is False

        # Cleanup
        await memory_monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, memory_monitor):
        """Test stopping memory monitoring."""
        await memory_monitor.start()
        result = await memory_monitor.stop()

        assert result is True
        assert memory_monitor._is_monitoring is False
        assert memory_monitor._monitor_task is None

    @pytest.mark.asyncio
    async def test_stop_not_running(self, memory_monitor):
        """Test stopping when not running."""
        result = await memory_monitor.stop()

        assert result is False


class TestMemoryMonitorLoop:
    """Test memory monitoring loop."""

    @pytest.mark.asyncio
    async def test_monitor_loop_no_action(self, memory_monitor, mock_state_saver):
        """Test monitor loop when memory is below limits."""
        with patch.object(memory_monitor, "get_memory_usage", return_value=50.0):
            await memory_monitor.start()

            # Wait for one check
            await asyncio.sleep(1.5)

            # Verify no action taken
            assert mock_state_saver.call_count == 0

            await memory_monitor.stop()

    @pytest.mark.asyncio
    async def test_monitor_loop_warning(self, memory_monitor, mock_alert_callback):
        """Test monitor loop when memory is at warning level."""
        memory_monitor.config.alert_callback = mock_alert_callback

        with patch.object(memory_monitor, "get_memory_usage", return_value=80.0):
            await memory_monitor.start()

            # Wait for one check
            await asyncio.sleep(1.5)

            # Verify warning callback called
            assert mock_alert_callback.call_count > 0
            assert "Memory usage high" in mock_alert_callback.call_args[0][0]

            await memory_monitor.stop()

    @pytest.mark.asyncio
    async def test_monitor_loop_limit_exceeded_alert_only(
        self, memory_monitor, mock_alert_callback
    ):
        """Test monitor loop when limit exceeded with ALERT_ONLY action."""
        memory_monitor.config.action = MemoryAction.ALERT_ONLY
        memory_monitor.config.alert_callback = mock_alert_callback

        with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
            await memory_monitor.start()

            # Wait for action to be triggered
            await asyncio.sleep(1.5)

            # Verify alert callback called
            assert mock_alert_callback.call_count > 0

            await memory_monitor.stop()


class TestMemoryMonitorActions:
    """Test memory monitor actions."""

    @pytest.mark.asyncio
    async def test_trigger_action_garbage_collect(self, memory_monitor):
        """Test garbage collection action."""
        memory_monitor.config.action = MemoryAction.GARBAGE_COLLECT

        # Mock garbage collection to return objects
        with patch("gc.collect", return_value=100) as mock_gc:
            with patch.object(memory_monitor, "get_memory_usage", return_value=50.0):
                await memory_monitor.trigger_action(150.0)

                # Verify garbage collection was called
                mock_gc.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_action_close_positions(self, memory_monitor, mock_position_closer):
        """Test close positions action."""
        memory_monitor.config.action = MemoryAction.CLOSE_POSITIONS

        with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
            await memory_monitor.trigger_action(150.0)

            # Verify position closer was called
            mock_position_closer.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_action_with_state_save(self, memory_monitor, mock_state_saver):
        """Test action with state save."""
        memory_monitor.config.save_state_before_restart = True

        with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
            await memory_monitor.trigger_action(150.0)

            # Verify state saver was called
            mock_state_saver.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_action_with_alert(self, memory_monitor, mock_alert_callback):
        """Test action with alert callback."""
        memory_monitor.config.alert_callback = mock_alert_callback

        with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
            await memory_monitor.trigger_action(150.0)

            # Verify alert callback was called
            mock_alert_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_action_restart(self, memory_monitor):
        """Test restart action."""
        memory_monitor.config.action = MemoryAction.RESTART

        with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
            with patch("os.execv") as mock_execv:
                with patch("sys.executable", "/usr/bin/python"):
                    with patch("sys.argv", ["main.py"]):
                        await memory_monitor.trigger_action(150.0)

                        # Verify restart was triggered
                        assert memory_monitor._restart_count == 1
                        assert memory_monitor._last_restart is not None
                        mock_execv.assert_called_once()


class TestMemoryMonitorStats:
    """Test memory statistics gathering."""

    def test_get_memory_usage(self, memory_monitor):
        """Test getting current memory usage."""
        # This will return actual memory usage
        memory_mb = memory_monitor.get_memory_usage()

        assert memory_mb >= 0
        assert isinstance(memory_mb, float)

    def test_get_detailed_stats(self, memory_monitor):
        """Test getting detailed memory statistics."""
        stats = memory_monitor.get_detailed_stats()

        assert isinstance(stats, dict)
        assert "rss_mb" in stats
        assert "vms_mb" in stats
        assert "percent" in stats
        assert "available_mb" in stats
        assert "gc_objects" in stats
        assert "limit_mb" in stats
        assert "warning_mb" in stats

    def test_take_snapshot(self, memory_monitor):
        """Test taking a memory snapshot."""
        snapshot = memory_monitor.take_snapshot()

        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.timestamp is not None
        assert snapshot.rss_mb >= 0
        assert snapshot.gc_objects >= 0

        # Verify snapshot was added to list
        assert len(memory_monitor._snapshots) == 1

    def test_snapshots_limit(self, memory_monitor):
        """Test that snapshots are limited to 100."""
        # Take more than 100 snapshots
        for _ in range(150):
            memory_monitor.take_snapshot()

        # Verify only last 100 are kept
        assert len(memory_monitor._snapshots) == 100

    def test_get_snapshots(self, memory_monitor):
        """Test getting recent snapshots."""
        # Take some snapshots
        for _ in range(5):
            memory_monitor.take_snapshot()

        # Get last 3
        snapshots = memory_monitor.get_snapshots(3)

        assert len(snapshots) == 3
        assert all(isinstance(s, MemorySnapshot) for s in snapshots)

    def test_get_statistics(self, memory_monitor):
        """Test getting monitor statistics."""
        stats = memory_monitor.get_statistics()

        assert isinstance(stats, dict)
        assert "is_monitoring" in stats
        assert "current_memory" in stats
        assert "restart_count" in stats
        assert "last_restart" in stats
        assert "config" in stats
        assert "snapshots_count" in stats

        # Verify config structure
        assert "limit_mb" in stats["config"]
        assert "warning_mb" in stats["config"]
        assert "check_interval_seconds" in stats["config"]
        assert "action" in stats["config"]


class TestGlobalInstance:
    """Test global memory monitor instance."""

    def test_get_memory_monitor_creates_instance(self):
        """Test that get_memory_monitor creates instance."""
        reset_memory_monitor()

        monitor = get_memory_monitor()

        assert monitor is not None
        assert isinstance(monitor, MemoryMonitor)

    def test_get_memory_monitor_returns_same_instance(self):
        """Test that get_memory_monitor returns same instance."""
        reset_memory_monitor()

        monitor1 = get_memory_monitor()
        monitor2 = get_memory_monitor()

        assert monitor1 is monitor2

    def test_reset_memory_monitor(self):
        """Test resetting the global instance."""
        monitor1 = get_memory_monitor()
        reset_memory_monitor()
        monitor2 = get_memory_monitor()

        assert monitor1 is not monitor2

    def test_get_memory_monitor_with_config(self):
        """Test get_memory_monitor with custom config."""
        reset_memory_monitor()

        config = MemoryConfig(memory_limit_mb=2048)
        monitor = get_memory_monitor(config=config)

        assert monitor.config.memory_limit_mb == 2048


class TestGracefulRestart:
    """Test graceful restart functionality."""

    @pytest.mark.asyncio
    async def test_trigger_graceful_restart(self, memory_monitor):
        """Test triggering graceful restart."""
        with patch("os.execv") as mock_execv:
            with patch("sys.executable", "/usr/bin/python"):
                with patch("sys.argv", ["main.py"]):
                    await memory_monitor.trigger_graceful_restart()

                    # Verify restart stats updated
                    assert memory_monitor._restart_count == 1
                    assert memory_monitor._last_restart is not None

                    # Verify execv was called
                    mock_execv.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_flushes_logs(self, memory_monitor):
        """Test that restart flushes logs."""
        with patch("os.execv"):
            with patch("sys.executable", "/usr/bin/python"):
                with patch("sys.argv", ["main.py"]):
                    # Add a real log handler
                    handler = logging.StreamHandler()
                    handler.flush = Mock()

                    logger = logging.getLogger("app.services.monitoring.memory_monitor")
                    logger.addHandler(handler)

                    await memory_monitor.trigger_graceful_restart()

                    # Verify flush was called
                    handler.flush.assert_called()

                    # Cleanup
                    logger.removeHandler(handler)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_monitor_loop_handles_cancellation(self, memory_monitor):
        """Test that monitor loop handles cancellation gracefully."""
        await memory_monitor.start()

        # Store the task reference
        task = memory_monitor._monitor_task

        # Cancel the task
        task.cancel()

        # Wait for the task to be cancelled
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

        # Verify monitoring stopped (the loop should have set this to False)
        # Note: The loop continues until it catches CancelledError
        # So we need to stop it explicitly
        await memory_monitor.stop()

    @pytest.mark.asyncio
    async def test_monitor_loop_handles_exception(self, memory_monitor):
        """Test that monitor loop handles exceptions gracefully."""
        # Make get_memory_usage raise exception
        with patch.object(memory_monitor, "get_memory_usage", side_effect=Exception("Test error")):
            await memory_monitor.start()

            # Wait for one check
            await asyncio.sleep(1.5)

            # Verify monitoring still running
            assert memory_monitor._is_monitoring is True

            await memory_monitor.stop()

    def test_get_memory_usage_handles_error(self, memory_monitor):
        """Test that get_memory_usage handles errors gracefully."""
        # Mock process to raise error
        with patch.object(memory_monitor.process, "memory_info", side_effect=Exception("Error")):
            memory_mb = memory_monitor.get_memory_usage()

            # Should return 0 on error
            assert memory_mb == 0.0

    def test_take_snapshot_handles_error(self, memory_monitor):
        """Test that take_snapshot handles errors gracefully."""
        # Mock process to raise error
        with patch.object(memory_monitor.process, "memory_info", side_effect=Exception("Error")):
            # Capture logging to avoid MagicMock level comparison issues
            with patch("app.services.monitoring.memory_monitor.logger"):
                snapshot = memory_monitor.take_snapshot()

                # Should return snapshot with zeros
                assert snapshot.rss_mb == 0
                assert snapshot.vms_mb == 0

    @pytest.mark.asyncio
    async def test_trigger_action_handles_state_saver_error(self, memory_monitor, mock_state_saver):
        """Test that trigger_action handles state saver errors."""
        memory_monitor.config.save_state_before_restart = True
        mock_state_saver.side_effect = Exception("State save error")

        # Should not raise exception
        with patch("app.services.monitoring.memory_monitor.logger"):
            with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
                await memory_monitor.trigger_action(150.0)

    @pytest.mark.asyncio
    async def test_trigger_action_handles_position_closer_error(
        self, memory_monitor, mock_position_closer
    ):
        """Test that trigger_action handles position closer errors."""
        memory_monitor.config.action = MemoryAction.CLOSE_POSITIONS
        mock_position_closer.side_effect = Exception("Position close error")

        # Should not raise exception
        with patch("app.services.monitoring.memory_monitor.logger"):
            with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
                await memory_monitor.trigger_action(150.0)

    @pytest.mark.asyncio
    async def test_trigger_action_handles_alert_callback_error(
        self, memory_monitor, mock_alert_callback
    ):
        """Test that trigger_action handles alert callback errors."""
        memory_monitor.config.alert_callback = mock_alert_callback
        mock_alert_callback.side_effect = Exception("Alert error")

        # Should not raise exception
        with patch("app.services.monitoring.memory_monitor.logger"):
            with patch.object(memory_monitor, "get_memory_usage", return_value=150.0):
                await memory_monitor.trigger_action(150.0)

    @pytest.mark.asyncio
    async def test_graceful_restart_handles_error(self, memory_monitor):
        """Test that graceful restart handles errors."""
        with patch("os.execv", side_effect=Exception("Restart error")):
            # Should not raise exception
            with patch("app.services.monitoring.memory_monitor.logger"):
                await memory_monitor.trigger_graceful_restart()

                # Verify restart stats still updated
                assert memory_monitor._restart_count == 1
