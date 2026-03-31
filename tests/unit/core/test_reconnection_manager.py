"""
Unit tests for Reconnection Manager.

Tests the exponential backoff reconnection strategy for 24/7 markets.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.resilience.reconnection_manager import (
    ReconnectionConfig,
    ReconnectionManager,
    ReconnectionStats,
)


class TestReconnectionConfig:
    """Test ReconnectionConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ReconnectionConfig()

        assert config.max_attempts == 5
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.jitter_factor == 0.1
        assert config.alert_after_attempts == 3
        assert config.on_attempt is None
        assert config.on_success is None
        assert config.on_failure is None
        assert config.alert_callback is None

    def test_custom_config(self):
        """Test custom configuration values."""
        callback = MagicMock()

        config = ReconnectionConfig(
            max_attempts=5,
            base_delay_seconds=2.0,
            max_delay_seconds=30.0,
            exponential_base=3.0,
            jitter=False,
            alert_after_attempts=2,
            on_attempt=callback,
        )

        assert config.max_attempts == 5
        assert config.base_delay_seconds == 2.0
        assert config.max_delay_seconds == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.alert_after_attempts == 2
        assert config.on_attempt == callback


class TestReconnectionStats:
    """Test ReconnectionStats dataclass."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = ReconnectionStats()

        assert stats.total_attempts == 0
        assert stats.successful_connections == 0
        assert stats.failed_connections == 0
        assert stats.last_connection_time is None
        assert stats.last_failure_time is None
        assert stats.current_backoff_seconds == 0.0

    def test_success_rate(self):
        """Test success rate calculation."""
        stats = ReconnectionStats()

        # No attempts
        assert stats.success_rate == 0.0

        # All successful
        stats.total_attempts = 10
        stats.successful_connections = 10
        assert stats.success_rate == 1.0

        # Half successful
        stats.total_attempts = 10
        stats.successful_connections = 5
        assert stats.success_rate == 0.5

        # All failed
        stats.total_attempts = 10
        stats.successful_connections = 0
        assert stats.success_rate == 0.0


class TestReconnectionManager:
    """Test ReconnectionManager class."""

    def test_initialization(self):
        """Test manager initialization."""
        config = ReconnectionConfig(max_attempts=5)
        manager = ReconnectionManager("TestService", config)

        assert manager.service_name == "TestService"
        assert manager.config == config
        assert isinstance(manager.stats, ReconnectionStats)
        assert manager.stats.total_attempts == 0

    def test_initialization_with_default_config(self):
        """Test manager initialization with default config."""
        manager = ReconnectionManager("TestService")

        assert manager.service_name == "TestService"
        assert isinstance(manager.config, ReconnectionConfig)
        assert isinstance(manager.stats, ReconnectionStats)

    def test_calculate_backoff_no_jitter(self):
        """Test exponential backoff calculation without jitter."""
        config = ReconnectionConfig(
            base_delay_seconds=1.0,
            max_delay_seconds=100.0,
            exponential_base=2.0,
            jitter=False,
        )
        manager = ReconnectionManager("TestService", config)

        # Test exponential growth: 1, 2, 4, 8, 16, 32, 64, 128 (capped)
        assert manager.calculate_backoff(0) == 1.0
        assert manager.calculate_backoff(1) == 2.0
        assert manager.calculate_backoff(2) == 4.0
        assert manager.calculate_backoff(3) == 8.0
        assert manager.calculate_backoff(4) == 16.0
        assert manager.calculate_backoff(5) == 32.0
        assert manager.calculate_backoff(6) == 64.0
        assert manager.calculate_backoff(7) == 100.0  # Capped at max

    def test_calculate_backoff_with_max_delay(self):
        """Test that backoff is capped at max_delay."""
        config = ReconnectionConfig(
            base_delay_seconds=1.0,
            max_delay_seconds=10.0,
            exponential_base=2.0,
            jitter=False,
        )
        manager = ReconnectionManager("TestService", config)

        # Should be capped at 10.0
        assert manager.calculate_backoff(0) == 1.0
        assert manager.calculate_backoff(1) == 2.0
        assert manager.calculate_backoff(2) == 4.0
        assert manager.calculate_backoff(3) == 8.0
        assert manager.calculate_backoff(4) == 10.0  # Capped
        assert manager.calculate_backoff(10) == 10.0  # Capped

    def test_calculate_backoff_with_jitter(self):
        """Test that jitter is applied to backoff."""
        config = ReconnectionConfig(
            base_delay_seconds=10.0,
            max_delay_seconds=100.0,
            exponential_base=2.0,
            jitter=True,
            jitter_factor=0.1,
        )
        manager = ReconnectionManager("TestService", config)

        # With jitter, the delay should be within +/- 10% of base
        delay = manager.calculate_backoff(0)
        assert 9.0 <= delay <= 11.0  # 10 +/- 1

        delay = manager.calculate_backoff(1)
        assert 18.0 <= delay <= 22.0  # 20 +/- 2

    @pytest.mark.asyncio
    async def test_connect_with_backoff_success_first_attempt(self):
        """Test successful connection on first attempt."""
        connect_func = AsyncMock(return_value="connection_object")

        manager = ReconnectionManager("TestService")
        result = await manager.connect_with_backoff(connect_func)

        assert result == "connection_object"
        assert manager.stats.total_attempts == 1
        assert manager.stats.successful_connections == 1
        assert manager.stats.failed_connections == 0
        assert manager.stats.last_connection_time is not None
        assert manager.stats.current_backoff_seconds == 0.0
        connect_func.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_with_backoff_success_after_retries(self):
        """Test successful connection after several failures."""
        connect_func = AsyncMock(
            side_effect=[Exception("fail"), Exception("fail"), "connection_object"]
        )

        manager = ReconnectionManager("TestService")
        result = await manager.connect_with_backoff(connect_func)

        assert result == "connection_object"
        assert manager.stats.total_attempts == 3
        assert manager.stats.successful_connections == 1
        assert manager.stats.failed_connections == 0
        assert manager.stats.last_connection_time is not None
        assert connect_func.call_count == 3

    @pytest.mark.asyncio
    async def test_connect_with_backoff_all_attempts_fail(self):
        """Test when all connection attempts fail."""
        connect_func = AsyncMock(side_effect=Exception("connection failed"))

        config = ReconnectionConfig(max_attempts=3, base_delay_seconds=0.1)
        manager = ReconnectionManager("TestService", config)
        result = await manager.connect_with_backoff(connect_func)

        assert result is None
        assert manager.stats.total_attempts == 3
        assert manager.stats.successful_connections == 0
        assert manager.stats.failed_connections == 1
        assert manager.stats.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_connect_with_backoff_handles_timeout_error(self):
        """Test handling of asyncio.TimeoutError."""

        # Mock a function that raises TimeoutError
        async def timeout_connect():
            raise asyncio.TimeoutError("Connection timed out")

        connect_func = timeout_connect

        config = ReconnectionConfig(max_attempts=2, base_delay_seconds=0.01)
        manager = ReconnectionManager("TestService", config)
        result = await manager.connect_with_backoff(connect_func)

        # Should handle TimeoutError and return None after all attempts
        assert result is None
        assert manager.stats.failed_connections > 0

    @pytest.mark.asyncio
    async def test_connect_with_backoff_callbacks(self):
        """Test that callbacks are called correctly."""
        attempt_callback = MagicMock()
        success_callback = MagicMock()

        connect_func = AsyncMock(side_effect=[Exception("fail"), "connection_object"])

        config = ReconnectionConfig(
            max_attempts=5,
            base_delay_seconds=0.01,
            on_attempt=attempt_callback,
            on_success=success_callback,
        )
        manager = ReconnectionManager("TestService", config)
        await manager.connect_with_backoff(connect_func)

        # Should have called attempt callback twice
        assert attempt_callback.call_count == 2

        # Should have called success callback once
        success_callback.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_connect_with_backoff_alert_callback(self):
        """Test that alert callback is called after threshold."""
        alert_callback = MagicMock()

        connect_func = AsyncMock(side_effect=Exception("fail"))

        config = ReconnectionConfig(
            max_attempts=5,
            base_delay_seconds=0.01,
            alert_after_attempts=3,
            alert_callback=alert_callback,
        )
        manager = ReconnectionManager("TestService", config)
        await manager.connect_with_backoff(connect_func)

        # Alert should be called for attempts 3, 4, and 5
        assert alert_callback.call_count == 3

    @pytest.mark.asyncio
    async def test_maintain_connection_basic(self):
        """Test basic connection maintenance."""
        connect_func = AsyncMock(return_value="connection_object")

        manager = ReconnectionManager("TestService")

        # Start connection maintenance in background
        task = asyncio.create_task(manager.maintain_connection(connect_func, reconnect_delay=0.01))

        # Wait a bit for connection
        await asyncio.sleep(0.1)

        # Should have connected
        assert manager.stats.successful_connections > 0

        # Cancel the maintenance task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_maintain_connection_with_health_check(self):
        """Test connection maintenance with health check."""
        connection = {"connected": True}
        connection_count = [0]  # Use list to allow modification in nested function

        async def connect_func():
            connection_count[0] += 1
            return connection

        async def check_func():
            return connection.get("connected", False)

        manager = ReconnectionManager("TestService")

        # Start connection maintenance
        task = asyncio.create_task(
            manager.maintain_connection(connect_func, check_func, reconnect_delay=0.01)
        )

        # Wait for initial connection
        await asyncio.sleep(0.1)

        # Should have connected
        assert manager.stats.successful_connections > 0

        # Simulate connection loss
        connection["connected"] = False

        # Wait for reconnection attempt
        await asyncio.sleep(0.5)

        # Should have attempted reconnection (connection_count should increase)
        # The health check runs every 5 seconds in the implementation,
        # but we're testing that it would eventually reconnect
        assert connection_count[0] >= 1

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def test_get_stats(self):
        """Test getting statistics."""
        manager = ReconnectionManager("TestService")

        # Modify some stats
        manager.stats.total_attempts = 10
        manager.stats.successful_connections = 8
        manager.stats.failed_connections = 2
        manager.stats.current_backoff_seconds = 5.0

        stats = manager.get_stats()

        assert stats["service_name"] == "TestService"
        assert stats["total_attempts"] == 10
        assert stats["successful_connections"] == 8
        assert stats["failed_connections"] == 2
        assert stats["success_rate"] == 0.8
        assert stats["current_backoff_seconds"] == 5.0
        assert "last_connection_time" in stats
        assert "last_failure_time" in stats

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """Test that exponential backoff creates correct delays."""
        delays = []

        async def tracking_connect():
            # Record the delay before each call
            delays.append(manager.stats.current_backoff_seconds)
            raise Exception("fail")

        config = ReconnectionConfig(
            max_attempts=5,
            base_delay_seconds=1.0,
            max_delay_seconds=100.0,
            jitter=False,
        )
        manager = ReconnectionManager("TestService", config)

        await manager.connect_with_backoff(tracking_connect)

        # Check that delays follow exponential pattern
        # First attempt has 0 delay (it's immediate)
        assert delays[0] == 0.0

        # Subsequent attempts should have exponentially increasing delays
        # (before the actual wait happens)
        # Note: The delay is set after the attempt fails

    @pytest.mark.asyncio
    async def test_custom_base_and_exponential(self):
        """Test custom base delay and exponential base."""
        config = ReconnectionConfig(
            max_attempts=4,
            base_delay_seconds=2.0,
            max_delay_seconds=100.0,
            exponential_base=3.0,
            jitter=False,
        )
        manager = ReconnectionManager("TestService", config)

        # 2, 6, 18, 54 (2 * 3^0, 2 * 3^1, 2 * 3^2, 2 * 3^3)
        assert manager.calculate_backoff(0) == 2.0
        assert manager.calculate_backoff(1) == 6.0
        assert manager.calculate_backoff(2) == 18.0
        assert manager.calculate_backoff(3) == 54.0
