"""
Unit tests for EmergencyCloser.

Tests the emergency position closing functionality that protects
against catastrophic losses when the system fails.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.emergency_handler.emergency_closer import (
    EmergencyCloser,
    EmergencyCloseResult,
    EmergencyTrigger,
)


@pytest.fixture
def mock_broker():
    """Create a mock broker."""
    broker = AsyncMock()
    broker.get_positions = AsyncMock(return_value=[])
    broker.place_order = AsyncMock(return_value=None)
    return broker


@pytest.fixture
def mock_alert_callback():
    """Create a mock alert callback."""
    return Mock()


@pytest.fixture
def emergency_closer(mock_broker, mock_alert_callback):
    """Create an EmergencyCloser instance for testing."""
    return EmergencyCloser(
        broker=mock_broker,
        alert_callback=mock_alert_callback,
        require_confirmation=False,
    )


class TestEmergencyTrigger:
    """Tests for EmergencyTrigger enum."""

    def test_trigger_values(self):
        """Test that all trigger types have correct values."""
        assert EmergencyTrigger.CONNECTION_LOST.value == "connection_lost"
        assert EmergencyTrigger.SYSTEM_SHUTDOWN.value == "system_shutdown"
        assert EmergencyTrigger.CRITICAL_ERROR.value == "critical_error"
        assert EmergencyTrigger.MANUAL_TRIGGER.value == "manual_trigger"
        assert EmergencyTrigger.HEARTBEAT_FAILURE.value == "heartbeat_failure"
        assert EmergencyTrigger.MEMORY_EXCEEDED.value == "memory_exceeded"


class TestEmergencyCloseResult:
    """Tests for EmergencyCloseResult dataclass."""

    def test_result_creation(self):
        """Test creating an EmergencyCloseResult."""
        result = EmergencyCloseResult(
            success=True,
            trigger=EmergencyTrigger.MANUAL_TRIGGER,
            total_positions=5,
            closed_positions=5,
            failed_positions=0,
            total_value=Decimal("10000.00"),
            execution_time_seconds=2.5,
        )

        assert result.success is True
        assert result.trigger == EmergencyTrigger.MANUAL_TRIGGER
        assert result.total_positions == 5
        assert result.closed_positions == 5
        assert result.failed_positions == 0
        assert result.total_value == Decimal("10000.00")
        assert result.execution_time_seconds == 2.5
        assert result.errors == []

    def test_result_to_dict(self):
        """Test converting EmergencyCloseResult to dictionary."""
        result = EmergencyCloseResult(
            success=True,
            trigger=EmergencyTrigger.CONNECTION_LOST,
            total_positions=3,
            closed_positions=2,
            failed_positions=1,
            total_value=Decimal("5000.00"),
            execution_time_seconds=1.8,
            errors=["Connection timeout"],
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["trigger"] == "connection_lost"
        assert result_dict["total_positions"] == 3
        assert result_dict["closed_positions"] == 2
        assert result_dict["failed_positions"] == 1
        assert result_dict["total_value"] == "5000.00"
        assert result_dict["execution_time_seconds"] == 1.8
        assert result_dict["errors"] == ["Connection timeout"]
        assert "timestamp" in result_dict


class TestEmergencyCloser:
    """Tests for EmergencyCloser class."""

    def test_initialization(self, mock_broker, mock_alert_callback):
        """Test EmergencyCloser initialization."""
        closer = EmergencyCloser(
            broker=mock_broker,
            alert_callback=mock_alert_callback,
            require_confirmation=False,
            confirmation_timeout_seconds=30.0,
        )

        assert closer.broker == mock_broker
        assert closer.alert_callback == mock_alert_callback
        assert closer.require_confirmation is False
        assert closer.confirmation_timeout_seconds == 30.0
        assert closer._is_closing is False
        assert closer._audit_log == []
        assert closer._last_trigger is None
        assert closer._last_close_time is None

    def test_initialization_defaults(self, mock_broker):
        """Test EmergencyCloser initialization with defaults."""
        closer = EmergencyCloser(broker=mock_broker)

        assert closer.broker == mock_broker
        assert closer.alert_callback is None
        assert closer.require_confirmation is False
        assert closer.confirmation_timeout_seconds == 30.0

    @pytest.mark.asyncio
    async def test_close_all_positions_no_positions(self, emergency_closer, mock_broker):
        """Test closing all positions when there are none."""
        mock_broker.get_positions.return_value = []

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.total_positions == 0
        assert result.closed_positions == 0
        assert result.failed_positions == 0
        assert result.trigger == EmergencyTrigger.MANUAL_TRIGGER
        mock_broker.get_positions.assert_called_once()
        mock_broker.place_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_all_positions_success(self, emergency_closer, mock_broker):
        """Test successfully closing all positions."""
        # Create mock positions
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.side = "LONG"
        mock_position.quantity = Decimal("100")
        mock_position.current_price = Decimal("150.00")

        mock_broker.get_positions.return_value = [mock_position]
        mock_broker.place_order.return_value = {"order_id": 12345}

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.total_positions == 1
        assert result.closed_positions == 1
        assert result.failed_positions == 0
        assert result.trigger == EmergencyTrigger.MANUAL_TRIGGER
        mock_broker.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_all_positions_partial_failure(self, emergency_closer, mock_broker):
        """Test closing positions with some failures."""
        # Create mock positions
        mock_position1 = Mock()
        mock_position1.symbol = "AAPL"
        mock_position1.side = "LONG"
        mock_position1.quantity = Decimal("100")
        mock_position1.current_price = Decimal("150.00")

        mock_position2 = Mock()
        mock_position2.symbol = "MSFT"
        mock_position2.side = "LONG"
        mock_position2.quantity = Decimal("50")
        mock_position2.current_price = Decimal("300.00")

        mock_broker.get_positions.return_value = [mock_position1, mock_position2]

        # First order succeeds, second fails
        async def side_effect(*args, **kwargs):
            symbol = kwargs.get("symbol", args[0] if args else None)
            if symbol == "AAPL":
                return {"order_id": 12345}
            else:
                return None

        mock_broker.place_order.side_effect = side_effect

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is False
        assert result.total_positions == 2
        assert result.closed_positions == 1
        assert result.failed_positions == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_close_all_positions_already_closing(self, emergency_closer):
        """Test that concurrent close attempts are prevented."""
        emergency_closer._is_closing = True

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is False
        assert "already in progress" in result.errors[0]

    @pytest.mark.asyncio
    async def test_close_all_positions_short_position(self, emergency_closer, mock_broker):
        """Test closing a short position (should buy to cover)."""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.side = "SHORT"
        mock_position.quantity = Decimal("100")
        mock_position.current_price = Decimal("150.00")

        mock_broker.get_positions.return_value = [mock_position]
        mock_broker.place_order.return_value = {"order_id": 12345}

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        # For SHORT position, we should BUY
        mock_broker.place_order.assert_called_once()
        call_args = mock_broker.place_order.call_args
        assert call_args[1]["side"] == "BUY"

    @pytest.mark.asyncio
    async def test_on_connection_lost(self, emergency_closer, mock_broker, mock_alert_callback):
        """Test handling connection loss."""
        mock_broker.get_positions.return_value = []
        mock_broker.place_order.return_value = {"order_id": 12345}

        result = await emergency_closer.on_connection_lost()

        assert result.trigger == EmergencyTrigger.CONNECTION_LOST
        mock_alert_callback.assert_called_once()
        assert "connection lost" in mock_alert_callback.call_args[0][0].lower()
        assert len(emergency_closer._audit_log) == 1
        assert emergency_closer._audit_log[0]["trigger"] == "connection_lost"

    @pytest.mark.asyncio
    async def test_on_system_shutdown(self, emergency_closer, mock_broker, mock_alert_callback):
        """Test handling system shutdown."""
        mock_broker.get_positions.return_value = []
        mock_broker.place_order.return_value = {"order_id": 12345}

        result = await emergency_closer.on_system_shutdown()

        assert result.trigger == EmergencyTrigger.SYSTEM_SHUTDOWN
        mock_alert_callback.assert_called_once()
        assert "shutting down" in mock_alert_callback.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_on_critical_error_critical(
        self, emergency_closer, mock_broker, mock_alert_callback
    ):
        """Test handling critical error."""
        mock_broker.get_positions.return_value = []
        mock_broker.place_order.return_value = {"order_id": 12345}

        error = ConnectionError("Connection lost")
        result = await emergency_closer.on_critical_error(error)

        assert result.trigger == EmergencyTrigger.CRITICAL_ERROR
        mock_alert_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_critical_error_non_critical(self, emergency_closer, mock_broker):
        """Test that non-critical errors don't trigger close."""
        error = ValueError("Invalid parameter")

        result = await emergency_closer.on_critical_error(error)

        assert result.success is False
        assert "not critical enough" in result.errors[0]
        mock_broker.get_positions.assert_not_called()

    @pytest.mark.asyncio
    async def test_manual_trigger(self, emergency_closer, mock_broker, mock_alert_callback):
        """Test manual emergency trigger."""
        mock_broker.get_positions.return_value = []
        mock_broker.place_order.return_value = {"order_id": 12345}

        result = await emergency_closer.manual_trigger(reason="Testing emergency close")

        assert result.trigger == EmergencyTrigger.MANUAL_TRIGGER
        mock_alert_callback.assert_called_once()
        assert "testing emergency close" in mock_alert_callback.call_args[0][0].lower()
        assert len(emergency_closer._audit_log) == 1

    def test_is_error_critical_by_type(self, emergency_closer):
        """Test error criticality determination by type."""
        assert emergency_closer._is_error_critical(ConnectionError()) is True
        assert emergency_closer._is_error_critical(TimeoutError()) is True
        assert emergency_closer._is_error_critical(MemoryError()) is True
        assert emergency_closer._is_error_critical(ValueError("test")) is False

    def test_is_error_critical_by_message(self, emergency_closer):
        """Test error criticality determination by message."""
        assert emergency_closer._is_error_critical(Exception("connection lost")) is True
        assert emergency_closer._is_error_critical(Exception("connection failed")) is True
        assert emergency_closer._is_error_critical(Exception("authentication failed")) is True
        assert emergency_closer._is_error_critical(Exception("insufficient funds")) is True
        assert emergency_closer._is_error_critical(Exception("order rejected")) is True
        assert emergency_closer._is_error_critical(Exception("market closed")) is True
        assert emergency_closer._is_error_critical(Exception("some other error")) is False

    def test_get_audit_log(self, emergency_closer):
        """Test retrieving audit log."""
        emergency_closer._audit_log = [
            {"timestamp": "2024-01-01T12:00:00", "trigger": "manual_trigger"},
            {"timestamp": "2024-01-01T13:00:00", "trigger": "connection_lost"},
        ]

        log = emergency_closer.get_audit_log()

        assert len(log) == 2
        assert log[0]["trigger"] == "manual_trigger"
        assert log[1]["trigger"] == "connection_lost"

    def test_get_audit_log_with_limit(self, emergency_closer):
        """Test retrieving audit log with limit."""
        emergency_closer._audit_log = [
            {"timestamp": "2024-01-01T12:00:00", "trigger": "manual_trigger"},
            {"timestamp": "2024-01-01T13:00:00", "trigger": "connection_lost"},
        ]

        log = emergency_closer.get_audit_log(limit=1)

        assert len(log) == 1
        assert log[0]["trigger"] == "connection_lost"

    def test_get_last_trigger(self, emergency_closer):
        """Test getting last trigger."""
        emergency_closer._last_trigger = EmergencyTrigger.CONNECTION_LOST

        assert emergency_closer.get_last_trigger() == EmergencyTrigger.CONNECTION_LOST

    def test_get_last_close_time(self, emergency_closer):
        """Test getting last close time."""
        from app.shared.utils.timezone_utils import utc_now

        test_time = utc_now()
        emergency_closer._last_close_time = test_time

        assert emergency_closer.get_last_close_time() == test_time

    @pytest.mark.asyncio
    async def test_send_alert_with_callback(self, emergency_closer, mock_alert_callback):
        """Test sending alert with callback."""
        await emergency_closer._send_alert("Test alert message")

        mock_alert_callback.assert_called_once_with("Test alert message")

    @pytest.mark.asyncio
    async def test_send_alert_without_callback(self, mock_broker):
        """Test sending alert without callback (logs only)."""
        closer = EmergencyCloser(broker=mock_broker, alert_callback=None)

        # Should not raise exception
        await closer._send_alert("Test alert message")

    @pytest.mark.asyncio
    async def test_close_position_timeout(self, emergency_closer, mock_broker):
        """Test handling timeout when closing position."""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.side = "LONG"
        mock_position.quantity = Decimal("100")
        mock_position.current_price = Decimal("150.00")

        mock_broker.get_positions.return_value = [mock_position]

        # Simulate timeout
        async def timeout_side_effect(*args, **kwargs):
            await asyncio.sleep(35)
            return {"order_id": 12345}

        mock_broker.place_order.side_effect = timeout_side_effect

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is False
        assert result.failed_positions == 1
        assert "timeout" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_close_position_exception(self, emergency_closer, mock_broker):
        """Test handling exception when closing position."""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.side = "LONG"
        mock_position.quantity = Decimal("100")
        mock_position.current_price = Decimal("150.00")

        mock_broker.get_positions.return_value = [mock_position]
        mock_broker.place_order.side_effect = Exception("Broker error")

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is False
        assert result.failed_positions == 1
        assert "error" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_get_positions_error_handling(self, emergency_closer, mock_broker):
        """Test handling error when fetching positions."""
        mock_broker.get_positions.side_effect = Exception("Connection error")

        result = await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Should handle gracefully and return success with 0 positions
        assert result.success is True
        assert result.total_positions == 0

    @pytest.mark.asyncio
    async def test_require_confirmation_not_confirmed(self, mock_broker, mock_alert_callback):
        """Test emergency close with confirmation required but not given."""
        closer = EmergencyCloser(
            broker=mock_broker,
            alert_callback=mock_alert_callback,
            require_confirmation=True,
            confirmation_timeout_seconds=0.1,
        )

        # Mock confirmation to return False (not confirmed)
        with patch.object(closer, "_wait_for_confirmation", return_value=False):
            result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Verify close was not executed
        assert result.success is False
        assert "not confirmed" in result.errors[0]
        # Verify broker was not called (positions not fetched)
        mock_broker.get_positions.assert_not_called()

    @pytest.mark.asyncio
    async def test_connection_lost_bypasses_confirmation(self, emergency_closer, mock_broker):
        """Test that connection lost bypasses confirmation requirement."""
        emergency_closer.require_confirmation = True
        mock_broker.get_positions.return_value = []
        mock_broker.place_order.return_value = {"order_id": 12345}

        result = await emergency_closer.on_connection_lost()

        # Should succeed despite confirmation being required
        assert result.trigger == EmergencyTrigger.CONNECTION_LOST
        mock_broker.get_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_reset_after_close(self, emergency_closer, mock_broker):
        """Test that _is_closing flag is reset after operation."""
        mock_broker.get_positions.return_value = []
        mock_broker.place_order.return_value = {"order_id": 12345}

        assert emergency_closer._is_closing is False

        await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert emergency_closer._is_closing is False

    @pytest.mark.asyncio
    async def test_state_reset_on_exception(self, emergency_closer, mock_broker):
        """Test that _is_closing flag is reset even if exception occurs."""
        mock_broker.get_positions.side_effect = Exception("Unexpected error")

        assert emergency_closer._is_closing is False

        try:
            await emergency_closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)
        except Exception:
            pass

        # Flag should be reset
        assert emergency_closer._is_closing is False
